import React from 'react';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';
import { AnalysisResponse } from '../../types/analysis';
import RiskLevelBadge from '../common/RiskLevelBadge';
import { findingStatusLabels } from './resultLabels';
import SourceBadge from './SourceBadge';

interface ResultSummaryProps {
  analysis: AnalysisResponse;
}

const PENALTY_LABELS: Record<string, string> = {
  direct: '벌칙 안내 있음',
  conditional: '조건부 안내',
  no_penalty: '안내 없음',
};

const ResultSummary: React.FC<ResultSummaryProps> = ({ analysis }) => {
  return (
    <section className="card bg-gradient-to-r from-gray-50 to-gray-100">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">분석 결과 요약</h2>
          <p className="text-sm text-gray-500 mt-1">
            {format(new Date(analysis.analyzed_at), 'yyyy년 M월 d일 HH:mm', { locale: ko })}
          </p>
        </div>
        <RiskLevelBadge level={analysis.overall_risk_level} size="lg" />
      </div>

      <p className="text-gray-700 leading-relaxed mb-2">{analysis.summary}</p>
      {analysis.overall_risk_level === 'unknown' && (
        <p className="mb-3 rounded-md bg-slate-100 border border-slate-300 px-3 py-2 text-xs text-slate-700">
          ⚠️ <strong>판정 불가</strong> — 이 입력만으로는 위험 유무를 확정할 수 없습니다.{' '}
          <strong>미탐지는 안전을 의미하지 않습니다.</strong> 추가 현장 확인이 필요합니다.
        </p>
      )}
      <p className="text-[10px] text-gray-400 mb-4 flex items-center gap-1">
        <SourceBadge source="gpt" />
        <span>위 요약은 LLM이 생성. 아래 통계는 backend가 PG/SHE/정규화 결과 집계.</span>
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-4 border-t border-gray-200">
        <SummaryMetric label="관찰 사실" value={analysis.observations.length} />
        <SummaryMetric label="위험 특징" value={analysis.risk_features.length} />
        <SummaryMetric
          label="위험 판단"
          value={findingStatusLabels[analysis.finding_status] || analysis.finding_status}
          compact
        />
        <SummaryMetric
          label="벌칙 안내"
          value={PENALTY_LABELS[analysis.penalty_exposure_status] || analysis.penalty_exposure_status}
          compact
        />
      </div>

      <div className="mt-4 pt-3 border-t border-gray-200">
        <p className="text-[11px] text-gray-500 mb-2 font-semibold">데이터 출처 범례 (각 패널에 표시)</p>
        <div className="flex flex-wrap gap-2">
          <SourceBadge source="gpt" />
          <SourceBadge source="normalized" />
          <SourceBadge source="she" />
          <SourceBadge source="pg_asserted" />
          <SourceBadge source="pg_candidate" />
          <SourceBadge source="pg_guide" />
          <SourceBadge source="pg_penalty" />
          <SourceBadge source="llm_enrich" />
          <SourceBadge source="mixed" />
        </div>
        <p className="text-[10px] text-gray-400 mt-2">badge에 hover하면 정확한 source 위치(PG table / runtime artifact) 설명이 나옵니다.</p>
      </div>
    </section>
  );
};

const SummaryMetric: React.FC<{ label: string; value: number | string; compact?: boolean }> = ({
  label,
  value,
  compact = false,
}) => (
  <div className="text-center min-w-0">
    <p className={`${compact ? 'text-sm' : 'text-2xl'} font-bold text-gray-900 break-words`}>
      {value}
    </p>
    <p className="text-sm text-gray-500 mt-1">{label}</p>
  </div>
);

export default ResultSummary;
