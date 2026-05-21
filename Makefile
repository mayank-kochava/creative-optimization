.PHONY: dev seed reset demo stop expand-data clean-data fresh

# Use venv Python if setup.sh was run, otherwise fall back to system python3.11
PYTHON := $(shell [ -f backend/.venv/bin/python ] && echo backend/.venv/bin/python || echo python3.11)
UVICORN := $(shell [ -f backend/.venv/bin/uvicorn ] && echo backend/.venv/bin/uvicorn || echo uvicorn)

# Start postgres, backend (hot-reload), and frontend dev server
dev:
	docker-compose up -d postgres
	@echo "Waiting for postgres..."
	@sleep 3
	@cd backend && PYTHONPATH=. $(UVICORN) app.main:app --reload --port 8000 &
	@cd frontend && npm run dev

# Download more CVPR subfolders to expand image pool (run once, ~5 min, ~500 images)
expand-data:
	cd backend && PYTHONPATH=. $(PYTHON) scripts/setup_benchmark.py --max-images 500

# Full re-seed: wipe everything, new images from benchmark, new KPIs, then re-analyse (~3 min)
seed:
	docker-compose up -d postgres
	@sleep 2
	cd backend && PYTHONPATH=. $(PYTHON) scripts/seed_data.py
	cd backend && PYTHONPATH=. $(PYTHON) scripts/precompute_analysis.py

# Re-analyse only: keep existing creatives/KPIs, just truncate analyses and recompute (~3 min)
reset:
	docker-compose up -d postgres
	@sleep 2
	cd backend && PYTHONPATH=. $(PYTHON) scripts/precompute_analysis.py --reset

# Full demo reset: wipe + reseed + reanalyse + start all servers
demo: seed
	@cd backend && PYTHONPATH=. $(UVICORN) app.main:app --reload --port 8000 &
	@cd frontend && npm run dev

# Wipe all downloaded images, benchmark corpus, and uploaded creatives
clean-data:
	@pkill -f "setup_benchmark\|seed_data\|precompute_analysis" 2>/dev/null || true
	rm -rf backend/data/benchmark/
	rm -rf /tmp/uploads/
	@echo "All image data cleared."

# Full clean slate: wipe data + re-download benchmark + reseed + reanalyse (~10 min)
fresh: clean-data expand-data seed

# Stop background servers
stop:
	@pkill -f "uvicorn app.main" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	docker-compose stop postgres
