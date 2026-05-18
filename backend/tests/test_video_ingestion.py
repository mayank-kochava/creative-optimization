import os
import pytest
from pathlib import Path
from app.services.video_ingestion import VideoIngestionService, VideoMetadata


@pytest.fixture(scope="module")
def valid_video(tmp_path_factory):
    path = tmp_path_factory.mktemp("videos") / "valid_5s.mp4"
    ret = os.system(
        f"ffmpeg -f lavfi -i testsrc=duration=5:size=320x240:rate=25 "
        f"-c:v libx264 -preset ultrafast {path} -y -loglevel quiet"
    )
    assert ret == 0, "ffmpeg must be installed: brew install ffmpeg"
    return path


@pytest.fixture(scope="module")
def short_video(tmp_path_factory):
    path = tmp_path_factory.mktemp("videos") / "short_2s.mp4"
    os.system(
        f"ffmpeg -f lavfi -i testsrc=duration=2:size=320x240:rate=25 "
        f"-c:v libx264 -preset ultrafast {path} -y -loglevel quiet"
    )
    return path


@pytest.fixture(scope="module")
def svc():
    return VideoIngestionService()


def test_validate_valid_video_returns_metadata(svc, valid_video):
    meta = svc.validate_video(valid_video)
    assert isinstance(meta, VideoMetadata)
    assert meta.duration_seconds >= 5.0
    assert meta.width == 320
    assert meta.height == 240


def test_validate_short_video_raises(svc, short_video):
    with pytest.raises(ValueError, match="at least 3 seconds"):
        svc.validate_video(short_video)


def test_validate_nonexistent_file_raises(svc):
    with pytest.raises(Exception):
        svc.validate_video(Path("/nonexistent/video.mp4"))


@pytest.mark.asyncio
async def test_extract_keyframes_returns_paths(svc, valid_video):
    paths = await svc.extract_keyframes(valid_video, duration=5.0)
    assert len(paths) >= 2
    assert all(p.exists() for p in paths)
    assert all(p.suffix == ".jpg" for p in paths)
    for p in paths:
        p.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_keyframes_are_valid_images(svc, valid_video):
    from PIL import Image
    paths = await svc.extract_keyframes(valid_video, duration=5.0)
    for p in paths:
        img = Image.open(p)
        assert img.width > 0
        assert img.height > 0
    for p in paths:
        p.unlink(missing_ok=True)
