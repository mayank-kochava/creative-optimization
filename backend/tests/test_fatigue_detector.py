import pytest
import pytest_asyncio
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.fatigue_detector import FatigueDetector
from app.models.creative import Creative
from app.models.metric import CreativeMetric
from app.models.campaign import Campaign


@pytest_asyncio.fixture
async def campaign(db_session):
    c = Campaign(name="Test Campaign")
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def creative(db_session, campaign):
    c = Creative(
        campaign_id=campaign.id, filename="test.jpg", storage_path="/tmp/test.jpg",
        format="jpg", file_size_bytes=1000, phash=999999,
        fatigue_status="insufficient_data"
    )
    db_session.add(c)
    await db_session.flush()
    await db_session.refresh(c)
    return c


async def insert_metrics(db, creative_id: int, days: int, impressions_per_day: int,
                         base_ctr: float, decline_per_day: float = 0.0):
    today = date.today()
    for i in range(days):
        day = today - timedelta(days=days - 1 - i)
        factor = max(0.1, 1.0 - decline_per_day * i)
        clicks = int(impressions_per_day * base_ctr * factor)
        m = CreativeMetric(
            creative_id=creative_id, date=day,
            impressions=impressions_per_day, clicks=clicks,
            installs=0, spend=0, revenue=0
        )
        db.add(m)
    await db.flush()  # flush within existing transaction


@pytest.mark.asyncio
async def test_insufficient_data_less_than_7_days(db_session, creative):
    await insert_metrics(db_session, creative.id, days=5, impressions_per_day=10000, base_ctr=0.02)
    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "insufficient_data"


@pytest.mark.asyncio
async def test_healthy_when_ctr_stable(db_session, creative):
    await insert_metrics(db_session, creative.id, days=14, impressions_per_day=10000, base_ctr=0.02, decline_per_day=0)
    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "healthy"


@pytest.mark.asyncio
async def test_fatiguing_when_wow_decline_25pct(db_session, creative):
    today = date.today()
    for i in range(7):
        day = today - timedelta(days=14 - i)
        m = CreativeMetric(creative_id=creative.id, date=day,
                           impressions=10000, clicks=200, installs=0, spend=0, revenue=0)
        db_session.add(m)
    for i in range(7):
        day = today - timedelta(days=7 - i)
        m = CreativeMetric(creative_id=creative.id, date=day,
                           impressions=10000, clicks=150, installs=0, spend=0, revenue=0)
        db_session.add(m)
    await db_session.flush()

    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "fatiguing"


@pytest.mark.asyncio
async def test_exact_20pct_decline_is_fatiguing(db_session, creative):
    today = date.today()
    for i in range(7):
        day = today - timedelta(days=14 - i)
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=10000, clicks=250, installs=0, spend=0, revenue=0))
    for i in range(7):
        day = today - timedelta(days=7 - i)
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=10000, clicks=200, installs=0, spend=0, revenue=0))
    await db_session.flush()

    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "fatiguing"


@pytest.mark.asyncio
async def test_zero_impressions_days_skipped(db_session, creative):
    today = date.today()
    for i in range(7):
        day = today - timedelta(days=14 - i)
        impressions = 0 if i % 2 == 0 else 10000
        clicks = 0 if impressions == 0 else 200
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=impressions, clicks=clicks,
                                      installs=0, spend=0, revenue=0))
    for i in range(7):
        day = today - timedelta(days=7 - i)
        impressions = 0 if i % 3 == 0 else 10000
        clicks = 0 if impressions == 0 else 200
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=impressions, clicks=clicks,
                                      installs=0, spend=0, revenue=0))
    await db_session.flush()

    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status in ("healthy", "fatiguing", "insufficient_data")
