#!/usr/bin/env python3
"""Validate the generated serving ontology snapshot with rdflib/SPARQL."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF


ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = Path(__file__).resolve().parents[1]

POLICY_TTL_PATH = ONTOLOGY_DIR / "serving-policy.ttl"
SNAPSHOT_TTL_PATH = ONTOLOGY_DIR / "serving-snapshot-context_safe_gate1.ttl"
BASE_INSTANCES_PATH = ONTOLOGY_DIR / "kosha-instances.ttl"

REPORT_JSON_PATH = ONTOLOGY_DIR / "serving-validation-report-context_safe_gate1.json"
REPORT_MD_PATH = ONTOLOGY_DIR / "serving-validation-report-context_safe_gate1.md"
REPORT_CSV_PATH = ONTOLOGY_DIR / "serving-validation-report-context_safe_gate1.csv"

GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
APP = Namespace("https://cashtoss.info/ontology/app#")

BASELINE_ID = "context_safe_gate1"
GENERIC_REQUIRED_TERMS = {
    "화학물질",
    "화재",
    "폭발",
    "고소 작업",
    "낙하물",
    "피부",
    "흡입",
    "용제",
    "construction",
    "chemical_process",
    "laboratory",
    "작업",
    "안전",
    "관리",
}
PHOTO_UNMATCHABLE_ROLES = {
    "measurement_analysis",
    "test_protocol",
    "health_screening",
    "risk_method",
    "document_reference",
}
ROLE_OVERRIDE_REASON_FRAGMENT = "role overridden by explicit field-action title and WorkProcess evidence"


def local_name(uri: Any) -> str:
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[-1]
    return text.rsplit("/", 1)[-1]


def lit_values(g: Graph, subject, predicate) -> list[str]:
    return [str(v) for v in g.objects(subject, predicate)]


def one(g: Graph, subject, predicate) -> str | None:
    values = lit_values(g, subject, predicate)
    return values[0] if values else None


def add_issue(
    issues: list[dict[str, Any]],
    severity: str,
    rule_id: str,
    subject: str,
    message: str,
    category: str,
    **extra: Any,
) -> None:
    row = {
        "severity": severity,
        "rule_id": rule_id,
        "subject": subject,
        "message": message,
        "category": category,
    }
    row.update(extra)
    issues.append(row)


def load_graphs() -> tuple[Graph, Graph]:
    g = Graph()
    g.parse(POLICY_TTL_PATH, format="turtle")
    g.parse(SNAPSHOT_TTL_PATH, format="turtle")

    base = Graph()
    if BASE_INSTANCES_PATH.exists():
        base.parse(BASE_INSTANCES_PATH, format="turtle")
    return g, base


def validate_profiles(g: Graph, base: Graph, issues: list[dict[str, Any]]) -> None:
    for profile in sorted(set(g.subjects(RDF.type, GUIDE.GuideUsageProfile)), key=str):
        guide_values = list(g.objects(profile, GUIDE.profileOfGuide))
        baseline_values = lit_values(g, profile, APP.baselineId)
        subject = local_name(profile)

        if len(guide_values) != 1:
            add_issue(
                issues,
                "hard",
                "profile_exactly_one_guide",
                subject,
                f"GuideUsageProfile has {len(guide_values)} profileOfGuide links.",
                "structure_issue",
            )
            continue
        guide = guide_values[0]

        if baseline_values != [BASELINE_ID]:
            add_issue(
                issues,
                "hard",
                "profile_baseline_id",
                subject,
                f"GuideUsageProfile baselineId is {baseline_values!r}.",
                "structure_issue",
                guide_code=local_name(guide),
            )

        photo_matchability = one(g, profile, GUIDE.photoMatchability)
        top_policy = one(g, profile, GUIDE.topProcedurePolicy)
        procedure_role = one(g, profile, GUIDE.procedureRole)
        classification_reason = one(g, profile, GUIDE.classificationReason) or ""
        profile_level = one(g, profile, GUIDE.profileLevel)
        required_terms = set(lit_values(g, profile, GUIDE.requiredContextTerm))
        negative_terms = set(lit_values(g, profile, GUIDE.negativeBoundaryTerm))
        observable_cues = set(lit_values(g, profile, GUIDE.observableRequiredCue))

        if photo_matchability == "photo_unmatchable" and top_policy != "suppress_photo_top":
            add_issue(
                issues,
                "hard",
                "photo_unmatchable_policy",
                subject,
                "photo_unmatchable profile does not use suppress_photo_top.",
                "data_issue",
                guide_code=local_name(guide),
            )

        if procedure_role == "field_control" and not observable_cues:
            add_issue(
                issues,
                "warning",
                "field_control_without_observable_cue",
                subject,
                "field_control Guide has no observableRequiredCue.",
                "data_issue",
                guide_code=local_name(guide),
            )

        if profile_level == "exclusive" and required_terms and required_terms <= GENERIC_REQUIRED_TERMS:
            add_issue(
                issues,
                "warning",
                "exclusive_required_terms_too_generic",
                subject,
                "exclusive Guide only has generic required context terms.",
                "data_issue",
                guide_code=local_name(guide),
                required_terms=sorted(required_terms),
            )

        has_accepted_role_override = (
            photo_matchability == "photo_actionable"
            and procedure_role in PHOTO_UNMATCHABLE_ROLES
            and ROLE_OVERRIDE_REASON_FRAGMENT in classification_reason
            and bool(observable_cues)
        )
        if (
            photo_matchability == "photo_actionable"
            and procedure_role in PHOTO_UNMATCHABLE_ROLES
            and not has_accepted_role_override
        ):
            add_issue(
                issues,
                "warning",
                "photo_actionable_role_conflict",
                subject,
                f"photo_actionable Guide has normally non-photo role {procedure_role}.",
                "data_issue",
                guide_code=local_name(guide),
            )

        overlap = sorted(required_terms & negative_terms)
        if overlap:
            add_issue(
                issues,
                "warning",
                "required_negative_term_overlap",
                subject,
                "requiredContextTerm overlaps negativeBoundaryTerm.",
                "data_issue",
                guide_code=local_name(guide),
                overlap=overlap[:20],
            )

        for wp in g.objects(profile, GUIDE.primaryWorkProcess):
            owners = set(base.subjects(GUIDE.hasWorkProcess, wp))
            if guide in owners:
                continue
            if owners:
                add_issue(
                    issues,
                    "hard",
                    "primary_workprocess_wrong_guide",
                    local_name(wp),
                    "primaryWorkProcess belongs to a different Guide in the base TTL.",
                    "data_issue",
                    guide_code=local_name(guide),
                    observed_owner=[local_name(owner) for owner in sorted(owners, key=str)],
                )
            else:
                add_issue(
                    issues,
                    "warning",
                    "primary_workprocess_not_in_base_ttl",
                    local_name(wp),
                    "primaryWorkProcess is not present in the current base kosha-instances.ttl materialization.",
                    "data_issue",
                    guide_code=local_name(guide),
                )


def validate_candidates(g: Graph, issues: list[dict[str, Any]]) -> None:
    for candidate in sorted(set(g.subjects(RDF.type, APP.ServingCandidate)), key=str):
        status = one(g, candidate, APP.reviewStatus)
        serving_allowed = one(g, candidate, APP.servingAllowed) == "true"
        legal_asserted = one(g, candidate, APP.legalAsserted) == "true"
        if status in {"needs_review", "rejected"} and (serving_allowed or legal_asserted):
            add_issue(
                issues,
                "hard",
                "review_candidate_serving_or_legal",
                local_name(candidate),
                "needs_review/rejected candidate is serving-allowed or legal asserted.",
                "review_only",
                review_status=status,
            )


def validate_evaluation_cases(g: Graph, issues: list[dict[str, Any]]) -> None:
    repeated: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for case in sorted(set(g.subjects(RDF.type, APP.EvaluationCase)), key=str):
        subject = local_name(case)
        top_guides = list(g.objects(case, APP.topGuide))
        guide_code = local_name(top_guides[0]) if top_guides else None
        photo_unmatchable_top = one(g, case, APP.photoUnmatchableTop) == "true"
        broad_only_top = one(g, case, APP.broadSrOnlyTop) == "true"
        broad_attention = one(g, case, APP.broadSrAttention) == "true"
        guide_category = one(g, case, APP.guideCategory)

        if photo_unmatchable_top:
            add_issue(
                issues,
                "hard",
                "photo_unmatchable_top_guide",
                subject,
                "Evaluation case has a photo_unmatchable top Guide.",
                "algorithm_issue",
                guide_code=guide_code,
            )
        if broad_only_top:
            add_issue(
                issues,
                "hard",
                "broad_sr_only_top",
                subject,
                "Evaluation case has a broad-SR-only top Guide.",
                "algorithm_issue",
                guide_code=guide_code,
            )
        elif broad_attention:
            add_issue(
                issues,
                "warning",
                "broad_sr_overreach_attention",
                subject,
                "Evaluation case still carries broad_sr_overreach attention.",
                "algorithm_issue",
                guide_code=guide_code,
            )

        if guide_code and guide_category in {
            "missing_usage_profile",
            "workprocess_mismatch",
            "ci_no_action",
            "ci_guide_boundary_mismatch",
            "industry_boundary_gap",
        }:
            repeated[(guide_category, guide_code)][subject] += 1

    for (category, guide_code), cases in sorted(repeated.items()):
        if len(cases) >= 3:
            add_issue(
                issues,
                "warning",
                "repeated_evaluation_failure_by_guide",
                guide_code,
                f"{guide_code} appears in {len(cases)} evaluation cases for {category}.",
                "corpus_gap" if category == "missing_usage_profile" else "algorithm_issue",
                guide_code=guide_code,
                failure_queue=category,
                case_count=len(cases),
                sample_cases=list(cases)[:10],
            )


def summarize(g: Graph, issues: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts = Counter(issue["severity"] for issue in issues)
    category_counts = Counter(issue["category"] for issue in issues)
    rule_counts = Counter(issue["rule_id"] for issue in issues)
    profiles = set(g.subjects(RDF.type, GUIDE.GuideUsageProfile))
    photo_counts = Counter(one(g, p, GUIDE.photoMatchability) for p in profiles)
    accepted_role_override_count = sum(
        1
        for p in profiles
        if one(g, p, GUIDE.photoMatchability) == "photo_actionable"
        and one(g, p, GUIDE.procedureRole) in PHOTO_UNMATCHABLE_ROLES
        and ROLE_OVERRIDE_REASON_FRAGMENT in (one(g, p, GUIDE.classificationReason) or "")
        and bool(lit_values(g, p, GUIDE.observableRequiredCue))
    )
    broad_srs = [
        subject
        for subject in set(g.subjects(APP.servingRole, None))
        if one(g, subject, APP.servingRole) == "broad_secondary_only"
    ]
    eval_cases = set(g.subjects(RDF.type, APP.EvaluationCase))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baseline_id": BASELINE_ID,
        "profile_count": len(profiles),
        "photo_matchability_counts": dict(sorted(photo_counts.items())),
        "accepted_photo_actionable_role_override_count": accepted_role_override_count,
        "broad_sr_count": len(broad_srs),
        "evaluation_case_count": len(eval_cases),
        "hard_violation_count": severity_counts.get("hard", 0),
        "warning_count": severity_counts.get("warning", 0),
        "severity_counts": dict(severity_counts),
        "category_counts": dict(category_counts),
        "rule_counts": dict(rule_counts),
        "pass": severity_counts.get("hard", 0) == 0,
    }


def write_reports(summary: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    payload = {"summary": summary, "issues": issues}
    REPORT_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with REPORT_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "severity",
            "rule_id",
            "category",
            "subject",
            "guide_code",
            "message",
            "case_count",
            "failure_queue",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for issue in issues:
            writer.writerow({key: issue.get(key, "") for key in fieldnames})

    lines = [
        "# Serving Snapshot Validation Report",
        "",
        f"- baseline: `{summary['baseline_id']}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- result: `{'PASS' if summary['pass'] else 'FAIL'}`",
        f"- GuideUsageProfile: `{summary['profile_count']}`",
        f"- evaluation cases: `{summary['evaluation_case_count']}`",
        f"- broad SRs: `{summary['broad_sr_count']}`",
        f"- hard violations: `{summary['hard_violation_count']}`",
        f"- warnings: `{summary['warning_count']}`",
        f"- accepted photo-actionable role overrides: `{summary['accepted_photo_actionable_role_override_count']}`",
        "",
        "## Photo Matchability Counts",
        "",
    ]
    for key, value in summary["photo_matchability_counts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Rule Counts", ""])
    for key, value in sorted(summary["rule_counts"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Sample Issues", ""])
    for issue in issues[:80]:
        guide = f" / {issue.get('guide_code')}" if issue.get("guide_code") else ""
        lines.append(
            f"- `{issue['severity']}` `{issue['rule_id']}` `{issue['subject']}`{guide}: {issue['message']}"
        )
    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    g, base = load_graphs()
    issues: list[dict[str, Any]] = []
    validate_profiles(g, base, issues)
    validate_candidates(g, issues)
    validate_evaluation_cases(g, issues)
    summary = summarize(g, issues)
    write_reports(summary, issues)

    print(f"wrote: {REPORT_JSON_PATH}")
    print(f"wrote: {REPORT_MD_PATH}")
    print(f"wrote: {REPORT_CSV_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
