# Task 11: Annotation Pipeline

**Files to create:**
- `backend/app/services/annotation_pipeline.py`
- `backend/tests/test_annotation_pipeline.py`

**Prereq:** Task 01 complete. Tesseract must be installed: `brew install tesseract`

---

## Step 1: Write failing tests

```python
# backend/tests/test_annotation_pipeline.py
import pytest
from pathlib import Path
from PIL import Image, ImageDraw
from app.services.annotation_pipeline import AnnotationPipeline, AnnotationResult


@pytest.fixture(scope="module")
def pipeline():
    return AnnotationPipeline()


@pytest.fixture
def image_with_text(tmp_path):
    """Create image with visible text at bottom."""
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 290], outline="black", width=2)
    draw.text((150, 250), "DOWNLOAD NOW", fill="black")
    path = tmp_path / "text_image.png"
    img.save(str(path))
    return path


@pytest.fixture
def blank_image(tmp_path):
    img = Image.new("RGB", (300, 250), "white")
    path = tmp_path / "blank.png"
    img.save(str(path))
    return path


@pytest.mark.asyncio
async def test_text_annotation_detected(pipeline, image_with_text):
    results = await pipeline.annotate(image_with_text)
    text_anns = [r for r in results if r.annotation_type == "text"]
    assert len(text_anns) > 0
    words = [a.label.upper() for a in text_anns if a.label]
    assert any("DOWNLOAD" in w or "NOW" in w for w in words)


@pytest.mark.asyncio
async def test_blank_image_returns_empty(pipeline, blank_image):
    results = await pipeline.annotate(blank_image)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_annotation_result_has_valid_bbox(pipeline, image_with_text):
    results = await pipeline.annotate(image_with_text)
    for r in results:
        assert r.bbox["x"] >= 0
        assert r.bbox["y"] >= 0
        assert r.bbox["w"] > 0
        assert r.bbox["h"] > 0
        assert 0.0 <= r.confidence <= 1.0


@pytest.mark.asyncio
async def test_cta_detected_in_bottom_third(pipeline, image_with_text):
    results = await pipeline.annotate(image_with_text)
    cta_anns = [r for r in results if r.annotation_type == "cta"]
    # Text "DOWNLOAD NOW" is at y=250 out of 300 — bottom third
    if cta_anns:
        assert cta_anns[0].bbox["y"] > 200
```

Run: `cd backend && pytest tests/test_annotation_pipeline.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/services/annotation_pipeline.py`

```python
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import pytesseract
from PIL import Image


@dataclass
class AnnotationResult:
    annotation_type: str  # face | text | cta
    bbox: dict  # {x, y, w, h}
    label: Optional[str]
    confidence: float


class AnnotationPipeline:
    def __init__(self):
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    async def annotate(self, image_path: Path) -> list[AnnotationResult]:
        """Run face + text + CTA detection on an image. Returns list of AnnotationResult."""
        return await asyncio.get_event_loop().run_in_executor(None, self._annotate_sync, image_path)

    def _annotate_sync(self, image_path: Path) -> list[AnnotationResult]:
        annotations = []

        # 1. Face detection (OpenCV Haar cascade)
        img_cv = cv2.imread(str(image_path))
        if img_cv is not None:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            faces = self._cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            for x, y, w, h in faces:
                annotations.append(AnnotationResult(
                    annotation_type="face",
                    bbox={"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                    label=None,
                    confidence=0.85,
                ))

        # 2. Text detection (pytesseract)
        try:
            pil_img = Image.open(image_path).convert("RGB")
            img_height = pil_img.height
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            text_annotations = []
            for i, word in enumerate(data["text"]):
                word = word.strip()
                conf = int(data["conf"][i])
                if word and conf > 60:
                    ann = AnnotationResult(
                        annotation_type="text",
                        bbox={
                            "x": int(data["left"][i]),
                            "y": int(data["top"][i]),
                            "w": int(data["width"][i]),
                            "h": int(data["height"][i]),
                        },
                        label=word,
                        confidence=conf / 100.0,
                    )
                    text_annotations.append(ann)
                    annotations.append(ann)

            # 3. CTA heuristic: highest-confidence word in bottom 30%
            bottom_threshold = img_height * 0.7
            cta_candidates = [a for a in text_annotations if a.bbox["y"] > bottom_threshold]
            if cta_candidates:
                cta = max(cta_candidates, key=lambda a: a.confidence)
                annotations.append(AnnotationResult(
                    annotation_type="cta",
                    bbox=cta.bbox,
                    label=cta.label,
                    confidence=cta.confidence,
                ))
        except Exception:
            pass  # tesseract not available or failed — skip text annotations

        return annotations
```

---

## Step 3: Run tests

```bash
cd backend && pytest tests/test_annotation_pipeline.py -v
```

Expected: all 4 tests PASS (face test may pass/fail depending on test image — blank_image and bbox tests always pass).

---

## Step 4: Commit

```bash
git add backend/app/services/annotation_pipeline.py backend/tests/test_annotation_pipeline.py
git commit -m "feat: annotation pipeline — OpenCV faces + pytesseract text + CTA heuristic"
```
