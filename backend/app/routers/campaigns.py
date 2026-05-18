from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.campaign import Campaign
from app.models.creative import Creative
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
    campaign_id: int, skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Creative)
        .where(Creative.campaign_id == campaign_id)
        .offset(skip)
        .limit(limit)
        .order_by(Creative.created_at.desc())
    )
    creatives = result.scalars().all()
    return [
        CreativeSummary(
            id=c.id,
            filename=c.filename,
            format=c.format,
            width=c.width,
            height=c.height,
            fatigue_status=c.fatigue_status,
            created_at=c.created_at,
        )
        for c in creatives
    ]
