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

QR 링크(2026-08-12 추가): 카드마다 인쇄된 QR(임베디드 이미지 ~158±40px)을 opencv로 디코딩해
manifest에 `q:[{u,x,y,w,h}]`(URL + 0~1 정규화 좌표)로 싣는다 — 모달에서 클릭 오버레이/'연관
콘텐츠' 링크로 실현. PDF에 링크 annotation은 없어(전수 0건) 이미지 디코딩만이 경로다.
좌표는 page.get_image_rects() 페이지 좌표를 페이지 크기로 나눈 값 — 렌더 배율과 무관.

검증: 파일명 파싱 결과를 _목록.csv(cp949)와 전수 대조 — 불일치 시 abort(조용한 매핑 오염 방지).
증분: 같은 PDF+파라미터면 skip, 같은 인덱스의 구 해시 파일은 삭제(고아 방지). QR 디코딩은
      WebP 해시에 안 들어가므로 재실행해도 이미지는 불변(재배포는 manifest+프론트만).
실행: cd serving-team/08-app/backend && .venv/bin/python scripts/build_cartoon_assets.py
      (순수 파일 변환 — pymupdf+pillow+opencv-python-headless. LLM/DB 0.
       ⚠ opencv는 빌드타임 전용 — 서빙 requirements에 추가하지 않는다)
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

import cv2  # opencv-python-headless — QR 디코딩(빌드타임 전용). 없으면 여기서 loud abort —
import numpy as np  # 조용히 q 없이 생성되면 커밋된 manifest에서 QR이 통째로 증발한다.
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
QR_PX = (110, 220)  # QR 임베디드 이미지 실측 158±40px — 여유 폭. 필터 밖 이미지는 디코딩 시도 안 함


def decode_qrs(page: "fitz.Page") -> tuple[list[dict], int, int]:
    """페이지 임베디드 이미지 중 QR 후보를 디코딩 → ([{u,x,y,w,h} 0~1 정규화], 후보수, 실패수).

    같은 xref가 여러 위치에 재사용되면 rect마다 한 항목(URL 동일). http(s) 외 디코딩 결과는
    실패로 센다 — 오디코딩 문자열이 링크로 실리는 것 방지.

    ⚠ 페이지 밖 rect 필터 필수: 원본을 조문별로 분할할 때 이웃 조문의 이미지가 콘텐츠 스트림에
    남아 CropBox 밖(음수 y 등)에 배치돼 있다 — get_image_rects는 그것도 돌려준다(실측: 제13조
    y=-0.218). 렌더 이미지에는 안 보이므로 교차 60% 미만 rect는 버리고, 걸치는 rect는 페이지로
    클램프해 0~1을 보장한다."""
    doc = page.parent
    pw, ph = page.rect.width, page.rect.height
    det = cv2.QRCodeDetector()
    out: list[dict] = []
    n_cand = n_fail = 0
    seen_xref = set()
    for info in page.get_images(full=True):
        xref, w, h = info[0], info[2], info[3]
        if xref in seen_xref:
            continue
        seen_xref.add(xref)
        if not (QR_PX[0] <= w <= QR_PX[1] and QR_PX[0] <= h <= QR_PX[1] and 0.8 <= w / h <= 1.25):
            continue
        n_cand += 1
        url = ""
        try:
            arr = cv2.imdecode(np.frombuffer(doc.extract_image(xref)["image"], np.uint8),
                               cv2.IMREAD_COLOR)
            if arr is not None:
                # 3x 업스케일이 판독 관건(원본 해상도로는 실패 — 프로브 실측)
                big = cv2.resize(arr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                url, _, _ = det.detectAndDecode(big)
        except cv2.error:
            url = ""
        if not url.startswith(("http://", "https://")):
            n_fail += 1
            continue
        for r in page.get_image_rects(xref):
            x0, y0 = max(r.x0, 0.0), max(r.y0, 0.0)
            x1, y1 = min(r.x1, pw), min(r.y1, ph)
            inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            area = r.width * r.height
            if area <= 0 or inter < 0.6 * area:
                continue  # 페이지 밖(분할 잔재) — 렌더에 안 보임
            entry = {
                "u": url,
                "x": round(x0 / pw, 4), "y": round(y0 / ph, 4),
                "w": round((x1 - x0) / pw, 4), "h": round((y1 - y0) / ph, 4),
            }
            if entry not in out:  # 클램프로 생긴 완전 중복 방지
                out.append(entry)
    return out, n_cand, n_fail


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

    # ── 변환 (증분) + QR 디코딩 (매 실행 — WebP 해시와 무관) ─────────────
    made = reused = removed = 0
    qr_links = qr_cards = qr_cand = qr_fail = 0
    qr_fail_cards: list[str] = []
    manifest_cards = {}
    for n, (idx, jo, title, p) in enumerate(cards, 1):
        raw = p.read_bytes()
        h8 = hashlib.sha256(raw + f"|{PARAMS}".encode()).hexdigest()[:8]
        dst = OUT_IMG / f"{idx}.{h8}.webp"
        for old in OUT_IMG.glob(f"{idx}.*.webp"):
            if old != dst:
                old.unlink()
                removed += 1
        doc = fitz.open(stream=raw, filetype="pdf")
        page = doc[0]
        if dst.exists():
            with Image.open(dst) as im:
                w, hgt = im.size
            reused += 1
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            im.save(dst, "WEBP", quality=QUALITY, method=6)
            w, hgt = im.size
            made += 1
        qs, n_cand, n_fail = decode_qrs(page)
        doc.close()
        qr_links += len(qs)
        qr_cand += n_cand
        qr_fail += n_fail
        if qs:
            qr_cards += 1
        if n_fail:
            qr_fail_cards.append(f"{jo} ({p.name}): 후보 {n_cand} 중 {n_fail} 실패")
        entry = {"f": dst.name, "w": w, "h": hgt, "t": title}
        if qs:
            entry["q"] = qs
        manifest_cards[jo] = entry
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
    no_qr = sum(1 for c in manifest_cards.values() if "q" not in c)
    print(f"QR: 링크 {qr_links}개 / 보유 카드 {qr_cards}장 · 후보 {qr_cand} · 실패 {qr_fail}"
          f" · 링크 없는 카드 {no_qr}장")
    if qr_fail_cards:
        print(f"QR 디코딩 실패 카드 {len(qr_fail_cards)}장 (해당 카드만 링크 없음 — 현행 유지):")
        for line in qr_fail_cards[:20]:
            print("  ", line)
    print("\n표본 눈검사(품질 게이트 — 흐리면 ZOOM=4로 재실행):")
    for jo in ("제13조", "제172조", "제243조"):
        c = manifest_cards.get(jo)
        if c:
            print(f"  {jo} {c['t']}: {OUT_IMG.relative_to(REPO)}/{c['f']} ({c['w']}x{c['h']})")


if __name__ == "__main__":
    main()
