#!/usr/bin/env python3
"""synthetic 케이스 → {case_id, work_context, case_type, scene} jsonl (Claude-agent 태깅 입력).

scene = photo_description + visual_cues(=GPT가 인식한 장면). expected_*(정답)은 미포함(독립 태깅).
--cases-from <jsonl> 으로 특정 case_id만, --positive-only 가능.
사용: python scripts/export_case_scenes.py [--cases-from gold_articles.jsonl] [--out PATH] [--positive-only]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
EVAL = REPO / "data-team" / "05-enrichment" / "eval-data"
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases-from", default=None, help="이 jsonl의 case_id만(예: gold_articles.jsonl)")
    ap.add_argument("--out", default=str(ART / "gold_cases.jsonl"))
    ap.add_argument("--positive-only", action="store_true")
    args = ap.parse_args()

    want = None
    if args.cases_from:
        want = set()
        for line in Path(args.cases_from).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("case_id") and not d.get("error"):
                    want.add(d["case_id"])
            except Exception:  # noqa: BLE001
                pass

    n = 0
    with open(args.out, "w", encoding="utf-8") as o:
        for f in sorted(EVAL.glob("synthetic_observations_v*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if want is not None and d.get("case_id") not in want:
                    continue
                if args.positive_only and d.get("case_type") != "positive":
                    continue
                scene = d.get("photo_description", "")
                vc = d.get("visual_cues") or []
                if vc:
                    scene += "\n시각단서: " + " / ".join(vc)
                o.write(json.dumps({
                    "case_id": d.get("case_id"), "work_context": d.get("work_context"),
                    "case_type": d.get("case_type"), "scene": scene,
                }, ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} cases → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
