import asyncio
import pytest
import pytest_asyncio
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
