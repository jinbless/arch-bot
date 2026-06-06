from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    # WS-SAFETY-1: '평가 못 함/근거 부족' — risk 축(low/medium/high)과 구조적으로 분리된
    # 명시 채널. 'low'(녹색 안전)로 붕괴시키지 않아 '미탐지 = 안전' 오신호를 차단한다.
    UNKNOWN = "unknown"


class VisualCue(BaseModel):
    text: str
    cue_type: str = "visual"
    confidence: float = 0.0


class VisualObservation(BaseModel):
    observation_id: str
    text: str
    confidence: float = 0.0
    severity: str = "MEDIUM"
    visual_cues: List[VisualCue] = []


class RiskFeature(BaseModel):
    axis: str
    code: str
    label: Optional[str] = None
    source_text: Optional[str] = None
    confidence: float = 0.0


class SituationMatch(BaseModel):
    pattern_id: str
    title: Optional[str] = None
    status: str = "candidate"
    score: float = 0.0
    matched_features: List[str] = []
    visual_trigger_hits: List[str] = []
    applies_sr_ids: List[str] = []
    applies_ci_ids: List[str] = []


class Finding(BaseModel):
    finding_id: str
    status: str
    summary: str
    evidence_strength: str = "medium"
    observation_ids: List[str] = []
    situation_pattern_ids: List[str] = []
    sr_ids: List[str] = []


class CorrectiveAction(BaseModel):
    action_id: str
    title: str
    description: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    urgency: str = "reference"
    confidence: float = 0.0


class ProcedureStep(BaseModel):
    step_id: str
    order: int
    title: str
    safety_measures: Optional[str] = None
    source_section: Optional[str] = None
    source_sr_ids: List[str] = []


class StandardProcedure(BaseModel):
    procedure_id: str
    title: str
    description: Optional[str] = None
    guide_code: Optional[str] = None
    work_process: Optional[str] = None
    steps: List[ProcedureStep] = []
    source_sr_ids: List[str] = []
    source_ci_ids: List[str] = []
    evidence_summary: Optional[str] = None
    confidence: float = 0.0
    # WS-PROV-3: 이 절차가 어떻게 부착됐는지(표시전용, scoring 무관).
    # hybrid_semantic/hybrid_cache=임베딩 후보(미검증) vs she_sr_wp_guide/sr_ci_link=규칙 기반.
    mapping_type: Optional[str] = None


class PenaltyPath(BaseModel):
    path_type: str
    title: str
    notice_level: str
    summary: str
    penalty_rule_ids: List[str] = []
    penalty_descriptions: List[str] = []
    article_refs: List[dict[str, Any]] = []
    max_severity_score: Optional[int] = None
    source_sr_ids: List[str] = []


class ReasoningTrace(BaseModel):
    observations: List[str] = []
    risk_features: List[str] = []
    situation_patterns: List[str] = []
    safety_requirements: List[str] = []
    articles: List[str] = []
    guides: List[str] = []
    checklist_items: List[str] = []
    penalty_rules: List[str] = []
