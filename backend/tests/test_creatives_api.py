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
import random


def make_jpg_bytes(seed=42) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (300, 250), (rng.randint(0,255), rng.randint(0,255), rng.randint(0,255)))
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
    import random
    c = Creative(
        campaign_id=campaign.id, filename="analyzed.jpg", storage_path="/tmp/analyzed.jpg",
        format="jpg", width=300, height=250, file_size_bytes=5000,
        phash=random.randint(-9223372036854775808, 9223372036854775807),
        fatigue_status="healthy"
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
    jpg = make_jpg_bytes(seed=99)
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
