from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.analysis import AnnotationResponse, KPISummary, OllamaAnalysisResponse


class CreativeSummary(BaseModel):
    id: int
    filename: str
    format: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    fatigue_status: Literal["healthy", "fatiguing", "insufficient_data"]
    overall_score: Optional[float] = None
    has_duplicate: bool = False
    created_at: datetime
    # KPI fields (may be None if no metric data)
    ctr: Optional[float] = None
    ipm: Optional[float] = None
    cost_total: Optional[float] = None
    ctr_delta_wow: Optional[float] = None
    days_active: Optional[int] = None
    # Metadata
    platform_tags: list[str] = []
    search_tags: list[str] = []

    model_config = {"from_attributes": True}


class CreativeDetail(BaseModel):
    id: int
    campaign_id: int
    filename: str
    storage_path: str
    format: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: int
    fatigue_status: Literal["healthy", "fatiguing", "insufficient_data"]
    analysis: Optional[OllamaAnalysisResponse] = None
    annotations: list[AnnotationResponse] = []
    kpi: Optional[KPISummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    creative_id: int
    duplicate_detected: bool
    duplicate_id: Optional[int] = None
    duplicate_type: Optional[str] = None
    hamming_distance: Optional[int] = None
    analysis_status: str
