# Task 06: Pydantic Analysis Schemas

**Files to create:**
- `backend/app/schemas/analysis.py`
- `backend/app/schemas/campaign.py`
- `backend/app/schemas/creative.py`
- `backend/app/schemas/__init__.py`
- `backend/tests/test_schemas.py`

**Prereq:** Task 01 complete.

---

## Step 1: Write failing test

```python
# backend/tests/test_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.analysis import OllamaAnalysisResponse, AnalysisScores


def test_valid_analysis_response_passes():
    data = {
        "scores": {
            "hook_strength": 8, "cta_clarity": 7, "visual_quality": 9,
            "message_clarity": 7, "emotional_resonance": 8, "social_proof": 4,
            "brand_consistency": 6
        },
        "overall_score": 7,
        "persuasion_strategy": "aspirational",
        "dominant_emotion": "excitement",
        "strengths": ["Strong visual hook", "Clear CTA"],
        "weaknesses": ["Low social proof"],
        "recommendations": ["Add testimonials", "Boost CTA contrast", "Simplify message"],
        "explanation": "This creative uses aspirational imagery effectively."
    }
    result = OllamaAnalysisResponse(**data)
    assert result.scores.hook_strength == 8
    assert len(result.recommendations) == 3


valid_data = {
    "scores": {
        "hook_strength": 8, "cta_clarity": 7, "visual_quality": 9,
        "message_clarity": 7, "emotional_resonance": 8, "social_proof": 4,
        "brand_consistency": 6,
    },
    "overall_score": 7,
    "persuasion_strategy": "aspirational",
    "dominant_emotion": "excitement",
    "strengths": ["Strong visual hook", "Clear CTA"],
    "weaknesses": ["Low social proof"],
    "recommendations": ["Add testimonials", "Boost CTA contrast", "Simplify message"],
    "explanation": "This creative uses aspirational imagery effectively.",
}


def test_overall_score_clamped_to_0_10():
    with pytest.raises(ValidationError):
        AnalysisScores(hook_strength=11, cta_clarity=5, visual_quality=5,
                       message_clarity=5, emotional_resonance=5, social_proof=5,
                       brand_consistency=5)


def test_recommendations_must_be_exactly_3():
    with pytest.raises(ValidationError):
        OllamaAnalysisResponse(**{**valid_data, "recommendations": ["only one"]})


def test_invalid_persuasion_strategy_fails():
    with pytest.raises(ValidationError):
        OllamaAnalysisResponse(**{**valid_data, "persuasion_strategy": "magic"})


def test_overall_score_computed_from_scores():
    # scores average = (8+7+9+7+8+4+6)/7 = 7.0
    result = OllamaAnalysisResponse(**valid_data)
    assert result.overall_score == 7
```

Run: `cd backend && pytest tests/test_schemas.py -v`
Expected: FAIL — module not found.

---

## Step 2: Create `backend/app/schemas/analysis.py`

```python
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisScores(BaseModel):
    hook_strength: int = Field(ge=0, le=10)
    cta_clarity: int = Field(ge=0, le=10)
    visual_quality: int = Field(ge=0, le=10)
    message_clarity: int = Field(ge=0, le=10)
    emotional_resonance: int = Field(ge=0, le=10)
    social_proof: int = Field(ge=0, le=10)
    brand_consistency: int = Field(ge=0, le=10)

    def average(self) -> int:
        vals = list(self.model_dump().values())
        return round(sum(vals) / len(vals))


class OllamaAnalysisResponse(BaseModel):
    scores: AnalysisScores
    overall_score: int = Field(ge=0, le=10, default=0)
    persuasion_strategy: Literal[
        "fear_appeal", "fomo", "aspirational", "social_proof", "rational", "unknown"
    ]
    dominant_emotion: Literal[
        "excitement", "fear", "trust", "joy", "sadness", "neutral", "unknown"
    ]
    strengths: list[str] = Field(default_factory=list, max_length=5)
    weaknesses: list[str] = Field(default_factory=list, max_length=5)
    recommendations: list[str] = Field(min_length=3, max_length=3)
    explanation: str = Field(min_length=1)
    benchmark_percentile: int | None = Field(default=None, ge=1, le=100)
    status: Literal["complete", "degraded"] = "complete"

    @model_validator(mode="after")
    def compute_overall_score(self) -> "OllamaAnalysisResponse":
        self.overall_score = self.scores.average()
        return self


def _zero_scores() -> AnalysisScores:
    return AnalysisScores(
        hook_strength=0, cta_clarity=0, visual_quality=0, message_clarity=0,
        emotional_resonance=0, social_proof=0, brand_consistency=0,
    )


class DegradedAnalysisResponse(OllamaAnalysisResponse):
    """Subclass of OllamaAnalysisResponse so type annotations accept it everywhere."""
    scores: AnalysisScores = _zero_scores()
    overall_score: int = 0
    persuasion_strategy: Literal[
        "fear_appeal", "fomo", "aspirational", "social_proof", "rational", "unknown"
    ] = "unknown"
    dominant_emotion: Literal[
        "excitement", "fear", "trust", "joy", "sadness", "neutral", "unknown"
    ] = "unknown"
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = [
        "Analysis unavailable",
        "Retry after Ollama restart",
        "Check model: qwen2.5vl:7b",
    ]
    explanation: str = "Analysis could not be completed after 3 retries."
    benchmark_percentile: int | None = None
    status: Literal["complete", "degraded"] = "degraded"

    @model_validator(mode="after")
    def compute_overall_score(self) -> "DegradedAnalysisResponse":
        # Override parent validator — degraded always returns 0, don't recompute from zeros
        return self


class AnnotationResponse(BaseModel):
    annotation_type: Literal["face", "text", "cta"]
    bbox: dict  # {x, y, w, h}
    label: str | None
    confidence: float


class KPISummary(BaseModel):
    total_impressions: int
    total_clicks: int
    total_installs: int
    total_spend: float
    total_revenue: float
    ctr: float | None  # clicks / impressions
    cvr: float | None  # installs / clicks
    cpi: float | None  # spend / installs
    roas: float | None  # revenue / spend
```

---

## Step 3: Create `backend/app/schemas/campaign.py`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform_tags: list[str] = []


class CampaignResponse(BaseModel):
    id: int
    name: str
    platform_tags: list[str]
    creative_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

---

## Step 4: Create `backend/app/schemas/creative.py`

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.analysis import AnnotationResponse, KPISummary, OllamaAnalysisResponse


class CreativeSummary(BaseModel):
    id: int
    filename: str
    format: str
    width: int | None
    height: int | None
    fatigue_status: Literal["healthy", "fatiguing", "insufficient_data"]
    overall_score: int | None = None
    has_duplicate: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class CreativeDetail(BaseModel):
    id: int
    campaign_id: int
    filename: str
    storage_path: str
    format: str
    width: int | None
    height: int | None
    duration_seconds: float | None
    file_size_bytes: int
    fatigue_status: Literal["healthy", "fatiguing", "insufficient_data"]
    analysis: OllamaAnalysisResponse | None
    annotations: list[AnnotationResponse] = []
    kpi: KPISummary | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    creative_id: int
    duplicate_detected: bool
    duplicate_id: int | None = None
    duplicate_type: str | None = None
    hamming_distance: int | None = None
    analysis_status: str = "pending"
```

---

## Step 5: Create `backend/app/schemas/__init__.py`

```python
from app.schemas.analysis import (
    AnalysisScores, OllamaAnalysisResponse, DegradedAnalysisResponse,
    AnnotationResponse, KPISummary
)
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.schemas.creative import CreativeSummary, CreativeDetail, UploadResponse
```

---

## Step 6: Run tests

```bash
cd backend && pytest tests/test_schemas.py -v
```

Expected: all 5 tests PASS.

---

## Step 7: Commit

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic v2 schemas — analysis response, campaign, creative with validators"
```
