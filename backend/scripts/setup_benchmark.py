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
CVPR_GCS_BASE = "https://storage.googleapis.com/ads-dataset/subfolder-{n}.zip"
MAX_IMAGES_DEFAULT = 500
CVPR_SUBFOLDERS = 1  # subfolder-0 has 5673 images — one zip is enough
MAX_PER_SUBFOLDER = 500  # 500 shuffled picks from 5673 = plenty of variety


def _filter_nsfw(directory: Path) -> None:
    """Remove NSFW images from directory using nudenet classifier."""
    try:
        from nudenet import NudeClassifier
        classifier = NudeClassifier()
    except Exception:
        print("  nudenet not available, skipping NSFW filter")
        return
    paths = list(directory.glob("*.jpg")) + list(directory.glob("*.jpeg")) + list(directory.glob("*.png"))
    removed = 0
    for path in paths:
        try:
            result = classifier.classify(str(path))
            score = result.get(str(path), {}).get("unsafe", 0.0)
            if score > 0.6:
                path.unlink()
                removed += 1
        except Exception:
            continue
    if removed:
        print(f"  Removed {removed} NSFW images")


async def download_cvpr_subfolder(n: int, images_dir: Path, client: httpx.AsyncClient) -> int:
    """Download one subfolder zip and extract images. Returns count extracted."""
    url = CVPR_GCS_BASE.format(n=n)
    zip_path = BENCHMARK_DIR / f"subfolder-{n}.zip"
    dest = images_dir / str(n)
    if dest.exists() and any(dest.glob("*.jpg")):
        count = len(list(dest.glob("*.jpg")))
        print(f"  subfolder-{n}: already downloaded ({count} images), skipping")
        return count
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading subfolder-{n}...", end=" ", flush=True)
    try:
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                print(f"HTTP {resp.status_code}, skipping")
                return 0
            with open(zip_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        with zipfile.ZipFile(zip_path) as zf:
            import random as _rnd
            imgs = [nm for nm in zf.namelist() if nm.lower().endswith(('.jpg', '.jpeg', '.png'))]
            _rnd.shuffle(imgs)
            imgs = imgs[:MAX_PER_SUBFOLDER]
            for nm in imgs:
                data = zf.read(nm)
                (dest / Path(nm).name).write_bytes(data)
        zip_path.unlink(missing_ok=True)
        _filter_nsfw(dest)
        count = len(list(dest.glob("*.jpg")))
        print(f"{count} images (after NSFW filter)")
        return count
    except Exception as e:
        print(f"failed: {e}")
        zip_path.unlink(missing_ok=True)
        return 0


async def download_cvpr_subset(max_images: int) -> list[int]:
    """Download multiple CVPR subfolders until we have enough images."""
    print(f"Downloading CVPR 2017 Ads Dataset (up to {CVPR_SUBFOLDERS} subfolders)...")
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = BENCHMARK_DIR / "images"
    images_dir.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=300) as client:
        for n in range(CVPR_SUBFOLDERS):
            await download_cvpr_subfolder(n, images_dir, client)
    return compute_phashes_for_dir(images_dir, max_images)


def compute_phashes_for_dir(directory: Path, max_images: int) -> list[int]:
    hashes = []
    image_paths = list(directory.rglob("*.jpg")) + list(directory.rglob("*.jpeg")) + list(directory.rglob("*.png"))
    for path in image_paths[:max_images]:
        try:
            h = imagehash.phash(Image.open(path).convert("RGB"), hash_size=8)
            hashes.append(int(str(h), 16))
        except Exception as e:
            print(f"  Warning: failed to hash {path}: {e}")
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
        if len(existing) >= max_images and len(existing) > 0:
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
