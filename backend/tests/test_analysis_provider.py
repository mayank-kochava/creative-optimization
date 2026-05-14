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
