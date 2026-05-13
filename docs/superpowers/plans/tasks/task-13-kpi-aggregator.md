# Task 13: KPI Aggregator

**Files to create:**
- `backend/app/services/kpi_aggregator.py`
- `backend/tests/test_kpi_aggregator.py`

**Prereq:** Tasks 02 + 03 complete.

---

## Step 1: Write failing tests

```python
# backend/tests/test_kpi_aggregator.py
import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.services.kpi_aggregator import KPIAggregator
from app.models.metric import CreativeMetric
from app.models.creative import Creative


@pytest.fixture
async def creative_with_metrics(db_session):
    c = Creative(
        campaign_id=1, filename="kpi_test.jpg", storage_path="/tmp/kpi.jpg",
        format="jpg", file_size_bytes=1000, phash=777777,
        fatigue_status="insufficient_data"
    )
    db_session.add(c)
    await db_session.flush()

    today = date.today()
    # 3 days: impressions [1000, 2000, 1500], clicks [30, 60, 45]
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
    # CTR = 135 / 4500 = 0.03
    assert summary.ctr is not None
    assert abs(summary.ctr - 0.03) < 0.001


@pytest.mark.asyncio
async def test_ctr_is_none_when_zero_impressions(db_session):
    c = Creative(
        campaign_id=1, filename="zero.jpg", storage_path="/tmp/zero.jpg",
        format="jpg", file_size_bytes=1000, phash=666666,
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
    assert len(summary.daily_trend) == 3  # only 3 days have data
```

Run: `cd backend && pytest tests/test_kpi_aggregator.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/kpi_aggregator.py`

```python
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import CreativeMetric


@dataclass
class DailyKPI:
    date: date
    impressions: int
    clicks: int
    installs: int
    spend: float
    ctr: float | None


@dataclass
class KPISummary:
    total_impressions: int
    total_clicks: int
    total_installs: int
    total_spend: float
    total_revenue: float
    ctr: float | None
    cvr: float | None
    cpi: float | None
    roas: float | None
    daily_trend: list[DailyKPI] = field(default_factory=list)


class KPIAggregator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_kpi_summary(self, creative_id: int, days: int = 30) -> KPISummary | None:
        since = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(CreativeMetric)
            .where(
                CreativeMetric.creative_id == creative_id,
                CreativeMetric.date >= since,
            )
            .order_by(CreativeMetric.date.asc())
        )
        metrics = result.scalars().all()

        if not metrics:
            return None

        total_impressions = sum(m.impressions for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_installs = sum(m.installs for m in metrics)
        total_spend = float(sum(Decimal(str(m.spend)) for m in metrics))
        total_revenue = float(sum(Decimal(str(m.revenue)) for m in metrics))

        ctr = total_clicks / total_impressions if total_impressions > 0 else None
        cvr = total_installs / total_clicks if total_clicks > 0 else None
        cpi = total_spend / total_installs if total_installs > 0 else None
        roas = total_revenue / total_spend if total_spend > 0 else None

        daily_trend = [
            DailyKPI(
                date=m.date,
                impressions=m.impressions,
                clicks=m.clicks,
                installs=m.installs,
                spend=float(m.spend),
                ctr=m.clicks / m.impressions if m.impressions > 0 else None,
            )
            for m in metrics
        ]

        return KPISummary(
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_installs=total_installs,
            total_spend=total_spend,
            total_revenue=total_revenue,
            ctr=ctr,
            cvr=cvr,
            cpi=cpi,
            roas=roas,
            daily_trend=daily_trend,
        )
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_kpi_aggregator.py -v
```

Expected: all 5 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/kpi_aggregator.py backend/tests/test_kpi_aggregator.py
git commit -m "feat: KPI aggregator — CTR/CVR/CPI/ROAS with None for zero denominators"
```
