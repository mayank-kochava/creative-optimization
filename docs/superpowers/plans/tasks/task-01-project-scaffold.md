# Task 01: Project Scaffold

**Files to create:**
- `docker-compose.yml`
- `backend/requirements.txt`
- `backend/pytest.ini`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/Dockerfile`

---

## Step 1: Create directory structure

```bash
mkdir -p creative-optimization/{backend/app/{models,schemas,services,routers,ingestion},backend/tests,backend/scripts,backend/alembic/versions,frontend,data/{benchmark,seed,uploads}}
touch creative-optimization/backend/app/__init__.py
touch creative-optimization/backend/app/models/__init__.py
touch creative-optimization/backend/app/schemas/__init__.py
touch creative-optimization/backend/app/services/__init__.py
touch creative-optimization/backend/app/routers/__init__.py
touch creative-optimization/backend/app/ingestion/__init__.py
```

Expected: directories created, no errors.

---

## Step 2: Create `docker-compose.yml`

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: creative_opt
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppassword
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d creative_opt"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://appuser:apppassword@postgres:5432/creative_opt
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      STORAGE_PATH: /app/uploads
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/benchmark:/app/benchmark
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

---

## Step 3: Create `backend/requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
alembic==1.13.1
asyncpg==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
httpx==0.27.0
python-multipart==0.0.9
imagehash==4.3.2
Pillow==10.3.0
opencv-python==4.9.0.80
pytesseract==0.3.10
ffmpeg-python==0.2.0
numpy==1.26.4
scipy==1.13.0
pytest==8.2.0
pytest-asyncio==0.23.6
respx==0.21.1
pytest-postgresql==6.0.0
```

---

## Step 4: Create `backend/pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

---

## Step 5: Create `backend/app/config.py`

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

    class Config:
        env_file = ".env"


settings = Settings()
```

---

## Step 6: Create `backend/app/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Step 7: Create `backend/app/main.py`

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import settings
from app.routers import health, campaigns, creatives


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm Ollama on startup
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={"model": "qwen2.5vl:7b", "prompt": "hi", "stream": False},
                timeout=30,
            )
    except Exception:
        pass  # Ollama not running — degraded mode
    yield


app = FastAPI(title="Creative Intelligence Platform", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(campaigns.router)
app.include_router(creatives.router)
```

---

## Step 8: Create `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Step 8b: Create `backend/tests/conftest.py`

> **BUG FIX:** `db_session` fixture must live here so Tasks 09–15 tests can find it.
> Without this, every test using `db_session` fails with "fixture not found".

```python
# backend/tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base  # all models must be imported before create_all


TEST_DATABASE_URL = "postgresql+asyncpg://appuser:apppassword@localhost:5432/creative_opt_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Provides a transactional DB session that rolls back after each test."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("fixtures")


@pytest.fixture(scope="session")
def sample_jpg(fixtures_dir):
    path = fixtures_dir / "sample.jpg"
    img = Image.new("RGB", (300, 250), color="blue")
    draw = ImageDraw.Draw(img)
    draw.text((10, 120), "DOWNLOAD NOW", fill="white")
    draw.rectangle([20, 20, 280, 230], outline="white", width=2)
    img.save(str(path))
    return path
```

Add to `backend/app/models/__init__.py` so `Base.metadata` knows all tables:

```python
# backend/app/models/__init__.py
from app.models.campaign import Campaign          # noqa: F401
from app.models.creative import Creative          # noqa: F401
from app.models.analysis import CreativeAnalysis  # noqa: F401
from app.models.annotation import CreativeAnnotation  # noqa: F401
from app.models.duplicate import DuplicatePair    # noqa: F401
from app.models.metric import CreativeMetric      # noqa: F401
```

> **Note:** This import requires models to exist (Tasks 02+). The conftest file is created now so it's in place; the models/__init__.py is completed in Task 02.

---

## Step 9: Verify structure

```bash
cd creative-optimization
docker-compose config  # validates YAML
cd backend && python -c "from app.config import settings; print(settings.ollama_base_url)"
```

Expected: `http://localhost:11434`

---

## Step 10: Commit

```bash
git init
git add docker-compose.yml backend/
git commit -m "feat: project scaffold — FastAPI + PostgreSQL + Docker Compose"
```
