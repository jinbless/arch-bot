# Evaluation Baseline

Latest updated: 2026-05-10

Accepted baseline: `usage_profile11`

The full report bodies under `pictures-json/reports/**` are local/external artifacts. Root git tracks `pictures-json/reports-manifest.json` and this summary instead of adding historical report files to repository history.

## Synthetic Guide Recommendation v1~v10

Source report:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.*
```

Summary:

```text
total samples: 2,360
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction count: 980
reduction ratio: 85.59%
attention cases: 560
```

Current failure queues:

```text
missing_usage_profile: 395
industry_boundary_gap: 160
workprocess_mismatch: 4
broad_sr_overreach: 1
```

## Synthetic NO_TOP Queue

Source report:

```text
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.*
```

Summary:

```text
total NO_TOP: 395
other_taxonomy_gap: 141
chemical_profile_gap: 64
construction_fall_profile_gap: 57
service_sector_taxonomy_gap: 49
machine_profile_gap: 43
burn_heat_profile_gap: 25
material_handling_profile_gap: 9
electrical_profile_gap: 7
```

## v10 Smoke

Source report:

```text
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.*
```

Summary:

```text
v10 cases: 330
SHE recall: 100.0%
SHE false negative: 0
SHE false positive: 0
normal suppression: 100.0%
```

## Actual Response 240 Regression

Source report:

```text
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.*
```

Summary:

```text
total samples: 240
status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
attention cases: 74
```

## Operating Note

The next Guide-quality work should improve usage profiles and WorkProcess relevance. Broadening status-level risk inference or adding generic text aliases was rejected because it changed actual 240 status boundaries.
