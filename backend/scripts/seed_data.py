"""Seed demo data: 10 campaigns, 50 creatives, 30-day KPIs, fatigue examples, duplicates."""
import asyncio
import ctypes
import json
import os
import random
import shutil
import uuid
from datetime import date, timedelta
from pathlib import Path

import asyncpg
from PIL import Image

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://appuser:apppassword@localhost:5432/creative_opt"
)

BENCHMARK_DIR = Path(__file__).parent.parent / "data" / "benchmark" / "images" / "0"

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


def _benchmark_images() -> list[Path]:
    imgs = sorted(BENCHMARK_DIR.glob("*.jpg"))
    if not imgs:
        raise RuntimeError(f"No benchmark images found in {BENCHMARK_DIR}")
    return imgs


def copy_benchmark_image(output_path: Path, index: int) -> tuple[int, int]:
    imgs = _benchmark_images()
    src = imgs[index % len(imgs)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(output_path))
    with Image.open(str(output_path)) as img:
        width, height = img.size
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
            filename = f"creative_{uuid.uuid4().hex[:8]}.jpg"  # .jpg matches benchmark source format
            storage_path = storage_base / str(campaign_id) / filename
            width, height = copy_benchmark_image(storage_path, idx)
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

    # Annotations: face/text/CTA bounding boxes in pixel space
    CTA_LABELS = ["DOWNLOAD NOW", "GET STARTED", "LEARN MORE", "TRY FREE", "SHOP NOW", "INSTALL FREE"]
    TEXT_LABELS = ["Download Now", "Get Started Free", "Limited Time Offer", "Try for Free",
                   "50% OFF Today", "Join 1M+ Users", "See How It Works"]
    ann_rows = []
    random.seed(7)
    for cid, phash, camp_id, trend in creative_phashes:
        row = await conn.fetchrow("SELECT width, height FROM creatives WHERE id = $1", cid)
        W, H = float(row["width"] or 400), float(row["height"] or 300)

        n_faces = random.randint(0, 2)
        for _ in range(n_faces):
            fw = random.uniform(0.12, 0.22) * W
            fh = fw * random.uniform(1.1, 1.4)
            fx = random.uniform(0.1, 0.75) * W
            fy = random.uniform(0.05, 0.35) * H
            ann_rows.append((cid, "face",
                json.dumps({"x": round(fx, 1), "y": round(fy, 1), "w": round(fw, 1), "h": round(fh, 1)}),
                None, round(random.uniform(0.72, 0.97), 2)))

        n_text = random.randint(1, 3)
        for t in range(n_text):
            tw = random.uniform(0.35, 0.7) * W
            th = random.uniform(0.04, 0.09) * H
            tx = random.uniform(0.05, 0.2) * W
            ty = (0.35 + t * 0.12 + random.uniform(0, 0.05)) * H
            ann_rows.append((cid, "text",
                json.dumps({"x": round(tx, 1), "y": round(ty, 1), "w": round(tw, 1), "h": round(th, 1)}),
                random.choice(TEXT_LABELS), round(random.uniform(0.80, 0.99), 2)))

        cw = random.uniform(0.22, 0.42) * W
        ch = random.uniform(0.06, 0.10) * H
        cx = (W - cw) / 2 + random.uniform(-0.05, 0.05) * W
        cy = random.uniform(0.72, 0.86) * H
        ann_rows.append((cid, "cta",
            json.dumps({"x": round(cx, 1), "y": round(cy, 1), "w": round(cw, 1), "h": round(ch, 1)}),
            random.choice(CTA_LABELS), round(random.uniform(0.85, 0.99), 2)))

    await conn.executemany(
        "INSERT INTO creative_annotations (creative_id, annotation_type, bbox, label, confidence) "
        "VALUES ($1, $2, $3, $4, $5)",
        ann_rows
    )
    print(f"Seeded {len(ann_rows)} annotations")

    await conn.close()
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(main())
