#!/usr/bin/env python3
"""F.2 후속 — promote_she_review.py: pending_review SHE → approved_auto 신중 승격.

Day 5 lesson: 79 SHE 일괄 status='approved_auto' INSERT → matcher 손상 (she_accuracy -39.5%p).
해결: 5-by-5 incremental + Gate 3 regression 사이마다 → FAIL 시 즉시 rollback.

흐름:
1. 입력: PG she_catalog WHERE status='pending_review' (현재 77 rows)
2. 정렬: broadness_score ASC (specific first, ranking 영향 적음)
3. 배치 처리 (default batch_size=5):
   a. UPDATE status='approved_auto' for batch
   b. Run replay_synthetic_observations.py
   c. Run regression_gate.py (vs baseline_v3)
   d. PASS: commit, continue
   e. FAIL: ROLLBACK (status='pending_review'), exit + report
4. audit: promote_she_review_audit.jsonl

ENV: DATABASE_URL

사용:
  python promote_she_review.py --list                          # 현황만
  python promote_she_review.py --dry-run                       # 첫 5 batch plan
  python promote_she_review.py --apply --max-batches 1         # 5 SHE만 시도 (~5분)
  python promote_she_review.py --apply                         # 전체 (~80분, 16 batches)
  python promote_she_review.py --apply --batch-size 10         # 더 큰 batch (위험↑, 빠름)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
sys.path.insert(0, str(REPO_ROOT / "serving-team" / "08-app" / "backend"))

AUDIT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "promote_she_review_audit.jsonl"
BASELINE_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "replay_baseline_v3.json"
BACKEND_DIR = REPO_ROOT / "serving-team" / "08-app" / "backend"
REPLAY_SCRIPT = BACKEND_DIR / "scripts" / "replay_synthetic_observations.py"
REGRESSION_SCRIPT = BACKEND_DIR / "scripts" / "regression_gate.py"
# Use currently-running python (already in .venv per execution context)
VENV_PY = sys.executable


def fetch_pending(db, limit: int = 0, exclude_other: bool = True) -> list[dict]:
    """exclude_other=True: skip SHE with wc='OTHER' or at='OTHER' (catch-all → matcher 위험)."""
    from sqlalchemy import text
    where = "status='pending_review'"
    if exclude_other:
        where += " AND features->>'work_context' != 'OTHER' AND features->>'accident_type' != 'OTHER'"
    sql = f"""
        SELECT she_id, name, broadness_score,
               features->>'work_context' AS wc,
               features->>'accident_type' AS at
        FROM she_catalog
        WHERE {where}
        ORDER BY broadness_score ASC, she_id
    """
    if limit:
        sql += f" LIMIT {limit}"
    rows = db.execute(text(sql)).fetchall()
    return [{"she_id": r[0], "name": r[1], "broadness_score": r[2], "wc": r[3], "at": r[4]} for r in rows]


def promote_batch(db, batch: list[dict]) -> int:
    from sqlalchemy import text
    she_ids = [b["she_id"] for b in batch]
    db.execute(
        text("UPDATE she_catalog SET status='approved_auto' WHERE she_id = ANY(:ids) AND status='pending_review'"),
        {"ids": she_ids},
    )
    db.commit()
    return len(she_ids)


def rollback_batch(db, batch: list[dict]) -> int:
    from sqlalchemy import text
    she_ids = [b["she_id"] for b in batch]
    db.execute(
        text("UPDATE she_catalog SET status='pending_review' WHERE she_id = ANY(:ids) AND status='approved_auto'"),
        {"ids": she_ids},
    )
    db.commit()
    return len(she_ids)


def run_regression() -> tuple[bool, dict, str]:
    """Run replay + regression_gate. Return (pass, summary, log)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    try:
        # 1. Replay
        r1 = subprocess.run(
            [str(VENV_PY), "-u", str(REPLAY_SCRIPT), "--output", out_path],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if r1.returncode != 0:
            return False, {}, f"REPLAY FAIL exit={r1.returncode}\n{r1.stderr[-1000:]}"

        # 2. Regression gate
        r2 = subprocess.run(
            [str(VENV_PY), str(REGRESSION_SCRIPT), out_path, "--baseline", str(BASELINE_PATH)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = (r2.returncode == 0)
        summary = {"stdout": r2.stdout, "exit": r2.returncode}
        return passed, summary, r2.stdout
    finally:
        Path(out_path).unlink(missing_ok=True)


def append_audit(events: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps({"ts": ts, **ev}, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--max-batches", type=int, default=0, help="0 = no cap")
    parser.add_argument("--include-other", action="store_true", help="include SHE with wc='OTHER' or at='OTHER' (catch-all 위험)")
    args = parser.parse_args()
    if not (args.list or args.dry_run or args.apply):
        args.dry_run = True

    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        pending = fetch_pending(db, exclude_other=not args.include_other)
        n = len(pending)
        filter_note = " (wc/at='OTHER' 제외)" if not args.include_other else " (전체)"
        print(f"pending_review SHE{filter_note}: {n}")
        if n == 0:
            print("Nothing to promote.")
            return 0

        wc_counter: Counter = Counter()
        for p in pending:
            wc_counter[p["wc"]] += 1
        print(f"  by work_context (top 5):")
        for wc, c in wc_counter.most_common(5):
            print(f"    {wc}: {c}")
        print()

        if args.list:
            print("All pending SHE (broadness ASC):")
            for p in pending:
                print(f"  bs={p['broadness_score']}  {p['she_id']:36s}  wc={p['wc']!r:25s} at={p['at']!r}")
            return 0

        # Plan batches
        batches = [pending[i:i+args.batch_size] for i in range(0, n, args.batch_size)]
        if args.max_batches:
            batches = batches[:args.max_batches]
        print(f"Plan: {len(batches)} batches × ~{args.batch_size} each")
        print(f"  estimated time: ~{len(batches) * 5}분 (replay ~5min/batch)")
        print()

        if args.dry_run:
            print("[dry-run] first batch preview:")
            for p in batches[0][:args.batch_size]:
                print(f"  {p['she_id']:36s}  wc={p['wc']!r} at={p['at']!r}")
            return 0

        # APPLY: per-batch promote + regression + rollback-on-FAIL
        print("=" * 70)
        total_promoted = 0
        total_rolled = 0
        for i, batch in enumerate(batches, 1):
            print(f"\n[Batch {i}/{len(batches)}] promoting {len(batch)} SHE...")
            for p in batch:
                print(f"  - {p['she_id']:36s}  wc={p['wc']!r} at={p['at']!r}")

            n_up = promote_batch(db, batch)
            print(f"  status='approved_auto': {n_up} updated")

            print(f"  [Gate 3] running regression (~5min)...")
            passed, summary, log = run_regression()
            # Parse deltas from regression stdout
            print("  " + "\n  ".join((log or "").splitlines()[-10:]))

            event = {
                "batch": i, "batch_size": len(batch),
                "she_ids": [b["she_id"] for b in batch],
                "gate3_pass": passed,
            }

            if passed:
                total_promoted += len(batch)
                event["action"] = "promoted"
                append_audit([event])
                print(f"  ✅ PASS — kept promoted ({total_promoted} total)")
            else:
                # Rollback this batch
                n_rb = rollback_batch(db, batch)
                total_rolled += n_rb
                event["action"] = "rolled_back"
                event["gate3_log"] = log[-500:] if log else ""
                append_audit([event])
                print(f"  ❌ FAIL — rolled back {n_rb} SHE. Stopping sprint.")
                print(f"  Audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
                print(f"  → Total promoted before fail: {total_promoted}")
                return 1

        print()
        print("=" * 70)
        print(f"✅ All {len(batches)} batches PASSED. Promoted {total_promoted} SHE total.")
        print(f"   Audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
