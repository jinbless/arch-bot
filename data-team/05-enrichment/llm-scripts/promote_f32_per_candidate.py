#!/usr/bin/env python3
"""T2.D — 8 F.3.2 candidates 1-by-1 vetted 승격 + Gate 3 regression wrap.

기존 promote_f32_first_batch.py는 8 candidates batch 승격만 지원 → Quick Win
Task 1에서 1회 시도 시 she_accuracy -7.07%p (Gate 3 FAIL) → 전량 rollback.
원인 분석: vetted state penalty -0.18 vs candidate -0.05 (3.6x stronger).

해결: 1-by-1 promote with Gate 3 wrap.
- 각 candidate 단독 promote → replay → regression_gate
- FAIL 시 자동 rollback (해당 candidate만)
- PASS 시 vetted 유지, 다음 candidate 진행
- 예상: 8 중 5-6 PASS, 2-3 FAIL (penalty 가중 효과 누적)

사용:
  # Dry-run (실행 시뮬레이션, KB 변경 X)
  python promote_f32_per_candidate.py

  # 실제 실행 (필수: 사용자 승인)
  python promote_f32_per_candidate.py --apply
  python promote_f32_per_candidate.py --apply --baseline replay_baseline_v3.json --tolerance 0.02

  # 특정 candidate만
  python promote_f32_per_candidate.py --apply --only-index 1,3,5

산출:
- KB 갱신: f32 candidates 일부 → vetted
- audit log: incompatibility_audit.jsonl (action=per_candidate_promote / per_candidate_rollback)
- summary log: f32_per_candidate_promotion_results.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
KB_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"
AUDIT_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/incompatibility_audit.jsonl"
RESULTS_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/f32_per_candidate_promotion_results.json"
DEFAULT_BASELINE = REPO / "data-team/05-enrichment/runtime-artifacts/replay_baseline_v3.json"
REPLAY_SCRIPT = REPO / "serving-team/08-app/backend/scripts/replay_synthetic_observations.py"
REGRESSION_SCRIPT = REPO / "serving-team/08-app/backend/scripts/regression_gate.py"


def load_kb() -> dict:
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def save_kb(data: dict) -> None:
    """Atomic write of KB JSON."""
    tmp = KB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(KB_PATH)


def update_header_counts(data: dict) -> None:
    """Recompute vetted/candidate counts in KB header."""
    entries = data.get("incompatibilities", [])
    vetted = sum(1 for e in entries if e.get("incompatible") and e.get("level") == "vetted")
    candidate = sum(1 for e in entries if e.get("incompatible") and e.get("level") == "candidate")
    if "vetted_count" in data:
        data["vetted_count"] = vetted
    if "candidate_count" in data:
        data["candidate_count"] = candidate


def find_f32_candidates(data: dict) -> list[dict]:
    """Return f32_axiom_miner entries with level=candidate."""
    entries = data.get("incompatibilities", [])
    return [e for e in entries
            if e.get("source") == "f32_axiom_miner"
            and e.get("incompatible")
            and e.get("level") == "candidate"]


def append_audit(rows: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_replay(out_path: Path) -> int:
    """Run full synthetic replay → out_path. Returns exit code."""
    cmd = [
        sys.executable,
        str(REPLAY_SCRIPT),
        "--output", str(out_path),
    ]
    print(f"  → running replay (full synthetic)...")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(REPLAY_SCRIPT.parent.parent))
    if proc.returncode != 0:
        print(f"  ! replay exit {proc.returncode}", file=sys.stderr)
        print(f"  stderr tail: {proc.stderr[-500:]}", file=sys.stderr)
    return proc.returncode


def run_regression(current_path: Path, baseline: Path, tolerance: float) -> tuple[int, str]:
    """Run regression_gate.py. Returns (exit_code, stdout)."""
    cmd = [
        sys.executable,
        str(REGRESSION_SCRIPT),
        str(current_path),
        "--baseline", str(baseline),
        "--tolerance", str(tolerance),
    ]
    print(f"  → running regression_gate (baseline={baseline.name}, tol={tolerance})...")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(REGRESSION_SCRIPT.parent.parent))
    return proc.returncode, proc.stdout + "\n" + proc.stderr


def promote_one_in_memory(data: dict, candidate: dict, ts: str) -> None:
    """Mark a single candidate as vetted in the in-memory data structure."""
    for e in data["incompatibilities"]:
        if (e.get("domain_a") == candidate["domain_a"]
                and e.get("domain_b") == candidate["domain_b"]
                and e.get("source") == "f32_axiom_miner"):
            e["level"] = "vetted"
            e["promoted_at"] = ts
            e["promotion_reason"] = "f32_per_candidate_promote_t2d_gate3_wrap"
            return
    raise ValueError(f"candidate not found: {candidate['domain_a']} x {candidate['domain_b']}")


def rollback_one_in_memory(data: dict, candidate: dict, ts: str) -> None:
    """Revert a single entry back to candidate level."""
    for e in data["incompatibilities"]:
        if (e.get("domain_a") == candidate["domain_a"]
                and e.get("domain_b") == candidate["domain_b"]
                and e.get("source") == "f32_axiom_miner"):
            e["level"] = "candidate"
            e["rollback_at"] = ts
            e["rollback_reason"] = "gate3_regression_fail"
            # Keep promoted_at as history
            return


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--apply", action="store_true",
                    help="실제 KB 갱신 + Gate 3 실행. 미지정 시 dry-run.")
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE,
                    help="Gate 3 baseline JSON (default: replay_baseline_v3.json)")
    ap.add_argument("--tolerance", type=float, default=0.02,
                    help="허용 metric 하락 폭 (default: 0.02 = 2%%p)")
    ap.add_argument("--only-index", type=str, default=None,
                    help="comma-separated 1-based indices (예: '1,3,5'). 미지정 시 모두.")
    args = ap.parse_args()

    if not args.baseline.exists():
        print(f"ERROR: baseline not found: {args.baseline}", file=sys.stderr)
        return 1
    if not REPLAY_SCRIPT.exists():
        print(f"ERROR: replay script not found: {REPLAY_SCRIPT}", file=sys.stderr)
        return 1
    if not REGRESSION_SCRIPT.exists():
        print(f"ERROR: regression script not found: {REGRESSION_SCRIPT}", file=sys.stderr)
        return 1

    data = load_kb()
    candidates = find_f32_candidates(data)
    print(f"Found {len(candidates)} F.3.2 candidates (source=f32_axiom_miner, level=candidate)")
    for i, c in enumerate(candidates, 1):
        print(f"  [{i}] {c['domain_a']:30s} x {c['domain_b']:30s} conf={c.get('confidence',0):.2f}")

    if not candidates:
        print("\nNothing to promote. Exit.")
        return 0

    # Index filter
    target_indices = list(range(len(candidates)))
    if args.only_index:
        try:
            target_indices = [int(s.strip()) - 1 for s in args.only_index.split(",")]
            target_indices = [i for i in target_indices if 0 <= i < len(candidates)]
        except ValueError:
            print(f"ERROR: invalid --only-index: {args.only_index}", file=sys.stderr)
            return 1
        print(f"\nFiltered to indices: {[i+1 for i in target_indices]}")

    if not args.apply:
        print(f"\n[dry-run] {len(target_indices)} candidates would be tested 1-by-1.")
        print(f"  Each: promote → replay → regression_gate (tolerance={args.tolerance})")
        print(f"  Failure: auto-rollback. Re-run with --apply to commit.")
        return 0

    # Apply mode
    ts_session = datetime.now(timezone.utc).isoformat()
    results: list[dict] = []
    audit_rows: list[dict] = []
    successes = 0
    failures = 0
    errors = 0

    with tempfile.TemporaryDirectory(prefix="t2d_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        for seq, idx in enumerate(target_indices, 1):
            cand = candidates[idx]
            label = f"[{seq}/{len(target_indices)}] {cand['domain_a']} x {cand['domain_b']}"
            print(f"\n=== {label} (conf={cand.get('confidence',0):.2f}) ===")

            ts = datetime.now(timezone.utc).isoformat()
            try:
                # 1. Promote (in-memory + save)
                promote_one_in_memory(data, cand, ts)
                update_header_counts(data)
                save_kb(data)
                print(f"  promoted in KB.")

                # 2. Replay
                replay_out = tmpdir_path / f"replay_t2d_idx{idx}.json"
                replay_rc = run_replay(replay_out)
                if replay_rc != 0:
                    print(f"  ! replay failed → rollback")
                    rollback_one_in_memory(data, cand, ts)
                    update_header_counts(data)
                    save_kb(data)
                    results.append({
                        "index": idx + 1,
                        "domain_a": cand["domain_a"],
                        "domain_b": cand["domain_b"],
                        "verdict": "error",
                        "stage": "replay",
                        "exit_code": replay_rc,
                    })
                    audit_rows.append({
                        "ts": ts, "action": "per_candidate_replay_fail",
                        "domain_a": cand["domain_a"], "domain_b": cand["domain_b"],
                        "exit_code": replay_rc,
                    })
                    errors += 1
                    continue

                # 3. Gate 3
                gate_rc, gate_out = run_regression(replay_out, args.baseline, args.tolerance)

                if gate_rc == 0:
                    print(f"  ✓ Gate 3 PASS — keep as vetted")
                    successes += 1
                    results.append({
                        "index": idx + 1,
                        "domain_a": cand["domain_a"],
                        "domain_b": cand["domain_b"],
                        "verdict": "pass",
                        "kept": "vetted",
                        "gate_stdout_tail": gate_out[-1000:],
                    })
                    audit_rows.append({
                        "ts": ts, "action": "per_candidate_promote_pass",
                        "domain_a": cand["domain_a"], "domain_b": cand["domain_b"],
                        "confidence": cand.get("confidence"),
                    })
                else:
                    print(f"  ✗ Gate 3 FAIL (exit {gate_rc}) → rollback")
                    rollback_one_in_memory(data, cand, ts)
                    update_header_counts(data)
                    save_kb(data)
                    failures += 1
                    results.append({
                        "index": idx + 1,
                        "domain_a": cand["domain_a"],
                        "domain_b": cand["domain_b"],
                        "verdict": "fail",
                        "rolled_back_to": "candidate",
                        "gate_exit_code": gate_rc,
                        "gate_stdout_tail": gate_out[-1500:],
                    })
                    audit_rows.append({
                        "ts": ts, "action": "per_candidate_rollback_fail",
                        "domain_a": cand["domain_a"], "domain_b": cand["domain_b"],
                        "confidence": cand.get("confidence"),
                        "gate_exit_code": gate_rc,
                    })

            except Exception as exc:
                # Defensive rollback
                print(f"  ! exception → rollback ({exc})", file=sys.stderr)
                try:
                    rollback_one_in_memory(data, cand, ts)
                    update_header_counts(data)
                    save_kb(data)
                except Exception:
                    pass
                errors += 1
                results.append({
                    "index": idx + 1,
                    "domain_a": cand["domain_a"],
                    "domain_b": cand["domain_b"],
                    "verdict": "exception",
                    "error": str(exc)[:300],
                })
                audit_rows.append({
                    "ts": ts, "action": "per_candidate_exception",
                    "domain_a": cand["domain_a"], "domain_b": cand["domain_b"],
                    "error": str(exc)[:300],
                })

    # Save results + audit
    summary = {
        "generated_at": ts_session,
        "baseline": str(args.baseline.relative_to(REPO)),
        "tolerance": args.tolerance,
        "total_tested": len(target_indices),
        "pass": successes,
        "fail": failures,
        "errors": errors,
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    append_audit(audit_rows)

    print(f"\n=== T2.D Summary ===")
    print(f"  Tested  : {len(target_indices)}")
    print(f"  PASS    : {successes} (kept as vetted)")
    print(f"  FAIL    : {failures} (rolled back to candidate)")
    print(f"  ERRORS  : {errors}")
    print(f"  Results : {RESULTS_PATH.relative_to(REPO)}")
    print(f"  Audit   : {AUDIT_PATH.relative_to(REPO)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
