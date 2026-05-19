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
cd backend && PYTHONPATH=. python3.11 scripts/seed_data.py

# 5. Setup benchmark corpus
cd backend && PYTHONPATH=. python3.11 scripts/setup_benchmark.py

# 6. Install frontend dependencies
cd frontend && npm install

# 7. Add API key to backend/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> backend/.env

# 8. Pre-compute analysis with AI (~3 min for 50 images)
cd backend && PYTHONPATH=. python3.11 scripts/precompute_analysis.py --reset
```

## Daily dev workflow

```bash
make dev      # start postgres + backend (hot-reload) + frontend
make stop     # stop background servers
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Reset demo data (re-analyse all creatives with active AI provider)

```bash
make reset    # truncate analyses + recompute (~3 min)
```

## One-shot demo start (reset + start all servers)

```bash
make demo
```

## Test

```bash
cd backend && python3.11 -m pytest -v
```

## Key config

| Setting | Value |
|---|---|
| Default AI provider | Claude Sonnet 4.6 (switchable from header) |
| Fallback provider | Qwen2.5-VL via Ollama (local) |
| API key location | `backend/.env` → `ANTHROPIC_API_KEY` |
| pHash threshold | 10 Hamming bits |
| Fatigue threshold | 20% WoW CTR decline |
| Analysis timeout | 60s per image |
| Max image size | 20MB |
| Max video size | 500MB |

## Switching AI provider

Use the badge in the top-right corner of the UI to switch between Claude and Qwen2.5-VL at runtime. Active provider applies to new uploads immediately. To re-analyse all existing creatives with the new provider run `make reset`.

## Architecture

```
Upload → Validate format/size → pHash compute → Content classify
       → Dedup check → Save Creative
       → Fire-and-forget: active provider analysis + OpenCV/Tesseract annotations
```

## Demo remote access

```bash
ngrok http 3000
```

Prints a URL like `https://abc123.ngrok-free.app`. Send to Sachin.

## Troubleshooting

- **ModuleNotFoundError: No module named 'app':** Run backend scripts with `PYTHONPATH=. python3.11 scripts/...` from the `backend/` directory, or use `make` targets which handle this automatically.
- **Claude API errors:** Check `ANTHROPIC_API_KEY` in `backend/.env`. Switch to Ollama from the header badge if API is unavailable.
- **Ollama slow first call:** Cold start 30-60s. Run `make reset` the night before the demo.
- **tesseract not found:** `brew install tesseract`
- **ffmpeg error:** `brew install ffmpeg`
- **DB connection refused:** `docker-compose up -d postgres`
