from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import CreativeMetric


class FatigueDetector:
    FATIGUE_THRESHOLD = 0.20
    MIN_DAYS_REQUIRED = 7

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_fatigue_status(self, creative_id: int) -> str:
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

        cutoff = today - timedelta(days=7)
        this_week = [m for m in metrics if m.date >= cutoff]
        last_week = [m for m in metrics if m.date < cutoff]

        if len(this_week) < 3 or len(last_week) < 3:
            return "insufficient_data"

        avg_ctr_this = self._avg_ctr(this_week)
        avg_ctr_last = self._avg_ctr(last_week)

        if avg_ctr_last is None or avg_ctr_last == 0:
            return "insufficient_data"

        wow_decline = (avg_ctr_last - avg_ctr_this) / avg_ctr_last
        return "fatiguing" if wow_decline >= self.FATIGUE_THRESHOLD else "healthy"

    def _avg_ctr(self, metrics: list[CreativeMetric]) -> float | None:
        valid = [m for m in metrics if m.impressions > 0]
        if not valid:
            return None
        return sum(m.clicks for m in valid) / sum(m.impressions for m in valid)
