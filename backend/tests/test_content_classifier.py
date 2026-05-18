import pytest
import respx
import httpx
from pathlib import Path
from app.services.content_classifier import ContentClassifier
from app.services.analysis_provider import OllamaProvider


@pytest.fixture
def provider():
    return OllamaProvider(base_url="http://localhost:11434")


@pytest.fixture
def classifier(provider):
    return ContentClassifier(provider)


@pytest.mark.asyncio
async def test_yes_response_returns_true(classifier, sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "YES"})
        )
        result = await classifier.is_advertisement(sample_jpg)
    assert result is True


@pytest.mark.asyncio
async def test_no_response_returns_false(classifier, sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "NO"})
        )
        result = await classifier.is_advertisement(sample_jpg)
    assert result is False


@pytest.mark.asyncio
async def test_connection_error_defaults_to_true(classifier, sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            side_effect=httpx.ConnectError("Ollama offline")
        )
        result = await classifier.is_advertisement(sample_jpg)
    assert result is True


@pytest.mark.asyncio
async def test_ambiguous_response_defaults_to_true(classifier, sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "I'm not sure"})
        )
        result = await classifier.is_advertisement(sample_jpg)
    assert result is True
