#!/usr/bin/env python3
"""Merge 5 partial replay outputs into one combined result + recompute summary."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND.parent.parent))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="partial JSON paths")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    all_cases = []
    for path_str in args.inputs:
        path = Path(path_str)
        if not path.exists():
            print(f"WARN: {path} not found", file=sys.stderr)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        all_cases.extend(payload.get("cases") or [])
        print(f"Loaded {len(payload.get('cases') or [])} cases from {path.name}")

    # Recompute summary using replay_synthetic_observations.build_summary
    sys.path.insert(0, str(BACKEND / "scripts"))
    from replay_synthetic_observations import build_summary  # type: ignore

    summary = build_summary(all_cases)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "merge_replay_partials.py",
        "merged_from": [Path(p).name for p in args.inputs],
        "total_cases": len(all_cases),
        "summary": summary,
        "cases": all_cases,
    }
    args.output.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved merged: {args.output} ({len(all_cases)} cases)")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
