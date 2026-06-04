#!/usr/bin/env python3
"""Step1 — BM25 토크나이저 품질 judge: rule vs kiwi가 '발산한' guide 케이스에서
어느 쪽 top guide가 더 적합한지 LLM 블라인드 pairwise(0/1/2) 판정.

ohs_guide 대상. 8장 hazards + synthetic 질의 → RRF top-1이 rule≠kiwi인 케이스만 judge.
"""
import random
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from rank_bm25 import BM25Okapi  # noqa: E402
from openai import OpenAI  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgKoshaGuide  # noqa: E402
from app.services.hybrid_search import get_index, RRF_K  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
from judge_semantic_attach import judge  # noqa: E402  (blind pairwise 0/1/2)

REPO = Path(__file__).resolve().parents[4]
JOSA = "이가을를은는에서와도의로으로"
_kiwi = None


def rule_tokens(t):
    return [c for w in (t or "").split() if len(c := w.rstrip(JOSA)) >= 2]


def kiwi_tokens(t):
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return [m.form for m in _kiwi.tokenize(t or "") if m.tag[0] in ("N", "V") or m.tag in ("SL", "SN", "SH")]


def bm25_top(bm, ids, qt, pool=20):
    if not qt:
        return []
    s = bm.get_scores(qt)
    return [ids[i] for i in sorted(range(len(s)), key=lambda i: s[i], reverse=True)[:pool] if s[i] > 0]


def rrf_top1(vec, bm, k=RRF_K):
    f = {}
    for r, i in enumerate(vec):
        f[i] = f.get(i, 0) + 1.0 / (k + r + 1)
    for r, i in enumerate(bm):
        f[i] = f.get(i, 0) + 1.0 / (k + r + 1)
    ranked = sorted(f.items(), key=lambda x: x[1], reverse=True)
    return ranked[0][0] if ranked else None


# 질의 (label, rich_text)
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
data = idx.collection.get(include=["documents"])
ids, docs = data["ids"], data["documents"]
print(f"ohs_guide {len(ids)} docs — BM25(rule/kiwi) 빌드...", flush=True)
bm_rule = BM25Okapi([rule_tokens(d) for d in docs])
bm_kiwi = BM25Okapi([kiwi_tokens(d) for d in docs])

# 발산 케이스 수집
div = []
for label, q in queries:
    v = [r["id"] for r in idx._vector_rank(q, 20)]
    rt = rrf_top1(v, bm25_top(bm_rule, ids, rule_tokens(q)))
    kt = rrf_top1(v, bm25_top(bm_kiwi, ids, kiwi_tokens(q)))
    if rt and kt and rt != kt:
        div.append((label, q, rt, kt))
print(f"발산(top-1 rule≠kiwi): {len(div)}/{len(queries)}")

codes = {g for _, _, a, b in div for g in (a, b)}
with SessionLocal() as db:
    titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

oai = OpenAI(api_key=settings.OPENAI_API_KEY)
random.seed(11)
rule_w = kiwi_w = tie = 0
rule_sum = kiwi_sum = 0
rows = []
for k, (label, q, rg, kg) in enumerate(div):
    rt_title, kt_title = titles.get(rg), titles.get(kg)
    swap = random.random() < 0.5
    ta, tb = (kt_title, rt_title) if swap else (rt_title, kt_title)
    sa, sb, reason = judge(oai, "gpt-4.1-mini", q[:700], ta, tb)
    if sa is None:
        continue
    rule_s = sb if swap else sa
    kiwi_s = sa if swap else sb
    rule_sum += rule_s
    kiwi_sum += kiwi_s
    if kiwi_s > rule_s:
        kiwi_w += 1
    elif rule_s > kiwi_s:
        rule_w += 1
    else:
        tie += 1
    rows.append({"label": label, "rule_guide": rg, "kiwi_guide": kg, "rule_score": rule_s, "kiwi_score": kiwi_s, "reason": reason})

n = rule_w + kiwi_w + tie
print(f"\n=== 토크나이저 품질 (발산 {n}건, ohs_guide top guide 적합성 0/1/2) ===")
print(f"  rule 평균={rule_sum/n:.2f}  kiwi 평균={kiwi_sum/n:.2f}  delta(kiwi-rule)={ (kiwi_sum-rule_sum)/n:+.2f}")
print(f"  승부: kiwi 우세 {kiwi_w} / rule 우세 {rule_w} / 동점 {tie}")
out = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "judge_tokenizer.json"
out.write_text(json.dumps({"divergent": len(div), "rule_mean": round(rule_sum/n, 3), "kiwi_mean": round(kiwi_sum/n, 3),
                           "kiwi_win": kiwi_w, "rule_win": rule_w, "tie": tie, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved: {out}")
print("\n예시(앞 6건):")
for r in rows[:6]:
    print(f"  [{r['label'][:14]:14s}] rule={r['rule_guide']}({r['rule_score']}) kiwi={r['kiwi_guide']}({r['kiwi_score']}) | {r['reason'][:70]}")
