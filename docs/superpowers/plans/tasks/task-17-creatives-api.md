# Task 17: Creative Upload + Detail Endpoints

**Files to modify/create:**
- `backend/app/routers/creatives.py` (replace stub from Task 16)
- `backend/tests/test_creatives_api.py`

**Prereq:** Tasks 15 (orchestrator) + 16 (campaign API) complete.

---

## Step 1: Write failing tests

```python
# backend/tests/test_creatives_api.py
import io
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image
from unittest.mock import AsyncMock, patch
from app.main import app
from app.database import get_db
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.analysis import CreativeAnalysis
from app.models.metric import CreativeMetric
from datetime import date, timedelta
from decimal import Decimal


def make_jpg_bytes(w=300, h=250) -> bytes:
    img = Image.new("RGB", (w, h), "blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def campaign(db_session):
    c = Campaign(name="Upload Test Campaign", platform_tags=["facebook"])
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest.fixture
async def creative_with_analysis(db_session, campaign):
    c = Creative(
        campaign_id=campaign.id, filename="analyzed.jpg", storage_path="/tmp/analyzed.jpg",
        format="jpg", width=300, height=250, file_size_bytes=5000,
        phash=12345678, fatigue_status="healthy"
    )
    db_session.add(c)
    await db_session.flush()
    a = CreativeAnalysis(
        creative_id=c.id,
        scores={"hook_strength": 8, "cta_clarity": 7, "visual_quality": 9,
                "message_clarity": 7, "emotional_resonance": 8, "social_proof": 4, "brand_consistency": 6},
        overall_score=7, persuasion_strategy="aspirational", dominant_emotion="excitement",
        strengths=["Good hook"], weaknesses=["Low social proof"],
        recommendations=["Add testimonials", "Boost CTA", "Simplify copy"],
        explanation="Effective creative.", status="complete"
    )
    db_session.add(a)
    today = date.today()
    for i in range(7):
        db_session.add(CreativeMetric(
            creative_id=c.id, date=today - timedelta(days=6 - i),
            impressions=10000, clicks=300, installs=30,
            spend=Decimal("50.00"), revenue=Decimal("120.00")
        ))
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest.mark.asyncio
async def test_upload_jpg_returns_201(client, campaign, tmp_path):
    jpg = make_jpg_bytes()
    with patch("app.routers.creatives.get_orchestrator") as mock_orch:
        from app.ingestion.orchestrator import IngestionResult
        mock_orch.return_value.ingest = AsyncMock(
            return_value=IngestionResult(creative_id=42, duplicate_detected=False)
        )
        resp = await client.post(
            f"/campaigns/{campaign.id}/creatives",
            files={"file": ("test.jpg", io.BytesIO(jpg), "image/jpeg")}
        )
    assert resp.status_code == 201
    assert "creative_id" in resp.json()


@pytest.mark.asyncio
async def test_get_creative_detail(client, creative_with_analysis):
    resp = await client.get(f"/creatives/{creative_with_analysis.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == creative_with_analysis.id
    assert data["analysis"] is not None
    assert data["analysis"]["overall_score"] == 7
    assert "kpi" in data


@pytest.mark.asyncio
async def test_get_creative_not_found(client):
    resp = await client.get("/creatives/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fatigue_endpoint(client, creative_with_analysis):
    resp = await client.get(f"/creatives/{creative_with_analysis.id}/fatigue")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("healthy", "fatiguing", "insufficient_data")
    assert "daily_ctr" in data


@pytest.mark.asyncio
async def test_duplicates_endpoint_empty(client, creative_with_analysis):
    resp = await client.get(f"/creatives/{creative_with_analysis.id}/duplicates")
    assert resp.status_code == 200
    assert resp.json() == []
```

Run: `cd backend && pytest tests/test_creatives_api.py -v`
Expected: FAIL — routes not implemented.

---

## Step 2: Create `backend/app/routers/creatives.py`

```python
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair
from app.schemas.analysis import AnnotationResponse, KPISummary, OllamaAnalysisResponse
from app.schemas.creative import CreativeDetail, UploadResponse
from app.services.fatigue_detector import FatigueDetector
from app.services.kpi_aggregator import KPIAggregator

router = APIRouter(tags=["creatives"])

# Module-level singletons — initialized once at startup, not per-request.
# AnnotationPipeline loads Haar cascade XML from disk; VideoIngestionService
# validates ffmpeg on init. Creating these per-request wastes I/O on every upload.
from app.config import settings as _settings
from app.services.analysis_provider import OllamaProvider as _OllamaProvider
from app.services.annotation_pipeline import AnnotationPipeline as _AnnotationPipeline
from app.services.video_ingestion import VideoIngestionService as _VideoIngestionService
from app.services.content_classifier import ContentClassifier as _ContentClassifier

_provider = _OllamaProvider(base_url=_settings.ollama_base_url)
_annotation_pipeline = _AnnotationPipeline()
_video_service = _VideoIngestionService()
_content_classifier = _ContentClassifier(_provider)


def get_orchestrator(db: AsyncSession = Depends(get_db)):
    """Build the ingestion orchestrator — reuses module-level singletons, injects per-request db."""
    from app.ingestion.orchestrator import CreativeIngestionOrchestrator
    from app.services.deduplication import DeduplicationService
    from app.services.fatigue_detector import FatigueDetector

    return CreativeIngestionOrchestrator(
        db=db,
        analysis_provider=_provider,
        dedup_service=DeduplicationService(db),
        annotation_pipeline=_annotation_pipeline,
        video_service=_video_service,
        content_classifier=_content_classifier,
        fatigue_detector=FatigueDetector(db),
    )


@router.post("/campaigns/{campaign_id}/creatives",
             response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_creative(
    campaign_id: int,
    file: UploadFile = File(...),
    orchestrator=Depends(get_orchestrator),
):
    result = await orchestrator.ingest(file, campaign_id=campaign_id)
    return UploadResponse(
        creative_id=result.creative_id,
        duplicate_detected=result.duplicate_detected,
        duplicate_id=result.duplicate_id,
        duplicate_type=result.duplicate_type,
        hamming_distance=result.hamming_distance,
        analysis_status=result.analysis_status,
    )


@router.get("/creatives/{creative_id}", response_model=CreativeDetail)
async def get_creative(creative_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    # Load analysis
    analysis_result = await db.execute(
        select(CreativeAnalysis).where(CreativeAnalysis.creative_id == creative_id)
    )
    analysis_row = analysis_result.scalar_one_or_none()

    # Load annotations
    ann_result = await db.execute(
        select(CreativeAnnotation).where(CreativeAnnotation.creative_id == creative_id)
    )
    annotation_rows = ann_result.scalars().all()

    # Load KPI
    kpi_agg = KPIAggregator(db)
    kpi = await kpi_agg.get_kpi_summary(creative_id, days=30)

    analysis = None
    if analysis_row:
        from app.schemas.analysis import AnalysisScores
        analysis = OllamaAnalysisResponse(
            scores=AnalysisScores(**analysis_row.scores),
            overall_score=analysis_row.overall_score,
            persuasion_strategy=analysis_row.persuasion_strategy,
            dominant_emotion=analysis_row.dominant_emotion,
            strengths=analysis_row.strengths,
            weaknesses=analysis_row.weaknesses,
            recommendations=analysis_row.recommendations,
            explanation=analysis_row.explanation,
            benchmark_percentile=analysis_row.benchmark_percentile,
            status=analysis_row.status,
        )

    kpi_summary = None
    if kpi:
        kpi_summary = KPISummary(
            total_impressions=kpi.total_impressions,
            total_clicks=kpi.total_clicks,
            total_installs=kpi.total_installs,
            total_spend=kpi.total_spend,
            total_revenue=kpi.total_revenue,
            ctr=kpi.ctr, cvr=kpi.cvr, cpi=kpi.cpi, roas=kpi.roas,
        )

    return CreativeDetail(
        id=creative.id, campaign_id=creative.campaign_id,
        filename=creative.filename, storage_path=creative.storage_path,
        format=creative.format, width=creative.width, height=creative.height,
        duration_seconds=creative.duration_seconds, file_size_bytes=creative.file_size_bytes,
        fatigue_status=creative.fatigue_status, analysis=analysis,
        annotations=[AnnotationResponse(
            annotation_type=a.annotation_type, bbox=a.bbox,
            label=a.label, confidence=a.confidence
        ) for a in annotation_rows],
        kpi=kpi_summary,
        created_at=creative.created_at, updated_at=creative.updated_at,
    )


@router.get("/creatives/{creative_id}/fatigue")
async def get_fatigue(creative_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    detector = FatigueDetector(db)
    status = await detector.compute_fatigue_status(creative_id)

    kpi_agg = KPIAggregator(db)
    kpi = await kpi_agg.get_kpi_summary(creative_id, days=14)
    daily_ctr = []
    if kpi:
        daily_ctr = [
            {"date": str(d.date), "ctr": d.ctr}
            for d in kpi.daily_trend
        ]

    return {"status": status, "daily_ctr": daily_ctr, "threshold": 0.20}


@router.get("/creatives/{creative_id}/duplicates")
async def get_duplicates(creative_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DuplicatePair).where(
            (DuplicatePair.creative_id_a == creative_id) |
            (DuplicatePair.creative_id_b == creative_id)
        )
    )
    pairs = result.scalars().all()
    return [
        {
            "id": p.id,
            "creative_id_a": p.creative_id_a,
            "creative_id_b": p.creative_id_b,
            "hamming_distance": p.hamming_distance,
            "duplicate_type": p.duplicate_type,
            "detected_at": str(p.detected_at),
        }
        for p in pairs
    ]
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_creatives_api.py -v
```

Expected: all 5 tests PASS.

---

## Step 4: Run full test suite

```bash
cd backend && pytest -v
```

Expected: all tests PASS.

---

## Step 5: Commit

```bash
git add backend/app/routers/creatives.py backend/tests/test_creatives_api.py
git commit -m "feat: creative API — upload endpoint, detail, fatigue trend, duplicates list"
```
