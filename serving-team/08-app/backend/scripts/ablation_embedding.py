#!/usr/bin/env python3
"""Step2 — 임베딩 모델 ablation: text-embedding-3-small vs 3-large.
벡터-only guide 회수만 격리 비교(BM25 배제) → 강한 임베딩이 실제로 더 적합한 guide를 주나.
발산(top-1 small≠large) 케이스를 LLM 블라인드 pairwise(0/1/2)로 품질 판정.

(BGE-m3는 torch+2.2GB 미설치 → self-host 필요. 3-large는 API drop-in이라 우리 스택에 더 현실적.)
"""
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from openai import OpenAI  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgKoshaGuide  # noqa: E402
from app.services.hybrid_search import get_index  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
from judge_semantic_attach import judge  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
SMALL, LARGE = "text-embedding-3-small", "text-embedding-3-large"
oai = OpenAI(api_key=settings.OPENAI_API_KEY)


def embed(texts, model):
    out = []
    for i in range(0, len(texts), 50):
        r = oai.embeddings.create(model=model, input=[(t or "")[:6000] for t in texts[i:i + 50]])
        out.extend(d.embedding for d in r.data)
    return np.array(out, dtype=np.float32)


def norm(M):
    return M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)


# 질의
photos = json.loads((REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "claude_vision_8photo_input.json").read_text(encoding="utf-8"))["photos"]
queries = []
for p in photos:
    for h in p["result"].get("hazards") or []:
        q = " ".join(filter(None, [h.get("name", ""), h.get("description", ""), *(h.get("preventive_measures") or [])]))
        if q.strip():
            queries.append((h.get("name", ""), q))
for c in load_synthetic_cases(limit=40):
    q = " ".join(filter(None, [c.get("photo_description", ""), " ".join(c.get("visual_cues") or []), c.get("expected_corrective_direction", "")]))
    if q.strip():
        queries.append((c.get("case_id", ""), q))

idx = get_index("ohs_guide")
data = idx.collection.get(include=["documents", "embeddings"])
ids, docs = data["ids"], data["documents"]
small_M = norm(np.array(data["embeddings"], dtype=np.float32))  # 저장된 3-small 벡터
print(f"guides={len(ids)}  3-large로 코퍼스 재임베딩 중...", flush=True)
large_M = norm(embed(docs, LARGE))

# 질의 임베딩 일괄
qtexts = [q for _, q in queries]
qs_small = norm(embed(qtexts, SMALL))
qs_large = norm(embed(qtexts, LARGE))

div = []
for k, (label, q) in enumerate(queries):
    s1 = ids[int(np.argmax(small_M @ qs_small[k]))]
    l1 = ids[int(np.argmax(large_M @ qs_large[k]))]
    if s1 != l1:
        div.append((label, q, s1, l1))
print(f"vector top-1 발산(small≠large): {len(div)}/{len(queries)}")

codes = {g for _, _, a, b in div for g in (a, b)}
with SessionLocal() as db:
    titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

random.seed(13)
small_w = large_w = tie = 0
small_sum = large_sum = 0
rows = []
for label, q, sg, lg in div:
    st, lt = titles.get(sg), titles.get(lg)
    swap = random.random() < 0.5
    ta, tb = (lt, st) if swap else (st, lt)
    sa, sb, reason = judge(oai, "gpt-4.1-mini", q[:700], ta, tb)
    if sa is None:
        continue
    small_s = sb if swap else sa
    large_s = sa if swap else sb
    small_sum += small_s
    large_sum += large_s
    if large_s > small_s:
        large_w += 1
    elif small_s > large_s:
        small_w += 1
    else:
        tie += 1
    rows.append({"label": label, "small_guide": sg, "large_guide": lg, "small_score": small_s, "large_score": large_s, "reason": reason})

n = small_w + large_w + tie or 1
print(f"\n=== 임베딩 품질 (벡터-only 발산 {n}건, guide 적합성 0/1/2) ===")
print(f"  3-small 평균={small_sum/n:.2f}  3-large 평균={large_sum/n:.2f}  delta(large-small)={(large_sum-small_sum)/n:+.2f}")
print(f"  승부: 3-large 우세 {large_w} / 3-small 우세 {small_w} / 동점 {tie}")
out = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "ablation_embedding.json"
out.write_text(json.dumps({"divergent": len(div), "small_mean": round(small_sum/n, 3), "large_mean": round(large_sum/n, 3),
                           "large_win": large_w, "small_win": small_w, "tie": tie, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved: {out}")
print("\n예시(앞 6건):")
for r in rows[:6]:
    print(f"  [{r['label'][:14]:14s}] small={r['small_guide']}({r['small_score']}) large={r['large_guide']}({r['large_score']}) | {r['reason'][:66]}")
