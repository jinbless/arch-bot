# Manual Domain Guard Import Preview

- generated_at: `2026-05-10T04:51:21.677495+00:00`
- source_batches: `35`
- unique_guides: `1038`
- asserted_mapping_updates: `0`
- import_mode: `preview_only`

## Candidate Rows

| table | rows | serving_eligible | excluded_by_status | excluded_by_confidence |
| --- | ---: | ---: | ---: | ---: |
| `guide_entity_feature_candidates` | 2084 | 1812 | 268 | 4 |
| `guide_sr_link_candidates` | 4323 | 2767 | 1556 | 0 |
| `guide_visual_trigger_candidates` | 2077 | 2067 | 10 | 0 |

## Validation

- missing_required_fields: `0`
- invalid_review_status: `0`
- invalid_sr_id: `0`
- non_catalog_feature_code: `0`
- entity_fk_violations: `0`
- duplicate_unique_key_tables: `1`

### Mergeable Duplicate Unique Keys

These source rows must be pre-aggregated before real DB import.

- `guide_sr_link_candidates`
  - `['GUIDE', 'A-67-2018', 'SR-FIRE_EXPLOSION-015', 'codex_manual_pilot']` count 2
  - `['GUIDE', 'A-68-2018', 'SR-FIRE_EXPLOSION-015', 'codex_manual_pilot']` count 2

## Import Strategy

- Do not write asserted mapping tables from this preview.
- Import candidate tables with `replace-per-method`: delete/replace rows for `method=codex_manual_pilot` before inserting corrected rows.
- Do not use `GREATEST(confidence)` for this import path because manual demotions to `needs_review`/lower confidence must be preserved.
- OHS serving must require both `confidence >= 0.65` and `review_status in ('candidate', 'asserted')`.
