from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.hazard import (
    CorrectiveAction,
    Finding,
    PenaltyPath,
    ReasoningTrace,
    RiskFeature,
    RiskLevel,
    SituationMatch,
    StandardProcedure,
    VisualObservation,
)


class TextAnalysisRequest(BaseModel):
    description: str
    workplace_type: Optional[str] = None
    industry_sector: Optional[str] = None


class ExcludedCandidate(BaseModel):
    """Phase B.2 — LLM rerank reject 결과.

    embedding pre-filter의 drop 또는 LLM validator의 reject로 제외된 candidate.
    debug/observability 용도.
    """
    guide_code: str
    title: Optional[str] = None
    verdict: str  # "reject" | "drop"
    reason: str = ""
    confidence: float = 0.0
    similarity: Optional[float] = None
    source: str = "embedding"  # "embedding" | "llm"


class AnalysisResponse(BaseModel):
    analysis_id: str
    analysis_type: str
    overall_risk_level: RiskLevel
    summary: str
    observations: List[VisualObservation] = []
    risk_features: List[RiskFeature] = []
    situation_matches: List[SituationMatch] = []
    findings: List[Finding] = []
    immediate_actions: List[CorrectiveAction] = []
    standard_procedures: List[StandardProcedure] = []
    penalty_paths: List[PenaltyPath] = []
    reasoning_trace: ReasoningTrace = ReasoningTrace()
    finding_status: str = "not_determined"
    penalty_exposure_status: str = "no_penalty"
    excluded_candidates: List[ExcludedCandidate] = []
    analyzed_at: datetime

    class Config:
        from_attributes = True


class AnalysisHistoryItem(BaseModel):
    analysis_id: str
    analysis_type: str
    overall_risk_level: RiskLevel
    summary: str
    analyzed_at: datetime
    input_preview: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisHistoryResponse(BaseModel):
    total: int
    items: List[AnalysisHistoryItem]
