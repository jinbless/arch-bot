#!/usr/bin/env python3
"""Build review-only Guide support candidates for current NO_TOP cases.

The output is a serving artifact preview.  It does not approve new SHE
patterns, does not write DB mappings, and does not create legal SR evidence.
Rows are accepted only when a specific SituationFrame child context has an
explicit Guide seed.  Parent-only and generic term-only routing stays blocked.
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


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_NO_TOP_REPORT = PROJECT_ROOT / "pictures-json" / "reports" / "stage2_5_no_top_root_cause_photo_matchability1.json"
DEFAULT_STAGE3_CANDIDATES = PROJECT_ROOT / "koshaontology" / "data" / "she" / "she-stage3-new-pattern-candidates-reference-guard1.jsonl"
DEFAULT_PROFILES = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v3.preview.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_REPORT_PREFIX = "no_top_guide_support_candidates_v1"

STAGE3_ROOT_CAUSES = {
    "stage3_she_to_sr_gap",
    "stage3_she_gap_but_sr_available",
}

PHOTO_ACTIONABLE = "photo_actionable"

GENERIC_TERMS = {
    "전원 차단",
    "절단",
    "끼임",
    "충돌",
    "추락",
    "화상",
    "보호구",
    "장갑",
    "보안경",
    "마스크",
    "환기",
    "MSDS",
    "잠금",
    "방호",
    "작업자",
    "작업 중",
    "관리",
    "점검",
    "교육",
}

# Explicit child-context seeds.  These are Guide recommendation support only:
# a seed never asserts SHE/SR/legal evidence by itself.
CHILD_GUIDE_SEEDS: dict[str, list[str]] = {
    # Machine and manufacturing
    "LATHE_MILLING": ["M-1-2013", "M-96-2012", "M-20-2012"],
    "GRINDING_POLISHING": ["B-M-14-2025", "B-M-39-2026"],
    "MACHINE_MAINTENANCE": ["B-M-37-2026"],
    "EQUIPMENT_MAINTENANCE": ["B-M-37-2026", "B-E-16-2026"],
    "FOOD_PROCESSING_LINE": ["B-M-6-2025", "B-M-2-2025"],
    "STERILIZATION_BLANCHING": ["B-M-6-2025"],
    "PACKAGING_OPERATION": ["M-161-2012"],
    "PACKAGING_SEALING": ["M-161-2012"],
    "INJECTION_MOLDING": ["M-187-2016", "M-56-2020"],
    "MOLDING_TOOL_CHANGE": ["M-187-2016", "M-56-2020"],
    "COMPOUND_MIXING": ["B-M-2-2025", "M-124-2012"],
    "EXTRUSION_OPERATION": ["M-57-2020"],
    "CONVEYOR_OPERATION": ["B-M-33-2026"],
    "CONVEYOR_HOOK": ["B-M-33-2026"],
    "SORTING_LINE": ["G-110-2014", "B-M-33-2026"],
    "COMPACTOR_OPERATION": ["G-131-2020", "M-177-2014"],
    "SHREDDER_OPERATION": ["B-M-3-2025", "B-M-4-2025", "G-131-2020"],
    "BAND_SAW": ["M-25-2012", "M-176-2014", "M-183-2015"],
    "TABLE_SAW": ["M-6-2012", "M-179-2014"],
    "PLANER_JOINTER": ["M-76-2013", "M-47-2012"],
    "CUTTING_FABRIC": ["M-180-2023"],
    "PAPER_CUTTING": ["M-180-2023"],
    "OFFSET_PRESS": ["M-193-2020"],
    "BINDING_MACHINE": ["M-193-2020"],
    "ASSEMBLY_PRESS": ["M-103-2017", "G-17-2017"],
    "YARN_WINDING": ["B-M-37-2026"],
    "SEWING_MACHINE": ["B-M-37-2026"],
    "NEEDLE_BROKEN": ["B-M-37-2026"],
    # Construction
    "EXCAVATION_WORK": ["D-C-11-2026", "D-C-4-2025"],
    "EARTH_RETAINING": ["D-C-1-2025", "D-C-11-2026"],
    "SOIL_COMPACTION": ["D-C-11-2026", "D-C-4-2025"],
    "TRENCH_WORK": ["D-C-11-2026", "D-C-1-2025"],
    "UNDERGROUND_UTILITY": ["B-E-2-2025", "D-C-11-2026"],
    "HEAVY_EQUIPMENT_OP": ["C-48-2022", "D-C-4-2025"],
    "FORMWORK_STRIPPING": ["D-C-9-2026", "D-C-8-2026"],
    "FORMWORK_ERECTION": ["D-C-9-2026", "D-C-8-2026"],
    "SCAFFOLD_ERECTION": ["D-C-7-2026"],
    "ROOFING_WORK": ["C-59-2022"],
    "STEEL_ERECTION": ["D-C-3-2025"],
    "DECKING_INSTALLATION": ["D-C-3-2025"],
    "PUMP_OPERATION": ["D-C-15-2026"],
    "REBAR_WORK": ["D-C-15-2026"],
    "CRANE_OPERATION": ["B-M-34-2026", "B-M-12-2025", "B-M-8-2025"],
    "SHAFT_HOIST": ["B-M-7-2026"],
    "UNDERGROUND_DRILLING": ["C-45-2012"],
    "TUNNEL_SUPPORT": ["C-45-2012"],
    "SCAFFOLDING_SHIP": ["D-C-7-2026", "G-116-2014"],
    # Food/service/healthcare
    "DEEP_FRYER": ["A-G-5-2025", "A-G-6-2025"],
    "STEAM_KETTLE": ["A-G-6-2025", "A-G-10-2025"],
    "DISHWASHING": ["A-G-6-2025", "A-G-10-2025"],
    "SLICING_CUTTING": ["A-G-5-2025", "B-M-6-2025"],
    "SCALDING_DEHAIRING": ["B-M-6-2025"],
    "SLAUGHTER_LINE": ["B-M-6-2025"],
    "PATIENT_TRANSFER": ["G-91-2012", "G-28-2016"],
    "NEEDLESTICK": ["E-M-3-2025"],
    "MEDICAL_WASTE": ["E-M-4-2025"],
    "MAINTENANCE_HEIGHT": ["D-C-13-2026"],
    # Chemical, waste, environment, energy
    "SOLDERING_ASSEMBLY": ["G-126-2018", "B-E-21-2026"],
    "CLEANING_SANITATION": ["C-C-16-2026", "C-C-29-2026"],
    "CLEANROOM_OPERATION": ["P-46-2012"],
    "PLATE_MAKING": ["C-C-29-2026"],
    "INK_HANDLING": ["P-34-2012"],
    "DYEING_FINISHING": ["B-M-15-2026"],
    "DUST_COLLECTION": ["D-43-2012", "F-2-2011"],
    "HAZARDOUS_WASTE": ["P-50-2012"],
    "HAZMAT_TRANSPORT": ["P-74-2011"],
    "COLD_CHAIN_HANDLING": ["W-17-2015", "C-70-2012"],
    "COLD_ROOM_WORK": ["W-17-2015", "C-70-2012"],
    "COLD_STORAGE_WORK": ["D-6-2012", "H-103-2012"],
    "CONCRETE_FINISHING": ["C-C-16-2026", "D-C-15-2026"],
    "BRAKE_EXHAUST_WORK": ["H-70-2020"],
    "ENGINE_OVERHAUL": ["G-131-2020"],
    "BLASTING_OPERATION": ["D-C-11-2026"],
    "MINE_GAS_DETECTION": ["C-45-2012"],
    "TRACTOR_OPERATION": ["M-165-2013", "M-133-2012"],
    "WASTE_COLLECTION": ["G-131-2020", "B-M-22-2026"],
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _unique(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _context_blob(*values: Any) -> str:
    bits: list[str] = []
    for value in values:
        if isinstance(value, list):
            bits.extend(str(item) for item in value if item)
        elif value:
            bits.append(str(value))
    return " ".join(bits)


def _profile_terms(profile: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in (
        "intended_workplaces",
        "intended_tasks",
        "observable_required_cues",
        "required_context_terms",
        "visual_triggers",
    ):
        value = profile.get(key) or []
        if isinstance(value, list):
            terms.extend(str(item) for item in value if item)
    boundary = profile.get("recommendation_boundary") or {}
    terms.extend(str(item) for item in (boundary.get("include_when") or []) if item)
    return _unique(terms)


def _term_hits(text: str, terms: list[str], limit: int = 8) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for term in terms:
        if len(str(term)) < 2 or term in GENERIC_TERMS:
            continue
        if str(term).lower() in lowered and term not in hits:
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


def _candidate_case_ids(row: dict[str, Any]) -> set[str]:
    return {
        str(case.get("case_id"))
        for case in ((row.get("notes") or {}).get("evidence_cases") or [])
        if case.get("case_id")
    }


def _candidate_text(row: dict[str, Any], no_top_cases: list[dict[str, Any]]) -> str:
    bits: list[Any] = []
    bits.extend(row.get("visual_triggers") or [])
    bits.append(row.get("rationale") or "")
    for case in (row.get("notes") or {}).get("evidence_cases") or []:
        bits.extend([
            case.get("industry_context"),
            case.get("work_context"),
            case.get("photo_description"),
            case.get("expected_primary_risk"),
        ])
    for case in no_top_cases:
        bits.extend([
            case.get("industry_context"),
            case.get("work_context"),
            case.get("photo_description"),
            case.get("expected_primary_risk"),
            case.get("expected_corrective_direction"),
        ])
    return _context_blob(bits)


def _load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "profiles" in data:
        return data["profiles"]
    return data


def _accepted_guides_for_child(
    *,
    child: str,
    text: str,
    profiles: dict[str, dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    review: list[dict[str, Any]] = []
    guides: list[str] = []
    seed_codes = CHILD_GUIDE_SEEDS.get(child) or []
    if not seed_codes:
        return [], [{"decision": "reject", "reason": "missing_child_guide_seed"}]
    for guide_code in seed_codes:
        profile = profiles.get(guide_code)
        if not profile:
            review.append({"guide_code": guide_code, "decision": "reject", "reason": "guide_profile_missing"})
            continue
        if profile.get("photo_matchability") != PHOTO_ACTIONABLE:
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": f"not_photo_actionable:{profile.get('photo_matchability')}",
            })
            continue
        if profile.get("procedure_role") != "field_control":
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": f"not_field_control:{profile.get('procedure_role')}",
            })
            continue
        hits = _term_hits(text, _profile_terms(profile), limit=6)
        if not hits:
            # The exact child context is already the structural evidence.  Keep
            # this separate from generic term hits so that the runtime can use it
            # only through SituationFrame child matching, never through broad
            # parent or title keyword expansion.
            guides.append(guide_code)
            review.append({"guide_code": guide_code, "decision": "accept", "reason": "explicit_child_seed_only"})
            continue
        guides.append(guide_code)
        review.append({"guide_code": guide_code, "decision": "accept", "reason": "child_seed_and_profile_term", "term_hits": hits[:4]})
    return guides[:6], review


def build_preview(args: argparse.Namespace) -> dict[str, Any]:
    no_top_report = json.loads(args.no_top_report.read_text(encoding="utf-8"))
    no_top_rows = [
        row for row in no_top_report.get("rows", [])
        if row.get("primary_root_cause") in STAGE3_ROOT_CAUSES
        and row.get("frame_match_policy") != "status_safe"
    ]
    no_top_by_case_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in no_top_rows:
        if row.get("case_id"):
            no_top_by_case_id[str(row["case_id"])].append(row)

    profiles = _load_profiles(args.profiles)
    stage3_rows = _read_jsonl(args.stage3_candidates)
    support_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    covered_case_ids: set[str] = set()

    for source in stage3_rows:
        features = source.get("features") or {}
        runtime = source.get("runtime_match_features") or {}
        child = str(features.get("work_context") or "")
        source_case_ids = _candidate_case_ids(source)
        matched_cases = [
            case
            for case_id in sorted(source_case_ids)
            for case in no_top_by_case_id.get(case_id, [])
        ]
        if not matched_cases:
            continue
        text = _candidate_text(source, matched_cases)
        guide_codes, guide_review = _accepted_guides_for_child(
            child=child,
            text=text,
            profiles=profiles,
        )
        reasons = [item.get("reason") for item in guide_review if item.get("decision") == "reject"]
        audit = {
            "source_candidate_id": source.get("she_id"),
            "child_context": child,
            "parent_contexts": _unique([runtime.get("work_context")]),
            "case_ids": sorted({case.get("case_id") for case in matched_cases if case.get("case_id")}),
            "domain_buckets": dict(Counter(case.get("domain_bucket") for case in matched_cases)),
            "root_causes": dict(Counter(case.get("primary_root_cause") for case in matched_cases)),
            "accepted_guide_codes": guide_codes,
            "guide_review": guide_review,
            "decision": "candidate" if guide_codes else "blocked",
            "blocked_reasons": _unique(reasons),
        }
        audit_rows.append(audit)
        if not guide_codes:
            continue
        case_ids = sorted({case.get("case_id") for case in matched_cases if case.get("case_id")})
        covered_case_ids.update(case_ids)
        has_profile_hit = any(
            item.get("decision") == "accept" and item.get("reason") == "child_seed_and_profile_term"
            for item in guide_review
        )
        support_rows.append({
            "support_id": f"NO_TOP-{source.get('she_id')}",
            "source_candidate_id": source.get("she_id"),
            "allowed_runtime_use": "guide_support_only",
            "child_context": child,
            "parent_contexts": _unique([runtime.get("work_context")]),
            "accident_type": features.get("accident_type"),
            "hazardous_agent": features.get("hazardous_agent"),
            "trigger_terms": _unique([
                *(source.get("visual_triggers") or []),
                *[case.get("photo_description") for case in matched_cases],
                *[case.get("expected_primary_risk") for case in matched_cases],
            ])[:14],
            "guide_codes": guide_codes,
            "source_sr_ids": _unique(source.get("source_sr_ids") or []),
            "candidate_labels": ["taxonomy_gap", "guide_support_only", "no_top_repair_preview"],
            "confidence": 0.62 if has_profile_hit else 0.56,
            "evidence": source.get("rationale"),
            "review_status": "candidate",
            "policy": "support_only_no_status_penalty_no_asserted_sr",
            "source_no_top_cases": case_ids,
            "guide_review": [item for item in guide_review if item.get("decision") == "accept"],
        })

    support_rows.sort(key=lambda row: (row["child_context"], row["source_candidate_id"]))
    _write_jsonl(args.support_output, support_rows)

    child_counts = Counter(row["child_context"] for row in support_rows)
    guide_counts = Counter(
        guide_code
        for row in support_rows
        for guide_code in row.get("guide_codes") or []
    )
    blocked_reasons = Counter(
        reason
        for row in audit_rows
        for reason in row.get("blocked_reasons") or []
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "policy": {
            "input_scope": "NO_TOP rows with Stage3/SHE-SR root causes only",
            "runtime_use": "guide_support_only",
            "status_penalty_update": 0,
            "asserted_mapping_update": 0,
            "parent_only_match": "blocked",
            "generic_term_only_match": "blocked",
        },
        "input_no_top_rows": len(no_top_rows),
        "stage3_candidate_rows": len(stage3_rows),
        "audit_rows": len(audit_rows),
        "support_candidate_rows": len(support_rows),
        "covered_no_top_case_count": len(covered_case_ids),
        "distinct_child_contexts": len(child_counts),
        "distinct_guide_codes": len(guide_counts),
        "child_context_counts": dict(child_counts.most_common()),
        "guide_code_counts": dict(guide_counts.most_common()),
        "blocked_reason_counts": dict(blocked_reasons.most_common()),
        "outputs": {
            "support_candidates": str(args.support_output),
        },
        "audit_rows": audit_rows,
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# NO_TOP Guide Support Candidates v1",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Input NO_TOP Stage3 rows: `{summary['input_no_top_rows']}`",
        f"- Audit rows: `{summary['audit_rows'] and len(summary['audit_rows'])}`",
        f"- Support candidate rows: `{summary['support_candidate_rows']}`",
        f"- Covered NO_TOP cases: `{summary['covered_no_top_case_count']}`",
        f"- Distinct child contexts: `{summary['distinct_child_contexts']}`",
        f"- Distinct Guide codes: `{summary['distinct_guide_codes']}`",
        "- Status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Policy",
        "",
        "- Uses only Stage3/SHE-SR NO_TOP rows.",
        "- Requires a specific child context and explicit child→Guide seed.",
        "- Blocks parent-only and generic term-only routing.",
        "- Emits Guide support candidates only; legal evidence is unchanged.",
        "",
        "## Child Contexts",
        "",
    ]
    for child, count in summary["child_context_counts"].items():
        lines.append(f"- `{child}`: {count}")
    lines.extend(["", "## Guide Codes", ""])
    for guide_code, count in summary["guide_code_counts"].items():
        lines.append(f"- `{guide_code}`: {count}")
    lines.extend(["", "## Blocked Reasons", ""])
    for reason, count in summary["blocked_reason_counts"].items():
        lines.append(f"- `{reason}`: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    fieldnames = [
        "source_candidate_id",
        "child_context",
        "decision",
        "case_ids",
        "accepted_guide_codes",
        "blocked_reasons",
        "domain_buckets",
        "root_causes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["audit_rows"]:
            writer.writerow({
                "source_candidate_id": row.get("source_candidate_id"),
                "child_context": row.get("child_context"),
                "decision": row.get("decision"),
                "case_ids": ";".join(row.get("case_ids") or []),
                "accepted_guide_codes": ";".join(row.get("accepted_guide_codes") or []),
                "blocked_reasons": ";".join(row.get("blocked_reasons") or []),
                "domain_buckets": json.dumps(row.get("domain_buckets") or {}, ensure_ascii=False, sort_keys=True),
                "root_causes": json.dumps(row.get("root_causes") or {}, ensure_ascii=False, sort_keys=True),
            })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--stage3-candidates", type=Path, default=DEFAULT_STAGE3_CANDIDATES)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_preview(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    report = {key: value for key, value in summary.items() if key != "audit_rows"}
    report["audit_rows"] = summary["audit_rows"]
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, summary)
    print("=== NO_TOP Guide Support Candidate Preview ===")
    print(f"input_no_top_rows: {summary['input_no_top_rows']}")
    print(f"audit_rows: {summary['audit_rows'] and len(summary['audit_rows'])}")
    print(f"support_candidate_rows: {summary['support_candidate_rows']}")
    print(f"covered_no_top_case_count: {summary['covered_no_top_case_count']}")
    print(f"distinct_child_contexts: {summary['distinct_child_contexts']}")
    print(f"distinct_guide_codes: {summary['distinct_guide_codes']}")
    print(f"wrote: {args.support_output}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    sys.exit(main())
