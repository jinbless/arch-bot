/**
 * 조문별 만화 카드 (2026-08-12) — 텍스트 행 유지 + '그림으로 보기' 확대 모달.
 * (방식1/방식2 토글 비교 후 방식1 확정 — 인라인 카드·토글은 철거됨, 2026-08-12 사용자 결정)
 *
 * 자산: frontend/public/cartoons/NNN.<해시8>.webp (git 미추적 — dev는 vite public, prod는
 * nginx bind-mount, 같은 URL `${BASE_URL}cartoons/…`). 매핑은 커밋된 manifest가 정본이며
 * backend/scripts/build_cartoon_assets.py 가 생성한다(수동 편집 금지).
 * 카드에 인쇄된 QR은 manifest의 q(URL+0~1 정규화 좌표)로 실현 — 모달에서 QR 영역 클릭
 * 오버레이 + 하단 '연관 콘텐츠' 링크.
 */
import React, { useEffect, useState } from 'react';
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

/** 카드에 인쇄된 QR 1개 — 디코딩된 URL + 카드 안 위치(0~1 정규화, build 스크립트가 생성) */
interface QrLink {
  u: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CartoonCard {
  jo: string;
  url: string;
  w: number;
  h: number;
  title: string;
  q: QrLink[];
}

const cards = (
  manifest as {
    cards: Record<string, { f: string; w: number; h: number; t: string; q?: QrLink[] }>;
  }
).cards;

/** ref → 만화 카드. **선두 앵커**가 핵심: '법 제38조'·'시행규칙 제99조'·가이드코드(B-E-21…)·
 *  '고시 제16조…'·작업명 평문은 선두가 `제N조`가 아니라 자연 탈락한다 — 만화는 규칙 조문만
 *  커버하므로(667종) 다른 법의 조번호에 규칙 카드가 붙는 오염을 이 한 줄이 막는다.
 *  '제35조제2항 · 별표 3 제10호' 류는 선두 조번호로 매칭(카드는 조 단위 1장). */
export const cartoonFor = (ref: string): CartoonCard | null => {
  const m = ref?.trim().match(/^제\d+조(의\d+)?/);
  if (!m) return null;
  const e = cards[m[0]];
  if (!e) return null; // 미보유(제227조·제4조의2 등)는 조용히 텍스트 유지
  return {
    jo: m[0],
    url: `${import.meta.env.BASE_URL}cartoons/${e.f}`,
    w: e.w,
    h: e.h,
    title: e.t,
    q: e.q ?? [],
  };
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
  const qrUrls = Array.from(new Set(card.q.map((q) => q.u))); // 카드당 1~3개, 중복 rect 방지
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
          {/* relative 래퍼가 img를 shrink-wrap — %-좌표 오버레이가 표시 크기와 무관하게 정렬된다
              (aspect-ratio + max 제약은 비율을 보존하므로 래퍼 박스 = 보이는 이미지) */}
          <div className="relative inline-block align-top">
            <img
              src={card.url}
              alt={`${card.jo} ${card.title} — 조문 원문과 만화 카드`}
              className="max-h-[78vh] max-w-[92vw] object-contain"
              style={{ aspectRatio: `${card.w}/${card.h}` }}
            />
            {/* 카드에 인쇄된 QR 영역 클릭 → 실제 링크(빌드타임 디코딩). 폰에서 QR을 찍을 수 없는
                화면 속 QR의 대체 경로 — 하단 '연관 콘텐츠' 링크와 같은 목적지 */}
            {card.q.map((q, i) => (
              <a
                key={`${q.u}#${i}`}
                href={q.u}
                target="_blank"
                rel="noreferrer"
                aria-label={`연관 콘텐츠 열기: ${q.u}`}
                title={`연관 콘텐츠 열기: ${q.u}`}
                className="absolute rounded ring-sky-400 hover:bg-sky-400/10 hover:ring-2"
                style={{
                  left: `${q.x * 100}%`,
                  top: `${q.y * 100}%`,
                  width: `${q.w * 100}%`,
                  height: `${q.h * 100}%`,
                }}
              />
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 px-3 py-1.5 text-[11px] text-gray-500">
          <span className="flex flex-wrap gap-3">
            {qrUrls.map((u, i) => (
              <a
                key={u}
                href={u}
                target="_blank"
                rel="noreferrer"
                className="font-medium text-sky-700 underline hover:text-sky-900"
                title={u}
              >
                연관 콘텐츠{qrUrls.length > 1 ? ` ${i + 1}` : ''}
              </a>
            ))}
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

/** '그림으로 보기' 버튼 — 만화가 없는 ref(법/시행령/가이드 등)면 아예 렌더 안 함. */
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
