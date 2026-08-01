import React, { useMemo, useState } from 'react';
import type { FlowItem, FlowSlot, WorkFlow } from '../../types/analysis';

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

const Item: React.FC<{ it: FlowItem }> = ({ it }) => {
  const tier = TIER_META[it.tier] ?? TIER_META.법정;
  return (
    <li className="rounded-lg border border-gray-100 bg-white p-2.5">
      <div className="flex items-start gap-2">
        <span
          title={tier.title}
          className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${tier.cls}`}
        >
          {tier.label}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-gray-800">{it.text}</p>
          <p className="mt-0.5 text-[11px] text-gray-400">
            {it.ref}
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

const Slot: React.FC<{ slot: FlowSlot }> = ({ slot }) => {
  const [open, setOpen] = useState(false);
  const 법정 = useMemo(() => slot.items.filter((i) => i.tier === '법정'), [slot.items]);
  const 권고 = useMemo(() => slot.items.filter((i) => i.tier === '권고'), [slot.items]);
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
              <Item key={`${slot.key}-${i}`} it={it} />
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

const WorkFlowPanel: React.FC<{
  flow?: WorkFlow | null;
  /** 앵커 정정. 미지정이면 대안을 '표시만' 한다(백엔드 재조회 없이). */
  onPickAnchor?: (groupKey: string) => void;
}> = ({ flow, onPickAnchor }) => {
  if (!flow) return null;
  const { anchor, alternates, slots, reviewed } = flow;
  const total = slots.reduce((n, s) => n + s.items.length, 0);

  return (
    <section className="rounded-xl border border-slate-300 bg-white p-4">
      <div className="mb-3">
        <h2 className="text-lg font-bold text-gray-900">
          이 기인물의 작업 흐름 <span className="text-slate-500">(참고 자료)</span>
        </h2>
        <p className="text-sm text-gray-500">
          사진은 작업의 <strong>한 시점</strong>입니다. 사진에서 확인된 기인물을 기준으로, 그 앞뒤로 해야 할
          일을 규칙·고시·가이드에서 모아 보여줍니다.
        </p>
      </div>

      {/* ① 앵커 — 흐름 전체가 여기에 걸린다 */}
      <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="text-xs text-gray-500">사진에서 확인된 기인물</span>
          <strong className="text-base text-gray-900">{anchor.label}</strong>
          {anchor.is_inspection_target && (
            <span
              title="산업안전보건법 제93조 안전검사 대상"
              className="rounded border border-slate-800 bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold text-white"
            >
              안전검사 대상
            </span>
          )}
        </div>
        {anchor.path && <p className="mt-0.5 text-[11px] text-gray-400">{anchor.path}</p>}

        {alternates.length > 0 && (
          <div className="mt-2 border-t border-dashed border-slate-200 pt-2">
            <p className="text-xs text-gray-600">
              기인물이 <strong>다르면</strong> 아래 흐름 전체가 맞지 않습니다. 사진에서 함께 확인된 것:
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {alternates.map((a) => (
                <button
                  key={a.group_key}
                  type="button"
                  onClick={() => onPickAnchor?.(a.group_key)}
                  title={a.path}
                  disabled={!onPickAnchor}
                  className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:border-slate-500 disabled:cursor-default disabled:opacity-70"
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ② 신뢰 고지 — tooltip에 숨기지 않는다(폰 스크린샷 전달이 주 경로) */}
      <div className="mb-3 space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs leading-relaxed text-slate-700">
        <p>
          <strong>기인물을 잘못 잡으면 아래 흐름 전체가 어긋납니다.</strong> 먼저 위의 기인물이 맞는지
          확인하세요.
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

      {/* ③ 타임라인 — 단계에 번호를 매기지 않는다 */}
      <div className="space-y-2">
        {slots.map((s) => (
          <Slot key={s.key} slot={s} />
        ))}
      </div>

      <p className="mt-3 text-[11px] text-gray-400">
        총 {total}건 · 출처: 산업안전보건기준규칙, 같은 규칙 별표 2·3·4, 안전검사 고시, KOSHA 가이드
      </p>
    </section>
  );
};

export default WorkFlowPanel;
