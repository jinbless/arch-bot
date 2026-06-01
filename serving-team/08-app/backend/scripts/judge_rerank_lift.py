#!/usr/bin/env python3
"""Phase 5 — bounded LLM rerank의 품질 lift 측정.

이전 judge_semantic_attach.json의 동일 80건에 대해, SEMANTIC_ATTACH_RERANK=on으로
top guide를 재계산하고 **no-rerank vs rerank를 블라인드 pairwise(0/1/2)** 채점.
rerank가 절대 적합도를 올리는지(=A의 가치) facet-독립으로 확정.

실행: ./.venv/bin/python scripts/judge_rerank_lift.py
"""
from __future__ import annotations

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
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
from eval_semantic_attach import synth  # noqa: E402
from judge_semantic_attach import judge, rich_text  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
PRIOR = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "judge_semantic_attach.json"
OUT = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "judge_rerank_lift.json"


def main() -> int:
    prior = [r for r in json.loads(PRIOR.read_text(encoding="utf-8"))["rows"] if not r.get("error")]
    cases = {c["case_id"]: c for c in load_synthetic_cases()}
    prior = [r for r in prior if r["case_id"] in cases]
    print(f"prior judged cases: {len(prior)}")

    # rerank-on top guide 재계산
    os.environ["SEMANTIC_ATTACH"] = "on"
    os.environ["SEMANTIC_ATTACH_RERANK"] = "on"
    rerank_guide: dict[str, str] = {}
    with SessionLocal() as db:
        for k, r in enumerate(prior):
            if k % 20 == 0:
                print(f"  rerank-attach {k}/{len(prior)}", flush=True)
            hz, canon = synth(cases[r["case_id"]])
            rels, _ = match_hazards_to_guides(db, [hz], canon, industry_contexts=[])
            gs = (rels[0].get("guides") if rels else []) or []
            rerank_guide[r["case_id"]] = gs[0]["guide_code"] if gs else None

    codes = {r["on_guide"] for r in prior} | set(rerank_guide.values())
    codes.discard(None)
    with SessionLocal() as db:
        titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

    oai = OpenAI(api_key=settings.OPENAI_API_KEY)
    random.seed(7)
    rows = []
    for k, r in enumerate(prior):
        if k % 20 == 0:
            print(f"  judging {k}/{len(prior)}", flush=True)
        cid = r["case_id"]
        ng, rg = r["on_guide"], rerank_guide.get(cid)  # ng=no-rerank, rg=rerank
        nt, rt = titles.get(ng), titles.get(rg)
        swap = random.random() < 0.5
        ta, tb = (rt, nt) if swap else (nt, rt)
        sa, sb, reason = judge(oai, "gpt-4.1-mini", rich_text(cases[cid]), ta, tb)
        if sa is None:
            continue
        norerank_s = sb if swap else sa
        rerank_s = sa if swap else sb
        rows.append({"case_id": cid, "seg": r["seg"], "norerank_guide": ng, "rerank_guide": rg,
                     "changed": ng != rg, "norerank_score": norerank_s, "rerank_score": rerank_s, "reason": reason})

    def agg(sub):
        if not sub:
            return {}
        n = len(sub)
        nm = sum(x["norerank_score"] for x in sub) / n
        rm = sum(x["rerank_score"] for x in sub) / n
        return {"n": n, "norerank_mean": round(nm, 3), "rerank_mean": round(rm, 3), "delta": round(rm - nm, 3),
                "rerank_win": sum(1 for x in sub if x["rerank_score"] > x["norerank_score"]),
                "tie": sum(1 for x in sub if x["rerank_score"] == x["norerank_score"]),
                "rerank_loss": sum(1 for x in sub if x["rerank_score"] < x["norerank_score"]),
                "changed_top1": sum(1 for x in sub if x["changed"]),
                "norerank_adeq>=2": sum(1 for x in sub if x["norerank_score"] >= 2),
                "rerank_adeq>=2": sum(1 for x in sub if x["rerank_score"] >= 2)}

    summary = {"all": agg(rows), "rescue": agg([r for r in rows if r["seg"] == "rescue"]),
               "both": agg([r for r in rows if r["seg"] == "both"])}
    print("\n=== rerank lift (no-rerank vs rerank, 블라인드 pairwise 0/1/2) ===")
    for seg in ("all", "rescue", "both"):
        s = summary[seg]
        if s:
            print(f"[{seg:7s}] n={s['n']:3d} norerank={s['norerank_mean']:.3f} rerank={s['rerank_mean']:.3f} "
                  f"delta={s['delta']:+.3f} | rerank win/tie/loss={s['rerank_win']}/{s['tie']}/{s['rerank_loss']} "
                  f"| top1 changed={s['changed_top1']} | adeq>=2 {s['norerank_adeq>=2']}→{s['rerank_adeq>=2']}")
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
