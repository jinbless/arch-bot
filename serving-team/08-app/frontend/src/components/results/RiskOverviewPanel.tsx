import React from 'react';
import type { AnalysisResponse } from '../../types/analysis';
import { severityColors, situationStatusColors, situationStatusLabels } from './resultLabels';
import SourceBadge from './SourceBadge';

const HAZARD_RISK_COLORS: Record<string, string> = {
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-sky-50 text-sky-700 border-sky-200',
};

const RiskOverviewPanel: React.FC<{ analysis: AnalysisResponse }> = ({ analysis }) => (
  <section className="space-y-4">
    {/* ⭐ Hazard-Direct Pivot Phase 4 Day 2 — 자연어 hazards[] 직관적 표시 */}
    {analysis.hazards && analysis.hazards.length > 0 ? (
      <div className="bg-white rounded-xl border p-4">
        <div className="flex items-start justify-between gap-2 mb-3">
          <h2 className="text-lg font-bold text-gray-900">식별된 위험요소</h2>
          <SourceBadge source="gpt" extra="GPT-4.1 hazards-direct" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {analysis.hazards.map((hz, i) => (
            <div key={`${hz.name}-${i}`} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
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
              {hz.location && (
                <p className="text-xs text-gray-500 mt-1">📍 {hz.location}</p>
              )}
              {hz.description && (
                <p className="text-xs text-gray-700 mt-1">{hz.description}</p>
              )}
              {hz.preventive_measures.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {hz.preventive_measures.slice(0, 4).map((pm, j) => (
                    <li key={j} className="text-[11px] text-gray-600 pl-3 relative">
                      <span className="absolute left-0 top-1">·</span>
                      {pm}
                    </li>
                  ))}
                </ul>
              )}
              {hz.mapped_codes.length > 0 && (
                <p className="text-[10px] text-gray-400 mt-2 font-mono">
                  {hz.mapped_codes.join(', ')}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    ) : null}

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div className="bg-white rounded-xl border p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <h2 className="text-lg font-bold text-gray-900">발견된 위험 요약</h2>
        <SourceBadge source="gpt" extra="LLM Vision" />
      </div>
      {analysis.observations.length ? (
        <div className="space-y-3">
          {analysis.observations.map((observation) => (
            <div key={observation.observation_id} className="rounded-lg bg-gray-50 p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-gray-900">{observation.text}</p>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border ${
                    severityColors[observation.severity] ||
                    'bg-gray-100 text-gray-600 border-gray-200'
                  }`}
                >
                  {observation.severity}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                신뢰도 {Math.round(observation.confidence * 100)}%
              </p>
              {observation.visual_cues?.length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {observation.visual_cues.slice(0, 4).map((cue, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100">
                      {cue.text}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">확인된 관찰 사실이 없습니다.</p>
      )}
    </div>

    <div className="bg-white rounded-xl border p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <h2 className="text-lg font-bold text-gray-900">정규화된 위험 특징</h2>
        <SourceBadge source="normalized" extra="risk_feature_*.json" />
      </div>
      {analysis.risk_features.length ? (
        <div className="flex flex-wrap gap-2">
          {analysis.risk_features.map((feature) => (
            <span
              key={`${feature.axis}-${feature.code}`}
              className="px-2 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs border border-blue-100"
            >
              {feature.label || feature.code}
              <span className="ml-1 text-blue-400">({feature.axis})</span>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">정규화된 위험 특징이 없습니다.</p>
      )}
      <div className="mt-4 border-t border-gray-100 pt-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-gray-800">위험상황 패턴</h3>
          <SourceBadge source="she" extra="PG she_patterns" />
        </div>
        {analysis.situation_matches.length ? (
          <div className="space-y-2">
            {analysis.situation_matches.slice(0, 4).map((match) => (
              <div key={match.pattern_id} className="rounded-lg border border-gray-100 bg-gray-50 p-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-xs font-medium text-gray-800 break-words">
                    {match.title || match.pattern_id}
                  </p>
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded-full border whitespace-nowrap ${
                      situationStatusColors[match.status] ||
                      'bg-gray-50 text-gray-600 border-gray-100'
                    }`}
                  >
                    {situationStatusLabels[match.status] || match.status}
                  </span>
                </div>
                {match.visual_trigger_hits.length > 0 && (
                  <p className="text-[11px] text-gray-500 mt-1 break-words">
                    {match.visual_trigger_hits.slice(0, 3).join(', ')}
                  </p>
                )}
                <p className="text-[10px] text-gray-400 mt-1 font-mono">{match.pattern_id}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">연결된 위험상황 패턴이 없습니다.</p>
        )}
      </div>
    </div>
    </div>
  </section>
);

export default RiskOverviewPanel;
