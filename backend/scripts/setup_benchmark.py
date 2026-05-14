"""Download CVPR 2017 Ads Dataset subset for benchmark corpus, or generate synthetic fallback."""
import argparse
import asyncio
import json
import os
import zipfile
from pathlib import Path

import httpx
import imagehash
from PIL import Image, ImageDraw

BENCHMARK_DIR = Path(os.environ.get("BENCHMARK_PATH", "data/benchmark"))
CORPUS_FILE = BENCHMARK_DIR / "corpus.json"
CVPR_GCS_URL = "https://storage.googleapis.com/ads-dataset/subfolder-0.zip"
MAX_IMAGES_DEFAULT = 500


async def download_cvpr_subset(max_images: int) -> list[int]:
    """Download subfolder-0.zip from GCS and extract up to max_images images."""
    print(f"Downloading CVPR 2017 Ads Dataset (subfolder-0)...")
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = BENCHMARK_DIR / "images"
    images_dir.mkdir(exist_ok=True)
    zip_path = BENCHMARK_DIR / "subfolder-0.zip"
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("GET", CVPR_GCS_URL) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"Download failed: {resp.status_code}")
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(zip_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:.1f}%", end="", flush=True)
    print()
    print("Extracting images...")
    with zipfile.ZipFile(zip_path) as zf:
        image_files = [n for n in zf.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png'))][:max_images]
        for name in image_files:
            zf.extract(name, images_dir)
    zip_path.unlink()
    return compute_phashes_for_dir(images_dir, max_images)


def compute_phashes_for_dir(directory: Path, max_images: int) -> list[int]:
    hashes = []
    image_paths = list(directory.rglob("*.jpg")) + list(directory.rglob("*.jpeg")) + list(directory.rglob("*.png"))
    for path in image_paths[:max_images]:
        try:
            h = imagehash.phash(Image.open(path).convert("RGB"), hash_size=8)
            hashes.append(int(str(h), 16))
        except Exception:
            continue
    print(f"Computed {len(hashes)} pHashes from real images")
    return hashes


def generate_synthetic_corpus(count: int) -> list[int]:
    import random
    print(f"Generating {count} synthetic benchmark images (fallback)...")
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    hashes = []
    colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan", "white", "gray"]
    for i in range(count):
        width = random.choice([300, 728, 160, 320, 300])
        height = random.choice([250, 90, 600, 50, 250])
        color = colors[i % len(colors)]
        img = Image.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Ad Creative {i}", fill="white" if color != "white" else "black")
        draw.rectangle([width // 4, height // 4, 3 * width // 4, 3 * height // 4], outline="black", width=2)
        h = imagehash.phash(img, hash_size=8)
        hashes.append(int(str(h), 16))
        if i % 100 == 0:
            print(f"  {i}/{count}", end="\r")
    print(f"Generated {len(hashes)} synthetic pHashes")
    return hashes


async def main(max_images: int):
    if CORPUS_FILE.exists():
        existing = json.loads(CORPUS_FILE.read_text())
        if len(existing) >= max_images:
            print(f"Corpus already exists with {len(existing)} hashes. Skipping.")
            return
    hashes = []
    try:
        hashes = await asyncio.wait_for(download_cvpr_subset(max_images), timeout=300)
    except Exception as e:
        print(f"Download failed: {e}. Using synthetic fallback.")
        hashes = generate_synthetic_corpus(max_images)
    if len(hashes) < max_images:
        synthetic = generate_synthetic_corpus(max_images - len(hashes))
        hashes.extend(synthetic)
    CORPUS_FILE.write_text(json.dumps(hashes[:max_images]))
    print(f"Corpus saved: {CORPUS_FILE} ({len(hashes[:max_images])} hashes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-images", type=int, default=MAX_IMAGES_DEFAULT)
    args = parser.parse_args()
    asyncio.run(main(args.max_images))
