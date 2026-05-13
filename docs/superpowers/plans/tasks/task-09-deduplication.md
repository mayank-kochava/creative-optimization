# Task 09: Deduplication Service

**Files to create:**
- `backend/app/services/deduplication.py`
- `backend/tests/test_deduplication.py`

**Prereq:** Tasks 02 + 03 complete (models + migration).

---

## Step 1: Write failing tests

```python
# backend/tests/test_deduplication.py
import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.deduplication import DeduplicationService
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair


@pytest.fixture
async def dedup_service(db_session):
    return DeduplicationService(db_session)


@pytest.fixture
async def creative_in_campaign_1(db_session):
    """Insert a creative with a known phash into campaign 1."""
    creative = Creative(
        campaign_id=1, filename="a.jpg", storage_path="/tmp/a.jpg",
        format="jpg", file_size_bytes=1000, phash=0xABCDEF1234567890,
        fatigue_status="insufficient_data"
    )
    db_session.add(creative)
    await db_session.commit()
    await db_session.refresh(creative)
    return creative


@pytest.mark.asyncio
async def test_no_duplicate_returns_none(dedup_service, creative_in_campaign_1):
    result = await dedup_service.check_and_register(
        phash=0x0000000000000001,  # very different hash
        creative_id=999,
        campaign_id=1
    )
    assert result is None


@pytest.mark.asyncio
async def test_exact_duplicate_detected(dedup_service, creative_in_campaign_1):
    new_creative = Creative(
        campaign_id=1, filename="b.jpg", storage_path="/tmp/b.jpg",
        format="jpg", file_size_bytes=1000, phash=0xABCDEF1234567891,
        fatigue_status="insufficient_data"
    )
    dedup_service.db.add(new_creative)
    await dedup_service.db.commit()
    await dedup_service.db.refresh(new_creative)

    result = await dedup_service.check_and_register(
        phash=0xABCDEF1234567890,  # same as creative_in_campaign_1
        creative_id=new_creative.id,
        campaign_id=1
    )
    assert result is not None
    assert result.hamming_distance == 0
    assert result.duplicate_type == "self"


@pytest.mark.asyncio
async def test_cross_platform_duplicate_different_campaign(dedup_service, creative_in_campaign_1):
    new_creative = Creative(
        campaign_id=2, filename="c.jpg", storage_path="/tmp/c.jpg",
        format="jpg", file_size_bytes=1000, phash=0x1111111111111111,
        fatigue_status="insufficient_data"
    )
    dedup_service.db.add(new_creative)
    await dedup_service.db.commit()
    await dedup_service.db.refresh(new_creative)

    result = await dedup_service.check_and_register(
        phash=0xABCDEF1234567890,
        creative_id=new_creative.id,
        campaign_id=2  # different campaign
    )
    assert result is not None
    assert result.duplicate_type == "cross_platform"


@pytest.mark.asyncio
async def test_hamming_distance_above_threshold_returns_none(dedup_service, creative_in_campaign_1):
    # 0xABCDEF1234567890 XOR 0xFFFFFFFFFFFFFFFF = many bits different
    result = await dedup_service.check_and_register(
        phash=0xFFFFFFFFFFFFFFFF,
        creative_id=888,
        campaign_id=1
    )
    assert result is None
```

Run: `cd backend && pytest tests/test_deduplication.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/deduplication.py`

```python
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair


class DeduplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_register(
        self,
        phash: int,
        creative_id: int,
        campaign_id: int,
    ) -> DuplicatePair | None:
        """
        Check if phash is a near-duplicate of any existing creative.
        Uses pg_advisory_xact_lock to prevent race conditions on concurrent uploads.

        IMPORTANT: pg_advisory_xact_lock is transaction-level — it releases when the
        transaction ends. We wrap the entire check+insert in an explicit BEGIN so the
        lock is held for the full duration of the check.
        """
        import ctypes

        # Convert unsigned pHash to signed BIGINT range for pg_advisory_xact_lock
        # (PostgreSQL BIGINT is signed; values > 2^63-1 would be negative in two's complement)
        lock_key = ctypes.c_int64(phash).value

        async with self.db.begin():
            # Advisory lock serializes concurrent checks for the same hash bucket
            await self.db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

            # Fetch all existing creatives (phash + campaign_id)
            result = await self.db.execute(
                select(Creative.id, Creative.phash, Creative.campaign_id)
                .where(Creative.id != creative_id)
            )
            rows = result.all()

            # Find closest match within threshold
            best_match = None
            best_distance = settings.phash_duplicate_threshold + 1

            for row in rows:
                # XOR works correctly in Python for both positive and negative ints
                distance = bin(phash ^ row.phash).count("1")
                if distance <= settings.phash_duplicate_threshold and distance < best_distance:
                    best_distance = distance
                    best_match = row

            if best_match is None:
                return None

            duplicate_type = "self" if best_match.campaign_id == campaign_id else "cross_platform"

            pair = DuplicatePair(
                creative_id_a=min(creative_id, best_match.id),
                creative_id_b=max(creative_id, best_match.id),
                hamming_distance=best_distance,
                duplicate_type=duplicate_type,
            )
            self.db.add(pair)
            await self.db.flush()
            return pair
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_deduplication.py -v
```

Expected: all 4 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/deduplication.py backend/tests/test_deduplication.py
git commit -m "feat: deduplication service — pHash Hamming distance with pg_advisory_xact_lock"
```
