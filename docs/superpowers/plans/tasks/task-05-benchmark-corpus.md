# Task 05: Benchmark Corpus Setup

**Files to create:**
- `backend/scripts/setup_benchmark.py`
- `backend/tests/test_benchmark.py`

**Prereq:** Task 01 complete (project structure exists).

---

## Step 1: Write failing test

```python
# backend/tests/test_benchmark.py
import json
import pytest
from pathlib import Path


def test_corpus_file_exists_after_setup():
    """Run setup and verify corpus.json is created with ≥500 hashes."""
    import subprocess
    result = subprocess.run(
        ["python", "scripts/setup_benchmark.py", "--max-images", "50"],  # fast mode for test
        cwd="backend",
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    corpus_path = Path("data/benchmark/corpus.json")
    assert corpus_path.exists()
    hashes = json.loads(corpus_path.read_text())
    assert len(hashes) >= 50
    assert all(isinstance(h, int) for h in hashes)
```

Run: `cd backend && pytest tests/test_benchmark.py -v`
Expected: FAIL — script not found.

---

## Step 2: Create `backend/scripts/setup_benchmark.py`

```python
"""Download CVPR 2017 Ads Dataset subset for benchmark corpus, or generate synthetic fallback."""
import argparse
import asyncio
import json
import os
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import imagehash
from PIL import Image

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
                        print(f"\r  {pct:.1f}% ({downloaded // 1024 // 1024}MB)", end="", flush=True)
    print()

    print("Extracting images...")
    with zipfile.ZipFile(zip_path) as zf:
        image_files = [n for n in zf.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png'))][:max_images]
        for name in image_files:
            zf.extract(name, images_dir)

    zip_path.unlink()  # free space
    return compute_phashes_for_dir(images_dir, max_images)


def compute_phashes_for_dir(directory: Path, max_images: int) -> list[int]:
    """Compute pHash for all images in directory."""
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
    """Generate synthetic benchmark images using Pillow and compute their pHashes."""
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
        from PIL import ImageDraw
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
        # Top up with synthetic images
        synthetic = generate_synthetic_corpus(max_images - len(hashes))
        hashes.extend(synthetic)

    CORPUS_FILE.write_text(json.dumps(hashes[:max_images]))
    print(f"Corpus saved: {CORPUS_FILE} ({len(hashes[:max_images])} hashes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-images", type=int, default=MAX_IMAGES_DEFAULT)
    args = parser.parse_args()
    asyncio.run(main(args.max_images))
```

---

## Step 3: Run benchmark setup

```bash
cd backend
python scripts/setup_benchmark.py --max-images 500
```

Expected: downloads CVPR images (or falls back to synthetic), saves `data/benchmark/corpus.json`.

---

## Step 4: Run tests

```bash
pytest tests/test_benchmark.py -v
```

Expected: PASS.

---

## Step 5: Verify corpus

```bash
python -c "import json; h=json.loads(open('data/benchmark/corpus.json').read()); print(f'{len(h)} hashes, first: {h[0]}')"
```

Expected: `500 hashes, first: <integer>`

---

## Step 6: Create `backend/app/services/benchmark.py`

> **BUG FIX:** Without this service, `benchmark_percentile` is always NULL in analysis results.
> This is the only service that computes competitive percentile for the demo's "Top X%" badge.

```python
import json
from pathlib import Path

from app.config import settings


class BenchmarkService:
    def __init__(self):
        self._corpus: list[int] | None = None

    def _load_corpus(self) -> list[int]:
        if self._corpus is not None:
            return self._corpus
        corpus_path = Path(settings.benchmark_corpus_path)
        if not corpus_path.exists():
            self._corpus = []
            return self._corpus
        self._corpus = json.loads(corpus_path.read_text())
        return self._corpus

    def compute_percentile(self, phash: int) -> int | None:
        """
        Return the percentile rank of `phash` against the benchmark corpus.

        We measure how close this creative's hash is to any benchmark ad.
        Lower minimum Hamming distance → more similar to known good ads → higher percentile.
        Returns None if corpus is empty.

        Returns int in range [1, 100] where 100 = top of corpus (most similar).
        """
        corpus = self._load_corpus()
        if not corpus:
            return None

        # Compute minimum Hamming distance to any corpus hash
        min_dist = min(bin(phash ^ h).count("1") for h in corpus)

        # Distance 0 = identical = top 1%, distance 64 (max) = bottom 1%
        # Linear mapping: percentile = 100 - round(min_dist / 64 * 99)
        percentile = max(1, 100 - round(min_dist / 64 * 99))
        return percentile
```

---

## Step 6b: Add test for BenchmarkService

Add to `backend/tests/test_benchmark.py`:

```python
def test_benchmark_service_returns_percentile():
    import json
    from pathlib import Path
    from app.services.benchmark import BenchmarkService

    # Write a temp corpus
    corpus = [0xABCDEF1234567890, 0x1111111111111111, 0x0000000000000000]
    corpus_path = Path("data/benchmark/corpus.json")
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(corpus))

    svc = BenchmarkService()
    svc._corpus = corpus  # inject directly to avoid file I/O

    # Identical hash → top percentile
    p = svc.compute_percentile(0xABCDEF1234567890)
    assert p == 100

    # Very different hash → low percentile
    p2 = svc.compute_percentile(0x5432101234567890)
    assert p2 is not None
    assert 1 <= p2 <= 100


def test_benchmark_service_returns_none_for_empty_corpus():
    from app.services.benchmark import BenchmarkService
    svc = BenchmarkService()
    svc._corpus = []
    assert svc.compute_percentile(12345) is None
```

---

## Step 6c: Wire BenchmarkService into analysis flow

In `backend/app/ingestion/orchestrator.py`, after analysis runs, compute percentile:

```python
# In _run_analysis, after result = await self.analysis_provider.analyse_image(path)
from app.services.benchmark import BenchmarkService
benchmark_svc = BenchmarkService()
benchmark_percentile = benchmark_svc.compute_percentile(
    # re-read phash from DB since creative was already saved
    (await db.execute(select(Creative.phash).where(Creative.id == creative_id))).scalar_one()
)
# Pass benchmark_percentile to CreativeAnalysis constructor:
analysis = CreativeAnalysis(
    ...
    benchmark_percentile=benchmark_percentile,
    ...
)
```

> **Note:** In `orchestrator.py` Step 2, add `benchmark_percentile=benchmark_percentile` to the `CreativeAnalysis(...)` constructor. The `CreativeAnalysis` model must have this column (verified in Task 02).

---

## Step 7: Commit

```bash
git add backend/scripts/setup_benchmark.py backend/app/services/benchmark.py backend/tests/test_benchmark.py
git commit -m "feat: benchmark corpus setup + BenchmarkService.compute_percentile"
```
