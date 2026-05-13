# Task 15: Ingestion Orchestrator

**Files to create:**
- `backend/app/ingestion/orchestrator.py`
- `backend/tests/test_ingestion_orchestrator.py`

**Prereq:** Tasks 08-14 complete (all services exist).

---

## Step 1: Write failing tests

```python
# backend/tests/test_ingestion_orchestrator.py
import io
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from PIL import Image
from app.ingestion.orchestrator import CreativeIngestionOrchestrator, IngestionResult
from app.config import settings


def make_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), size=len(content),
                      headers={"content-type": content_type})


def make_jpg_bytes(w=300, h=250) -> bytes:
    img = Image.new("RGB", (w, h), "red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def mock_services(db_session):
    analysis_provider = AsyncMock()
    from app.schemas.analysis import OllamaAnalysisResponse, AnalysisScores
    analysis_provider.analyse_image.return_value = OllamaAnalysisResponse(
        scores=AnalysisScores(hook_strength=8, cta_clarity=7, visual_quality=9,
                              message_clarity=7, emotional_resonance=8, social_proof=4, brand_consistency=6),
        overall_score=7, persuasion_strategy="aspirational", dominant_emotion="excitement",
        strengths=["Good"], weaknesses=["Bad"],
        recommendations=["Fix A", "Fix B", "Fix C"],
        explanation="Good ad."
    )
    dedup = AsyncMock()
    dedup.check_and_register.return_value = None  # no duplicate
    annotation = AsyncMock()
    annotation.annotate.return_value = []
    video_svc = MagicMock()
    classifier = AsyncMock()
    classifier.is_advertisement.return_value = True
    fatigue = AsyncMock()
    fatigue.compute_fatigue_status.return_value = "insufficient_data"
    return analysis_provider, dedup, annotation, video_svc, classifier, fatigue


@pytest.fixture
def orchestrator(db_session, mock_services, tmp_path):
    ap, dedup, ann, video, classifier, fatigue = mock_services
    settings.storage_path = str(tmp_path)
    return CreativeIngestionOrchestrator(
        db=db_session,
        analysis_provider=ap,
        dedup_service=dedup,
        annotation_pipeline=ann,
        video_service=video,
        content_classifier=classifier,
        fatigue_detector=fatigue,
    )


@pytest.mark.asyncio
async def test_ingest_jpg_returns_creative_id(orchestrator, db_session):
    # need campaign in DB first
    from app.models.campaign import Campaign
    c = Campaign(name="Test", platform_tags=[])
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    upload = make_upload_file(make_jpg_bytes(), "test.jpg", "image/jpeg")
    result = await orchestrator.ingest(upload, campaign_id=c.id)
    assert isinstance(result, IngestionResult)
    assert result.creative_id > 0
    assert result.duplicate_detected is False


@pytest.mark.asyncio
async def test_unsupported_format_raises_415(orchestrator, db_session):
    from fastapi import HTTPException
    upload = make_upload_file(b"fake pdf content", "test.pdf", "application/pdf")
    with pytest.raises(HTTPException) as exc:
        await orchestrator.ingest(upload, campaign_id=1)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_oversized_image_raises_413(orchestrator, db_session):
    from fastapi import HTTPException
    large_content = b"x" * (settings.max_image_size_bytes + 1)
    upload = make_upload_file(large_content, "big.jpg", "image/jpeg")
    with pytest.raises(HTTPException) as exc:
        await orchestrator.ingest(upload, campaign_id=1)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_duplicate_detected_returns_duplicate_info(orchestrator, db_session, mock_services):
    ap, dedup, ann, video, classifier, fatigue = mock_services
    from app.models.duplicate import DuplicatePair
    dedup.check_and_register.return_value = DuplicatePair(
        creative_id_a=1, creative_id_b=2, hamming_distance=0, duplicate_type="self"
    )
    from app.models.campaign import Campaign
    c = Campaign(name="Test2", platform_tags=[])
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    upload = make_upload_file(make_jpg_bytes(), "dup.jpg", "image/jpeg")
    result = await orchestrator.ingest(upload, campaign_id=c.id)
    assert result.duplicate_detected is True
    assert result.hamming_distance == 0
```

Run: `cd backend && pytest tests/test_ingestion_orchestrator.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/ingestion/orchestrator.py`

```python
import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

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
        # 1. Validate format
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_FORMATS:
            raise HTTPException(status_code=415, detail=f"Unsupported format: {ext}")

        # 2. Read and check size
        content = await file.read()
        max_size = settings.max_video_size_bytes if ext in VIDEO_FORMATS else settings.max_image_size_bytes
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File exceeds size limit")

        # 3. Save to storage
        storage_dir = Path(settings.storage_path) / str(campaign_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        storage_path = storage_dir / unique_name
        storage_path.write_bytes(content)

        try:
            # 4. Get dimensions + validate video
            width = height = duration_seconds = None
            if ext in IMAGE_FORMATS:
                from PIL import Image
                img = Image.open(storage_path)
                width, height = img.size
            elif ext in VIDEO_FORMATS:
                meta = self.video_service.validate_video(storage_path)
                width, height, duration_seconds = meta.width, meta.height, meta.duration_seconds

            # 5. Compute pHash (use first keyframe for video)
            import imagehash
            from PIL import Image
            if ext in VIDEO_FORMATS:
                keyframes = await self.video_service.extract_keyframes(storage_path, duration_seconds)
                hash_image = Image.open(keyframes[0]) if keyframes else Image.new("RGB", (8, 8))
            else:
                hash_image = Image.open(storage_path)
            import ctypes
            phash_unsigned = int(str(imagehash.phash(hash_image, hash_size=8)), 16)
            phash_val = ctypes.c_int64(phash_unsigned).value  # convert to signed BIGINT range

            # 6. Content classification
            classify_path = storage_path if ext in IMAGE_FORMATS else (keyframes[0] if keyframes else storage_path)
            is_ad = await self.content_classifier.is_advertisement(classify_path)
            if not is_ad:
                storage_path.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail="Not an advertisement creative")

            # 7. Create Creative DB row
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

            # 8. Check duplicates
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
                return IngestionResult(
                    creative_id=creative.id,
                    duplicate_detected=True,
                    duplicate_id=other_id,
                    duplicate_type=duplicate_pair.duplicate_type,
                    hamming_distance=duplicate_pair.hamming_distance,
                    analysis_status="skipped_duplicate",
                )

            # 9. Fire-and-forget analysis
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
        """Background task: run analysis + annotation, save results."""
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                # Analysis
                if ext in VIDEO_FORMATS:
                    meta = self.video_service.validate_video(path)
                    keyframes = await self.video_service.extract_keyframes(path, meta.duration_seconds)
                    result = await self.analysis_provider.analyse_video_keyframes(keyframes)
                    for kf in keyframes:
                        kf.unlink(missing_ok=True)
                else:
                    result = await self.analysis_provider.analyse_image(path)

                # Compute benchmark percentile against CVPR corpus
                from app.services.benchmark import BenchmarkService
                from sqlalchemy import select as _select
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
                    recommendations=result.recommendations,
                    explanation=result.explanation,
                    benchmark_percentile=benchmark_percentile,
                    status=result.status,
                )
                db.add(analysis)

                # Annotations (images only)
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
            pass  # analysis failure is non-fatal
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_ingestion_orchestrator.py -v
```

Expected: all 4 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/ingestion/orchestrator.py backend/tests/test_ingestion_orchestrator.py
git commit -m "feat: ingestion orchestrator — upload flow with validation, dedup, fire-and-forget analysis"
```
