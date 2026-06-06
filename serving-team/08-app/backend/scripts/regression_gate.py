#!/usr/bin/env python3
"""Regression Gate — Phase 0.3.

replay_synthetic_observations.py 의 결과를 baseline과 비교한다.
F1/정확도가 임계치 이상 하락하면 exit 1 (변경 자동 vetoed),
회귀 통과 시 exit 0.

Phase A/B/C 에서 신규 axiom/incompatibility/rerank 적용 후
이 게이트를 통과해야 채택된다.

사용:
  python scripts/regression_gate.py current.json [--baseline path] [--tolerance 0.02]
  python scripts/regression_gate.py current.json --baseline replay_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
# WS-EVAL-4: 기본 baseline v1 → v3 (phase3-baseline-shift). v1/v2는 구 corpus 스냅샷,
# v3가 현행 정본(evaluation-baseline.md가 vs replay_baseline_v3.json으로 보고).
DEFAULT_BASELINE = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "replay_baseline_v3.json"
)


METRIC_KEYS = (
    "she_accuracy",
    "sr_accuracy",
    "penalty_accuracy",
    "overall_accuracy",
)
MAX_RATE_KEYS = (
    "false_positive_rate",
    "false_negative_rate",
)

# WS-OBS-1: FN-방향 1급 veto의 비대칭 허용폭. 일반 tolerance(0.02)보다 엄격(0.005) —
# 안전 도메인에서 missed hazard(recall 하락)는 specificity(FP) 개선으로 상쇄될 수 없다.
FN_VETO_TOLERANCE = 0.005


def _nested(d: dict, *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary") or payload
    if "she_accuracy" not in summary:
        raise ValueError(f"{path} does not contain expected summary keys")
    return summary


def compare(baseline: dict[str, Any], current: dict[str, Any], tolerance: float) -> dict[str, Any]:
    """Return dict of metric → {baseline, current, delta, vetoed}.

    vetoed=True 면 그 metric 단독으로 회귀 fail 사유가 된다.
    """
    findings: dict[str, dict[str, Any]] = {}
    for key in METRIC_KEYS:
        b = float(baseline.get(key, 0.0))
        c = float(current.get(key, 0.0))
        delta = round(c - b, 4)
        vetoed = delta < -tolerance
        findings[key] = {
            "baseline": b,
            "current": c,
            "delta": delta,
            "vetoed": vetoed,
            "direction": "expect_higher",
        }
    for key in MAX_RATE_KEYS:
        b = float(baseline.get(key, 0.0))
        c = float(current.get(key, 0.0))
        delta = round(c - b, 4)
        vetoed = delta > tolerance
        findings[key] = {
            "baseline": b,
            "current": c,
            "delta": delta,
            "vetoed": vetoed,
            "direction": "expect_lower",
        }
    # WS-OBS-1: positive-only SHE recall — FN-방향 1급 veto.
    # 기존 false_negative_rate는 'positive인데 절차·조치 0건'이라는 좁은 정의(절차 전멸만 감지)라
    # SHE 패턴을 놓쳐도 절차가 1개라도 나오면 miss로 안 센다. per_case_type.positive.she_accuracy는
    # 절차 유무와 무관한 진짜 recall이므로, 이를 비대칭 tolerance(하락만 엄격)로 veto해 구멍을 막는다.
    b_psr = _nested(baseline, "per_case_type", "positive", "she_accuracy")
    c_psr = _nested(current, "per_case_type", "positive", "she_accuracy")
    if b_psr is not None and c_psr is not None:
        b_psr = float(b_psr)
        c_psr = float(c_psr)
        d_psr = round(c_psr - b_psr, 4)
        findings["positive_she_recall"] = {
            "baseline": round(b_psr, 4),
            "current": round(c_psr, 4),
            "delta": d_psr,
            "vetoed": d_psr < -FN_VETO_TOLERANCE,
            "direction": "expect_higher",
        }
        # she_recall_miss = 1 - recall (절차 유무 무관). false_negative_rate와 대비해 진짜 miss를 노출.
        b_miss = round(1.0 - b_psr, 4)
        c_miss = round(1.0 - c_psr, 4)
        findings["she_recall_miss"] = {
            "baseline": b_miss,
            "current": c_miss,
            "delta": round(c_miss - b_miss, 4),
            "vetoed": (c_miss - b_miss) > FN_VETO_TOLERANCE,
            "direction": "expect_lower",
        }
    else:
        # baseline이 신 키를 모르면(구 스냅샷) veto 불가 — crash/false-veto 대신 경고만.
        findings["positive_she_recall"] = {
            "baseline": float(b_psr or 0.0),
            "current": float(c_psr or 0.0),
            "delta": 0.0,
            "vetoed": False,
            "direction": "expect_higher",
            "note": "per_case_type.positive.she_accuracy 부재 — baseline 재캡처 필요",
        }
    return findings


def render(findings: dict[str, dict[str, Any]]) -> str:
    lines = []
    header = f"{'metric':<25s} {'baseline':>10s} {'current':>10s} {'delta':>10s}  {'verdict':<10s}"
    lines.append(header)
    lines.append("-" * len(header))
    for key, f in findings.items():
        verdict = "VETOED" if f["vetoed"] else "ok"
        arrow = "↑" if f["direction"] == "expect_higher" else "↓"
        lines.append(
            f"{key:<25s} {f['baseline']:>10.4f} {f['current']:>10.4f} {f['delta']:>+10.4f}  {verdict:<10s} {arrow}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "current",
        type=Path,
        help="현재 replay 결과 JSON (replay_synthetic_observations.py 산출물)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="baseline JSON (기본: data-team/05-enrichment/runtime-artifacts/replay_baseline.json)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="허용 하락 폭 (기본 0.02 = 2%%p). 이보다 큰 회귀 발생 시 vetoed.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON으로 stdout 출력 (CI 통합용)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.baseline.exists():
        print(f"Baseline not found: {args.baseline}", file=sys.stderr)
        print(
            "  → 먼저 `python scripts/replay_synthetic_observations.py --save-baseline` 실행 필요",
            file=sys.stderr,
        )
        return 2
    if not args.current.exists():
        print(f"Current result not found: {args.current}", file=sys.stderr)
        return 2

    baseline = load_summary(args.baseline)
    current = load_summary(args.current)

    findings = compare(baseline, current, args.tolerance)
    vetoed_keys = [k for k, f in findings.items() if f["vetoed"]]
    passed = not vetoed_keys

    if args.json:
        print(
            json.dumps(
                {
                    "passed": passed,
                    "tolerance": args.tolerance,
                    "baseline_path": str(args.baseline),
                    "current_path": str(args.current),
                    "findings": findings,
                    "vetoed_metrics": vetoed_keys,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"baseline: {args.baseline}")
        print(f"current : {args.current}")
        print(f"tolerance: {args.tolerance:.4f}")
        print()
        print(render(findings))
        print()
        print(
            f"  · positive_she_recall / she_recall_miss = WS-OBS-1 FN-방향 1급 veto "
            f"(비대칭 tolerance {FN_VETO_TOLERANCE}, 일반 {args.tolerance})"
        )
        print()
        if passed:
            print("PASS — 회귀 통과")
        else:
            print(f"FAIL — vetoed metrics: {', '.join(vetoed_keys)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
