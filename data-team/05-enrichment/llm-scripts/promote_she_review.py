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


def fetch_pending(db, limit: int = 0, exclude_other: bool = True, she_ids_filter: list[str] | None = None) -> list[dict]:
    """exclude_other=True: skip SHE with wc='OTHER' or at='OTHER' (catch-all → matcher 위험).

    she_ids_filter: if provided, restrict to these she_ids (intersected with pending_review).
    Manual review use case (T4 #1 후속, 2026-05-19): approve only manually-vetted 57.
    """
    from sqlalchemy import text
    where = "status='pending_review'"
    if exclude_other:
        where += " AND features->>'work_context' != 'OTHER' AND features->>'accident_type' != 'OTHER'"
    params: dict = {}
    if she_ids_filter is not None:
        where += " AND she_id = ANY(:ids)"
        params["ids"] = list(she_ids_filter)
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
    rows = db.execute(text(sql), params).fetchall()
    return [{"she_id": r[0], "name": r[1], "broadness_score": r[2], "wc": r[3], "at": r[4]} for r in rows]


def _count_status(db, she_ids: list[str], status: str) -> int:
    """Defensive verification helper — actual PG count for given she_ids in given status."""
    from sqlalchemy import text
    r = db.execute(
        text("SELECT COUNT(*) FROM she_catalog WHERE she_id = ANY(:ids) AND status=:s"),
        {"ids": she_ids, "s": status},
    ).scalar()
    return int(r or 0)


def promote_batch(db, batch: list[dict]) -> tuple[int, list[str]]:
    """Promote batch to approved_auto. Return (actual_updated_count, mismatched_ids).

    T1.A fix (rollback bug): return result.rowcount + verification.
    """
    from sqlalchemy import text
    she_ids = [b["she_id"] for b in batch]
    result = db.execute(
        text("UPDATE she_catalog SET status='approved_auto' WHERE she_id = ANY(:ids) AND status='pending_review'"),
        {"ids": she_ids},
    )
    actual_updated = int(result.rowcount or 0)
    db.commit()
    # Post-promote verification — ensure all batch she_ids are now 'approved_auto'
    expected = len(she_ids)
    now_approved = _count_status(db, she_ids, "approved_auto")
    mismatch = []
    if now_approved != expected:
        # Find which ids are NOT approved_auto
        from sqlalchemy import text
        rows = db.execute(
            text("SELECT she_id, status FROM she_catalog WHERE she_id = ANY(:ids) AND status != 'approved_auto'"),
            {"ids": she_ids},
        ).fetchall()
        mismatch = [r[0] for r in rows]
    return actual_updated, mismatch


def rollback_batch(db, batch: list[dict]) -> tuple[int, list[str]]:
    """Rollback batch to pending_review. Return (actual_rolled_count, stuck_ids).

    T1.A fix: returns actual rowcount + post-rollback verification.
    stuck_ids: she_ids that are STILL approved_auto after rollback (critical — investigate).
    """
    from sqlalchemy import text
    she_ids = [b["she_id"] for b in batch]
    result = db.execute(
        text("UPDATE she_catalog SET status='pending_review' WHERE she_id = ANY(:ids) AND status='approved_auto'"),
        {"ids": she_ids},
    )
    actual_rolled = int(result.rowcount or 0)
    db.commit()
    # Post-rollback verification — these MUST not be approved_auto anymore
    still_approved = _count_status(db, she_ids, "approved_auto")
    stuck_ids = []
    if still_approved > 0:
        rows = db.execute(
            text("SELECT she_id FROM she_catalog WHERE she_id = ANY(:ids) AND status='approved_auto'"),
            {"ids": she_ids},
        ).fetchall()
        stuck_ids = [r[0] for r in rows]
    return actual_rolled, stuck_ids


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
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        if r1.returncode != 0:
            return False, {}, f"REPLAY FAIL exit={r1.returncode}\n{r1.stderr[-1000:]}"

        # 2. Regression gate
        r2 = subprocess.run(
            [str(VENV_PY), str(REGRESSION_SCRIPT), out_path, "--baseline", str(BASELINE_PATH)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
    parser.add_argument("--only-from-review-json", type=str, default=None,
                        help="path to pending_review_she_REVIEWED.json; restrict promote to rows with decision='approve'")
    args = parser.parse_args()
    if not (args.list or args.dry_run or args.apply):
        args.dry_run = True

    # Manual review filter (T4 #1 후속): restrict to approve-only she_ids
    she_ids_filter = None
    if args.only_from_review_json:
        review = json.loads(Path(args.only_from_review_json).read_text(encoding="utf-8"))
        approved = [r["she_id"] for r in review.get("rows", []) if r.get("decision") == "approve"]
        she_ids_filter = approved
        print(f"[manual-review filter] approve she_ids: {len(approved)} (from {args.only_from_review_json})")

    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        pending = fetch_pending(db, exclude_other=not args.include_other, she_ids_filter=she_ids_filter)
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

            n_up, promote_mismatch = promote_batch(db, batch)
            print(f"  status='approved_auto': {n_up} actually updated (input: {len(batch)})")
            if promote_mismatch:
                # Some she_ids weren't 'pending_review' to start (skipped). Surface clearly.
                print(f"  ⚠️  {len(promote_mismatch)} she_ids skipped (not in pending_review state): {promote_mismatch[:5]}")

            print(f"  [Gate 3] running regression (~5min)...")
            passed, summary, log = run_regression()
            print("  " + "\n  ".join((log or "").splitlines()[-10:]))

            event = {
                "batch": i, "batch_size": len(batch),
                "she_ids": [b["she_id"] for b in batch],
                "gate3_pass": passed,
                "promote_actual_updated": n_up,
                "promote_skipped_ids": promote_mismatch,
            }

            if passed:
                total_promoted += n_up  # actual, not input count
                event["action"] = "promoted"
                append_audit([event])
                print(f"  ✅ PASS — kept promoted ({total_promoted} total actual)")
            else:
                # T1.A fix — defensive rollback with verification
                n_rb, stuck_ids = rollback_batch(db, batch)
                total_rolled += n_rb
                event["action"] = "rolled_back"
                event["rollback_actual"] = n_rb
                event["rollback_stuck_ids"] = stuck_ids  # CRITICAL — must be empty
                event["gate3_log"] = log[-500:] if log else ""
                append_audit([event])
                print(f"  ❌ FAIL — rolled back {n_rb} SHE actual.")
                if stuck_ids:
                    print(f"  🚨 CRITICAL: {len(stuck_ids)} SHE STILL approved_auto after rollback!")
                    print(f"     Stuck ids: {stuck_ids}")
                    print(f"     Run manual rollback: UPDATE she_catalog SET status='pending_review' WHERE she_id IN ({','.join(repr(i) for i in stuck_ids)})")
                    return 2  # critical failure code
                else:
                    print(f"  ✅ Rollback verified — all {len(batch)} she_ids restored to pending_review")
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
