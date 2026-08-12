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


class FlowItem(BaseModel):
    """작업 흐름 한 단계 안의 항목 하나."""
    text: str
    source: str = ""                  # 별표 3 | 조문(전용) | 가이드(권고) | 안전검사(법정) …
    ref: str = ""                     # 조문번호·별표 출처
    # 법정 = 안 하면 위법(안전검사·조문) / 권고 = KOSHA 가이드 절차.
    # 같은 칸에 섞어 보여주면 사업주가 '해야 하는 것'과 '하면 좋은 것'을 구별하지 못한다.
    tier: str = "법정"                 # 법정 | 권고
    # 이름 매칭으로 붙은 항목은 좌표 매칭보다 불확실하다(사람 검수 대상).
    uncertain: bool = False
    # 이 항목이 **왜 이 칸에 있는지**를 말해주는 조문 원문 문구.
    # 한 조문이 두 칸에 걸치면(제35조 = 인적 배치 + 작업 전 점검) 제목만으로는 중복으로 보인다.
    evidence: str = ""


class FlowSlot(BaseModel):
    """흐름 골격의 한 칸. **번호를 매기지 않는다** — '8단계 중 4단계'는 시간 추론이라 미측정 오류원이다."""
    key: str                          # PLAN | ASSIGN | PRECHECK | EXEC | POST | PERIODIC
    label: str                        # 계획·사전조사 …
    items: List[FlowItem] = []
    empty_reason: str = ""            # 비었을 때 화면에 띄울 사유(정기 칸의 '안전검사 대상 아님' 등)


class FlowAnchor(BaseModel):
    """사진에서 잡은 기인물 = 흐름 전체가 걸리는 지점."""
    group_key: str
    label: str = ""
    path: str = ""                    # 편 > 장 > 절 > 관
    is_inspection_target: bool = False
    machines: List[str] = []
    # ★ 안전검사 대상에는 **조건**이 붙는다(정격하중 2톤 미만 크레인 제외, 이동식 국소배기장치 제외 …).
    #   조건 없이 '안전검사 대상' 배지만 달면 대상이 아닌 설비까지 대상으로 읽힌다.
    #   시행령 제78조제1항 각 호의 괄호 단서를 그대로 싣는다.
    inspection_scopes: List[str] = []
    periodic_source: str = "없음"      # 안전검사 · 조문 · 가이드의 합성 문자열 | 없음
    # ★ 앵커 카탈로그 127종은 규칙의 절·관 구조를 그대로 옮긴 것이라 **사진으로 지목할 수 없는 칸**이
    #   34종 섞여 있다(통칙·보호구·관리·상위 개념). 여기로 떨어지면 흐름이 의미가 없으므로
    #   화면이 그 사실을 말하고 사용자가 실제 기인물을 고르게 해야 한다.
    kind: str = ""                    # 기인물 | 장소 | 환경 | 부적격
    kind_why: str = ""


class BasicsTopicRef(BaseModel):
    """기본 안전수칙(/basics) 주제 참조 — 장소성 라우팅 화면의 주제 카드용 (2026-08-12 Track A).

    items는 싣지 않는다 — 카드+/basics 링크면 충분하고 저장 기록이 비대해진다."""
    name: str
    desc: str = ""
    n: int = 0


class WorkFlow(BaseModel):
    """기인물 앵커 기준 작업 전체 흐름(flag off 시 None).

    ⚠ 앵커는 이 구조의 **단일 실패점**이다 — 관 단위 정확 일치 0.711(감독관 gold 45장,
    evaluation-baseline '앵커 인식 정확도'). 4장 중 1장 이상이 통째로 틀리므로
    `alternates`(사용자 정정 후보)를 반드시 함께 노출한다.
    ⚠ 각 항목이 그 칸에 맞는지(라벨 정확도)는 **아직 사람 검수 전**이다.
    anchor.kind='기인물없음'(장소성 라우팅, Track A)이면 slots는 비고 basics_topics가 찬다.
    """
    anchor: FlowAnchor
    alternates: List[FlowAnchor] = []
    slots: List[FlowSlot] = []
    reviewed: bool = False            # 라벨 사람 검수 완료 여부 — 화면 경고 문구 제어
    # 장소성 사진일 때 결과 화면에 배치할 기본 안전수칙 주제(그 외에는 빈 배열 — 구 기록 호환)
    basics_topics: List[BasicsTopicRef] = []


class WorkFlowWithActions(WorkFlow):
    """정정 API(GET /flow) 전용 — 흐름에 '지금 당장' 재선별을 얹은 응답.

    분석 응답의 work_flow에는 붙이지 않는다(그쪽 즉시조치는 immediate_actions가 정본).
    기인물을 바꾸면 '지금 당장'도 그 기인물의 검수 조문에서 다시 선별해야 하는데(2026-08-12),
    선별 결과는 흐름과 한 몸이라 별도 응답으로 쪼개면 앵커-조치 불일치가 생길 수 있다.
    """
    statute_actions: List[CorrectiveAction] = []


class AiActionAlignment(BaseModel):
    """GPT 자유 조치 제안 1건을 흐름 조문(닫힌 집합)에 정렬한 결과.

    사용자 정책(2026-08-09): matched → 해당 조문을 근거로 보여주고, unmatched → 폐기가 아니라
    '구체 조문 불비 후보'로 적립(ohs_action_statute_gaps). unaligned(정렬 실패·대조 전)는
    적립하지 않는다 — 무매칭 판정과 판정 실패를 섞으면 불비 원장이 오염된다.
    """
    text: str                         # AI 제안 원문
    status: str = "unaligned"         # matched | unmatched | unaligned
    matched_ref: str = ""             # 대응 조문/별표 ref (matched일 때만)
    matched_title: str = ""           # 대응 흐름 항목 제목
    slot_key: str = ""                # 대응 항목이 있는 흐름 칸
    slot_label: str = ""
    reason: str = ""                  # 정렬 LLM의 한 줄 근거


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
    # ⭐ 기인물 앵커 기준 작업 흐름(flag off 시 None — 기존 경로 무변화, 호환 default = None)
    work_flow: Optional[WorkFlow] = None
    # ⭐ AI 자유 제안 ↔ 흐름 조문 정렬(2026-08-09, 흐름 있을 때만 — 호환 default = [])
    ai_action_alignments: List[AiActionAlignment] = []
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
