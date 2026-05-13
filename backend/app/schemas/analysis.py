from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class AnalysisScores(BaseModel):
    hook_strength: float
    cta_clarity: float
    visual_quality: float
    message_clarity: float
    emotional_resonance: float
    social_proof: float
    brand_consistency: float

    @field_validator("*", mode="before")
    @classmethod
    def clamp(cls, v: float) -> float:
        return max(0.0, min(10.0, float(v)))

    def average(self) -> float:
        vals = [
            self.hook_strength, self.cta_clarity, self.visual_quality,
            self.message_clarity, self.emotional_resonance, self.social_proof,
            self.brand_consistency,
        ]
        return round(sum(vals) / len(vals), 1)


class OllamaAnalysisResponse(BaseModel):
    scores: AnalysisScores
    overall_score: float = 0.0
    persuasion_strategy: str
    dominant_emotion: str
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    explanation: str
    status: Literal["complete", "degraded"] = "complete"

    @model_validator(mode="after")
    def compute_overall_score(self) -> OllamaAnalysisResponse:
        self.overall_score = self.scores.average()
        return self


class DegradedAnalysisResponse(OllamaAnalysisResponse):
    persuasion_strategy: str = "unknown"
    dominant_emotion: str = "unknown"
    explanation: str = "Analysis unavailable — Ollama did not return valid JSON."
    status: Literal["complete", "degraded"] = "degraded"

    @model_validator(mode="after")
    def zero_scores(self) -> DegradedAnalysisResponse:
        self.scores = AnalysisScores(
            hook_strength=0, cta_clarity=0, visual_quality=0,
            message_clarity=0, emotional_resonance=0, social_proof=0,
            brand_consistency=0,
        )
        self.overall_score = 0.0
        return self


class BBoxResponse(BaseModel):
    x: float
    y: float
    w: float
    h: float


class AnnotationResponse(BaseModel):
    annotation_type: Literal["face", "text", "cta"]
    bbox: BBoxResponse
    label: Optional[str] = None
    confidence: float


class KPISummary(BaseModel):
    total_impressions: int
    total_clicks: int
    total_installs: int
    total_spend: float
    total_revenue: float
    ctr: Optional[float] = None
    cvr: Optional[float] = None
    cpi: Optional[float] = None
    roas: Optional[float] = None
