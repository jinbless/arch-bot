#!/usr/bin/env python3
"""의미매칭 rerank 프로토타입 — facet 매칭(precision@1 2~6%)을 대체할 수 있는지 측정.

장면 텍스트(photo_description+visual_cues)를 임베딩해 3가지로 정답 조(consensus gold)와 채점:
  (a-full)  장면 ↔ 전체 RULE 조문(653) 전문 유사도 랭킹.          (facet candidate-gen 무시, 상한)
  (a-broad) 장면 ↔ 그 케이스 broad 후보 조만 유사도 재랭킹.       (현실 서빙: broad 후보를 의미로 정렬)
  (b-knn)   장면 ↔ 다른 gold 장면 kNN(leave-one-out) → 이웃 정답 조 재사용. (gold를 reference로)
baseline: dump native broad 순서 precision@k.

사용: .venv/bin/python scripts/prototype_semantic_rerank.py   (OPENAI_API_KEY/.env + DATABASE_URL)
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
EMBED_MODEL = "text-embedding-3-large"
KS = (1, 2, 3, 5, 10)


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


def report(name, per_case_ranked, gold_by_cid):
    """per_case_ranked: cid -> [article_code ranked]. micro precision@k/recall@k."""
    agg = {k: [0, 0, 0] for k in KS}
    n = 0
    for cid, ranked in per_case_ranked.items():
        gold = set(gold_by_cid[cid])
        if not gold:
            continue
        n += 1
        for k in KS:
            pred = set(ranked[:k])
            agg[k][0] += len(pred & gold)
            agg[k][1] += len(pred - gold)
            agg[k][2] += len(gold - pred)
    print(f"\n[{name}] cases={n}")
    print("  k    precision recall   F1")
    for k in KS:
        p, r, f = _prf(*agg[k])
        print(f"  @{k:<3} {p:.3f}     {r:.3f}    {f:.3f}")


def main():
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    db = SessionLocal()
    try:
        arts = db.execute(text("""
            select article_code, title, full_text from articles
            where law_type='RULE' and coalesce(deleted,false)=false and coalesce(full_text,'')<>''
        """)).fetchall()
        art_codes = [a[0] for a in arts]
        art_texts = [f"{a[1]}. {a[2][:1000]}" for a in arts]
        print(f"RULE articles={len(arts)}", file=sys.stderr)

        dump = {json.loads(l)["case_id"]: json.loads(l)
                for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()}
        auto = {json.loads(l)["case_id"]: json.loads(l)
                for l in GOLD_AUTO.read_text(encoding="utf-8").splitlines() if l.strip()}
        # consensus core(두 LLM 합의 positive)만
        cases = [cid for cid, a in auto.items() if a.get("core") and cid in dump]
        gold_by_cid = {cid: auto[cid]["core"] for cid in cases}
        scene_text = {}
        broad_by_cid = {}
        for cid in cases:
            d = dump[cid]
            vc = "; ".join(d.get("visual_cues") or [])
            scene_text[cid] = f"{d.get('photo_description','')} 시각단서: {vc}"
            # broad article 원순서 dedup
            seen, order = set(), []
            for c in d.get("broad") or []:
                if c["article_code"] not in seen:
                    seen.add(c["article_code"])
                    order.append(c["article_code"])
            broad_by_cid[cid] = order
        print(f"consensus cases={len(cases)}", file=sys.stderr)

        print("embedding articles...", file=sys.stderr)
        A = embed(client, art_texts)
        print("embedding scenes...", file=sys.stderr)
        S = embed(client, [scene_text[cid] for cid in cases])
        art_idx = {c: i for i, c in enumerate(art_codes)}

        # baseline: native broad
        report("baseline: native broad 순서", broad_by_cid, gold_by_cid)

        # (a-full) scene vs all articles
        sims_all = S @ A.T  # [ncase, narts]
        a_full = {}
        for i, cid in enumerate(cases):
            order = np.argsort(-sims_all[i])
            a_full[cid] = [art_codes[j] for j in order[:max(KS)]]
        report("(a-full) 장면 ↔ 전체 조문 의미랭킹", a_full, gold_by_cid)

        # (a-broad) rerank broad candidates by scene-article sim
        a_broad = {}
        for i, cid in enumerate(cases):
            cand = [c for c in broad_by_cid[cid] if c in art_idx]
            cand.sort(key=lambda c: -sims_all[i][art_idx[c]])
            a_broad[cid] = cand[:max(KS)]
        report("(a-broad) broad 후보를 의미로 재랭킹", a_broad, gold_by_cid)

        # (b-knn) leave-one-out over gold scenes
        sims_ss = S @ S.T
        np.fill_diagonal(sims_ss, -1.0)
        b_knn = {}
        KNN = 10
        for i, cid in enumerate(cases):
            nbr = np.argsort(-sims_ss[i])[:KNN]
            score = {}
            for j in nbr:
                w = float(sims_ss[i][j])
                for code in gold_by_cid[cases[j]]:
                    score[code] = score.get(code, 0.0) + w
            ranked = sorted(score, key=lambda c: -score[c])
            b_knn[cid] = ranked[:max(KS)]
        report(f"(b-knn) gold 이웃 {KNN}개 정답 재사용 (leave-one-out)", b_knn, gold_by_cid)
    finally:
        db.close()


if __name__ == "__main__":
    main()
