#!/usr/bin/env python3
"""Phase I — F.3.2 candidate 자동 batch promotion.

Plan B (docs/workplans/ontology-axiom-100pct.md) Phase I 실행:
- KB JSON (runtime-artifacts/guide_domain_incompatibilities.json) 의 f32_axiom_miner candidate 중
  confidence ≥ --min-conf (default 0.85) 자동 batch promotion.
- promote_f32_per_candidate.py를 wrapper로 호출하여 1-by-1 Gate 3 wrap.
- FAIL 시 자동 rollback (per-candidate level), PASS 시 vetted 유지.
- 결과 집계: f32_auto_batch_results.json + audit log append.

LLM cost: 본 스크립트 자체는 LLM call 없음 (기존 confidence 활용).
Plan B의 "Sonnet 4.6 verify $10-20" cost는 별도 LLM verify 단계 추가 시 발생.
본 batch는 PG/JSON KB transition + Gate 3 sequential replay (backend infra만 필요).

사용:
  # Dry-run (실행 시뮬레이션, KB 변경 X)
  python promote_f32_auto_batch.py --min-conf 0.85

  # 실제 실행 (backend venv + PG access 필요)
  python promote_f32_auto_batch.py --apply --min-conf 0.85

  # 더 보수적인 conf threshold
  python promote_f32_auto_batch.py --apply --min-conf 0.9

  # 50개 batch 단위 (default), Gate 3 fail 시 rollback
  python promote_f32_auto_batch.py --apply --batch-size 50

산출:
- KB 갱신: f32 candidates 일부 → vetted
- audit log: incompatibility_audit.jsonl (action=auto_batch_promote / auto_batch_rollback)
- summary: data-team/05-enrichment/runtime-artifacts/f32_auto_batch_results.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
KB_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"
RESULTS_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/f32_auto_batch_results.json"
AUDIT_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/incompatibility_audit.jsonl"
PER_CANDIDATE_SCRIPT = REPO / "data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py"


def load_kb() -> dict:
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def find_eligible_candidates(data: dict, min_conf: float) -> list[tuple[int, dict]]:
    """KB의 candidate (level=candidate, source != self_refine)에서 confidence >= min_conf인 항목과 idx 반환.

    Note: plan B의 "2,184 F.3.2 candidate"는 KB JSON에서 source 필드가 명시되지 않은
    candidate 항목들 (mining 출처는 generated_at + model 헤더로 추적). f32_axiom_miner는
    이미 vetted 8건. 본 batch는 vetted/self_refine 외 모든 candidate를 대상.
    """
    entries = data.get("incompatibilities", [])
    eligible = []
    for idx, e in enumerate(entries):
        if (e.get("incompatible")
                and e.get("level") == "candidate"
                and e.get("source") != "self_refine"
                and float(e.get("confidence", 0.0)) >= min_conf):
            eligible.append((idx, e))
    return eligible


def run_per_candidate(indices: list[int], apply: bool, baseline: str | None,
                      tolerance: float) -> tuple[int, str, str]:
    """promote_f32_per_candidate.py를 호출하여 indices subset만 promote.

    Returns: (returncode, stdout, stderr).
    """
    cmd = [
        sys.executable,
        str(PER_CANDIDATE_SCRIPT),
        "--only-index", ",".join(str(i) for i in indices),
    ]
    if apply:
        cmd.append("--apply")
    if baseline:
        cmd.extend(["--baseline", baseline])
    if tolerance is not None:
        cmd.extend(["--tolerance", str(tolerance)])

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(REPO))
    return proc.returncode, proc.stdout, proc.stderr


def append_audit(rows: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="F.3.2 candidate 자동 batch promotion (Plan B Phase I)")
    parser.add_argument("--apply", action="store_true",
                        help="실제 KB 변경 + Gate 3 실행. 기본은 dry-run.")
    parser.add_argument("--min-conf", type=float, default=0.85,
                        help="promotion confidence threshold (default 0.85).")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="batch size (default 50). 각 batch sequential.")
    parser.add_argument("--baseline", type=str, default=None,
                        help="Gate 3 baseline JSON path.")
    parser.add_argument("--tolerance", type=float, default=0.02,
                        help="Gate 3 tolerance (default 0.02).")
    parser.add_argument("--max-batches", type=int, default=None,
                        help="제한 (debug). None이면 전체.")
    args = parser.parse_args()

    if not KB_PATH.exists():
        print(f"ERROR: KB not found: {KB_PATH}", file=sys.stderr)
        sys.exit(1)

    data = load_kb()
    eligible = find_eligible_candidates(data, args.min_conf)
    total = len(eligible)
    print(f"=== F.3.2 auto-batch promotion ===")
    print(f"KB: {KB_PATH}")
    print(f"min-conf: {args.min_conf}, batch-size: {args.batch_size}")
    print(f"Eligible candidates: {total}")

    if total == 0:
        print("No eligible candidates. Exit.")
        sys.exit(0)

    if not args.apply:
        print(f"\n[DRY-RUN] {total} candidates would be processed in {(total + args.batch_size - 1) // args.batch_size} batches.")
        print("Top 10 by confidence:")
        sorted_eligible = sorted(eligible, key=lambda t: -float(t[1].get("confidence", 0.0)))
        for idx, e in sorted_eligible[:10]:
            print(f"  [{idx}] conf={e['confidence']:.3f} {e.get('domain_a', '?')} x {e.get('domain_b', '?')}")
        print(f"\nRe-run with --apply to execute (LLM call 없음, backend Gate 3 sequential replay 필요).")
        sys.exit(0)

    # Real execution
    indices = [idx for idx, _ in eligible]
    batches = [indices[i:i + args.batch_size] for i in range(0, len(indices), args.batch_size)]
    if args.max_batches is not None:
        batches = batches[:args.max_batches]

    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "min_conf": args.min_conf,
        "batch_size": args.batch_size,
        "total_eligible": total,
        "batches_planned": len(batches),
        "batches": [],
    }

    for bi, batch_indices in enumerate(batches, 1):
        print(f"\n--- Batch {bi}/{len(batches)} ({len(batch_indices)} candidates) ---")
        t0 = time.time()
        rc, stdout, stderr = run_per_candidate(
            batch_indices, apply=True,
            baseline=args.baseline, tolerance=args.tolerance,
        )
        elapsed = time.time() - t0
        batch_record = {
            "batch_index": bi,
            "indices": batch_indices,
            "returncode": rc,
            "elapsed_sec": round(elapsed, 1),
            "stdout_tail": stdout[-500:] if stdout else "",
            "stderr_tail": stderr[-300:] if stderr else "",
        }
        summary["batches"].append(batch_record)
        print(f"  returncode={rc}, elapsed={elapsed:.1f}s")
        if rc != 0:
            print(f"  ! Batch {bi} FAILED. stderr tail: {stderr[-300:]}", file=sys.stderr)
            # 다음 batch 진행 여부 결정 — 기본은 stop on first fail
            print(f"  Stopping at first failed batch. Re-run with adjusted parameters.")
            break

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== DONE ===")
    print(f"Results: {RESULTS_PATH}")
    print(f"Batches completed: {len(summary['batches'])}/{summary['batches_planned']}")
    failed = sum(1 for b in summary['batches'] if b['returncode'] != 0)
    print(f"Failed batches: {failed}")


if __name__ == "__main__":
    main()
