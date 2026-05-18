import asyncio
import base64
import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.analysis import AnalysisScores, DegradedAnalysisResponse, OllamaAnalysisResponse
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
