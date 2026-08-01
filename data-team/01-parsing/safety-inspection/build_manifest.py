#!/usr/bin/env python3
"""safety-inspection 원본 PDF ↔ 파싱 산출물 provenance manifest 생성.

rawPDF/ 는 git 미추적이라 리포만 봐서는 무엇을 파싱했는지 알 수 없다.
파일명·바이트수·SHA-256을 남겨 재다운로드 시 동일본인지 검증할 수 있게 한다.

사용: python data-team/01-parsing/safety-inspection/build_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "rawPDF"
PARSED = HERE / "parsed"
OUT = HERE / "manifest" / "safety-inspection-manifest.json"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw_of(appendix_id: str) -> Path | None:
    """'별표 3' → rawPDF의 '[별표 3] …(안전검사 고시).pdf'. 기준규칙 별표와 섞이지 않도록
    파일명에 '(안전검사 고시)'가 있는 것만 본다."""
    n = appendix_id.replace("별표", "").strip()
    for p in RAW.glob("*.pdf"):
        if "(안전검사 고시)" not in p.name:
            continue
        m = re.match(r"\[별표 (\S+)\]", p.name)
        if m and m.group(1) == n:
            return p
    return None


def main() -> None:
    entries, total_rows, total_items = [], 0, 0
    for f in sorted(PARSED.glob("inspection-appendix-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        n_rows = len(d.get("rows", []))
        n_items = sum(len(r.get("items") or []) for r in d.get("rows", []))
        total_rows += n_rows
        total_items += n_items
        raw = raw_of(d["appendix_id"])
        entries.append({
            "appendix_id": d["appendix_id"],
            "title": d.get("title", ""),
            "machine": d.get("machine", ""),
            "related_article": d.get("related_article", ""),
            "columns": d.get("columns", []),
            "rows": n_rows,
            "items": n_items,
            "last_no": (d.get("rows") or [{}])[-1].get("no", ""),
            "parsed_file": f.name,
            "raw_file": raw.name if raw else None,
            "raw_bytes": raw.stat().st_size if raw else None,
            "raw_sha256": sha256(raw) if raw else None,
        })

    notice = next((p for p in RAW.glob("*.pdf") if p.name.startswith("안전검사 고시(")), None)
    manifest = {
        "_note": "안전검사 고시(고용노동부고시 제2026-49호) 본문·별표 파싱 manifest. raw PDF는 미추적(.gitignore), 파싱 산출물만 추적.",
        "source": "국가법령정보센터 행정규칙 > 안전검사 고시 (사용자가 브라우저로 직접 수집. law.go.kr은 robots.txt로 자동 접근 차단)",
        "source_url": None,
        "notice_id": "고용노동부고시 제2026-49호",
        "effective_date": "2026-06-26",
        "parse_method": "VLM 시각 판독(Claude Read) — PDF 텍스트 레이어는 한글 공백이 소실되어 부적합",
        "parsed_at": "2026-08-01",
        "notice_body": {
            "raw_file": notice.name if notice else None,
            "raw_bytes": notice.stat().st_size if notice else None,
            "raw_sha256": sha256(notice) if notice else None,
            "pages": 15,
            "structure": "제1장 총칙 ~ 제16장 보칙, 제1조~제33조 및 부칙. 기계별 장(제2장~제15장)마다 정의 조문 + 검사기준 조문(별표 지정)",
        },
        "n_raw_pdf": len(list(RAW.glob("*.pdf"))),
        "n_appendix": len(entries),
        "total_rows": total_rows,
        "total_items": total_items,
        "appendices": entries,
        "not_obtained": [
            "산업안전보건법 제93조 원문",
            "산업안전보건법 시행령 제78조 원문",
            "산업안전보건법 시행규칙 제124조~제126조 원문",
            "안전검사대상기계등의 규격 및 형식별 적용범위 관련 고시(혼합기·파쇄기/분쇄기 적용 제외 범위의 출처로 추정, 미확인)",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"별표 {len(entries)}종 · 행 {total_rows} · 항목 {total_items}")
    for e in entries:
        flag = "" if e["raw_file"] else "   ← 원본 PDF 못 찾음"
        print(f"  {e['appendix_id']:>7} {e['machine'][:14]:16} 행 {e['rows']:>3} 항목 {e['items']:>4} "
              f"마지막 제{e['last_no']}호{flag}")
    print(f"\n→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
