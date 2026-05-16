#!/usr/bin/env python3
"""Export manual domain-guard batches as OHS serving artifacts.

OHS runtime intentionally reads local data files under serving-team/08-app/backend/app/data,
not koshaontology working files.  This script packages the reviewed manual
Guide boundary profiles and the broad-SR policy into that serving location.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
ARCH_ROOT = PIPE_B_ROOT.parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
OHS_DATA_DIR = ARCH_ROOT / "OHS" / "backend" / "app" / "data"

SERVING_CONFIDENCE = 0.65
SERVING_STATUSES = {"candidate", "asserted"}
PROFILE_OUT = OHS_DATA_DIR / "guide_domain_profiles.json"
BROAD_SR_OUT = OHS_DATA_DIR / "broad_sr_policy.json"
BROAD_SR_SOURCE = DATA_DIR / "manual-enrichment-domain-guard-broad-sr-policy.json"
USAGE_PROFILE_SOURCE = DATA_DIR / "manual-guide-usage-profiles.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def batch_paths() -> list[Path]:
    return sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json"))


def load_usage_profiles() -> dict[str, dict[str, Any]]:
    if not USAGE_PROFILE_SOURCE.exists():
        return {}
    data = read_json(USAGE_PROFILE_SOURCE)
    profiles = data.get("profiles") or {}
    return profiles if isinstance(profiles, dict) else {}


def candidate_status(candidate: dict[str, Any], guide: dict[str, Any]) -> str:
    return str(candidate.get("review_status") or guide.get("review_status") or "candidate")


def is_serving_eligible(candidate: dict[str, Any], guide: dict[str, Any]) -> bool:
    confidence = float(candidate.get("confidence") or 0.0)
    return confidence >= SERVING_CONFIDENCE and candidate_status(candidate, guide) in SERVING_STATUSES


def compact_candidate(candidate: dict[str, Any], guide: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    payload = {field: candidate.get(field) for field in fields}
    payload.update({
        "confidence": candidate.get("confidence"),
        "evidence": candidate.get("evidence"),
        "source_fields": candidate.get("source_fields") or [],
        "method": candidate.get("method") or guide.get("method"),
        "review_status": candidate_status(candidate, guide),
    })
    return payload


def build_profiles() -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    usage_profiles = load_usage_profiles()
    level_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    procedure_role_counts: Counter[str] = Counter()
    total_feature = 0
    total_sr = 0
    total_visual = 0

    for path in batch_paths():
        batch = read_json(path)
        batch_id = (batch.get("scope") or {}).get("batch_id") or path.stem
        for guide in batch.get("guides", []) or []:
            guide_code = guide.get("guide_code")
            if not guide_code:
                continue
            domain_profile = dict(guide.get("domain_profile") or {})
            profile_level = domain_profile.get("profile_level") or "general"
            level_counts[profile_level] += 1

            serving_features = [
                compact_candidate(candidate, guide, ["entity_type", "entity_id", "axis", "feature_code"])
                for candidate in guide.get("feature_candidates", []) or []
                if is_serving_eligible(candidate, guide)
            ]
            serving_srs = [
                compact_candidate(candidate, guide, ["entity_type", "entity_id", "sr_id"])
                for candidate in guide.get("sr_link_candidates", []) or []
                if is_serving_eligible(candidate, guide)
            ]
            serving_visuals = [
                compact_candidate(candidate, guide, ["entity_type", "entity_id", "trigger_text", "cue_type"])
                for candidate in guide.get("visual_trigger_candidates", []) or []
                if is_serving_eligible(candidate, guide)
            ]

            for collection in (
                guide.get("feature_candidates", []) or [],
                guide.get("sr_link_candidates", []) or [],
                guide.get("visual_trigger_candidates", []) or [],
            ):
                for candidate in collection:
                    status_counts[candidate_status(candidate, guide)] += 1
            total_feature += len(serving_features)
            total_sr += len(serving_srs)
            total_visual += len(serving_visuals)

            usage_profile = usage_profiles.get(guide_code) or {}
            procedure_role = usage_profile.get("procedure_role") or "unknown"
            procedure_role_counts[procedure_role] += 1

            profiles[guide_code] = {
                "guide_code": guide_code,
                "title": guide.get("title"),
                "short_code": guide.get("short_code"),
                "source_file": guide.get("source_file"),
                "batch_id": batch_id,
                "profile_level": profile_level,
                "domain_family": domain_profile.get("domain_family"),
                "mismatch_policy": domain_profile.get("mismatch_policy"),
                "required_context_terms": domain_profile.get("required_context_terms") or [],
                "negative_context_terms": domain_profile.get("negative_context_terms") or [],
                "industry_alignment": domain_profile.get("industry_alignment") or [],
                "confidence": domain_profile.get("confidence"),
                "evidence": domain_profile.get("evidence"),
                "source_fields": domain_profile.get("source_fields") or [],
                "recommendation_boundary": guide.get("recommendation_boundary") or {},
                "feature_codes": sorted({row["feature_code"] for row in serving_features if row.get("feature_code")}),
                "sr_ids": sorted({row["sr_id"] for row in serving_srs if row.get("sr_id")}),
                "visual_triggers": sorted({row["trigger_text"] for row in serving_visuals if row.get("trigger_text")}),
                "serving_feature_candidates": serving_features,
                "serving_sr_link_candidates": serving_srs,
                "serving_visual_trigger_candidates": serving_visuals,
                "usage_summary": usage_profile.get("usage_summary"),
                "intended_workplaces": usage_profile.get("intended_workplaces") or [],
                "intended_tasks": usage_profile.get("intended_tasks") or [],
                "observable_required_cues": usage_profile.get("observable_required_cues") or [],
                "negative_boundaries": usage_profile.get("negative_boundaries") or [],
                "procedure_role": usage_profile.get("procedure_role"),
                "primary_work_process_ids": usage_profile.get("primary_work_process_ids") or [],
                "primary_work_process_titles": usage_profile.get("primary_work_process_titles") or [],
                "usage_profile_evidence": usage_profile.get("evidence"),
                "usage_profile_review_status": usage_profile.get("review_status"),
            }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "codex_manual_domain_profiles",
        "source": "data-team/02-extraction/pipe-B/data/manual-enrichment-domain-guard-batch-001..035.json",
        "serving_policy": {
            "min_confidence": SERVING_CONFIDENCE,
            "review_status_in": sorted(SERVING_STATUSES),
            "legal_asserted_use": False,
        },
        "guide_count": len(profiles),
        "profile_level_counts": dict(sorted(level_counts.items())),
        "procedure_role_counts": dict(sorted(procedure_role_counts.items())),
        "candidate_review_status_counts": dict(sorted(status_counts.items())),
        "serving_candidate_counts": {
            "feature": total_feature,
            "sr": total_sr,
            "visual": total_visual,
        },
        "profiles": dict(sorted(profiles.items())),
    }


def build_broad_policy() -> dict[str, Any]:
    source = read_json(BROAD_SR_SOURCE)
    broad_ids = [item["sr_id"] for item in source.get("broad_sr_candidates", []) if item.get("sr_id")]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "codex_manual_broad_sr_policy_export",
        "source": f"data-team/02-extraction/pipe-B/data/{BROAD_SR_SOURCE.name}",
        "policy_version": source.get("policy_version"),
        "purpose": source.get("purpose"),
        "broad_sr_ids": broad_ids,
        "secondary_score_multiplier": 0.35,
        "runtime_rules": source.get("runtime_rules") or [],
        "broad_sr_candidates": source.get("broad_sr_candidates") or [],
        "legal_asserted_use": False,
    }


def main() -> None:
    OHS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    profiles = build_profiles()
    broad_policy = build_broad_policy()
    write_json(PROFILE_OUT, profiles)
    write_json(BROAD_SR_OUT, broad_policy)
    print(f"Wrote {PROFILE_OUT}")
    print(f"Wrote {BROAD_SR_OUT}")


if __name__ == "__main__":
    main()
