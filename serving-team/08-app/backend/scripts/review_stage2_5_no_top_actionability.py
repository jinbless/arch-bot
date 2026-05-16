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
    / "stage2_5_no_top_root_cause_no_forced_hotwork_gate1.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "pictures-json" / "reports"
DEFAULT_PREFIX = "stage2_5_no_top_actionability_no_forced_hotwork_gate1"


RUNTIME_REPAIR_ACTIONABILITIES = {
    "guide_usage_profile_repair_candidate",
    "situation_frame_support_repair_candidate",
    "serving_bridge_repair_candidate",
}
SOURCE_OR_TAXONOMY_REVIEW_ACTIONABILITIES = {
    "taxonomy_or_child_context_review",
    "stage3_she_sr_review_only",
    "corpus_gap_no_exact_photo_guide",
    "corpus_gap_or_taxonomy_review",
}
ACCEPTED_EMPTY_TOP_ACTIONABILITIES = {
    "safe_controlled_positive",
    "outside_kosha_photo_guide_scope",
    "followup_only_document_or_program",
    "followup_only_or_corpus_gap",
    "reject_existing_support_candidate",
}

OUT_OF_SCOPE_TERMS = (
    "아동",
    "어린이",
    "유치원",
    "회원",
    "고객",
    "반려동물",
    "펫샵",
    "개가",
    "동물",
    "클라이밍",
    "수영장",
    "스포츠",
    "피부 타입",
    "귓바퀴",
)
FOLLOWUP_ONLY_TERMS = (
    "체크리스트",
    "msds",
    "라벨",
    "라벨을 부착",
    "절차에 따라",
    "위험 이력",
    "방문 전",
    "허가서",
    "농도를 측정",
    "외부 감시원",
    "정기 점검",
)
SAFE_CONTROL_TERMS = (
    "loto",
    "전원 차단",
    "차단기를 내리고",
    "냉각",
    "확인한 뒤",
    "착용",
    "흄후드",
    "방호복",
    "이중 장갑",
    "잠금",
    "보관",
)


CASE_REVIEW: dict[str, dict[str, str]] = {
    "SYN-V10-0023": {
        "actionability": "serving_bridge_repair_candidate",
        "recommendation": "Keep as a narrow serving-bridge repair candidate. The scene has emergency-light/electrical-maintenance and ladder cues, but the standard-procedure lane still does not surface the matching Guide.",
        "reason": "Guide support and CI evidence exist, yet the top standard procedure remains empty. Fix by connecting trigger-backed support to the standard-procedure candidate lane, not by broadening electrical aliases.",
    },
    "SYN-V9-0181": {
        "actionability": "serving_bridge_repair_candidate",
        "recommendation": "Keep as a narrow serving-bridge repair candidate for port container-crane lifting. Do not relax the A-G-18 domain guard globally.",
        "reason": "A-G-18 checklist evidence is selected for the immediate action, but the WorkProcess/standard-procedure lane remains empty. This is a bridge/ranking issue, not a missing broad alias issue.",
    },
    "SYN-V3-0061": {
        "actionability": "corpus_gap_no_exact_photo_guide",
        "recommendation": "Keep NO_TOP until an exact cold-room entrapment/emergency-release Guide source exists. Do not promote freezer, refrigeration-system, or generic facility Guides from cold-room text alone.",
        "reason": "The observed hazard is a worker trapped inside a freezer room without an internal emergency-release button/sign. Current KOSHA matches focus on refrigeration systems, fire prevention, measurement, or cold PPE rather than this photo-top control.",
    },
    "SYN-V9-0128": {
        "actionability": "corpus_gap_or_taxonomy_review",
        "recommendation": "Keep NO_TOP for now. Do not map this waterworks ozone-leak measurement scene to UV-coating ozone or broad chemical Guides without an exact ozone-generator/ozone-room profile.",
        "reason": "The worker is measuring ozone with full PPE and the available support child context is from a different UV-coating process. This needs source/profile taxonomy review, not runtime guide forcing.",
    },
    "SYN-V9-0216": {
        "actionability": "safe_controlled_positive",
        "recommendation": "Keep NO_TOP and tighten the underground live-cable child context separately. Insulated gloves and breaker-off cues should not trigger underground-cable excavation support by themselves.",
        "reason": "The observation already includes breaker isolation and insulated gloves for fire receiver wiring. The current child-context hit is caused by generic electric safety terms, not by underground or excavation evidence.",
    },
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
    rows = list(data.get("rows") or [])
    if rows:
        return rows
    if data.get("records") is not None:
        raise SystemExit(
            "This actionability review expects a Stage 2~5 root-cause report with a 'rows' array. "
            "Run analyze_stage2_5_no_top_root_cause.py first, then pass its JSON here."
        )
    return []


def _row_text(row: dict[str, Any]) -> str:
    values = [
        row.get("industry_context") or "",
        row.get("work_context") or "",
        row.get("domain_bucket") or "",
        row.get("photo_description") or "",
        row.get("expected_primary_risk") or "",
        row.get("expected_corrective_direction") or "",
    ]
    return " ".join(str(value) for value in values if value).lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def _review_group(actionability: str) -> str:
    if actionability in RUNTIME_REPAIR_ACTIONABILITIES:
        return "runtime_repair_candidate"
    if actionability in SOURCE_OR_TAXONOMY_REVIEW_ACTIONABILITIES:
        return "source_or_taxonomy_review"
    if actionability in ACCEPTED_EMPTY_TOP_ACTIONABILITIES:
        return "accepted_empty_top"
    return "manual_review"


def _auto_review(row: dict[str, Any]) -> dict[str, str]:
    root_cause = str(row.get("primary_root_cause") or "")
    repair_lane = str(row.get("repair_lane") or "")
    domain_bucket = str(row.get("domain_bucket") or "")
    frame_policy = str(row.get("frame_match_policy") or "")
    text = _row_text(row)
    safe_cues = row.get("frame_safe_cues") or []

    if root_cause == "synthetic_fixture_or_safe_controlled_positive" or frame_policy == "status_safe":
        return {
            "actionability": "safe_controlled_positive",
            "recommendation": "Keep NO_TOP unless a later product mode explicitly asks for follow-up management Guides.",
            "reason": "The scene already contains control/safe cues, so forcing a photo-top Guide would likely create noise.",
        }
    if _has_any(text, OUT_OF_SCOPE_TERMS):
        return {
            "actionability": "outside_kosha_photo_guide_scope",
            "recommendation": "Keep NO_TOP in the KOSHA photo-top lane. Revisit only if a public/customer/animal-safety taxonomy is added.",
            "reason": "The observed harm target or domain is not a clear occupational KOSHA Guide photo-top procedure case.",
        }
    if _has_any(text, FOLLOWUP_ONLY_TERMS) and safe_cues:
        return {
            "actionability": "followup_only_document_or_program",
            "recommendation": "Keep NO_TOP for the primary photo procedure; allow only explicit follow-up/management display later.",
            "reason": "The row is dominated by document, checklist, measurement, or already-controlled management context.",
        }
    if repair_lane == "guide_usage_profile":
        return {
            "actionability": "guide_usage_profile_repair_candidate",
            "recommendation": "Inspect whether an existing photo-actionable Guide profile needs required cues, negative boundaries, or primary WorkProcess ids.",
            "reason": "The root-cause audit found possible Guide profiles, but their context terms did not anchor a top procedure.",
        }
    if repair_lane == "situation_frame_support":
        return {
            "actionability": "situation_frame_support_repair_candidate",
            "recommendation": "Add or tighten support-only SituationFrame-to-Guide evidence if an exact Guide family exists; do not affect status/penalty.",
            "reason": "A child context exists, but accepted Guide support did not reach ranking.",
        }
    if repair_lane in {"stage3_she", "stage3_she_sr"}:
        return {
            "actionability": "stage3_she_sr_review_only",
            "recommendation": "Review SHE/SR support candidates conservatively. Use as Guide support only; do not approve runtime SHE or legal asserted links automatically.",
            "reason": "SHE/SR evidence is incomplete or indirect, so it is not a safe shortcut to a top Guide.",
        }
    if repair_lane in {"stage2_taxonomy", "situation_frame_taxonomy"}:
        if safe_cues or _has_any(text, SAFE_CONTROL_TERMS):
            return {
                "actionability": "corpus_gap_or_taxonomy_review",
                "recommendation": "Keep NO_TOP now. If repeated in real traffic, split the child context and check whether an exact source Guide exists.",
                "reason": "The case has broad taxonomy/context collapse, but the scene also contains controls or lacks a specific photo-actionable Guide anchor.",
            }
        return {
            "actionability": "taxonomy_or_child_context_review",
            "recommendation": "Split the broad parent context into a child context first, then decide whether a corpus Guide actually covers it.",
            "reason": "The current representation is too broad to choose a Guide without risking wrong substitution.",
        }
    if domain_bucket in {"service_healthcare_people_gap", "burn_heat_profile_gap"}:
        return {
            "actionability": "corpus_gap_no_exact_photo_guide",
            "recommendation": "Keep NO_TOP unless a precise occupational source Guide is added or an existing Guide profile is proven by evidence.",
            "reason": "The domain often describes customer/user/service micro-hazards where the KOSHA Guide corpus may simply not contain a photo-top procedure.",
        }
    return {
        "actionability": "manual_review_required",
        "recommendation": "Review manually before adding runtime support.",
        "reason": "No confident structural actionability decision was available from current root-cause fields.",
    }


def _review_row(row: dict[str, Any]) -> dict[str, Any]:
    auto_review = _auto_review(row)
    review = CASE_REVIEW.get(str(row.get("case_id"))) or auto_review
    actionability = review["actionability"]
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
        "actionability": actionability,
        "actionability_group": _review_group(actionability),
        "auto_actionability": auto_review["actionability"],
        "recommended_next_action": review["recommendation"],
        "review_reason": review["reason"],
        "frame_match_policy": row.get("frame_match_policy"),
        "frame_child_contexts": row.get("frame_child_contexts") or [],
        "frame_parent_contexts": row.get("frame_parent_contexts") or [],
        "frame_safe_cues": row.get("frame_safe_cues") or [],
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
        "actionability_group",
        "recommended_next_action",
        "review_reason",
        "frame_match_policy",
        "frame_child_contexts",
        "frame_parent_contexts",
        "frame_safe_cues",
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
        f"- Accepted empty top: {summary['accepted_empty_top_count']}",
        f"- Source/taxonomy review: {summary['source_or_taxonomy_review_count']}",
        "",
        "This report intentionally does not treat every `NO_TOP` as a bug. If the photo scene has no precise KOSHA Guide in the current corpus, the correct behavior is to leave the top standard procedure empty instead of substituting a broad Guide.",
        "",
        "## Actionability Groups",
        "",
        "| Group | Count |",
        "|---|---:|",
    ]
    for key, count in summary["actionability_group_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend([
        "",
        "## Actionability Counts",
        "",
        "| Actionability | Count |",
        "|---|---:|",
    ])
    for key, count in summary["actionability_counts"].items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend([
        "",
        "## Recommendation",
        "",
        (
            "Do not reduce NO_TOP by broad aliases, generic SRs, or hot-work/chemical fallback Guides. "
            "Handle runtime repair candidates through Guide usage profiles, SituationFrame support, "
            "and WorkProcess evidence. Keep accepted empty-top cases empty unless an exact source Guide "
            "or a separate non-KOSHA/public-safety taxonomy is added."
        ),
        "",
        "## Rows",
        "",
        "| Case | Actionability | Reason | Next Action |",
        "|---|---|---|---|",
    ])
    for row in payload["rows"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['actionability']}` / `{row['actionability_group']}` | "
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
    group_counts = dict(Counter(row["actionability_group"] for row in rows).most_common())
    runtime_repair_count = sum(
        1
        for row in rows
        if row["actionability_group"] == "runtime_repair_candidate"
    )
    payload = {
        "summary": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_report": str(args.input),
            "total_no_top": len(rows),
            "actionability_counts": actionability_counts,
            "actionability_group_counts": group_counts,
            "runtime_repair_candidate_count": runtime_repair_count,
            "accepted_empty_top_count": group_counts.get("accepted_empty_top", 0),
            "source_or_taxonomy_review_count": group_counts.get("source_or_taxonomy_review", 0),
            "manual_review_count": group_counts.get("manual_review", 0),
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
