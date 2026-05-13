# Task 18: Integration Tests

**Files to create:**
- `backend/tests/test_integration.py`

**Prereq:** Tasks 16 + 17 complete. Test DB running.

---

## Step 1: Create `backend/tests/test_integration.py`

```python
"""
End-to-end integration tests.
Requires: PostgreSQL running at localhost:5432, creative_opt_test DB exists.
Ollama calls are mocked via respx.
"""
import asyncio
import io
import json
import pytest
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from PIL import Image, ImageDraw
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


def make_test_image_bytes() -> bytes:
    """Create a 300x250 image with text and return JPEG bytes."""
    img = Image.new("RGB", (300, 250), color="steelblue")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 290, 240], outline="white", width=2)
    draw.text((80, 120), "GET STARTED", fill="white")
    draw.text((100, 210), "DOWNLOAD NOW", fill="yellow")
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
    """
    1. Create campaign
    2. Upload image (mock Ollama analysis)
    3. Wait for background analysis
    4. GET creative detail → verify analysis + annotations present
    """
    # 1. Create campaign
    camp_resp = await client.post("/campaigns", json={"name": "Integration Test Campaign"})
    assert camp_resp.status_code == 201
    campaign_id = camp_resp.json()["id"]

    # 2. Upload image with mocked Ollama
    img_bytes = make_test_image_bytes()
    with respx.mock(assert_all_called=False):
        # Mock Ollama analysis call
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": json.dumps(MOCK_ANALYSIS)})
        )
        # Mock content classifier (returns YES)
        upload_resp = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("test_creative.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )

    assert upload_resp.status_code == 201
    creative_id = upload_resp.json()["creative_id"]
    assert creative_id > 0
    assert upload_resp.json()["duplicate_detected"] is False

    # 3. Wait up to 5s for background analysis to complete
    detail = None
    for _ in range(10):
        detail_resp = await client.get(f"/creatives/{creative_id}")
        assert detail_resp.status_code == 200
        if detail_resp.json().get("analysis"):
            detail = detail_resp.json()
            break
        await asyncio.sleep(0.5)

    # 4. Verify detail
    assert detail is not None, "Analysis did not complete within 5 seconds"
    assert detail["analysis"]["overall_score"] >= 0
    assert len(detail["analysis"]["recommendations"]) == 3
    assert detail["kpi"] is None  # no metrics yet for new creative


@pytest.mark.asyncio
async def test_duplicate_detection_full_flow(client, db_session):
    """Upload same image twice → second returns duplicate_detected=True."""
    # Create campaign
    camp_resp = await client.post("/campaigns", json={"name": "Duplicate Test Campaign"})
    campaign_id = camp_resp.json()["id"]

    img_bytes = make_test_image_bytes()

    with respx.mock(assert_all_called=False):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": json.dumps(MOCK_ANALYSIS)})
        )

        # First upload — unique
        resp1 = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("creative_a.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )
        assert resp1.status_code == 201
        assert resp1.json()["duplicate_detected"] is False

        # Second upload — same image → duplicate
        resp2 = await client.post(
            f"/campaigns/{campaign_id}/creatives",
            files={"file": ("creative_b.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        )
        assert resp2.status_code == 201
        assert resp2.json()["duplicate_detected"] is True
        assert resp2.json()["hamming_distance"] == 0
        assert resp2.json()["duplicate_type"] == "self"


@pytest.mark.asyncio
async def test_campaign_creative_count_updates(client, db_session):
    """Campaign creative_count should increment after upload."""
    camp_resp = await client.post("/campaigns", json={"name": "Count Test Campaign"})
    campaign_id = camp_resp.json()["id"]
    assert camp_resp.json()["creative_count"] == 0

    img_bytes = make_test_image_bytes()
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
    """PDF upload should return 415."""
    camp_resp = await client.post("/campaigns", json={"name": "Format Test"})
    campaign_id = camp_resp.json()["id"]

    resp = await client.post(
        f"/campaigns/{campaign_id}/creatives",
        files={"file": ("document.pdf", io.BytesIO(b"fake pdf"), "application/pdf")}
    )
    assert resp.status_code == 415
```

---

## Step 2: Run integration tests

```bash
cd backend && pytest tests/test_integration.py -v -s
```

Expected: all 4 tests PASS.

---

## Step 3: Run complete test suite

```bash
cd backend && pytest -v --tb=short
```

Expected: all tests PASS with 0 failures.

---

## Step 4: Commit

```bash
git add backend/tests/test_integration.py
git commit -m "test: E2E integration tests — upload flow, duplicate detection, campaign count"
```
