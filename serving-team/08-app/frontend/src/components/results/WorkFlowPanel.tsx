import React, { useEffect, useMemo, useRef, useState } from 'react';
import { flowApi, type FlowGroup } from '../../api/flowApi';
import { TrustBadge } from './SourceBadge';
import type { AiActionAlignment, CorrectiveAction, FlowItem, FlowSlot, WorkFlow } from '../../types/analysis';

/** B0: 조문 ref → 국가법령정보센터 딥링크(`법령/<법령명>/<제N조>` pretty URL).
 *  접두사 없으면 산업안전보건기준에 관한 규칙 — 화면 각주의 표기 규약과 동일해야 한다.
 *  별표·고시·가이드 ref는 조문 패턴이 없어 자연히 링크 제외. */
const LAW_BY_PREFIX: Array<[RegExp, string]> = [
  [/^법\s*제/, '산업안전보건법'],
  [/^시행령\s*제/, '산업안전보건법 시행령'],
  [/^시행규칙\s*제/, '산업안전보건법 시행규칙'],
];
const lawLink = (ref: string): string | null => {
  const jo = ref?.match(/제\d+조(의\d+)?/)?.[0];
  if (!jo) return null;
  const law = LAW_BY_PREFIX.find(([re]) => re.test(ref.trim()))?.[1] ?? '산업안전보건기준에 관한 규칙';
  return `https://law.go.kr/${encodeURIComponent('법령')}/${encodeURIComponent(law)}/${encodeURIComponent(jo)}`;
};

/**
 * 기인물 앵커 기준 **작업 전체 흐름** 패널 (표시전용).
 *
 * 제품 전제: 사진은 작업 흐름의 한 시점 스냅샷이다. 그 시점만 보여주면 앞뒤로 해야 할 일을 알 수 없다.
 * → 사진에서 기인물을 잡고, 그걸 기준으로 계획 → 인적배치 → 작업 전 → 작업 중 → 종료 → 정기 를 보여준다.
 *
 * 표시 원칙:
 *  - **단계에 번호를 매기지 않는다.** '6단계 중 4단계'는 시간 추론이라 미측정 오류원이 된다.
 *  - **법정과 권고를 섞지 않는다.** 안전검사·조문은 안 하면 위법이고, KOSHA 가이드는 권고다.
 *    같은 목록에 두면 사업주가 '해야 하는 것'과 '하면 좋은 것'을 구별하지 못한다.
 *  - **앵커 정정 장치는 선택이 아니다.** 기인물 인식 정확도가 0.711이라 4장 중 1장 이상이
 *    통째로 틀린다. 틀렸을 때 사용자가 바로잡을 길이 없으면 흐름 전체가 오안내가 된다.
 *  - **빈 칸을 그냥 비워두지 않는다.** '자료가 없음'과 '해당 없음'은 다른 말이고,
 *    후자를 전자로 읽으면 점검을 안 해도 되는 것으로 오해한다.
 *  - 위험등급 색(amber/red)을 쓰지 않는다 — 같은 페이지의 위험도 칩과 섞이면 흐름이 위험 판정으로 읽힌다.
 */

const TIER_META: Record<string, { label: string; cls: string; title: string }> = {
  법정: {
    label: '법정',
    cls: 'bg-slate-800 text-white border-slate-800',
    title: '법령·고시가 정한 의무 — 이행하지 않으면 위반이 될 수 있습니다',
  },
  권고: {
    label: '권고',
    cls: 'bg-white text-slate-500 border-slate-300',
    title: 'KOSHA 가이드의 권장 절차 — 법적 의무는 아닙니다',
  },
};

const Item: React.FC<{ it: FlowItem; actNow?: boolean; highlighted?: boolean; hlN?: number }> = ({
  it,
  actNow,
  highlighted,
  hlN,
}) => {
  const tier = TIER_META[it.tier] ?? TIER_META.법정;
  const el = useRef<HTMLLIElement>(null);
  // '지금 당장' 스트립·AI 대조에서 눌러 이동해 온 항목 — hlN을 deps에 두어 같은 항목 재클릭도 다시 스크롤한다
  useEffect(() => {
    if (highlighted) el.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [highlighted, hlN]);
  return (
    <li
      ref={el}
      className={`rounded-lg border bg-white p-2.5 ${
        highlighted ? 'border-orange-400 ring-2 ring-orange-200' : 'border-gray-100'
      }`}
    >
      <div className="flex items-start gap-2">
        <span
          title={tier.title}
          className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${tier.cls}`}
        >
          {tier.label}
        </span>
        {actNow && (
          <span
            title="이 사진의 사고형태 기준으로 위 ‘지금 당장’에 선별된 조문입니다"
            className="mt-0.5 shrink-0 rounded border border-orange-400 bg-orange-50 px-1.5 py-0.5 text-[10px] font-semibold text-orange-700"
          >
            지금
          </span>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm text-gray-800">{it.text}</p>
          {/* 이 항목이 왜 이 단계에 있는지 — 조문 원문 문구 그대로.
              같은 조문이 두 단계에 걸치는 경우(제35조 = 인적 배치 + 작업 전 점검)
              제목만 보면 중복으로 읽힌다. 근거를 보여야 다른 의무임을 안다. */}
          {it.evidence && (
            <p className="mt-1 border-l-2 border-slate-200 pl-2 text-[12px] leading-snug text-gray-600">
              “{it.evidence}”
            </p>
          )}
          <p className="mt-0.5 text-[11px] text-gray-400">
            {it.ref && lawLink(it.ref) ? (
              <a
                href={lawLink(it.ref)!}
                target="_blank"
                rel="noreferrer"
                title="국가법령정보센터에서 원문 보기"
                className="underline decoration-dotted underline-offset-2 hover:text-gray-600"
              >
                {it.ref}
              </a>
            ) : (
              it.ref
            )}
            {it.ref && it.source ? ' · ' : ''}
            {it.source}
            {it.uncertain && (
              <span
                title="이름이 비슷해 연결한 항목이라 이 기인물과 무관할 수 있습니다"
                className="ml-1 text-gray-500"
              >
                (연결 확인 필요)
              </span>
            )}
          </p>
        </div>
      </div>
    </li>
  );
};

const PREVIEW = 4;

const Slot: React.FC<{
  slot: FlowSlot;
  actNowRefs?: Set<string>;
  hlRef?: string;
  hlN?: number;
}> = ({ slot, actNowRefs, hlRef, hlN }) => {
  const [open, setOpen] = useState(false);
  const 법정 = useMemo(() => slot.items.filter((i) => i.tier === '법정'), [slot.items]);
  const 권고 = useMemo(() => slot.items.filter((i) => i.tier === '권고'), [slot.items]);
  // 이동 목적지가 미리보기(4건) 뒤에 접혀 있으면 펼친다 — 안 펼치면 스크롤 목적지가 DOM에 없다
  useEffect(() => {
    if (hlRef && slot.items.slice(PREVIEW).some((i) => i.ref === hlRef)) setOpen(true);
  }, [hlRef, hlN, slot.items]);
  const shown = open ? slot.items : slot.items.slice(0, PREVIEW);
  const rest = slot.items.length - shown.length;

  return (
    <section className="rounded-xl border border-slate-200">
      <header className="flex items-baseline gap-2 border-b border-slate-100 bg-slate-50 px-3 py-2">
        <h3 className="text-sm font-bold text-gray-900">{slot.label}</h3>
        <span className="text-xs text-gray-500">
          {slot.items.length ? `${slot.items.length}건` : '자료 없음'}
        </span>
        {법정.length > 0 && 권고.length > 0 && (
          <span className="ml-auto text-[11px] text-gray-400">
            법정 {법정.length} · 권고 {권고.length}
          </span>
        )}
      </header>

      {slot.items.length ? (
        <>
          <ol className="space-y-1.5 p-2.5">
            {shown.map((it, i) => (
              <Item
                key={`${slot.key}-${i}`}
                it={it}
                actNow={!!it.ref && actNowRefs?.has(it.ref)}
                highlighted={!!hlRef && it.ref === hlRef}
                hlN={hlN}
              />
            ))}
          </ol>
          {(rest > 0 || open) && (
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="mb-2.5 ml-3 text-xs font-medium text-slate-700 underline hover:text-slate-900"
            >
              {open ? '접기' : `나머지 ${rest}건 보기 (전체 ${slot.items.length}건)`}
            </button>
          )}
        </>
      ) : (
        <p className="p-3 text-xs leading-relaxed text-gray-500">{slot.empty_reason}</p>
      )}
    </section>
  );
};

/** 기인물 선택기 — 대안 칩만으로는 완전 오인식(26.7%)을 고칠 수 없어 전체에서 찾게 한다. */
const AnchorPicker: React.FC<{ current: string; onPick: (k: string) => void; onClose: () => void }> = ({
  current,
  onPick,
  onClose,
}) => {
  const [groups, setGroups] = useState<FlowGroup[] | null>(null);
  const [q, setQ] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    flowApi
      .listGroups()
      .then((g) => alive && setGroups(g))
      .catch(() => alive && setErr('목록을 불러오지 못했습니다.'));
    return () => {
      alive = false;
    };
  }, []);

  const hits = useMemo(() => {
    if (!groups) return [];
    const k = q.trim();
    const pool = k ? groups.filter((g) => g.label.includes(k) || g.path.includes(k)) : groups;
    return pool.slice(0, 40);
  }, [groups, q]);

  return (
    <div className="mt-2 rounded-lg border border-slate-300 bg-white p-2.5">
      <div className="flex items-center gap-2">
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="기인물 검색 (예: 지게차, 비계, 전기)"
          className="flex-1 rounded border border-slate-300 px-2 py-1 text-sm outline-none focus:border-slate-500"
        />
        <button type="button" onClick={onClose} className="text-xs text-slate-500 underline">
          닫기
        </button>
      </div>
      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}
      {!groups && !err && <p className="mt-2 text-xs text-gray-500">불러오는 중…</p>}
      {groups && (
        <>
          <p className="mt-1.5 text-[11px] text-gray-400">
            전체 {groups.length}종 중 {hits.length}종 표시{q ? '' : ' (검색해서 좁히세요)'}
          </p>
          <ul className="mt-1 max-h-64 divide-y divide-slate-100 overflow-auto">
            {hits.map((g) => (
              <li key={g.group_key}>
                <button
                  type="button"
                  disabled={g.group_key === current}
                  onClick={() => onPick(g.group_key)}
                  className="w-full px-1.5 py-1.5 text-left hover:bg-slate-50 disabled:opacity-40"
                >
                  <span className="text-sm text-gray-800">{g.label}</span>
                  {/* 사진으로 지목할 수 없는 칸은 고르기 전에 알려준다. 목록에서 빼지는 않는다 */}
                  {g.kind === '부적격' && (
                    <span
                      title="규칙의 편제상 분류(통칙·보호구·관리 등)라 작업 흐름이 성립하지 않습니다"
                      className="ml-1.5 rounded border border-slate-300 px-1 text-[9px] text-slate-500"
                    >
                      사진 지목 불가
                    </span>
                  )}
                  {g.is_inspection_target && (
                    <span className="ml-1.5 rounded border border-slate-800 px-1 text-[9px] font-semibold text-slate-800">
                      안전검사
                    </span>
                  )}
                  <span className="ml-1.5 text-[11px] text-gray-400">{g.n_items}건</span>
                  <span className="block text-[11px] text-gray-400">{g.path}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

const WorkFlowPanel: React.FC<{
  flow?: WorkFlow | null;
  /** '지금 당장' — 이 흐름의 조문에서 자동 선별된 즉시조치(source_type=rule:Article) */
  actNow?: CorrectiveAction[];
  /** AI 자유 제안 ↔ 흐름 조문 정렬 결과 */
  aiAlignments?: AiActionAlignment[];
}> = ({ flow, actNow = [], aiAlignments = [] }) => {
  // 원본(모델이 인식한 결과)과 현재 보고 있는 흐름을 나눠 둔다 — 되돌아갈 길을 남긴다.
  const [current, setCurrent] = useState<WorkFlow | null>(null);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  // 스트립·AI 대조에서 흐름 항목으로 이동 — n을 올려 같은 항목 재클릭도 다시 스크롤되게 한다.
  // slot을 함께 들면 같은 조문이 여러 칸에 있을 때(제35조류) 매칭된 칸만 하이라이트한다.
  const [hl, setHl] = useState<{ ref: string; slot: string; n: number }>({ ref: '', slot: '', n: 0 });
  const jumpTo = (ref: string, slot = '') => setHl((p) => ({ ref, slot, n: p.n + 1 }));
  const clearHl = () => setHl({ ref: '', slot: '', n: 0 });
  const actNowRefs = useMemo(() => new Set(actNow.map((a) => a.action_id)), [actNow]);

  useEffect(() => {
    setCurrent(null);
    setPicking(false);
    setErr('');
    setHl({ ref: '', slot: '', n: 0 });
  }, [flow]);

  const shown = current ?? flow;
  const corrected = current !== null;

  const pick = async (key: string) => {
    if (!flow) return;
    setBusy(true);
    setErr('');
    try {
      const keep = [flow.anchor.group_key, ...flow.alternates.map((a) => a.group_key)];
      const next = await flowApi.byGroupKey(key, {
        alternates: keep,
        fromGroupKey: shown?.anchor.group_key,
      });
      setCurrent(next);
      setPicking(false);
      // 하이라이트는 원 흐름 기준 값 — 남겨두면 '되돌리기' 순간 stale ref로 자동 스크롤이 튄다
      clearHl();
    } catch {
      setErr('해당 기인물의 흐름을 불러오지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  if (!flow || !shown) return null;
  const { anchor, alternates, slots, reviewed } = shown;
  const total = slots.reduce((n, s) => n + s.items.length, 0);

  // B0: matched 제안의 근거 발췌를 인라인으로 — 인용 링크는 거의 클릭되지 않는다는 실측(NN/g)
  // 때문에 점프는 보조이고 발췌가 주력이어야 한다. 스크린샷 유통에서도 발췌만 살아남는다.
  const evidenceFor = (al: AiActionAlignment): string => {
    for (const s of slots) {
      if (al.slot_key && s.key !== al.slot_key) continue;
      const hit =
        s.items.find((i) => i.ref === al.matched_ref && (!al.matched_title || i.text === al.matched_title)) ??
        s.items.find((i) => i.ref === al.matched_ref);
      if (hit?.evidence) return hit.evidence;
    }
    return '';
  };
  const nMatched = aiAlignments.filter((a) => a.status === 'matched').length;
  const nUnmatched = aiAlignments.filter((a) => a.status === 'unmatched').length;
  const nPending = aiAlignments.length - nMatched - nUnmatched;

  return (
    <section className="rounded-xl border border-slate-300 bg-white p-4">
      <div className="mb-3">
        <h2 className="flex flex-wrap items-center gap-2 text-lg font-bold text-gray-900">
          이 기인물의 작업 흐름 <TrustBadge level="reviewed" />
        </h2>
        <p className="text-sm text-gray-500">
          사진은 작업의 <strong>한 시점</strong>입니다. 사진에서 확인된 기인물을 기준으로 그 앞뒤로 해야 할
          일을 규칙·고시·가이드에서 모으고, 그중 <strong>지금 당장 할 조치</strong>를 먼저 보여줍니다.
        </p>
        {/* B0: 검수 사실을 라벨이 아니라 **이력**으로 — 근거는 flow_service.LABELS_REVIEWED 주석과 동일.
            숫자가 바뀌면 그쪽과 같이 갱신한다(검수 체계가 바뀌는 일 자체가 드묾). */}
        <p className="mt-1 text-[11px] text-gray-400">
          검수 이력: Sol 전수 재판정 885건 + 우선순위 사람 검수 + 서빙 전 게이트 감사 (2026-08 기준)
        </p>
      </div>

      {/* ① 앵커 — 흐름 전체가 여기에 걸린다 */}
      <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="text-xs text-gray-500">
            {corrected ? '직접 고른 기인물' : '사진에서 확인된 기인물'}
          </span>
          <strong className="text-base text-gray-900">{anchor.label}</strong>
          {anchor.is_inspection_target && (
            <span
              title={
                anchor.inspection_scopes?.length
                  ? `산업안전보건법 제93조 안전검사 — 다음 범위에만 해당합니다\n${anchor.inspection_scopes.join('\n')}`
                  : '산업안전보건법 제93조 안전검사 대상'
              }
              className="rounded border border-slate-800 bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold text-white"
            >
              안전검사 대상{anchor.inspection_scopes?.length ? ' (조건 있음)' : ''}
            </span>
          )}
          {busy && <span className="text-xs text-gray-400">불러오는 중…</span>}
        </div>
        {anchor.path && <p className="mt-0.5 text-[11px] text-gray-400">{anchor.path}</p>}

        <div className="mt-2 border-t border-dashed border-slate-200 pt-2">
          <p className="text-xs text-gray-600">
            기인물이 <strong>다르면</strong> 아래 흐름 전체가 맞지 않습니다.
            {alternates.length > 0 ? ' 사진에서 함께 확인된 것:' : ' 직접 고를 수 있습니다.'}
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {alternates.map((a) => (
              <button
                key={a.group_key}
                type="button"
                onClick={() => pick(a.group_key)}
                title={a.path}
                disabled={busy}
                className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:border-slate-500 disabled:opacity-50"
              >
                {a.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setPicking((v) => !v)}
              disabled={busy}
              className="rounded-full border border-dashed border-slate-400 bg-white px-2.5 py-1 text-xs text-slate-600 hover:border-slate-600 disabled:opacity-50"
            >
              {picking ? '검색 닫기' : '＋ 목록에서 직접 찾기'}
            </button>
            {corrected && (
              <button
                type="button"
                onClick={() => {
                  setCurrent(null);
                  clearHl(); // stale 하이라이트가 복귀 순간 자동 스크롤을 일으키지 않도록
                }}
                disabled={busy}
                className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-500 underline hover:text-slate-800 disabled:opacity-50"
              >
                처음 인식으로 되돌리기
              </button>
            )}
          </div>
          {err && <p className="mt-1.5 text-xs text-red-600">{err}</p>}
          {picking && (
            <AnchorPicker current={anchor.group_key} onPick={pick} onClose={() => setPicking(false)} />
          )}
        </div>
      </div>

      {/* ①-1 '지금 당장' 스트립 — 즉시조치는 이 흐름 조문의 부분집합이다(한 카테고리, 두 시점).
          별도 패널로 두면 같은 조문이 화면에 두 번 나와 출처가 흐려진다(2026-08-09 통합).
          앵커를 직접 정정한 뒤에는 감춘다 — 선별은 원래 인식된 흐름 기준으로 계산된 값이라
          정정된 흐름에 그대로 얹으면 근거 없는 조문을 가리키게 된다. */}
      {!corrected && actNow.length > 0 && (
        <div className="mb-3 rounded-lg border border-orange-300 bg-orange-50 p-3">
          <div className="flex flex-wrap items-baseline gap-2">
            <h3 className="text-sm font-bold text-orange-900">지금 당장</h3>
            <span className="text-[11px] text-orange-800">
              아래 흐름의 조문 중 이 사진의 사고형태 기준으로 자동 선별 — 누르면 근거 위치로 이동합니다
            </span>
          </div>
          <ol className="mt-2 space-y-1">
            {actNow.map((a, i) => (
              <li key={a.action_id}>
                <button
                  type="button"
                  onClick={() => jumpTo(a.action_id)}
                  className="flex w-full items-start justify-between gap-2 rounded-lg border border-orange-200 bg-white px-3 py-2 text-left hover:border-orange-400"
                >
                  <span className="text-sm font-medium text-gray-900">
                    {i + 1}. {a.title}
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    {a.urgency !== 'immediate' && (
                      <span
                        title="법정 의무지만 구매·설치 등이 필요해 ‘지금 당장’보다는 계획해서 할 조치입니다"
                        className="text-[10px] text-gray-400"
                      >
                        계획 조치
                      </span>
                    )}
                    <span className="rounded border border-orange-300 bg-orange-50 px-1.5 py-0.5 text-[10px] font-semibold text-orange-700">
                      {a.action_id}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}
      {corrected && (actNow.length > 0 || aiAlignments.length > 0) && (
        <p className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-600">
          직접 고른 기인물 기준에서는 ‘지금 당장’ 선별과 AI 제안 대조를 다시 계산하지 않습니다 — 아래
          흐름 항목을 직접 확인하세요.
        </p>
      )}

      {/* ② 신뢰 고지 — tooltip에 숨기지 않는다(폰 스크린샷 전달이 주 경로) */}
      <div className="mb-3 space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs leading-relaxed text-slate-700">
        {/* ★ 앵커가 규칙 편제상의 칸(통칙·보호구·관리)으로 떨어진 경우. 흐름이 의미가 없으므로
            빈 칸을 보여주며 넘어가지 말고, 사용자가 실제 기인물을 고르도록 말해준다. */}
        {anchor.kind === '부적격' && (
          <p className="rounded border border-slate-400 bg-white p-2">
            <strong>이 항목은 사진에서 지목할 수 있는 기인물이 아닙니다.</strong> 규칙의 편제상 분류
            (통칙·보호구·관리 등)라 작업 흐름이 성립하지 않습니다.
            {anchor.kind_why ? ` ${anchor.kind_why}` : ''} 위의 <strong>‘＋ 목록에서 직접 찾기’</strong>로
            사진 속 기계·장소를 골라 주세요.
          </p>
        )}
        <p>
          <strong>기인물을 잘못 잡으면 아래 흐름 전체가 어긋납니다.</strong> 먼저 위의 기인물이 맞는지
          확인하세요.
          {corrected && ' 지금은 직접 고른 기인물 기준으로 보고 있습니다.'}
        </p>
        {!reviewed && (
          <p>
            각 항목이 <strong>해당 단계에 맞게 배치되었는지는 아직 검수 전</strong>입니다. 순서와 시점은
            참고로만 보시고, 조문 번호로 원문을 확인하세요.
          </p>
        )}
        <p>
          사진에 안 보이는 것(작업계획서·자격·정기검사 이력 등)은 <strong>확인한 것이 아니라</strong> 해당
          기인물에 일반적으로 요구되는 항목을 모아 놓은 것입니다.
        </p>
      </div>

      {/* ③ 타임라인 — 단계에 번호를 매기지 않는다.
          '지금' 배지는 PRECHECK·EXEC에만 준다 — 선별 모집단이 그 두 칸이라, 같은 조문이
          다른 칸에도 있으면(제35조류) 배지가 엉뚱한 시점에 붙는다. */}
      <div className="space-y-2">
        {slots.map((s) => (
          <Slot
            key={s.key}
            slot={s}
            actNowRefs={
              !corrected && (s.key === 'PRECHECK' || s.key === 'EXEC') ? actNowRefs : undefined
            }
            hlRef={corrected || (hl.slot !== '' && hl.slot !== s.key) ? '' : hl.ref}
            hlN={hl.n}
          />
        ))}
      </div>

      {/* ④ AI 제안 대조 — matched는 조문으로 점프, unmatched는 '구체 조문 불비 후보'(백엔드 원장 적립).
          unaligned(정렬 실패·구 기록)는 불비로 표기하지 않는다 — 판정과 판정 실패는 다른 상태다. */}
      {!corrected && aiAlignments.length > 0 && (
        <div className="mt-3 rounded-lg border border-violet-200 bg-violet-50/60 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-violet-900">AI 제안 대조</h3>
            <TrustBadge level="ai" extra="정렬 검수 전" />
            {/* B0: 대조 결과를 한 줄로 — 인용을 클릭해 확인하는 사용자는 드물다(NN/g 실측) */}
            <span className="text-[11px] font-medium text-violet-800">
              AI 제안 {aiAlignments.length}건 — 조문 일치 {nMatched} · 대응 없음 {nUnmatched}
              {nPending > 0 ? ` · 대조 전 ${nPending}` : ''}
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-violet-700">
            AI가 사진에서 낸 조치 제안을 위 확정 의무와 대조한 결과입니다
          </p>
          <ul className="mt-2 space-y-1.5">
            {aiAlignments.map((al, i) => (
              <li key={i} className="rounded-lg border border-violet-100 bg-white px-3 py-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <span className="min-w-0 flex-1 text-sm text-gray-800">{al.text}</span>
                  {al.status === 'matched' ? (
                    <button
                      type="button"
                      onClick={() => jumpTo(al.matched_ref, al.slot_key)}
                      title={al.reason || al.matched_title}
                      className="shrink-0 rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 hover:border-emerald-500"
                    >
                      {al.matched_ref}와 같은 취지 →
                    </button>
                  ) : al.status === 'unmatched' ? (
                    <span
                      title={al.reason || undefined}
                      className="shrink-0 rounded-full border border-violet-300 bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700"
                    >
                      흐름 조문에 대응 없음 — 구체 조문 불비 후보
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full border border-gray-300 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-500">
                      대조 전
                    </span>
                  )}
                </div>
                {/* B0: 근거 발췌를 인라인으로 — 점프(칩)는 보조 */}
                {al.status === 'matched' && evidenceFor(al) && (
                  <p className="mt-1 border-l-2 border-emerald-200 pl-2 text-[12px] leading-snug text-gray-600">
                    “{evidenceFor(al)}”
                  </p>
                )}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] leading-relaxed text-violet-800/80">
            ‘대응 없음’은 위법이 아니라는 뜻이 아닙니다 — 포괄 의무조항(산업안전보건법 제38·39조)이
            적용될 수 있습니다. 대응 없는 제안은 별도 원장에 적립해 구체 조문 공백 검토 자료로 씁니다.
          </p>
        </div>
      )}

      <p className="mt-3 text-[11px] text-gray-400">
        총 {total}건 · 출처: 산업안전보건법·시행령·시행규칙, 산업안전보건기준규칙과 같은 규칙 별표 2·3·4,
        안전검사 고시, KOSHA 가이드
        <br />
        {/* 조문 번호만 보면 '제99조'(규칙)와 '시행규칙 제99조'가 같은 것처럼 읽힌다.
            법령에서 온 항목은 ref 앞에 법 이름을 붙여 구별한다. */}
        조문 번호 앞에 법 이름이 없으면 산업안전보건기준에 관한 규칙입니다.
      </p>
    </section>
  );
};

export default WorkFlowPanel;
