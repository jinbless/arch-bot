#!/usr/bin/env python3
"""retrieve(⒞ gold-kNN) → LLM rerank 파이프라인의 *천장* 측정.

⒞가 R@5=76%(정답이 상위에 있음)지만 P@1은 58%. 후보 top-K에 LLM(gpt-5.4)을 한 겹 얹어
장면+후보 조문 전문으로 yes/maybe/no 판정 → precision이 어디까지 오르는지(=풀 파이프라인 천장).

샘플 N건 sync 호출. 임베딩은 semantic_proto_emb.npz 캐시 사용(무료). 비교: ⒞ 검색만 vs ⒞+rerank.
사용: .venv/bin/python scripts/eval_rerank_ceiling.py [--n 120] [--k 8]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from judge_sr_article_mapping import _ensure_openai_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"
CACHE = ART / "semantic_proto_emb.npz"
CACHE_IDS = ART / "semantic_proto_emb_ids.json"
OUT = ART / "rerank_ceiling.json"
MODEL = "gpt-5.4"

SYS = ("너는 대한민국 산업안전보건 전문가다. 작업장 '장면 서술'과 '후보 조(전문)' 목록을 받는다. "
       "각 후보 조가 그 장면에서 관찰된 위험의 위반으로 성립하는지 조문 근거로 판정하라. "
       "applies: yes(직접 명백)/maybe(정황 필요)/no(무관). 모든 후보를 빠짐없이 판정.")
SCHEMA = {"name": "v", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"verdicts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]}},
        "required": ["article_code", "applies"]}}}, "required": ["verdicts"]}}


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 3), round(r, 3), round(f, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    dump = {json.loads(l)["case_id"]: json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = [cid for cid, a in auto.items() if a.get("core") and cid in dump]
    gold = {cid: set(auto[cid]["core"]) for cid in cases}
    scene = {cid: f"{dump[cid].get('photo_description','')} 시각단서: {'; '.join(dump[cid].get('visual_cues') or [])}" for cid in cases}

    ids = json.loads(CACHE_IDS.read_text(encoding="utf-8"))
    assert ids["cases"] == cases, "캐시 case 불일치 — eval_knn_generalization.py 먼저 실행"
    z = np.load(CACHE)
    S = z["S"]
    art_codes = ids["art_codes"]
    sims_ss = S @ S.T
    np.fill_diagonal(sims_ss, -1.0)

    # ⒞ kNN 후보 top-K (검색 점수순)
    cand = {}
    for i, cid in enumerate(cases):
        order = np.argsort(-sims_ss[i])[:10]
        score = {}
        for j in order:
            w = float(sims_ss[i][j])
            for code in auto[cases[j]]["core"]:
                score[code] = score.get(code, 0.0) + w
        cand[cid] = [c for c in sorted(score, key=lambda c: -score[c])][:args.k]

    sample = cases[::max(1, len(cases) // args.n)][:args.n]
    need_codes = sorted({c for cid in sample for c in cand[cid]})
    db = SessionLocal()
    try:
        rows = db.execute(text("select article_code, title, coalesce(full_text,'') from articles where article_code = any(:c) and law_type='RULE'"), {"c": need_codes}).fetchall()
    finally:
        db.close()
    atext = {r[0]: (r[1], r[2]) for r in rows}

    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()

    # baseline ⒞ 검색만 (sample 한정)
    base = {1: [0, 0, 0], 3: [0, 0, 0]}
    rr_yes = [0, 0, 0]       # yes set
    rr_ym = [0, 0, 0]        # yes∪maybe set
    rr_at = {1: [0, 0, 0], 3: [0, 0, 0]}  # rerank yes, 검색순 @k
    done = 0
    for cid in sample:
        g = gold[cid]
        cands = cand[cid]
        for k in (1, 3):
            pred = set(cands[:k])
            base[k][0] += len(pred & g); base[k][1] += len(pred - g); base[k][2] += len(g - pred)
        lines = [f"[장면]\n{scene[cid]}", "", "[후보 조 (전문)]"]
        for c in cands:
            t, full = atext.get(c, ("", ""))
            lines.append(f"- {c} {t}\n  {full[:350]}")
        user = "\n".join(lines) + "\n\n위 후보를 모두 판정하라."
        try:
            resp = client.chat.completions.create(model=MODEL, messages=[
                {"role": "system", "content": SYS}, {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": SCHEMA})
            vd = {v["article_code"]: v["applies"] for v in json.loads(resp.choices[0].message.content)["verdicts"]}
        except Exception as e:  # noqa: BLE001
            print(f"  err {cid}: {e}", file=sys.stderr)
            continue
        yes = {c for c in cands if vd.get(c) == "yes"}
        ym = {c for c in cands if vd.get(c) in ("yes", "maybe")}
        rr_yes[0] += len(yes & g); rr_yes[1] += len(yes - g); rr_yes[2] += len(g - yes)
        rr_ym[0] += len(ym & g); rr_ym[1] += len(ym - g); rr_ym[2] += len(g - ym)
        yes_ranked = [c for c in cands if c in yes]
        for k in (1, 3):
            pred = set(yes_ranked[:k])
            rr_at[k][0] += len(pred & g); rr_at[k][1] += len(pred - g); rr_at[k][2] += len(g - pred)
        done += 1
        if done % 20 == 0:
            print(f"  {done}/{len(sample)}", file=sys.stderr)

    res = {
        "model": MODEL, "n": done, "k_candidates": args.k,
        "baseline_retrieval_only": {"P@1R@1F1": _prf(*base[1]), "P@3R@3F1": _prf(*base[3])},
        "rerank_yes_set": {"P_R_F1": _prf(*rr_yes)},
        "rerank_yes∪maybe_set": {"P_R_F1": _prf(*rr_ym)},
        "rerank_yes_ranked": {"P@1R@1F1": _prf(*rr_at[1]), "P@3R@3F1": _prf(*rr_at[3])},
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
