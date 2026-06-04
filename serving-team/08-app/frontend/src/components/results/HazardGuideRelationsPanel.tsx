/**
 * ⭐ Hazard-Direct Pivot Phase 4 Day 2 — HazardGuideRelationsPanel.
 *
 * hazard별로 관련 KOSHA Guide를 묶어 표시. 같은 사진의 GuideProcedurePanel(standard_procedures)
 * 보다 더 직관적인 진입 (사용자 멘탈 모델: hazard → 어느 Guide?).
 */
import React from 'react';
import type { AnalysisResponse } from '../../types/analysis';
import SourceBadge from './SourceBadge';

const RISK_COLORS: Record<string, string> = {
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-sky-50 text-sky-700 border-sky-200',
};

const HazardGuideRelationsPanel: React.FC<{ analysis: AnalysisResponse }> = ({ analysis }) => {
  const relations = analysis.hazard_guide_relations ?? [];
  if (!relations.length) return null;

  return (
    <section className="bg-white rounded-xl border p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <h2 className="text-lg font-bold text-gray-900">위험요소별 관련 Guide</h2>
        <SourceBadge source="ontology" extra="hazard-direct → SR → Guide" />
      </div>
      <p className="text-xs text-gray-500 mb-3">
        각 위험요소에 직접 연결된 KOSHA Guide와 적합도 점수.
        legacy 표준 절차 패널은 SHE 매칭 기반 (병행 유지).
      </p>
      <div className="space-y-3">
        {relations.map((rel, i) => (
          <div key={`${rel.hazard_name}-${i}`} className="rounded-lg border border-gray-100 p-3">
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-sm font-semibold text-gray-900">{rel.hazard_name}</p>
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full border whitespace-nowrap ${
                  RISK_COLORS[rel.risk_level] || 'bg-gray-100 text-gray-600 border-gray-200'
                }`}
              >
                {rel.risk_level.toUpperCase()}
              </span>
            </div>
            {rel.mapped_codes.length > 0 && (
              <p className="text-[10px] text-gray-400 font-mono mb-2">
                {rel.mapped_codes.join(', ')} · SR {rel.matched_sr_count}건
              </p>
            )}
            {rel.guides.length > 0 ? (
              <ul className="space-y-1">
                {rel.guides.map((g, j) => (
                  <li
                    key={`${g.guide_code}-${j}`}
                    className="flex items-start justify-between gap-2 py-1 px-2 rounded bg-gray-50 border border-gray-100"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-gray-800 truncate">
                        <span className="font-mono text-blue-700">{g.guide_code}</span>
                        {' · '}
                        {g.title}
                      </p>
                      {g.top_procedure_title && (
                        <p className="text-[11px] text-gray-500 mt-0.5 truncate">
                          → {g.top_procedure_title}
                        </p>
                      )}
                      {g.relevant_sections && g.relevant_sections.length > 0 && (
                        <p
                          className="text-[11px] text-green-700 mt-0.5 truncate"
                          title={g.relevant_sections.map((s) => s.section_title).join(', ')}
                        >
                          § {g.relevant_sections.map((s) => s.section_title).join(' · ')}
                        </p>
                      )}
                    </div>
                    <span className="text-[11px] text-gray-600 whitespace-nowrap">
                      {Math.round(g.relevance_score * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400">매핑된 Guide가 없습니다.</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
};

export default HazardGuideRelationsPanel;
