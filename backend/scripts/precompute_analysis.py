"""
Pre-compute analysis for all seeded creatives.

Usage:
    cd backend
    PYTHONPATH=. python3.11 scripts/precompute_analysis.py           # analyse missing only
    PYTHONPATH=. python3.11 scripts/precompute_analysis.py --reset   # truncate then re-analyse all
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.services.provider_state import get_active_provider
from app.services.annotation_pipeline import AnnotationPipeline


async def main(reset: bool = False):
    provider = get_active_provider()
    print(f"Provider: {type(provider).__name__}")
    await provider.prewarm()
    print("Ready.\n")

    annotation_pipeline = AnnotationPipeline()

    async with AsyncSessionLocal() as db:
        if reset:
            print("Truncating existing analyses and annotations...")
            await db.execute(text("TRUNCATE creative_analyses, creative_annotations RESTART IDENTITY"))
            await db.commit()
            print("Done.\n")
        result = await db.execute(
            select(Creative).where(
                ~Creative.id.in_(
                    select(CreativeAnalysis.creative_id)
                )
            ).order_by(Creative.id)
        )
        creatives = result.scalars().all()
        total = len(creatives)
        print(f"Found {total} creatives without analysis.\n")

        for i, creative in enumerate(creatives, 1):
            print(f"[{i}/{total}] Creative #{creative.id}: {creative.filename}")
            path = Path(creative.storage_path)

            if not path.exists():
                print(f"  ✗ File not found: {path} — skipping")
                continue

            try:
                if creative.format in ("mp4", "mov"):
                    from app.services.video_ingestion import VideoIngestionService
                    video_svc = VideoIngestionService()
                    try:
                        meta = video_svc.validate_video(path)
                        keyframes = await video_svc.extract_keyframes(path, meta.duration_seconds)
                        result_analysis = await provider.analyse_video_keyframes(keyframes)
                        for kf in keyframes:
                            kf.unlink(missing_ok=True)
                    except Exception as e:
                        print(f"  ✗ Video analysis failed: {e}")
                        continue
                else:
                    result_analysis = await provider.analyse_image(path)

                analysis = CreativeAnalysis(
                    creative_id=creative.id,
                    scores=result_analysis.scores.model_dump(),
                    overall_score=result_analysis.overall_score,
                    persuasion_strategy=result_analysis.persuasion_strategy,
                    dominant_emotion=result_analysis.dominant_emotion,
                    strengths=result_analysis.strengths,
                    weaknesses=result_analysis.weaknesses,
                    recommendations=result_analysis.recommendations,
                    explanation=result_analysis.explanation,
                    status=result_analysis.status,
                )
                db.add(analysis)

                if creative.format not in ("mp4", "mov"):
                    annotations = await annotation_pipeline.annotate(path)
                    for ann in annotations:
                        db.add(CreativeAnnotation(
                            creative_id=creative.id,
                            annotation_type=ann.annotation_type,
                            bbox=ann.bbox,
                            label=ann.label,
                            confidence=ann.confidence,
                        ))

                await db.commit()
                print(f"  ✓ Score: {result_analysis.overall_score}/10 | Strategy: {result_analysis.persuasion_strategy}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                await db.rollback()

    print(f"\nPre-computation complete!")


if __name__ == "__main__":
    asyncio.run(main(reset="--reset" in sys.argv))
