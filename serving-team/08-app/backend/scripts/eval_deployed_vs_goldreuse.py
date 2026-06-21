#!/usr/bin/env python3
"""배포된 semantic SR 경로 vs 내 gold-reuse — 같은 gold·같은 입력 정직 비교.

발견: 시스템은 이미 semantic(hybrid_search 'sr' + guide rerank, config ON)을 씀. 앞선 "1.9%"는
dump의 facet(focused/broad) 경로였고 배포 semantic 경로는 측정 안 됐었음. 이 스크립트가 그걸 측정:
  (a) facet broad        — dump native (참고, ~1.9%)
  (b) 배포 semantic SR    — hybrid_search('sr', scene) → SR→조(1:1)
  (c) 내 ⒞ gold-reuse     — scene 임베딩 kNN로 gold 이웃 조 재사용
모두 같은 eval(consensus core, leave-one-out)·같은 입력(scene text). precision@k/recall@k.

사용: .venv/bin/python scripts/eval_deployed_vs_goldreuse.py [--n 0(=전체)]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("SEMANTIC_ATTACH", "1")
HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"
PROTO = ART / "semantic_proto_emb.npz"
PROTO_IDS = ART / "semantic_proto_emb_ids.json"
KS = (1, 3, 5, 10)


def _scene(d):
    return f"{d.get('photo_description','')} 시각단서: {'; '.join(d.get('visual_cues') or [])}"


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def report(name, ranked_by_cid, gold_by_cid):
    agg = {k: [0, 0, 0] for k in KS}
    n = 0
    for cid, ranked in ranked_by_cid.items():
        g = gold_by_cid.get(cid)
        if not g:
            continue
        n += 1
        for k in KS:
            pred = set(ranked[:k])
            agg[k][0] += len(pred & g); agg[k][1] += len(pred - g); agg[k][2] += len(g - pred)
    print(f"\n[{name}] cases={n}")
    print("  k    P      R      F1")
    for k in KS:
        p, r, f = _prf(*agg[k])
        print(f"  @{k:<3} {p:.3f}  {r:.3f}  {f:.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0)
    args = ap.parse_args()

    dump = {json.loads(l)["case_id"]: json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    pid = json.loads(PROTO_IDS.read_text(encoding="utf-8"))
    cases = pid["cases"]
    if args.n:
        cases = cases[::max(1, len(cases)//args.n)][:args.n]
    gold = {cid: set(auto[cid]["core"]) for cid in cases if auto.get(cid, {}).get("core")}
    cases = [c for c in cases if c in gold]
    z = np.load(PROTO)
    S, A = z["S"], z["A"]
    art_codes = pid["art_codes"]
    cidx = {c: i for i, c in enumerate(pid["cases"])}

    db = SessionLocal()
    try:
        sr2art = {r[0]: r[1] for r in db.execute(text(
            "select sr_id, article_code from sr_article_mapping where law_type='RULE'")).fetchall()}

        # (a) facet broad (dump native)
        facet = {}
        for cid in cases:
            seen, order = set(), []
            for c in dump[cid].get("broad") or []:
                a = c["article_code"]
                if a not in seen:
                    seen.add(a); order.append(a)
            facet[cid] = order
        report("(a) facet broad (dump native, 참고)", facet, gold)

        # (b) 배포 semantic SR: hybrid_search('sr') → 조(1:1)
        from app.services.hybrid_search import hybrid_search
        depl = {}
        for n, cid in enumerate(cases):
            rows = hybrid_search("sr", _scene(dump[cid]), n_results=15)
            seen, order = set(), []
            for r in rows:
                a = sr2art.get(r["id"])
                if a and a not in seen:
                    seen.add(a); order.append(a)
            depl[cid] = order
            if (n + 1) % 100 == 0:
                print(f"  hybrid {n+1}/{len(cases)}", file=sys.stderr)
        report("(b) 배포 semantic SR (hybrid_search→조)", depl, gold)
    finally:
        db.close()

    # (c) 내 ⒞ gold-reuse (leave-one-out)
    Esub = np.array([S[cidx[c]] for c in cases])
    sims = Esub @ S.T
    goldreuse = {}
    for i, cid in enumerate(cases):
        order = np.argsort(-sims[i])
        score, used = {}, 0
        for j in order:
            jc = pid["cases"][j]
            if jc == cid or not auto.get(jc, {}).get("core"):
                continue
            for code in auto[jc]["core"]:
                score[code] = score.get(code, 0.0) + float(sims[i][j])
            used += 1
            if used >= 10:
                break
        goldreuse[cid] = [c for c in sorted(score, key=lambda c: -score[c])][:max(KS)]
    report("(c) 내 ⒞ gold-reuse (scene kNN→gold 조)", goldreuse, gold)


if __name__ == "__main__":
    main()
