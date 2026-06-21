#!/usr/bin/env python3
"""사고사례_규칙_매핑.md (사람 큐레이션) → 구조화 JSON.

산출 parsed/case_rule_mapping.json:
  gimulmul_articles: {기인물: {count, articles:[{code,title,chapter}]}}  (Section B, 사람 큐레이션 기인물→조문)
  accident_type_chapters: {재해유형: {count, items:[{chapter, articles:[code]}]}}  (Section A, 재해유형→장)

Track A 후보생성의 사람 검증 출발점(LLM alias보다 정밀). 관찰성 필터는 별도 적용.

사용: .venv/bin/python scripts/parse_case_rule_mapping.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
SRC = REF / "사고사례_규칙_매핑.md"
OUT = REF / "parsed" / "case_rule_mapping.json"

CODE = r"제\d+조(?:의\d+)?"


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    section = None  # 'A' or 'B'
    gimulmul_articles = {}
    accident_type_chapters = {}
    cur_key = None

    for ln in lines:
        if ln.startswith("## A."):
            section = "A"; cur_key = None; continue
        if ln.startswith("## B."):
            section = "B"; cur_key = None; continue
        if ln.startswith("### "):
            head = ln[4:].strip()
            # "끼임 — 총 167건 (...)" / "지게차 — 사고 92건 (...)"
            m = re.match(r"(.+?)\s*—\s*(?:총|사고)\s*(\d+)건", head)
            name = m.group(1).strip() if m else head
            cnt = int(m.group(2)) if m else 0
            cur_key = name
            if section == "A":
                accident_type_chapters[name] = {"count": cnt, "items": []}
            elif section == "B":
                gimulmul_articles[name] = {"count": cnt, "articles": []}
            continue
        if ln.startswith("- ") and cur_key:
            if section == "A":
                # - **제2편 ... 제1장 ...** → 예: 제87조(...) , 제88조(...)
                mm = re.match(r"-\s*\*\*(.+?)\*\*\s*→\s*예:\s*(.+)", ln)
                if mm:
                    chapter = mm.group(1).strip()
                    arts = re.findall(CODE, mm.group(2))
                    accident_type_chapters[cur_key]["items"].append(
                        {"chapter": chapter, "articles": arts})
            elif section == "B":
                # - 제11조(작업장의 출입구) [제2장 작업장]
                mm = re.match(rf"-\s*({CODE})\((.+?)\)\s*(?:\[(.+?)\])?", ln)
                if mm:
                    gimulmul_articles[cur_key]["articles"].append(
                        {"code": mm.group(1), "title": mm.group(2).strip(),
                         "chapter": (mm.group(3) or "").strip()})

    OUT.write_text(json.dumps({
        "gimulmul_articles": gimulmul_articles,
        "accident_type_chapters": accident_type_chapters,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    nb = sum(len(v["articles"]) for v in gimulmul_articles.values())
    na = sum(len(v["items"]) for v in accident_type_chapters.values())
    print(f"Section B 기인물 {len(gimulmul_articles)}종 / 조문링크 {nb}")
    print(f"Section A 재해유형 {len(accident_type_chapters)}종 / 장링크 {na}")
    print("\n[Section B 샘플]")
    for k in list(gimulmul_articles)[:4]:
        arts = gimulmul_articles[k]["articles"]
        print(f"  {k}({gimulmul_articles[k]['count']}건): {', '.join(a['code'] for a in arts)}")
    print("\n[Section A 샘플]")
    for k in list(accident_type_chapters)[:3]:
        it = accident_type_chapters[k]["items"]
        print(f"  {k}: {len(it)}장 → " + " | ".join(i['chapter'][:14] + f"({len(i['articles'])})" for i in it))
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
