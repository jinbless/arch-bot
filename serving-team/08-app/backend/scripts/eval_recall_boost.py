#!/usr/bin/env python3
"""recall 보강 측정 — KB 확장(consensus722→claude2360) + ⒜(장면↔조문) union 효과.

⒞ gold-kNN 천장은 KB 커버리지에 갇힘(정답 조가 어떤 이웃 gold에도 없으면 못 잡음). 두 보강:
  KB 확장: 이웃 풀을 claude_gold 전체로 → 더 다양한 정답 조 노출.
  ⒜ union: 장면↔조문 직접 의미매칭 후보를 ⒞에 합쳐 KB 밖 조도 포착.
eval = consensus core(고신뢰), leave-one-out(자기 case 이웃 제외). precision@k/recall@k.

임베딩: 전체 claude KB 장면 캐시(semantic_kb_claude_emb.npz) + 조문 A는 semantic_proto_emb.npz 재사용.
사용: .venv/bin/python scripts/eval_recall_boost.py
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
GOLD_AUTO = ART / "gold_auto.jsonl"
CLAUDE = ART / "claude_gold_v2.jsonl"
PROTO = ART / "semantic_proto_emb.npz"
PROTO_IDS = ART / "semantic_proto_emb_ids.json"
KBC = ART / "semantic_kb_claude_emb.npz"
KBC_IDS = ART / "semantic_kb_claude_ids.json"
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
    auto = {json.loads(l)["case_id"]: json.loads(l) for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    claude = {json.loads(l)["case_id"]: json.loads(l) for l in CLAUDE.read_text(encoding="utf-8").splitlines() if l.strip()}

    # KB = claude_gold 전체(gold_codes 보유) ∩ dump. eval = consensus core ⊆ KB.
    kb_cases = [cid for cid, c in claude.items() if c.get("gold_codes") and cid in dump]
    kb_gold = {cid: claude[cid]["gold_codes"] for cid in kb_cases}
    consensus = {cid for cid, a in auto.items() if a.get("core")}
    eval_cases = [cid for cid in kb_cases if cid in consensus]
    eval_gold = {cid: set(auto[cid]["core"]) for cid in eval_cases}
    idx = {cid: i for i, cid in enumerate(kb_cases)}
    print(f"KB(claude)={len(kb_cases)}  eval(consensus)={len(eval_cases)}", file=sys.stderr)

    # 조문 임베딩(proto 캐시 재사용)
    pid = json.loads(PROTO_IDS.read_text(encoding="utf-8"))
    A = np.load(PROTO)["A"]
    art_codes = pid["art_codes"]

    # KB 장면 임베딩(캐시)
    want = {"kb_cases": kb_cases, "model": EMBED_MODEL}
    if KBC.exists() and KBC_IDS.exists() and json.loads(KBC_IDS.read_text(encoding="utf-8")) == want:
        S = np.load(KBC)["S"]
        print("KB 임베딩 캐시 재사용", file=sys.stderr)
    else:
        _ensure_openai_key()
        from openai import OpenAI
        S = embed(OpenAI(), [_scene(dump[c]) for c in kb_cases])
        np.savez(KBC, S=S)
        KBC_IDS.write_text(json.dumps(want, ensure_ascii=False), encoding="utf-8")

    E = np.array([S[idx[c]] for c in eval_cases])  # eval 장면 임베딩
    sims_ss = E @ S.T          # eval × KB
    sims_sa = E @ A.T          # eval × 조문
    cons_mask = np.array([1 if c in consensus else 0 for c in kb_cases])

    def knn_cands(i, pool_consensus_only, knn=10, cap=12):
        sims = sims_ss[i]
        order = np.argsort(-sims)
        score, used = {}, 0
        for j in order:
            cj = kb_cases[j]
            if cj == eval_cases[i]:
                continue
            if pool_consensus_only and not cons_mask[j]:
                continue
            for code in kb_gold[cj]:
                score[code] = score.get(code, 0.0) + float(sims[j])
            used += 1
            if used >= knn:
                break
        return [c for c in sorted(score, key=lambda c: -score[c])][:cap]

    def a_cands(i, cap=12):
        order = np.argsort(-sims_sa[i])
        return [art_codes[j] for j in order[:cap]]

    def union(a, b, cap=12):
        out, seen = [], set()
        for c in list(a) + list(b):
            if c not in seen:
                seen.add(c)
                out.append(c)
            if len(out) >= cap:
                break
        return out

    def report(name, ranked_fn):
        agg = {k: [0, 0, 0] for k in KS}
        for i, cid in enumerate(eval_cases):
            g = eval_gold[cid]
            ranked = ranked_fn(i)
            for k in KS:
                pred = set(ranked[:k])
                agg[k][0] += len(pred & g); agg[k][1] += len(pred - g); agg[k][2] += len(g - pred)
        print(f"\n[{name}]")
        print("  k    P      R      F1")
        for k in KS:
            p, r, f = _prf(*agg[k])
            print(f"  @{k:<3} {p:.3f}  {r:.3f}  {f:.3f}")

    report("A) ⒞ KB=consensus722 (기준)", lambda i: knn_cands(i, True))
    report("B) ⒞ KB=claude2360", lambda i: knn_cands(i, False))
    report("C) ⒞ claude2360 ∪ ⒜", lambda i: union(knn_cands(i, False), a_cands(i)))
    report("D) ⒜ 단독(참고)", lambda i: a_cands(i))


if __name__ == "__main__":
    main()
