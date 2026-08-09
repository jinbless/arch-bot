import React from 'react';
import { Link } from 'react-router-dom';
import { TrustBadge } from './SourceBadge';
import type { AnalysisResponse, WorkFlow, GuideRef } from '../../types/analysis';

/** 4단계 — 사업주가 직접 확인할 자료.
 *
 * 흐름(3단계)이 "이 기계를 어떻게 관리하나"라면, 여기는 "더 읽을 것"이다:
 *   · KOSHA 가이드 — hazard 연결에서 추린다. ⚠ 이 연결은 정확도 검증 전이라 문구로 밝힌다
 *   · 기본 안전수칙(/basics) — 사진과 무관하게 늘 걸리는 것
 *   · 안전검사 — 앵커가 법정 검사 대상인지. "대상 아님"도 자체 점검 안내와 함께 명시한다
 *     ("자료 없음"과 "검사 불필요"는 다른 말이다)
 */

const OwnerResourcesCard: React.FC<{ analysis: AnalysisResponse; flow?: WorkFlow | null }> = ({
  analysis,
  flow,
}) => {
  const guides = React.useMemo(() => {
    const seen = new Map<string, GuideRef>();
    for (const rel of analysis.hazard_guide_relations || []) {
      for (const g of rel.guides || []) {
        if (!seen.has(g.guide_code)) seen.set(g.guide_code, g);
      }
    }
    return [...seen.values()].sort((a, b) => b.relevance_score - a.relevance_score).slice(0, 5);
  }, [analysis.hazard_guide_relations]);

  const anchor = flow?.anchor;

  return (
    <section className="bg-white rounded-xl border p-4">
      <div className="space-y-3">
        {guides.length > 0 && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-gray-800">
              KOSHA 가이드 <TrustBadge level="unverified" />
            </p>
            <ul className="space-y-1">
              {guides.map((g) => (
                <li key={g.guide_code} className="text-sm text-gray-700 pl-3 relative">
                  <span className="absolute left-0 top-0.5 text-gray-400">·</span>
                  {g.title} <span className="text-xs text-gray-400 font-mono">{g.guide_code}</span>
                </li>
              ))}
            </ul>
            <p className="text-[10px] text-gray-400 mt-1">
              위험요소 기반 자동 연결 — 연결 정확도는 검증 전입니다. 가이드 원문으로 확인하세요.
            </p>
          </div>
        )}

        <div>
          <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-gray-800">
            기본 안전수칙 <TrustBadge level="reviewed" />
          </p>
          <p className="text-sm text-gray-700">
            사진과 관계없이 현장이 늘 갖춰야 하는 것 —{' '}
            <Link to="/basics" className="text-primary-600 hover:text-primary-800 underline">
              작업장·통로·보호구 등 45건 보기
            </Link>
          </p>
        </div>

        {anchor && (
          <div>
            <p className="text-sm font-semibold text-gray-800 mb-1">안전검사</p>
            {anchor.is_inspection_target ? (
              <div className="text-sm text-gray-700">
                <p>
                  <span className="font-medium">{anchor.label}</span>
                  {anchor.machines.length > 0 && (
                    <span className="text-gray-500"> ({anchor.machines.join('·')})</span>
                  )}
                   은(는) 산업안전보건법 제93조 <strong>법정 안전검사 대상</strong>입니다 — 검사
                  이력을 확인하세요.
                </p>
                {(anchor.inspection_scopes?.length ?? 0) > 0 && (
                  <ul className="mt-1 space-y-0.5">
                    {(anchor.inspection_scopes ?? []).slice(0, 3).map((s, i) => (
                      <li key={i} className="text-xs text-gray-500 pl-3 relative">
                        <span className="absolute left-0 top-0.5">·</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-700">
                <span className="font-medium">{anchor.label}</span> 은(는) 법정 안전검사 대상이
                아닙니다 — 작업 시작 전 자체 점검(위 3단계의 점검 칸)으로 관리합니다.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export default OwnerResourcesCard;
