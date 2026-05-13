"""Seed demo data: 10 campaigns, 50 creatives, 30-day KPIs, fatigue examples, duplicates."""
import asyncio
import ctypes
import os
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

import asyncpg
from PIL import Image, ImageDraw

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


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def generate_creative_image(output_path: Path, campaign_name: str, index: int) -> tuple[int, int]:
    import numpy as np
    sizes = [(300, 250), (728, 90), (160, 600), (320, 50), (300, 600)]
    width, height = sizes[index % len(sizes)]
    rgb = hex_to_rgb(COLORS[index % len(COLORS)])
    rng = np.random.RandomState(seed=index * 31337)
    # Add per-pixel noise so each image has a unique pHash
    base = np.full((height, width, 3), rgb, dtype=np.uint8)
    noise = rng.randint(-30, 30, (height, width, 3), dtype=np.int16)
    pixels = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(pixels)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, width - 10, height - 10], outline="white", width=2)
    draw.text((15, max(10, height // 2 - 20)), f"[{index:02d}] {campaign_name[:16]}", fill="white")
    draw.text((15, max(20, height - 30)), "DOWNLOAD NOW", fill="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="JPEG")
    return width, height


def compute_phash_signed(image_path: Path, index: int) -> int:
    import hashlib
    # Combine file content hash with index to guarantee uniqueness in seed data
    content = image_path.read_bytes()
    raw = int(hashlib.sha256(content + str(index).encode()).hexdigest()[:16], 16)
    return ctypes.c_int64(raw).value


def generate_kpi_row(creative_id: int, day_offset: int, base_ctr: float, trend: str) -> dict:
    factor = 1.0
    if trend == "fatiguing":
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

    await conn.execute(
        "TRUNCATE duplicate_pairs, creative_metrics, creative_annotations, "
        "creative_analyses, creatives, campaigns RESTART IDENTITY CASCADE"
    )

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
    creatives_per_campaign = 50 // len(CAMPAIGNS)

    for i, campaign_id in enumerate(campaign_ids):
        campaign_name = CAMPAIGNS[i][0]
        for j in range(creatives_per_campaign):
            idx = i * creatives_per_campaign + j
            filename = f"creative_{uuid.uuid4().hex[:8]}.jpg"
            storage_path = storage_base / str(campaign_id) / filename
            width, height = generate_creative_image(storage_path, campaign_name, idx)
            file_size = storage_path.stat().st_size
            phash = compute_phash_signed(storage_path, idx)

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

    if len(creative_ids) >= 8:
        await conn.execute(
            """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
               VALUES ($1, $2, 0, 'self') ON CONFLICT DO NOTHING""",
            creative_ids[0], creative_ids[1]
        )
        await conn.execute(
            """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
               VALUES ($1, $2, 3, 'cross_platform') ON CONFLICT DO NOTHING""",
            creative_ids[2], creative_ids[7]
        )
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
