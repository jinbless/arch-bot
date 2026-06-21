#!/usr/bin/env python3
"""확정 gold(final_gold = core ∪ tiebreak-yes)로 ⒞ gold-kNN 권위 재측정.

consensus 722(쉬운 케이스)만이 아니라 disputed(어려운 케이스)까지 포함한 일반화 숫자.
KB·eval 모두 final_gold(비어있지 않은 케이스), leave-one-out. consensus/disputed 분리 보고.
⚠ final_gold는 maybe(1036코드) 제외한 보수적 gold — precision 하한 성격.

사용: .venv/bin/python scripts/eval_final_gold.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from judge_sr_article_mapping import _ensure_openai_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
FINAL = ART / "final_gold.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"
EMB = ART / "semantic_final_emb.npz"
EMB_IDS = ART / "semantic_final_ids.json"
EMBED_MODEL = "text-embedding-3-large"
KS = (1, 3, 5, 10)


def _scene(d):
    return f"{d.get('photo_description','')} 시각단서: {'; '.join(d.get('visual_cues') or [])}"


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def embed(client, texts, batch=256):
    out = []
    for i in range(0, len(texts), batch):
        r = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch])
        out.extend([d.embedding for d in r.data])
        print(f"  embedded {min(i+batch,len(texts))}/{len(texts)}", file=sys.stderr)
    m = np.array(out, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def main():
    dump = {json.loads(l)["case_id"]: json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    final = {json.loads(l)["case_id"]: json.loads(l)["gold_codes"]
             for l in FINAL.read_text(encoding="utf-8").splitlines() if l.strip()}
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = [cid for cid, g in final.items() if g and cid in dump]
    gold = {cid: set(final[cid]) for cid in cases}
    is_consensus = {cid: bool(auto.get(cid, {}).get("consensus")) for cid in cases}
    print(f"final_gold nonempty cases={len(cases)} (consensus={sum(is_consensus.values())}, disputed={len(cases)-sum(is_consensus.values())})", file=sys.stderr)

    want = {"cases": cases, "model": EMBED_MODEL}
    if EMB.exists() and EMB_IDS.exists() and json.loads(EMB_IDS.read_text(encoding="utf-8")) == want:
        S = np.load(EMB)["S"]
        print("임베딩 캐시 재사용", file=sys.stderr)
    else:
        _ensure_openai_key()
        from openai import OpenAI
        S = embed(OpenAI(), [_scene(dump[c]) for c in cases])
        np.savez(EMB, S=S)
        EMB_IDS.write_text(json.dumps(want, ensure_ascii=False), encoding="utf-8")

    sims = S @ S.T
    np.fill_diagonal(sims, -1.0)
    ranked = {}
    for i, cid in enumerate(cases):
        order = np.argsort(-sims[i])[:10]
        score = {}
        for j in order:
            w = float(sims[i][j])
            for code in gold[cases[j]]:
                score[code] = score.get(code, 0.0) + w
        ranked[cid] = [c for c in sorted(score, key=lambda c: -score[c])][:max(KS)]

    def report(name, subset):
        agg = {k: [0, 0, 0] for k in KS}
        n = 0
        for cid in subset:
            g = gold[cid]
            n += 1
            for k in KS:
                pred = set(ranked[cid][:k])
                agg[k][0] += len(pred & g); agg[k][1] += len(pred - g); agg[k][2] += len(g - pred)
        print(f"\n[{name}] cases={n}")
        print("  k    P      R      F1")
        for k in KS:
            p, r, f = _prf(*agg[k])
            print(f"  @{k:<3} {p:.3f}  {r:.3f}  {f:.3f}")

    report("전체 final_gold (easy+hard)", cases)
    report("consensus subset (쉬움)", [c for c in cases if is_consensus[c]])
    report("disputed subset (어려움)", [c for c in cases if not is_consensus[c]])


if __name__ == "__main__":
    main()
