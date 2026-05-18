import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    ollama_status = "ok"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
            ollama_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unavailable"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "ollama": ollama_status}
