# Demo Checklist

## Night Before

- [ ] `ollama list` — verify `qwen2.5vl:7b` present
- [ ] `docker-compose up -d postgres`
- [ ] `cd backend && alembic upgrade head`
- [ ] `cd backend && python scripts/seed_data.py` — ends with "Seed complete!"
- [ ] `cd backend && python scripts/precompute_analysis.py` — ends with "Pre-computation complete!"
- [ ] `cd backend && python scripts/setup_benchmark.py`

## Day Of (30 min before)

- [ ] Disable laptop sleep
- [ ] `curl http://localhost:8000/health` → `{"status":"ok","db":"ok","ollama":"ok"}`
- [ ] `docker-compose up` (or start backend + frontend manually)
- [ ] `ngrok http 3000` — copy URL, send to Sachin
- [ ] Open `http://localhost:3000` — dashboard loads with campaigns
- [ ] Click "Summer Fitness App 2024" campaign → creatives show scores
- [ ] Click a creative → detail page shows radar chart + annotations + recommendations
- [ ] Verify ≥3 creatives show red "Fatiguing" badge
- [ ] Upload a test image → see duplicate alert

## Demo Flow (8 min)

1. **Dashboard** → "10 campaigns, 50 analyzed creatives"
2. **Campaign view** → creative grid with AI scores and fatigue badges
3. **Creative detail** → radar chart, 7 dimensions, explain bounding boxes
4. **Fatiguing creative** → WoW CTR decline chart
5. **Live upload** → analysis appears within 15s
6. **Upload same image** → "Duplicate detected — Hamming distance: 0"
7. **API docs** → http://localhost:8000/docs

## Key Talking Points

- "No data leaves Kochava — everything runs on our hardware"
- "We explain WHY a creative works, not just the click rate"
- "We catch resized variants that silently waste budget"
- "We flag fatigue before CTR falls off a cliff"
- "< 15 seconds per image, live"

## Fallback if Ollama is slow

Pre-computed analyses load instantly from DB. Live upload may take up to 60s on cold start — that's OK, pivot to showing existing creatives while it processes.
