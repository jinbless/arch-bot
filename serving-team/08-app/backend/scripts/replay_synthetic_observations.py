#!/usr/bin/env python3
"""Synthetic Replay 인프라 — Phase 0.

2,360 synthetic_observations (v1~v10) 를 backend의 full pipeline에 inject한다.
Vision LLM 단계를 우회하기 위해 expected_features를 ONTOLOGY_OBSERVATION_SCHEMA 형식의
fake result로 변환하고 analysis_pipeline.run을 직접 호출한다.

목적:
- 모든 후속 Phase (B/A/C) 의 회귀 게이트 backbone
- precision/recall/F1 metric 산출
- over-promote 차단 효과 측정 (case_type='negative'에서 procedure 발생률)

사용:
  python scripts/replay_synthetic_observations.py --save-baseline
  python scripts/replay_synthetic_observations.py --limit 50
  python scripts/replay_synthetic_observations.py --output custom.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _find_repo_root() -> Path:
    """Walk up until we find data-team/05-enrichment/eval-data.

    Robust across both the primary repo path and any worktree.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError(
        "Cannot locate repo root: data-team/05-enrichment/eval-data not found"
    )


REPO_ROOT = _find_repo_root()
EVAL_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"

sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.analysis_pipeline import AnalysisRunInput, analysis_pipeline  # noqa: E402

logging.getLogger("app").setLevel(logging.WARNING)


PENALTY_EXPOSURE_MAP = {
    "DIRECT": "direct",
    "CONDITIONAL": "conditional",
    "NONE": "no_penalty",
    "NO_PENALTY": "no_penalty",
}


def load_synthetic_cases(
    limit: int | None = None,
    start_idx: int = 0,
    end_idx: int | None = None,
) -> list[dict[str, Any]]:
    files = sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl"))
    cases: list[dict[str, Any]] = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if start_idx or end_idx is not None:
        cases = cases[start_idx:end_idx]
    if limit:
        cases = cases[:limit]
    return cases


def build_fake_result(case: dict[str, Any]) -> dict[str, Any]:
    """Synthetic case → ONTOLOGY_OBSERVATION_SCHEMA 호환 fake result.

    expected_features를 LLM 결과로 가정하고 inject. 정규화 + SHE + Guide
    추천 단계의 over-promote만 측정 대상이 된다.
    """
    expected = case.get("expected_features") or {}
    visual_cues = case.get("visual_cues") or []
    description = case.get("photo_description") or ""

    candidates: list[dict[str, Any]] = []
    axis_map = [
        ("accident_type", "accident_types"),
        ("hazardous_agent", "hazardous_agents"),
        ("work_context", "work_contexts"),
    ]
    for axis, key in axis_map:
        for term in expected.get(key) or []:
            if not term:
                continue
            candidates.append(
                {
                    "axis": axis,
                    "text": term,
                    "evidence": None,
                    "confidence": 0.9,
                }
            )

    fake_visual_observations = [
        {
            "text": description,
            "confidence": 0.9,
            "severity": "HIGH" if case.get("case_type") != "negative" else "MEDIUM",
        }
    ]

    fake_visual_cues = [
        {"text": cue, "cue_type": "object", "confidence": 0.9}
        for cue in visual_cues
        if cue
    ]

    return {
        "visual_observations": fake_visual_observations,
        "visual_cues": fake_visual_cues,
        "risk_feature_candidates": candidates,
        "overall_assessment": case.get("expected_primary_risk") or "",
        "immediate_actions": (
            [case["expected_corrective_direction"]]
            if case.get("expected_corrective_direction")
            else []
        ),
    }


def evaluate_case(case: dict[str, Any], response: Any) -> dict[str, Any]:
    """Backend response를 case의 expected_*와 비교."""
    expected_behavior = case.get("expected_pipeline_behavior") or {}
    case_type = case.get("case_type") or "unknown"
    industry_ctx = case.get("industry_context") or ""

    she_matched = bool(getattr(response, "situation_matches", None))
    she_expected = bool(expected_behavior.get("should_match_she", False))
    she_correct = she_matched == she_expected

    reasoning_trace = getattr(response, "reasoning_trace", None)
    sr_recommended = bool(
        getattr(reasoning_trace, "safety_requirements", None)
        if reasoning_trace
        else False
    )
    sr_expected = bool(expected_behavior.get("should_recommend_sr", False))
    sr_correct = sr_recommended == sr_expected

    penalty_expected_raw = expected_behavior.get("penalty_exposure") or "NONE"
    penalty_expected = PENALTY_EXPOSURE_MAP.get(
        str(penalty_expected_raw).upper(), str(penalty_expected_raw).lower()
    )
    penalty_actual = getattr(response, "penalty_exposure_status", None) or "no_penalty"
    penalty_correct = penalty_expected == penalty_actual

    standard_procedures = getattr(response, "standard_procedures", None) or []
    immediate_actions = getattr(response, "immediate_actions", None) or []
    procedures_count = len(standard_procedures)
    actions_count = len(immediate_actions)

    procedure_titles = [
        getattr(p, "title", "") for p in standard_procedures if getattr(p, "title", None)
    ]
    procedure_guide_codes = [
        getattr(p, "guide_code", "") for p in standard_procedures if getattr(p, "guide_code", None)
    ]

    false_positive = case_type == "negative" and (procedures_count > 0 or actions_count > 0)
    false_negative = (
        case_type == "positive"
        and expected_behavior.get("should_match_she", False)
        and procedures_count == 0
        and actions_count == 0
    )

    finding_status = getattr(response, "finding_status", None) or "not_determined"
    overall_risk_level = getattr(response, "overall_risk_level", None)
    overall_risk_level_str = (
        overall_risk_level.value if hasattr(overall_risk_level, "value") else str(overall_risk_level)
    )

    return {
        "case_id": case.get("case_id"),
        "case_type": case_type,
        "industry_context": industry_ctx,
        "she_matched": she_matched,
        "she_expected": she_expected,
        "she_correct": she_correct,
        "sr_recommended": sr_recommended,
        "sr_expected": sr_expected,
        "sr_correct": sr_correct,
        "penalty_expected": penalty_expected,
        "penalty_actual": penalty_actual,
        "penalty_correct": penalty_correct,
        "procedures_count": procedures_count,
        "actions_count": actions_count,
        "procedure_titles": procedure_titles,
        "procedure_guide_codes": procedure_guide_codes,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "finding_status": finding_status,
        "overall_risk_level": overall_risk_level_str,
    }


async def run_one(db, case: dict[str, Any]) -> dict[str, Any]:
    fake_result = build_fake_result(case)
    case_id = case.get("case_id", "unknown")
    industry_text = case.get("industry_context")
    try:
        response = await analysis_pipeline.run(
            db=db,
            run_input=AnalysisRunInput(
                result=fake_result,
                analysis_type="text",
                input_preview=f"replay:{case_id}",
                full_description=case.get("photo_description", ""),
                declared_industry_text=industry_text,
            ),
        )
        return evaluate_case(case, response)
    except Exception as exc:
        return {
            "case_id": case_id,
            "case_type": case.get("case_type"),
            "industry_context": industry_text,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=3),
        }


def build_summary(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(per_case)
    errored = sum(1 for r in per_case if "error" in r)
    valid = [r for r in per_case if "error" not in r]
    n = len(valid)

    case_breakdown = Counter(r.get("case_type") for r in valid)
    industry_breakdown = Counter(r.get("industry_context") for r in valid)

    she_correct = sum(1 for r in valid if r.get("she_correct"))
    sr_correct = sum(1 for r in valid if r.get("sr_correct"))
    penalty_correct = sum(1 for r in valid if r.get("penalty_correct"))
    false_positives = sum(1 for r in valid if r.get("false_positive"))
    false_negatives = sum(1 for r in valid if r.get("false_negative"))
    overall_correct = sum(
        1
        for r in valid
        if r.get("she_correct") and r.get("sr_correct") and r.get("penalty_correct")
    )

    negatives = case_breakdown.get("negative", 0)
    positives = case_breakdown.get("positive", 0)

    per_case_type: dict[str, dict[str, Any]] = {}
    for ct in ("positive", "negative", "edge"):
        subset = [r for r in valid if r.get("case_type") == ct]
        if not subset:
            continue
        per_case_type[ct] = {
            "count": len(subset),
            "she_accuracy": _ratio(sum(1 for r in subset if r.get("she_correct")), len(subset)),
            "sr_accuracy": _ratio(sum(1 for r in subset if r.get("sr_correct")), len(subset)),
            "penalty_accuracy": _ratio(
                sum(1 for r in subset if r.get("penalty_correct")), len(subset)
            ),
            "avg_procedures": _avg([r.get("procedures_count", 0) for r in subset]),
            "avg_actions": _avg([r.get("actions_count", 0) for r in subset]),
        }

    avg_procedures = _avg([r.get("procedures_count", 0) for r in valid])
    avg_actions = _avg([r.get("actions_count", 0) for r in valid])

    return {
        "total": total,
        "valid": n,
        "errored": errored,
        "case_breakdown": dict(case_breakdown),
        "industry_breakdown_top10": dict(industry_breakdown.most_common(10)),
        "she_accuracy": _ratio(she_correct, n),
        "sr_accuracy": _ratio(sr_correct, n),
        "penalty_accuracy": _ratio(penalty_correct, n),
        "overall_accuracy": _ratio(overall_correct, n),
        "false_positive_count": false_positives,
        "false_positive_rate": _ratio(false_positives, negatives),
        "false_negative_count": false_negatives,
        "false_negative_rate": _ratio(false_negatives, positives),
        "avg_procedures": avg_procedures,
        "avg_actions": avg_actions,
        "per_case_type": per_case_type,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _avg(values: list[int]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


async def main_async(args: argparse.Namespace) -> int:
    cases = load_synthetic_cases(
        limit=args.limit,
        start_idx=args.start_idx,
        end_idx=args.end_idx,
    )
    if not cases:
        print(f"No cases loaded from {EVAL_DIR}", file=sys.stderr)
        return 1
    print(f"Loaded {len(cases)} cases from {EVAL_DIR}")

    db = SessionLocal()
    per_case: list[dict[str, Any]] = []
    try:
        for idx, case in enumerate(cases):
            if idx % 50 == 0:
                print(
                    f"  [{idx:4d}/{len(cases)}] {case.get('case_id'):<20s} "
                    f"{case.get('case_type', '?'):<8s} {case.get('industry_context', '')[:30]}",
                    flush=True,
                )
            result = await run_one(db, case)
            per_case.append(result)
    finally:
        db.close()

    summary = build_summary(per_case)
    output_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "replay_synthetic_observations.py",
        "case_limit": args.limit,
        "summary": summary,
        "cases": per_case,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.save_baseline:
        out_path = ARTIFACTS_DIR / "replay_baseline.json"
    elif args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = ARTIFACTS_DIR / f"replay_results_{ts}.json"

    out_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved: {out_path}")
    print("\n=== Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="저장 경로를 replay_baseline.json으로 고정 (Phase 0.2 baseline 측정용)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처음 N개 case만 실행 (디버깅용)",
    )
    parser.add_argument(
        "--start-idx",
        type=int,
        default=0,
        help="시작 case 인덱스 (multi-process 분할용)",
    )
    parser.add_argument(
        "--end-idx",
        type=int,
        default=None,
        help="종료 case 인덱스 (multi-process 분할용)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 경로 (지정 시 --save-baseline보다 우선)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
