# Task 12: Fatigue Detector

**Files to create:**
- `backend/app/services/fatigue_detector.py`
- `backend/tests/test_fatigue_detector.py`

**Prereq:** Tasks 02 + 03 complete (models + migration running).

---

## Step 1: Write failing tests

```python
# backend/tests/test_fatigue_detector.py
import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.fatigue_detector import FatigueDetector
from app.models.creative import Creative
from app.models.metric import CreativeMetric


@pytest.fixture
async def creative(db_session):
    c = Creative(
        campaign_id=1, filename="test.jpg", storage_path="/tmp/test.jpg",
        format="jpg", file_size_bytes=1000, phash=999999,
        fatigue_status="insufficient_data"
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


async def insert_metrics(db, creative_id: int, days: int, impressions_per_day: int,
                         base_ctr: float, decline_per_day: float = 0.0):
    """Insert `days` days of metrics ending today."""
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
    await db.commit()


@pytest.mark.asyncio
async def test_insufficient_data_less_than_7_days(db_session, creative):
    await insert_metrics(db_session, creative.id, days=5, impressions_per_day=10000, base_ctr=0.02)
    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "insufficient_data"


@pytest.mark.asyncio
async def test_healthy_when_ctr_stable(db_session, creative):
    # 14 days, no decline
    await insert_metrics(db_session, creative.id, days=14, impressions_per_day=10000, base_ctr=0.02, decline_per_day=0)
    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "healthy"


@pytest.mark.asyncio
async def test_fatiguing_when_wow_decline_25pct(db_session, creative):
    # last_week CTR ~2%, this_week CTR ~1.5% → 25% decline
    today = date.today()
    # last week (days 8-14 ago): CTR = 2%
    for i in range(7):
        day = today - timedelta(days=14 - i)
        m = CreativeMetric(creative_id=creative.id, date=day,
                           impressions=10000, clicks=200, installs=0, spend=0, revenue=0)
        db_session.add(m)
    # this week (days 1-7 ago): CTR = 1.5%
    for i in range(7):
        day = today - timedelta(days=7 - i)
        m = CreativeMetric(creative_id=creative.id, date=day,
                           impressions=10000, clicks=150, installs=0, spend=0, revenue=0)
        db_session.add(m)
    await db_session.commit()

    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "fatiguing"


@pytest.mark.asyncio
async def test_exact_20pct_decline_is_fatiguing(db_session, creative):
    today = date.today()
    # last week CTR = 2.5% (250 clicks)
    for i in range(7):
        day = today - timedelta(days=14 - i)
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=10000, clicks=250, installs=0, spend=0, revenue=0))
    # this week CTR = 2.0% (200 clicks) — exactly 20% decline
    for i in range(7):
        day = today - timedelta(days=7 - i)
        db_session.add(CreativeMetric(creative_id=creative.id, date=day,
                                      impressions=10000, clicks=200, installs=0, spend=0, revenue=0))
    await db_session.commit()

    detector = FatigueDetector(db_session)
    status = await detector.compute_fatigue_status(creative.id)
    assert status == "fatiguing"


@pytest.mark.asyncio
async def test_zero_impressions_days_skipped(db_session, creative):
    today = date.today()
    # Mix of zero-impression days and real days
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
    await db_session.commit()

    detector = FatigueDetector(db_session)
    # Should not raise ZeroDivisionError
    status = await detector.compute_fatigue_status(creative.id)
    assert status in ("healthy", "fatiguing", "insufficient_data")
```

Run: `cd backend && pytest tests/test_fatigue_detector.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/fatigue_detector.py`

```python
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import CreativeMetric


class FatigueDetector:
    FATIGUE_THRESHOLD = 0.20  # 20% WoW CTR decline
    MIN_DAYS_REQUIRED = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_fatigue_status(self, creative_id: int) -> str:
        """
        Returns 'healthy', 'fatiguing', or 'insufficient_data'.
        Requires 7+ days of data. Computes WoW CTR decline over two 7-day windows.
        """
        today = date.today()
        since = today - timedelta(days=14)

        result = await self.db.execute(
            select(CreativeMetric)
            .where(
                CreativeMetric.creative_id == creative_id,
                CreativeMetric.date >= since,
                CreativeMetric.date <= today,
            )
            .order_by(CreativeMetric.date.asc())
        )
        metrics = result.scalars().all()

        if len(metrics) < self.MIN_DAYS_REQUIRED:
            return "insufficient_data"

        # Split: this_week = last 7, last_week = 8-14 days ago
        cutoff = today - timedelta(days=7)
        this_week = [m for m in metrics if m.date > cutoff]
        last_week = [m for m in metrics if m.date <= cutoff]

        if len(this_week) < 3 or len(last_week) < 3:
            return "insufficient_data"

        avg_ctr_this = self._avg_ctr(this_week)
        avg_ctr_last = self._avg_ctr(last_week)

        if avg_ctr_last is None or avg_ctr_last == 0:
            return "insufficient_data"

        wow_decline = (avg_ctr_last - avg_ctr_this) / avg_ctr_last

        return "fatiguing" if wow_decline >= self.FATIGUE_THRESHOLD else "healthy"

    def _avg_ctr(self, metrics: list[CreativeMetric]) -> float | None:
        """Compute CTR = total_clicks / total_impressions, skipping zero-impression days."""
        valid = [m for m in metrics if m.impressions > 0]
        if not valid:
            return None
        total_impressions = sum(m.impressions for m in valid)
        total_clicks = sum(m.clicks for m in valid)
        return total_clicks / total_impressions
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_fatigue_detector.py -v
```

Expected: all 5 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/fatigue_detector.py backend/tests/test_fatigue_detector.py
git commit -m "feat: fatigue detector — WoW CTR decline with 14-day window, handles sparse data"
```
