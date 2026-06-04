#!/usr/bin/env python3
"""Ablation — BM25 토크나이저 '룰베이스(현재)' vs 'kiwi 형태소'가 hybrid recall 최종 결과를
실제로 바꾸는지 측정. production 코드 미변경 — 두 BM25를 스크립트 내에서 직접 빌드 후 RRF 비교.

질의: 8장 실사진 hazards + synthetic 샘플. 대상: ohs_guide·ohs_sr.
지표: RRF top-1 동일률 / RRF top-K Jaccard / (참고)BM25-only Jaccard.
해석: RRF top이 거의 안 변하면 → 벡터가 지배 → 토크나이저 교체 효과 marginal.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from rank_bm25 import BM25Okapi  # noqa: E402
from app.services.hybrid_search import get_index, RRF_K  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
JOSA = "이가을를은는에서와도의로으로"


def rule_tokens(text):
    return [c for w in (text or "").split() if len(c := w.rstrip(JOSA)) >= 2]


_kiwi = None


def kiwi_tokens(text):
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    out = []
    for t in _kiwi.tokenize(text or ""):
        if t.tag[0] in ("N", "V") or t.tag in ("SL", "SN", "SH"):
            out.append(t.form)
    return out


def bm25_top(bm25, ids, query_tokens, pool):
    if not query_tokens:
        return []
    scores = bm25.get_scores(query_tokens)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [ids[i] for i in order[:pool] if scores[i] > 0]


def rrf(vec_ids, bm_ids, topn, k=RRF_K):
    f = {}
    for r, i in enumerate(vec_ids):
        f[i] = f.get(i, 0) + 1.0 / (k + r + 1)
    for r, i in enumerate(bm_ids):
        f[i] = f.get(i, 0) + 1.0 / (k + r + 1)
    return [i for i, _ in sorted(f.items(), key=lambda x: x[1], reverse=True)[:topn]]


def jacc(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0


# ── 질의 구성 ──
photos = json.loads((REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json").read_text(encoding="utf-8"))["photos"]
queries = []
for p in photos:
    for h in p["result"].get("hazards") or []:
        q = " ".join(filter(None, [h.get("name", ""), h.get("description", ""), *(h.get("preventive_measures") or [])]))
        if q.strip():
            queries.append(q)
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
for c in load_synthetic_cases(limit=40):
    q = " ".join(filter(None, [c.get("photo_description", ""), " ".join(c.get("visual_cues") or []), c.get("expected_corrective_direction", "")]))
    if q.strip():
        queries.append(q)
print(f"queries: {len(queries)} (8장 hazards + synthetic 40)")

POOL, TOPN = 20, 3
for cname in ["ohs_guide", "ohs_sr"]:
    idx = get_index(cname)
    data = idx.collection.get(include=["documents"])
    ids, docs = data["ids"], data["documents"]
    print(f"\n=== {cname} ({len(ids)} docs) — BM25 빌드(rule/kiwi) ===", flush=True)
    bm_rule = BM25Okapi([rule_tokens(d) for d in docs])
    bm_kiwi = BM25Okapi([kiwi_tokens(d) for d in docs])
    same1 = 0
    jrrf = 0.0
    jbm = 0.0
    n = 0
    for q in queries:
        v = [r["id"] for r in idx._vector_rank(q, POOL)]
        br = bm25_top(bm_rule, ids, rule_tokens(q), POOL)
        bk = bm25_top(bm_kiwi, ids, kiwi_tokens(q), POOL)
        rr, rk = rrf(v, br, TOPN), rrf(v, bk, TOPN)
        if rr and rk and rr[0] == rk[0]:
            same1 += 1
        jrrf += jacc(rr, rk)
        jbm += jacc(br[:TOPN], bk[:TOPN])
        n += 1
    print(f"  RRF top-1 동일률      : {same1}/{n} = {same1/n:.1%}")
    print(f"  RRF top-{TOPN} Jaccard 평균 : {jrrf/n:.3f}   (1.0=완전 동일)")
    print(f"  BM25-only top-{TOPN} Jaccard: {jbm/n:.3f}   (참고: 토크나이저가 BM25 자체를 얼마나 바꾸나)")
