#!/usr/bin/env python3
"""Phase 5 — LLM-judge (facet-독립) for semantic attach.

eval_semantic_attach_full.json의 off/on top-guide를, 각 case rich text에 대해
GPT가 **블라인드(A/B 무작위 swap)**로 0/1/2 채점 → facet proxy 편향·맹점 우회.
0=무관/엉뚱, 1=같은 대분류지만 부정확, 2=직접 적합.

표본: facet-miss(off 가이드 0개=semantic 구제) N + both-have-guide N, random.seed 고정.

실행: ./.venv/bin/python scripts/judge_semantic_attach.py [--n 40] [--model gpt-4.1-mini]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from openai import OpenAI  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgKoshaGuide  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
EVAL_JSON = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "eval_semantic_attach_full.json"
OUT_JSON = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "judge_semantic_attach.json"

SYS = (
    "당신은 한국 산업안전보건(KOSHA) 전문가입니다. 현장 위험 상황 설명과 후보 KOSHA 가이드 제목이 주어지면, "
    "각 가이드가 그 위험의 '표준 개선 절차' 근거로 얼마나 적합한지 평가합니다. "
    "점수: 0=무관/엉뚱한 주제, 1=같은 대분류지만 부정확, 2=직접 적합. 오직 JSON만 출력."
)


def rich_text(case: dict) -> str:
    return " ".join(filter(None, [
        case.get("photo_description", ""),
        " ".join(case.get("visual_cues") or []),
        case.get("expected_corrective_direction", ""),
    ]))[:700]


def judge(oai, model, rich, title_a, title_b):
    user = (f"[위험 상황]\n{rich}\n\n"
            f"[가이드 A] {title_a or '(부착된 가이드 없음)'}\n"
            f"[가이드 B] {title_b or '(부착된 가이드 없음)'}\n\n"
            "JSON 형식: {\"a\": 0|1|2, \"b\": 0|1|2, \"reason\": \"간단 근거\"}")
    for _ in range(2):
        try:
            resp = oai.chat.completions.create(
                model=model, temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}],
            )
            d = json.loads(resp.choices[0].message.content)
            return int(d.get("a", 0)), int(d.get("b", 0)), str(d.get("reason", ""))[:160]
        except Exception:  # noqa: BLE001
            continue
    return None, None, "ERROR"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=40, help="구간별 표본 수 (rescue N + both N)")
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    d = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    off = {r["case_id"]: r for r in d["off"] if "error" not in r}
    on = {r["case_id"]: r for r in d["on"] if "error" not in r}
    cases = {c["case_id"]: c for c in load_synthetic_cases()}

    ids = [i for i in (set(off) & set(on)) if i in cases]
    rescue = sorted(i for i in ids if off[i]["n_guides"] == 0 and on[i]["n_guides"] > 0)
    both = sorted(i for i in ids if off[i]["n_guides"] > 0 and on[i]["n_guides"] > 0)
    random.seed(args.seed)
    samp_rescue = random.sample(rescue, min(args.n, len(rescue)))
    samp_both = random.sample(both, min(args.n, len(both)))
    sample = [("rescue", i) for i in samp_rescue] + [("both", i) for i in samp_both]
    print(f"sample: rescue={len(samp_rescue)} both={len(samp_both)} (pool rescue={len(rescue)} both={len(both)})")

    codes = {off[i].get("top_guide") for _, i in sample} | {on[i].get("top_guide") for _, i in sample}
    codes.discard(None)
    with SessionLocal() as db:
        titles = {g.guide_code: g.title for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(list(codes))).all()}

    oai = OpenAI(api_key=settings.OPENAI_API_KEY)
    rows = []
    for k, (seg, cid) in enumerate(sample):
        if k % 20 == 0:
            print(f"  judging {k}/{len(sample)}", flush=True)
        og, ng = off[cid].get("top_guide"), on[cid].get("top_guide")
        ot, nt = titles.get(og), titles.get(ng)
        swap = random.random() < 0.5
        ta, tb = (nt, ot) if swap else (ot, nt)
        sa, sb, reason = judge(oai, args.model, rich_text(cases[cid]), ta, tb)
        if sa is None:
            rows.append({"case_id": cid, "seg": seg, "error": True})
            continue
        on_s = sa if swap else sb
        off_s = sb if swap else sa
        if og is None:
            off_s = 0
        rows.append({"case_id": cid, "seg": seg, "industry": cases[cid].get("industry_context"),
                     "off_guide": og, "on_guide": ng, "off_score": off_s, "on_score": on_s, "reason": reason})

    valid = [r for r in rows if not r.get("error")]
    def agg(sub):
        if not sub:
            return {}
        n = len(sub)
        offm = sum(r["off_score"] for r in sub) / n
        onm = sum(r["on_score"] for r in sub) / n
        win = sum(1 for r in sub if r["on_score"] > r["off_score"])
        tie = sum(1 for r in sub if r["on_score"] == r["off_score"])
        loss = sum(1 for r in sub if r["on_score"] < r["off_score"])
        return {"n": n, "off_mean": round(offm, 3), "on_mean": round(onm, 3),
                "delta": round(onm - offm, 3), "on_win": win, "tie": tie, "on_loss": loss,
                "off_adequate(>=2)": sum(1 for r in sub if r["off_score"] >= 2),
                "on_adequate(>=2)": sum(1 for r in sub if r["on_score"] >= 2)}

    summary = {"all": agg(valid),
               "rescue": agg([r for r in valid if r["seg"] == "rescue"]),
               "both": agg([r for r in valid if r["seg"] == "both"]),
               "errored": len(rows) - len(valid),
               "model": args.model}
    print("\n=== LLM-judge 결과 (0=무관 1=부분 2=적합) ===")
    for seg in ("all", "rescue", "both"):
        s = summary[seg]
        if s:
            print(f"[{seg:7s}] n={s['n']:3d}  off_mean={s['off_mean']:.3f}  on_mean={s['on_mean']:.3f}  "
                  f"delta={s['delta']:+.3f}  | on win/tie/loss = {s['on_win']}/{s['tie']}/{s['on_loss']}  "
                  f"| 적합(>=2) off={s['off_adequate(>=2)']} on={s['on_adequate(>=2)']}")
    OUT_JSON.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
