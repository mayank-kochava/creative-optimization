import ctypes

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
        transaction ends. We execute directly on the session (no nested begin) because
        the caller's transaction is already active.
        """
        # Convert unsigned pHash to signed BIGINT range for pg_advisory_xact_lock
        # (PostgreSQL BIGINT is signed; values > 2^63-1 would be negative in two's complement)
        lock_key = ctypes.c_int64(phash).value

        # Advisory lock serializes concurrent checks for the same hash bucket
        await self.db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

        # Fetch all existing creatives (phash + campaign_id) except the current one
        result = await self.db.execute(
            select(Creative.id, Creative.phash, Creative.campaign_id)
            .where(Creative.id != creative_id)
        )
        rows = result.all()

        # Find closest match within threshold
        best_match = None
        best_distance = settings.phash_duplicate_threshold + 1

        for row in rows:
            # Mask to 64 bits before bin() — Python bin(-n) uses sign-magnitude, not
            # two's complement, so negative XOR results give wrong popcount without mask.
            distance = bin((phash ^ row.phash) & 0xFFFFFFFFFFFFFFFF).count("1")
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
