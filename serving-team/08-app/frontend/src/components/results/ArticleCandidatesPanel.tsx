import React, { useMemo, useState } from 'react';
import type { ArticleCandidate } from '../../types/analysis';

/**
 * Track A cue-pool union 조문 **후보** 패널 (표시전용).
 *
 * 성격: trace.articles(PG 결정론 경로)와 분리된 additive 필드. 관찰단서(cue)로 좁힌
 * "점검관이 확인해 볼 조문" 제안이며 **위반 확정이 아니다**. 후보 생성기(랭커)에는
 * 기권 경로가 없어(오탐 스모크 abstain 0%) 위반이 없는 사진에서도 목록이 비지 않는다 →
 * 제목·문구·배지 전부 '후보/검토 대상'으로 고정하고, 확정 성격 패널(즉시조치·벌칙)과
 * 시각적으로 구분한다(빨강 계열 금지).
 *
 * flag off(기본)면 backend가 빈 배열을 주므로 패널은 렌더되지 않는다.
 */

const APPLIES_META: Record<string, { label: string; cls: string; title: string }> = {
  yes: {
    label: '가시 단서 있음',
    cls: 'bg-amber-100 text-amber-800 border-amber-200',
    title: '사진에서 구체적 결여가 보인다고 판단된 후보 — 확정 위반이 아니라 우선 확인 대상',
  },
  maybe: {
    label: '정황·미확인',
    cls: 'bg-slate-100 text-slate-700 border-slate-200',
    title: '정황상 가능하나 사진에서 충족 여부가 확인되지 않은 후보',
  },
  unranked: {
    label: '미정렬',
    cls: 'bg-gray-100 text-gray-600 border-gray-200',
    title: '순위 산정(RANK)을 거치지 않은 후보 — 조문 번호 순으로만 나열',
  },
};

const SOURCE_TITLE: Record<string, string> = {
  큐레이션: '기인물 큐레이션 매핑에서 온 후보',
  기인물: '식별된 기인물(기계·설비·물질) 그룹의 조문',
  단서: '관찰단서(cue-pool) 직접 매칭',
  흐름: '관찰단서의 판단흐름(연결 조문)',
  횡단: '거의 모든 작업장에 걸리는 일반의무 — 이 사진의 핵심 위반이 아닐 수 있음',
};

const PREVIEW_COUNT = 6;

const ArticleCandidatesPanel: React.FC<{ candidates?: ArticleCandidate[] }> = ({ candidates }) => {
  const [expanded, setExpanded] = useState(false);
  const items = useMemo(() => candidates ?? [], [candidates]);

  if (!items.length) return null;

  const ranked = items.some((c) => c.rank > 0);
  const shown = expanded ? items : items.slice(0, PREVIEW_COUNT);
  const rest = items.length - shown.length;

  return (
    <section className="bg-white rounded-xl border border-amber-200 p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            조문 후보 <span className="text-amber-700">(확정 아님 · 검토 대상)</span>
          </h2>
          <p className="text-sm text-gray-500">
            사진에서 관찰된 단서로 좁힌 산업안전보건기준규칙 조문 <strong>후보</strong>입니다.
            {ranked ? ' 점검관이 먼저 지적할 순서로 정렬했습니다.' : ' 순위 없이 조문 번호 순입니다.'}
          </p>
        </div>
        <span
          title="Track A cue-pool union 후보 — 관찰단서(cue) + 기인물 앵커로 생성. PG 결정론 경로(근거 추적의 조문)와는 별개 필드."
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-50 text-amber-700 border-amber-200 whitespace-nowrap"
        >
          관찰단서 후보
        </span>
      </div>

      <div className="mb-3 rounded-lg bg-amber-50 border border-amber-100 p-2.5 text-xs text-amber-900 leading-relaxed">
        위반 여부를 확정한 결과가 아닙니다. 후보 목록은 <strong>해당 없음을 반환하지 않으므로</strong>,
        실제로 위반이 없는 현장에서도 조문이 표시될 수 있습니다. 각 조문의 성립 여부는 현장 확인 후 판단하세요.
      </div>

      <ol className="space-y-2">
        {shown.map((c, i) => {
          const meta = APPLIES_META[c.applies] ?? APPLIES_META.unranked;
          return (
            <li
              key={`${c.article_code}-${i}`}
              className="rounded-lg border border-gray-100 bg-gray-50 p-2.5 flex items-start gap-2.5"
            >
              <span className="mt-0.5 w-6 shrink-0 text-center text-xs font-bold text-gray-400">
                {c.rank > 0 ? c.rank : '·'}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-sm font-semibold text-gray-900">{c.article_code}</span>
                  <span className="text-sm text-gray-700">{c.title}</span>
                  <span
                    title={meta.title}
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${meta.cls} whitespace-nowrap`}
                  >
                    {meta.label}
                  </span>
                  {c.source && (
                    <span
                      title={SOURCE_TITLE[c.source] || '후보 생성 경로'}
                      className="text-[10px] px-1.5 py-0.5 rounded border bg-white text-gray-500 border-gray-200 whitespace-nowrap"
                    >
                      {c.source}
                    </span>
                  )}
                </div>
                {c.evidence && (
                  <p className="mt-1 text-xs text-gray-500">매칭된 관찰단서: {c.evidence}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {(rest > 0 || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 text-xs font-medium text-amber-700 hover:text-amber-900"
        >
          {expanded ? '접기' : `나머지 후보 ${rest}개 보기 (전체 ${items.length}개)`}
        </button>
      )}
    </section>
  );
};

export default ArticleCandidatesPanel;
