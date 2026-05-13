# Task 10: Content Classifier

**Files to create:**
- `backend/app/services/content_classifier.py`
- `backend/tests/test_content_classifier.py`

**Prereq:** Task 08 (Ollama provider) complete.

---

## Step 1: Write failing tests

```python
# backend/tests/test_content_classifier.py
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
    assert result is True  # fail open — don't block uploads if Ollama down


@pytest.mark.asyncio
async def test_ambiguous_response_defaults_to_true(classifier, sample_jpg):
    with respx.mock:
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "I'm not sure"})
        )
        result = await classifier.is_advertisement(sample_jpg)
    assert result is True
```

Run: `cd backend && pytest tests/test_content_classifier.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/content_classifier.py`

```python
import base64
from pathlib import Path

import httpx

from app.services.prompts import CONTENT_CLASSIFIER_PROMPT


class ContentClassifier:
    def __init__(self, provider):
        self.provider = provider

    async def is_advertisement(self, image_path: Path) -> bool:
        """
        Returns True if the image is an advertisement creative.
        Defaults to True on any error (fail open — don't block uploads).
        """
        try:
            b64 = base64.b64encode(image_path.read_bytes()).decode()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.provider.base_url}/api/generate",
                    json={
                        "model": self.provider.model,
                        "prompt": CONTENT_CLASSIFIER_PROMPT,
                        "images": [b64],
                        "stream": False,
                    },
                    timeout=30,
                )
            resp.raise_for_status()
            answer = resp.json()["response"].strip().upper()
            return "NO" not in answer  # if not explicitly NO, treat as YES
        except Exception:
            return True  # fail open
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_content_classifier.py -v
```

Expected: all 4 tests PASS.

---

## Step 4: Commit

```bash
git add backend/app/services/content_classifier.py backend/tests/test_content_classifier.py
git commit -m "feat: content classifier — non-ad rejection with fail-open on errors"
```
