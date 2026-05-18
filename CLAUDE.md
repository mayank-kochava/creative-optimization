# Creative Intelligence Platform

## Prerequisites

```bash
brew install tesseract ffmpeg postgresql@15
brew install ngrok/ngrok/ngrok
ollama pull qwen2.5vl:7b
```

## Setup (first time)

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Install backend dependencies
cd backend && pip install -r requirements.txt

# 3. Run migrations
cd backend && alembic upgrade head

# 4. Seed demo data
cd backend && python scripts/seed_data.py

# 5. Setup benchmark corpus
cd backend && python scripts/setup_benchmark.py

# 6. Pre-compute analysis (run night before demo — ~15 min)
cd backend && python scripts/precompute_analysis.py
```

## Run

```bash
# Docker (recommended)
docker-compose up

# OR local dev
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Test

```bash
cd backend && python3.11 -m pytest -v
```

## Key config

| Setting | Value |
|---|---|
| Ollama model | `qwen2.5vl:7b` |
| pHash threshold | 10 Hamming bits |
| Fatigue threshold | 20% WoW CTR decline |
| Analysis timeout | 60s per image |
| Max image size | 20MB |
| Max video size | 500MB |

## Architecture

```
Upload → Validate format/size → pHash compute → Content classify
       → Dedup check → Save Creative
       → Fire-and-forget: Ollama analysis + OpenCV/Tesseract annotations
```

## Demo remote access

```bash
ngrok http 3000
```

Prints a URL like `https://abc123.ngrok-free.app`. Send to Sachin.

## Troubleshooting

- **Ollama slow first call:** Cold start 30-60s. Run precompute the night before.
- **tesseract not found:** `brew install tesseract`
- **ffmpeg error:** `brew install ffmpeg`
- **DB connection refused:** `docker-compose up -d postgres`
