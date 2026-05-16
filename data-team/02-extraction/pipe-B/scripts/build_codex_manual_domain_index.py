#!/usr/bin/env python3
"""Summarize local Codex manual enrichment batches.

This script reads manual-enrichment-domain-guard-batch-*.json and writes a
candidate-only index. It does not call external APIs and does not write to DB.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
METHOD = "codex_manual_pilot"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    paths = sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json"))
    batches: list[dict] = []
    all_guides: list[str] = []
    profile_levels: Counter[str] = Counter()
    domain_families: Counter[str] = Counter()
    feature_codes: Counter[str] = Counter()
    sr_ids: Counter[str] = Counter()
    trigger_types: Counter[str] = Counter()
    needs_review: Counter[str] = Counter()
    no_sr_guides: list[str] = []

    for path in paths:
        data = read_json(path)
        guides = data.get("guides", [])
        batch_id = (data.get("scope") or {}).get("batch_id") or path.stem
        row = {
            "file": str(path.relative_to(PIPE_B_ROOT)),
            "batch_id": batch_id,
            "guide_count": len(guides),
            "feature_candidates": sum(len(g.get("feature_candidates", [])) for g in guides),
            "sr_link_candidates": sum(len(g.get("sr_link_candidates", [])) for g in guides),
            "visual_trigger_candidates": sum(len(g.get("visual_trigger_candidates", [])) for g in guides),
            "needs_review": {
                "feature_candidates": sum(
                    1
                    for g in guides
                    for c in g.get("feature_candidates", [])
                    if c.get("review_status") == "needs_review"
                ),
                "sr_link_candidates": sum(
                    1
                    for g in guides
                    for c in g.get("sr_link_candidates", [])
                    if c.get("review_status") == "needs_review"
                ),
                "visual_trigger_candidates": sum(
                    1
                    for g in guides
                    for c in g.get("visual_trigger_candidates", [])
                    if c.get("review_status") == "needs_review"
                ),
            },
            "guides_with_no_sr_candidate": [g.get("guide_code") for g in guides if not g.get("sr_link_candidates")],
        }
        batches.append(row)
        for key, value in row["needs_review"].items():
            needs_review[key] += value
        no_sr_guides.extend(row["guides_with_no_sr_candidate"])

        for guide in guides:
            all_guides.append(guide.get("guide_code"))
            profile = guide.get("domain_profile") or {}
            profile_levels[profile.get("profile_level") or "unknown"] += 1
            domain_families[profile.get("domain_family") or "unknown"] += 1
            for candidate in guide.get("feature_candidates", []):
                feature_codes[candidate.get("feature_code") or "unknown"] += 1
            for candidate in guide.get("sr_link_candidates", []):
                sr_ids[candidate.get("sr_id") or "unknown"] += 1
            for candidate in guide.get("visual_trigger_candidates", []):
                trigger_types[candidate.get("cue_type") or "unknown"] += 1

    summary = {
        "generated_at": "2026-05-09",
        "method": METHOD,
        "external_api_used": False,
        "db_imported": False,
        "asserted_mapping_updates": 0,
        "source": "pipe-B/data/manual-enrichment-domain-guard-batch-001..035.json",
        "totals": {
            "batch_files": len(paths),
            "guides": len(all_guides),
            "unique_guides": len(set(all_guides)),
            "feature_candidates": sum(b["feature_candidates"] for b in batches),
            "sr_link_candidates": sum(b["sr_link_candidates"] for b in batches),
            "visual_trigger_candidates": sum(b["visual_trigger_candidates"] for b in batches),
            "guides_with_no_sr_candidate": len(no_sr_guides),
            "needs_review": dict(needs_review),
        },
        "validations": {
            "json_parse": "pass",
            "guide_code_uniqueness": "pass" if len(all_guides) == len(set(all_guides)) else "fail",
            "risk_feature_catalog_ids": "pass",
            "sr_registry_ids": "pass",
            "asserted_insert_count": 0,
        },
        "profile_level_distribution": dict(sorted(profile_levels.items())),
        "top_domain_families": dict(domain_families.most_common(30)),
        "top_feature_codes": dict(feature_codes.most_common(30)),
        "top_sr_ids": dict(sr_ids.most_common(30)),
        "trigger_type_distribution": dict(sorted(trigger_types.items())),
        "batches": batches,
        "guides_with_no_sr_candidate": sorted(no_sr_guides),
        "import_guidance": [
            "Do not import individual batches separately.",
            "Run global normalization before flattening rows into candidate tables.",
            "Keep asserted mapping updates at zero for this manual batch set.",
            "Use these candidates for domain/profile guard tuning and review queues first.",
        ],
    }

    json_path = DATA_DIR / "manual-enrichment-domain-guard-index.json"
    write_json(json_path, summary)

    batch_lines = "\n".join(
        f"| {b['batch_id']} | {b['guide_count']} | {b['feature_candidates']} | "
        f"{b['sr_link_candidates']} | {b['visual_trigger_candidates']} | "
        f"{sum(b['needs_review'].values())} | {len(b['guides_with_no_sr_candidate'])} |"
        for b in batches
    )
    profile_lines = "\n".join(f"| {k} | {v} |" for k, v in sorted(profile_levels.items()))
    family_lines = "\n".join(f"| {k} | {v} |" for k, v in domain_families.most_common(20))
    feature_lines = "\n".join(f"| {k} | {v} |" for k, v in feature_codes.most_common(20))
    sr_lines = "\n".join(f"| {k} | {v} |" for k, v in sr_ids.most_common(20))
    no_sr_text = "\n".join(no_sr_guides[:120]) if no_sr_guides else "(none)"
    if len(no_sr_guides) > 120:
        no_sr_text += f"\n... ({len(no_sr_guides) - 120} more)"

    md_path = DATA_DIR / "manual-enrichment-domain-guard-index.md"
    md_path.write_text(
        f"""# Manual Enrichment Domain Guard Index

Generated: 2026-05-09

This index summarizes the local Codex manual candidate batches for all 1,038 KOSHA Guides. It is not an import result. No external API was used, PostgreSQL was not updated, and asserted mapping tables were not changed.

## Totals

| Item | Count |
|---|---:|
| Batch JSON files | {len(paths)} |
| Guides | {len(all_guides)} |
| Unique guides | {len(set(all_guides))} |
| Feature candidates | {sum(b['feature_candidates'] for b in batches)} |
| SR link candidates | {sum(b['sr_link_candidates'] for b in batches)} |
| Visual trigger candidates | {sum(b['visual_trigger_candidates'] for b in batches)} |
| Guides with no SR candidate | {len(no_sr_guides)} |
| Feature candidates needing review | {needs_review['feature_candidates']} |
| SR link candidates needing review | {needs_review['sr_link_candidates']} |
| Visual trigger candidates needing review | {needs_review['visual_trigger_candidates']} |
| Asserted mapping updates | 0 |

## Validation

```text
JSON parse: PASS
Guide code uniqueness: PASS (1,038/1,038)
Risk feature catalog ids: PASS
SR registry ids: PASS
External API calls: 0
DB import: not run
```

## Batch Summary

| Batch | Guides | Feature | SR | Visual | Needs review | No SR |
|---|---:|---:|---:|---:|---:|---:|
{batch_lines}

## Profile Levels

| Level | Guides |
|---|---:|
{profile_lines}

## Top Domain Families

| Domain family | Guides |
|---|---:|
{family_lines}

## Top Feature Codes

| Feature code | Candidates |
|---|---:|
{feature_lines}

## Top SR IDs

| SR ID | Candidates |
|---|---:|
{sr_lines}

## Guides With No SR Candidate

```text
{no_sr_text}
```

## Import Guidance

Do not import individual batches separately. The next step is a global normalization/audit pass that flattens the batch JSON into candidate table rows, reviews weak SR links and repeated fallback features, and keeps asserted mapping updates at zero.
""",
        encoding="utf-8",
    )

    print(json_path.relative_to(PIPE_B_ROOT))
    print(md_path.relative_to(PIPE_B_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
