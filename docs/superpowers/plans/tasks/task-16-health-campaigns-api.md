# Task 16: Health + Campaign API Endpoints

**Files to create:**
- `backend/app/routers/health.py`
- `backend/app/routers/campaigns.py`
- `backend/app/routers/__init__.py`
- `backend/tests/test_campaigns_api.py`

**Prereq:** Tasks 02, 03, 06 complete.

---

## Step 1: Write failing tests

```python
# backend/tests/test_campaigns_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db


@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_create_campaign(client):
    resp = await client.post("/campaigns", json={"name": "My Campaign", "platform_tags": ["facebook"]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Campaign"
    assert data["platform_tags"] == ["facebook"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_campaign_empty_name_422(client):
    resp = await client.post("/campaigns", json={"name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_campaigns_empty(client):
    resp = await client.get("/campaigns")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_campaigns_after_create(client):
    await client.post("/campaigns", json={"name": "Camp A"})
    await client.post("/campaigns", json={"name": "Camp B"})
    resp = await client.get("/campaigns")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_campaign_by_id(client):
    create_resp = await client.post("/campaigns", json={"name": "Specific Campaign"})
    campaign_id = create_resp.json()["id"]
    resp = await client.get(f"/campaigns/{campaign_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Specific Campaign"


@pytest.mark.asyncio
async def test_get_campaign_not_found(client):
    resp = await client.get("/campaigns/99999")
    assert resp.status_code == 404
```

Run: `cd backend && pytest tests/test_campaigns_api.py -v`
Expected: FAIL — routers not found.

---

## Step 2: Create `backend/app/routers/health.py`

```python
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    # Check DB
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Ollama
    ollama_status = "ok"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=3)
            ollama_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unavailable"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "ollama": ollama_status}
```

---

## Step 3: Create `backend/app/routers/campaigns.py`

```python
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
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        platform_tags=campaign.platform_tags or [],
        creative_count=count or 0,
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
            id=c.id, filename=c.filename, format=c.format,
            width=c.width, height=c.height, fatigue_status=c.fatigue_status,
            created_at=c.created_at,
        )
        for c in creatives
    ]
```

---

## Step 4: Create `backend/app/routers/__init__.py`

```python
from app.routers import health, campaigns, creatives
```

---

## Step 5: Create stub `backend/app/routers/creatives.py` (full impl in Task 17)

```python
from fastapi import APIRouter
router = APIRouter(prefix="/creatives", tags=["creatives"])
```

---

## Step 6: Add db_session fixture to conftest.py

```python
# Add to backend/tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

TEST_DATABASE_URL = "postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt_test"

@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        from app.database import Base
        import app.models  # noqa
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

---

## Step 7: Run tests

```bash
# Ensure test DB exists first:
psql -U appuser -c "CREATE DATABASE creative_opt_test;" 2>/dev/null || true
cd backend && pytest tests/test_campaigns_api.py -v
```

Expected: all 7 tests PASS.

---

## Step 8: Commit

```bash
git add backend/app/routers/ backend/tests/test_campaigns_api.py backend/tests/conftest.py
git commit -m "feat: campaign API endpoints — CRUD with creative_count, health check"
```
