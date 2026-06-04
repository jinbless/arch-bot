#!/usr/bin/env python3
"""Full-pipeline 검증 — guide 섹션-청킹 배선(option 2, robust sum)의 net 효과 측정.

ablation_guide_section.py는 vector-only/max-집계를 격리 비교했음(+0.44, 22:10).
이 스크립트는 **실제 서비스 함수** `_semantic_guide_candidates`를 GUIDE_SECTION_RECALL=1/0으로
토글해(둘 다 rerank ON = production 설정) top-1 guide를 LLM 블라인드 pairwise(0/1/2)로 판정 →
hybrid⊕robust-sum 배선이 full pipeline에서도 win을 유지하는지 확인. 무회귀 게이트.

또한 섹션 ON arm이 §섹션 근거(relevant_sections)를 실제로 부착하는지 smoke 확인.

실행: ./scripts/_runpy.sh scripts/validate_guide_section.py
"""
import json
import os
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
from app.services import hazard_to_guide_service as H  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
from judge_semantic_attach import judge  # noqa: E402

REPO = Path(__file__).resolve().parents[4]

# ── 질의 수집 (ablation_guide_section.py와 동일 모집단) ──
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


def candidates(db, rich_text, on: bool):
    os.environ["GUIDE_SECTION_RECALL"] = "1" if on else "0"
    return H._semantic_guide_candidates(db, rich_text, n=3, industry_contexts=[])


print(f"queries={len(queries)}  rerank={'ON' if H._semantic_rerank_enabled() else 'OFF'}  (production 설정)", flush=True)

div = []          # (label, q, off_top1, on_top1, on_section)
agree = 0
sec_attached = 0  # 섹션 ON arm에서 §섹션 근거 부착된 guide 수
sec_total = 0
with SessionLocal() as db:
    for label, q in queries:
        on = candidates(db, q, True)
        off = candidates(db, q, False)
        for g in on:
            sec_total += 1
            if g.get("relevant_sections"):
                sec_attached += 1
        o1 = off[0]["guide_code"] if off else None
        n1 = on[0]["guide_code"] if on else None
        n_sec = (on[0].get("relevant_sections") or [{}])[0].get("section_title", "") if on else ""
        if o1 and n1 and o1 == n1:
            agree += 1
        elif o1 and n1:
            div.append((label, q, o1, n1, n_sec))
    print(f"top-1 동일: {agree}/{len(queries)} · 발산(off≠on): {len(div)}", flush=True)
    print(f"§섹션 근거 부착률(ON arm): {sec_attached}/{sec_total} guide rows", flush=True)

    codes = {g for _, _, o, n, _ in div for g in (o, n)}
    titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

oai = OpenAI(api_key=settings.OPENAI_API_KEY)
random.seed(23)
on_w = off_w = tie = 0
on_sum = off_sum = 0
rows = []
for label, q, og, ng, nsec in div:
    ot, nt = titles.get(og), titles.get(ng)
    swap = random.random() < 0.5
    ta, tb = (nt, ot) if swap else (ot, nt)
    sa, sb, reason = judge(oai, "gpt-4.1-mini", q[:700], ta, tb)
    if sa is None:
        continue
    off_s = sb if swap else sa
    on_s = sa if swap else sb
    off_sum += off_s
    on_sum += on_s
    if on_s > off_s:
        on_w += 1
    elif off_s > on_s:
        off_w += 1
    else:
        tie += 1
    rows.append({"label": label, "off_guide": og, "on_guide": ng, "on_section": nsec,
                 "off_score": off_s, "on_score": on_s, "reason": reason})

n = on_w + off_w + tie or 1
print(f"\n=== 섹션청킹 배선 full-pipeline 품질 (발산 {n}건, top guide 적합성 0/1/2) ===")
print(f"  섹션 OFF(현행 1벡터) 평균={off_sum/n:.2f}  섹션 ON 평균={on_sum/n:.2f}  delta(on-off)={(on_sum-off_sum)/n:+.2f}")
print(f"  승부: 섹션 ON 우세 {on_w} / OFF 우세 {off_w} / 동점 {tie}")
verdict = "✅ 채택(무회귀 통과)" if on_w >= off_w else "⚠️ 회귀 — 기본 off 권장"
print(f"  판정: {verdict}")
out = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "validate_guide_section.json"
out.write_text(json.dumps({
    "queries": len(queries), "agree": agree, "divergent": len(div),
    "section_evidence_rate": f"{sec_attached}/{sec_total}",
    "off_mean": round(off_sum / n, 3), "on_mean": round(on_sum / n, 3),
    "on_win": on_w, "off_win": off_w, "tie": tie, "verdict": verdict, "rows": rows,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved: {out}")
print("\n예시(앞 8건, 섹션 ON은 §섹션 근거 동반):")
for r in rows[:8]:
    print(f"  [{r['label'][:13]:13s}] OFF={r['off_guide']}({r['off_score']})  ON={r['on_guide']}#{r['on_section']}({r['on_score']}) | {r['reason'][:56]}")
