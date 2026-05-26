import asyncio
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.config import settings
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative

ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp", "gif", "mp4", "mov"}
IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_FORMATS = {"mp4", "mov"}


@dataclass
class IngestionResult:
    creative_id: int
    duplicate_detected: bool
    duplicate_id: int | None = None
    duplicate_type: str | None = None
    hamming_distance: int | None = None
    analysis_status: str = "pending"


class CreativeIngestionOrchestrator:
    def __init__(self, db, analysis_provider, dedup_service,
                 annotation_pipeline, video_service, content_classifier, fatigue_detector):
        self.db = db
        self.analysis_provider = analysis_provider
        self.dedup_service = dedup_service
        self.annotation_pipeline = annotation_pipeline
        self.video_service = video_service
        self.content_classifier = content_classifier
        self.fatigue_detector = fatigue_detector

    async def ingest(self, file: UploadFile, campaign_id: int) -> IngestionResult:
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_FORMATS:
            raise HTTPException(status_code=415, detail=f"Unsupported format: {ext}")

        content = await file.read()
        max_size = settings.max_video_size_bytes if ext in VIDEO_FORMATS else settings.max_image_size_bytes
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File exceeds size limit")

        storage_dir = Path(settings.storage_path) / str(campaign_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        storage_path = storage_dir / unique_name
        storage_path.write_bytes(content)

        try:
            width = height = duration_seconds = None
            if ext in IMAGE_FORMATS:
                from PIL import Image
                img = Image.open(storage_path)
                width, height = img.size
            elif ext in VIDEO_FORMATS:
                meta = self.video_service.validate_video(storage_path)
                width, height, duration_seconds = meta.width, meta.height, meta.duration_seconds

            import ctypes

            import imagehash
            from PIL import Image
            if ext in VIDEO_FORMATS:
                keyframes = await self.video_service.extract_keyframes(storage_path, duration_seconds)
                hash_image = Image.open(keyframes[0]) if keyframes else Image.new("RGB", (8, 8))
            else:
                hash_image = Image.open(storage_path)
            phash_unsigned = int(str(imagehash.phash(hash_image, hash_size=8)), 16)
            phash_val = ctypes.c_int64(phash_unsigned).value

            classify_path = storage_path if ext in IMAGE_FORMATS else (keyframes[0] if keyframes else storage_path)
            is_ad = await self.content_classifier.is_advertisement(classify_path)
            if not is_ad:
                storage_path.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail="Not an advertisement creative")

            norm_ext = "jpg" if ext == "jpeg" else ext
            creative = Creative(
                campaign_id=campaign_id,
                filename=file.filename,
                storage_path=str(storage_path),
                format=norm_ext,
                width=width,
                height=height,
                duration_seconds=duration_seconds,
                file_size_bytes=len(content),
                phash=phash_val,
                fatigue_status="insufficient_data",
            )
            self.db.add(creative)
            await self.db.flush()

            duplicate_pair = await self.dedup_service.check_and_register(
                phash=phash_val,
                creative_id=creative.id,
                campaign_id=campaign_id,
            )
            await self.db.commit()

            if duplicate_pair:
                other_id = (duplicate_pair.creative_id_b
                            if duplicate_pair.creative_id_a == creative.id
                            else duplicate_pair.creative_id_a)

                from sqlalchemy import select as _sa_select
                orig_result = await self.db.execute(
                    _sa_select(CreativeAnalysis).where(CreativeAnalysis.creative_id == other_id)
                )
                orig_analysis = orig_result.scalar_one_or_none()
                if orig_analysis:
                    self.db.add(CreativeAnalysis(
                        creative_id=creative.id,
                        scores=orig_analysis.scores,
                        overall_score=orig_analysis.overall_score,
                        persuasion_strategy=orig_analysis.persuasion_strategy,
                        dominant_emotion=orig_analysis.dominant_emotion,
                        strengths=orig_analysis.strengths,
                        weaknesses=orig_analysis.weaknesses,
                        recommendations=orig_analysis.recommendations,
                        explanation=orig_analysis.explanation,
                        benchmark_percentile=orig_analysis.benchmark_percentile,
                        status=orig_analysis.status,
                        search_tags=orig_analysis.search_tags,
                    ))
                    await self.db.commit()

                return IngestionResult(
                    creative_id=creative.id,
                    duplicate_detected=True,
                    duplicate_id=other_id,
                    duplicate_type=duplicate_pair.duplicate_type,
                    hamming_distance=duplicate_pair.hamming_distance,
                    analysis_status="skipped_duplicate",
                )

            asyncio.create_task(self._run_analysis(creative.id, storage_path, ext))

            return IngestionResult(
                creative_id=creative.id,
                duplicate_detected=False,
                analysis_status="pending",
            )

        except HTTPException:
            raise
        except Exception as e:
            storage_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _run_analysis(self, creative_id: int, path: Path, ext: str) -> None:
        logger.info("Analysis started — creative_id=%d ext=%s", creative_id, ext)
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                if ext in VIDEO_FORMATS:
                    meta = self.video_service.validate_video(path)
                    keyframes = await self.video_service.extract_keyframes(path, meta.duration_seconds)
                    logger.info("Extracted %d keyframes for creative_id=%d", len(keyframes), creative_id)
                    result = await self.analysis_provider.analyse_video_keyframes(keyframes)
                    for kf in keyframes:
                        kf.unlink(missing_ok=True)
                else:
                    result = await self.analysis_provider.analyse_image(path)

                from sqlalchemy import select as _select

                from app.services.benchmark import BenchmarkService
                phash_row = await db.execute(
                    _select(Creative.phash).where(Creative.id == creative_id)
                )
                stored_phash = phash_row.scalar_one()
                benchmark_svc = BenchmarkService()
                benchmark_percentile = benchmark_svc.compute_percentile(stored_phash)

                analysis = CreativeAnalysis(
                    creative_id=creative_id,
                    scores=result.scores.model_dump(),
                    overall_score=result.overall_score,
                    persuasion_strategy=result.persuasion_strategy,
                    dominant_emotion=result.dominant_emotion,
                    strengths=result.strengths,
                    weaknesses=result.weaknesses,
                    recommendations=[r.model_dump() for r in result.recommendations],
                    explanation=result.explanation,
                    benchmark_percentile=benchmark_percentile,
                    status=result.status,
                    search_tags=result.search_tags,
                )
                db.add(analysis)

                if ext in IMAGE_FORMATS:
                    annotations = await self.annotation_pipeline.annotate(path)
                    for ann in annotations:
                        db.add(CreativeAnnotation(
                            creative_id=creative_id,
                            annotation_type=ann.annotation_type,
                            bbox=ann.bbox,
                            label=ann.label,
                            confidence=ann.confidence,
                        ))

                await db.commit()
        except Exception:
            pass
