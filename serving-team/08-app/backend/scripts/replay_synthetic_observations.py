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


def _expected_to_hazards(case: dict[str, Any]) -> list[dict[str, Any]]:
    """WS-EVAL-1 — synthetic expected_features → 합성 hazard payload(GPT hazards[] 모사).

    근본 원인 해소: build_fake_result가 hazards를 안 만들어 analysis_pipeline의 hazard-direct
    ON 경로(match_hazards_to_guides / match_hazards_to_ci)가 replay에서 영구 dormant였다.
    GPT가 사진에서 산출하는 hazards[]를 expected_features로부터 합성해 ON 경로를 실제로 발동시킨다.

    설계(production-faithful + FP 무증가):
    - **NEGATIVE case는 hazard 0건** — 안전 장면에서 GPT는 빈 hazards[]를 낸다. 합성 hazard로
      negative에 절차를 만들면 false_positive_rate(이미 0.87)를 악화시키므로 절대 주입 안 함.
    - accident/agent 축이 모두 비면 합성 안 함(맥락만으론 hazard 단정 금지 — 과대생성 방지).
    - name=expected_primary_risk(자연어; normalize_hazards_array가 alias 매핑) + description=
      photo+visual_cues(semantic attach 매칭) → code/semantic 양 경로 발동.
    - legacy facet 경로(risk_feature_candidates)는 그대로 둬서 그쪽 무회귀.
    """
    if (case.get("case_type") or "") == "negative":
        return []
    expected = case.get("expected_features") or {}
    # hazard.name = canonical code. normalize_hazards_array._resolve_alias_code는 코드 직접매칭
    # (valid codes에 있으면 그대로)이라, expected_features의 정본 코드(FALL 등)를 name으로 쓰면
    # 매핑된다. 전체 문장(expected_primary_risk)을 name으로 쓰면 alias 미스로 0 guide가 났다.
    # work_context는 hazard가 아니라 breadth-gating context이므로 제외(legacy candidate 경로가
    # canonical.work_contexts로 전달 → match_hazards_to_guides context_work_contexts).
    codes = [t for t in (expected.get("accident_types") or []) if t]
    codes += [t for t in (expected.get("hazardous_agents") or []) if t]
    if not codes:
        return []
    cues = [c for c in (case.get("visual_cues") or []) if c]
    description = " ".join(
        p for p in [case.get("photo_description") or "", " ".join(cues)] if p
    ).strip()
    # MEAS-1(F19): 평가 정답(expected_corrective_direction)을 preventive_measures로 주입하면
    # (a) hazard_to_ci_service가 정답 텍스트로 CI를 grounding → immediate_actions 오염,
    # (b) hazard_to_guide_service가 정답 텍스트를 semantic 검색 쿼리에 결합 → guide_coverage_rate
    #     (FN-veto 키)가 정답 누수로 부풀려짐.
    # production에서 GPT는 사진에서 measures를 생성하므로, gold 미주입(빈 리스트)이 보수적·정직.
    measures: list[str] = []
    location = case.get("work_context") or ""
    # 축 코드별 1 hazard (normalize는 hazard당 첫 매칭 축 1코드만 취함 → 코드별 분리).
    return [
        {
            "name": code,
            "risk_level": "high",
            "location": location,
            "description": description,
            "preventive_measures": measures,
        }
        for code in codes
    ]


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
        # WS-EVAL-1: hazards[] 주입 → hazard-direct ON 경로(guide/ci/penalty) 실제 발동.
        "hazards": _expected_to_hazards(case),
        "overall_assessment": case.get("expected_primary_risk") or "",
        # MEAS-1(F19): 평가 정답(expected_corrective_direction)을 LLM immediate_actions로
        # 주입하지 않는다. 주입 시 ecd 보유 positive 1,224/1,377(88.9%)는 파이프라인이 절차
        # 추천을 전멸시켜도 actions_count>=1이라 FN 집계 불능이었고, negative 276 중 ecd 보유
        # 240건이 자동 FP → fp_rate가 평가셋 분포 상수(0.8696)로 고정됐다.
        # 빈 리스트 = 파이프라인 산출(CI/guide 유래)만 actions로 집계 → FN/FP 최초 실측화.
        # NOTE: overall_assessment(expected_primary_risk)는 summary 텍스트 전용(미채점)이라 유지.
        "immediate_actions": [],
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

    # WS-EVAL-1 — hazard-direct ON 경로 산출 측정.
    hgr = getattr(response, "hazard_guide_relations", None) or []
    on_guide_codes: list[str] = []
    for rel in hgr:
        for g in getattr(rel, "guides", None) or []:
            gc = getattr(g, "guide_code", None)
            if gc:
                on_guide_codes.append(gc)
    _seen: set[str] = set()
    on_guide_unique = [c for c in on_guide_codes if not (c in _seen or _seen.add(c))]
    has_on_guide = len(on_guide_unique) > 0

    # 순수 SHE recall miss (절차 유무 무관): positive & should_match_she & NOT matched.
    # 좁은 false_negative(절차·조치 0건)와 분리해 진짜 miss를 노출.
    she_recall_miss = case_type == "positive" and she_expected and not she_matched
    # gold-independent recall proxy: should_match_she positive가 ON guide를 1개라도 받았는가.
    guide_should = case_type == "positive" and she_expected
    guide_covered = guide_should and has_on_guide

    # gold(WS-EVAL-2) 있는 case만 guide_recall@3 / top1 산출 (synthetic엔 보통 부재 → None=observe-only).
    expected_guides = [c for c in (case.get("expected_guide_codes") or []) if c]
    guide_recall_at3 = None
    top1_relevant = None
    if expected_guides:
        top3 = set(on_guide_unique[:3])
        guide_recall_at3 = round(len(set(expected_guides) & top3) / len(expected_guides), 4)
        top1_relevant = bool(on_guide_unique and on_guide_unique[0] in set(expected_guides))

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
        # WS-EVAL-1
        "she_recall_miss": she_recall_miss,
        "on_guide_count": len(on_guide_unique),
        "has_on_guide": has_on_guide,
        "guide_should": guide_should,
        "guide_covered": guide_covered,
        "has_gold": bool(expected_guides),
        "guide_recall_at3": guide_recall_at3,
        "top1_relevant": top1_relevant,
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
                persist=False,  # 합성분석을 운영/데모 DB에 쓰지 않음(오염 방지)
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

    # WS-EVAL-1 — hazard-direct ON 경로 recall 측정.
    # 분모 = positive & should_match_she (= guide_should). gold 무관, 즉시 enforce 가능.
    she_should = [r for r in valid if r.get("guide_should")]
    n_should = len(she_should)
    she_recall_miss_n = sum(1 for r in she_should if r.get("she_recall_miss"))
    guide_covered_n = sum(1 for r in she_should if r.get("guide_covered"))
    # gold(WS-EVAL-2) 있는 case만 — 없으면 observe-only(veto 안 함). gold_eval_count로 투명 보고.
    gold_rows = [r for r in valid if r.get("has_gold")]
    avg_on_guides_pos = _avg([r.get("on_guide_count", 0) for r in valid if r.get("case_type") == "positive"])

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
        # WS-EVAL-1 — ON 경로 recall (gold-independent FN 지표 + gold-dependent observe-only)
        "she_should_count": n_should,
        "she_recall_miss_rate": _ratio(she_recall_miss_n, n_should),
        "guide_coverage_rate": _ratio(guide_covered_n, n_should),
        "avg_on_guides_positive": avg_on_guides_pos,
        "gold_eval_count": len(gold_rows),
        "guide_recall_at3": _avg([r["guide_recall_at3"] for r in gold_rows]) if gold_rows else 0.0,
        "top1_relevance_rate": _ratio(
            sum(1 for r in gold_rows if r.get("top1_relevant")), len(gold_rows)
        ),
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _avg(values: list[int]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _resolve_out_path(args: argparse.Namespace) -> Path:
    if args.save_baseline:
        return ARTIFACTS_DIR / "replay_baseline.json"
    if args.output:
        return Path(args.output)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ARTIFACTS_DIR / f"replay_results_{ts}.json"


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

    # 체크포인트/재개 (절전·중단 내성): 케이스별 결과를 append-only JSONL에 즉시 기록.
    # --resume 시 완료 case_id를 건너뛰고 이어서 실행 → 2,360-case 장시간 replay가
    # 노트북 절전으로 죽어도 처음부터 다시 안 돌린다. 기본 동작(미지정)은 불변.
    out_path = _resolve_out_path(args)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_path.with_suffix(out_path.suffix + ".checkpoint.jsonl")
    per_case: list[dict[str, Any]] = []
    done_ids: set[str] = set()
    if args.resume and ckpt_path.exists():
        for line in ckpt_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # 마지막 줄이 절전으로 잘렸을 수 있음 — skip
            cid = rec.get("case_id")
            if cid and cid not in done_ids:
                done_ids.add(cid)
                per_case.append(rec)
        print(f"[resume] 체크포인트에서 {len(done_ids)}건 복원 → 나머지만 실행")

    db = SessionLocal()
    try:
        with ckpt_path.open("a", encoding="utf-8") as ckpt:
            for idx, case in enumerate(cases):
                if idx % 50 == 0:
                    print(
                        f"  [{idx:4d}/{len(cases)}] {case.get('case_id'):<20s} "
                        f"{case.get('case_type', '?'):<8s} {case.get('industry_context', '')[:30]}",
                        flush=True,
                    )
                if case.get("case_id") in done_ids:
                    continue
                result = await run_one(db, case)
                per_case.append(result)
                ckpt.write(json.dumps(result, ensure_ascii=False) + "\n")
                ckpt.flush()  # 절전 시 마지막 케이스까지 보존
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

    out_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 완주 시 체크포인트 정리(부분 산출물 잔존 방지). 중단 시엔 남아 다음 --resume이 사용.
    try:
        ckpt_path.unlink()
    except OSError:
        pass
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
    parser.add_argument(
        "--resume",
        action="store_true",
        help="<output>.checkpoint.jsonl이 있으면 완료 case_id를 건너뛰고 이어서 실행 "
             "(절전·중단 내성). 완주 시 체크포인트 자동 삭제.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
