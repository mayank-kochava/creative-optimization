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
            ctr=ctr, cvr=cvr, cpi=cpi, roas=roas,
            daily_trend=daily_trend,
        )
