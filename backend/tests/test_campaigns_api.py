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
    assert isinstance(resp.json(), list)


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
