#!/usr/bin/env python3
"""⒞ gold-이웃 재사용의 *진짜* 일반화 측정 — 합성 redundancy(쌍둥이 이웃) 제거.

leave-one-out kNN의 58%@1은 합성 장면끼리 거의 쌍둥이라 부풀려진 상한. 두 보수적 컷:
  (1) 유사도 상한 τ: 이웃 중 cosine>=τ(쌍둥이) 제외 후 측정. τ↓ = 'KB에 그만큼 닮은 게 없는 novel 사진'.
  (2) 최근접이웃 유사도 버킷별 precision: 각 테스트 장면을 top1-이웃 유사도로 층화 → novel 영역(low) 성능.
⒜(장면↔전체 조문)는 다른 장면 미사용 → redundancy 무관, 깨끗한 기준선으로 병기.

임베딩 npz 캐시(semantic_proto_emb.npz) — 재실행 무료. 사용: .venv/bin/python scripts/eval_knn_generalization.py
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

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from judge_sr_article_mapping import _ensure_openai_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"
CACHE = ART / "semantic_proto_emb.npz"
CACHE_IDS = ART / "semantic_proto_emb_ids.json"
EMBED_MODEL = "text-embedding-3-large"
KS = (1, 3, 5)


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def _micro(ranked_by_cid, gold_by_cid, ks=KS):
    agg = {k: [0, 0, 0] for k in ks}
    n = 0
    for cid, ranked in ranked_by_cid.items():
        gold = set(gold_by_cid[cid])
        if not gold:
            continue
        n += 1
        for k in ks:
            pred = set(ranked[:k])
            agg[k][0] += len(pred & gold)
            agg[k][1] += len(pred - gold)
            agg[k][2] += len(gold - pred)
    return {k: _prf(*agg[k]) for k in ks}, n


def _load():
    dump = {json.loads(l)["case_id"]: json.loads(l)
            for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
    auto = {json.loads(l)["case_id"]: json.loads(l)
            for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
    cases = [cid for cid, a in auto.items() if a.get("core") and cid in dump]
    gold = {cid: auto[cid]["core"] for cid in cases}
    scene = {}
    for cid in cases:
        d = dump[cid]
        scene[cid] = f"{d.get('photo_description','')} 시각단서: {'; '.join(d.get('visual_cues') or [])}"
    return cases, gold, scene, dump


def embed(client, texts, batch=256):
    out = []
    for i in range(0, len(texts), batch):
        r = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + batch])
        out.extend([d.embedding for d in r.data])
    m = np.array(out, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def get_embeddings(cases, scene):
    db = SessionLocal()
    try:
        arts = db.execute(text("""
            select article_code, title, full_text from articles
            where law_type='RULE' and coalesce(deleted,false)=false and coalesce(full_text,'')<>''
        """)).fetchall()
    finally:
        db.close()
    art_codes = [a[0] for a in arts]
    art_texts = [f"{a[1]}. {a[2][:1000]}" for a in arts]
    want = {"cases": cases, "art_codes": art_codes, "model": EMBED_MODEL}
    if CACHE.exists() and CACHE_IDS.exists() and json.loads(CACHE_IDS.read_text(encoding="utf-8")) == want:
        z = np.load(CACHE)
        print("embeddings: cache hit", file=sys.stderr)
        return z["S"], z["A"], art_codes
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    print("embeddings: computing...", file=sys.stderr)
    A = embed(client, art_texts)
    S = embed(client, [scene[c] for c in cases])
    np.savez(CACHE, S=S, A=A)
    CACHE_IDS.write_text(json.dumps(want, ensure_ascii=False), encoding="utf-8")
    return S, A, art_codes


def main():
    cases, gold, scene, dump = _load()
    S, A, art_codes = get_embeddings(cases, scene)
    print(f"cases={len(cases)} articles={len(art_codes)}", file=sys.stderr)

    # ⒜ scene↔all articles (redundancy 무관 기준선)
    sims_all = S @ A.T
    a_full = {cid: [art_codes[j] for j in np.argsort(-sims_all[i])[:max(KS)]]
              for i, cid in enumerate(cases)}
    m, n = _micro(a_full, gold)
    print(f"\n=== ⒜ 장면↔전체 조문 (redundancy 무관 기준선) · cases={n} ===")
    print("  k    P      R      F1")
    for k in KS:
        p, r, f = m[k]
        print(f"  @{k:<3} {p:.3f}  {r:.3f}  {f:.3f}")

    sims_ss = S @ S.T
    np.fill_diagonal(sims_ss, -1.0)
    top1 = sims_ss.max(axis=1)

    def knn(cap, knn_k=10):
        out = {}
        for i, cid in enumerate(cases):
            sims = sims_ss[i]
            order = np.argsort(-sims)
            score = {}
            used = 0
            for j in order:
                s = float(sims[j])
                if s < -0.5:
                    break
                if cap is not None and s >= cap:
                    continue  # 쌍둥이 제외
                for code in gold[cases[j]]:
                    score[code] = score.get(code, 0.0) + s
                used += 1
                if used >= knn_k:
                    break
            out[cid] = sorted(score, key=lambda c: -score[c])[:max(KS)]
        return out

    print("\n=== (1) 유사도 상한 τ별 ⒞ gold-이웃 재사용 (sim>=τ 이웃 제외) ===")
    print("  τ      P@1    P@3    R@5    (제외되는 쌍둥이↑일수록 novel에 근접)")
    for cap in (None, 0.95, 0.90, 0.85, 0.80, 0.70):
        m, _ = _micro(knn(cap), gold)
        label = "none" if cap is None else f"{cap:.2f}"
        print(f"  {label:<6} {m[1][0]:.3f}  {m[3][0]:.3f}  {m[5][1]:.3f}")

    print("\n=== (2) 최근접이웃 유사도 버킷별 (novel=낮은 버킷) ===")
    print("  top1-sim 구간   n     ⒞P@1   ⒜P@1   ⒞R@5")
    bins = [(-1, .80), (.80, .85), (.85, .90), (.90, .95), (.95, 1.01)]
    knn_full = knn(None)
    for lo, hi in bins:
        ids = [cid for i, cid in enumerate(cases) if lo <= top1[i] < hi]
        if not ids:
            continue
        gsub = {c: gold[c] for c in ids}
        mc, _ = _micro({c: knn_full[c] for c in ids}, gsub)
        ma, _ = _micro({c: a_full[c] for c in ids}, gsub)
        print(f"  [{lo if lo>=0 else 0:.2f},{hi:.2f})   {len(ids):<5} {mc[1][0]:.3f}  {ma[1][0]:.3f}  {mc[5][1]:.3f}")
    # 분포 요약
    import numpy as _np
    print(f"\n  top1-sim 분포: min={top1.min():.3f} p25={_np.percentile(top1,25):.3f} "
          f"median={_np.median(top1):.3f} p75={_np.percentile(top1,75):.3f} max={top1.max():.3f}")


if __name__ == "__main__":
    main()
