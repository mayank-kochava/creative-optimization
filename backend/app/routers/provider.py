from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.provider_state import PROVIDERS, get_active_name, set_active

router = APIRouter()


class ProviderStatus(BaseModel):
    active: str
    available: list[str]


class SetProviderRequest(BaseModel):
    provider: str


@router.get("/provider", response_model=ProviderStatus)
async def get_provider():
    return ProviderStatus(active=get_active_name(), available=list(PROVIDERS))


@router.post("/provider", response_model=ProviderStatus)
async def set_provider(body: SetProviderRequest):
    try:
        set_active(body.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ProviderStatus(active=get_active_name(), available=list(PROVIDERS))
