#!/usr/bin/env python3
"""Review whether remaining NO_TOP cases are actually runtime repair targets.

This is a manual audit helper for the small tail of Stage 2~5 NO_TOP cases.
It does not change runtime behavior.  The point is to avoid treating public
safety, document-only, safe-controlled, or wrong-guide support rows as if they
should all become photo-based top standard procedures.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    PROJECT_ROOT
    / "pictures-json"
    / "reports"
    / "stage2_5_no_top_root_cause_ci_wp_relevance7_profile_tight1.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PREFIX = "stage2_5_no_top_actionability_ci_wp_relevance7_profile_tight1"


CASE_REVIEW: dict[str, dict[str, str]] = {
    "SYN-V10-0122": {
        "actionability": "followup_only_document_or_program",
        "recommendation": "Do not broaden runtime status. H-203 is a document/manual guide and should remain follow-up only unless manual/procedure context is explicit.",
        "reason": "Mental-health home visit violence risk is real, but the available KOSHA match is a customer-response health manual/document guide, not a photo-top field procedure.",
    },
    "SYN-V10-0061": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Keep NO_TOP rather than falling back to care-facility burn Guides. The observation already includes power isolation and PPE.",
        "reason": "Electric soup-kettle cleaning is described as controlled before cleaning; the removed G-28 match was a care-facility bath/stair Guide overreach.",
    },
    "SYN-V10-0092": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Keep NO_TOP unless a specific kitchen oil-changing Guide exists. Do not restore generic care-facility burn matching.",
        "reason": "The fryer-oil replacement is described with heat gloves, apron, and temperature confirmation after cooling.",
    },
    "SYN-V10-0246": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Keep NO_TOP. Do not map cooled sterilizer cleaning to smelting/high-heat health Guides.",
        "reason": "Power disconnection, cooling confirmation, and heat gloves are already present.",
    },
    "SYN-V10-0286": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Keep NO_TOP. Do not map oxygen-generator filter replacement to smelting/high-heat or generic electric Guides.",
        "reason": "Power isolation, cooling, and gloves are explicitly present.",
    },
    "SYN-V10-0273": {
        "actionability": "followup_only_or_corpus_gap",
        "recommendation": "Do not map generic MATERIAL_HANDLING to cargo/port guides. Keep as ergonomic/patient-handling corpus gap unless an exact patient-transfer work guide is added.",
        "reason": "The case is safe two-person patient repositioning. Existing G-91 is hoist/sling-specific, while E-G guides are management/ergonomic programs rather than direct photo hazards.",
    },
    "SYN-V10-0283": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Do not force a top procedure. Treat as safe-control/follow-up evidence; avoid broad chemical guide promotion.",
        "reason": "The observation says cytotoxic handling procedures and PPE are already being followed.",
    },
    "SYN-V10-0288": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Do not force a top procedure from MACHINE/ELECTRIC broad features. Consider a future medical-electrical follow-up only when unsafe cue is present.",
        "reason": "The observation says power is disconnected and inspection is being performed with gloves; current top guide would be broad electrical/machine overreach.",
    },
    "SYN-V10-0302": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Do not force a top procedure. H-138/lab guides require specimen/biological contamination context, not generic cytotoxic PPE compliance.",
        "reason": "The observation states PPE and biological safety cabinet controls are in place.",
    },
    "SYN-V6-0163": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP or route to a non-KOSHA/public-facility safety taxonomy later.",
        "reason": "Pool suction/drain-cover hazard is mainly public facility/user safety, not a current KOSHA Guide photo-top field procedure.",
    },
    "SYN-V6-0167": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP. Avoid using generic FALL/construction guides for a sports climbing-wall user hazard.",
        "reason": "Loose climbing hold is sports-facility user safety and does not have a precise KOSHA Guide boundary in the current corpus.",
    },
    "SYN-V6-0172": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP. Do not convert generic collision into workplace traffic or machinery guide recommendations.",
        "reason": "Exercise-class participant collision is a customer/user safety scenario, not an occupational Guide top-procedure case.",
    },
    "SYN-V6-0243": {
        "actionability": "corpus_gap_no_exact_photo_guide",
        "recommendation": "Do not use mercury analysis/measurement guides as photo-top procedures. Add a dental-amalgam/mercury handling Guide only if a true source exists.",
        "reason": "The risk is plausible occupational mercury exposure, but current matches are measurement/analysis or broad chemical guides, not dental-amalgam field controls.",
    },
    "SYN-V3-0075": {
        "actionability": "corpus_gap_no_exact_photo_guide",
        "recommendation": "Keep NO_TOP unless a food-service hot-meal carrying/collision Guide is added. Do not restore smelting heat Guide matching.",
        "reason": "The risk is hot-food service collision, while the removed H-192 match was a smelting worker health Guide based on broad heat features.",
    },
    "SYN-V4-0029": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP or route to a personal-service/customer-safety taxonomy later.",
        "reason": "Hair iron near a customer's ear is primarily customer service injury risk and has no exact KOSHA photo-top Guide in the current corpus.",
    },
    "SYN-V5-0043": {
        "actionability": "corpus_gap_no_exact_photo_guide",
        "recommendation": "Keep NO_TOP unless a car-wash hot-surface Guide is added. Do not use smelting heat controls.",
        "reason": "Hot vehicle hood waxing is a plausible service-work heat contact case, but the current corpus lacks a precise field-control Guide.",
    },
    "SYN-V5-0076": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP or route to pet-service/customer-animal safety taxonomy later.",
        "reason": "Overheated cage dryer primarily describes animal welfare/customer-service risk; generic high-heat worker Guide matching is not reliable.",
    },
    "SYN-V6-0307": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP or route to childcare/public safety taxonomy later.",
        "reason": "Worn playground swing chain is child/user safety, not an occupational KOSHA Guide field procedure.",
    },
    "SYN-V6-0311": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP. Do not promote broad chemical/PPE guides from child exposure to residual cleaner.",
        "reason": "Residual cleaner exposure to children is childcare/public hygiene safety; worker chemical exposure is not the explicit observed target.",
    },
    "SYN-V6-0323": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP or route to childcare/public safety taxonomy later.",
        "reason": "Drawer/furniture tip-over is child/user safety and has no exact KOSHA Guide photo-top procedure in the current corpus.",
    },
    "SYN-V6-0327": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP. Do not map unauthorized childcare medication storage to occupational health guides.",
        "reason": "Medication authorization/storage is childcare/health administration, not KOSHA workplace photo control.",
    },
    "SYN-V6-0328": {
        "actionability": "outside_kosha_photo_guide_scope",
        "recommendation": "Keep NO_TOP. Do not map expired EpiPen management to occupational field-control guides.",
        "reason": "Expired emergency medication is childcare/health administration rather than a KOSHA photo-top field procedure.",
    },
    "SYN-V7-0081": {
        "actionability": "reject_existing_support_candidate",
        "recommendation": "Reject or leave blocked the C-C-16 support candidate. Do not use eyewash/shower Guide for food CIP residue.",
        "reason": "The case is food contamination/consumer health from CIP caustic residue. C-C-16 is an eyewash/emergency-shower Guide, so the previous support row is semantically wrong.",
    },
    "SYN-V7-0307": {
        "actionability": "reject_existing_support_candidate",
        "recommendation": "Reject or leave blocked the G-131 support candidate. Do not use municipal-waste collection Guide for automotive coolant/oil disposal.",
        "reason": "The case is environmental/waste disposal during engine overhaul. G-131 is municipal waste collection/processing and does not match automotive waste-fluid handling.",
    },
}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("rows") or [])


def _review_row(row: dict[str, Any]) -> dict[str, Any]:
    review = CASE_REVIEW.get(str(row.get("case_id"))) or {
        "actionability": "manual_review_required",
        "recommendation": "Review manually before adding runtime support.",
        "reason": "No curated actionability decision has been recorded for this case.",
    }
    return {
        "case_id": row.get("case_id"),
        "version": row.get("version"),
        "line_no": row.get("line_no"),
        "case_type": row.get("case_type"),
        "industry_context": row.get("industry_context"),
        "work_context": row.get("work_context"),
        "domain_bucket": row.get("domain_bucket"),
        "primary_root_cause": row.get("primary_root_cause"),
        "repair_lane": row.get("repair_lane"),
        "actionability": review["actionability"],
        "recommended_next_action": review["recommendation"],
        "review_reason": review["reason"],
        "support_hit_count": row.get("support_hit_count"),
        "support_guide_codes": [
            guide_code
            for support in (row.get("support_hits") or [])
            for guide_code in (support.get("guide_codes") or [])
        ],
        "profile_top_guide_codes": [
            candidate.get("guide_code")
            for candidate in (row.get("profile_top_candidates") or [])
        ],
        "feature_codes": row.get("feature_codes") or [],
        "photo_description": row.get("photo_description"),
        "expected_primary_risk": row.get("expected_primary_risk"),
        "expected_corrective_direction": row.get("expected_corrective_direction"),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "case_id",
        "version",
        "line_no",
        "industry_context",
        "work_context",
        "primary_root_cause",
        "repair_lane",
        "actionability",
        "recommended_next_action",
        "review_reason",
        "support_guide_codes",
        "profile_top_guide_codes",
        "feature_codes",
        "photo_description",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: ";".join(row[key]) if isinstance(row.get(key), list) else row.get(key)
                for key in fieldnames
            })


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Stage 2~5 NO_TOP Actionability Review",
        "",
        f"- Source report: `{summary['source_report']}`",
        f"- Total NO_TOP reviewed: {summary['total_no_top']}",
        f"- Runtime repair candidates: {summary['runtime_repair_candidate_count']}",
        "",
        "## Actionability Counts",
        "",
        "| Actionability | Count |",
        "|---|---:|",
    ]
    for key, count in summary["actionability_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend([
        "",
        "## Recommendation",
        "",
        (
            "No remaining case should be blindly promoted by broad aliases or generic Guide support. "
            "The next runtime work should move to CI/WorkProcess relevance and only revisit these "
            "NO_TOP cases when an exact source Guide or a non-KOSHA/public-safety taxonomy is added."
        ),
        "",
        "## Rows",
        "",
        "| Case | Actionability | Reason | Next Action |",
        "|---|---|---|---|",
    ])
    for row in payload["rows"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['actionability']}` | "
            f"{row['review_reason']} | {row['recommended_next_action']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    args = parser.parse_args()

    rows = [_review_row(row) for row in _load_rows(args.input)]
    actionability_counts = dict(Counter(row["actionability"] for row in rows).most_common())
    runtime_repair_count = sum(
        1
        for row in rows
        if row["actionability"] in {"runtime_repair_candidate", "manual_review_required"}
    )
    payload = {
        "summary": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_report": str(args.input),
            "total_no_top": len(rows),
            "actionability_counts": actionability_counts,
            "runtime_repair_candidate_count": runtime_repair_count,
            "status_penalty_she_sr_impact": "none",
            "runtime_behavior_changed": False,
        },
        "rows": rows,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.prefix}.json"
    csv_path = args.output_dir / f"{args.prefix}.csv"
    md_path = args.output_dir / f"{args.prefix}.md"
    _write_json(json_path, payload)
    _write_csv(csv_path, rows)
    _write_md(md_path, payload)
    print(json.dumps({
        "summary": payload["summary"],
        "outputs": {
            "json": str(json_path),
            "csv": str(csv_path),
            "md": str(md_path),
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
