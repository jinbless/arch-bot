# Manual Enrichment Domain Guard Domain Guard Manual Batch 024

Generated: 2026-05-09

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: data/manual-enrichment-domain-guard-batch-024.json
method: codex_manual_pilot
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: inventory order excluding prior manual batches
manual_review: source-JSON reviewed on 2026-05-09
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | 30 |
| Guide domain profiles | 30 |
| Feature candidates | 60 |
| SR link candidates | 118 |
| Visual trigger candidates | 60 |
| Guides with no SR candidate | 0 |
| Feature candidates needing review | 0 |
| SR link candidates needing review | 118 |
| Visual trigger candidates needing review | 0 |

Guides with no SR candidate:

```text
(none)
```

## Manual Correction Notes

```text
A-119/A-120/A-122/A-145: glycol ether and glycol measurement Guides constrained to adsorption-tube, GC/FID, desorption, calibration, and lab-analysis cues.
A-12/A-13: tin and zirconium measurement Guides separated from field metal-control procedures and kept as membrane-filter/AAS/acid-digestion profiles.
A-121/A-123~A-131/A-133/A-135~A-137/A-139/A-140/A-144: acrylate, acetate, ether, alcohol, and allyl glycidyl ether measurement Guides bounded by charcoal/Tenax tubes, GC/FID, volatile/flammable lab handling, hood, and PPE evidence.
A-132/A-134/A-138/A-141/A-142/A-143/A-146: amine/alkanolamine measurement Guides bounded by coated sorbent tubes, HPLC or GC/FID, derivatization/neutralization, irritation/corrosion cues, hood, and PPE evidence.
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
| A-119-2018 | exclusive | work_environment_measurement_analysis_에틸렌글리콜모노부틸에테르 |
| A-12-2018 | exclusive | work_environment_measurement_analysis_주석 |
| A-120-2018 | exclusive | work_environment_measurement_analysis_에틸렌글리콜모노에틸에테르 |
| A-121-2018 | exclusive | work_environment_measurement_analysis_에틸아크릴레이트 |
| A-122-2018 | exclusive | work_environment_measurement_analysis_에틸렌글리콜모노에틸에테르아세테이트 |
| A-123-2018 | exclusive | work_environment_measurement_analysis_초산부틸 |
| A-124-2018 | exclusive | work_environment_measurement_analysis_초산이소부틸 |
| A-125-2018 | exclusive | work_environment_measurement_analysis_초산이소펜틸 |
| A-126-2018 | exclusive | work_environment_measurement_analysis_초산펜틸 |
| A-127-2018 | exclusive | work_environment_measurement_analysis_초산프로필 |
| A-128-2018 | exclusive | work_environment_measurement_analysis_에틸에테르 |
| A-129-2018 | exclusive | work_environment_measurement_analysis_초산이소프로필 |
| A-13-2018 | exclusive | work_environment_measurement_analysis_지르코니움 |
| A-130-2018 | exclusive | work_environment_measurement_analysis_초산메틸 |
| A-131-2018 | exclusive | work_environment_measurement_analysis_초산에틸 |
| A-132-2018 | exclusive | work_environment_measurement_analysis_2_디에틸아미노에탄올 |
| A-133-2018 | exclusive | work_environment_measurement_analysis_이소프로필알콜 |
| A-134-2018 | exclusive | work_environment_measurement_analysis_에탄올아민 |
| A-135-2018 | exclusive | work_environment_measurement_analysis_1_부탄올 |
| A-136-2018 | exclusive | work_environment_measurement_analysis_2_부탄올 |
| A-137-2018 | exclusive | work_environment_measurement_analysis_이소부틸알콜 |
| A-138-2018 | exclusive | work_environment_measurement_analysis_디메틸아민 |
| A-139-2018 | exclusive | work_environment_measurement_analysis_시클로헥사놀 |
| A-140-2018 | exclusive | work_environment_measurement_analysis_이소아밀알콜 |
| A-141-2018 | exclusive | work_environment_measurement_analysis_디에틸아민 |
| A-142-2018 | exclusive | work_environment_measurement_analysis_디에탄올아민 |
| A-143-2018 | exclusive | work_environment_measurement_analysis_디에틸렌트리아민 |
| A-144-2018 | exclusive | work_environment_measurement_analysis_알릴글리시딜에테르 |
| A-145-2018 | exclusive | work_environment_measurement_analysis_에틸렌글리콜 |
| A-146-2018 | exclusive | work_environment_measurement_analysis_트리에틸아민 |

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
