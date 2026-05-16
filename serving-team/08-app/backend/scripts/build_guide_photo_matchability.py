#!/usr/bin/env python3
"""Build photo-matchability policy for KOSHA Guide usage profiles.

The generated policy is a recommendation guard only.  It does not update
asserted mappings, SHE approval state, SR legal evidence, or penalty logic.
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
sys.path.insert(0, str(BACKEND_DIR))

from app.services.guide_photo_matchability import (  # noqa: E402
    FOLLOWUP_EXPLICIT_CONTEXT_ONLY,
    FOLLOWUP_NONE,
    PHOTO_ACTIONABLE,
    PHOTO_CONDITIONAL_FOLLOWUP,
    PHOTO_UNMATCHABLE,
    TOP_ALLOW,
    TOP_SUPPRESS,
    UNMATCHABLE_ROLES,
)


DEFAULT_PROFILES_PATH = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_ARTIFACT_PATH = BACKEND_DIR / "app" / "data" / "guide_photo_matchability.v1.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_BASELINE_REPORT = DEFAULT_REPORT_DIR / "pipeline_quality_v1_v10_situation_frame_support7.json"

FIELD_CONTROL_EVIDENCE_KEYS = (
    "observable_required_cues",
    "intended_workplaces",
    "intended_tasks",
    "required_context_terms",
    "visual_triggers",
    "feature_codes",
    "primary_work_process_ids",
)
GENERIC_EVIDENCE_FRAGMENTS = (
    "해당 guide",
    "해당 작업",
    "보건관리 문맥",
    "물질·작업",
    "확인되는 사업장",
)
FIELD_ACTION_TITLE_TERMS = (
    "안전보건작업",
    "안전작업",
    "작업 안전",
    "시공 및 작업",
    "응급대응",
    "누출사고",
    "경고표지",
)
METHOD_TITLE_TERMS = (
    "작업환경측정",
    "측정·분석",
    "측정,분석",
    "측정ㆍ분석",
    "분석 기술지침",
    "분석기술지침",
    "시료채취",
    "검량선",
    "독성시험",
    "건강진단",
    "검진",
    "위험성평가",
    "예측기법",
    "평가기법",
    "계측관리",
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _as_terms(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def collect_evidence_terms(profile: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in FIELD_CONTROL_EVIDENCE_KEYS:
        terms.extend(_as_terms(profile.get(key)))
    boundary = profile.get("recommendation_boundary") or {}
    terms.extend(_as_terms(boundary.get("include_when")))
    filtered = []
    for term in _unique(terms):
        lowered = term.lower()
        if any(fragment in lowered for fragment in GENERIC_EVIDENCE_FRAGMENTS):
            continue
        filtered.append(term)
    return filtered[:24]


def apparent_field_control(profile: dict[str, Any], evidence_terms: list[str]) -> bool:
    title = str(profile.get("title") or "")
    if any(term in title for term in METHOD_TITLE_TERMS):
        return False
    if not profile.get("primary_work_process_ids"):
        return False
    return bool(evidence_terms and any(term in title for term in FIELD_ACTION_TITLE_TERMS))


def classify_profile(guide_code: str, profile: dict[str, Any]) -> dict[str, Any]:
    role = str(profile.get("procedure_role") or "field_control")
    evidence_terms = collect_evidence_terms(profile)

    if role in UNMATCHABLE_ROLES and apparent_field_control(profile, evidence_terms):
        matchability = PHOTO_ACTIONABLE
        reason = (
            f"{role} role overridden by explicit field-action title and WorkProcess evidence; "
            "treated as photo-actionable for top procedure ranking."
        )
    elif role == "management_program":
        matchability = PHOTO_CONDITIONAL_FOLLOWUP
        reason = "management_program Guide is a follow-up management/control document, not a photo-top field action."
    elif role in UNMATCHABLE_ROLES:
        matchability = PHOTO_UNMATCHABLE
        reason = f"{role} Guide needs explicit document, measurement, test, health, or method context."
    elif role == "field_control" and not evidence_terms:
        matchability = PHOTO_CONDITIONAL_FOLLOWUP
        reason = "field_control Guide lacks observable cue, task, workplace, feature, or WorkProcess evidence."
    else:
        matchability = PHOTO_ACTIONABLE
        reason = "field_control Guide has observable field/task evidence usable for photo-top procedure ranking."

    return {
        "guide_code": guide_code,
        "photo_matchability": matchability,
        "top_procedure_policy": TOP_ALLOW if matchability == PHOTO_ACTIONABLE else TOP_SUPPRESS,
        "followup_policy": FOLLOWUP_NONE if matchability == PHOTO_ACTIONABLE else FOLLOWUP_EXPLICIT_CONTEXT_ONLY,
        "evidence_terms": evidence_terms[:12],
        "classification_reason": reason,
        "review_status": "auto_classified",
        "procedure_role": role,
        "profile_level": profile.get("profile_level") or "general",
        "domain_family": profile.get("domain_family"),
    }


def load_baseline_top_counts(path: Path, classifications: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not path.exists():
        return {
            "baseline_report": str(path),
            "available": False,
            "top_counts_by_matchability": {},
            "top_guides": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records") or []
    by_matchability: Counter[str] = Counter()
    top_guides: Counter[str] = Counter()
    unmatchable_guides: Counter[str] = Counter()
    conditional_guides: Counter[str] = Counter()
    for record in records:
        top = ((record.get("stage5_guide_ci") or {}).get("top_procedure") or {})
        guide_code = top.get("guide_code") or "NO_TOP"
        top_guides[guide_code] += 1
        if guide_code == "NO_TOP":
            by_matchability["NO_TOP"] += 1
            continue
        matchability = (classifications.get(guide_code) or {}).get("photo_matchability") or "unknown"
        by_matchability[matchability] += 1
        if matchability == PHOTO_UNMATCHABLE:
            unmatchable_guides[guide_code] += 1
        elif matchability == PHOTO_CONDITIONAL_FOLLOWUP:
            conditional_guides[guide_code] += 1
    return {
        "baseline_report": str(path),
        "available": True,
        "total_records": len(records),
        "top_counts_by_matchability": dict(sorted(by_matchability.items())),
        "top_unmatchable_guides": dict(unmatchable_guides.most_common(40)),
        "top_conditional_guides": dict(conditional_guides.most_common(40)),
        "top_guides": dict(top_guides.most_common(40)),
    }


def write_csv(path: Path, classifications: dict[str, dict[str, Any]], profiles: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "guide_code",
                "title",
                "procedure_role",
                "profile_level",
                "photo_matchability",
                "top_procedure_policy",
                "followup_policy",
                "evidence_terms",
                "classification_reason",
                "review_status",
            ],
        )
        writer.writeheader()
        for guide_code, item in sorted(classifications.items()):
            profile = profiles.get(guide_code) or {}
            writer.writerow({
                "guide_code": guide_code,
                "title": profile.get("title"),
                "procedure_role": item["procedure_role"],
                "profile_level": item["profile_level"],
                "photo_matchability": item["photo_matchability"],
                "top_procedure_policy": item["top_procedure_policy"],
                "followup_policy": item["followup_policy"],
                "evidence_terms": " | ".join(item["evidence_terms"]),
                "classification_reason": item["classification_reason"],
                "review_status": item["review_status"],
            })


def write_markdown(path: Path, audit: dict[str, Any]) -> None:
    counts = audit["classification_counts"]
    role_counts = audit["classification_by_role"]
    baseline = audit["baseline_top_exposure"]
    lines = [
        "# Guide Photo Matchability Audit v1",
        "",
        f"- generated_at: `{audit['generated_at']}`",
        f"- guide_count: `{audit['guide_count']}`",
        f"- artifact: `{audit['artifact_path']}`",
        "",
        "## Classification Counts",
        "",
        "```json",
        json.dumps(counts, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Classification By Role",
        "",
        "```json",
        json.dumps(role_counts, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Baseline Top Exposure",
        "",
        "```json",
        json.dumps({
            "baseline_report": baseline.get("baseline_report"),
            "top_counts_by_matchability": baseline.get("top_counts_by_matchability"),
            "top_unmatchable_guides": baseline.get("top_unmatchable_guides"),
            "top_conditional_guides": baseline.get("top_conditional_guides"),
        }, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Manual Review Samples",
        "",
    ]
    for item in audit["manual_review_samples"][:60]:
        lines.append(
            f"- `{item['guide_code']}` {item['photo_matchability']} / "
            f"{item['procedure_role']} / {item.get('title') or ''}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, Path]:
    data = json.loads(args.profiles_path.read_text(encoding="utf-8"))
    profiles = data.get("profiles") or {}
    classifications = {
        guide_code: classify_profile(guide_code, profile)
        for guide_code, profile in profiles.items()
    }
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    counts = Counter(item["photo_matchability"] for item in classifications.values())
    by_role: dict[str, dict[str, int]] = defaultdict(dict)
    for role, role_count in Counter(item["procedure_role"] for item in classifications.values()).items():
        role_items = [
            item for item in classifications.values()
            if item["procedure_role"] == role
        ]
        by_role[role] = dict(sorted(Counter(item["photo_matchability"] for item in role_items).items()))
        by_role[role]["total"] = role_count

    artifact = {
        "generated_at": generated_at,
        "schema_version": "guide_photo_matchability.v1",
        "source": str(args.profiles_path),
        "guide_count": len(classifications),
        "policy": {
            "scope": "photo-based top standard procedure guard only",
            "photo_actionable": "Guide may appear as top standard procedure for photo-based analysis.",
            "photo_conditional_followup": "Guide cannot be top; may appear as one lower follow-up when explicit role context is present.",
            "photo_unmatchable": "Guide cannot be photo-top; explicit document/measurement/test/health/method context is required for any follow-up use.",
            "status_penalty_she_sr_impact": "none",
        },
        "classification_counts": dict(sorted(counts.items())),
        "classification_by_role": dict(sorted(by_role.items())),
        "profiles": classifications,
    }
    args.artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.update_profiles:
        data["photo_matchability_policy"] = {
            "generated_at": generated_at,
            "artifact": str(args.artifact_path),
            "schema_version": "guide_photo_matchability.v1",
        }
        data["photo_matchability_counts"] = dict(sorted(counts.items()))
        for guide_code, item in classifications.items():
            profile = profiles[guide_code]
            for key in (
                "photo_matchability",
                "top_procedure_policy",
                "followup_policy",
                "evidence_terms",
                "classification_reason",
                "review_status",
            ):
                profile[key] = item[key]
        args.profiles_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    audit = {
        "generated_at": generated_at,
        "guide_count": len(classifications),
        "artifact_path": str(args.artifact_path),
        "profiles_path": str(args.profiles_path),
        "classification_counts": dict(sorted(counts.items())),
        "classification_by_role": dict(sorted(by_role.items())),
        "baseline_top_exposure": load_baseline_top_counts(args.baseline_report, classifications),
        "manual_review_samples": [
            {
                **item,
                "title": (profiles.get(guide_code) or {}).get("title"),
            }
            for guide_code, item in sorted(classifications.items())
            if item["photo_matchability"] != PHOTO_ACTIONABLE
        ],
    }
    json_path = args.report_dir / "guide_photo_matchability_audit_v1.json"
    md_path = args.report_dir / "guide_photo_matchability_audit_v1.md"
    csv_path = args.report_dir / "guide_photo_matchability_audit_v1.csv"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(md_path, audit)
    write_csv(csv_path, classifications, profiles)
    return {"artifact": args.artifact_path, "json": json_path, "md": md_path, "csv": csv_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles-path", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--artifact-path", type=Path, default=DEFAULT_ARTIFACT_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--baseline-report", type=Path, default=DEFAULT_BASELINE_REPORT)
    parser.add_argument(
        "--no-update-profiles",
        action="store_false",
        dest="update_profiles",
        help="Only write the standalone artifact/audit, leaving guide_domain_profiles.json unchanged.",
    )
    parser.set_defaults(update_profiles=True)
    return parser.parse_args()


def main() -> None:
    paths = build(parse_args())
    print(json.dumps({key: str(value) for key, value in paths.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
