#!/usr/bin/env python3
"""Step (정확도) — guide 표현 ablation: 현행 1벡터/guide(ohs_guide) vs 섹션-청킹(ohs_guide_section).
둘 다 3-small 벡터로 격리 비교(임베딩 동일) → 청킹이 더 적합한 guide를 회수하나.
섹션-청킹은 top 섹션들을 guide로 집계(max sim) + 매칭 섹션을 근거로 보존.
발산(top-1 cur≠sec) 케이스를 LLM 블라인드 pairwise(0/1/2)로 판정.
"""
import json
import random
import sys
from pathlib import Path

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

guide_idx = get_index("ohs_guide")
sec_idx = get_index("ohs_guide_section")
print(f"ohs_guide={guide_idx.count()}  ohs_guide_section={sec_idx.count()}  queries={len(queries)}", flush=True)


def cur_top1(q):
    r = guide_idx._vector_rank(q, 1)
    return r[0]["id"] if r else None


def sec_top1(q, pool=30):
    best = {}
    for r in sec_idx._vector_rank(q, pool):
        m = r.get("meta") or {}
        g, s, v = m.get("guide"), m.get("section"), (r.get("vscore") or 0)
        if g and (g not in best or v > best[g][0]):
            best[g] = (v, s)
    if not best:
        return None, None
    g = max(best, key=lambda k: best[k][0])
    return g, best[g][1]


div = []
agree = 0
for label, q in queries:
    c = cur_top1(q)
    s, sec = sec_top1(q)
    if c and s and c == s:
        agree += 1
    elif c and s:
        div.append((label, q, c, s, sec))
print(f"top-1 동일: {agree}/{len(queries)} · 발산(cur≠sec): {len(div)}", flush=True)

codes = {g for _, _, c, s, _ in div for g in (c, s)}
with SessionLocal() as db:
    titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

oai = OpenAI(api_key=settings.OPENAI_API_KEY)
random.seed(17)
cur_w = sec_w = tie = 0
cur_sum = sec_sum = 0
rows = []
for label, q, cg, sg, sec in div:
    ct, st = titles.get(cg), titles.get(sg)
    swap = random.random() < 0.5
    ta, tb = (st, ct) if swap else (ct, st)
    sa, sb, reason = judge(oai, "gpt-4.1-mini", q[:700], ta, tb)
    if sa is None:
        continue
    cur_s = sb if swap else sa
    sec_s = sa if swap else sb
    cur_sum += cur_s
    sec_sum += sec_s
    if sec_s > cur_s:
        sec_w += 1
    elif cur_s > sec_s:
        cur_w += 1
    else:
        tie += 1
    rows.append({"label": label, "cur_guide": cg, "sec_guide": sg, "sec_section": sec,
                 "cur_score": cur_s, "sec_score": sec_s, "reason": reason})

n = cur_w + sec_w + tie or 1
print(f"\n=== guide 표현 품질 (발산 {n}건, top guide 적합성 0/1/2) ===")
print(f"  현행 1벡터 평균={cur_sum/n:.2f}  섹션청킹 평균={sec_sum/n:.2f}  delta(sec-cur)={(sec_sum-cur_sum)/n:+.2f}")
print(f"  승부: 섹션청킹 우세 {sec_w} / 현행 우세 {cur_w} / 동점 {tie}")
out = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "ablation_guide_section.json"
out.write_text(json.dumps({"agree": agree, "divergent": len(div), "cur_mean": round(cur_sum/n, 3), "sec_mean": round(sec_sum/n, 3),
                           "sec_win": sec_w, "cur_win": cur_w, "tie": tie, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved: {out}")
print("\n예시(앞 8건, 섹션청킹은 §섹션 근거 동반):")
for r in rows[:8]:
    print(f"  [{r['label'][:13]:13s}] 현행={r['cur_guide']}({r['cur_score']})  섹션={r['sec_guide']}#{r['sec_section']}({r['sec_score']}) | {r['reason'][:60]}")
