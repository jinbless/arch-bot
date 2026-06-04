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


# ===== Hazard-Direct Pivot Phase 4 Day 1 ===== #
# GPT가 자연어로 직접 출력한 hazards[] + hazard별 Guide 매핑.

class HazardItem(BaseModel):
    """⭐ Hazard-Direct Pivot — GPT 자연어 hazard 카테고리.

    moellab 스타일 직관적 출력. preventive_measures는 사진 context 기반
    권고 (법령 판단 아님). mapped_codes는 normalize_hazards_array의 audit.
    """
    name: str
    risk_level: str = "medium"  # "high" | "medium" | "low"
    location: str = ""
    description: str = ""
    preventive_measures: List[str] = []
    mapped_codes: List[str] = []  # ["accident_type.FALL_FROM_HEIGHT", ...]


class GuideSectionRef(BaseModel):
    """매칭된 guide 섹션 인용 (§근거 — _attach_section_evidence 사후 부착)."""
    section_title: str
    excerpt: str = ""
    section_type: Optional[str] = None


class GuideRef(BaseModel):
    """Hazard-Direct Pivot — hazard별 Guide 요약 (HazardGuideRelation 안)."""
    guide_code: str
    title: str
    classification: Optional[str] = None
    relevance_score: float = 0.0
    mapping_type: str = "sr_ci_link"
    ci_hit_count: int = 0
    industry_alignment: Optional[str] = None
    top_procedure_title: Optional[str] = None
    relevant_sections: List[GuideSectionRef] = []


class HazardGuideRelation(BaseModel):
    """⭐ Hazard-Direct Pivot — hazard별 관련 Guide 묶음."""
    hazard_name: str
    risk_level: str = "medium"
    location: str = ""
    description: str = ""
    preventive_measures: List[str] = []
    mapped_codes: List[str] = []
    guides: List[GuideRef] = []
    matched_sr_count: int = 0


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
    # ⭐ Hazard-Direct Pivot 신규 필드 (호환 default = []) — Phase 4 Day 1
    hazards: List[HazardItem] = []
    hazard_guide_relations: List[HazardGuideRelation] = []
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
