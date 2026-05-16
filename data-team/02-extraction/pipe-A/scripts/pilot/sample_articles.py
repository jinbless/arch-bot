#!/usr/bin/env python3
"""Multi-SR pilot: paragraph 단위로 분할 가능한 article 10개를 결정론적으로 샘플링.

조건:
  - law_id = 'RULE'
  - articles.deleted = false
  - OBLIGATION/PROHIBITION NS >= 3
  - 정규화된 paragraph >= 2 (한 article에 의미 있는 항이 2개 이상)

정렬: md5(article_code || SEED) — 같은 SEED면 같은 결과.
출력: pipe-A/data/pilot/sample-articles.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"
SEED = "pilot-seed-2026-04-26"
SAMPLE_SIZE = 10
MIN_NS = 3
MIN_PARA = 2

PARA_NORM_RE = re.compile(r"^(제\d+조(?:의\d+)? 제\d+항)")


def normalize_para(pref: str) -> str:
    """paragraphRef 정규화: '제42조 제2항 단서' / '제42조 제2항 제3호' → '제42조 제2항'."""
    if not pref:
        return "본문"
    m = PARA_NORM_RE.match(pref)
    return m.group(1) if m else pref


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    pilot_dir = Path(__file__).resolve().parents[2] / "data" / "pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect(PG_CONNINFO) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.article_code, n.paragraph_ref, a.title, a.section
            FROM norm_statements n
            JOIN articles a
              ON a.law_type = 'RULE' AND a.article_code = n.article_code
            WHERE n.law_id = 'RULE'
              AND n.has_modality IN ('OBLIGATION', 'PROHIBITION')
              AND a.deleted = FALSE
            """
        )
        rows = cur.fetchall()

    by_art: dict[str, dict] = {}
    for ac, pref, title, section in rows:
        d = by_art.setdefault(
            ac, {"paras": set(), "ns_count": 0, "title": title, "section": section}
        )
        d["paras"].add(normalize_para(pref))
        d["ns_count"] += 1

    candidates = [
        (ac, len(d["paras"]), d["ns_count"], d["title"], d["section"])
        for ac, d in by_art.items()
        if len(d["paras"]) >= MIN_PARA and d["ns_count"] >= MIN_NS
    ]

    candidates.sort(key=lambda x: hashlib.md5((x[0] + SEED).encode()).hexdigest())
    samples = candidates[:SAMPLE_SIZE]

    out = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "seed": SEED,
            "selectionRule": f"para>={MIN_PARA} AND ns>={MIN_NS}, sorted by md5(ac||seed)",
            "totalCandidates": len(candidates),
            "sampleSize": len(samples),
        },
        "samples": [
            {
                "articleCode": ac,
                "paragraphCount": pc,
                "nsCount": nc,
                "title": t,
                "section": s,
            }
            for ac, pc, nc, t, s in samples
        ],
    }
    out_path = pilot_dir / "sample-articles.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] candidates={len(candidates)} → samples={len(samples)}")
    print(f"[OK] saved: {out_path}")
    print()
    for ac, pc, nc, t, _ in samples:
        print(f"  {ac:12s} paras={pc} ns={nc:2d}  — {t}")


if __name__ == "__main__":
    main()
