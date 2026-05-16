# Serving WorkProcess Alignment Audit

- baseline: `ci_candidate_promotion_v1`
- generated_at: `2026-05-15T12:32:32.716759+00:00`
- profiles: `1038`
- base TTL Guides: `1038`
- base TTL WorkProcesses: `9316`
- source WorkProcesses for profiles: `9316`
- primary WorkProcess links: `4715`
- affected Guides: `0`
- hard issue count: `0`
- source-present/base-missing count: `0`

## Status Counts

- `present_in_base_ttl_same_guide`: 4715

## Top Affected Guides


## Interpretation

source_present_base_* means the serving profile points to a WorkProcess that exists in Pipe-B ci-output but is absent from the current base kosha-instances.ttl materialization.

If most rows are `source_present_base_wp_missing` or `source_present_base_guide_missing`, the correct next step is to regenerate the core Guide A-Box from Pipe-B/PG source data. Do not hand-edit generated TTL.

## Sample Rows
