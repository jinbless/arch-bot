#!/usr/bin/env python3
"""T2.C — F.3.5 drift detection (weekly cycle 정확도 모니터링).

baseline_v3 vs 현재 replay 결과 비교, false_negative_rate 등 핵심 metric
이 ±tolerance 초과 시 drift 알림. cron weekly 운영 가정.

특히 false_negative_rate가 +2%p 초과 시 (true positives을 놓치는 경향
증가) → axiom 추가 reject가 자동 학습 loop를 통해 누적되고 있을 가능성.
즉시 검토 필요.

사용:
  # baseline_v3 vs 자동 replay
  python f3_drift_check.py

  # 명시적 입력
  python f3_drift_check.py --current /tmp/replay_recent.json --baseline replay_baseline_v3.json

  # 임계치 조정
  python f3_drift_check.py --tolerance 0.03 --critical-fn 0.025

  # JSON output (CI / slack hook용)
  python f3_drift_check.py --json

산출:
- stdout: 사람읽기 좋은 표
- f3_drift_log.jsonl: per-run row append (시계열 보존)
- exit code: 0 (no drift), 1 (warning), 2 (critical)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_BASELINE = ARTIFACTS / "replay_baseline_v3.json"
DRIFT_LOG = ARTIFACTS / "f3_drift_log.jsonl"

# Metrics tracked + meaning
METRICS = {
    "she_accuracy": "SHE matcher hit rate",
    "sr_accuracy": "SR mapping correctness",
    "penalty_accuracy": "Penalty path correctness",
    "overall_accuracy": "End-to-end correctness",
    "false_positive_rate": "Wrong SHE matched",
    "false_negative_rate": "True SHE missed (drift 핵심 지표)",
}


def load_metrics(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary") or {}
    return {k: float(summary.get(k, 0.0)) for k in METRICS}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--current", type=Path, default=None,
                    help="현재 replay 결과 JSON. 미지정 시 가장 최근 replay_results_*.json")
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE,
                    help="baseline JSON (default: replay_baseline_v3.json)")
    ap.add_argument("--tolerance", type=float, default=0.02,
                    help="general drift tolerance (default 0.02)")
    ap.add_argument("--critical-fn", type=float, default=0.02,
                    help="false_negative_rate critical 임계 (default 0.02)")
    ap.add_argument("--json", action="store_true",
                    help="JSON output (slack hook / CI 통합용)")
    args = ap.parse_args()

    # Resolve current
    if args.current is None:
        candidates = sorted(ARTIFACTS.glob("replay_results_*.json"))
        if not candidates:
            print(f"ERROR: --current not given and no replay_results_*.json found",
                  file=sys.stderr)
            return 3
        args.current = candidates[-1]
        print(f"Using auto-detected current: {args.current.name}")

    # Resolve to absolute paths for relative_to() safety
    args.baseline = args.baseline.resolve()
    args.current = args.current.resolve()

    if not args.baseline.exists():
        print(f"ERROR: baseline not found: {args.baseline}", file=sys.stderr)
        return 3
    if not args.current.exists():
        print(f"ERROR: current not found: {args.current}", file=sys.stderr)
        return 3

    baseline_m = load_metrics(args.baseline)
    current_m = load_metrics(args.current)

    deltas: dict[str, float] = {}
    verdicts: dict[str, str] = {}  # ok / warning / critical
    max_severity = 0  # 0=ok 1=warning 2=critical

    for metric, _desc in METRICS.items():
        b = baseline_m[metric]
        c = current_m[metric]
        delta = c - b
        deltas[metric] = delta

        # FN rate special-case: positive delta = bad (missing more)
        if metric == "false_negative_rate":
            if delta > args.critical_fn:
                verdicts[metric] = "critical"
                max_severity = max(max_severity, 2)
            elif delta > args.tolerance:
                verdicts[metric] = "warning"
                max_severity = max(max_severity, 1)
            else:
                verdicts[metric] = "ok"
        # FP rate: positive delta = bad
        elif metric == "false_positive_rate":
            if delta > args.tolerance:
                verdicts[metric] = "warning"
                max_severity = max(max_severity, 1)
            else:
                verdicts[metric] = "ok"
        # Accuracy metrics: negative delta = bad
        else:
            if -delta > args.tolerance:
                verdicts[metric] = "warning"
                max_severity = max(max_severity, 1)
            else:
                verdicts[metric] = "ok"

    ts = datetime.now(timezone.utc).isoformat()
    def _maybe_rel(p: Path) -> str:
        try:
            return str(p.relative_to(REPO))
        except ValueError:
            return str(p)

    result = {
        "ts": ts,
        "baseline": _maybe_rel(args.baseline),
        "current": _maybe_rel(args.current),
        "tolerance": args.tolerance,
        "critical_fn": args.critical_fn,
        "metrics": {
            metric: {
                "baseline": baseline_m[metric],
                "current": current_m[metric],
                "delta": deltas[metric],
                "verdict": verdicts[metric],
            }
            for metric in METRICS
        },
        "overall_verdict": ["ok", "warning", "critical"][max_severity],
    }

    # Append drift log (time-series preserve)
    try:
        DRIFT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DRIFT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"WARN: drift log append failed: {exc}", file=sys.stderr)

    # Output
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print()
        print(f"=== F.3.5 Drift Check ({ts}) ===")
        print(f"baseline: {args.baseline.name}")
        print(f"current : {args.current.name}")
        print(f"tolerance: {args.tolerance}  critical_fn: {args.critical_fn}")
        print()
        print(f"{'metric':<26} {'baseline':>10} {'current':>10} {'delta':>10}  {'verdict':<10}")
        print("-" * 78)
        for metric, desc in METRICS.items():
            b = baseline_m[metric]
            c = current_m[metric]
            d = deltas[metric]
            v = verdicts[metric]
            sign = "+" if d >= 0 else ""
            marker = {"ok": "ok ", "warning": "WARN", "critical": "CRIT"}[v]
            print(f"{metric:<26} {b:>10.4f} {c:>10.4f} {sign}{d:>9.4f}  {marker:<10} {desc}")
        print()
        print(f"OVERALL: {result['overall_verdict'].upper()}")
        if max_severity == 2:
            print("\n⚠ CRITICAL — false_negative_rate drift 초과. 즉시 검토:")
            print("  1. recent F.3.0/3.2 promote 확인")
            print("  2. kosha-disjoint-axioms.ttl rollback 검토")
            print("  3. promote_f32_per_candidate 로 1-by-1 재검증")
        elif max_severity == 1:
            print("\n⚠ WARNING — 모니터링 강화 권장. 1주 후 재측정.")

    return max_severity  # 0/1/2


if __name__ == "__main__":
    sys.exit(main())
