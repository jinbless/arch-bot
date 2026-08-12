"""조문별 만화 카드 자산 빌드 — PDF 667장 → WebP + 프론트 manifest (2026-08-12).

원본: data-team/06-조문별만화/*.pdf — 고용노동부·KOSHA 「만화로 보는 산업안전보건기준에 관한
규칙」의 조문 카드(1페이지에 제목+원문+만화+QR 합성, 폭 228~471pt·높이 105~658pt 가변).
임베디드 이미지 4~13개+텍스트 레이어의 합성물이라 **페이지 래스터화(get_pixmap)** 만이 원형을
보존한다(개별 이미지 추출로는 재구성 불가).

출력:
  frontend/public/cartoons/NNN.<해시8>.webp   — 숫자 인덱스 파일명(한글 URL 인코딩 함정 회피 —
                                                build_fp_viewer.py 선례) + 콘텐츠 해시(immutable
                                                캐시·증분·재렌더 캐시버스트 동시 해결). git 미추적.
  frontend/src/data/cartoons.manifest.json    — 조문키(제N조/제N조의M) → {f,w,h,t}. **추적**(프론트
                                                코드와 함께 버저닝 — articleCartoon.tsx가 import).

검증: 파일명 파싱 결과를 _목록.csv(cp949)와 전수 대조 — 불일치 시 abort(조용한 매핑 오염 방지).
증분: 같은 PDF+파라미터면 skip, 같은 인덱스의 구 해시 파일은 삭제(고아 방지).
실행: cd serving-team/08-app/backend && .venv/bin/python scripts/build_cartoon_assets.py
      (순수 파일 변환 — pymupdf+pillow만 있으면 아무 파이썬으로도 실행 가능. LLM/DB 0)
품질 게이트: 말미에 표본 3장 경로 출력 — 사람 눈검사(흐리면 ZOOM을 4로 올려 재실행,
             해시 파일명이라 캐시버스트는 자동).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]  # scripts→backend→08-app→serving-team→arch-bot
SRC = REPO / "data-team" / "06-조문별만화"
OUT_IMG = REPO / "serving-team" / "08-app" / "frontend" / "public" / "cartoons"
OUT_MANIFEST = REPO / "serving-team" / "08-app" / "frontend" / "src" / "data" / "cartoons.manifest.json"

ZOOM = 3.0          # 449pt 폭 기준 ~1350px — 실측 q75 ≈ 116KB/장
QUALITY = 75
PARAMS = f"zoom{ZOOM:g}-webp-q{QUALITY}"
NAME_RE = re.compile(r"^(\d{3})_(제\d+조(?:의\d+)?)_(.+)\.pdf$")
EXCLUDE = {"000_부칙_별표_등.pdf"}  # 32페이지 부칙·별표 모음 — 조문 카드 아님


def load_csv_index() -> dict:
    """_목록.csv(cp949: 순번,조문,제목,…,파일명) → 파일명 → (조문, 제목)."""
    out = {}
    with (SRC / "_목록.csv").open(encoding="cp949", newline="") as fh:
        for row in csv.DictReader(fh):
            fn = (row.get("파일명") or "").strip()
            if fn:
                out[fn] = ((row.get("조문") or "").strip(), (row.get("제목") or "").strip())
    return out


def main() -> None:
    pdfs = sorted(p for p in SRC.glob("*.pdf") if p.name not in EXCLUDE)
    csv_idx = load_csv_index()
    OUT_IMG.mkdir(parents=True, exist_ok=True)

    # ── 검증 먼저: 파일명 파싱 ↔ CSV 전수 대조 (불일치 시 abort) ──────────
    cards, errors = [], []
    seen_jo = set()
    for p in pdfs:
        m = NAME_RE.match(p.name)
        if not m:
            errors.append(f"파일명 형식 이탈: {p.name}")
            continue
        idx, jo, title = m.group(1), m.group(2), m.group(3)
        cv = csv_idx.get(p.name)
        if cv is None:
            errors.append(f"CSV에 없음: {p.name}")
        elif cv[0] != jo:
            errors.append(f"CSV 조문 불일치: {p.name} 파일명={jo} csv={cv[0]}")
        if jo in seen_jo:
            errors.append(f"조문 키 중복: {jo} ({p.name})")
        seen_jo.add(jo)
        cards.append((idx, jo, title, p))
    if errors:
        print(f"검증 실패 {len(errors)}건 — 변환하지 않음:")
        for e in errors[:20]:
            print("  ", e)
        sys.exit(1)
    print(f"검증 통과: 카드 {len(cards)}장 (CSV {len(csv_idx)}행)")

    # ── 변환 (증분) ────────────────────────────────────────────────────
    made = reused = removed = 0
    manifest_cards = {}
    for n, (idx, jo, title, p) in enumerate(cards, 1):
        raw = p.read_bytes()
        h8 = hashlib.sha256(raw + f"|{PARAMS}".encode()).hexdigest()[:8]
        dst = OUT_IMG / f"{idx}.{h8}.webp"
        for old in OUT_IMG.glob(f"{idx}.*.webp"):
            if old != dst:
                old.unlink()
                removed += 1
        if dst.exists():
            with Image.open(dst) as im:
                w, hgt = im.size
            reused += 1
        else:
            page = fitz.open(stream=raw, filetype="pdf")[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            im.save(dst, "WEBP", quality=QUALITY, method=6)
            w, hgt = im.size
            made += 1
        manifest_cards[jo] = {"f": dst.name, "w": w, "h": hgt, "t": title}
        if n % 100 == 0:
            print(f"  {n}/{len(cards)} …", flush=True)

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "_source": "고용노동부·KOSHA 「만화로 보는 산업안전보건기준에 관한 규칙」",
        "_note": "생성: backend/scripts/build_cartoon_assets.py — 수동 편집 금지. "
                 "이미지는 frontend/public/cartoons/(미추적·bind-mount 서빙), 이 manifest만 추적.",
        "_params": PARAMS,
        "n": len(manifest_cards),
        "cards": manifest_cards,
    }
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    total_kb = sum(f.stat().st_size for f in OUT_IMG.glob("*.webp")) // 1024
    print(f"\n생성 {made} · 재사용 {reused} · 구해시 삭제 {removed} · 총 {total_kb/1024:.1f}MB")
    print(f"manifest {len(manifest_cards)}키 → {OUT_MANIFEST.relative_to(REPO)}")
    print("\n표본 눈검사(품질 게이트 — 흐리면 ZOOM=4로 재실행):")
    for jo in ("제13조", "제172조", "제243조"):
        c = manifest_cards.get(jo)
        if c:
            print(f"  {jo} {c['t']}: {OUT_IMG.relative_to(REPO)}/{c['f']} ({c['w']}x{c['h']})")


if __name__ == "__main__":
    main()
