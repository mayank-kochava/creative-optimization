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
        return await asyncio.get_event_loop().run_in_executor(None, self._annotate_sync, image_path)

    def _annotate_sync(self, image_path: Path) -> list[AnnotationResult]:
        annotations = []

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
            pass

        return annotations
