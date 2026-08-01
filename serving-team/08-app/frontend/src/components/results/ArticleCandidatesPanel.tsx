import React, { useMemo, useState } from 'react';
import type { ArticleCandidate } from '../../types/analysis';
import { findingStatusLabels } from './resultLabels';

/**
 * Track A cue-pool union 조문 **후보** 패널 (표시전용).
 *
 * 성격: trace.articles(PG 결정론 경로)와 분리된 additive 필드. 관찰단서(cue)로 좁힌
 * "점검관이 확인해 볼 조문" 제안이며 **위반 확정이 아니다**. 후보 생성기(랭커)에는
 * 기권 경로가 없어(오탐 스모크 abstain 0%) 위반이 없는 사진에서도 목록이 비지 않는다.
 *
 * 표시 원칙(적대 리뷰 반영):
 *  - 완충 문구를 tooltip에 숨기지 않는다. 폰 스크린샷으로 전달되는 것이 주 경로라, hover가 없으면
 *    사라지는 정보에 안전 고지를 싣지 않는다.
 *  - 위험등급 색(amber/red)을 배지에 쓰지 않는다. 같은 페이지의 '중간 위험' 칩과 같은 색이면
 *    후보 강도가 위험 판정으로 읽힌다 → 중립 slate 계열로만 강약을 준다.
 *  - RANK off(미정렬)에서는 조번호 순이 곧 횡단 일반의무 순이라 미리보기 6칸이 전 사진 동일해진다
 *    → 표시 순서만 출처 우선순위로 재정렬(백엔드 반환 순서는 건드리지 않음).
 *  - finding_status가 확정이 아니면 그 사실을 패널 안에서 먼저 말한다. 미확정 화면에서 이 패널만
 *    내용이 차 있으면 "결국 내 문제는 이 목록"으로 읽힌다.
 */

const APPLIES_META: Record<string, { label: string; cls: string; title: string }> = {
  yes: {
    label: '우선 확인',
    cls: 'bg-slate-200 text-slate-900 border-slate-300',
    title: '사진에 구체적 결여가 보인다고 모델이 판단한 후보 — 위반 판정이 아니라 먼저 확인할 대상',
  },
  maybe: {
    label: '추가 확인',
    cls: 'bg-white text-slate-500 border-slate-200',
    title: '정황상 가능하나 사진에서 충족 여부가 확인되지 않은 후보',
  },
  unranked: {
    label: '미정렬',
    cls: 'bg-white text-slate-400 border-slate-200',
    title: '순위 산정(RANK)을 거치지 않은 후보',
  },
};

/** 출처 칩: 라벨은 사람 말로, 정렬 우선순위는 구체성 순(횡단 일반의무가 맨 뒤). */
const SOURCE_META: Record<string, { label: string; order: number; title: string }> = {
  단서: { label: '관찰단서', order: 0, title: '사진 관찰단서(cue-pool)에 직접 매칭' },
  큐레이션: { label: '기인물 매핑', order: 1, title: '기인물 큐레이션 매핑에서 온 후보' },
  기인물: { label: '기인물', order: 2, title: '식별된 기인물(기계·설비·물질) 그룹의 조문' },
  흐름: { label: '판단흐름', order: 3, title: '관찰단서의 판단흐름으로 이어진 조문' },
  횡단: { label: '일반의무', order: 4, title: '거의 모든 작업장에 걸리는 일반의무 — 이 사진의 핵심 위반이 아닐 수 있음' },
};

const PREVIEW_COUNT = 6;

const codeNum = (code: string): number => {
  const m = /제(\d+)조/.exec(code);
  return m ? Number(m[1]) : 99999;
};

const Row: React.FC<{ c: ArticleCandidate; muted?: boolean }> = ({ c, muted }) => {
  const meta = APPLIES_META[c.applies] ?? APPLIES_META.unranked;
  const src = SOURCE_META[c.source];
  return (
    <li className={`rounded-lg border border-gray-100 p-2.5 flex items-start gap-2.5 ${muted ? 'bg-white' : 'bg-gray-50'}`}>
      <span className="mt-0.5 w-6 shrink-0 text-center text-xs font-bold text-gray-400">
        {c.rank > 0 && !muted ? c.rank : '·'}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-sm font-semibold text-gray-900">{c.article_code}</span>
          <span className="text-sm text-gray-700">{c.title}</span>
          {!muted && (
            <span
              title={meta.title}
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${meta.cls} whitespace-nowrap`}
            >
              {meta.label}
            </span>
          )}
          {c.source && !muted && (
            <span
              title={src?.title || '후보 생성 경로'}
              className="text-[10px] px-1.5 py-0.5 rounded border bg-white text-gray-500 border-gray-200 whitespace-nowrap"
            >
              {src?.label || c.source}
            </span>
          )}
        </div>
        {c.evidence && !muted && (
          <p className="mt-1 text-xs text-gray-500">
            {c.source === '흐름' ? '판단흐름 진입 단서' : '매칭된 관찰단서'}: {c.evidence}
          </p>
        )}
      </div>
    </li>
  );
};

const ArticleCandidatesPanel: React.FC<{
  candidates?: ArticleCandidate[];
  findingStatus?: string;
}> = ({ candidates, findingStatus }) => {
  const [expanded, setExpanded] = useState(false);

  const all = useMemo(() => {
    const src = candidates ?? [];
    // 같은 조문이 두 번 오면(랭커 중복 출력) 앞의 것만 남긴다 — 상반된 배지가 나란히 뜨는 것 방지
    const seen = new Set<string>();
    const deduped = src.filter((c) => !seen.has(c.article_code) && seen.add(c.article_code));
    const ranked = deduped.some((c) => c.rank > 0);
    if (ranked) return deduped; // RANK 결과 순서는 그대로 존중
    return [...deduped].sort((a, b) => {
      const oa = SOURCE_META[a.source]?.order ?? 9;
      const ob = SOURCE_META[b.source]?.order ?? 9;
      return oa !== ob ? oa - ob : codeNum(a.article_code) - codeNum(b.article_code);
    });
  }, [candidates]);

  // C안: 포괄조문(SSOT §6.2 제3·4·22조)은 '이 사진의 위반'이 아니라 '공통 점검'으로 분리해 아래에 따로 낸다.
  // 정상 현장 사진의 36%에 제3조가 붙는다는 실측 → 같은 목록에 두면 목록 전체의 신뢰가 깎인다.
  const items = useMemo(() => all.filter((c) => c.group !== 'common'), [all]);
  const commons = useMemo(() => all.filter((c) => c.group === 'common'), [all]);

  if (!all.length) return null;

  const ranked = items.some((c) => c.rank > 0);
  const shown = expanded ? items : items.slice(0, PREVIEW_COUNT);
  const rest = items.length - shown.length;
  const hasCross = items.some((c) => c.source === '횡단');
  const unconfirmed = findingStatus && findingStatus !== 'confirmed';

  return (
    <section className="bg-white rounded-xl border border-slate-300 p-4">
      <div className="mb-3">
        <h2 className="text-lg font-bold text-gray-900">
          조문 후보 <span className="text-slate-500">(확정 아님 · 검토 대상)</span>
        </h2>
        <p className="text-sm text-gray-500">
          사진에서 관찰된 단서로 좁힌 산업안전보건기준규칙 조문 <strong>후보</strong>입니다.
          {ranked
            ? ' 사진에 구체적으로 드러난 정도 순으로 나열했으며, 순서는 참고용입니다(재분석 시 바뀔 수 있습니다).'
            : ' 순위를 매기지 않은 목록입니다.'}
        </p>
      </div>

      <div className="mb-3 rounded-lg bg-slate-50 border border-slate-200 p-2.5 text-xs text-slate-700 leading-relaxed space-y-1">
        <p>
          위반 여부를 확정한 결과가 아닙니다. <strong>‘우선 확인’은 사진에 단서가 보인다는 모델 판단</strong>일 뿐,
          위반 판정이 아닙니다.
        </p>
        <p>
          <strong>위반이 없는 현장에서도 조문이 표시될 수 있습니다</strong> — 정상 현장 사진으로 측정했을 때
          상당수에서 목록이 비지 않았습니다. 각 조문의 성립 여부는 현장에서 확인해 판단하세요.
        </p>
        {unconfirmed && (
          <p className="font-medium">
            이 분석의 위험 판단은 ‘{findingStatusLabels[findingStatus!] || findingStatus}’ 상태입니다. 아래 목록이
            확정된 위반 목록으로 읽히지 않도록 주의하세요.
          </p>
        )}
      </div>

      {items.length ? (
        <ol className="space-y-2">
          {shown.map((c) => (
            <Row key={c.article_code} c={c} />
          ))}
        </ol>
      ) : (
        <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-sm text-gray-600">
          이 사진에서 <strong>구체적으로 지적할 위반은 확인되지 않았습니다.</strong>
          <span className="block mt-1 text-xs text-gray-500">
            위반이 없다는 보증은 아닙니다 — 사진에 안 보이는 위반(서류·절차 등)은 판단하지 못합니다.
          </span>
        </div>
      )}

      {hasCross && (
        <p className="mt-2 text-[11px] text-gray-500">
          ‘일반의무’ 표시 조문은 거의 모든 작업장에 걸리는 포괄 의무라, 이 사진의 핵심 위반이 아닐 수 있습니다.
        </p>
      )}

      {(rest > 0 || expanded) && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 text-xs font-medium text-slate-700 hover:text-slate-900 underline"
        >
          {expanded ? '접기' : `나머지 후보 ${rest}개 보기 (전체 ${items.length}개)`}
        </button>
      )}

      {commons.length > 0 && (
        <div className="mt-4 pt-3 border-t border-dashed border-slate-200">
          <h3 className="text-sm font-semibold text-gray-700">모든 현장 공통 점검항목</h3>
          <p className="text-xs text-gray-500 mb-2">
            어느 작업장에나 성립하는 포괄 의무라 <strong>이 사진의 위반이라는 뜻이 아닙니다.</strong>
            위 목록과 분리해 참고용으로만 표시합니다.
          </p>
          <ol className="space-y-2">
            {commons.map((c) => (
              <Row key={c.article_code} c={c} muted />
            ))}
          </ol>
        </div>
      )}
    </section>
  );
};

export default ArticleCandidatesPanel;
