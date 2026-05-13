# Task 22: Pre-compute Script + CLAUDE.md + Demo Checklist

**Files to create:**
- `backend/scripts/precompute_analysis.py`
- `CLAUDE.md`
- `docs/DEMO-CHECKLIST.md`

**Prereq:** All previous tasks complete. Ollama running with `qwen2.5vl:7b` pulled.

---

## Step 1: Create `backend/scripts/precompute_analysis.py`

```python
"""
Pre-compute Ollama analysis for all seeded creatives.
Run this the night before the demo — takes ~15 minutes for 50 images.

Usage:
    cd backend
    python scripts/precompute_analysis.py
"""
import asyncio
import os
from pathlib import Path

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.services.analysis_provider import OllamaProvider
from app.services.annotation_pipeline import AnnotationPipeline


async def main():
    print("Pre-warming Ollama model qwen2.5vl:7b...")
    provider = OllamaProvider()
    await provider.prewarm()
    print("Model ready.\n")

    annotation_pipeline = AnnotationPipeline()

    async with AsyncSessionLocal() as db:
        # Find all creatives without analysis
        result = await db.execute(
            select(Creative).where(
                ~Creative.id.in_(
                    select(CreativeAnalysis.creative_id)
                )
            ).order_by(Creative.id)
        )
        creatives = result.scalars().all()
        total = len(creatives)
        print(f"Found {total} creatives without analysis.\n")

        for i, creative in enumerate(creatives, 1):
            print(f"[{i}/{total}] Creative #{creative.id}: {creative.filename}")
            path = Path(creative.storage_path)

            if not path.exists():
                print(f"  ✗ File not found: {path} — skipping")
                continue

            try:
                # Run analysis
                if creative.format in ("mp4", "mov"):
                    from app.services.video_ingestion import VideoIngestionService
                    video_svc = VideoIngestionService()
                    try:
                        meta = video_svc.validate_video(path)
                        keyframes = await video_svc.extract_keyframes(path, meta.duration_seconds)
                        result_analysis = await provider.analyse_video_keyframes(keyframes)
                        for kf in keyframes:
                            kf.unlink(missing_ok=True)
                    except Exception as e:
                        print(f"  ✗ Video analysis failed: {e}")
                        continue
                else:
                    result_analysis = await provider.analyse_image(path)

                # Save analysis
                analysis = CreativeAnalysis(
                    creative_id=creative.id,
                    scores=result_analysis.scores.model_dump(),
                    overall_score=result_analysis.overall_score,
                    persuasion_strategy=result_analysis.persuasion_strategy,
                    dominant_emotion=result_analysis.dominant_emotion,
                    strengths=result_analysis.strengths,
                    weaknesses=result_analysis.weaknesses,
                    recommendations=result_analysis.recommendations,
                    explanation=result_analysis.explanation,
                    status=result_analysis.status,
                )
                db.add(analysis)

                # Run annotations (images only)
                if creative.format not in ("mp4", "mov"):
                    annotations = await annotation_pipeline.annotate(path)
                    for ann in annotations:
                        db.add(CreativeAnnotation(
                            creative_id=creative.id,
                            annotation_type=ann.annotation_type,
                            bbox=ann.bbox,
                            label=ann.label,
                            confidence=ann.confidence,
                        ))

                await db.commit()
                print(f"  ✓ Score: {result_analysis.overall_score}/10 | Strategy: {result_analysis.persuasion_strategy}")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                await db.rollback()

    print(f"\nPre-computation complete! {total} creatives processed.")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 2: Create `CLAUDE.md`

```markdown
# Creative Intelligence Platform

## Prerequisites

```bash
brew install tesseract ffmpeg postgresql@15
brew install ngrok/ngrok/ngrok
ollama pull qwen2.5vl:7b
ngrok config add-authtoken <YOUR_NGROK_TOKEN>  # free at ngrok.com
```

## Setup (first time)

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Install backend dependencies
cd backend && pip install -r requirements.txt

# 3. Run migrations
cd backend && alembic upgrade head

# 4. Seed demo data (10 campaigns, 50 creatives, 30-day KPIs)
cd backend && python scripts/seed_data.py

# 5. Setup benchmark corpus (downloads ~500 CVPR 2017 images, falls back to synthetic)
cd backend && python scripts/setup_benchmark.py

# 6. Pre-compute analysis (run night before demo — ~15 min)
cd backend && python scripts/precompute_analysis.py
```

## Run

```bash
# Option A: Docker (recommended for demo)
docker-compose up

# Option B: Local dev
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Access:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Test

```bash
cd backend && pytest -v
cd backend && pytest tests/test_integration.py -v -s  # requires DB + Ollama
```

## Key config

| Setting | Value |
|---------|-------|
| Ollama model | `qwen2.5vl:7b` (NOT qwen2-vl) |
| pHash threshold | 10 Hamming bits |
| Fatigue threshold | 20% WoW CTR decline |
| Analysis timeout | 60s per image |
| Max image size | 20MB |
| Max video size | 500MB |

## Architecture

```
Upload → Validate format/size → pHash compute → Content classify
       → Advisory lock → Dedup check → Save Creative
       → Fire-and-forget: Ollama analysis + OpenCV/Tesseract annotations
```

## Troubleshooting

**Ollama slow first call:** Normal — model cold start takes 30-60s. Run precompute_analysis.py the night before.

**tesseract not found:** `brew install tesseract` then restart backend.

**ffmpeg error:** `brew install ffmpeg`

**DB connection refused:** `docker-compose up -d postgres`
```

---

## Step 3: Create `docs/DEMO-CHECKLIST.md`

```markdown
# Demo Checklist

Run through this list in order before the pitch. Takes ~5 minutes.

## Night Before

- [ ] `ollama list` — verify `qwen2.5vl:7b` is present
- [ ] `docker-compose up -d postgres`
- [ ] `cd backend && alembic upgrade head` — no errors
- [ ] `cd backend && python scripts/seed_data.py` — ends with "Seed complete!"
- [ ] `cd backend && python scripts/precompute_analysis.py` — ends with "Pre-computation complete!"
- [ ] `cd backend && python scripts/setup_benchmark.py` — ends with corpus file written

## Day Of (30 min before)

- [ ] Disable laptop sleep: System Preferences → Battery → uncheck "Prevent automatic sleeping"
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","db":"ok","ollama":"ok"}`
- [ ] `docker-compose up` (or start backend + frontend manually)
- [ ] `ngrok http 3000` — copy the `https://xxxx.ngrok-free.app` URL
- [ ] Send URL to Sachin — verify he can open it on his device
- [ ] Open `http://localhost:3000` locally (your machine) AND the ngrok URL — both must load
- [ ] Click "Summer Fitness App 2024" campaign → creative table shows ≥5 creatives with scores
- [ ] Click any creative → detail page shows score radar + annotations + recommendations
- [ ] Verify ≥3 creatives show red "Fatiguing" badge
- [ ] Go to dashboard → Upload a test image → duplicate alert appears (for seeded duplicate)

## Demo Flow Script

1. **Open dashboard** → "10 active campaigns, 50 analyzed creatives"
2. **Click campaign** → show creative table with score column (progress bars) and fatigue badges
3. **Click high-scoring creative** → show radar chart, highlight the 7 dimensions
4. **Explain bounding boxes** on annotated image → face detection, text, CTA
5. **Click fatiguing creative** → explain WoW CTR decline graph
6. **Upload new creative live** → shows "Analysis queued" → within 15s shows score
7. **Upload same image again** → shows "Duplicate detected — Hamming distance: 0"
8. **Go to API docs** → http://localhost:8000/docs → show OpenAPI spec

## Talking Points

- **On-premise model**: "No data leaves Kochava. Everything runs on our hardware."
- **7 dimensions**: "We score what competitors don't explain — not just click rate, but WHY."
- **Deduplication**: "We catch resized ad variants that waste budget silently."
- **Fatigue**: "We flag before your CTR falls off a cliff, not after."
- **Speed**: "< 15 seconds per image. Live during pitch."

## Fallback if Ollama is slow

Pre-computed analyses are already in DB. Even if live upload analysis takes 60s,
the existing 50 seeded creatives all show instant analysis from pre-compute.
```

---

## Step 3b: Remote Hosting via ngrok

So Sachin can demo from any browser without needing your machine in the room.

### Install ngrok

```bash
brew install ngrok/ngrok/ngrok
ngrok config add-authtoken <YOUR_TOKEN>  # free at ngrok.com — takes 30 seconds
```

### Update `next.config.js` to allow ngrok hostname

The Next.js dev server blocks unknown hosts by default. Add this:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
  // Allow ngrok tunnel hostname
  allowedDevOrigins: ['*.ngrok-free.app', '*.ngrok.io'],
};

module.exports = nextConfig;
```

### Demo-day startup sequence

```bash
# Terminal 1 — start everything
docker-compose up -d postgres
cd backend && uvicorn app.main:app --reload --port 8000 &
cd frontend && npm run dev &

# Terminal 2 — open tunnel to frontend
ngrok http 3000
```

ngrok prints a URL like `https://abc123.ngrok-free.app`. That's the demo URL.

**Send Sachin this URL** — works from any browser, any network.

### Caveats + fallbacks

| Risk | Mitigation |
|------|-----------|
| Your laptop sleeps | System Preferences → Battery → turn off "Put hard disks to sleep" + "Prevent automatic sleeping when display is off" |
| ngrok session expires (free tier 2hr) | Start ngrok ≤30min before demo. Or pay $8/mo for persistent URL. |
| Live upload slow (Ollama cold start) | Pre-computed analyses load instantly. Run `python scripts/precompute_analysis.py` night before. |
| Network drops mid-demo | Backup plan: plug laptop into same projector, demo locally |

### Optional: stable subdomain ($8/mo ngrok personal plan)

Instead of random URL each session:
```bash
ngrok http --domain=kochava-demo.ngrok.app 3000
```
Gives permanent URL `https://kochava-demo.ngrok.app` — no need to resend link each time.

---

## Step 4: Final full-stack smoke test

```bash
# Start everything
docker-compose up -d

# Verify health
curl http://localhost:8000/health

# Check campaigns exist
curl http://localhost:8000/campaigns | python -m json.tool | head -20

# Check creative has analysis
curl http://localhost:8000/creatives/1 | python -m json.tool | grep overall_score

# Open frontend
open http://localhost:3000
```

Expected: health = ok, campaigns return 10 items, creative has overall_score > 0, frontend loads.

---

## Step 5: Commit

```bash
git add backend/scripts/precompute_analysis.py CLAUDE.md docs/DEMO-CHECKLIST.md
git commit -m "feat: pre-compute script, CLAUDE.md setup guide, demo checklist"
```

---

## All tasks complete! 🎉

Run the full test suite:
```bash
cd backend && pytest -v --tb=short
```

Expected: all tests pass. Backend ready for demo.
