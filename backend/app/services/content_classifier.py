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
            return answer != "NO"
        except Exception:
            return True
