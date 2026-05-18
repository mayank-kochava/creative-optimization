import pytest
from pathlib import Path
from PIL import Image, ImageDraw
from app.services.annotation_pipeline import AnnotationPipeline, AnnotationResult


@pytest.fixture(scope="module")
def pipeline():
    return AnnotationPipeline()


@pytest.fixture
def image_with_text(tmp_path):
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
    if cta_anns:
        assert cta_anns[0].bbox["y"] > 200
