---
id: eng-research
title: Engineering Research
---

# Engineering Research: Creative Intelligence Platform

**Date:** 2026-05-14  
**Spec:** product-spec-v2.md  
**Status:** Complete — 0 open questions

---

## Context

This is a **greenfield project** — no existing codebase to research. All decisions are new. Research validates technology choices against spec requirements, confirms library APIs, and documents rationale with alternatives.

---

## Unknowns Table

| Item | Category | Source | Status |
|------|----------|--------|--------|
| Ollama API format for vision models | Tech | Analysis Engine module | ✅ Resolved |
| Correct Qwen2-VL model name in Ollama | Tech | Analysis Engine | ✅ Resolved |
| imagehash pHash algorithm (DCT vs avg) | Tech | Deduplication module | ✅ Resolved |
| Hamming distance API in imagehash | Tech | Deduplication module | ✅ Resolved |
| PostgreSQL advisory lock syntax | Tech | CG-005 (race condition) | ✅ Resolved |
| CVPR 2017 dataset download — registration required? | Data | Benchmark module | ✅ Resolved |
| ffmpeg Python binding choice | Tech | Video pipeline | ✅ Resolved |
| OpenCV face detection approach | Tech | Annotation pipeline | ✅ Resolved |
| Pydantic v2 response validation approach | Tech | Analysis Engine | ✅ Resolved |

---

## Confirmed Technical Facts

### Ollama Vision API

- **Endpoint:** `POST http://localhost:11434/api/chat`
- **Model name:** `qwen2.5vl:7b`
- **Image format:** Base64-encoded string in `images` array
- **Streaming:** Supported (`"stream": true`), not needed for demo
- **Pre-warm:** Send one dummy inference at startup — forces memory map, subsequent calls are fast

```python
import httpx, base64

def analyse(image_path: str, prompt: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    resp = httpx.post("http://localhost:11434/api/generate", json={
        "model": "qwen2.5vl:7b",
        "prompt": prompt,
        "images": [b64],
        "stream": False,
    }, timeout=60)
    return resp.json()["response"]
```

### imagehash pHash

- **Library:** `imagehash==4.3.2` (pip install imagehash)
- **Algorithm:** Full DCT-based pHash via `scipy.fftpack.dct` — matches spec exactly
- **64-bit hash:** `imagehash.phash(img, hash_size=8)` → 8×8 binary matrix = 64 bits
- **Hamming distance:** subtraction operator `hash1 - hash2` → integer 0–64

```python
import imagehash
from PIL import Image

h1 = imagehash.phash(Image.open("creative_a.jpg"), hash_size=8)
h2 = imagehash.phash(Image.open("creative_b.jpg"), hash_size=8)
distance = h1 - h2  # 0 = identical, ≤10 = duplicate per spec
```

### CVPR 2017 Dataset

- **No registration required.** Freely accessible on Google Cloud Storage.
- **Download:** `https://storage.googleapis.com/ads-dataset/subfolder-{0..10}.zip`
- **Size:** ~11.6 GB compressed (subfolder-10 alone is 6.5 GB)
- **Annotations:** `https://people.cs.pitt.edu/~kovashka/ads/annotations_images.zip` (6.5 MB)
- **Fallback corpus still needed** on Day 1 — 11.6 GB takes hours to download. Bundle 500 images.

---

## Technology Decisions

### Decision: Python 3.11 as primary language

**Chosen:** Python 3.11

**Rationale:**
- ML/vision ecosystem lives in Python: PyTorch, OpenCV, imagehash, Pillow, scikit-learn
- Ollama Python SDK + httpx for local inference calls
- FastAPI + Pydantic v2 for typed REST API with auto-generated OpenAPI docs
- ffmpeg-python for video processing
- Fastest path to working demo — no language boundary friction

**Alternatives Considered:**
1. **Go** — Kochava's primary backend language
   - Pros: Performance, existing team knowledge, deploys well
   - Cons: ML ecosystem is Python-native; bridging Go→Python for Ollama adds complexity; no Go imagehash with DCT pHash; vision/annotation tooling absent
   - Rejected: Wrong language for ML-heavy workload
2. **Node.js** — Frontend team familiarity
   - Pros: Shared language with frontend
   - Cons: Even weaker ML ecosystem; no production imagehash; OpenCV bindings fragile
   - Rejected: Not suitable for ML pipeline

---

### Decision: FastAPI over Flask/Django

**Chosen:** FastAPI 0.111+

**Rationale:**
- Native Pydantic v2 integration — response schema validation is automatic
- Async request handling — won't block on Ollama calls (up to 15s per creative)
- Auto-generates OpenAPI spec at `/docs` — useful for demo ("look, it's already documented")
- Dependency injection system — clean module wiring for AnalysisProvider

**Alternatives Considered:**
1. **Flask** — simpler, lighter
   - Pros: Minimal boilerplate
   - Cons: No async; requires marshmallow or manual validation; no built-in OpenAPI
   - Rejected: Missing async and auto-validation — both critical here
2. **Django REST Framework**
   - Pros: Batteries-included, admin UI
   - Cons: Heavy; ORM conflicts with SQLAlchemy; overkill for 8 endpoints
   - Rejected: Too much overhead for a focused API

---

### Decision: Qwen2-VL-7B via Ollama over alternatives

**Chosen:** Qwen2-VL-7B (`qwen2.5vl:7b`) via Ollama

**Rationale:**
- Best vision-language reasoning at 7B scale — outperforms LLaVA-1.6-7B on structured output tasks
- Ollama Metal acceleration on M4 Pro — 20-30 tokens/sec at Q4 quantisation → ~10-15s per creative
- Structured JSON output via prompt engineering — Pydantic validates the response
- No external API calls — data stays on-device (critical for privacy claim)
- Ollama model management: `ollama pull qwen2.5vl:7b` is all setup needed

**Alternatives Considered:**
1. **LLaVA-1.6-7B via Ollama**
   - Pros: Mature, well-tested
   - Cons: Weaker at following structured JSON output instructions; less accurate on ad creative elements
   - Rejected: Qwen2-VL produces more consistent structured output
2. **Claude/GPT-4V API**
   - Pros: Highest quality output
   - Cons: Data leaves Kochava infra; API cost; external dependency; "it's just a wrapper" criticism
   - Rejected: Privacy and credibility concerns
3. **InternVL2-8B**
   - Pros: Competitive with Qwen2-VL
   - Cons: Not available in Ollama registry; requires manual model loading
   - Rejected: Setup complexity for 1-week timeline
4. **Fine-tuned model on ad datasets**
   - Pros: Most "our own model" story
   - Cons: 3-6 weeks minimum; not feasible for MVP timeline
   - Deferred: Phase 1

**Implementation Notes:**
- Pre-warm on startup: one dummy inference forces memory map. Without this, first call takes 30-60s.
- Retry logic: 3 retries on Pydantic validation failure, temperature=0 for determinism
- System prompt must constrain output to JSON only — include `respond ONLY with valid JSON` instruction

---

### Decision: PostgreSQL 15 over SQLite

**Chosen:** PostgreSQL 15

**Rationale:**
- Advisory locks (`pg_advisory_xact_lock`) required for race-condition-safe duplicate detection (CG-005)
- JSONB column type for scores/annotations — fast indexed queries without separate tables
- Production-ready for Phase 1 — no migration needed when going live
- Docker Compose image readily available

**Alternatives Considered:**
1. **SQLite**
   - Pros: Zero setup, file-based, trivially simple for demo
   - Cons: No advisory locks (race condition unsolvable); no JSONB; WAL mode still serialises writes; can't scale to Phase 1
   - Rejected: Cannot safely implement CG-005 without advisory locks
2. **MongoDB**
   - Pros: Flexible schema for JSON analysis results
   - Cons: No advisory locks; unfamiliar to Kochava Go team; overkill for relational data
   - Rejected: JSONB in Postgres gives same flexibility with ACID guarantees

**Implementation Notes:**
```sql
-- Advisory lock pattern for duplicate detection
SELECT pg_advisory_xact_lock(phash_bigint);
-- Then query + insert in same transaction
```

---

### Decision: SQLAlchemy 2.0 + Alembic for ORM

**Chosen:** SQLAlchemy 2.0 (async) + Alembic

**Rationale:**
- SQLAlchemy 2.0 has full async support with asyncpg driver — matches FastAPI async model
- Alembic handles migrations cleanly — critical for Docker seed step
- Type-annotated model definitions compatible with Pydantic v2
- Industry standard; well-documented

**Alternatives Considered:**
1. **Tortoise ORM** — async-native, Django-like
   - Pros: Clean async API
   - Cons: Smaller ecosystem; less tooling; weaker migration story
   - Rejected: SQLAlchemy more robust for production path
2. **Raw asyncpg** — no ORM
   - Pros: Maximum control
   - Cons: Manual query building; no migration tooling; verbose
   - Rejected: Too slow to build for 1-week timeline

---

### Decision: imagehash 4.3.2 for perceptual hashing

**Chosen:** `imagehash==4.3.2`

**Rationale:**
- Implements DCT-based pHash via `scipy.fftpack` — exactly matches spec algorithm
- `hash_size=8` produces 64-bit hash as specified
- Subtraction operator gives Hamming distance directly
- Single pip install; BSD license; no native dependencies

**Alternatives Considered:**
1. **Custom pHash implementation**
   - Pros: Full control; no dependency
   - Cons: 2-4 hours to implement and test; risk of subtle DCT bugs
   - Rejected: Library is correct and battle-tested
2. **OpenCV perceptual hash** (`cv2.img_hash`)
   - Pros: Already a dependency
   - Cons: Different hash sizes; API less clean; harder to store as bigint
   - Rejected: imagehash API cleaner for our use case

---

### Decision: OpenCV Haar Cascade for face detection

**Chosen:** OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`)

**Rationale:**
- CPU-only, no GPU required — runs on M4 Pro without Metal acceleration
- Sub-100ms per image — annotation doesn't add to the 30s SLA
- Sufficient accuracy for bounding box annotation in demo context
- Zero additional dependencies (OpenCV already required for image processing)

**Alternatives Considered:**
1. **OpenCV DNN face detector (ResNet-based)**
   - Pros: Higher accuracy (better on angled/partial faces)
   - Cons: Requires downloading external model weights; slower on CPU
   - Deferred: Good for Phase 1 if annotation quality matters
2. **face_recognition library (dlib)**
   - Pros: Very accurate
   - Cons: dlib compilation on M4 Pro is fragile; large dependency
   - Rejected: Installation risk too high for 1-week timeline

---

### Decision: Tesseract via pytesseract for text detection

**Chosen:** pytesseract (Tesseract OCR layout analysis)

**Rationale:**
- Text region bounding boxes via `image_to_data()` — returns per-word bbox
- Tesseract is pre-installed via Homebrew on Mac; Docker image available
- Gives both text content AND location — useful for CTA heuristic
- Zero model downloads needed

**Alternatives Considered:**
1. **EAST text detector (OpenCV DNN)**
   - Pros: Faster, scene-text optimised
   - Cons: Requires downloading model weights; less accurate on small text
   - Deferred: Phase 1 if text precision needed
2. **PaddleOCR**
   - Pros: State-of-art accuracy
   - Cons: Large install (~800MB); paddle framework overhead
   - Rejected: Too heavy for demo

---

### Decision: ffmpeg-python for video keyframe extraction

**Chosen:** `ffmpeg-python` wrapper library

**Rationale:**
- Clean Python API over ffmpeg subprocess — no shell injection risk
- Keyframe extraction at specific timestamps: `ffmpeg.input(path, ss=timestamp)`
- Output to PIL Image in memory without temp files
- Handles H.264/H.265 decode correctly

**Alternatives Considered:**
1. **subprocess + ffmpeg directly**
   - Pros: No extra dependency
   - Cons: Shell injection risk if path contains special chars; verbose error handling
   - Rejected: Security risk not worth the dependency savings
2. **OpenCV VideoCapture**
   - Pros: Already a dependency
   - Cons: Seeks by frame number not timestamp (fragile for variable frame rates); poor H.265 support on some platforms
   - Rejected: Timestamp-based extraction unreliable

---

### Decision: React 18 + Next.js 14 + Ant Design 5

**Chosen:** React 18 / Next.js 14 / Ant Design 5

**Rationale:**
- User preference — team comfortable with this stack
- Next.js App Router: file-based routing, no extra config
- Ant Design 5: production-quality data tables, charts (ant-design/plots), upload components — all needed for demo out of the box
- No Vuetify/Vue to avoid K4A codebase confusion (separate standalone product)

**Alternatives Considered:**
1. **Vue 3 + Vuetify** (K4A stack)
   - Pros: Matches Kochava's existing frontend stack
   - Cons: User uncomfortable with Vue; standalone product should have independent stack
   - Rejected: User preference overrides stack alignment for standalone MVP
2. **React + plain CSS**
   - Pros: Minimal dependencies
   - Cons: Building upload components, tables, charts from scratch costs 2-3 days
   - Rejected: Ant Design gives these for free

---

### Decision: Pytest + pytest-asyncio for testing

**Chosen:** pytest + pytest-asyncio + httpx (AsyncClient) + pytest-postgresql

**Rationale:**
- pytest is Python standard; async test support via pytest-asyncio
- httpx AsyncClient mounts directly to FastAPI app — no real server needed for integration tests
- pytest-postgresql spins up ephemeral Postgres for integration tests — matches spec requirement for real DB (not mocks)
- Fixtures for Ollama mock via `respx` (httpx mock library)

---

## Specification Validation

### Confirmed Assumptions

| Spec Statement | Verified By | Notes |
|---|---|---|
| pHash uses DCT, 64-bit, Hamming distance | imagehash 4.3.2 source | `imagehash.phash(img, hash_size=8)` is exactly correct |
| Qwen2-VL-7B runs on M4 Pro 24GB | Ollama docs + benchmarks | Q4 quantisation ~8GB RAM, Metal acceleration, ~20-30 tok/s |
| `pg_advisory_xact_lock` prevents duplicate race condition | PostgreSQL 15 docs | Advisory lock per hash value is the correct pattern |
| ffmpeg keyframe extraction at specific timestamps | ffmpeg-python docs | `ss` parameter seeks correctly for H.264/H.265 |
| CVPR 2017 freely downloadable | Direct verification | No registration; GCS bucket publicly readable |

### Corrected Assumptions

| Spec Statement | Actual Reality | Impact |
|---|---|---|
| "Qwen2-VL-7B" as model name | Ollama name is `qwen2.5vl:7b` | Update all config references — model name in Ollama uses `qwen2.5vl` not `qwen2-vl` |
| CVPR dataset "may require 24-48h registration" | No registration needed — direct GCS download | Reduce fallback corpus priority; still bundle for Day 1 speed |
| Video analysis "30-60 seconds total" | 3-5 keyframes × 15s each = 45-75s realistic | Pre-compute all demo video creatives; don't do live video analysis during pitch |

---

## Performance Characteristics

| Operation | Expected Latency | Notes |
|---|---|---|
| Image analysis (Qwen2-VL-7B, Q4, M4 Pro) | 10–15s | After model pre-warm |
| Video analysis (3 keyframes) | 30–45s | Too slow for live demo — pre-compute |
| pHash computation (imagehash) | < 50ms | CPU-only, negligible |
| Duplicate check (DB query) | < 10ms | Index on phash column |
| Annotation pipeline (OpenCV + Tesseract) | 200–500ms | CPU-bound, acceptable |
| Benchmark percentile lookup | < 20ms | In-memory corpus index |
| Fatigue detection (WoW calculation) | < 5ms | Pure arithmetic on time-series |

---

## Dependency List (pinned)

```txt
# Backend
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
alembic==1.13.1
asyncpg==0.29.0
pydantic==2.7.1
httpx==0.27.0
python-multipart==0.0.9

# ML / Vision
imagehash==4.3.2
Pillow==10.3.0
opencv-python==4.9.0.80
pytesseract==0.3.10
ffmpeg-python==0.2.0

# Testing
pytest==8.2.0
pytest-asyncio==0.23.6
pytest-postgresql==6.0.0
respx==0.21.1
```

---

## Open Questions

None. All technical unknowns resolved.

---

## Decision Log

| Date | Decision | Rationale | Decided By |
|---|---|---|---|
| 2026-05-14 | Python over Go | ML ecosystem fit | Architecture session |
| 2026-05-14 | Qwen2-VL over LLaVA | Better structured JSON output | Architecture session |
| 2026-05-14 | PostgreSQL over SQLite | Advisory locks required for CG-005 | Critique review |
| 2026-05-14 | React/Next.js over Vue 3 | User preference, standalone product | User decision |
| 2026-05-14 | Ollama over direct API | Data privacy + "no external API" requirement | Architecture session |
