#!/usr/bin/env python3
"""전사된 별표 JSON의 구분점 문자를 가운뎃점(U+00B7)으로 통일.

왜 필요한가: 법제처 PDF의 텍스트 레이어는 '볼트․너트'의 구분점에 U+2024(ONE DOT LEADER)를 쓴다.
전사 에이전트마다 이걸 원문대로 두거나(별표 1·2·12) 가운뎃점으로 옮겨(나머지) 파일별로 갈렸다.
같은 코퍼스 안에서 '상․하'와 '상·하'가 공존하면 검색·조인이 조용히 빗나간다.

이건 **표기 정규화**이지 내용 수정이 아니다. 무엇을 몇 개 바꿨는지 manifest에 남긴다.
되돌리려면 U+00B7 → U+2024로 역치환하면 되지만, 원문이 두 문자를 섞어 쓰는 곳
(별표 1은 U+2024 6개 + U+00B7 1개)이 있어 완전 복원은 안 된다 — rawPDF 재판독이 정본이다.

사용: python data-team/01-parsing/safety-inspection/normalize_separators.py [--apply]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARSED = HERE / "parsed"

# U+2024 ONE DOT LEADER, U+318D 한글 아래아 → U+00B7 MIDDLE DOT
SUBS = {"․": "·", "ㆍ": "·"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    total, changed_files = 0, []
    for f in sorted(PARSED.glob("inspection-appendix-*.json")):
        t = f.read_text(encoding="utf-8")
        n = sum(t.count(k) for k in SUBS)
        if not n:
            continue
        total += n
        changed_files.append({"file": f.name, "n": n})
        print(f"  {f.name}  {n}곳")
        if args.apply:
            for k, v in SUBS.items():
                t = t.replace(k, v)
            json.loads(t)  # 치환 후에도 유효 JSON인지 확인
            f.write_text(t, encoding="utf-8")

    print(f"\n총 {total}곳 / {len(changed_files)}개 파일" + ("  → 적용함" if args.apply else "  (--apply 미지정, 변경 없음)"))
    if args.apply:
        rec = PARSED / "normalizations.json"
        rec.write_text(json.dumps({
            "_note": "전사 후 적용한 표기 정규화 기록. 내용 수정이 아니라 문자 통일이다. 정본은 rawPDF.",
            "applied_at": "2026-08-01",
            "rules": [{"from": "U+2024 ONE DOT LEADER", "to": "U+00B7 MIDDLE DOT",
                       "why": "법제처 PDF 텍스트 레이어가 구분점에 U+2024를 쓰는데 전사 파일마다 보존/치환이 갈렸다"},
                      {"from": "U+318D HANGUL LETTER ARAEA", "to": "U+00B7 MIDDLE DOT",
                       "why": "가운뎃점 용도로 부적절한 한글 자모"}],
            "files": changed_files, "total": total,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {rec.name}")


if __name__ == "__main__":
    main()
