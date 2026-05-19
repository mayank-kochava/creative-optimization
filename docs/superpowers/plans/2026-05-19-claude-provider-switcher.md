# Claude Provider Switcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Claude Sonnet 4.6 as an analysis provider alongside Qwen/Ollama, with a frontend badge in the header showing the active model and a click-to-switch modal.

**Architecture:** A `ClaudeProvider` class implementing the same `analyse_image`/`analyse_video_keyframes` interface as `OllamaProvider`. Active provider stored in a module-level singleton in a new `provider_state.py` module, toggled via `GET/POST /api/provider`. Frontend header badge reads active provider and opens a switch modal.

**Tech Stack:** Python `anthropic` SDK (messages API + vision), FastAPI, React 18 / Next.js 14, custom CSS design system.

---

## File Map

**Create:**
- `backend/app/services/claude_provider.py` — ClaudeProvider class
- `backend/app/services/provider_state.py` — module-level active provider singleton + factory
- `backend/app/routers/provider.py` — GET/POST /provider endpoints
- `frontend/src/components/ProviderBadge.tsx` — header badge + switch modal

**Modify:**
- `backend/app/services/analysis_provider.py` — extract shared `AnalysisProvider` protocol
- `backend/app/config.py` — add `anthropic_api_key`, `analysis_provider` fields
- `backend/app/routers/creatives.py` — use `get_active_provider()` instead of hardcoded `OllamaProvider`
- `backend/app/main.py` — register provider router, update lifespan prewarm
- `backend/requirements.txt` — add `anthropic`
- `frontend/src/app/AppHeader.tsx` — embed ProviderBadge
- `frontend/src/lib/api.ts` — add `getProvider`, `setProvider` calls

---

### Task 1: Add `anthropic` dependency + config fields

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add anthropic to requirements**

Open `backend/requirements.txt` and add after the `httpx` line:
```
anthropic>=0.40.0
```

- [ ] **Step 2: Add config fields**

Replace `backend/app/config.py` with:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt"
    ollama_base_url: str = "http://localhost:11434"
    storage_path: str = "/tmp/uploads"
    max_image_size_bytes: int = 20 * 1024 * 1024
    max_video_size_bytes: int = 500 * 1024 * 1024
    phash_duplicate_threshold: int = 10
    benchmark_corpus_path: str = "data/benchmark/corpus.json"
    anthropic_api_key: str = ""
    analysis_provider: str = "claude"  # "claude" | "ollama"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 3: Install dependency**

```bash
cd backend && pip install anthropic>=0.40.0
```

Expected: `Successfully installed anthropic-...`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat(provider): add anthropic dependency and config fields"
```

---

### Task 2: Add `AnalysisProvider` protocol to `analysis_provider.py`

**Files:**
- Modify: `backend/app/services/analysis_provider.py`

- [ ] **Step 1: Add Protocol at top of file**

Add after the imports at the top of `backend/app/services/analysis_provider.py`:
```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class AnalysisProvider(Protocol):
    async def analyse_image(self, path: Path) -> "OllamaAnalysisResponse | DegradedAnalysisResponse": ...
    async def analyse_video_keyframes(self, paths: "list[Path]") -> "OllamaAnalysisResponse | DegradedAnalysisResponse": ...
    async def prewarm(self) -> None: ...
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd backend && python3.11 -m pytest -v -x 2>&1 | tail -20
```

Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analysis_provider.py
git commit -m "feat(provider): add AnalysisProvider protocol"
```

---

### Task 3: Implement `ClaudeProvider`

**Files:**
- Create: `backend/app/services/claude_provider.py`

- [ ] **Step 1: Create the file**

Create `backend/app/services/claude_provider.py`:

```python
import base64
import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.analysis import DegradedAnalysisResponse, OllamaAnalysisResponse, AnalysisScores
from app.services.prompts import IMAGE_ANALYSIS_PROMPT


CLAUDE_MODEL = "claude-sonnet-4-6"

_SYSTEM = (
    "You are an expert advertising analyst. "
    "Always respond with valid JSON only — no markdown, no explanation outside the JSON."
)


class ClaudeProvider:
    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    async def prewarm(self) -> None:
        pass  # Claude API has no cold start

    async def analyse_image(self, path: Path) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        try:
            raw_bytes = path.read_bytes()
        except (FileNotFoundError, PermissionError, OSError):
            return DegradedAnalysisResponse()

        suffix = path.suffix.lower().lstrip(".")
        media_type = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp", "gif": "image/gif",
        }.get(suffix, "image/jpeg")

        b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")

        for attempt in range(3):
            try:
                message = self._client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=1024,
                    system=_SYSTEM,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": b64,
                                    },
                                },
                                {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                            ],
                        }
                    ],
                )
                raw = message.content[0].text.strip()
                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(raw)
                return OllamaAnalysisResponse(**data)
            except (json.JSONDecodeError, ValidationError, KeyError, IndexError):
                if attempt == 2:
                    return DegradedAnalysisResponse()
            except Exception:
                if attempt == 2:
                    return DegradedAnalysisResponse()

        return DegradedAnalysisResponse()

    async def analyse_video_keyframes(self, paths: list[Path]) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        if not paths:
            return DegradedAnalysisResponse()

        results = []
        for path in paths:
            result = await self.analyse_image(path)
            if result.status == "complete":
                results.append(result)

        if not results:
            return DegradedAnalysisResponse()

        score_fields = [
            "hook_strength", "cta_clarity", "visual_quality", "message_clarity",
            "emotional_resonance", "social_proof", "brand_consistency",
        ]
        averaged_scores = {}
        for field in score_fields:
            try:
                averaged_scores[field] = round(
                    sum(getattr(r.scores, field) for r in results) / len(results)
                )
            except (AttributeError, ZeroDivisionError):
                averaged_scores[field] = 0

        best = max(results, key=lambda r: r.overall_score)
        merged_scores = AnalysisScores(**averaged_scores)

        return OllamaAnalysisResponse(
            scores=merged_scores,
            overall_score=merged_scores.average(),
            persuasion_strategy=best.persuasion_strategy,
            dominant_emotion=best.dominant_emotion,
            strengths=best.strengths,
            weaknesses=best.weaknesses,
            recommendations=best.recommendations,
            explanation=f"(Video analysis across {len(results)} keyframes) {best.explanation}",
        )
```

- [ ] **Step 2: Verify import works**

```bash
cd backend && python3.11 -c "from app.services.claude_provider import ClaudeProvider; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/claude_provider.py
git commit -m "feat(provider): implement ClaudeProvider with claude-sonnet-4-6"
```

---

### Task 4: Create `provider_state.py` — active provider singleton

**Files:**
- Create: `backend/app/services/provider_state.py`

- [ ] **Step 1: Create the file**

Create `backend/app/services/provider_state.py`:

```python
from app.config import settings
from app.services.analysis_provider import OllamaProvider
from app.services.claude_provider import ClaudeProvider

# Valid provider names
PROVIDERS = ("claude", "ollama")

# Active provider name — reads default from config on startup
_active: str = settings.analysis_provider if settings.analysis_provider in PROVIDERS else "claude"


def get_active_name() -> str:
    return _active


def set_active(name: str) -> None:
    global _active
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Valid: {PROVIDERS}")
    _active = name


def get_active_provider() -> OllamaProvider | ClaudeProvider:
    if _active == "claude":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        return ClaudeProvider(api_key=settings.anthropic_api_key)
    return OllamaProvider(base_url=settings.ollama_base_url)
```

- [ ] **Step 2: Verify**

```bash
cd backend && python3.11 -c "
from app.services.provider_state import get_active_name, get_active_provider
print('active:', get_active_name())
p = get_active_provider()
print('provider type:', type(p).__name__)
"
```

Expected:
```
active: claude
provider type: ClaudeProvider
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/provider_state.py
git commit -m "feat(provider): add provider_state singleton with get/set active provider"
```

---

### Task 5: Provider API endpoints

**Files:**
- Create: `backend/app/routers/provider.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create provider router**

Create `backend/app/routers/provider.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.provider_state import PROVIDERS, get_active_name, set_active

router = APIRouter()


class ProviderStatus(BaseModel):
    active: str
    available: list[str]


class SetProviderRequest(BaseModel):
    provider: str


@router.get("/provider", response_model=ProviderStatus)
async def get_provider():
    return ProviderStatus(active=get_active_name(), available=list(PROVIDERS))


@router.post("/provider", response_model=ProviderStatus)
async def set_provider(body: SetProviderRequest):
    try:
        set_active(body.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ProviderStatus(active=get_active_name(), available=list(PROVIDERS))
```

- [ ] **Step 2: Register router in main.py**

In `backend/app/main.py`, add provider router import and registration:

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import settings
from app.routers import health, campaigns, creatives
from app.routers.provider import router as provider_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only prewarm Ollama if that's the active provider
    from app.services.provider_state import get_active_name
    if get_active_name() == "ollama":
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": "qwen2.5vl:7b", "prompt": "hi", "stream": False},
                    timeout=30,
                )
        except Exception:
            pass
    yield


app = FastAPI(title="Creative Intelligence Platform", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(creatives.router)
app.include_router(provider_router)
```

- [ ] **Step 3: Verify endpoint responds**

```bash
cd backend && uvicorn app.main:app --port 8001 --no-access-log &
sleep 3
curl -s http://localhost:8001/provider | python3 -m json.tool
kill %1
```

Expected:
```json
{
    "active": "claude",
    "available": ["claude", "ollama"]
}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/provider.py backend/app/main.py
git commit -m "feat(provider): add GET/POST /provider endpoints"
```

---

### Task 6: Wire `creatives.py` router to use active provider

**Files:**
- Modify: `backend/app/routers/creatives.py`

- [ ] **Step 1: Replace hardcoded OllamaProvider singleton**

In `backend/app/routers/creatives.py`, replace the top section (lines 1–48) with:

```python
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.ingestion.orchestrator import CreativeIngestionOrchestrator, IngestionResult
from app.models.analysis import CreativeAnalysis
from app.models.annotation import CreativeAnnotation
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair
from app.models.metric import CreativeMetric
from app.schemas.analysis import AnnotationResponse, BBoxResponse
from app.schemas.analysis import KPISummary as KPISummarySchema
from app.schemas.analysis import OllamaAnalysisResponse
from app.schemas.creative import CreativeDetail, UploadResponse
from app.services.annotation_pipeline import AnnotationPipeline
from app.services.content_classifier import ContentClassifier
from app.services.deduplication import DeduplicationService
from app.services.fatigue_detector import FatigueDetector
from app.services.kpi_aggregator import KPIAggregator
from app.services.provider_state import get_active_provider
from app.services.video_ingestion import VideoIngestionService

router = APIRouter()

_annotation_pipeline = AnnotationPipeline()
_video_service = VideoIngestionService()


def get_orchestrator(db: AsyncSession) -> CreativeIngestionOrchestrator:
    """Return a new orchestrator bound to the given db session, using the active provider."""
    provider = get_active_provider()
    return CreativeIngestionOrchestrator(
        db=db,
        analysis_provider=provider,
        dedup_service=DeduplicationService(db),
        annotation_pipeline=_annotation_pipeline,
        video_service=_video_service,
        content_classifier=ContentClassifier(provider),
        fatigue_detector=FatigueDetector(db),
    )
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python3.11 -m pytest -v -x 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/creatives.py
git commit -m "feat(provider): wire creatives router to use active provider from provider_state"
```

---

### Task 7: Frontend — `ProviderBadge` component

**Files:**
- Create: `frontend/src/components/ProviderBadge.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/AppHeader.tsx`

- [ ] **Step 1: Add API calls to `api.ts`**

In `frontend/src/lib/api.ts`, add the `ProviderStatus` interface and two API calls at the end:

```typescript
export interface ProviderStatus {
  active: 'claude' | 'ollama';
  available: string[];
}
```

And inside the `api` object, add:
```typescript
  getProvider: (): Promise<ProviderStatus> =>
    client.get('/provider').then(r => r.data),

  setProvider: (provider: string): Promise<ProviderStatus> =>
    client.post('/provider', { provider }).then(r => r.data),
```

- [ ] **Step 2: Create `ProviderBadge.tsx`**

Create `frontend/src/components/ProviderBadge.tsx`:

```tsx
'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { api } from '@/lib/api';

const LABELS: Record<string, string> = {
  claude: 'Claude Sonnet 4.6',
  ollama: 'Qwen2.5-VL (Local)',
};

const ICONS: Record<string, string> = {
  claude: '◆',
  ollama: '⬡',
};

export function ProviderBadge() {
  const { data, mutate } = useSWR('provider', () => api.getProvider(), {
    refreshInterval: 0,
  });
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  if (!data) return null;

  const handleSwitch = async (name: string) => {
    if (name === data.active) { setOpen(false); return; }
    setSwitching(true);
    try {
      const updated = await api.setProvider(name);
      await mutate(updated, false);
    } finally {
      setSwitching(false);
      setOpen(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 20,
          border: '1px solid var(--border)',
          background: 'var(--surface)', cursor: 'pointer',
          fontSize: 12, color: 'var(--text-2)',
          fontFamily: 'inherit',
        }}
      >
        <span style={{ color: data.active === 'claude' ? '#7B61FF' : '#27AE60', fontSize: 10 }}>
          {ICONS[data.active] ?? '●'}
        </span>
        {LABELS[data.active] ?? data.active}
        <span style={{ fontSize: 9, opacity: 0.6 }}>▾</span>
      </button>

      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 99 }}
          />
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', right: 0,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 10, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            minWidth: 200, zIndex: 100, overflow: 'hidden',
          }}>
            <div style={{ padding: '8px 12px 6px', fontSize: 11, color: 'var(--text-2)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Analysis Model
            </div>
            {data.available.map(name => (
              <button
                key={name}
                disabled={switching}
                onClick={() => handleSwitch(name)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  width: '100%', padding: '8px 12px',
                  border: 'none', background: name === data.active ? 'var(--bg)' : 'transparent',
                  cursor: 'pointer', fontSize: 13, color: 'var(--text)',
                  fontFamily: 'inherit', textAlign: 'left',
                }}
              >
                <span style={{ color: name === 'claude' ? '#7B61FF' : '#27AE60', fontSize: 12 }}>
                  {ICONS[name] ?? '●'}
                </span>
                <div>
                  <div style={{ fontWeight: name === data.active ? 600 : 400 }}>
                    {LABELS[name] ?? name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)' }}>
                    {name === 'claude' ? 'Anthropic API' : 'Local Ollama'}
                  </div>
                </div>
                {name === data.active && (
                  <span style={{ marginLeft: 'auto', color: 'var(--primary)', fontSize: 12 }}>✓</span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add `ProviderBadge` to `AppHeader.tsx`**

Replace `frontend/src/app/AppHeader.tsx` with:

```tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ProviderBadge } from '@/components/ProviderBadge';

export default function AppHeader() {
  const path = usePathname();
  return (
    <header className="hdr">
      <Link href="/" className="logo">
        <div className="logo-orb">✦</div>
        Creative Intelligence
      </Link>
      <nav className="hdr-nav">
        <Link href="/" className={`nav-btn${path === '/' ? ' on' : ''}`}>Dashboard</Link>
        <Link href="/campaigns" className={`nav-btn${path.startsWith('/campaigns') ? ' on' : ''}`}>Campaigns</Link>
        <Link href="/performance" className={`nav-btn${path === '/performance' ? ' on' : ''}`}>Performance</Link>
      </nav>
      <ProviderBadge />
    </header>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProviderBadge.tsx frontend/src/lib/api.ts frontend/src/app/AppHeader.tsx
git commit -m "feat(provider): add ProviderBadge to header with click-to-switch modal"
```

---

### Task 8: Truncate fake analyses + run precompute with Claude

**Files:**
- No code changes — data migration only.

- [ ] **Step 1: Restart backend so new provider config is loaded**

```bash
# Kill existing uvicorn if running locally, or restart docker service
docker-compose restart backend 2>/dev/null || pkill -f "uvicorn app.main" && sleep 2 && cd backend && uvicorn app.main:app --reload --port 8000 &
sleep 3
curl -s http://localhost:8000/provider | python3 -m json.tool
```

Expected: `"active": "claude"`

- [ ] **Step 2: Truncate synthetic analyses and annotations**

```bash
docker exec $(docker ps -q --filter "name=postgres") psql -U appuser -d creative_opt \
  -c "TRUNCATE creative_analyses, creative_annotations RESTART IDENTITY;"
```

Expected: `TRUNCATE TABLE`

- [ ] **Step 3: Run precompute with Claude**

```bash
cd backend && python scripts/precompute_analysis.py
```

This analyses all 50 creatives. Expected output:
```
Pre-warming Ollama model qwen2.5vl:7b...   ← skipped if Claude active
Found 50 creatives without analysis.
[1/50] Creative #1: creative_f4e8p3en.jpg
  ✓ Analysis complete (score: 7.2)
[2/50] ...
```

Wait for completion (~2–3 min for 50 images via Claude API).

- [ ] **Step 4: Verify in DB**

```bash
docker exec $(docker ps -q --filter "name=postgres") psql -U appuser -d creative_opt \
  -c "SELECT status, count(*) FROM creative_analyses GROUP BY status;"
```

Expected:
```
  status  | count
----------+-------
 complete |    50
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(provider): truncate synthetic analyses, re-seeded with Claude Sonnet 4.6"
```

---

## Self-Review

**Spec coverage:**
- ✅ ClaudeProvider — Task 3
- ✅ GET/POST /provider endpoints — Task 5
- ✅ Frontend badge in header — Task 7
- ✅ Click-to-switch modal — Task 7 (ProviderBadge)
- ✅ anthropic in requirements — Task 1
- ✅ Truncate + recompute — Task 8
- ✅ New uploads use active provider — Task 6

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:**
- `ProviderStatus` defined in Task 5 (Python) and Task 7 (TypeScript) — field names match (`active`, `available`)
- `get_active_provider()` defined in Task 4, used in Task 6 — signature consistent
- `ClaudeProvider.analyse_image` / `analyse_video_keyframes` match `OllamaProvider` signatures exactly
