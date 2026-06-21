#!/usr/bin/env python3
"""OWA→CWA 정밀화 — 기인물(起因物) 인덱스 구축.

사용자 통찰: 산업안전보건규칙의 편/장/절/관 계층은 대부분 '기인물'(사고를 일으키는
기계·설비·물질·구조물)별로 조직돼 있다. 절8=사출성형기, 절10관2=지게차, 절12관1=차량계
건설기계처럼 절/관 이름 자체가 기인물이다. 따라서 사진의 기인물을 먼저 식별하면 →
해당 절/관 → 그 안의 조문으로 좁히는 게 자유 의미매칭보다 P@1이 높다.

산출 gimulmul_index.json:
  groups: {group_key: {gimulmul, pyeon, jang, jeol, gwan, articles:[{code,title,observable}]}}
  cross_cutting: 기인물 무관 횡단 관찰조문 그룹키 목록(보호구·추락·전도·통로·작업장 등)
  observable_codes: 관찰가능(yes/partial) 조문코드 집합

사용: .venv/bin/python scripts/build_gimulmul_index.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SIGS = ART / "article_signatures.jsonl"
OUT = ART / "gimulmul_index.json"

# 기인물 무관 '횡단' 일반의무 — 어떤 기인물 사진에도 적용 가능(장 단위)
CROSS_CUTTING_JANG = [
    "장2 작업장", "장3 통로", "장4 보호구",
    "장6 추락 또는 붕괴에 의한 위험 방지",
    "장7 비계",
]


def parse(section: str):
    def g(p):
        m = re.search(p, section or "")
        return m.group(1).strip() if m else ""
    return {
        "pyeon": g(r"(편\d+[^>]*)"),
        "jang": g(r"(장\d+[^>]*)"),
        "jeol": g(r"(절\d+[^>]*)"),
        "gwan": g(r"(관\d+[^>]*)"),
    }


def group_key(p):
    if p["jeol"]:
        return p["jeol"] + (" > " + p["gwan"] if p["gwan"] else "")
    return p["jang"] or p["pyeon"] or "(상위)"


def gimulmul_label(p):
    """기인물 = 가장 깊은 절/관 이름(번호 제거)."""
    deepest = p["gwan"] or p["jeol"] or p["jang"]
    return re.sub(r"^[편장절관]\d+\s*", "", deepest).strip()


def main():
    obs = {}
    if SIGS.exists():
        for l in SIGS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                obs[r["article_code"]] = r["observable"]

    db = SessionLocal()
    rows = db.execute(text(
        "select article_code, title, coalesce(section,'') from articles "
        "where law_type='RULE' and not deleted and length(full_text)>10 order by article_code")).fetchall()
    db.close()

    groups = {}
    for code, title, section in rows:
        p = parse(section)
        gk = group_key(p)
        g = groups.setdefault(gk, {"gimulmul": gimulmul_label(p), **p, "articles": []})
        g["articles"].append({"code": code, "title": title, "observable": obs.get(code, "no")})

    def is_cross(gk, g):
        return any(g["jang"].startswith(c) or c in g["jang"] for c in CROSS_CUTTING_JANG) and not g["jeol"] or \
               any(c in (g["jang"] or "") for c in CROSS_CUTTING_JANG)

    cross = sorted([gk for gk, g in groups.items()
                    if any(c in (g["jang"] or "") for c in CROSS_CUTTING_JANG)])

    out = {
        "groups": groups,
        "cross_cutting": cross,
        "observable_codes": sorted([c for c, o in obs.items() if o in ("yes", "partial")]),
        "n_groups": len(groups),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 요약 출력
    print(f"groups={len(groups)}  cross_cutting_groups={len(cross)}  observable={len(out['observable_codes'])}")
    print("\n=== 기인물 그룹(관찰가능 조문 ≥2개, 상위 35) ===")
    ranked = sorted(groups.items(),
                    key=lambda kv: -sum(1 for a in kv[1]["articles"] if a["observable"] in ("yes", "partial")))
    for gk, g in ranked[:35]:
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs < 2:
            continue
        cc = " [횡단]" if gk in cross else ""
        print(f"  {nobs:>2}obs | {g['gimulmul'][:24]:<24} | {gk[:46]}{cc}")


if __name__ == "__main__":
    main()
