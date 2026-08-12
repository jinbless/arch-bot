import React, { useEffect, useState } from 'react';
import { flowApi, type AlwaysTopic } from '../api/flowApi';
import { CartoonButton } from '../components/results/articleCartoon';

/**
 * 기본 안전수칙 — **사진과 무관하게 늘 지켜야 하는 것**.
 *
 * 왜 별도 화면인가:
 *  - 작업 흐름 6칸은 사진에서 잡은 앵커에 매달린다. 앵커가 틀리면 흐름이 통째로 틀린다.
 *  - 그런데 작업장 시설·통로 구조·보호구 지급처럼 **시간축이 없고 현장이 늘 갖춰야 할 상태**인
 *    의무가 있다. 이런 건 앵커에 안 걸리면 사업주가 볼 방법이 아예 없다.
 *  - 여기는 **앵커 정확도와 무관하게 항상 맞는 유일한 화면**이다. 사진을 안 올려도 볼 수 있다.
 *
 * 표시 원칙은 흐름 패널과 같다 — 법정/권고를 섞지 않고, 근거 조문을 항상 같이 보여준다.
 */
const BasicsPage: React.FC = () => {
  const [topics, setTopics] = useState<AlwaysTopic[] | null>(null);
  const [total, setTotal] = useState(0);
  const [reviewed, setReviewed] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    flowApi
      .always()
      .then((d) => {
        if (!alive) return;
        setTopics(d.topics);
        setTotal(d.n_total);
        setReviewed(d.reviewed);
      })
      .catch(() =>
        alive &&
        setErr('기본 안전수칙을 불러오지 못했습니다. 작업 흐름 기능이 켜져 있는지 확인해 주세요.'),
      );
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <h1 className="text-2xl font-bold text-gray-900">기본 안전수칙</h1>
      <p className="mt-1 text-sm text-gray-600">
        사진과 관계없이 <strong>현장이 늘 갖추고 있어야 하는 것</strong>입니다. 특정 기계의 작업 흐름이
        아니라 어느 현장에나 걸립니다.
      </p>

      {err && <p className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{err}</p>}
      {!topics && !err && <p className="mt-6 text-sm text-gray-500">불러오는 중…</p>}

      {topics && (
        <>
          <div className="mt-4 space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
            <p>
              사진 분석의 <strong>작업 흐름</strong>은 사진에서 잡은 기계·장소에 따라 달라지지만, 이 목록은
              달라지지 않습니다. <strong>기인물을 잘못 잡아도 이 항목들은 그대로 유효합니다.</strong>
            </p>
            {!reviewed && (
              <p>각 항목이 어느 주제에 묶였는지는 아직 검수 전입니다. 조문 번호로 원문을 확인하세요.</p>
            )}
          </div>

          <div className="mt-5 space-y-4">
            {topics.map((t) => (
              <section key={t.name} className="rounded-xl border border-slate-200">
                <header className="border-b border-slate-100 bg-slate-50 px-3 py-2">
                  <div className="flex items-baseline gap-2">
                    <h2 className="text-base font-bold text-gray-900">{t.name}</h2>
                    <span className="text-xs text-gray-500">{t.n}건</span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500">{t.desc}</p>
                </header>
                <ol className="space-y-1.5 p-2.5">
                  {t.items.map((it, i) => (
                    <li key={`${t.name}-${i}`} className="rounded-lg border border-gray-100 bg-white p-2.5">
                      <div className="flex items-start gap-2">
                        <span
                          title={
                            it.tier === '법정'
                              ? '법령이 정한 의무 — 이행하지 않으면 위반이 될 수 있습니다'
                              : 'KOSHA 가이드의 권장 절차 — 법적 의무는 아닙니다'
                          }
                          className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
                            it.tier === '법정'
                              ? 'border-slate-800 bg-slate-800 text-white'
                              : 'border-slate-300 bg-white text-slate-500'
                          }`}
                        >
                          {it.tier}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-gray-800">{it.text}</p>
                          {it.evidence && (
                            <p className="mt-1 border-l-2 border-slate-200 pl-2 text-[12px] leading-snug text-gray-600">
                              “{it.evidence}”
                            </p>
                          )}
                          <p className="mt-0.5 text-[11px] text-gray-400">
                            {it.ref}
                            {it.ref && it.group ? ' · ' : ''}
                            {it.group}
                            <span className="ml-1.5">
                              <CartoonButton refText={it.ref} />
                            </span>
                          </p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            ))}
          </div>

          <p className="mt-4 text-[11px] text-gray-400">
            총 {total}건 · 출처: 산업안전보건기준에 관한 규칙
            <br />
            특정 기계·설비의 작업 흐름은 사진을 올리면 볼 수 있습니다. 조문 번호 앞에 법 이름이 없으면
            산업안전보건기준에 관한 규칙입니다.
          </p>
        </>
      )}
    </div>
  );
};

export default BasicsPage;
