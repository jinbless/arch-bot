/**
 * 조문별 만화 카드 (2026-08-12) — 고용노동부·KOSHA 「만화로 보는 산업안전보건기준에 관한 규칙」.
 *
 * ⚠ **비교 실험 스캐폴딩**: 방식1(텍스트 행 유지 + '그림으로 보기' 모달)과 방식2(행 본문을
 * 카드 이미지로 교체)를 토글로 함께 배포하고 사용자가 화면에서 직접 비교해 최종 선택한다.
 * 선택이 확정되면 탈락 방식과 토글을 제거할 것.
 *
 * 자산: frontend/public/cartoons/NNN.<해시8>.webp (git 미추적 — dev는 vite public, prod는
 * nginx bind-mount, 같은 URL `${BASE_URL}cartoons/…`). 매핑은 커밋된 manifest가 정본이며
 * backend/scripts/build_cartoon_assets.py 가 생성한다(수동 편집 금지).
 */
import React, { useEffect, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import manifest from '../../data/cartoons.manifest.json';

/** B0: 조문 ref → 국가법령정보센터 딥링크(`법령/<법령명>/<제N조>` pretty URL).
 *  접두사 없으면 산업안전보건기준에 관한 규칙 — 화면 각주의 표기 규약과 동일해야 한다.
 *  별표·고시·가이드 ref는 조문 패턴이 없어 자연히 링크 제외. (WorkFlowPanel에서 이관) */
const LAW_BY_PREFIX: Array<[RegExp, string]> = [
  [/^법\s*제/, '산업안전보건법'],
  [/^시행령\s*제/, '산업안전보건법 시행령'],
  [/^시행규칙\s*제/, '산업안전보건법 시행규칙'],
];
export const lawLink = (ref: string): string | null => {
  const jo = ref?.match(/제\d+조(의\d+)?/)?.[0];
  if (!jo) return null;
  const law = LAW_BY_PREFIX.find(([re]) => re.test(ref.trim()))?.[1] ?? '산업안전보건기준에 관한 규칙';
  return `https://law.go.kr/${encodeURIComponent('법령')}/${encodeURIComponent(law)}/${encodeURIComponent(jo)}`;
};

export const CARTOON_SOURCE = '고용노동부·KOSHA 「만화로 보는 산업안전보건기준에 관한 규칙」';

interface CartoonCard {
  jo: string;
  url: string;
  w: number;
  h: number;
  title: string;
}

const cards = (manifest as { cards: Record<string, { f: string; w: number; h: number; t: string }> })
  .cards;

/** ref → 만화 카드. **선두 앵커**가 핵심: '법 제38조'·'시행규칙 제99조'·가이드코드(B-E-21…)·
 *  '고시 제16조…'·작업명 평문은 선두가 `제N조`가 아니라 자연 탈락한다 — 만화는 규칙 조문만
 *  커버하므로(667종) 다른 법의 조번호에 규칙 카드가 붙는 오염을 이 한 줄이 막는다.
 *  '제35조제2항 · 별표 3 제10호' 류는 선두 조번호로 매칭(카드는 조 단위 1장). */
export const cartoonFor = (ref: string): CartoonCard | null => {
  const m = ref?.trim().match(/^제\d+조(의\d+)?/);
  if (!m) return null;
  const e = cards[m[0]];
  if (!e) return null; // 미보유(제227조·제4조의2 등)는 조용히 텍스트 유지
  return { jo: m[0], url: `${import.meta.env.BASE_URL}cartoons/${e.f}`, w: e.w, h: e.h, title: e.t };
};

// ── 표시 모드 (localStorage, 크로스탭 동기) ────────────────────────────
export type CartoonMode = 'modal' | 'inline';
const MODE_KEY = 'ohs.cartoon_mode_v1';
const listeners = new Set<() => void>();
const readMode = (): CartoonMode =>
  (localStorage.getItem(MODE_KEY) === 'inline' ? 'inline' : 'modal');
export const setCartoonMode = (m: CartoonMode) => {
  localStorage.setItem(MODE_KEY, m);
  listeners.forEach((l) => l());
};
const subscribe = (cb: () => void) => {
  listeners.add(cb);
  const onStorage = (e: StorageEvent) => e.key === MODE_KEY && cb();
  window.addEventListener('storage', onStorage);
  return () => {
    listeners.delete(cb);
    window.removeEventListener('storage', onStorage);
  };
};
export const useCartoonMode = (): CartoonMode => useSyncExternalStore(subscribe, readMode);

/** 화면 우하단 고정 토글 — ResultPage·BasicsPage에서만 마운트. 비교 실험용(선택 후 철거). */
export const CartoonModeToggle: React.FC = () => {
  const mode = useCartoonMode();
  return (
    <div className="fixed bottom-4 right-4 z-40 flex items-center gap-1 rounded-full border border-slate-300 bg-white/95 px-2 py-1 text-xs shadow-lg">
      <span className="px-1 text-gray-500">조문 표시</span>
      {(
        [
          ['modal', '글+그림보기'],
          ['inline', '그림 카드'],
        ] as const
      ).map(([m, label]) => (
        <button
          key={m}
          type="button"
          onClick={() => setCartoonMode(m)}
          className={`rounded-full px-2 py-0.5 ${
            mode === m ? 'bg-slate-800 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
};

// ── 확대 모달 ──────────────────────────────────────────────────────────
const CartoonLightbox: React.FC<{ card: CartoonCard; refText: string; onClose: () => void }> = ({
  card,
  refText,
  onClose,
}) => {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const link = lawLink(refText);
  return createPortal(
    // z-[60]: sticky 헤더(z-50)보다 위. createPortal(body) — 조상 transform/stacking 사고 회피.
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${card.jo} ${card.title} 만화 카드`}
      className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-full max-w-full flex-col overflow-hidden rounded-lg bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-3 py-2">
          <strong className="text-sm text-gray-900">
            {card.jo} {card.title}
          </strong>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="rounded px-2 py-0.5 text-sm text-slate-500 hover:bg-slate-100"
          >
            ✕ 닫기
          </button>
        </div>
        <div className="overflow-auto">
          <img
            src={card.url}
            alt={`${card.jo} ${card.title} — 조문 원문과 만화 카드`}
            className="max-h-[78vh] max-w-[92vw] object-contain"
            style={{ aspectRatio: `${card.w}/${card.h}` }}
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 px-3 py-1.5 text-[11px] text-gray-500">
          <span>{CARTOON_SOURCE}</span>
          <span className="flex gap-3">
            {/* 핀치/휠 줌 대신 브라우저 네이티브 줌에 위임 — v1 단순화 */}
            <a href={card.url} target="_blank" rel="noreferrer" className="underline hover:text-gray-800">
              원본 크기로 보기
            </a>
            {link && (
              <a href={link} target="_blank" rel="noreferrer" className="underline hover:text-gray-800">
                국가법령정보센터
              </a>
            )}
          </span>
        </div>
      </div>
    </div>,
    document.body
  );
};

/** 방식1: '그림으로 보기' 버튼 — 만화가 없는 ref(법/시행령/가이드 등)면 아예 렌더 안 함. */
export const CartoonButton: React.FC<{ refText: string; className?: string }> = ({
  refText,
  className,
}) => {
  const [open, setOpen] = useState(false);
  const card = cartoonFor(refText);
  if (!card) return null;
  const preload = () => {
    new Image().src = card.url;
  };
  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        onMouseEnter={preload}
        onFocus={preload}
        title={`${card.jo} ${card.title} — 만화 카드로 보기`}
        className={
          className ??
          'rounded border border-sky-300 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 hover:border-sky-500'
        }
      >
        그림으로 보기
      </button>
      {open && <CartoonLightbox card={card} refText={refText} onClose={() => setOpen(false)} />}
    </>
  );
};

/** 방식2: 인라인 카드 — 행 본문(텍스트+근거 인용)을 이미지로 교체. manifest w/h로 aspect-ratio를
 *  예약해 lazy 로드에도 CLS 0 → 기존 scrollIntoView 하이라이트와 간섭 없음. 로드 실패(자산
 *  미배치 환경)는 텍스트로 조용히 강등. 클릭 시 확대 모달. */
export const CartoonInlineCard: React.FC<{ refText: string; fallbackText: string }> = ({
  refText,
  fallbackText,
}) => {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const card = cartoonFor(refText);
  if (!card || failed) return <p className="text-sm text-gray-800">{fallbackText}</p>;
  return (
    <>
      <img
        src={card.url}
        alt={`${card.jo} ${card.title} — 조문 원문과 만화 카드`}
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
        onClick={() => setOpen(true)}
        title="클릭하면 크게 봅니다"
        className="w-full max-w-md cursor-zoom-in rounded border border-slate-200 bg-white"
        style={{ aspectRatio: `${card.w}/${card.h}` }}
      />
      {open && <CartoonLightbox card={card} refText={refText} onClose={() => setOpen(false)} />}
    </>
  );
};
