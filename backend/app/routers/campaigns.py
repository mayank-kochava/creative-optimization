from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair
from app.models.metric import CreativeMetric
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.creative import CreativeSummary

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def _campaign_response(campaign: Campaign, db: AsyncSession) -> CampaignResponse:
    count = await db.scalar(
        select(func.count(Creative.id)).where(Creative.campaign_id == campaign.id)
    )
    fatiguing = await db.scalar(
        select(func.count(Creative.id)).where(
            Creative.campaign_id == campaign.id,
            Creative.fatigue_status == "fatiguing",
        )
    )
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        platform_tags=campaign.platform_tags or [],
        creative_count=count or 0,
        fatiguing_count=fatiguing or 0,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    return [await _campaign_response(c, db) for c in campaigns]


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(name=payload.name, platform_tags=payload.platform_tags)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return await _campaign_response(campaign, db)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await _campaign_response(campaign, db)


@router.get("/{campaign_id}/creatives", response_model=list[CreativeSummary])
async def list_campaign_creatives(
    campaign_id: int, skip: int = 0, limit: int = 200, db: AsyncSession = Depends(get_db)
):
    # Fetch campaign for platform_tags
    camp_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = camp_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    platform_tags = campaign.platform_tags or []

    result = await db.execute(
        select(Creative)
        .where(Creative.campaign_id == campaign_id)
        .options(selectinload(Creative.analysis))
        .offset(skip)
        .limit(limit)
        .order_by(Creative.created_at.desc())
    )
    creatives = result.scalars().all()

    creative_ids = [c.id for c in creatives]

    dup_result = await db.execute(
        select(DuplicatePair.creative_id_a, DuplicatePair.creative_id_b).where(
            or_(
                DuplicatePair.creative_id_a.in_(creative_ids),
                DuplicatePair.creative_id_b.in_(creative_ids),
            )
        )
    )
    dup_ids: set[int] = set()
    for row in dup_result.all():
        dup_ids.add(row.creative_id_a)
        dup_ids.add(row.creative_id_b)

    # --- Metric aggregation (all-time, last 7 days, prior 7 days) ---
    today = date.today()
    last7_start = today - timedelta(days=7)
    prior7_start = today - timedelta(days=14)

    # All-time: impressions, clicks, spend, installs, first/last date
    alltime_result = await db.execute(
        select(
            CreativeMetric.creative_id,
            func.sum(CreativeMetric.impressions).label("impressions"),
            func.sum(CreativeMetric.clicks).label("clicks"),
            func.sum(CreativeMetric.installs).label("installs"),
            func.sum(CreativeMetric.spend).label("spend"),
            func.min(CreativeMetric.date).label("first_date"),
            func.max(CreativeMetric.date).label("last_date"),
        )
        .where(CreativeMetric.creative_id.in_(creative_ids))
        .group_by(CreativeMetric.creative_id)
    )
    alltime: dict[int, dict] = {}
    for row in alltime_result.all():
        alltime[row.creative_id] = {
            "impressions": row.impressions or 0,
            "clicks": row.clicks or 0,
            "installs": row.installs or 0,
            "spend": float(row.spend or 0),
            "first_date": row.first_date,
            "last_date": row.last_date,
        }

    # Last 7 days CTR
    last7_result = await db.execute(
        select(
            CreativeMetric.creative_id,
            func.sum(CreativeMetric.impressions).label("impressions"),
            func.sum(CreativeMetric.clicks).label("clicks"),
        )
        .where(
            CreativeMetric.creative_id.in_(creative_ids),
            CreativeMetric.date >= last7_start,
        )
        .group_by(CreativeMetric.creative_id)
    )
    last7: dict[int, dict] = {}
    for row in last7_result.all():
        last7[row.creative_id] = {
            "impressions": row.impressions or 0,
            "clicks": row.clicks or 0,
        }

    # Prior 7 days CTR
    prior7_result = await db.execute(
        select(
            CreativeMetric.creative_id,
            func.sum(CreativeMetric.impressions).label("impressions"),
            func.sum(CreativeMetric.clicks).label("clicks"),
        )
        .where(
            CreativeMetric.creative_id.in_(creative_ids),
            CreativeMetric.date >= prior7_start,
            CreativeMetric.date < last7_start,
        )
        .group_by(CreativeMetric.creative_id)
    )
    prior7: dict[int, dict] = {}
    for row in prior7_result.all():
        prior7[row.creative_id] = {
            "impressions": row.impressions or 0,
            "clicks": row.clicks or 0,
        }

    def _ctr(imp: int, clicks: int) -> float | None:
        return round(clicks / imp * 100, 2) if imp > 0 else None

    def _ipm(imp: int, installs: int) -> float | None:
        return round(installs / imp * 1000, 2) if imp > 0 else None

    def _wow_delta(ctr_last: float | None, ctr_prior: float | None) -> float | None:
        if ctr_last is None or ctr_prior is None or ctr_prior == 0:
            return None
        return round((ctr_last - ctr_prior) / ctr_prior * 100, 1)

    summaries = []
    for c in creatives:
        at = alltime.get(c.id, {})
        l7 = last7.get(c.id, {})
        p7 = prior7.get(c.id, {})

        imp_at = at.get("impressions", 0)
        ctr_at = _ctr(imp_at, at.get("clicks", 0))
        ipm_at = _ipm(imp_at, at.get("installs", 0))
        ctr_l7 = _ctr(l7.get("impressions", 0), l7.get("clicks", 0))
        ctr_p7 = _ctr(p7.get("impressions", 0), p7.get("clicks", 0))

        first_date = at.get("first_date")
        last_date = at.get("last_date")
        days_active = (last_date - first_date).days + 1 if first_date and last_date else None

        summaries.append(CreativeSummary(
            id=c.id,
            filename=c.filename,
            format=c.format,
            width=c.width,
            height=c.height,
            duration_seconds=c.duration_seconds,
            fatigue_status=c.fatigue_status,
            overall_score=c.analysis.overall_score if c.analysis else None,
            has_duplicate=c.id in dup_ids,
            created_at=c.created_at,
            ctr=ctr_at,
            ipm=ipm_at,
            cost_total=at.get("spend") if at else None,
            ctr_delta_wow=_wow_delta(ctr_l7, ctr_p7),
            days_active=days_active,
            platform_tags=platform_tags,
            search_tags=c.analysis.search_tags if c.analysis else [],
        ))

    return summaries
