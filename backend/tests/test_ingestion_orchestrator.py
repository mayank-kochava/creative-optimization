import io
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from PIL import Image
from app.ingestion.orchestrator import CreativeIngestionOrchestrator, IngestionResult
from app.config import settings
from app.models.campaign import Campaign


def make_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), size=len(content),
                      headers={"content-type": content_type})


def make_jpg_bytes(w=300, h=250, seed: int = 0) -> bytes:
    import random
    rng = random.Random(seed)
    img = Image.new("RGB", (w, h))
    pixels = [(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)) for _ in range(w * h)]
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def mock_services(db_session):
    from app.schemas.analysis import OllamaAnalysisResponse, AnalysisScores
    analysis_provider = AsyncMock()
    analysis_provider.analyse_image.return_value = OllamaAnalysisResponse(
        scores=AnalysisScores(hook_strength=8, cta_clarity=7, visual_quality=9,
                              message_clarity=7, emotional_resonance=8, social_proof=4, brand_consistency=6),
        overall_score=7, persuasion_strategy="aspirational", dominant_emotion="excitement",
        strengths=["Good"], weaknesses=["Bad"],
        recommendations=["Fix A", "Fix B", "Fix C"],
        explanation="Good ad."
    )
    dedup = AsyncMock()
    dedup.check_and_register.return_value = None
    annotation = AsyncMock()
    annotation.annotate.return_value = []
    video_svc = MagicMock()
    classifier = AsyncMock()
    classifier.is_advertisement.return_value = True
    fatigue = AsyncMock()
    fatigue.compute_fatigue_status.return_value = "insufficient_data"
    return analysis_provider, dedup, annotation, video_svc, classifier, fatigue


@pytest.fixture
def orchestrator(db_session, mock_services, tmp_path):
    ap, dedup, ann, video, classifier, fatigue = mock_services
    settings.storage_path = str(tmp_path)
    return CreativeIngestionOrchestrator(
        db=db_session,
        analysis_provider=ap,
        dedup_service=dedup,
        annotation_pipeline=ann,
        video_service=video,
        content_classifier=classifier,
        fatigue_detector=fatigue,
    )


@pytest.mark.asyncio
async def test_ingest_jpg_returns_creative_id(orchestrator, db_session):
    camp = Campaign(name="Orch Test", platform_tags=[])
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    upload = make_upload_file(make_jpg_bytes(seed=1), "test.jpg", "image/jpeg")
    result = await orchestrator.ingest(upload, campaign_id=camp.id)
    assert isinstance(result, IngestionResult)
    assert result.creative_id > 0
    assert result.duplicate_detected is False


@pytest.mark.asyncio
async def test_unsupported_format_raises_415(orchestrator, db_session):
    from fastapi import HTTPException
    upload = make_upload_file(b"fake pdf content", "test.pdf", "application/pdf")
    with pytest.raises(HTTPException) as exc:
        await orchestrator.ingest(upload, campaign_id=1)
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_oversized_image_raises_413(orchestrator, db_session):
    from fastapi import HTTPException
    large_content = b"x" * (settings.max_image_size_bytes + 1)
    upload = make_upload_file(large_content, "big.jpg", "image/jpeg")
    with pytest.raises(HTTPException) as exc:
        await orchestrator.ingest(upload, campaign_id=1)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_duplicate_detected_returns_duplicate_info(orchestrator, db_session, mock_services):
    ap, dedup, ann, video, classifier, fatigue = mock_services
    from app.models.duplicate import DuplicatePair
    dedup.check_and_register.return_value = DuplicatePair(
        creative_id_a=1, creative_id_b=2, hamming_distance=0, duplicate_type="self"
    )
    camp = Campaign(name="Dup Camp", platform_tags=[])
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    # Use a distinct seed to avoid phash collision with other tests
    upload = make_upload_file(make_jpg_bytes(seed=42), "dup.jpg", "image/jpeg")
    result = await orchestrator.ingest(upload, campaign_id=camp.id)
    assert result.duplicate_detected is True
    assert result.hamming_distance == 0
