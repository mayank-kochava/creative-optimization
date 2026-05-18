import pytest
import random
from datetime import date, timedelta
from decimal import Decimal
from app.services.kpi_aggregator import KPIAggregator
from app.models.metric import CreativeMetric
from app.models.creative import Creative
from app.models.campaign import Campaign


@pytest.fixture
async def creative_with_metrics(db_session):
    camp = Campaign(name="KPI Test Camp", platform_tags=[])
    db_session.add(camp)
    await db_session.flush()

    c = Creative(
        campaign_id=camp.id, filename="kpi_test.jpg", storage_path="/tmp/kpi.jpg",
        format="jpg", file_size_bytes=1000, phash=random.randint(10**9, 10**12),
        fatigue_status="insufficient_data"
    )
    db_session.add(c)
    await db_session.flush()

    today = date.today()
    for i, (imp, cl) in enumerate([(1000, 30), (2000, 60), (1500, 45)]):
        db_session.add(CreativeMetric(
            creative_id=c.id,
            date=today - timedelta(days=2 - i),
            impressions=imp, clicks=cl, installs=cl // 10,
            spend=Decimal("50.00"), revenue=Decimal("100.00")
        ))
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest.mark.asyncio
async def test_kpi_correct_totals(db_session, creative_with_metrics):
    agg = KPIAggregator(db_session)
    summary = await agg.get_kpi_summary(creative_with_metrics.id)
    assert summary is not None
    assert summary.total_impressions == 4500
    assert summary.total_clicks == 135
    assert summary.total_installs == 13  # 3+6+4
    assert abs(summary.total_spend - 150.0) < 0.01
    assert abs(summary.total_revenue - 300.0) < 0.01


@pytest.mark.asyncio
async def test_ctr_computed_correctly(db_session, creative_with_metrics):
    agg = KPIAggregator(db_session)
    summary = await agg.get_kpi_summary(creative_with_metrics.id)
    assert summary.ctr is not None
    assert abs(summary.ctr - 0.03) < 0.001


@pytest.mark.asyncio
async def test_ctr_is_none_when_zero_impressions(db_session):
    camp = Campaign(name="Zero Camp", platform_tags=[])
    db_session.add(camp)
    await db_session.flush()
    c = Creative(
        campaign_id=camp.id, filename="zero.jpg", storage_path="/tmp/zero.jpg",
        format="jpg", file_size_bytes=1000, phash=random.randint(10**9, 10**12),
        fatigue_status="insufficient_data"
    )
    db_session.add(c)
    await db_session.flush()
    db_session.add(CreativeMetric(
        creative_id=c.id, date=date.today(),
        impressions=0, clicks=0, installs=0,
        spend=Decimal("0"), revenue=Decimal("0")
    ))
    await db_session.commit()

    agg = KPIAggregator(db_session)
    summary = await agg.get_kpi_summary(c.id)
    assert summary.ctr is None


@pytest.mark.asyncio
async def test_returns_none_for_unknown_creative(db_session):
    agg = KPIAggregator(db_session)
    summary = await agg.get_kpi_summary(99999)
    assert summary is None


@pytest.mark.asyncio
async def test_daily_trend_has_correct_length(db_session, creative_with_metrics):
    agg = KPIAggregator(db_session)
    summary = await agg.get_kpi_summary(creative_with_metrics.id, days=30)
    assert len(summary.daily_trend) == 3
