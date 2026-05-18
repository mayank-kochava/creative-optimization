import ctypes
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deduplication import DeduplicationService
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.duplicate import DuplicatePair


def s64(v: int) -> int:
    return ctypes.c_int64(v).value


@pytest_asyncio.fixture
async def campaigns(db_session):
    c1 = Campaign(name="Dedup Campaign 1")
    c2 = Campaign(name="Dedup Campaign 2")
    db_session.add(c1)
    db_session.add(c2)
    await db_session.flush()
    await db_session.refresh(c1)
    await db_session.refresh(c2)
    return c1, c2


@pytest_asyncio.fixture
async def dedup_service(db_session):
    return DeduplicationService(db_session)


@pytest_asyncio.fixture
async def creative_in_campaign_1(db_session, campaigns):
    c1, _ = campaigns
    creative = Creative(
        campaign_id=c1.id, filename="a.jpg", storage_path="/tmp/a.jpg",
        format="jpg", file_size_bytes=1000, phash=s64(0xABCDEF1234567890),
        fatigue_status="insufficient_data"
    )
    db_session.add(creative)
    await db_session.flush()
    await db_session.refresh(creative)
    return creative


@pytest.mark.asyncio
async def test_no_duplicate_returns_none(dedup_service, creative_in_campaign_1, campaigns):
    c1, _ = campaigns
    result = await dedup_service.check_and_register(
        phash=s64(0x0000000000000001),
        creative_id=creative_in_campaign_1.id + 9000,
        campaign_id=c1.id,
    )
    assert result is None


@pytest.mark.asyncio
async def test_exact_duplicate_detected(dedup_service, creative_in_campaign_1, campaigns):
    c1, _ = campaigns
    new_creative = Creative(
        campaign_id=c1.id, filename="b.jpg", storage_path="/tmp/b.jpg",
        format="jpg", file_size_bytes=1000, phash=s64(0xABCDEF1234567891),
        fatigue_status="insufficient_data"
    )
    dedup_service.db.add(new_creative)
    await dedup_service.db.flush()
    await dedup_service.db.refresh(new_creative)

    result = await dedup_service.check_and_register(
        phash=s64(0xABCDEF1234567890),
        creative_id=new_creative.id,
        campaign_id=c1.id,
    )
    assert result is not None
    assert result.hamming_distance == 0
    assert result.duplicate_type == "self"


@pytest.mark.asyncio
async def test_cross_platform_duplicate_different_campaign(dedup_service, creative_in_campaign_1, campaigns):
    c1, c2 = campaigns
    new_creative = Creative(
        campaign_id=c2.id, filename="c.jpg", storage_path="/tmp/c.jpg",
        format="jpg", file_size_bytes=1000, phash=s64(0x1111111111111111),
        fatigue_status="insufficient_data"
    )
    dedup_service.db.add(new_creative)
    await dedup_service.db.flush()
    await dedup_service.db.refresh(new_creative)

    result = await dedup_service.check_and_register(
        phash=s64(0xABCDEF1234567890),
        creative_id=new_creative.id,
        campaign_id=c2.id,
    )
    assert result is not None
    assert result.duplicate_type == "cross_platform"


@pytest.mark.asyncio
async def test_hamming_distance_above_threshold_returns_none(dedup_service, creative_in_campaign_1, campaigns):
    c1, _ = campaigns
    result = await dedup_service.check_and_register(
        phash=s64(0xFFFFFFFFFFFFFFFF),
        creative_id=creative_in_campaign_1.id + 9001,
        campaign_id=c1.id,
    )
    assert result is None
