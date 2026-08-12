import React from 'react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { AnalysisResponse } from '../../types/analysis';
import RiskLevelBadge from '../common/RiskLevelBadge';
import { TrustBadge } from './SourceBadge';

/** 1단계 — 사진에서 본 것.
 *
 * 기존 3개 패널(분석결과요약·식별된 위험요소·발견된 위험요약)의 통합.
 * 셋 다 같은 GPT Vision 응답의 다른 필드를 보여주고 있었다 — 사업주에게는
 * "사진에서 무엇을 봤는가" 하나로 답하면 된다.
 * ⚠ 이 카드는 서술이지 판정이 아니다 — 판정 불가·미분류 경고는 그대로 유지한다.
 */

const HAZARD_RISK_COLORS: Record<string, string> = {
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-sky-50 text-sky-700 border-sky-200',
};

const FindingsCard: React.FC<{ analysis: AnalysisResponse }> = ({ analysis }) => (
  <section className="bg-white rounded-xl border p-4">
    <div className="flex items-start justify-between gap-4 mb-3">
      <p className="text-xs text-gray-500">
        {format(new Date(analysis.analyzed_at), 'yyyy년 M월 d일 HH:mm', { locale: ko })}
      </p>
      <RiskLevelBadge level={analysis.overall_risk_level} size="lg" />
    </div>

    {/* B0: 한계 고지는 서술 **위**에, "무엇이 데이터에 없는지"로 구체 서술(PAIR Do/Don't·NN/g —
        푸터 면책은 안 읽힌다). "판정 아님" 같은 모호한 문구보다 결측 데이터 나열이 강하다. */}
    <p className="mb-2 flex flex-wrap items-center gap-1.5 rounded-md bg-blue-50/60 border border-blue-100 px-2.5 py-1.5 text-[11px] leading-relaxed text-blue-900">
      <TrustBadge level="ai" />
      <span>
        이 서술은{' '}
        <strong>{analysis.analysis_type === 'text' ? '입력하신 설명만' : '사진 1장만'}</strong> 근거로
        합니다 — 기계 이력·작업표준·최근 점검 결과는 반영돼 있지 않고,{' '}
        <strong>언급이 없다고 문제가 없는 것이 아닙니다.</strong> 아래 2단계의 검수된 조문과 대조하세요.
      </span>
    </p>

    <p className="text-gray-800 leading-relaxed mb-3">{analysis.summary}</p>

    {analysis.overall_risk_level === 'unknown' && (
      <p className="mb-3 rounded-md bg-slate-100 border border-slate-300 px-3 py-2 text-xs text-slate-700">
        ⚠️ <strong>판정 불가</strong> — 이 입력만으로는 위험 유무를 확정할 수 없습니다.{' '}
        <strong>미탐지는 안전을 의미하지 않습니다.</strong> 추가 현장 확인이 필요합니다.
      </p>
    )}
    {analysis.unmapped_safety_terms && analysis.unmapped_safety_terms.length > 0 && (
      <div className="mb-3 rounded-md bg-amber-50 border border-amber-300 px-3 py-2">
        <p className="text-xs font-semibold text-amber-800 mb-1">
          ⚠️ 관찰된 미분류 위험 ({analysis.unmapped_safety_terms.length}) — 표준 분석에 미반영, 추가 확인 필요
        </p>
        <div className="flex flex-wrap gap-1">
          {analysis.unmapped_safety_terms.map((t, i) => (
            <span
              key={i}
              title={t.note}
              className="text-[10px] px-1.5 py-0.5 rounded border bg-amber-100 text-amber-800 border-amber-200"
            >
              {t.term}
            </span>
          ))}
        </div>
      </div>
    )}

    {analysis.hazards && analysis.hazards.length > 0 && (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
        {analysis.hazards.map((hz, i) => (
          <div key={`${hz.name}-${i}`} className="rounded-lg border border-gray-100 bg-gray-50 p-2.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-semibold text-gray-900">{hz.name}</p>
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full border whitespace-nowrap ${
                  HAZARD_RISK_COLORS[hz.risk_level] || 'bg-gray-100 text-gray-600 border-gray-200'
                }`}
              >
                {hz.risk_level.toUpperCase()}
              </span>
            </div>
            {hz.location && <p className="text-xs text-gray-500 mt-0.5">📍 {hz.location}</p>}
            {hz.description && <p className="text-xs text-gray-700 mt-1">{hz.description}</p>}
          </div>
        ))}
      </div>
    )}

    {analysis.observations.length > 0 && (
      <ul className="space-y-1 mb-3">
        {analysis.observations.map((o) => (
          <li key={o.observation_id} className="text-xs text-gray-600 pl-3 relative">
            <span className="absolute left-0 top-0.5 text-gray-400">·</span>
            {o.text}
          </li>
        ))}
      </ul>
    )}

  </section>
);

export default FindingsCard;
