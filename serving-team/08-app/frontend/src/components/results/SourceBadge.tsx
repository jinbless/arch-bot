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
  | 'mixed'
  | 'ontology'
  | 'embedding_candidate';

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
  ontology:     { label: '온톨로지',      cls: 'bg-violet-100 text-violet-700 border-violet-200', title: 'hazard-direct → SR → Guide (온톨로지 기반 추론 경로)' },
  embedding_candidate: { label: '임베딩 후보(미검증)', cls: 'bg-orange-50 text-orange-700 border-orange-300', title: 'WS-PROV-3: 벡터 임베딩 유사도로 부착된 후보 — 닫힌세계(disjoint/규칙) 검증 미통과. 규칙 기반 부착과 신뢰등급이 다름.' },
};

/**
 * B0(2026-08-09) 신뢰 등급 3종 — 색이 아니라 **모양**으로 구분한다(scite 패턴).
 * 폰 스크린샷 압축·흑백 인쇄·색각이상에서도 구분돼야 한다(주 유통 경로가 스크린샷).
 * 항상 라벨 좌측, 같은 자리. 각 등급의 title에 행동 지침을 붙인다
 * (PAIR 지침: 등급에는 "그래서 뭘 하라"가 따라와야 한다).
 */
export type TrustLevel = 'reviewed' | 'ai' | 'unverified';

const TRUST_META: Record<TrustLevel, { mark: string; label: string; cls: string; title: string }> = {
  reviewed: {
    mark: '✓', label: '검수됨',
    cls: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    title: '사람 검수 체계를 거친 자료 — 조문 번호로 원문을 확인할 수 있습니다',
  },
  ai: {
    mark: '〜', label: 'AI',
    cls: 'bg-blue-50 text-blue-800 border-blue-300',
    title: 'AI가 생성한 내용 — 검수된 조문과 직접 대조하세요',
  },
  unverified: {
    mark: '?', label: '검증 전',
    cls: 'bg-amber-50 text-amber-800 border-amber-300',
    title: '자동 연결 — 정확도 검증 전이니 원문으로 확인하세요',
  },
};

export const TrustBadge: React.FC<{ level: TrustLevel; extra?: string }> = ({ level, extra }) => {
  const meta = TRUST_META[level];
  return (
    <span
      title={meta.title}
      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded border whitespace-nowrap ${meta.cls}`}
    >
      <span aria-hidden className="font-bold">{meta.mark}</span>
      {meta.label}{extra ? ` · ${extra}` : ''}
    </span>
  );
};

const SourceBadge: React.FC<{ source: SourceType; extra?: string }> = ({ source, extra }) => {
  const meta = SOURCE_META[source] ?? SOURCE_META.mixed;
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
 * WS-DEEP-1: StandardProcedure.source_path(이중경로 출처) 배지.
 * both=두 경로(SHE/facet · hazard-direct) 합의(corroborated, 가장 grounded) ·
 * she_facet=SHE/facet 단독(CI-corroborated facet guide) · hazard_direct=위험직결(GPT hazard) 단독.
 * 표시전용 — scoring 무관. source_path 없으면(semantic off) 렌더 안 함.
 */
const PATH_META: Record<string, { label: string; cls: string; title: string }> = {
  both:          { label: '양경로 합의', cls: 'bg-green-100 text-green-800 border-green-300',     title: 'SHE/facet · hazard-direct 두 경로가 모두 부착 — corroborated(가장 grounded)' },
  she_facet:     { label: 'SHE/facet',  cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', title: 'SHE/facet 경로만 부착(CI-corroboration·work_process 보유 가능)' },
  hazard_direct: { label: '위험직결',   cls: 'bg-sky-50 text-sky-700 border-sky-200',             title: 'hazard-direct(GPT hazard→SR→Guide) 경로만 부착' },
};

export const ProcedurePathBadge: React.FC<{ sourcePath?: string | null }> = ({ sourcePath }) => {
  if (!sourcePath) return null;
  const meta = PATH_META[sourcePath];
  if (!meta) return null;
  return (
    <span
      title={meta.title}
      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${meta.cls} whitespace-nowrap`}
    >
      {meta.label}
    </span>
  );
};

/**
 * WS-DEEP-1: review_required(한 경로에서만 잡힌 고위험 항목) 칩.
 * **점수 하향이 아니라** 교차 검토 환기용 — 두 경로 finding 모두 visible 유지(plan step4).
 */
export const ReviewRequiredBadge: React.FC<{ show?: boolean }> = ({ show }) => {
  if (!show) return null;
  return (
    <span
      title="한 경로에서만 잡힌 고위험 항목 — 점수 하향 아님, 교차 검토 권장(WS-DEEP-1)"
      className="text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-100 text-amber-800 border-amber-300 whitespace-nowrap"
    >
      ⚠ 검토 필요
    </span>
  );
};

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

/**
 * WS-PROV-3: StandardProcedure.mapping_type 우선으로 source 판정.
 * 임베딩 유사도 부착(hybrid_semantic/hybrid_cache)은 '임베딩 후보(미검증)'으로 표시하고,
 * 그 외는 기존 evidence_summary 추정으로 폴백.
 */
export const inferProcedureSourceFromMapping = (
  mappingType?: string | null,
  evidenceSummary?: string | null,
): SourceType => {
  if (mappingType === 'hybrid_semantic' || mappingType === 'hybrid_cache') return 'embedding_candidate';
  return inferProcedureSource(evidenceSummary);
};
