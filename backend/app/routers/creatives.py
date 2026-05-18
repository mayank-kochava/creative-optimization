from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.ingestion.orchestrator import CreativeIngestionOrchestrator, IngestionResult
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair
from app.models.metric import CreativeMetric
from app.schemas.analysis import AnnotationResponse, BBoxResponse
from app.schemas.analysis import KPISummary as KPISummarySchema
from app.schemas.analysis import OllamaAnalysisResponse
from app.schemas.creative import CreativeDetail, UploadResponse
from app.services.analysis_provider import OllamaProvider
from app.services.annotation_pipeline import AnnotationPipeline
from app.services.content_classifier import ContentClassifier
from app.services.deduplication import DeduplicationService
from app.services.fatigue_detector import FatigueDetector
from app.services.kpi_aggregator import KPIAggregator
from app.services.video_ingestion import VideoIngestionService

router = APIRouter()

# Module-level singletons — created once at import, not per-request
_provider = OllamaProvider(base_url=settings.ollama_base_url)
_annotation_pipeline = AnnotationPipeline()
_video_service = VideoIngestionService()
_content_classifier = ContentClassifier(_provider)


def get_orchestrator(db: AsyncSession) -> CreativeIngestionOrchestrator:
    """Return a new orchestrator bound to the given db session."""
    return CreativeIngestionOrchestrator(
        db=db,
        analysis_provider=_provider,
        dedup_service=DeduplicationService(db),
        annotation_pipeline=_annotation_pipeline,
        video_service=_video_service,
        content_classifier=_content_classifier,
        fatigue_detector=FatigueDetector(db),
    )


# ---------------------------------------------------------------------------
# POST /campaigns/{campaign_id}/creatives
# ---------------------------------------------------------------------------

@router.post("/campaigns/{campaign_id}/creatives", status_code=201, response_model=UploadResponse)
async def upload_creative(
    campaign_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    orchestrator = get_orchestrator(db)
    result: IngestionResult = await orchestrator.ingest(file=file, campaign_id=campaign_id)
    return UploadResponse(
        creative_id=result.creative_id,
        duplicate_detected=result.duplicate_detected,
        duplicate_id=result.duplicate_id,
        duplicate_type=result.duplicate_type,
        hamming_distance=result.hamming_distance,
        analysis_status=result.analysis_status,
    )


# ---------------------------------------------------------------------------
# GET /creatives/{creative_id}
# ---------------------------------------------------------------------------

@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
async def get_creative_detail(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Creative)
        .where(Creative.id == creative_id)
        .options(selectinload(Creative.analysis))
    )
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Build analysis schema from ORM object
    analysis_response: OllamaAnalysisResponse | None = None
    if creative.analysis:
        a = creative.analysis
        analysis_response = OllamaAnalysisResponse(
            scores=a.scores,
            overall_score=a.overall_score,
            persuasion_strategy=a.persuasion_strategy,
            dominant_emotion=a.dominant_emotion,
            strengths=a.strengths,
            weaknesses=a.weaknesses,
            recommendations=a.recommendations,
            explanation=a.explanation,
            benchmark_percentile=a.benchmark_percentile,
            status=a.status,
        )

    # Build annotations
    ann_result = await db.execute(
        select(CreativeAnnotation).where(CreativeAnnotation.creative_id == creative_id)
    )
    annotations = ann_result.scalars().all()
    annotation_responses = [
        AnnotationResponse(
            annotation_type=ann.annotation_type,
            bbox=BBoxResponse(**ann.bbox),
            label=ann.label,
            confidence=ann.confidence,
        )
        for ann in annotations
    ]

    # Build KPI summary
    aggregator = KPIAggregator(db)
    kpi_dataclass = await aggregator.get_kpi_summary(creative_id)
    kpi_schema: KPISummarySchema | None = None
    if kpi_dataclass:
        kpi_schema = KPISummarySchema(
            total_impressions=kpi_dataclass.total_impressions,
            total_clicks=kpi_dataclass.total_clicks,
            total_installs=kpi_dataclass.total_installs,
            total_spend=kpi_dataclass.total_spend,
            total_revenue=kpi_dataclass.total_revenue,
            ctr=kpi_dataclass.ctr,
            cvr=kpi_dataclass.cvr,
            cpi=kpi_dataclass.cpi,
            roas=kpi_dataclass.roas,
        )

    return CreativeDetail(
        id=creative.id,
        campaign_id=creative.campaign_id,
        filename=creative.filename,
        storage_path=creative.storage_path,
        format=creative.format,
        width=creative.width,
        height=creative.height,
        duration_seconds=creative.duration_seconds,
        file_size_bytes=creative.file_size_bytes,
        fatigue_status=creative.fatigue_status,
        analysis=analysis_response,
        annotations=annotation_responses,
        kpi=kpi_schema,
        created_at=creative.created_at,
        updated_at=creative.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /creatives/{creative_id}/fatigue
# ---------------------------------------------------------------------------

@router.get("/creatives/{creative_id}/fatigue")
async def get_creative_fatigue(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    detector = FatigueDetector(db)
    status = await detector.compute_fatigue_status(creative_id)

    # Fetch recent metrics to build daily_ctr list
    from datetime import date, timedelta

    today = date.today()
    since = today - timedelta(days=14)
    metrics_result = await db.execute(
        select(CreativeMetric)
        .where(
            CreativeMetric.creative_id == creative_id,
            CreativeMetric.date >= since,
            CreativeMetric.date <= today,
        )
        .order_by(CreativeMetric.date.asc())
    )
    metrics = metrics_result.scalars().all()

    daily_ctr = [
        {
            "date": str(m.date),
            "ctr": m.clicks / m.impressions if m.impressions > 0 else None,
        }
        for m in metrics
    ]

    return {
        "status": status,
        "daily_ctr": daily_ctr,
        "threshold": FatigueDetector.FATIGUE_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# GET /creatives/{creative_id}/duplicates
# ---------------------------------------------------------------------------

@router.get("/creatives/{creative_id}/duplicates")
async def get_creative_duplicates(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    pairs_result = await db.execute(
        select(DuplicatePair).where(
            or_(
                DuplicatePair.creative_id_a == creative_id,
                DuplicatePair.creative_id_b == creative_id,
            )
        )
    )
    pairs = pairs_result.scalars().all()

    return [
        {
            "duplicate_id": (
                pair.creative_id_b if pair.creative_id_a == creative_id else pair.creative_id_a
            ),
            "hamming_distance": pair.hamming_distance,
            "duplicate_type": pair.duplicate_type,
            "detected_at": str(pair.detected_at),
        }
        for pair in pairs
    ]


# ---------------------------------------------------------------------------
# GET /creatives/{creative_id}/image  (kept from original stub)
# ---------------------------------------------------------------------------

@router.post("/creatives/{creative_id}/reanalyse", status_code=202)
async def reanalyse_creative(creative_id: int, db: AsyncSession = Depends(get_db)):
    """Delete degraded analysis and re-queue background analysis."""
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Only allow re-analysis when current analysis is degraded (or missing)
    existing = await db.execute(
        select(CreativeAnalysis).where(CreativeAnalysis.creative_id == creative_id)
    )
    analysis_row = existing.scalar_one_or_none()
    if analysis_row and analysis_row.status != "degraded":
        raise HTTPException(status_code=409, detail="Analysis already complete")

    if analysis_row:
        await db.delete(analysis_row)
        await db.commit()

    import asyncio
    orchestrator = CreativeIngestionOrchestrator()
    asyncio.create_task(orchestrator._run_analysis(creative_id, creative.storage_path))
    return {"status": "queued", "creative_id": creative_id}


@router.get("/creatives/{creative_id}/image")
async def get_creative_image(creative_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    path = Path(creative.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(str(path))
