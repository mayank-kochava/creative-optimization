"""
Pre-compute Ollama analysis for all seeded creatives.
Run this the night before the demo — takes ~15 minutes for 50 images.

Usage:
    cd backend
    python scripts/precompute_analysis.py
"""
import asyncio
import os
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.services.analysis_provider import OllamaProvider
from app.services.annotation_pipeline import AnnotationPipeline


async def main():
    print("Pre-warming Ollama model qwen2.5vl:7b...")
    provider = OllamaProvider()
    await provider.prewarm()
    print("Model ready.\n")

    annotation_pipeline = AnnotationPipeline()

    async with AsyncSessionLocal() as db:
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
    asyncio.run(main())
