import asyncio
import base64
import json
from pathlib import Path
from typing import Protocol, runtime_checkable

import httpx
from pydantic import ValidationError

from app.schemas.analysis import DegradedAnalysisResponse, OllamaAnalysisResponse
from app.services.prompts import IMAGE_ANALYSIS_PROMPT, VIDEO_ANALYSIS_PROMPT


@runtime_checkable
class AnalysisProvider(Protocol):
    async def analyse_image(self, path: Path) -> "OllamaAnalysisResponse | DegradedAnalysisResponse": ...
    async def analyse_video_keyframes(self, paths: "list[Path]") -> "OllamaAnalysisResponse | DegradedAnalysisResponse": ...
    async def prewarm(self) -> None: ...


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5vl:7b"):
        self.base_url = base_url
        self.model = model

    async def prewarm(self) -> None:
        """Send dummy inference to force model memory map. First call is 30-60s cold start."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": "hi", "stream": False},
                    timeout=60,
                )
        except Exception:
            pass  # Ollama not running — will fail gracefully later

    async def analyse_image(self, path: Path) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        """Analyse an image creative. Returns validated result or DegradedAnalysisResponse after 3 retries."""
        try:
            b64 = base64.b64encode(path.read_bytes()).decode()
        except (FileNotFoundError, PermissionError, OSError):
            return DegradedAnalysisResponse()
        return await self._call_with_retry(IMAGE_ANALYSIS_PROMPT, b64)

    async def analyse_video_keyframes(self, paths: list[Path]) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        """Analyse video by sending keyframes. Averages numeric scores, uses best frame for text fields."""
        if not paths:
            return DegradedAnalysisResponse()

        results = []
        for path in paths:
            try:
                b64 = base64.b64encode(path.read_bytes()).decode()
            except (FileNotFoundError, PermissionError, OSError):
                continue
            result = await self._call_with_retry(VIDEO_ANALYSIS_PROMPT, b64)
            if result.status == "complete":
                results.append(result)

        if not results:
            return DegradedAnalysisResponse()

        # Average scores across keyframes
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

        # Use best-scoring frame for text fields
        best = max(results, key=lambda r: r.overall_score)
        from app.schemas.analysis import AnalysisScores
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

    async def _call_with_retry(
        self, prompt: str, b64_image: str, max_retries: int = 3
    ) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "images": [b64_image],
                            "stream": False,
                        },
                        timeout=60,
                    )
                resp.raise_for_status()
                resp_data = resp.json()
                raw = resp_data.get("response", "")
                if not raw:
                    raise ValueError("Empty response from Ollama")
                data = json.loads(raw)
                return OllamaAnalysisResponse(**data)
            except (json.JSONDecodeError, ValidationError, KeyError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        return DegradedAnalysisResponse()
