# Synthetic Observations v1-v10 Confusion Matrix (v10fix6)

## Overall Summary

- Total cases: 2360
- SHE TP/FN/FP/TN: 2016/0/67/277
- SHE recall: 100.0%
- SHE precision: 96.8%
- SHE specificity: 80.5%
- SHE FN cases: 0
- SHE FP cases: 67

## Split Metrics

| Metric | Value |
|---|---:|
| confirmed_risk expected | 1377 |
| confirmed_risk TP/FN/FP | 930/447/157 |
| confirmed_risk recall | 67.5% |
| confirmed_risk precision | 85.6% |
| clarification expected/captured | 707/706 |
| clarification capture rate | 99.9% |
| clarification over-promotion | 157 (22.2%) |
| normal suppression | 276/276 (100.0%) |

## By Version

| Version | Cases | TP | FN | FP | TN | Recall | Specificity | Confirmed Recall | Confirmed Precision | Clarification Capture | Over-promotion | Normal Suppression |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v1 | 120 | 71 | 0 | 28 | 21 | 100.0% | 42.9% | 53.3% | 80.0% | 97.5% | 20.0% | 100.0% |
| v2 | 100 | 70 | 0 | 10 | 20 | 100.0% | 66.7% | 69.1% | 84.4% | 100.0% | 28.0% | 100.0% |
| v3 | 200 | 155 | 0 | 25 | 20 | 100.0% | 44.4% | 57.5% | 97.2% | 100.0% | 3.3% | 100.0% |
| v4 | 80 | 72 | 0 | 0 | 8 | 100.0% | 100.0% | 52.1% | 96.2% | 100.0% | 4.2% | 100.0% |
| v5 | 210 | 189 | 0 | 0 | 21 | 100.0% | 100.0% | 66.7% | 98.8% | 100.0% | 1.6% | 100.0% |
| v6 | 330 | 297 | 0 | 0 | 33 | 100.0% | 100.0% | 73.2% | 78.8% | 100.0% | 39.4% | 100.0% |
| v7 | 330 | 296 | 0 | 1 | 33 | 100.0% | 97.1% | 80.3% | 94.6% | 100.0% | 9.1% | 100.0% |
| v8 | 330 | 294 | 0 | 3 | 33 | 100.0% | 91.7% | 75.3% | 87.1% | 100.0% | 22.2% | 100.0% |
| v9 | 330 | 286 | 0 | 0 | 44 | 100.0% | 100.0% | 78.1% | 94.2% | 100.0% | 9.1% | 100.0% |
| v10 | 330 | 286 | 0 | 0 | 44 | 100.0% | 100.0% | 44.4% | 58.5% | 100.0% | 59.6% | 100.0% |

## FP Distribution

### Case Type
- ambiguous: 67

### Work Context
- GENERAL_WORKPLACE: 11
- VEHICLE: 4
- CONFINED_SPACE: 3
- CRANE: 3
- WELDING: 3
- MATERIAL_HANDLING: 3
- FOOD_PREP: 3
- HOT_BEVERAGE: 3
- CLEANING_WET: 3
- COLD_STORAGE: 3
- SERVING_FLOOR: 3
- DELIVERY_RIDER: 3
- DEEP_FRYING: 2
- GAS_APPLIANCE: 2
- STORAGE_SHELF: 2
- SCAFFOLD: 1
- EXCAVATION: 1
- CONVEYOR: 1
- ROBOT: 1
- DEMOLITION: 1
- PAINTING: 1
- GRINDING: 1
- PRESSURIZED_WORK: 1
- ROPE_ACCESS: 1
- MACHINE: 1
- LADDER: 1
- KITCHEN_COOKING: 1
- TIRE_WHEEL: 1
- MANUAL_HANDLING: 1
- WASHING_MACHINE: 1

## FN Distribution

- none

## Artifacts

- JSON: `pictures-json/reports/synthetic_observations_v1_v10_v10fix6_confusion_matrix.json`
- FP cases CSV: `pictures-json/reports/synthetic_observations_v1_v10_v10fix6_fp_cases.csv`
- FN cases CSV: `pictures-json/reports/synthetic_observations_v1_v10_v10fix6_fn_cases.csv`
