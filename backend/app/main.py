import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from app.config import settings
from app.routers import health, campaigns, creatives
from app.routers.provider import router as provider_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only prewarm Ollama if it's the active provider
    from app.services.provider_state import get_active_name
    if get_active_name() == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": "qwen2.5vl:7b", "prompt": "hi", "stream": False},
                    timeout=30,
                )
        except Exception:
            pass
    yield


app = FastAPI(title="Creative Intelligence Platform", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(creatives.router)
app.include_router(provider_router)
