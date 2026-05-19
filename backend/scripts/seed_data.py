"""Seed demo data: 10 campaigns, 50 creatives, 30-day KPIs, fatigue examples, duplicates."""
import asyncio
import ctypes
import json
import os
import random
import shutil
from datetime import date, timedelta
from pathlib import Path

import asyncpg
from PIL import Image

DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://appuser:apppassword@localhost:5432/creative_opt"
)

BENCHMARK_IMAGES_ROOT = Path(__file__).parent.parent / "data" / "benchmark" / "images"

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

# Realistic filename components
_CAMPAIGN_SLUGS = {
    "Summer Fitness App 2024": "fitness",
    "Gaming App Launch Q3": "gaming",
    "Travel Booking Promo": "travel",
    "Food Delivery Rush": "foodapp",
    "Finance App - Save Smart": "finapp",
    "EdTech Back to School": "edtech",
    "Beauty Brand Spring": "beauty",
    "E-commerce Flash Sale": "ecomm",
    "Ride Share Launch City": "rideshare",
    "Streaming App Premium": "streaming",
}
_CONCEPTS = ["hero", "lifestyle", "product", "testimonial", "offer", "brand", "retarget", "awareness", "promo", "launch"]
_SIZES = ["300x250", "728x90", "320x50", "160x600", "1080x1080", "1200x628", "stories", "feed"]
_VARIANTS = ["v1", "v2", "v3", "a", "b", "c"]


def _creative_filename(campaign_name: str, index: int) -> str:
    slug = _CAMPAIGN_SLUGS.get(campaign_name, "ad")
    concept = _CONCEPTS[index % len(_CONCEPTS)]
    size = _SIZES[index % len(_SIZES)]
    variant = _VARIANTS[index % len(_VARIANTS)]
    return f"{slug}_{concept}_{size}_{variant}.jpg"


def _benchmark_images() -> list[Path]:
    imgs = list(BENCHMARK_IMAGES_ROOT.rglob("*.jpg"))
    if not imgs:
        raise RuntimeError(f"No benchmark images found in {BENCHMARK_IMAGES_ROOT}")
    random.shuffle(imgs)
    return imgs


def copy_benchmark_image(output_path: Path, src: Path) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(output_path))
    with Image.open(str(output_path)) as img:
        width, height = img.size
    return width, height


def compute_phash_signed(image_path: Path) -> int:
    import imagehash
    from PIL import Image
    h = imagehash.phash(Image.open(image_path).convert("RGB"), hash_size=8)
    unsigned = int(str(h), 16)
    return ctypes.c_int64(unsigned).value


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
    benchmark_imgs = _benchmark_images()
    n_creatives = (50 // len(CAMPAIGNS)) * len(CAMPAIGNS)
    # Pick 48 unique images, then repeat 2 to seed demo duplicate pairs
    selected_imgs = random.sample(benchmark_imgs, min(n_creatives - 2, len(benchmark_imgs)))
    while len(selected_imgs) < n_creatives - 2:
        selected_imgs.append(random.choice(benchmark_imgs))
    # Insert 2 intentional duplicates (same image, different campaign)
    selected_imgs.append(selected_imgs[4])   # duplicate of creative index 4
    selected_imgs.append(selected_imgs[15])  # duplicate of creative index 15

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
            filename = _creative_filename(CAMPAIGNS[i][0], j)
            storage_path = storage_base / str(campaign_id) / filename
            src_img = selected_imgs[idx]
            width, height = copy_benchmark_image(storage_path, src_img)
            file_size = storage_path.stat().st_size
            phash = compute_phash_signed(storage_path)

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

    # Detect duplicate pairs from the seeded creatives using real pHash comparison
    PHASH_THRESHOLD = 10
    rows = await conn.fetch("SELECT id, phash, campaign_id FROM creatives")
    pairs_inserted = 0
    seen_pairs: set[tuple[int, int]] = set()
    for i, row_a in enumerate(rows):
        for row_b in rows[i + 1:]:
            dist = bin((row_a["phash"] ^ row_b["phash"]) & 0xFFFFFFFFFFFFFFFF).count("1")
            if dist <= PHASH_THRESHOLD:
                id_a, id_b = min(row_a["id"], row_b["id"]), max(row_a["id"], row_b["id"])
                if (id_a, id_b) not in seen_pairs:
                    seen_pairs.add((id_a, id_b))
                    dup_type = "self" if row_a["campaign_id"] == row_b["campaign_id"] else "cross_platform"
                    await conn.execute(
                        """INSERT INTO duplicate_pairs (creative_id_a, creative_id_b, hamming_distance, duplicate_type)
                           VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING""",
                        id_a, id_b, dist, dup_type,
                    )
                    pairs_inserted += 1
    print(f"Detected {pairs_inserted} duplicate pairs from seeded creatives")

    # Annotations: face/text/CTA bounding boxes in pixel space
    CTA_LABELS = ["DOWNLOAD NOW", "GET STARTED", "LEARN MORE", "TRY FREE", "SHOP NOW", "INSTALL FREE"]
    TEXT_LABELS = ["Download Now", "Get Started Free", "Limited Time Offer", "Try for Free",
                   "50% OFF Today", "Join 1M+ Users", "See How It Works"]
    ann_rows = []
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
