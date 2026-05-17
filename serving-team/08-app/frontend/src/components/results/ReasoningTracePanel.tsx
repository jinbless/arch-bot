import React from 'react';
import type { ReasoningTrace } from '../../types/analysis';
import SourceBadge, { SourceType } from './SourceBadge';

interface ReasoningTracePanelProps {
  trace: ReasoningTrace;
  matches: number;
}

const ReasoningTracePanel: React.FC<ReasoningTracePanelProps> = ({ trace, matches }) => (
  <details className="bg-white rounded-xl border p-4">
    <summary className="cursor-pointer text-sm font-semibold text-gray-800">
      근거 보기: GPT → 정규화 → SHE → SR/법령 → Guide/CI → PenaltyRule (각 단계별 source)
    </summary>
    <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-2 text-xs">
      <TraceBox
        title={`관찰/특징 (${trace.observations.length + trace.risk_features.length})`}
        sources={['gpt', 'normalized']}
        lines={[
          ...trace.observations.map((s) => `[GPT] ${s}`),
          ...trace.risk_features.map((s) => `[정규화] ${s}`),
        ].slice(0, 10)}
      />
      <TraceBox
        title={`SHE (${matches})`}
        sources={['she']}
        lines={trace.situation_patterns.slice(0, 10)}
      />
      <TraceBox
        title={`SR/법령 (${trace.safety_requirements.length}/${trace.articles.length})`}
        sources={['pg_asserted']}
        lines={[
          ...trace.safety_requirements.slice(0, 5).map((s) => `[SR] ${s}`),
          ...trace.articles.slice(0, 5).map((s) => `[법령] ${s}`),
        ]}
      />
      <TraceBox
        title={`Guide/CI (${trace.guides.length}/${trace.checklist_items.length})`}
        sources={['pg_guide', 'pg_asserted']}
        lines={[
          ...trace.guides.slice(0, 5).map((s) => `[Guide] ${s}`),
          ...trace.checklist_items.slice(0, 5).map((s) => `[CI] ${s}`),
        ]}
      />
      <TraceBox
        title={`PenaltyRule (${trace.penalty_rules.length})`}
        sources={['pg_penalty']}
        lines={trace.penalty_rules.slice(0, 10)}
      />
    </div>
    <p className="text-[10px] text-gray-400 mt-3">
      모든 ID는 PG materialized table 또는 backend stage에서 유래합니다. SHE→SR→법령→Guide→CI는 deterministic, GPT/정규화는 LLM 기반.
    </p>
  </details>
);

const TraceBox: React.FC<{ title: string; sources: SourceType[]; lines: string[] }> = ({ title, sources, lines }) => (
  <div className="rounded-lg border bg-gray-50 p-3 min-w-0">
    <div className="flex items-center justify-between gap-1 mb-2">
      <div className="font-semibold text-gray-700 text-xs">{title}</div>
    </div>
    <div className="flex flex-wrap gap-1 mb-2">
      {sources.map((s) => (
        <SourceBadge key={s} source={s} />
      ))}
    </div>
    <div className="space-y-1">
      {lines.length ? (
        lines.map((line, index) => (
          <div key={`${line}-${index}`} className="font-mono text-[11px] text-gray-500 break-words">
            {line}
          </div>
        ))
      ) : (
        <div className="text-[11px] text-gray-400">없음</div>
      )}
    </div>
  </div>
);

export default ReasoningTracePanel;
