# Task 08: Ollama Provider

**Files to create:**
- `backend/app/services/analysis_provider.py`
- `backend/tests/test_analysis_provider.py`
- `backend/tests/fixtures/sample.jpg` (created in conftest)

**Prereq:** Tasks 06 (schemas) + 07 (prompts) complete.

---

## Step 1: Create test fixtures in conftest.py

Add to `backend/tests/conftest.py` (create if not exists):

```python
# backend/tests/conftest.py
import pytest
from pathlib import Path
from PIL import Image, ImageDraw


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("fixtures")
    return d


@pytest.fixture(scope="session")
def sample_jpg(fixtures_dir):
    path = fixtures_dir / "sample.jpg"
    img = Image.new("RGB", (300, 250), color="blue")
    draw = ImageDraw.Draw(img)
    draw.text((10, 120), "DOWNLOAD NOW", fill="white")
    draw.rectangle([20, 20, 280, 230], outline="white", width=2)
    img.save(str(path))
    return path
```

---

## Step 2: Write failing tests

```python
# backend/tests/test_analysis_provider.py
import json
import pytest
import respx
import httpx
from pathlib import Path
from app.services.analysis_provider import OllamaProvider


MOCK_VALID_RESPONSE = {
    "response": json.dumps({
        "scores": {"hook_strength": 8, "cta_clarity": 7, "visual_quality": 9,
                   "message_clarity": 7, "emotional_resonance": 8, "social_proof": 4,
                   "brand_consistency": 6},
        "overall_score": 7,
        "persuasion_strategy": "aspirational",
        "dominant_emotion": "excitement",
        "strengths": ["Strong visual", "Clear CTA"],
        "weaknesses": ["No social proof"],
        "recommendations": ["Add testimonials", "Boost contrast", "Simplify message"],
        "explanation": "Effective aspirational creative."
    })
}


@pytest.mark.asyncio
async def test_analyse_image_returns_validated_result(sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json=MOCK_VALID_RESPONSE)
        )
        provider = OllamaProvider(base_url="http://localhost:11434")
        result = await provider.analyse_image(sample_jpg)

    assert result.scores.hook_strength == 8
    assert len(result.recommendations) == 3
    assert result.status == "complete"


@pytest.mark.asyncio
async def test_retries_on_invalid_json(sample_jpg):
    bad_response = {"response": "not valid json {{{{"}
    calls = 0

    with respx.mock:
        def side_effect(request):
            nonlocal calls
            calls += 1
            if calls < 3:
                return httpx.Response(200, json=bad_response)
            return httpx.Response(200, json=MOCK_VALID_RESPONSE)

        respx.post("http://localhost:11434/api/generate").mock(side_effect=side_effect)
        provider = OllamaProvider(base_url="http://localhost:11434")
        result = await provider.analyse_image(sample_jpg)

    assert calls == 3
    assert result.status == "complete"


@pytest.mark.asyncio
async def test_returns_degraded_after_3_failures(sample_jpg):
    bad_response = {"response": "{{invalid}}"}
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json=bad_response)
        )
        provider = OllamaProvider(base_url="http://localhost:11434")
        result = await provider.analyse_image(sample_jpg)

    assert result.status == "degraded"
    assert result.overall_score == 0
    assert len(result.recommendations) == 3


@pytest.mark.asyncio
async def test_prewarm_does_not_raise_on_connection_error():
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.ConnectError("Ollama not running")
        )
        provider = OllamaProvider(base_url="http://localhost:11434")
        # Should not raise
        await provider.prewarm()
```

Run: `cd backend && pytest tests/test_analysis_provider.py -v`
Expected: FAIL — module not found.

---

## Step 3: Create `backend/app/services/analysis_provider.py`

```python
import asyncio
import base64
import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.schemas.analysis import DegradedAnalysisResponse, OllamaAnalysisResponse
from app.services.prompts import IMAGE_ANALYSIS_PROMPT, VIDEO_ANALYSIS_PROMPT


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
        b64 = base64.b64encode(path.read_bytes()).decode()
        return await self._call_with_retry(IMAGE_ANALYSIS_PROMPT, b64)

    async def analyse_video_keyframes(self, paths: list[Path]) -> OllamaAnalysisResponse | DegradedAnalysisResponse:
        """Analyse video by sending keyframes. Averages numeric scores, uses best frame for text fields."""
        if not paths:
            return DegradedAnalysisResponse()

        results = []
        for path in paths:
            b64 = base64.b64encode(path.read_bytes()).decode()
            result = await self._call_with_retry(VIDEO_ANALYSIS_PROMPT, b64)
            if result.status == "complete":
                results.append(result)

        if not results:
            return DegradedAnalysisResponse()

        # Average scores across keyframes
        score_fields = ["hook_strength", "cta_clarity", "visual_quality", "message_clarity",
                        "emotional_resonance", "social_proof", "brand_consistency"]
        averaged_scores = {}
        for field in score_fields:
            averaged_scores[field] = round(
                sum(getattr(r.scores, field) for r in results) / len(results)
            )

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
                raw = resp.json()["response"]
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
```

---

## Step 4: Run tests

```bash
cd backend && pytest tests/test_analysis_provider.py -v
```

Expected: all 4 tests PASS.

---

## Step 5: Manual smoke test (requires Ollama running)

```bash
ollama list  # verify qwen2.5vl:7b is present
python -c "
import asyncio
from pathlib import Path
from app.services.analysis_provider import OllamaProvider
async def main():
    p = OllamaProvider()
    await p.prewarm()
    result = await p.analyse_image(Path('data/seed/sample.jpg'))
    print(result.overall_score, result.persuasion_strategy)
asyncio.run(main())
"
```

Expected: prints score integer and strategy string.

---

## Step 6: Commit

```bash
git add backend/app/services/analysis_provider.py backend/tests/
git commit -m "feat: Ollama provider — base64 encode, 3-retry, degraded fallback, video keyframe merging"
```
