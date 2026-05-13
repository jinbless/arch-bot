#!/usr/bin/env python3
"""Build SituationFrame taxonomy and Guide support artifacts.

This script consumes the review-only Stage 3 SHE candidates and turns them into
non-asserted support data.  It never writes to the database and never promotes
SHE/SR mappings.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.exc import OperationalError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgChecklistItem, PgCiSrMapping, PgKoshaGuide, PgWorkProcess, PgWpSrMapping  # noqa: E402
from app.services.guide_domain_profile import evaluate_guide_domain_profile  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "koshaontology" / "data" / "she" / "she-stage3-new-pattern-candidates-reference-guard1.jsonl"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v2.json"
DEFAULT_CLASSIFICATION_OUTPUT = PROJECT_ROOT / "koshaontology" / "data" / "she" / "she_stage3_candidate_classification.v2.jsonl"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v2.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_REPORT_PREFIX = "situation_frame_artifact_build.v2"
CATALOG_PATH = BACKEND_DIR / "app" / "data" / "risk_feature_catalog.json"

EXPLICIT_CHILD_ALIASES = {
    "BLASTING_OPERATION": ["발파 작업", "폭약", "발파"],
    "CONVEYOR_HOOK": ["컨베이어 훅", "도체 훅", "훅 이탈"],
    "CRANE_OPERATION": ["크레인 작업", "타워크레인", "이동식크레인", "인양 작업"],
    "CUTTING_BONING": ["발골", "정형 작업", "육류 절단"],
    "CUTTING_FABRIC": ["재단 작업", "원단 절단", "섬유 재단"],
    "DEEP_FRYER": ["튀김기", "딥프라이어", "튀김 작업"],
    "DISHWASHING": ["식기세척", "설거지", "세척조"],
    "DUST_COLLECTION": ["집진기", "분진 포집", "집진 설비"],
    "FORMWORK_STRIPPING": ["거푸집 해체", "동바리 제거", "거푸집", "동바리"],
    "MAINTENANCE_HEIGHT": ["고소 점검", "고소 정비", "높은 곳 점검"],
    "MINE_GAS_DETECTION": ["광산 가스", "가스 검지", "갱내 가스"],
    "NEEDLE_BROKEN": ["바늘 파손", "부러진 바늘", "바늘 파편"],
    "PACKAGING_SEALING": ["진공 포장기", "실링 바", "포장기 실링"],
    "PATIENT_TRANSFER": ["환자 이동", "휠체어 이동", "침대 이동", "환자 이송"],
    "SLAUGHTER_LINE": ["도축 라인", "도축 작업", "도축장"],
    "SLICING_CUTTING": ["슬라이서", "절단기", "식품 절단"],
    "SOLDERING_ASSEMBLY": ["납땜", "납땜 인두", "인두", "PCB 납땜"],
    "SORTING_LINE": ["선별 라인", "분리 선별", "재활용 선별", "선별 작업"],
    "STEAM_KETTLE": ["스팀솥", "증기솥", "스팀 케틀"],
    "TRACTOR_OPERATION": ["트랙터", "트랙터 작업", "농기계 운전"],
    "UNDERGROUND_DRILLING": ["갱내 천공", "지하 천공", "천공 작업"],
}

SUPPORT_GUIDE_ALLOWLIST = {
    # First-cycle manual review gate.  Source SR overlap alone was too broad:
    # it pulled port cargo, bridge, solvent extraction, and bridge-girder
    # Guides into unrelated child contexts.  Keep only Guide families whose
    # usage profile is specific to the child context being materialized.
    "CONVEYOR_HOOK": {"B-M-33-2026", "G-20-2011"},
    "CRANE_OPERATION": {"D-C-10-2026"},
    "FORMWORK_STRIPPING": {"D-C-1-2025", "D-C-2-2025", "D-C-11-2026"},
    "PACKAGING_SEALING": {"B-M-33-2026"},
    "SORTING_LINE": {"B-M-33-2026"},
}

AMBIGUOUS_TERMS = (
    "여부", "불명", "불분명", "시도", "하려고", "아직", "가능성",
    "확인 불가", "일 수", "사진만으로", "착용 중", "정상", "완료",
)
UNSAFE_TERMS = (
    "미설치", "미착용", "미체결", "미차단", "노출", "파손", "손상",
    "누출", "가동", "회전", "끼임", "절단", "화상", "감전", "폭발",
    "추락", "붕괴", "환기", "방독마스크 없이", "보호구 없이", "장갑 없이",
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _candidate_text(row: dict[str, Any]) -> str:
    notes = row.get("notes") or {}
    evidence_cases = notes.get("evidence_cases") or []
    bits: list[str] = []
    bits.extend(row.get("visual_triggers") or [])
    bits.append(row.get("rationale") or "")
    for case in evidence_cases:
        bits.extend([
            case.get("case_type") or "",
            case.get("industry_context") or "",
            case.get("work_context") or "",
            case.get("photo_description") or "",
            case.get("expected_primary_risk") or "",
        ])
    return " ".join(bits)


def _child_alias_terms(child: str) -> list[str]:
    return _unique([
        child,
        child.replace("_", " "),
        child.lower(),
        child.lower().replace("_", " "),
        *(EXPLICIT_CHILD_ALIASES.get(child) or []),
    ])


def _load_catalog_work_contexts(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    codes = set()
    for code, info in (data.get("axes", {}).get("work_context", {}).get("codes", {}) or {}).items():
        codes.add(code)
        codes.update(info.get("sub") or [])
    return codes


def _classify_candidate(row: dict[str, Any], valid_work_contexts: set[str]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    reasons: list[str] = []
    features = row.get("features") or {}
    runtime = row.get("runtime_match_features") or {}
    child = features.get("work_context")
    parent = runtime.get("work_context")
    text = _candidate_text(row)
    source_sr_strength = row.get("source_sr_evidence_strength")
    if child and (child not in valid_work_contexts or child != parent):
        labels.append("taxonomy_gap")
        reasons.append("exact child context is not represented by the flat runtime work_context")
    if source_sr_strength in {"weak", "missing"} or row.get("promotion_blockers"):
        labels.append("sr_review_needed")
        reasons.append("source SR evidence is weak, missing, or blocker-marked")
    case_types = {
        (case.get("case_type") or "")
        for case in ((row.get("notes") or {}).get("evidence_cases") or [])
    }
    if "ambiguous" in case_types or "negative" in case_types or _contains_any(text, AMBIGUOUS_TERMS):
        labels.append("ambiguous_confirmation")
        reasons.append("candidate contains ambiguity, safe/normal, or confirmation-only cues")
    if (
        row.get("review_priority") == "high"
        and source_sr_strength == "medium"
        and features.get("accident_type") not in {"", "OTHER", None}
        and _contains_any(text, UNSAFE_TERMS)
        and "ambiguous_confirmation" not in labels
    ):
        labels.append("true_new_she")
        reasons.append("specific context plus risk axis plus visible unsafe cue")
    if row.get("source_sr_ids") and "ambiguous_confirmation" not in labels:
        labels.append("guide_support_only")
        reasons.append("safe first-cycle use is Guide/WP/CI support only")
    if not labels:
        labels.append("guide_support_only")
        reasons.append("default non-asserted support queue")
    return _unique(labels), _unique(reasons)


def _guide_codes_for_srs(db: Any, sr_ids: list[str], limit: int = 20) -> list[str]:
    if not sr_ids:
        return []
    counts: Counter[str] = Counter()
    wp_rows = (
        db.query(PgWorkProcess.source_guide, func.count(PgWorkProcess.identifier))
        .join(PgWpSrMapping, PgWpSrMapping.wp_id == PgWorkProcess.identifier)
        .filter(PgWpSrMapping.sr_id.in_(sr_ids))
        .group_by(PgWorkProcess.source_guide)
        .all()
    )
    for guide_code, count in wp_rows:
        if guide_code:
            counts[guide_code] += int(count or 0) * 2
    ci_rows = (
        db.query(PgChecklistItem.source_guide, func.count(PgChecklistItem.identifier))
        .join(PgCiSrMapping, PgCiSrMapping.ci_id == PgChecklistItem.identifier)
        .filter(PgCiSrMapping.sr_id.in_(sr_ids))
        .group_by(PgChecklistItem.source_guide)
        .all()
    )
    for guide_code, count in ci_rows:
        if guide_code:
            counts[guide_code] += int(count or 0)
    return [guide for guide, _ in counts.most_common(limit)]


def _filter_support_guides(
    db: Any,
    *,
    guide_codes: list[str],
    candidate: dict[str, Any],
    labels: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    if not guide_codes:
        return [], []
    features = candidate.get("features") or {}
    runtime = candidate.get("runtime_match_features") or {}
    child_context = features.get("work_context")
    allowlist = SUPPORT_GUIDE_ALLOWLIST.get(child_context)
    context_text = _candidate_text(candidate)
    visual_cues = candidate.get("visual_triggers") or []
    risk_feature_codes = _unique([
        features.get("accident_type"),
        features.get("hazardous_agent"),
        features.get("work_context"),
        runtime.get("work_context"),
    ])
    guides = {
        guide.guide_code: guide
        for guide in db.query(PgKoshaGuide).filter(PgKoshaGuide.guide_code.in_(guide_codes)).all()
    }
    accepted: list[str] = []
    review: list[dict[str, Any]] = []
    for guide_code in guide_codes:
        if allowlist is None or guide_code not in allowlist:
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": "manual_child_guide_boundary",
            })
            continue
        guide = guides.get(guide_code)
        if not guide:
            review.append({"guide_code": guide_code, "decision": "reject", "reason": "guide_missing"})
            continue
        decision = evaluate_guide_domain_profile(
            guide_code=guide_code,
            title=guide.title,
            profile_text=guide.title,
            industry_contexts=[],
            risk_feature_codes=risk_feature_codes,
            visual_cues=visual_cues,
            context_text=context_text,
        )
        if decision.exclude or decision.alignment == "domain_mismatch":
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": decision.alignment,
                "evidence": decision.evidence,
            })
            continue
        if decision.level != "general" and decision.alignment != "domain_match":
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": f"weak_{decision.level}_profile",
                "evidence": decision.evidence,
            })
            continue
        # First-cycle support should not route ambiguous candidates to Guides.
        if "ambiguous_confirmation" in labels:
            review.append({"guide_code": guide_code, "decision": "reject", "reason": "ambiguous_candidate"})
            continue
        accepted.append(guide_code)
        review.append({
            "guide_code": guide_code,
            "decision": "accept",
            "reason": decision.alignment,
            "evidence": decision.evidence,
        })
    return accepted[:8], review


def _build_taxonomy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    child_contexts: dict[str, dict[str, Any]] = {}
    parent_counts: Counter[str] = Counter()
    aliases: dict[str, list[str]] = {}
    for row in rows:
        features = row.get("features") or {}
        runtime = row.get("runtime_match_features") or {}
        child = features.get("work_context") or "OTHER"
        parent = runtime.get("work_context") or "OTHER"
        parent_counts[parent] += 1
        trigger_terms = _child_alias_terms(child)
        aliases[child] = _unique([*(aliases.get(child) or []), *trigger_terms])[:20]
        info = child_contexts.setdefault(
            child,
            {
                "parents": [],
                "aliases": [],
                "candidate_count": 0,
                "allowed_runtime_use": "guide_support_only",
            },
        )
        info["parents"] = _unique([*info["parents"], parent])
        info["aliases"] = _unique([*info["aliases"], *trigger_terms])[:20]
        info["candidate_count"] += 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": "v1",
        "policy": {
            "child_context_use": "meaning_and_guide_support",
            "parent_context_use": "search_expansion_only",
            "parent_only_match": "blocked_from_status_penalty_and_confirmed_she",
            "asserted_mapping_update": 0,
        },
        "parent_contexts": {
            parent: {"candidate_count": count, "allowed_runtime_use": "search_expansion_only"}
            for parent, count in sorted(parent_counts.items())
        },
        "child_contexts": dict(sorted(child_contexts.items())),
        "aliases": dict(sorted(aliases.items())),
    }


def _support_confidence(row: dict[str, Any], labels: list[str]) -> float:
    confidence = 0.52
    if row.get("source_sr_evidence_strength") == "medium":
        confidence += 0.08
    if "true_new_she" in labels:
        confidence += 0.05
    if "ambiguous_confirmation" in labels:
        confidence -= 0.12
    if "sr_review_needed" in labels:
        confidence -= 0.06
    return round(max(0.30, min(0.72, confidence)), 4)


def build_artifacts(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_jsonl(args.input)
    valid_work_contexts = _load_catalog_work_contexts(CATALOG_PATH)
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db.close()
        raise

    classifications: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    for row in rows:
        labels, reasons = _classify_candidate(row, valid_work_contexts)
        features = row.get("features") or {}
        runtime = row.get("runtime_match_features") or {}
        source_sr_ids = _unique(row.get("source_sr_ids") or [])
        raw_guide_codes = _guide_codes_for_srs(db, source_sr_ids)
        guide_codes, guide_review = _filter_support_guides(
            db,
            guide_codes=raw_guide_codes,
            candidate=row,
            labels=labels,
        )
        classification = {
            "candidate_id": row.get("she_id"),
            "review_status": row.get("review_status"),
            "source_review_priority": row.get("review_priority"),
            "classification_labels": labels,
            "classification_reasons": reasons,
            "child_context": features.get("work_context"),
            "runtime_parent_context": runtime.get("work_context"),
            "accident_type": features.get("accident_type"),
            "hazardous_agent": features.get("hazardous_agent"),
            "source_sr_ids": source_sr_ids,
            "source_sr_evidence_strength": row.get("source_sr_evidence_strength"),
            "promotion_blockers": row.get("promotion_blockers") or [],
            "guide_review": guide_review,
            "runtime_use": "guide_support_only",
            "asserted_mapping_update": 0,
        }
        classifications.append(classification)
        if source_sr_ids and guide_codes and "ambiguous_confirmation" not in labels:
            support_rows.append({
                "support_id": row.get("she_id"),
                "source_candidate_id": row.get("she_id"),
                "allowed_runtime_use": "guide_support_only",
                "child_context": features.get("work_context"),
                "parent_contexts": _unique([runtime.get("work_context")]),
                "accident_type": features.get("accident_type"),
                "hazardous_agent": features.get("hazardous_agent"),
                "trigger_terms": _unique(row.get("visual_triggers") or [])[:12],
                "guide_codes": guide_codes,
                "source_sr_ids": source_sr_ids,
                "candidate_labels": labels,
                "confidence": _support_confidence(row, labels),
                "evidence": row.get("rationale"),
                "review_status": "candidate",
                "policy": "support_only_no_status_penalty_no_asserted_sr",
            })
    db.close()

    taxonomy = _build_taxonomy(rows)
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_jsonl(args.classification_output, classifications)
    _write_jsonl(args.support_output, support_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": str(args.input),
        "candidate_count": len(rows),
        "classification_count": len(classifications),
        "support_candidate_count": len(support_rows),
        "classification_label_counts": dict(Counter(label for row in classifications for label in row["classification_labels"])),
        "runtime_parent_context_counts": dict(Counter(row["runtime_parent_context"] for row in classifications)),
        "support_guide_review_counts": dict(Counter(
            item.get("decision")
            for row in classifications
            for item in row.get("guide_review", [])
        )),
        "support_guide_reject_reasons": dict(Counter(
            item.get("reason")
            for row in classifications
            for item in row.get("guide_review", [])
            if item.get("decision") == "reject"
        )),
        "child_context_count": len(taxonomy["child_contexts"]),
        "asserted_mapping_update": 0,
        "runtime_she_approved_update": 0,
        "outputs": {
            "taxonomy": str(args.taxonomy_output),
            "classification": str(args.classification_output),
            "guide_support_candidates": str(args.support_output),
        },
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SituationFrame Artifact Build v2",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Candidates: `{summary['candidate_count']}`",
        f"- Classified: `{summary['classification_count']}`",
        f"- Guide support candidates: `{summary['support_candidate_count']}`",
        f"- Child contexts: `{summary['child_context_count']}`",
        "- Asserted mapping update: `0`",
        "- Runtime SHE approved update: `0`",
        "",
        "## Classification Labels",
        "",
    ]
    for label, count in sorted(summary["classification_label_counts"].items()):
        lines.append(f"- `{label}`: {count}")
    lines.extend(["", "## Runtime Parent Contexts", ""])
    for label, count in sorted(summary["runtime_parent_context_counts"].items(), key=lambda item: (-item[1], str(item[0]))):
        lines.append(f"- `{label}`: {count}")
    lines.extend(["", "## Support Guide Review", ""])
    for label, count in sorted(summary["support_guide_review_counts"].items()):
        lines.append(f"- `{label}`: {count}")
    lines.extend(["", "## Support Guide Reject Reasons", ""])
    for label, count in sorted(summary["support_guide_reject_reasons"].items(), key=lambda item: (-item[1], str(item[0]))):
        lines.append(f"- `{label}`: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kind", "key", "count"])
        writer.writeheader()
        for label, count in sorted(summary["classification_label_counts"].items()):
            writer.writerow({"kind": "classification_label", "key": label, "count": count})
        for label, count in sorted(summary["runtime_parent_context_counts"].items(), key=lambda item: (-item[1], str(item[0]))):
            writer.writerow({"kind": "runtime_parent_context", "key": label, "count": count})
        for label, count in sorted(summary["support_guide_review_counts"].items()):
            writer.writerow({"kind": "support_guide_review", "key": label, "count": count})
        for label, count in sorted(summary["support_guide_reject_reasons"].items(), key=lambda item: (-item[1], str(item[0]))):
            writer.writerow({"kind": "support_guide_reject_reason", "key": label, "count": count})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--classification-output", type=Path, default=DEFAULT_CLASSIFICATION_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        summary = build_artifacts(args)
    except OperationalError as exc:
        print(f"[ERROR] PostgreSQL is not reachable: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, summary)
    print("=== SituationFrame Artifacts ===")
    print(f"candidate_count: {summary['candidate_count']}")
    print(f"classification_count: {summary['classification_count']}")
    print(f"support_candidate_count: {summary['support_candidate_count']}")
    print(f"child_context_count: {summary['child_context_count']}")
    print(f"wrote: {args.taxonomy_output}")
    print(f"wrote: {args.classification_output}")
    print(f"wrote: {args.support_output}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    main()
