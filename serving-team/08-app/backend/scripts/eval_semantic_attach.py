#!/usr/bin/env python3
"""Phase 5 — semantic attach 전 코퍼스 평가 (SEMANTIC_ATTACH off vs on).

각 synthetic case의 rich text(photo_description + visual_cues + corrective_direction)로
단일 hazard를 합성하고 match_hazards_to_guides를 off/on 두 패스 실행.

비교 설계(공정):
- off: hazard_name_to_codes에 **gold expected_features 코드를 직접 주입** → facet 경로의 상한
       (실제 GPT 시나리오에선 name이 코드로 안 풀려 0인 경우 많음 → off는 낙관적 상한).
- on : rich text 의미 recall(실제 GPT 시나리오) + facet 직접 보충.

gold: expected_features(canonical). per-hazard guide gold label 부재 →
      부착 guide의 canonical facet ∩ gold ≠ ∅ 를 on-topic@k proxy로 사용.
      (정확 forklift guide는 VEHICLE facet 보유 → 합리적 relevance proxy.)

실행: ./.venv/bin/python scripts/eval_semantic_attach.py [--limit N] [--output path]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_SHARED = Path(__file__).resolve().parents[4] / "shared" / "reference"
sys.path.insert(0, str(_SHARED))
import canonical_vocab as cv  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgKoshaGuide  # noqa: E402
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402

ARTIFACTS = Path(__file__).resolve().parents[4] / "data-team" / "05-enrichment" / "runtime-artifacts"


def canon_gold(exp: dict) -> set:
    out: set = set()
    for axis, key in (("accident_type", "accident_types"),
                      ("hazardous_agent", "hazardous_agents"),
                      ("work_context", "work_contexts")):
        for c in exp.get(key) or []:
            out.add(cv.to_canonical(axis, c))
    return out


def guide_facets(db, codes: list[str]) -> dict[str, set]:
    if not codes:
        return {}
    out: dict[str, set] = {}
    for g in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(codes)).all():
        pairs: set = set()
        for axis, col in (("accident_type", g.addresses_hazard_canonical),
                          ("hazardous_agent", g.hazardous_agents_canonical),
                          ("work_context", g.work_contexts_canonical)):
            for c in col or []:
                pairs.add((axis, c))
        out[g.guide_code] = pairs
    return out


def synth(case: dict):
    exp = case.get("expected_features") or {}
    rich = " ".join(filter(None, [
        case.get("photo_description", ""),
        " ".join(case.get("visual_cues") or []),
        case.get("expected_corrective_direction", ""),
    ]))
    name = (case.get("expected_primary_risk") or case.get("case_id") or "hazard")[:40]
    hazard = {"name": name, "risk_level": "high", "location": "",
              "description": rich, "preventive_measures": [case.get("expected_corrective_direction", "")]}
    codes = []
    for axis, key in (("accident_type", "accident_types"),
                      ("hazardous_agent", "hazardous_agents"),
                      ("work_context", "work_contexts")):
        for c in exp.get(key) or []:
            codes.append(f"{axis}.{c}")
    canonical = {"hazard_name_to_codes": {name: codes}, "work_contexts": exp.get("work_contexts") or []}
    return hazard, canonical


def run_pass(cases: list[dict], mode: str) -> list[dict]:
    os.environ["SEMANTIC_ATTACH"] = mode
    rows: list[dict] = []
    with SessionLocal() as db:
        for i, case in enumerate(cases):
            if i % 200 == 0:
                print(f"  [{mode}] {i}/{len(cases)}", flush=True)
            hz, canonical = synth(case)
            try:
                rels, _ = match_hazards_to_guides(db, [hz], canonical, industry_contexts=[])
            except Exception as e:  # noqa: BLE001
                rows.append({"case_id": case.get("case_id"), "error": str(e)[:120]})
                continue
            rel = rels[0] if rels else {}
            gcodes = [g["guide_code"] for g in (rel.get("guides") or []) if g.get("guide_code")]
            fac = guide_facets(db, gcodes)
            gold = canon_gold(case.get("expected_features") or {})
            def ontopic(k):
                return bool(gold) and any(fac.get(c, set()) & gold for c in gcodes[:k])
            rows.append({
                "case_id": case.get("case_id"),
                "industry": case.get("industry_context"),
                "n_guides": len(gcodes),
                "attach": rel.get("attach_method"),
                "ontopic@1": ontopic(1),
                "ontopic@3": ontopic(3),
                "top_guide": gcodes[0] if gcodes else None,
            })
    return rows


def summarize(rows: list[dict]) -> dict:
    valid = [r for r in rows if "error" not in r]
    scored = [r for r in valid if r.get("n_guides", 0) >= 0]
    n = len(scored) or 1
    has_guide = [r for r in scored if r["n_guides"] > 0]
    return {
        "n": len(scored),
        "errored": len(rows) - len(valid),
        "has_guide_rate": round(len(has_guide) / n, 4),
        "ontopic@1": round(sum(1 for r in scored if r.get("ontopic@1")) / n, 4),
        "ontopic@3": round(sum(1 for r in scored if r.get("ontopic@3")) / n, 4),
        "attach_methods": dict(Counter(r.get("attach") for r in scored)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output", type=str, default=None)
    args = ap.parse_args()

    cases = load_synthetic_cases(limit=args.limit)
    print(f"Loaded {len(cases)} cases")

    off = run_pass(cases, "off")
    on = run_pass(cases, "on")
    s_off, s_on = summarize(off), summarize(on)

    print("\n=== semantic attach 평가 (off=facet상한 / on=rich-text 의미 recall) ===")
    print(f"{'metric':<18s} {'off':>10s} {'on':>10s} {'delta':>10s}")
    for k in ("has_guide_rate", "ontopic@1", "ontopic@3"):
        d = round(s_on[k] - s_off[k], 4)
        print(f"{k:<18s} {s_off[k]:>10.4f} {s_on[k]:>10.4f} {d:>+10.4f}")
    print(f"\noff attach: {s_off['attach_methods']}")
    print(f"on  attach: {s_on['attach_methods']}")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = Path(args.output) if args.output else ARTIFACTS / "eval_semantic_attach.json"
    out.write_text(json.dumps({"summary": {"off": s_off, "on": s_on},
                               "off": off, "on": on}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
