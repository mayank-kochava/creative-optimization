# Task 14: Video Ingestion Service

**Files to create:**
- `backend/app/services/video_ingestion.py`
- `backend/tests/test_video_ingestion.py`

**Prereq:** ffmpeg installed: `brew install ffmpeg`. Task 01 complete.

---

## Step 1: Write failing tests

```python
# backend/tests/test_video_ingestion.py
import os
import pytest
from pathlib import Path
from app.services.video_ingestion import VideoIngestionService, VideoMetadata


@pytest.fixture(scope="module")
def valid_video(tmp_path_factory):
    """Generate a 5-second H.264 test video using ffmpeg."""
    path = tmp_path_factory.mktemp("videos") / "valid_5s.mp4"
    ret = os.system(
        f"ffmpeg -f lavfi -i testsrc=duration=5:size=320x240:rate=25 "
        f"-c:v libx264 -preset ultrafast {path} -y -loglevel quiet"
    )
    assert ret == 0, "ffmpeg must be installed: brew install ffmpeg"
    return path


@pytest.fixture(scope="module")
def short_video(tmp_path_factory):
    """Generate a 2-second video (below 3s minimum)."""
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
    # cleanup
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
```

Run: `cd backend && pytest tests/test_video_ingestion.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/video_ingestion.py`

```python
import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path

import ffmpeg


@dataclass
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    codec: str


class VideoIngestionService:
    SUPPORTED_CODECS = {"h264", "hevc", "h265"}
    MIN_DURATION_SECONDS = 3.0

    def validate_video(self, path: Path) -> VideoMetadata:
        """Probe video file and validate format. Raises ValueError on invalid video."""
        try:
            probe = ffmpeg.probe(str(path))
        except ffmpeg.Error as e:
            raise ValueError(f"Cannot read video file: {e}") from e

        video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
        if not video_streams:
            raise ValueError("No video stream found")

        stream = video_streams[0]
        codec = stream.get("codec_name", "").lower()
        duration = float(probe["format"].get("duration", 0))
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))

        if duration < self.MIN_DURATION_SECONDS:
            raise ValueError(f"Video must be at least 3 seconds (got {duration:.1f}s)")

        return VideoMetadata(
            duration_seconds=duration,
            width=width,
            height=height,
            codec=codec,
        )

    async def extract_keyframes(self, path: Path, duration: float) -> list[Path]:
        """
        Extract keyframes at 0s, 3s, 50% through, and end-1s.
        Returns list of temp JPEG paths. Caller must delete after use.
        """
        timestamps = self._compute_timestamps(duration)
        tasks = [self._extract_frame(path, ts) for ts in timestamps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, Path) and r.exists()]

    def _compute_timestamps(self, duration: float) -> list[float]:
        """Compute up to 4 evenly spaced timestamps."""
        timestamps = [0.0]
        if duration > 3.0:
            timestamps.append(3.0)
        if duration > 6.0:
            timestamps.append(duration * 0.5)
        if duration > 4.0:
            timestamps.append(max(duration - 1.0, timestamps[-1] + 0.5))
        return sorted(set(timestamps))

    async def _extract_frame(self, path: Path, timestamp: float) -> Path:
        """Extract single frame at timestamp to a temp JPEG file."""
        output_path = Path(f"/tmp/keyframe_{uuid.uuid4().hex}_{timestamp:.1f}.jpg")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._extract_frame_sync, path, timestamp, output_path)
        return output_path

    def _extract_frame_sync(self, path: Path, timestamp: float, output_path: Path) -> None:
        (
            ffmpeg
            .input(str(path), ss=timestamp)
            .output(str(output_path), vframes=1, format="image2", vcodec="mjpeg")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_video_ingestion.py -v
```

Expected: all 5 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/video_ingestion.py backend/tests/test_video_ingestion.py
git commit -m "feat: video ingestion — ffmpeg probe validation + timestamp-based keyframe extraction"
```
