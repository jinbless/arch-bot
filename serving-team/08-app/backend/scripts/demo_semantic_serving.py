#!/usr/bin/env python3
"""semantic_article_service end-to-end 스모크 데모 (leave-one-out).

KB(semantic_kb) 빌드 후, 샘플 케이스의 장면을 자기 자신 제외하고 recommend_articles에 넣어
추천 조 vs gold를 출력. 실제 서빙 경로(장면→검색→rerank→조)를 그대로 탄다.
사용: .venv/bin/python scripts/demo_semantic_serving.py [--n 6]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))

from app.services.semantic_article_service import recommend_articles  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    dump = {json.loads(l)["case_id"]: json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = [cid for cid, a in auto.items() if a.get("core") and cid in dump]
    sample = cases[::max(1, len(cases) // args.n)][:args.n]

    for cid in sample:
        d = dump[cid]
        scene = f"{d.get('photo_description','')} 시각단서: {'; '.join(d.get('visual_cues') or [])}"
        gold = set(auto[cid]["core"])
        recs = recommend_articles(scene, top_k=8, exclude_case_id=cid)
        print(f"\n=== {cid} ({d.get('work_context','')}) ===")
        print(f"  장면: {d.get('photo_description','')[:90]}")
        print(f"  gold: {sorted(gold)}")
        for r in recs[:6]:
            hit = "✓" if r["article_code"] in gold else " "
            print(f"   {hit} #{r['rank']} {r['article_code']} [{r['applies']}] {r['title'][:34]} (s={r['retrieval_score']})")


if __name__ == "__main__":
    main()
