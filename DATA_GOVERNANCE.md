# Data Governance

Latest updated: 2026-05-10

## Purpose

This document defines what data belongs in git, what belongs in LFS or external storage, and what is treated as a generated artifact.

The rule is selective tracking. The project should preserve reproducibility without turning GitHub into a dump of raw PDFs, cached reports, or transient parser output.

## Data Classes

| Class | Examples | Policy |
|---|---|---|
| Root coordination docs | `README.md`, `NEXT_SESSION_INSTRUCTIONS.md`, `MONOREPO_TRANSITION_PLAN.md` | Track in root git |
| Synthetic evaluation inputs | `pictures-json/synthetic_observations_v1.jsonl` through `v10` | Track in root git |
| Latest lightweight reports | selected `pictures-json/reports/*.md/json/csv` baseline files | Track only current baseline files |
| Old evaluation reports | historical `pictures-json/reports/**` | Do not bulk-edit; keep ignored unless explicitly promoted |
| Parsed guide corpus | future `kosha-guides/parsed/**` | Track after monorepo policy is enabled |
| Guide manifest | future `kosha-guides/manifest/**` | Track; source for provenance export |
| Raw KOSHA PDFs | `kosha-guides/{A,B,C,D,E}/**/*.pdf` | LFS or external storage with manifest references |
| Generated candidate artifacts | manual domain batches, import previews, usage profiles | Track only when they are accepted pipeline baselines |
| Local-only runtime state | `.env`, `.venv`, `node_modules`, cache, temporary logs | Never track |

## Current Size Signals

Current local data sizes show why selective tracking is required:

- `kosha-guides` is about 697 MB.
- raw KOSHA PDF bytes are about 680 MB.
- `kosha-guides/parsed` is about 92 MB.
- `pictures-json/reports` is about 11 GB.

The existing root tracked final-report PDF is treated as a historical exception. New large binary artifacts should use LFS or an external artifact location referenced by manifest.

## Manifest Policy

`kosha-guides/manifest/` is the future source metadata registry. It should identify:

- guide code and short code
- source PDF path
- parsed guide JSON path
- parsed CI/entity JSON path
- title
- checksum
- parse status
- parse run identifier
- conflict or mismatch state

The manifest is operational JSON first, but it must be exportable to W3C provenance graphs.

## Generated Artifact Policy

Generated artifacts may be tracked when they are accepted baselines used by another subsystem.

Examples:

- `OHS/backend/app/data/guide_domain_profiles.json` is a serving artifact and should be tracked in `OHS`.
- `koshaontology/pipe-B/data/manual-guide-usage-profiles.json` is a materialized pipeline baseline and should be tracked in `koshaontology`.
- ad hoc temporary files such as `tmp-*.json`, raw model logs, local parse scratch, and cache files should not be tracked.

## Report Policy

Synthetic and actual-response reports are append-only evidence. Do not rewrite old report bodies to update wording. Add a new report for a new run, then link the current accepted baseline from root docs.

Current accepted Guide recommendation baseline:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.*
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.*
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.*
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.*
```

## Secrets And Local State

Never track:

- `.env`
- API keys
- database passwords beyond already documented local defaults
- `node_modules`
- `.venv`
- `__pycache__`
- parser scratch logs
- browser automation cache

Before pushing, check:

```bash
git status --short
git diff --cached --name-only | rg '\\.env|node_modules|\\.venv|__pycache__|tmp-|raw-response'
```
