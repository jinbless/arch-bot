#!/usr/bin/env python3
"""Export OHS serving artifacts as a validation-only ontology snapshot.

The generated graph is intentionally separate from kosha-instances.ttl.  It is
used to find inconsistent Guide recommendation policy, not to drive runtime
recommendation scoring.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD


BASELINE_ID = "ci_cross_guide_broad_only_guard1"

ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_DIR = Path(__file__).resolve().parents[1]
OHS_DATA_DIR = ROOT / "OHS" / "backend" / "app" / "data"
REPORTS_DIR = ROOT / "data-team/05-enrichment/eval-data" / "reports"

GUIDE_PROFILES_PATH = OHS_DATA_DIR / "guide_domain_profiles.json"
PHOTO_MATCHABILITY_PATH = OHS_DATA_DIR / "guide_photo_matchability.v1.json"
BROAD_SR_POLICY_PATH = OHS_DATA_DIR / "broad_sr_policy.json"
SITUATION_TAXONOMY_PATH = OHS_DATA_DIR / "situation_context_taxonomy.v21.json"
GUIDE_SUPPORT_PATH = OHS_DATA_DIR / "guide_support_candidates.v21.jsonl"
PIPELINE_REPORT_PATH = REPORTS_DIR / "pipeline_quality_v1_v10_ci_cross_guide_broad_only_guard1_pg.json"
PG_GUIDE_USAGE_SYNC_REPORT_PATH = REPORTS_DIR / "pg_guide_usage_profiles_sync_ci_broad_sr_guard4.json"
CI_CANDIDATE_PROMOTION_REPORT_PATH = REPORTS_DIR / "ci_sr_candidate_promotion_ci_cross_guide_broad_only_guard1.json"

POLICY_TTL_PATH = ONTOLOGY_DIR / "serving-policy.ttl"
SNAPSHOT_TTL_PATH = ONTOLOGY_DIR / "serving-snapshot-ci_cross_guide_broad_only_guard1.ttl"
SHAPES_TTL_PATH = ONTOLOGY_DIR / "serving-validation-shapes.ttl"

CORE = Namespace("https://cashtoss.info/ontology#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
SR = Namespace("https://cashtoss.info/ontology/sr#")
APP = Namespace("https://cashtoss.info/ontology/app#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")
SH = Namespace("http://www.w3.org/ns/shacl#")
XSD_NS = Namespace("http://www.w3.org/2001/XMLSchema#")


def safe_id(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", "_", text)
    return quote(text, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


def bind(g: Graph) -> None:
    for prefix, ns in [
        ("core", CORE),
        ("guide", GUIDE),
        ("sr", SR),
        ("app", APP),
        ("prov", PROV),
        ("dct", DCT),
        ("sh", SH),
        ("owl", OWL),
        ("xsd", XSD_NS),
    ]:
        g.bind(prefix, ns)


def add_literal_list(g: Graph, subject, predicate, values: list[Any] | None) -> None:
    seen: set[str] = set()
    for raw in values or []:
        if raw is None:
            continue
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        g.add((subject, predicate, Literal(value, datatype=XSD.string)))


def add_optional_literal(g: Graph, subject, predicate, value: Any, datatype=XSD.string) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    g.add((subject, predicate, Literal(text, datatype=datatype)))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def build_policy_graph() -> Graph:
    g = Graph()
    bind(g)

    classes = {
        GUIDE.GuideUsageProfile: "Guide serving usage profile",
        APP.ServingSnapshot: "Generated validation snapshot for a serving baseline",
        APP.ServingCandidate: "Recommendation-support candidate used by serving artifacts",
        APP.EvaluationCase: "Synthetic evaluation case materialized for validation",
        APP.ValidationRun: "Serving ontology validation run",
    }
    for uri, label in classes.items():
        g.add((uri, RDF.type, OWL.Class))
        g.add((uri, RDFS.label, Literal(label, lang="en")))

    object_properties = {
        GUIDE.hasUsageProfile: (GUIDE.KoshaGuide, GUIDE.GuideUsageProfile),
        GUIDE.profileOfGuide: (GUIDE.GuideUsageProfile, GUIDE.KoshaGuide),
        GUIDE.primaryWorkProcess: (GUIDE.GuideUsageProfile, GUIDE.WorkProcess),
        APP.topGuide: (APP.EvaluationCase, GUIDE.KoshaGuide),
        APP.topChecklistItem: (APP.EvaluationCase, GUIDE.ChecklistItem),
        APP.servingCandidateFor: (APP.ServingCandidate, GUIDE.KoshaGuide),
        APP.candidateChecklistItem: (APP.ServingCandidate, GUIDE.ChecklistItem),
        APP.candidateRequirement: (APP.ServingCandidate, SR.SafetyRequirement),
    }
    for uri, (domain, range_) in object_properties.items():
        g.add((uri, RDF.type, OWL.ObjectProperty))
        g.add((uri, RDFS.domain, domain))
        g.add((uri, RDFS.range, range_))

    datatype_properties = [
        GUIDE.profileLevel,
        GUIDE.procedureRole,
        GUIDE.photoMatchability,
        GUIDE.topProcedurePolicy,
        GUIDE.followupPolicy,
        GUIDE.reviewStatus,
        GUIDE.usageSummary,
        GUIDE.requiredContextTerm,
        GUIDE.negativeBoundaryTerm,
        GUIDE.observableRequiredCue,
        APP.baselineId,
        APP.failureQueue,
        APP.guideCategory,
        APP.caseType,
        APP.syntheticVersion,
        APP.servingRole,
        APP.servingAllowed,
        APP.legalAsserted,
        APP.allowedRuntimeUse,
        APP.childContext,
        APP.parentContext,
        APP.triggerTerm,
        APP.broadSrAttention,
        APP.broadSrOnlyTop,
        APP.photoUnmatchableTop,
    ]
    for uri in datatype_properties:
        g.add((uri, RDF.type, OWL.DatatypeProperty))

    g.add((GUIDE.hasUsageProfile, RDFS.comment, Literal("Validation-only serving profile link. Runtime continues to read OHS JSON artifacts.", lang="en")))
    g.add((APP.ServingSnapshot, RDFS.comment, Literal("Generated from OHS serving artifacts and synthetic reports; do not hand-edit generated snapshots.", lang="en")))
    return g


def build_shapes_text() -> str:
    return """@prefix app: <https://cashtoss.info/ontology/app#> .
@prefix guide: <https://cashtoss.info/ontology/guide#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

app:GuideUsageProfileShape
    a sh:NodeShape ;
    sh:targetClass guide:GuideUsageProfile ;
    sh:property [
        sh:path guide:profileOfGuide ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:class guide:KoshaGuide ;
        sh:message "GuideUsageProfile must belong to exactly one KoshaGuide." ;
    ] ;
    sh:property [
        sh:path app:baselineId ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:message "GuideUsageProfile must carry the serving baseline id." ;
    ] .

app:PhotoUnmatchablePolicyShape
    a sh:NodeShape ;
    sh:targetClass guide:GuideUsageProfile ;
    sh:sparql [
        sh:message "photo_unmatchable profiles must use suppress_photo_top." ;
        sh:select \"\"\"
            PREFIX guide: <https://cashtoss.info/ontology/guide#>
            SELECT $this WHERE {
              $this guide:photoMatchability \"photo_unmatchable\" .
              FILTER NOT EXISTS { $this guide:topProcedurePolicy \"suppress_photo_top\" }
            }
        \"\"\" ;
    ] .

app:EvaluationPhotoTopShape
    a sh:NodeShape ;
    sh:targetClass app:EvaluationCase ;
    sh:sparql [
        sh:message "An evaluation top Guide must not be photo_unmatchable." ;
        sh:select \"\"\"
            PREFIX app: <https://cashtoss.info/ontology/app#>
            SELECT $this WHERE {
              $this app:photoUnmatchableTop true .
            }
        \"\"\" ;
    ] .

app:ServingCandidateShape
    a sh:NodeShape ;
    sh:targetClass app:ServingCandidate ;
    sh:sparql [
        sh:message "needs_review/rejected candidates must not be serving-allowed or legal asserted." ;
        sh:select \"\"\"
            PREFIX app: <https://cashtoss.info/ontology/app#>
            SELECT $this WHERE {
              $this app:reviewStatus ?status .
              FILTER(?status IN (\"needs_review\", \"rejected\"))
              {
                $this app:servingAllowed true .
              } UNION {
                $this app:legalAsserted true .
              }
            }
        \"\"\" ;
    ] .
"""


def add_artifacts(g: Graph, snapshot_uri) -> None:
    artifact_paths = [
        GUIDE_PROFILES_PATH,
        PHOTO_MATCHABILITY_PATH,
        BROAD_SR_POLICY_PATH,
        SITUATION_TAXONOMY_PATH,
        GUIDE_SUPPORT_PATH,
        PIPELINE_REPORT_PATH,
        PG_GUIDE_USAGE_SYNC_REPORT_PATH,
        CI_CANDIDATE_PROMOTION_REPORT_PATH,
    ]
    for path in artifact_paths:
        rel = path.relative_to(ROOT)
        artifact_uri = APP[f"Artifact_{safe_id(str(rel))}"]
        g.add((artifact_uri, RDF.type, PROV.Entity))
        g.add((artifact_uri, DCT.identifier, Literal(str(rel), datatype=XSD.string)))
        g.add((artifact_uri, DCT.title, Literal(path.name, datatype=XSD.string)))
        g.add((snapshot_uri, PROV.wasDerivedFrom, artifact_uri))


def add_candidates(g: Graph, profile_uri, guide_uri, guide_code: str, profile: dict[str, Any]) -> None:
    candidate_groups = [
        ("feature", "serving_feature_candidates"),
        ("sr_link", "serving_sr_link_candidates"),
        ("visual_trigger", "serving_visual_trigger_candidates"),
    ]
    allowed_statuses = {"candidate", "asserted"}
    for group_name, field in candidate_groups:
        for idx, candidate in enumerate(profile.get(field) or [], 1):
            node = APP[f"ServingCandidate_{safe_id(guide_code)}_{group_name}_{idx:03d}"]
            review_status = str(candidate.get("review_status") or "unknown")
            g.add((node, RDF.type, APP.ServingCandidate))
            g.add((node, APP.servingCandidateFor, guide_uri))
            g.add((node, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
            g.add((node, APP.candidateScope, Literal(group_name, datatype=XSD.string)))
            g.add((node, APP.reviewStatus, Literal(review_status, datatype=XSD.string)))
            g.add((node, APP.servingAllowed, Literal(review_status in allowed_statuses, datatype=XSD.boolean)))
            g.add((node, APP.legalAsserted, Literal(False, datatype=XSD.boolean)))
            add_optional_literal(g, node, APP.method, candidate.get("method"))
            add_optional_literal(g, node, APP.evidence, candidate.get("evidence"))
            add_optional_literal(g, node, APP.confidence, candidate.get("confidence"), XSD.decimal)
            if candidate.get("sr_id"):
                g.add((node, APP.candidateRequirement, SR[safe_id(candidate["sr_id"])]))
            if candidate.get("feature_code"):
                add_optional_literal(g, node, APP.featureCode, candidate.get("feature_code"))
            if candidate.get("trigger_text"):
                add_optional_literal(g, node, APP.triggerTerm, candidate.get("trigger_text"))
            g.add((profile_uri, APP.hasServingCandidate, node))


def add_guide_profiles(g: Graph, profiles: dict[str, Any]) -> None:
    for guide_code in sorted(profiles):
        profile = profiles[guide_code]
        guide_uri = GUIDE[safe_id(guide_code)]
        profile_uri = GUIDE[f"UsageProfile_{safe_id(guide_code)}_{BASELINE_ID}"]
        g.add((guide_uri, GUIDE.hasUsageProfile, profile_uri))
        g.add((profile_uri, RDF.type, GUIDE.GuideUsageProfile))
        g.add((profile_uri, GUIDE.profileOfGuide, guide_uri))
        g.add((profile_uri, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
        add_optional_literal(g, guide_uri, CORE.title, profile.get("title"))
        add_optional_literal(g, profile_uri, GUIDE.profileLevel, profile.get("profile_level"))
        add_optional_literal(g, profile_uri, GUIDE.procedureRole, profile.get("procedure_role"))
        add_optional_literal(g, profile_uri, GUIDE.photoMatchability, profile.get("photo_matchability"))
        add_optional_literal(g, profile_uri, GUIDE.topProcedurePolicy, profile.get("top_procedure_policy"))
        add_optional_literal(g, profile_uri, GUIDE.followupPolicy, profile.get("followup_policy"))
        add_optional_literal(g, profile_uri, GUIDE.reviewStatus, profile.get("usage_profile_review_status") or profile.get("review_status"))
        add_optional_literal(g, profile_uri, GUIDE.classificationReason, profile.get("classification_reason"))
        add_optional_literal(g, profile_uri, GUIDE.usageSummary, profile.get("usage_summary"))
        add_optional_literal(g, profile_uri, GUIDE.domainFamily, profile.get("domain_family"))
        add_literal_list(g, profile_uri, GUIDE.requiredContextTerm, profile.get("required_context_terms"))
        add_literal_list(g, profile_uri, GUIDE.negativeBoundaryTerm, profile.get("negative_boundaries") or profile.get("negative_context_terms"))
        add_literal_list(g, profile_uri, GUIDE.observableRequiredCue, profile.get("observable_required_cues"))
        add_literal_list(g, profile_uri, GUIDE.intendedWorkplace, profile.get("intended_workplaces"))
        add_literal_list(g, profile_uri, GUIDE.intendedTask, profile.get("intended_tasks"))
        add_literal_list(g, profile_uri, GUIDE.visualTriggerText, profile.get("visual_triggers"))
        for wp_id in profile.get("primary_work_process_ids") or []:
            if wp_id:
                g.add((profile_uri, GUIDE.primaryWorkProcess, GUIDE[safe_id(wp_id)]))
        add_candidates(g, profile_uri, guide_uri, guide_code, profile)


def add_broad_sr_policy(g: Graph, broad_policy: dict[str, Any]) -> None:
    policy_uri = APP[f"BroadSRPolicy_{safe_id(broad_policy.get('policy_version') or BASELINE_ID)}"]
    g.add((policy_uri, RDF.type, APP.BroadSRPolicy))
    g.add((policy_uri, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
    add_optional_literal(g, policy_uri, APP.policyVersion, broad_policy.get("policy_version"))
    add_optional_literal(g, policy_uri, APP.purpose, broad_policy.get("purpose"))
    for sr_id in broad_policy.get("broad_sr_ids") or []:
        sr_uri = SR[safe_id(sr_id)]
        g.add((sr_uri, APP.servingRole, Literal("broad_secondary_only", datatype=XSD.string)))
        g.add((sr_uri, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
        g.add((policy_uri, APP.hasBroadSafetyRequirement, sr_uri))


def add_support_candidates(g: Graph, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        support_id = row.get("support_id")
        if not support_id:
            continue
        node = APP[f"GuideSupportCandidate_{safe_id(support_id)}"]
        review_status = str(row.get("review_status") or "unknown")
        g.add((node, RDF.type, APP.ServingCandidate))
        g.add((node, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
        g.add((node, APP.allowedRuntimeUse, Literal(str(row.get("allowed_runtime_use") or ""), datatype=XSD.string)))
        g.add((node, APP.reviewStatus, Literal(review_status, datatype=XSD.string)))
        g.add((node, APP.servingAllowed, Literal(review_status in {"candidate", "asserted"}, datatype=XSD.boolean)))
        g.add((node, APP.legalAsserted, Literal(False, datatype=XSD.boolean)))
        add_optional_literal(g, node, APP.childContext, row.get("child_context"))
        add_literal_list(g, node, APP.parentContext, row.get("parent_contexts"))
        add_literal_list(g, node, APP.triggerTerm, row.get("trigger_terms"))
        add_optional_literal(g, node, APP.evidence, row.get("evidence"))
        add_optional_literal(g, node, APP.confidence, row.get("confidence"), XSD.decimal)
        for guide_code in row.get("guide_codes") or []:
            g.add((node, APP.servingCandidateFor, GUIDE[safe_id(guide_code)]))
        for sr_id in row.get("source_sr_ids") or []:
            g.add((node, APP.candidateRequirement, SR[safe_id(sr_id)]))


def add_ci_candidate_promotion_rows(g: Graph, rows: list[dict[str, Any]]) -> None:
    allowed_statuses = {"candidate", "asserted"}
    for row in rows:
        ci_id = row.get("entity_id")
        sr_id = row.get("sr_id")
        guide_code = row.get("guide_code")
        if not ci_id or not sr_id:
            continue
        node = APP[f"ServingCandidate_ci_candidate_review_v1_{safe_id(ci_id)}_{safe_id(sr_id)}"]
        review_status = str(row.get("current_review_status") or row.get("target_review_status") or "unknown")
        g.add((node, RDF.type, APP.ServingCandidate))
        g.add((node, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
        g.add((node, APP.candidateScope, Literal("ci_sr_link_candidate", datatype=XSD.string)))
        g.add((node, APP.reviewStatus, Literal(review_status, datatype=XSD.string)))
        g.add((node, APP.servingAllowed, Literal(review_status in allowed_statuses, datatype=XSD.boolean)))
        g.add((node, APP.legalAsserted, Literal(False, datatype=XSD.boolean)))
        add_optional_literal(g, node, APP.method, "ci_candidate_review_v1")
        add_optional_literal(g, node, APP.evidence, row.get("evidence"))
        add_optional_literal(g, node, APP.confidence, row.get("confidence"), XSD.decimal)
        add_optional_literal(g, node, APP.promotionDecision, row.get("decision"))
        add_optional_literal(g, node, APP.promotionReason, row.get("reason"))
        if guide_code:
            g.add((node, APP.servingCandidateFor, GUIDE[safe_id(guide_code)]))
        g.add((node, APP.candidateChecklistItem, GUIDE[safe_id(ci_id)]))
        g.add((node, APP.candidateRequirement, SR[safe_id(sr_id)]))


def top_guide_from_record(record: dict[str, Any]) -> str | None:
    stage5 = record.get("stage5_guide_ci") or {}
    top = stage5.get("top_procedure") or {}
    return top.get("guide_code") or top.get("procedure_id")


def top_ci_from_record(record: dict[str, Any]) -> str | None:
    ci = ((record.get("stage5_guide_ci") or {}).get("ci") or {}).get("top_action") or {}
    return ci.get("action_id")


def add_evaluation_cases(g: Graph, records: list[dict[str, Any]]) -> None:
    for record in records:
        case_id = record.get("case_id")
        if not case_id:
            continue
        node = APP[f"EvalCase_{safe_id(case_id)}"]
        stage5 = record.get("stage5_guide_ci") or {}
        guide_detail = stage5.get("guide_detail") or {}
        photo_policy = stage5.get("photo_policy") or {}
        top_policy = photo_policy.get("top") or {}
        queues = list(stage5.get("queues") or [])

        g.add((node, RDF.type, APP.EvaluationCase))
        g.add((node, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
        add_optional_literal(g, node, APP.syntheticVersion, record.get("version"))
        add_optional_literal(g, node, APP.caseType, record.get("case_type"))
        add_optional_literal(g, node, APP.industryContext, record.get("industry_context"))
        add_optional_literal(g, node, APP.workContext, record.get("work_context"))
        add_optional_literal(g, node, APP.guideCategory, stage5.get("guide_category"))
        add_optional_literal(g, node, APP.primaryFailureStage, record.get("primary_failure_stage"))
        add_literal_list(g, node, APP.failureQueue, queues)

        guide_code = top_guide_from_record(record)
        if guide_code:
            g.add((node, APP.topGuide, GUIDE[safe_id(guide_code)]))
        ci_id = top_ci_from_record(record)
        if ci_id:
            g.add((node, APP.topChecklistItem, GUIDE[safe_id(ci_id)]))

        g.add((node, APP.photoUnmatchableTop, Literal(bool(photo_policy.get("photo_unmatchable_top")), datatype=XSD.boolean)))
        g.add((node, APP.broadSrAttention, Literal("broad_sr_overreach" in queues, datatype=XSD.boolean)))
        broad_only = (
            "broad_sr_overreach" in queues
            and not guide_detail.get("term_hits")
            and not guide_detail.get("visual_hits")
            and not guide_detail.get("feature_hits")
        )
        g.add((node, APP.broadSrOnlyTop, Literal(bool(broad_only), datatype=XSD.boolean)))
        add_optional_literal(g, node, GUIDE.photoMatchability, top_policy.get("photo_matchability"))
        add_optional_literal(g, node, GUIDE.topProcedurePolicy, top_policy.get("top_procedure_policy"))


def build_snapshot_graph() -> Graph:
    g = Graph()
    bind(g)

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot_uri = APP[f"ServingSnapshot_{BASELINE_ID}"]
    g.add((snapshot_uri, RDF.type, APP.ServingSnapshot))
    g.add((snapshot_uri, APP.baselineId, Literal(BASELINE_ID, datatype=XSD.string)))
    g.add((snapshot_uri, PROV.generatedAtTime, Literal(generated_at, datatype=XSD.dateTime)))
    g.add((snapshot_uri, RDFS.comment, Literal("Validation-only snapshot generated from OHS serving artifacts. Runtime does not query this graph.", lang="en")))
    add_artifacts(g, snapshot_uri)

    run_uri = APP[f"ExportRun_{BASELINE_ID}_{safe_id(generated_at)}"]
    g.add((run_uri, RDF.type, PROV.Activity))
    g.add((run_uri, PROV.generated, snapshot_uri))
    g.add((run_uri, PROV.endedAtTime, Literal(generated_at, datatype=XSD.dateTime)))

    guide_data = load_json(GUIDE_PROFILES_PATH)
    photo_data = load_json(PHOTO_MATCHABILITY_PATH)
    broad_policy = load_json(BROAD_SR_POLICY_PATH)
    support_rows = load_jsonl(GUIDE_SUPPORT_PATH)
    pipeline_report = load_json(PIPELINE_REPORT_PATH)
    ci_candidate_promotion_report = load_json(CI_CANDIDATE_PROMOTION_REPORT_PATH)

    profiles = dict(guide_data.get("profiles") or {})
    photo_profiles = photo_data.get("profiles") or {}
    for guide_code, photo_profile in photo_profiles.items():
        if guide_code in profiles:
            # Runtime checks guide_photo_matchability.v1.json before falling
            # back to guide_domain_profiles.json, so the validation snapshot
            # must reflect the same precedence for photo top/follow-up policy.
            for key in [
                "photo_matchability",
                "top_procedure_policy",
                "followup_policy",
                "classification_reason",
                "review_status",
                "evidence_terms",
            ]:
                if photo_profile.get(key) not in (None, "", []):
                    profiles[guide_code][key] = photo_profile.get(key)

    add_guide_profiles(g, profiles)
    add_broad_sr_policy(g, broad_policy)
    add_support_candidates(g, support_rows)
    add_ci_candidate_promotion_rows(g, ci_candidate_promotion_report.get("rows") or [])
    add_evaluation_cases(g, pipeline_report.get("records") or [])

    summary = pipeline_report.get("summary") or {}
    for key, value in (summary.get("guide_metrics") or {}).items():
        if isinstance(value, (str, int, float, bool)):
            g.add((snapshot_uri, APP[f"metric_{safe_id(key)}"], Literal(value)))
    for key, value in (summary.get("ci_metrics") or {}).items():
        if isinstance(value, (str, int, float, bool)):
            g.add((snapshot_uri, APP[f"metric_{safe_id(key)}"], Literal(value)))
    return g


def main() -> int:
    policy_graph = build_policy_graph()
    snapshot_graph = build_snapshot_graph()

    POLICY_TTL_PATH.write_text(policy_graph.serialize(format="turtle").rstrip() + "\n", encoding="utf-8")
    SNAPSHOT_TTL_PATH.write_text(snapshot_graph.serialize(format="turtle").rstrip() + "\n", encoding="utf-8")
    SHAPES_TTL_PATH.write_text(build_shapes_text(), encoding="utf-8")

    print(f"wrote: {POLICY_TTL_PATH}")
    print(f"wrote: {SNAPSHOT_TTL_PATH}")
    print(f"wrote: {SHAPES_TTL_PATH}")
    print(f"snapshot triples: {len(snapshot_graph):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
