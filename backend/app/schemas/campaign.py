from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    platform_tags: list[str] = []


class CampaignResponse(BaseModel):
    id: int
    name: str
    platform_tags: list[str]
    creative_count: int = 0
    fatiguing_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
