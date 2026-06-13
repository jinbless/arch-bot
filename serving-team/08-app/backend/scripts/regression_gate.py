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
# WS-EVAL-4: 기본 baseline v1 → v3 (phase3-baseline-shift).
# WS-EVAL-1: v3 → v4 (hazards-injected, hazard-direct ON 경로 활성).
# MEAS-1/MEAS-3 (F19): v4 → v5. v4의 fp_rate 0.8696/fn_rate 0.0은 평가 정답(ecd) 주입의
#   구조적 상수였다 — 주입 제거 후 실측 fp 0.0906/fn 0.1489로 교체.
# VT backfill: v5 → v6. importer 버그로 유실된 phase3c 531패턴 visual_triggers 복구 →
#   overall +0.0221/penalty +0.0174 개선분 박제(fp/fn 무변화). 거버넌스:
#   docs/status/evaluation-baseline.md anchor + provenance. make verify-baseline이 일치 검증.
DEFAULT_BASELINE = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "replay_baseline_v6.json"
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


def compare(
    baseline: dict[str, Any],
    current: dict[str, Any],
    tolerance: float,
    fn_tolerance: float = FN_VETO_TOLERANCE,
) -> dict[str, Any]:
    """Return dict of metric → {baseline, current, delta, vetoed}.

    vetoed=True 면 그 metric 단독으로 회귀 fail 사유가 된다.
    fn_tolerance: FN-방향(recall) 키의 비대칭 허용폭(기본 0.005, 일반 tolerance보다 엄격).
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
            "vetoed": d_psr < -fn_tolerance,
            "direction": "expect_higher",
        }
        # she_recall_miss = 1 - recall (절차 유무 무관). false_negative_rate와 대비해 진짜 miss를 노출.
        b_miss = round(1.0 - b_psr, 4)
        c_miss = round(1.0 - c_psr, 4)
        findings["she_recall_miss"] = {
            "baseline": b_miss,
            "current": c_miss,
            "delta": round(c_miss - b_miss, 4),
            "vetoed": (c_miss - b_miss) > fn_tolerance,
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

    # WS-EVAL-1: hazard-direct ON 경로 recall — FN-방향 비대칭 veto (gold-independent, 즉시 enforce).
    #   baseline에 키가 없으면(v3→v4 전환 전) veto 보류 — 0.0 default 대비는 거짓 veto이므로
    #   (OBS-1의 baseline 재캡처 가드와 동일 철학). v4 채택 후 키가 생기면 실제 enforce.
    def _fn_finding(key: str, higher: bool) -> None:
        if key not in current and key not in baseline:
            return
        b = float(baseline.get(key, 0.0))
        c = float(current.get(key, 0.0))
        d = round(c - b, 4)
        present = key in baseline
        vetoed = present and (d < -fn_tolerance if higher else d > fn_tolerance)
        f: dict[str, Any] = {
            "baseline": round(b, 4), "current": round(c, 4), "delta": d,
            "vetoed": vetoed, "direction": "expect_higher" if higher else "expect_lower",
        }
        if not present:
            f["note"] = "baseline에 키 부재 — v4 재캡처 후 enforce"
        findings[key] = f

    #   guide_coverage_rate(↑): should_match_she positive가 ON guide를 받는 비율 — 하락=recall 회귀.
    _fn_finding("guide_coverage_rate", higher=True)
    #   she_recall_miss_rate(↓): 순수 SHE miss(positive&should_match_she&미매칭) — 상승=recall 회귀.
    _fn_finding("she_recall_miss_rate", higher=False)
    # WS-EVAL-1: guide_recall@K / top1 — gold(WS-EVAL-2) 의존 → observe-only(WARN, 결정 D13=B).
    #   gold set 안정화 + 2주 관찰 후 hard veto로 승격. 지금은 보고만(veto 안 함).
    for key in ("guide_recall_at3", "top1_relevance_rate"):
        if key in baseline or key in current:
            b = float(baseline.get(key, 0.0))
            c = float(current.get(key, 0.0))
            findings[key] = {
                "baseline": round(b, 4), "current": round(c, 4), "delta": round(c - b, 4),
                "vetoed": False, "direction": "expect_higher",
                "note": "observe-only (gold WS-EVAL-2 안정화 후 hard veto 승격)",
            }
    return findings


def render(findings: dict[str, dict[str, Any]]) -> str:
    lines = []
    header = f"{'metric':<25s} {'baseline':>10s} {'current':>10s} {'delta':>10s}  {'verdict':<10s}"
    lines.append(header)
    lines.append("-" * len(header))
    for key, f in findings.items():
        if f["vetoed"]:
            verdict = "VETOED"
        elif str(f.get("note", "")).startswith("observe"):
            verdict = "observe"
        else:
            verdict = "ok"
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
        "--fn-tolerance",
        type=float,
        default=FN_VETO_TOLERANCE,
        help=f"FN-방향(recall) 키 비대칭 허용폭 (기본 {FN_VETO_TOLERANCE}). 일반보다 엄격 — "
             "안전 도메인에서 recall 회귀는 specificity 개선으로 상쇄 불가.",
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

    findings = compare(baseline, current, args.tolerance, args.fn_tolerance)
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
            f"  · positive_she_recall / she_recall_miss / guide_coverage_rate / she_recall_miss_rate "
            f"= FN-방향 비대칭 veto (tolerance {args.fn_tolerance}, 일반 {args.tolerance})"
        )
        print(
            f"  · guide_recall_at3 / top1_relevance_rate = WS-EVAL-1 observe-only "
            f"(gold WS-EVAL-2 안정화 후 hard veto 승격 — 현재 veto 안 함)"
        )
        print()
        if passed:
            print("PASS — 회귀 통과")
        else:
            print(f"FAIL — vetoed metrics: {', '.join(vetoed_keys)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
