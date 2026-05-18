"""
End-to-end integration tests.
Requires: PostgreSQL at localhost:5432, creative_opt_test DB exists.
Ollama calls mocked via respx.
"""
import asyncio
import io
import json
import pytest
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from PIL import Image, ImageDraw
import random
from app.main import app
from app.database import get_db


MOCK_ANALYSIS = {
    "scores": {
        "hook_strength": 8, "cta_clarity": 7, "visual_quality": 9,
        "message_clarity": 7, "emotional_resonance": 8, "social_proof": 4,
        "brand_consistency": 6
    },
    "overall_score": 7,
    "persuasion_strategy": "aspirational",
    "dominant_emotion": "excitement",
    "strengths": ["Strong visual hook", "Clear CTA"],
    "weaknesses": ["Low social proof"],
    "recommendations": ["Add testimonials", "Boost contrast", "Simplify message"],
    "explanation": "This creative uses aspirational imagery effectively."
}


def make_test_image_bytes(seed=1) -> bytes:
    """
    Generate a perceptually distinct image per seed.
    Each seed produces a structurally unique image (different fill patterns,
    shape positions, and content) so phash values differ across test functions.
    """
    rng = random.Random(seed)
    # Vary background color significantly
    bg = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    img = Image.new("RGB", (300, 250), color=bg)
    draw = ImageDraw.Draw(img)

    # Draw seed-unique tiled pattern to maximally differentiate phash
    cell = max(10, seed % 40 + 10)
    for x in range(0, 300, cell):
        for y in range(0, 250, cell):
            c = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
            draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=c)

    # Add seed-specific large shapes at varying positions
    cx = rng.randint(30, 200)
    cy = rng.randint(30, 180)
    r = rng.randint(20, 60)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_full_upload_and_detail_flow(client, db_session):
    # 1. Create campaign
    camp_resp = await client.post("/campaigns", json={"name": "Integration Test Campaign"})
    assert camp_resp.status_code == 201
    campaign_id = camp_resp.json()["id"]

    # 2. Upload image with mocked Ollama
    img_bytes = make_test_image_bytes(seed=10)
    with respx.mock(assert_all_called=False):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": json.dumps(MOCK_ANALYSIS)})
        )
        upload_resp = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("test_creative.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )

    assert upload_resp.status_code == 201
    creative_id = upload_resp.json()["creative_id"]
    assert creative_id > 0
    assert upload_resp.json()["duplicate_detected"] is False

    # 3. GET creative detail — analysis may still be pending (fire-and-forget)
    detail_resp = await client.get(f"/creatives/{creative_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["id"] == creative_id
    # analysis may be None if background task hasn't completed
    assert "analysis" in data
    assert data["kpi"] is None  # no metrics yet


@pytest.mark.asyncio
async def test_duplicate_detection_full_flow(client, db_session):
    camp_resp = await client.post("/campaigns", json={"name": "Duplicate Test Campaign"})
    campaign_id = camp_resp.json()["id"]

    img_bytes = make_test_image_bytes(seed=20)

    with respx.mock(assert_all_called=False):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": json.dumps(MOCK_ANALYSIS)})
        )

        # First upload
        resp1 = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("creative_a.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )
        assert resp1.status_code == 201
        assert resp1.json()["duplicate_detected"] is False

        # Second upload — same bytes → same phash → duplicate
        resp2 = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("creative_b.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )
        assert resp2.status_code == 201
        assert resp2.json()["duplicate_detected"] is True
        assert resp2.json()["hamming_distance"] == 0


@pytest.mark.asyncio
async def test_campaign_creative_count_updates(client, db_session):
    camp_resp = await client.post("/campaigns", json={"name": "Count Test Campaign"})
    campaign_id = camp_resp.json()["id"]
    assert camp_resp.json()["creative_count"] == 0

    img_bytes = make_test_image_bytes(seed=30)
    with respx.mock(assert_all_called=False):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": json.dumps(MOCK_ANALYSIS)})
        )
        await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("c1.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )

    camp_detail = await client.get(f"/campaigns/{campaign_id}")
    assert camp_detail.json()["creative_count"] == 1


@pytest.mark.asyncio
async def test_unsupported_format_rejected(client, db_session):
    camp_resp = await client.post("/campaigns", json={"name": "Format Test"})
    campaign_id = camp_resp.json()["id"]

    resp = await client.post(
        f"/campaigns/{campaign_id}/creatives",
        files={"file": ("document.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
    )
    assert resp.status_code == 415
