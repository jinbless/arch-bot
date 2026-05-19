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

export interface GuideRef {
  guide_code: string;
  title: string;
  classification?: string | null;
  relevance_score: number;
  mapping_type: string;
  ci_hit_count: number;
  industry_alignment?: string | null;
  top_procedure_title?: string | null;
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
  analyzed_at: string;
}

export interface AnalysisHistoryItem {
  analysis_id: string;
  analysis_type: 'image' | 'text';
  overall_risk_level: RiskLevel;
  summary: string;
  analyzed_at: string;
  input_preview?: string;
}

export interface AnalysisHistoryResponse {
  total: number;
  items: AnalysisHistoryItem[];
}
