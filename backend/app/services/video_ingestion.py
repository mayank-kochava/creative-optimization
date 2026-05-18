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
    MIN_DURATION_SECONDS = 3.0

    def validate_video(self, path: Path) -> VideoMetadata:
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

        return VideoMetadata(duration_seconds=duration, width=width, height=height, codec=codec)

    async def extract_keyframes(self, path: Path, duration: float) -> list[Path]:
        timestamps = self._compute_timestamps(duration)
        tasks = [self._extract_frame(path, ts) for ts in timestamps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, Path) and r.exists()]

    def _compute_timestamps(self, duration: float) -> list[float]:
        timestamps = [0.0]
        if duration > 3.0:
            timestamps.append(3.0)
        if duration > 6.0:
            timestamps.append(duration * 0.5)
        if duration > 4.0:
            timestamps.append(max(duration - 1.0, timestamps[-1] + 0.5))
        return sorted(set(timestamps))

    async def _extract_frame(self, path: Path, timestamp: float) -> Path:
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
