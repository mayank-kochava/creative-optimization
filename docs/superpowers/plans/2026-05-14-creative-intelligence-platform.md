# Creative Intelligence Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Creative Intelligence Platform MVP in 7 days for executive demo — upload ad creatives, get AI analysis scores + annotations + fatigue detection + KPI dashboard.

**Architecture:** Python 3.11 FastAPI backend + PostgreSQL 15 + Qwen2-VL-7B via Ollama (local, no external API). React 18 + Next.js 14 + Ant Design 5 frontend.

**Tech Stack:** FastAPI 0.111, SQLAlchemy 2.0 async, asyncpg, Pydantic v2, imagehash 4.3.2, OpenCV, pytesseract, ffmpeg-python, Ollama model `qwen2.5vl:7b`

**Key docs:** `docs/eng-research.md`, `docs/data-model.md`, `docs/contracts/api.yaml`, `docs/product-spec-v2.md`

---

## Task Checklist

### Day 1 — Foundation (scaffold + DB + seed)

- [ ] [Task 01](tasks/task-01-project-scaffold.md) — Project Scaffold (docker-compose, requirements, config, database, main)
- [ ] [Task 02](tasks/task-02-db-models.md) — Database Models (SQLAlchemy 2.0 mapped_column)
- [ ] [Task 03](tasks/task-03-alembic-migration.md) — Alembic Migration (initial schema)
- [ ] [Task 04](tasks/task-04-seed-data.md) — Seed Data Script (10 campaigns, 50 creatives, 30-day KPIs)

**Day 1 done when:** `docker-compose up -d postgres && alembic upgrade head && python scripts/seed_data.py` runs clean.

---

### Day 2 — AI Pipeline (benchmark + schemas + Ollama)

- [ ] [Task 05](tasks/task-05-benchmark-corpus.md) — Benchmark Corpus Setup (CVPR 2017 download + fallback)
- [ ] [Task 06](tasks/task-06-pydantic-schemas.md) — Pydantic Analysis Schemas (OllamaAnalysisResponse, validators)
- [ ] [Task 07](tasks/task-07-prompts.md) — Prompt Engineering (structured JSON prompt, few-shot)
- [ ] [Task 08](tasks/task-08-ollama-provider.md) — Ollama Provider (retry logic, pre-warm, video keyframes)

**Day 2 done when:** `provider.analyse_image(sample.jpg)` returns valid scored JSON from Ollama.

---

### Day 3 — Analysis Services (dedup + classifier + annotations + fatigue)

- [ ] [Task 09](tasks/task-09-deduplication.md) — Deduplication Service (pHash + advisory lock)
- [ ] [Task 10](tasks/task-10-content-classifier.md) — Content Classifier (non-ad rejection)
- [ ] [Task 11](tasks/task-11-annotation-pipeline.md) — Annotation Pipeline (OpenCV faces + pytesseract text + CTA heuristic)
- [ ] [Task 12](tasks/task-12-fatigue-detector.md) — Fatigue Detector (WoW CTR decline ≥20%)

**Day 3 done when:** All service unit tests pass. Upload a JPEG → dedup + annotation + fatigue all return results.

---

### Day 4 — Data Services + Ingestion (KPI + video + orchestrator)

- [ ] [Task 13](tasks/task-13-kpi-aggregator.md) — KPI Aggregator (CTR/CVR/CPI/ROAS)
- [ ] [Task 14](tasks/task-14-video-ingestion.md) — Video Ingestion Service (ffmpeg keyframes, codec validation)
- [ ] [Task 15](tasks/task-15-ingestion-orchestrator.md) — Ingestion Orchestrator (full upload flow)

**Day 4 done when:** Full upload flow works end-to-end in isolation — file in → creative saved → analysis fired.

---

### Day 5 — API Layer (endpoints + integration tests)

- [ ] [Task 16](tasks/task-16-health-campaigns-api.md) — Health + Campaign API Endpoints
- [ ] [Task 17](tasks/task-17-creatives-api.md) — Creative Upload + Detail Endpoints
- [ ] [Task 18](tasks/task-18-integration-tests.md) — Integration Tests (E2E flow)

**Day 5 done when:** `pytest -v` passes all tests. `curl http://localhost:8000/docs` shows full API.

---

### Day 6 — Frontend (Next.js + Ant Design)

- [ ] [Task 19](tasks/task-19-frontend-setup.md) — Frontend Setup + API Client
- [ ] [Task 20](tasks/task-20-dashboard-pages.md) — Dashboard + Campaign Pages
- [ ] [Task 21](tasks/task-21-creative-detail.md) — Creative Detail Page + Components

**Day 6 done when:** http://localhost:3000 shows campaigns, creative table, detail page with radar chart + annotated image.

---

### Day 7 — Demo Prep (precompute + polish + rehearsal)

- [ ] [Task 22](tasks/task-22-precompute-demo.md) — Pre-compute Script + CLAUDE.md + Demo Checklist

**Day 7 done when:** All 50 seeded creatives have analysis. Demo checklist passes. 3 dry runs completed.
