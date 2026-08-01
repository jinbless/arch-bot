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


class UnmappedSafetyTerm(BaseModel):
    """WS-SAFETY-5: GPT가 관찰했으나 폐쇄세계(SHE/SR/penalty) 매칭·스코어링에 사용되지 못한
    안전 신호. 표시전용(display-only) — finding_status/penalty/매칭에 영향 없음. 매핑 누락된
    위험이 흔적 없이 사라지지 않도록 '미탐지 ≠ 안전'을 사용자에게 가시화한다."""
    term: str
    category: str  # "ppe_missing" | "environmental_hazard" | "unmapped_code"
    note: str = ""


class ArticleCandidate(BaseModel):
    """Track A cue-pool union 조문 **후보**(research v2 검증 — evaluation-baseline 최상단).

    trace.articles(PG 결정론 경로)와 분리된 additive 필드. 위반 확정이 아니라 후보 제안 —
    오탐 스모크에서 랭커에 기권 경로 없음(abstain 0%)이 확인됐으므로 표시 시 '후보' 표기 필수.
    """
    article_code: str                 # "제43조"
    law_type: str = "RULE"
    title: str = ""
    applies: str = "unranked"         # yes | maybe | unranked (RANK off). 기본 노출은 yes만(A안)
    rank: int = 0                     # 1..n (RANK on) / 0 (unranked)
    source: str = ""                  # 큐레이션 | 기인물 | 단서 | 흐름 | 횡단
    evidence: str = ""                # 매칭된 관찰단서(cue canonical)
    # violation = 이 사진의 구체적 위반 후보 / common = 모든 현장 공통 점검(SSOT §6.2 포괄조문).
    # 정상 현장 사진에서도 제3조가 36% 붙는 실측 → 같은 목록에 두면 목록 전체의 신뢰가 깎인다.
    group: str = "violation"


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
    # ⭐ WS-SAFETY-5: 관찰됐으나 매핑/스코어링 미반영된 안전 신호(표시전용, 호환 default = [])
    unmapped_safety_terms: List[UnmappedSafetyTerm] = []
    # ⭐ Track A cue-pool union 조문 후보(flag off 시 항상 [] — 기존 경로 무변화, 호환 default = [])
    article_candidates: List[ArticleCandidate] = []
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
    # 분석 사진 thumbnail(data URI) — image_path 컬럼 매핑. history에서 결과와 함께 표시(image 분석만).
    thumbnail: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisHistoryResponse(BaseModel):
    total: int
    items: List[AnalysisHistoryItem]
