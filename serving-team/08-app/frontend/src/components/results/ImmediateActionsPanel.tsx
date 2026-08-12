import React from 'react';
import type { CorrectiveAction } from '../../types/analysis';
import SourceBadge, { inferActionSource } from './SourceBadge';
import { CartoonButton, CartoonInlineCard, cartoonFor, useCartoonMode } from './articleCartoon';

interface ImmediateActionsPanelProps {
  items: CorrectiveAction[];
  findingStatus?: string;
}

const ImmediateActionsPanel: React.FC<ImmediateActionsPanelProps> = ({ items, findingStatus }) => {
  const needsClarification = findingStatus === 'needs_clarification';
  const cartoonMode = useCartoonMode();
  // 인라인 모드 dedup — 목록 내 같은 조문 카드는 첫 등장만
  const seenJo = new Set<string>();
  return (
    <section className="bg-white rounded-xl border border-orange-200 p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            {needsClarification ? '확인 필요 조치 후보' : '즉시 조치'}
          </h2>
          <p className="text-sm text-gray-500">
            {needsClarification
              ? '분석 단서만으로 확정하지 않고 현장에서 먼저 확인할 조치 후보입니다.'
              : '분석에서 확인된 위험을 먼저 줄이기 위한 조치입니다.'}
          </p>
        </div>
        {items[0]?.source_type === 'rule:Article' ? (
          <span className="text-[11px] px-2 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200 whitespace-nowrap">
            조문 기반 · 검수된 흐름에서 선별
          </span>
        ) : (
          <SourceBadge source="pg_asserted" extra="PG checklist_items" />
        )}
      </div>
      {items.length ? (
        <div className="space-y-2">
          {items.map((item, index) => {
            const source =
              item.source_type === 'app:VisualObservation'
                ? 'gpt'
                : inferActionSource(item.description);
            const isStatute = item.source_type === 'rule:Article';
            const jo = isStatute ? cartoonFor(item.action_id)?.jo : undefined;
            const inlineCard = cartoonMode === 'inline' && !!jo && !seenJo.has(jo);
            if (jo) seenJo.add(jo);
            return (
              <div key={`${item.action_id}#${index}`} className="rounded-lg bg-orange-50 px-3 py-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-medium text-gray-900 flex-1">
                    {index + 1}. {item.title}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {isStatute ? (
                      <span className="flex items-center gap-1">
                        <CartoonButton refText={item.action_id} />
                        <span className="text-[10px] px-1.5 py-0.5 rounded border bg-emerald-50 text-emerald-700 border-emerald-200 whitespace-nowrap">
                          조문 {item.action_id}
                        </span>
                      </span>
                    ) : (
                      <SourceBadge source={source} />
                    )}
                    {!isStatute && typeof item.confidence === 'number' && (
                      <span className="text-[10px] text-gray-500">신뢰도 {Math.round(item.confidence * 100)}%</span>
                    )}
                  </div>
                </div>
                {inlineCard ? (
                  /* 방식2: 설명 대신 카드(조문 원문 포함) — 비교 실험 */
                  <div className="mt-1">
                    <CartoonInlineCard refText={item.action_id} fallbackText={item.description ?? ''} />
                  </div>
                ) : (
                  item.description && <div className="text-xs text-gray-500 mt-1">{item.description}</div>
                )}
                <div className="text-xs text-orange-700 mt-1 flex gap-2">
                  {item.source_id && <span>{item.source_id}</span>}
                  {item.urgency && <span className="text-gray-400">[{item.urgency}]</span>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-gray-400">즉시 조치 후보가 없습니다.</p>
      )}
    </section>
  );
};

export default ImmediateActionsPanel;
