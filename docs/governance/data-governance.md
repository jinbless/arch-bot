# Data Governance

Latest updated: 2026-05-15

## Purpose

This document defines what data belongs in root git after the monorepo snapshot import, what stays external/LFS, and what is local-only generated state.

The rule is selective tracking. The project should preserve reproducibility without turning GitHub into a dump of raw PDFs, historical reports, runtime logs, or transient parser output.

## Data Classes

| Class | Examples | Policy |
|---|---|---|
| Root coordination docs | `README.md`, `CLAUDE.md`, `docs/README.md`, `docs/status/current-session.md`, `docs/governance/monorepo-transition.md` | Track |
| Project source | `OHS/**`, `koshaontology/**` | Track snapshot from pushed child baselines |
| External dependency | `legalize-kr/**` | Do not track in root |
| Synthetic evaluation inputs | `pictures-json/synthetic_observations_v1.jsonl` through `v10` | Track |
| Report manifest | `pictures-json/reports-manifest.json`, `docs/status/evaluation-baseline.md` | Track |
| Report bodies | `pictures-json/reports/**` | External/local unless explicitly promoted later |
| Parsed guide corpus | `kosha-guides/parsed/**` | Track |
| Guide manifest | `kosha-guides/manifest/**` | Track |
| Raw KOSHA PDFs | `kosha-guides/{A,B,C,D,E}/**/*.pdf` | External or LFS, referenced by manifest |
| Accepted serving artifacts | `OHS/backend/app/data/*.json`, accepted Pipe-B/C materializations | Track when already part of source baseline |
| Serving validation ontology snapshots | `koshaontology/ontology/serving-*.ttl`, `koshaontology/ontology/serving-validation-report-*.{json,md,csv}` | Track accepted baseline snapshots and validation reports |
| Local-only runtime state | `.env`, `.venv`, `node_modules`, `.dev-logs`, cache, temporary logs | Never track |

## Current Size Signals

Local size signals explain the policy:

- `kosha-guides` is about 697 MB.
- raw KOSHA PDF bytes are about 680 MB.
- `kosha-guides/parsed` is about 92 MB and is selected for tracking.
- `pictures-json/reports` is about 11 GB and is not selected for tracking.

The existing root tracked final-report PDF is treated as a historical exception. New large binary artifacts should use LFS or an external artifact location referenced by manifest.

## Manifest Policy

`kosha-guides/manifest/guides-manifest.json` is the current parsed Guide provenance registry. It records:

- guide code and short code
- title
- parsed Guide JSON path
- parsed Guide checksum
- source PDF path and local existence signal
- parse status
- parser metadata when available

The manifest is operational JSON first, but it must remain exportable to W3C provenance graphs using PROV-O, DCAT, DCTERMS, and SHACL.

`pictures-json/reports-manifest.json` records accepted evaluation baselines and checksums for local/external report bodies.

## Generated Artifact Policy

Generated artifacts may be tracked only when they are accepted baselines used by another subsystem.

Examples:

- `OHS/backend/app/data/guide_domain_profiles.json` is a serving artifact and is tracked.
- `koshaontology/ontology/serving-snapshot-ci_broad_sr_guard4.ttl` is a validation-only snapshot and is tracked because it is the accepted baseline audit artifact.
- `koshaontology/ontology/serving-validation-report-ci_broad_sr_guard4.*` is tracked because it records machine-found anomaly queues for the accepted baseline.
- `koshaontology/pipe-B/data/manual-guide-usage-profiles.json` is a materialized pipeline baseline and is tracked.
- `koshaontology/pipe-B/data/vlm-parse-errors.jsonl` remains tracked because it was part of the pushed Pipe-B source baseline.
- ad hoc files such as `tmp-*.json`, VLM parse logs, raw model logs, browser cache, and local scratch files are not tracked.

## Report Policy

Synthetic and actual-response reports are append-only evidence. Do not rewrite old report bodies to update wording. Add a new report for a new run, then update the current accepted baseline in:

```text
pictures-json/reports-manifest.json
docs/status/evaluation-baseline.md
```

Current accepted Guide recommendation baseline:

```text
ci_broad_sr_guard4
```

Referenced local/external report bodies:

```text
pictures-json/reports/pipeline_quality_v1_v10_ci_broad_sr_guard4.*
pictures-json/reports/stage2_5_no_top_root_cause_ci_broad_sr_guard4.*
pictures-json/reports/stage2_5_no_top_actionability_ci_broad_sr_guard4.*
pictures-json/reports/synthetic_observations_v10_ci_broad_sr_guard4_report.*
pictures-json/reports/actual_response_samples_ci_broad_sr_guard4.*
pictures-json/reports/pg_guide_usage_profiles_sync_ci_broad_sr_guard4.*
```

Validation-only ontology snapshot for the current baseline:

```text
koshaontology/ontology/serving-policy.ttl
koshaontology/ontology/serving-snapshot-ci_broad_sr_guard4.ttl
koshaontology/ontology/serving-validation-shapes.ttl
koshaontology/ontology/serving-validation-report-ci_broad_sr_guard4.*
koshaontology/ontology/serving-workprocess-alignment-ci_broad_sr_guard4.*
```

## Secrets And Local State

Never track:

- `.env`
- API keys
- database passwords beyond already documented local defaults
- `node_modules`
- `.venv`
- `__pycache__`
- `.dev-logs`
- parser scratch logs
- browser automation cache
- raw KOSHA PDFs
- historical report bodies under `pictures-json/reports/**`

Before pushing, check:

```bash
git diff --cached --name-only | rg '\\.env|node_modules|\\.venv|__pycache__|\\.dev-logs|tmp-|raw-response|pictures-json/reports/|kosha-guides/.+\\.pdf'
```
