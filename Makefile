.PHONY: dev seed reset demo stop

# Start postgres, backend (hot-reload), and frontend dev server
dev:
	docker-compose up -d postgres
	@echo "Waiting for postgres..."
	@sleep 3
	@cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000 &
	@cd frontend && npm run dev

# Full re-seed: wipe everything, new images from benchmark, new KPIs, then re-analyse (~3 min)
seed:
	docker-compose up -d postgres
	@sleep 2
	cd backend && PYTHONPATH=. python3.11 scripts/seed_data.py
	cd backend && PYTHONPATH=. python3.11 scripts/precompute_analysis.py

# Re-analyse only: keep existing creatives/KPIs, just truncate analyses and recompute (~3 min)
reset:
	docker-compose up -d postgres
	@sleep 2
	cd backend && PYTHONPATH=. python3.11 scripts/precompute_analysis.py --reset

# Full demo reset: wipe + reseed + reanalyse + start all servers
demo: seed
	@cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000 &
	@cd frontend && npm run dev

# Stop background servers
stop:
	@pkill -f "uvicorn app.main" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	docker-compose stop postgres
