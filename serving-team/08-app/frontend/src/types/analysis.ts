import { RiskLevel } from './hazard';

export interface TextAnalysisRequest {
  description: string;
  workplace_type?: string;
  industry_sector?: string;
}

export interface VisualCue {
  text: string;
  cue_type: string;
  confidence: number;
}

export interface VisualObservation {
  observation_id: string;
  text: string;
  confidence: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  visual_cues: VisualCue[];
}

export interface RiskFeature {
  axis: 'accident_type' | 'hazardous_agent' | 'work_context' | string;
  code: string;
  label?: string | null;
  source_text?: string | null;
  confidence: number;
}

export interface SituationMatch {
  pattern_id: string;
  title?: string | null;
  status: string;
  score: number;
  matched_features: string[];
  visual_trigger_hits: string[];
  applies_sr_ids: string[];
  applies_ci_ids: string[];
}

export interface Finding {
  finding_id: string;
  status: string;
  summary: string;
  evidence_strength: string;
  observation_ids: string[];
  situation_pattern_ids: string[];
  sr_ids: string[];
}

export interface CorrectiveAction {
  action_id: string;
  title: string;
  description?: string | null;
  source_type: string;
  source_id?: string | null;
  urgency: 'immediate' | 'planned' | 'reference' | string;
  confidence: number;
}

export interface ProcedureStep {
  step_id: string;
  order: number;
  title: string;
  safety_measures?: string | null;
  source_section?: string | null;
  source_sr_ids: string[];
}

export interface StandardProcedure {
  procedure_id: string;
  title: string;
  description?: string | null;
  guide_code?: string | null;
  work_process?: string | null;
  steps?: ProcedureStep[];
  source_sr_ids?: string[];
  source_ci_ids?: string[];
  evidence_summary?: string | null;
  confidence: number;
  mapping_type?: string | null; // WS-PROV-3: 부착 출처(표시전용)
  source_path?: string | null; // WS-DEEP-1: 이중경로 출처 she_facet/both/hazard_direct(표시전용)
  review_required?: boolean; // WS-DEEP-1: 단독경로 high-sev → 검토 필요(표시전용, down-weight 아님)
}

export interface PenaltyPath {
  path_type: 'general_incident' | 'death' | 'serious_accident' | string;
  title: string;
  notice_level: 'photo_based' | 'external_fact_required' | 'conditional' | string;
  summary: string;
  penalty_rule_ids: string[];
  penalty_descriptions: string[];
  article_refs: { ref_type: string; label: string; article_id: string }[];
  max_severity_score?: number | null;
  source_sr_ids: string[];
}

export interface ReasoningTrace {
  observations: string[];
  risk_features: string[];
  situation_patterns: string[];
  safety_requirements: string[];
  articles: string[];
  guides: string[];
  checklist_items: string[];
  penalty_rules: string[];
}

// ⭐ Hazard-Direct Pivot Phase 4 Day 2 — 자연어 hazards + hazard-별 Guide 매핑
export interface HazardItem {
  name: string;
  risk_level: 'high' | 'medium' | 'low' | string;
  location: string;
  description: string;
  preventive_measures: string[];
  mapped_codes: string[]; // ["accident_type.FALL_FROM_HEIGHT", ...]
}

export interface GuideSectionInfo {
  section_title: string;
  excerpt?: string;
  section_type?: string | null;
}

export interface GuideRef {
  guide_code: string;
  title: string;
  classification?: string | null;
  relevance_score: number;
  mapping_type: string;
  ci_hit_count: number;
  industry_alignment?: string | null;
  top_procedure_title?: string | null;
  relevant_sections?: GuideSectionInfo[];
}

export interface HazardGuideRelation {
  hazard_name: string;
  risk_level: 'high' | 'medium' | 'low' | string;
  location: string;
  description: string;
  preventive_measures: string[];
  mapped_codes: string[];
  guides: GuideRef[];
  matched_sr_count: number;
}

export interface UnmappedSafetyTerm {
  term: string;
  category: string; // "ppe_missing" | "environmental_hazard" | "unmapped_code"
  note?: string;
}

/**
 * Track A cue-pool union 조문 **후보**. trace.articles(PG 결정론 경로)와 별개인 additive 필드로,
 * 위반 확정이 아니라 "점검관이 볼 만한 조문" 제안이다. 후보 생성기에 기권(abstain) 경로가 없으므로
 * 화면에서는 반드시 '후보'로 표기한다(backend ArticleCandidate docstring과 동일 정책).
 * flag off(기본)면 빈 배열 → 패널 자체가 렌더되지 않는다.
 */
export interface ArticleCandidate {
  article_code: string; // "제43조"
  law_type: string; // "RULE"
  title: string;
  applies: 'yes' | 'maybe' | 'unranked' | string; // 기본 노출은 yes만(A안)
  rank: number; // 1..n (RANK on) / 0 (unranked)
  source: string; // 큐레이션 | 기인물 | 단서 | 흐름 | 횡단
  evidence: string; // 매칭된 관찰단서(cue canonical)
  /** violation = 이 사진의 구체적 위반 후보 / common = 모든 현장 공통 점검(SSOT §6.2 포괄조문). */
  group?: 'violation' | 'common' | string;
}

export interface AnalysisResponse {
  analysis_id: string;
  analysis_type: 'image' | 'text';
  overall_risk_level: RiskLevel;
  summary: string;
  observations: VisualObservation[];
  risk_features: RiskFeature[];
  situation_matches: SituationMatch[];
  findings: Finding[];
  immediate_actions: CorrectiveAction[];
  standard_procedures: StandardProcedure[];
  penalty_paths: PenaltyPath[];
  reasoning_trace: ReasoningTrace;
  finding_status: string;
  penalty_exposure_status: string;
  // ⭐ Hazard-Direct Pivot 신규 필드 (default = [])
  hazards?: HazardItem[];
  hazard_guide_relations?: HazardGuideRelation[];
  unmapped_safety_terms?: UnmappedSafetyTerm[]; // WS-SAFETY-5 (표시전용)
  article_candidates?: ArticleCandidate[]; // ⭐ Track A cue-pool union 조문 후보(표시전용, flag off면 [])
  work_flow?: WorkFlow | null; // ⭐ 기인물 앵커 기준 작업 흐름(표시전용, flag off면 null)
  ai_action_alignments?: AiActionAlignment[]; // ⭐ AI 제안 ↔ 흐름 조문 정렬(흐름 있을 때만)
  analyzed_at: string;
}

/** 작업 흐름 한 단계 안의 항목. tier로 법정/권고를 가른다. */
export interface FlowItem {
  text: string;
  source: string;
  ref: string;
  tier: '법정' | '권고';
  uncertain: boolean; // 이름 매칭으로 붙은 항목(좌표 매칭보다 불확실, 사람 검수 대상)
  evidence?: string; // 이 항목을 이 단계에 넣은 근거가 된 조문 원문 문구
}

/** 흐름 골격의 한 칸. **번호를 매기지 않는다** — 시간 추론은 미측정 오류원. */
export interface FlowSlot {
  key: 'PLAN' | 'ASSIGN' | 'PRECHECK' | 'EXEC' | 'POST' | 'PERIODIC';
  label: string;
  items: FlowItem[];
  empty_reason: string;
}

/** 사진에서 잡은 기인물 = 흐름 전체가 걸리는 지점. */
export interface FlowAnchor {
  group_key: string;
  label: string;
  path: string;
  is_inspection_target: boolean;
  machines: string[];
  inspection_scopes?: string[]; // 시행령 제78조제1항 각 호의 괄호 단서 — 조건 없이 '대상' 배지만 달면 안 된다
  periodic_source: string;
  kind?: '기인물' | '장소' | '환경' | '부적격'; // 부적격 = 규칙 편제상의 칸이라 사진으로 지목할 수 없다
  kind_why?: string;
}

export interface WorkFlow {
  anchor: FlowAnchor;
  alternates: FlowAnchor[]; // 앵커 정정 후보 — 앵커 정확도 0.711이라 필수
  slots: FlowSlot[];
  reviewed: boolean; // 항목 라벨 사람 검수 완료 여부
}

/** GPT 자유 조치 제안 1건 ↔ 흐름 조문(닫힌 집합) 정렬 결과.
 *  unmatched = 모델이 '대응 없음' 판정(구체 조문 불비 후보로 백엔드 원장에 적립됨).
 *  unaligned = 정렬 실패·대조 전 — 무매칭과 다른 상태다(불비로 표시하면 안 된다). */
export interface AiActionAlignment {
  text: string;
  status: 'matched' | 'unmatched' | 'unaligned' | string;
  matched_ref: string;
  matched_title: string;
  slot_key: string;
  slot_label: string;
  reason: string;
}

export interface AnalysisHistoryItem {
  analysis_id: string;
  analysis_type: 'image' | 'text';
  overall_risk_level: RiskLevel;
  summary: string;
  analyzed_at: string;
  input_preview?: string;
  thumbnail?: string | null; // 분석 사진 thumbnail(data URI, image 분석만) — 결과와 함께 표시
}

export interface AnalysisHistoryResponse {
  total: number;
  items: AnalysisHistoryItem[];
}
