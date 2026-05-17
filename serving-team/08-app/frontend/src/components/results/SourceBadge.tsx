import React from 'react';

/**
 * 데이터 출처 (source) 분류. UI badge로 표시.
 *
 * - gpt           : LLM Vision/Text가 사진/설명에서 직접 추출
 * - normalized    : backend hazard_normalizer가 alias/catalog로 정규화
 * - she           : PG she_patterns 매칭 (deterministic)
 * - pg_asserted   : PG ci_sr_mapping 정식 매핑 (legal quality)
 * - pg_candidate  : PG candidate (review_status='candidate', 검증 통과)
 * - pg_guide      : PG kosha_guides + work_processes
 * - pg_penalty    : PG penalty_rules + penalty_conditions
 * - llm_enrich    : 5번 LLM enrichment (guide_domain_profiles 등, 임시)
 * - llm_rejected  : Phase B LLM rerank 또는 embedding pre-filter가 도메인 불일치로 제외 (debug)
 * - mixed         : 여러 source 결합
 */
export type SourceType =
  | 'gpt'
  | 'normalized'
  | 'she'
  | 'pg_asserted'
  | 'pg_candidate'
  | 'pg_guide'
  | 'pg_penalty'
  | 'llm_enrich'
  | 'llm_rejected'
  | 'mixed';

const SOURCE_META: Record<SourceType, { label: string; cls: string; title: string }> = {
  gpt:          { label: 'GPT Vision',   cls: 'bg-blue-100 text-blue-700 border-blue-200',       title: 'LLM이 사진/텍스트에서 직접 추출' },
  normalized:   { label: '정규화',        cls: 'bg-indigo-100 text-indigo-700 border-indigo-200', title: 'backend hazard_normalizer가 risk_feature_catalog/aliases로 변환' },
  she:          { label: 'SHE 패턴',      cls: 'bg-emerald-100 text-emerald-700 border-emerald-200', title: 'PG she_patterns 매칭 (deterministic)' },
  pg_asserted:  { label: 'PG 정식매핑',   cls: 'bg-rose-100 text-rose-700 border-rose-200',       title: 'PG ci_sr_mapping (asserted, legal quality)' },
  pg_candidate: { label: 'PG candidate',  cls: 'bg-amber-100 text-amber-700 border-amber-200',    title: 'PG candidate (검증 통과, asserted 아님)' },
  pg_guide:     { label: 'PG Guide',      cls: 'bg-teal-100 text-teal-700 border-teal-200',       title: 'PG kosha_guides + work_processes (1,038개)' },
  pg_penalty:   { label: 'PG PenaltyRule',cls: 'bg-red-100 text-red-700 border-red-200',          title: 'PG penalty_rules + penalty_conditions' },
  llm_enrich:   { label: 'LLM 보강',      cls: 'bg-purple-100 text-purple-700 border-purple-200', title: '5번 LLM enrichment (guide_domain_profiles 등 runtime artifact, 임시)' },
  llm_rejected: { label: 'LLM reject',    cls: 'bg-zinc-200 text-zinc-700 border-zinc-300 line-through', title: 'Phase B 도메인 검증이 제외한 candidate (debug 표시)' },
  mixed:        { label: '복합',          cls: 'bg-gray-100 text-gray-700 border-gray-200',       title: '여러 source 결합' },
};

const SourceBadge: React.FC<{ source: SourceType; extra?: string }> = ({ source, extra }) => {
  const meta = SOURCE_META[source];
  return (
    <span
      title={meta.title}
      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${meta.cls} whitespace-nowrap`}
    >
      {meta.label}{extra ? ` · ${extra}` : ''}
    </span>
  );
};

export default SourceBadge;

/**
 * immediate_action의 description을 보고 source 추정.
 * backend는 description에 "asserted CI-SR" 또는 "SHE related checklist cue"를 명시한다.
 */
export const inferActionSource = (description?: string | null): SourceType => {
  if (!description) return 'pg_guide';
  if (description.includes('asserted CI-SR')) return 'pg_asserted';
  if (description.includes('SHE related checklist cue')) return 'she';
  if (description.includes('candidate')) return 'pg_candidate';
  return 'pg_guide';
};

/**
 * standard_procedure의 evidence_summary로 source 추정.
 */
export const inferProcedureSource = (evidenceSummary?: string | null): SourceType => {
  if (!evidenceSummary) return 'pg_guide';
  if (evidenceSummary.includes('exclusive:domain_match') || evidenceSummary.includes('usage profile')) return 'llm_enrich';
  if (evidenceSummary.includes('SHE source guide')) return 'she';
  if (evidenceSummary.includes('GUIDE feature') && evidenceSummary.includes('CI feature')) return 'mixed';
  return 'pg_guide';
};
