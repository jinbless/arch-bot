#!/usr/bin/env python3
"""Phase 3C — Bootstrap SHE patterns for all synthetic v*.jsonl + import to PG.

Runs bootstrap_she_from_synthetic.py for each v file, then optionally imports.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SYNTH = ROOT / "data-team/05-enrichment/eval-data"
OUT_DIR = ROOT / "data-team/05-enrichment/runtime-artifacts/she-bootstrap"
BOOTSTRAP = ROOT / "serving-team/08-app/backend/scripts/bootstrap_she_from_synthetic.py"
PYTHON = "/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--import-pg", action="store_true", help="Pass --import-pg to bootstrap (load into PG)")
    p.add_argument("--include-matched", action="store_true")
    p.add_argument("--min-matched-dims", type=int, default=2)
    p.add_argument("--sr-limit", type=int, default=20)
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SYNTH.glob("synthetic_observations_v*.jsonl"))
    print(f"found {len(files)} synthetic files")

    total_input = 0
    total_generated = 0
    for fp in files:
        base = fp.stem
        out_path = OUT_DIR / f"{base}.jsonl"
        cmd = [
            PYTHON, "-u", str(BOOTSTRAP),
            "--input", str(fp),
            "--output", str(out_path),
            "--sr-limit", str(args.sr_limit),
            "--min-matched-dims", str(args.min_matched_dims),
        ]
        if args.include_matched:
            cmd.append("--include-matched")
        if args.import_pg:
            cmd.append("--import-pg")
        print(f"\n--- {base} ---")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        # Parse output for stats
        out_text = (result.stdout or "") + (result.stderr or "")
        for line in out_text.splitlines():
            if "input_cases" in line or "generated_candidates" in line or "imported" in line or "ERROR" in line:
                print(f"  {line.strip()}")
                if "input_cases=" in line:
                    total_input += int(line.split("=")[1].strip())
                if "generated_candidates=" in line:
                    total_generated += int(line.split("=")[1].strip())

    print(f"\n=== TOTAL ===")
    print(f"  input cases: {total_input}")
    print(f"  generated candidates: {total_generated}")
    print(f"  outputs in: {OUT_DIR}")


if __name__ == "__main__":
    main()
