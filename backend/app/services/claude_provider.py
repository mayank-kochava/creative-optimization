import asyncio
import base64
import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.analysis import AnalysisScores, DegradedAnalysisResponse, OllamaAnalysisResponse
import logging

from app.services.prompts import IMAGE_ANALYSIS_PROMPT, VIDEO_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


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
        logger.info("Image analysis started — %s", path.name)
        try:
            raw_bytes = path.read_bytes()
        except (FileNotFoundError, PermissionError, OSError):
            logger.warning("Image not readable: %s", path)
            return DegradedAnalysisResponse()

        suffix = path.suffix.lower().lstrip(".")
        media_type = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp", "gif": "image/gif",
        }.get(suffix, "image/jpeg")

        b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")

        for attempt in range(3):
            try:
                logger.info("Claude image analysis attempt %d — %s", attempt + 1, path.name)
                message = await asyncio.to_thread(
                    self._client.messages.create,
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
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(raw)
                result = OllamaAnalysisResponse(**data)
                logger.info("Image analysis complete — %s score: %s", path.name, result.overall_score)
                return result
            except (json.JSONDecodeError, ValidationError, KeyError, IndexError) as e:
                logger.warning("Image analysis parse error attempt %d: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
                if attempt == 2:
                    return DegradedAnalysisResponse()
            except Exception as e:
                logger.warning("Image analysis error attempt %d: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
                if attempt == 2:
                    return DegradedAnalysisResponse()

        return DegradedAnalysisResponse()

    async def analyse_video_keyframes(self, paths: list[Path]) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        if not paths:
            return DegradedAnalysisResponse()

        logger.info("Analysing video: %d keyframes", len(paths))

        content: list[dict] = []
        for i, path in enumerate(paths):
            try:
                raw_bytes = path.read_bytes()
            except (FileNotFoundError, PermissionError, OSError):
                continue
            b64 = base64.standard_b64encode(raw_bytes).decode("utf-8")
            content.append({"type": "text", "text": f"Keyframe {i + 1} of {len(paths)}:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })

        if not content:
            return DegradedAnalysisResponse()

        content.append({"type": "text", "text": VIDEO_ANALYSIS_PROMPT})

        for attempt in range(3):
            try:
                logger.info("Claude video analysis attempt %d", attempt + 1)
                message = await asyncio.to_thread(
                    self._client.messages.create,
                    model=CLAUDE_MODEL,
                    max_tokens=1024,
                    system=_SYSTEM,
                    messages=[{"role": "user", "content": content}],
                )
                raw = message.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(raw)
                result = OllamaAnalysisResponse(**data)
                logger.info("Video analysis complete — overall score: %s", result.overall_score)
                return result
            except (json.JSONDecodeError, ValidationError, KeyError, IndexError) as e:
                logger.warning("Video analysis parse error attempt %d: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
                if attempt == 2:
                    return DegradedAnalysisResponse()
            except Exception as e:
                logger.warning("Video analysis error attempt %d: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
                if attempt == 2:
                    return DegradedAnalysisResponse()

        return DegradedAnalysisResponse()
