# Task 04: Seed Data Script

**Files to create:**
- `backend/scripts/seed_data.py`
- `backend/tests/test_seed.py`

**Prereq:** Task 03 complete (migration runs, tables exist).

---

## Step 1: Write failing test

```python
# backend/tests/test_seed.py
import pytest
import asyncpg
import subprocess
import os


@pytest.mark.asyncio
async def test_seed_creates_campaigns_and_creatives():
    result = subprocess.run(
        ["python", "scripts/seed_data.py"],
        cwd="backend",
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    conn = await asyncpg.connect("postgresql://appuser:apppassword@localhost:5432/creative_opt")
    campaign_count = await conn.fetchval("SELECT COUNT(*) FROM campaigns")
    creative_count = await conn.fetchval("SELECT COUNT(*) FROM creatives")
    metric_count = await conn.fetchval("SELECT COUNT(*) FROM creative_metrics")
    fatiguing_count = await conn.fetchval(
        "SELECT COUNT(*) FROM creatives WHERE fatigue_status='fatiguing'"
    )
    duplicate_count = await conn.fetchval("SELECT COUNT(*) FROM duplicate_pairs")
    await conn.close()

    assert campaign_count == 10
    assert creative_count == 50
    assert metric_count >= 50 * 14  # at least 14 days per creative
    assert fatiguing_count >= 3
    assert duplicate_count >= 2
```

Run: `cd backend && pytest tests/test_seed.py -v`
Expected: FAIL — `seed_data.py` not found.

---

## Step 2: Create `backend/scripts/seed_data.py`

```python
"""Seed demo data: 10 campaigns, 50 creatives, 30-day KPIs, fatigue examples, duplicates."""
import asyncio
import os
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

import asyncpg
from PIL import Image, ImageDraw, ImageFont

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://appuser:apppassword@localhost:5432/creative_opt"
)

CAMPAIGNS = [
    ("Summer Fitness App 2024", ["facebook", "instagram"]),
    ("Gaming App Launch Q3", ["google", "tiktok"]),
    ("Travel Booking Promo", ["facebook", "google"]),
    ("Food Delivery Rush", ["instagram", "tiktok"]),
    ("Finance App - Save Smart", ["facebook", "linkedin"]),
    ("EdTech Back to School", ["google", "facebook"]),
    ("Beauty Brand Spring", ["instagram", "pinterest"]),
    ("E-commerce Flash Sale", ["facebook", "google", "tiktok"]),
    ("Ride Share Launch City", ["google", "instagram"]),
    ("Streaming App Premium", ["facebook", "google"]),
]

FORMATS = ["jpg", "png", "webp"]
COLORS = [
    "#FF5733", "#33FF57", "#3357FF", "#FF33A8", "#33FFF5",
    "#FFD133", "#8C33FF", "#FF8C33", "#33FF8C", "#FF3333",
]


def generate_creative_image(output_path: Path, campaign_name: str, index: int) -> tuple[int, int]:
    """Generate a placeholder ad creative image with campaign name and index."""
    width, height = random.choice([(300, 250), (728, 90), (160, 600), (320, 50), (300, 600)])
    img = Image.new("RGB", (width, height), color=COLORS[index % len(COLORS)])
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, width - 10, height - 10], outline="white", width=2)
    draw.text((15, height // 2 - 20), campaign_name[:20], fill="white")
    draw.text((15, height - 30), "DOWNLOAD NOW", fill="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="JPEG")
    return width, height


def compute_phash(image_path: Path) -> int:
    """Compute 64-bit pHash as integer."""
    import imagehash
    from PIL import Image as PILImage
    h = imagehash.phash(PILImage.open(str(image_path)), hash_size=8)
    return int(str(h), 16)


def generate_kpi_row(creative_id: int, day_offset: int, base_ctr: float, trend: str) -> dict:
    """Generate one day of KPI metrics with realistic noise."""
    factor = 1.0
    if trend == "fatiguing":
        # Decline 3% per day — after 14 days = ~34% total decline
        factor = max(0.3, 1.0 - 0.03 * day_offset)
    elif trend == "healthy":
        factor = 1.0 + random.gauss(0, 0.05)

    impressions = max(1000, int(random.gauss(50000, 10000)))
    ctr = max(0.005, base_ctr * factor + random.gauss(0, 0.002))
    clicks = min(impressions, max(0, int(impressions * ctr)))
    cvr = random.uniform(0.02, 0.08)
    installs = min(clicks, max(0, int(clicks * cvr)))
    spend = round(impressions * random.uniform(0.001, 0.005), 4)
    revenue = round(installs * random.uniform(1.5, 4.0), 4)
    metric_date = date.today() - timedelta(days=29 - day_offset)
    return {
        "creative_id": creative_id,
        "date": metric_date,
        "impressions": impressions,
        "clicks": clicks,
        "installs": installs,
        "spend": spend,
        "revenue": revenue,
    }


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    # Clear existing seed data
    await conn.execute("TRUNCATE duplicate_pairs, creative_metrics, creative_annotations, creative_analyses, creatives, campaigns RESTART IDENTITY CASCADE")

    storage_base = Path(os.environ.get("STORAGE_PATH", "/tmp/uploads"))

    campaign_ids = []
    for name, tags in CAMPAIGNS:
        cid = await conn.fetchval(
            "INSERT INTO campaigns (name, platform_tags) VALUES ($1, $2) RETURNING id",
            name, tags
        )
        campaign_ids.append(cid)
    print(f"Created {len(campaign_ids)} campaigns")

    creative_ids = []
    creative_phashes = []
    fatiguing_assigned = 0
    creatives_per_campaign = 50 // len(CAMPAIGNS)  # 5 each

    for i, campaign_id in enumerate(campaign_ids):
        campaign_name = CAMPAIGNS[i][0]
        for j in range(creatives_per_campaign):
            idx = i * creatives_per_campaign + j
            filename = f"creative_{uuid.uuid4().hex[:8]}.jpg"
            storage_path = storage_base / str(campaign_id) / filename
            width, height = generate_creative_image(storage_path, campaign_name, idx)
            file_size = storage_path.stat().st_size
            phash = compute_phash(storage_path)

            # Determine trend: first 3 creatives across all campaigns are fatiguing
            trend = "fatiguing" if fatiguing_assigned < 3 and j == 0 else "healthy"
            fatigue_status = "fatiguing" if trend == "fatiguing" else "insufficient_data"
            if trend == "fatiguing":
                fatiguing_assigned += 1

            cid = await conn.fetchval(
                """INSERT INTO creatives
                   (campaign_id, filename, storage_path, format, width, height,
                    file_size_bytes, phash, fatigue_status)
                   VALUES ($1, $2, $3, 'jpg', $4, $5, $6, $7, $8) RETURNING id""",
                campaign_id, filename, str(storage_path), width, height,
                file_size, phash, fatigue_status
            )
            creative_ids.append(cid)
            creative_phashes.append((cid, phash, campaign_id, trend))

    print(f"Created {len(creative_ids)} creatives")

    # Insert 30-day KPI metrics
    metric_rows = []
    for cid, phash, camp_id, trend in creative_phashes:
        base_ctr = random.uniform(0.015, 0.035)
        for day in range(30):
            metric_rows.append(generate_kpi_row(cid, day, base_ctr, trend))

    await conn.executemany(
        """INSERT INTO creative_metrics (creative_id, date, impressions, clicks, installs, spend, revenue)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           ON CONFLICT (creative_id, date) DO NOTHING""",
        [(r["creative_id"], r["date"], r["impressions"], r["clicks"],
          r["installs"], r["spend"], r["revenue"]) for r in metric_rows]
    )
    print(f"Inserted {len(metric_rows)} metric rows")

    # Create 3 duplicate pairs (modify phash slightly for near-duplicates)
    if len(creative_ids) >= 4:
        # Pair 1: exact duplicate (same phash — use same file, different creative)
        await conn.execute(
            """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
               VALUES ($1, $2, 0, 'self') ON CONFLICT DO NOTHING""",
            creative_ids[0], creative_ids[1]
        )
        # Pair 2: near-duplicate across campaigns
        await conn.execute(
            """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
               VALUES ($1, $2, 3, 'cross_platform') ON CONFLICT DO NOTHING""",
            creative_ids[2], creative_ids[7]
        )
        # Pair 3: self duplicate
        await conn.execute(
            """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
               VALUES ($1, $2, 1, 'self') ON CONFLICT DO NOTHING""",
            creative_ids[4], creative_ids[5]
        )
    print("Created duplicate pairs")

    await conn.close()
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 3: Run seed script

```bash
cd backend
python scripts/seed_data.py
```

Expected output:
```
Created 10 campaigns
Created 50 creatives
Inserted 1500 metric rows
Created duplicate pairs
Seed complete!
```

---

## Step 4: Run tests

```bash
pytest tests/test_seed.py -v
```

Expected: PASS.

---

## Step 5: Verify in DB

```bash
docker exec -it creative-optimization-postgres-1 psql -U appuser -d creative_opt -c "SELECT COUNT(*) FROM creatives; SELECT COUNT(*) FROM creative_metrics; SELECT fatigue_status, COUNT(*) FROM creatives GROUP BY fatigue_status;"
```

Expected: 50 creatives, 1500 metrics, ≥3 fatiguing.

---

## Step 6: Commit

```bash
git add backend/scripts/seed_data.py backend/tests/test_seed.py
git commit -m "feat: seed script — 10 campaigns, 50 creatives, 30-day KPIs with fatigue and duplicates"
```
