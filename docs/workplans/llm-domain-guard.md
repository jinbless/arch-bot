# LLM Sampling Based Guide Domain Guard Workplan

Updated: 2026-05-10

## Purpose

This workstream generalizes the one-off `A-G-18-2026` port-context guard into a reusable Guide domain/profile guard.

The original implementation order was:

```text
30 Guide LLM pilot
-> store LLM outputs as candidates only
-> inspect domain/profile signals
-> use those signals plus runtime context to suppress or penalize domain-mismatched Guide recommendations
```

LLM output must not be treated as legal asserted evidence. It may improve candidate coverage and visual/domain cues, but asserted mapping tables stay unchanged unless a later strict review step explicitly promotes them.

## Workspace Boundaries

- Root monorepo snapshot: `/mnt/c/project/arch-bot`
  - This workplan lives at `docs/workplans/llm-domain-guard.md`.
  - `OHS/` and `koshaontology/` are ordinary root-tracked directories on `main`.
  - New report bodies may be generated locally under `pictures-json/reports/`, but root git tracks `pictures-json/reports-manifest.json` and `docs/status/evaluation-baseline.md` instead of historical report bodies.

- OHS source: `/mnt/c/project/arch-bot/OHS`
  - Runtime recommendation logic, backend/frontend checks, and actual/synthetic replay scripts.
  - Do not edit `frontend/node_modules/**`.

- koshaontology source: `/mnt/c/project/arch-bot/koshaontology`
  - Pipe-B LLM candidate generation and Pipe-C audit/status.
  - LLM rows are stored in candidate tables only.

- legalize-kr external dependency: `/mnt/c/project/arch-bot/legalize-kr`
  - Read-only for this workstream and ignored by root git.

## Current Accepted Baseline

`usage_profile11` supersedes the earlier `domain_guard2` and `usage_profile1/2/5` milestones.

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,145
current obvious top Guide mismatch: 165
reduction: 85.59%
NO_TOP: 395
v10 SHE recall: 100.0%, FN 0, FP 0
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
```

Current baseline index:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
```

## 30 Guide LLM Pilot Set

The pilot set mixes mandatory watch Guides and 240 replay top-procedure overexposure cases.

```text
A-G-18-2026
G-116-2014
B-5-2011
B-M-11-2025
B-M-32-2026
A-G-10-2025
B-E-21-2026
D-57-2016
C-C-16-2026
B-E-3-2025
B-E-19-2026
H-110-2013
H-221-2023
A-G-14-2026
D-C-10-2026
B-M-9-2025
A-G-1-2025
B-E-20-2026
D-C-7-2026
M-1-2013
P-24-2012
B-M-33-2026
E-M-4-2025
D-C-2-2025
O-1-2011
B-M-8-2025
D-53-2013
G-29-2011
H-115-2013
P-10-2012
```

## LLM Pilot Command

Run from `/mnt/c/project/arch-bot/koshaontology`.

```bash
set -a
. ../OHS/backend/.env
set +a
../OHS/backend/.venv/bin/python pipe-B/scripts/step8_ontology_enrichment.py \
  --use-llm \
  --llm-model gpt-4.1-mini \
  --report pipe-B/data/ontology-enrichment-llm-domain-guard-pilot-report.json \
  --guide A-G-18-2026 \
  --guide G-116-2014 \
  --guide B-5-2011 \
  --guide B-M-11-2025 \
  --guide B-M-32-2026 \
  --guide A-G-10-2025 \
  --guide B-E-21-2026 \
  --guide D-57-2016 \
  --guide C-C-16-2026 \
  --guide B-E-3-2025 \
  --guide B-E-19-2026 \
  --guide H-110-2013 \
  --guide H-221-2023 \
  --guide A-G-14-2026 \
  --guide D-C-10-2026 \
  --guide B-M-9-2025 \
  --guide A-G-1-2025 \
  --guide B-E-20-2026 \
  --guide D-C-7-2026 \
  --guide M-1-2013 \
  --guide P-24-2012 \
  --guide B-M-33-2026 \
  --guide E-M-4-2025 \
  --guide D-C-2-2025 \
  --guide O-1-2011 \
  --guide B-M-8-2025 \
  --guide D-53-2013 \
  --guide G-29-2011 \
  --guide H-115-2013 \
  --guide P-10-2012
```

Do not pass `--apply-asserted` or `--apply-facets` in the pilot.

Status:

```text
2026-05-09: External API LLM pilot was not executed.
Reason: this path sends local Guide text outside the workspace and requires explicit user approval.
The project instead completed local Codex manual review batches 001~035 for all 1,038 Guides.
If external LLM use is approved later, compare it against the manual baseline rather than replacing it blindly.
```

## Domain Guard Acceptance Checks

Historical baseline before generalization:

```text
actual response 240, ag18_guard2:
status changed 0
negative_false_positive 10
positive_missed 2
A-G-18 top procedure 51 -> 3
A-G-18 residual 3 all 항만 하역업
```

The generalized domain guard must keep:

```text
status changed 0
negative_false_positive <= 10
positive_missed <= 2
A-G-18 top procedure <= 3
A-G-18 residual only 항만 하역업
v10 synthetic SHE FN 0 / FP 0
```

## Current Implementation Notes

- `A-G-18-2026` is now represented as the first `exclusive` domain profile rule, not as a special runtime branch.
- `exclusive` mismatches are excluded from standard procedure and immediate action candidates.
- `domain_specific` mismatches are penalized, not excluded.
- Public API response fields are unchanged.

## Historical Domain-Guard Verification Results

Reports:

```text
pictures-json/reports/actual_response_samples_v1_v10_domain_guard2_vs_pipeb1038.json
pictures-json/reports/actual_response_samples_v1_v10_domain_guard2_vs_pipeb1038.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard2_vs_pipeb1038.csv
pictures-json/reports/synthetic_observations_v10_domain_guard2_report.json
pictures-json/reports/synthetic_observations_v10_domain_guard2_report.md
pictures-json/reports/synthetic_observations_v10_domain_guard2_cases.csv
```

Actual response 240 replay:

```text
status changed 0
negative_false_positive 10
positive_missed 2
A-G-18 top procedure 51 -> 3
G-116 top procedure 5 -> 0
A-G-10 top procedure 14 -> 3
```

v10 synthetic smoke:

```text
cases 330
SHE recall 100.0%
SHE false negative 0
SHE false positive 0
normal suppression 100.0%
```

Build checks:

```text
OHS backend targeted Python compile: OK
OHS frontend npm run build: OK
```

## Usage Profile Correction v3/v5

The second structural repair pass used the synthetic Guide v1~v10 evaluator as the main signal and kept actual response 240 as a status/penalty safety net.

Important implementation changes:

```text
exclusive Guide profiles now require a Guide-specific term/context hit
industry alignment is supplemental and cannot create a domain match by itself
domain_specific profiles no longer pass on industry-only matches
reference/management program Guides need explicit planning/program context
```

Manual batch corrections were applied to these overexposed Guides:

```text
A-G-12, A-G-9, C-70, H-100, A-R-2, H-187, A-G-14,
E-G-22, H-116, M-62, D-C-7
```

Accepted validation baseline:

```text
synthetic Guide v1~v10 total: 2,360
legacy obvious top Guide mismatch: 1,151
current obvious top Guide mismatch: 220
reduction: 80.89%
current failure counts:
  industry_boundary_gap 211
  missing_usage_profile 404
  workprocess_mismatch 7
  broad_sr_overreach 2
v10 SHE recall 100.0%, FN 0, FP 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

Intermediate reports:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile5_20260510_000306.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile5_20260510_000435.md
pictures-json/reports/synthetic_observations_v10_usage_profile5_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile5_vs_pipeb1038.md
```

NO_TOP queue split:

```text
total_no_top 404
other_taxonomy_gap 139
synthetic_fixture_gap 72
construction_fall_profile_gap 53
chemical_profile_gap 51
machine_profile_gap 33
service_sector_taxonomy_gap 26
burn_heat_profile_gap 22
electrical_profile_gap 5
material_handling_profile_gap 3
```

Interpretation:

```text
usage_profile5 was an accepted intermediate runtime baseline and is now superseded by usage_profile11.
It intentionally prefers suppressing weak Guide recommendations over filling the screen with domain-mismatched procedures.
The current repair step is coverage recovery from the usage_profile11 NO_TOP 395 queue: add missing Guide usage profiles, visual triggers, or WorkProcess links structurally without broadening status-level risk inference.
```

## Codex Manual Pilot Batch 001

External API use is still pending approval, so the first 30 Guide pilot was completed as a local Codex manual review instead.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-001.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-001.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 33
visual trigger candidates 60
asserted mapping updates 0
external API calls 0
```

Import status:

```text
Not imported into PostgreSQL yet.
Rows are candidate-table ready, but should be reviewed or flattened by a dedicated importer first.
All method values are codex_manual_pilot.
```

## Codex Manual Pilot Batch 002

Batch 002 continues in inventory order, excluding the 30 watch Guides already covered by batch 001.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-002.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-002.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 39
visual trigger candidates 60
asserted mapping updates 0
external API calls 0
```

Policy:

```text
Do not import batch 001 or 002 separately.
Accumulate all batches, run a global audit/normalization pass, then import candidates in one step.
```

## Codex Manual Batches 001-035

The full 1,038 Guide candidate draft set has now been generated locally.

Outputs:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-001.json
...
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-035.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-index.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-index.md
```

Helper scripts:

```text
koshaontology/pipe-B/scripts/build_codex_manual_domain_batches.py
koshaontology/pipe-B/scripts/build_codex_manual_domain_index.py
```

Counts:

```text
batch JSON files 35
guides reviewed 1,038
unique guides 1,038
feature candidates 2,083
SR link candidates 4,317
visual trigger candidates 2,076
guides with no SR candidate 76
feature candidates needing review 240
SR link candidates needing review 1,541
visual trigger candidates needing review 10
asserted mapping updates 0
external API calls 0
DB import not run
```

Domain profile distribution after tightening profile extraction to title/domainTerms/equipment-centered evidence:

```text
exclusive 692
domain_specific 316
general 30
```

Validation:

```text
JSON parse PASS
guide code uniqueness PASS 1,038/1,038
risk feature catalog id check PASS
SR registry id check PASS
required candidate fields PASS
domain guard schema PASS 35/35 files, errors 0, warnings 0
Python compile PASS
git diff whitespace check PASS
```

Semantic audit:

```text
report koshaontology/pipe-B/data/manual-enrichment-domain-guard-semantic-audit.json
report koshaontology/pipe-B/data/manual-enrichment-domain-guard-semantic-audit.md
correction report koshaontology/pipe-B/data/manual-enrichment-domain-guard-semantic-corrections.json
broad SR policy koshaontology/pipe-B/data/manual-enrichment-domain-guard-broad-sr-policy.json
guides with any review flag 739
high-risk guides 0
medium flags 1,288
low flags 809
asserted mapping updates 0
DB import not run
```

Key semantic risks:

```text
1. high-risk document/risk-method field-control SR candidates were demoted: 23 SR candidates across 9 Guides, changed files 5.
2. broad SRs are overused across unrelated domain families: SR-PPE-002, SR-CHEMICAL-024/025/026, SR-FIRE_EXPLOSION-015, SR-MGMT-004.
3. 333 exclusive Guides still use only broad feature codes, so runtime matching needs additional domain-specific feature/detail cues before import.
4. 17 operational-looking Guides have no SR candidate and need targeted review.
```

Important note:

```text
Batches 001-002 were rechecked against source JSON and normalized from pilot format.
Batches 003-035 were re-read and manually corrected from extracted Guide JSON.
All 35 batch JSON files now share the candidate-only domain guard schema:
domain_profile.negative_context_terms, domain_profile.industry_alignment,
recommendation_boundary, notes, and policy min_evidence/runtime fields are present.
All 35 batch files are still candidate draft data and must pass global audit/normalization before DB import.
```

## Codex Manual Batch 001-002 Recheck

Pilot batches 001-002 have been rechecked and normalized to the same candidate-only schema used by batches 003-035.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-001.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-001.md
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-002.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-002.md
```

Counts after recheck:

```text
batch 001: guides 30, feature 60, SR 65, visual 60, no-SR 3
batch 002: guides 30, feature 60, SR 66, visual 60, no-SR 6
asserted mapping updates 0
external API calls 0
```

Correction examples:

```text
B-M-11/M-1/B-M-33: forklift, CNC lathe, and conveyor Guides now use direct vehicle/machine/conveyor SR candidates.
E-M-4: corrected from chemical default to pathogen/PPE candidates.
A-G-12/A-G-15/A-G-16/A-G-4: PPE, emergency plan, lighting, and ladder Guides remapped to more direct SR candidates.
A-R-2/A-R-3: lifecycle safety and bowtie risk-assessment Guides kept no-SR because they are method/management documents.
F-2/G-1/G-100/G-106/G-108: wood dust/fire, tank hot work, forklift training, silica dust, and cultivator Guides corrected away from early broad defaults.
```

## Codex Manual Batch 003

Batch 003 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-003.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-003.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 48
visual trigger candidates 60
guides with no SR candidate 5
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
G-11-2017: chemical draft -> slip/trip/fall prevention
G-110-2014: fire/chemical draft -> waste paper baler/conveyor
G-44-2011: welding/fire draft -> hand tool use safety
```

## Codex Manual Batch 004

Batch 004 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-004.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-004.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 48
visual trigger candidates 60
guides with no SR candidate 4
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
G-53-2013: generic fire/electric draft -> event crowd and evacuation safety
G-55-2012: electrical-only draft -> vehicle repair lift/pit/electrical profile
G-90-2015: kitchen/food draft -> manual transport cart handling
G-78-2021: broad vehicle draft -> hazardous tank lorry loading/static control
```

## Codex Manual Batch 005

Batch 005 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-005.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-005.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 27
visual trigger candidates 60
guides with no SR candidate 16
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
X-34-2014/X-35-2014/X-43-2011: broad fire/chemical/electrical draft -> risk-analysis document profiles with no SR candidate
X-36-2016: generic fall/access draft -> moving-lift-truck exclusive profile
X-68-2015: generic confined/electric draft -> confined-space entry/rescue exclusive profile
B-6-2011: warehouse/material draft -> barge/marine cargo exclusive profile
B-E-1-2025: generic electrical draft -> lightning-protection exclusive profile
```

## Codex Manual Batch 006

Batch 006 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-006.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-006.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 67
visual trigger candidates 60
guides with no SR candidate 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
B-E-10/B-E-11: broad electrical draft -> deenergized/energized electrical work boundaries
B-E-14/B-E-9: electrical default -> leakage breaker and grounding system exclusive profiles
B-M-14/B-M-15/B-M-16: weak mechanical defaults -> grinding wheel, high-temperature dyeing pressure vessel, and mechanical parking system profiles
B-M-18/B-M-19/B-M-20: generic piping defaults -> piping life management, pipeline emergency plan, and pipe support installation profiles
```

## Codex Manual Batch 007

Batch 007 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-007.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-007.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 86
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 16
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
B-M-22: generic vehicle/mechanical draft -> 생활폐기물 수거차량 tailgate/hopper exclusive profile
B-M-25: generic machinery/electric draft -> lockout/tagout energy-isolation exclusive profile
B-M-27/B-M-28: broad equipment defaults -> autoclave pressure-vessel and hazardous flexible-hose profiles
B-M-34/B-M-7: crane/lifting guides split into crane operation and general lifting-equipment profiles
E-1/E-10/E-100/E-115: broad electrical defaults -> overhead line, battery, low-voltage shock protection, insulating PPE boundaries
```

## Codex Manual Batch 008

Batch 008 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-008.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-008.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 90
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 23
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
E-116/E-129/E-135/E-18: broad electrical/fire defaults -> overcurrent and switchgear-specific profiles
E-121/E-131/E-173/E-178: test-method documents -> ESD/EMC/static-measurement boundaries with conservative SR candidates
E-13/E-171/E-142: static electricity guides split into fuel-station, splash-filling, and pneumatic-grinder contexts
E-147: generic electrical draft -> communication cable manhole/pole work with confined-space and fall SR candidates
E-168/E-170: hospital electrical and photovoltaic installation profiles separated from generic electrical work
E-181/E-182: hazardous-area non-electrical equipment and accident-investigation guides kept exclusive to avoid broad recommendation leakage
```

## Codex Manual Batch 009

Batch 009 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-009.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-009.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 102
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 26
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
E-184: electrical_work draft -> portable chainsaw PPE / cutting boundary
E-185: generic fire/explosion -> lithium-ion ESS rack, BMS, ventilation, fire compartment boundary
E-186/E-22/E-46: operational document profiles kept exclusive with conservative SR candidates
E-187/E-188/E-74: gas detector, static prevention, and electrostatic spray equipment split by visual/domain cues
E-3/E-36/E-65/E-66/E-80: venue, forestry, agriculture, quarry, and shipbuilding electrical contexts separated
E-4/E-76: arc welding guides separated from generic hot-work/fire defaults
```

## Codex Manual Batch 010

Batch 010 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-010.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-010.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 87
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 1
SR link candidates needing review 38
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
E-85/E-94/E-96/E-97: broad fire/electrical defaults -> electrical installation, machine controlgear, emergency-stop, and petrochemical ex-proof power-system profiles
M-10/M-14: generic chemical/electrical drafts -> sharp-edge and hand-knife cut-prevention boundaries
M-103/M-107/M-109/M-111/M-113/M-146/M-150: pressure, pneumatic, NDT, welding, repair, aging-equipment, and inert-gas test profiles separated from generic hot-work/fire
M-124/M-128/M-13/M-133/M-134/M-135/M-142/M-155: machine-specific guarding and operation boundaries strengthened with visual equipment triggers
M-114/M-121/M-131: diagnostic/analysis Guides kept exclusive and linked only to conservative machine-defect review candidates
M-139/M-153/M-154: slip measurement, wood-panel stacking, and GRP tank chemical/static/confined-space contexts split into distinct profiles
```

## Codex Manual Batch 011

Batch 011 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-011.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-011.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 178
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 1
SR link candidates needing review 51
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
M-159/M-165/M-166/M-188: farm/vehicle defaults -> excavator, tractor, ATV, and agricultural-machine operation boundaries
M-16/M-168: grain mill and paper-machine Guides split into machine, dust, access, roll-nip, and confined-space profiles
M-169/M-176/M-178/M-179/M-181/M-183/M-25/M-27: saw/cutting Guides separated by actual equipment and visual guard cues
M-171/M-182/M-187/M-22/M-4: lift, press brake, injection molding, metal shearing, and multipurpose metalworker Guides mapped to machinery/lifting/press guarding
M-184/M-191/M-192: technical PWHT/MTTFd/SRP-CS design documents kept exclusive to prevent generic field-procedure leakage
M-193/M-20/M-21/M-37/M-39: printing press, lathe emery cloth, metalworking-fluid, noise-assessment, and ergonomics boundaries corrected
```

## Codex Manual Batch 012

Batch 012 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-012.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-012.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 158
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 84
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
M-47/M-48/M-49: generic chemical/electrical drafts -> woodshop sawdust/fire, workplace transport road, and loading/unloading dock/cargo boundaries
M-5/M-56/M-57/M-58/M-7/M-8: broad hot-work defaults -> work-equipment guarding, injection/extrusion/blow/thermoforming, and window-machine interlock profiles
M-51/M-62/M-73/M-75: workplace, woodworking, food/beverage, and pneumatic noise Guides normalized under noise-control profiles with SR-NOISE candidates
M-52/M-6/M-76/M-9: chainsaw, circular-saw bench, powered hand planer, and metal circular saw grounded in visible blade/guard/kickback/push-stick cues
M-53/M-67/M-74/M-77: plastics fume, manual arc welding, stainless welding fume, and automotive spray painting mapped to ventilation/PPE/fire-explosion boundaries
M-69/M-70/M-71/M-82/M-89/M-90: pressure-vessel, sling/wire-rope, thermoplastic tank, tower-crane installation/access, and hoist wire-rope Guides kept as exclusive technical/equipment boundaries
```

## Codex Manual Batch 013

Batch 013 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-013.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-013.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 142
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 80
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
M-91/M-92/M-93/M-94: tower-crane support, mobile lifting table, stacker, and round-sling Guides separated into crane, lifting-table, stacker, and rigging boundaries
M-96/M-98/M-99/O-2: lathe, drill, boring-machine, and bolt/nut Guides grounded in machine guarding or fastening technical profiles
P-79/C-73/C-C-21/C-C-24: M-HAZOP, process-hazard revalidation, risk-priority, and process-safety-culture Guides kept as management/risk-assessment profiles
P-56/C-05/C-06/C-07: cellular-plastic storage, construction rush work, tile work, and sheet waterproofing mapped to storage/fire/night-work/fall/electric/chemical cues
C-C-1/C-C-10/C-C-11/C-C-13/C-C-17/C-C-18/C-C-19: tank cleaning, venting, PRV, thermal-expansion valve, pressure test, flare, and rupture-disk Guides kept as exclusive pressure/chemical equipment boundaries
C-C-12/C-C-14/C-C-15/C-C-20/C-C-22/C-C-23: P&ID/PFD, piping/material selection, PVC fire-explosion, and RBI Guides separated into technical document/equipment profiles
```

## Codex Manual Batch 014

Batch 014 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-014.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-014.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 138
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 7
SR link candidates needing review 64
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
C-C-25/C-C-26/C-C-31/C-C-44: batch/fuel-gas/chemical-process operation Guides corrected into process-operation, inerting, gas detection, static-control, and abnormal-reaction boundaries
C-C-28/C-C-3/C-C-4: oxidizer, water-reactive/flammable solid, and ethylene-oxide Guides assigned exclusive chemical storage/equipment/fire-explosion profiles
C-C-30/C-C-32/C-C-33/C-C-5: runaway reaction, flame arrester, drying equipment, and safety-valve test Guides grounded in pressure-relief, venting, burner, PRV, and test-equipment cues
C-C-34/C-C-49: fire brigade and safe-work-permit Guides separated into emergency-response/SCBA and hot-work/confined-space permit boundaries
C-C-27/C-C-35/C-C-36/C-C-37/C-C-38/C-C-39/C-C-40/C-C-41/C-C-42/C-C-43/C-C-45/C-C-46/C-C-47/C-C-48/C-C-50/C-C-51: process safety KPI, risk-analysis, human-error, CEI, leak-modeling, maintenance, contractor, and training documents kept domain_specific with conservative SR candidates
```

## Codex Manual Batch 015

Batch 015 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-015.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-015.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 139
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 4
SR link candidates needing review 81
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
C-C-52/C-C-53/C-C-59/C-C-77: PSSR, MOC, SOP, and PSM operational-discipline Guides corrected into domain_specific management/procedure profiles instead of broad electrical defaults
C-C-55/C-C-69/C-C-74: emergency-plan Guides grounded in alarm, evacuation, control-center, fire/explosion/toxic-release response, and emergency equipment cues
C-C-56/C-C-58/C-C-7: consequence, worst/alternative scenario, and QRA Guides kept as analysis documents with conservative SR candidates
C-C-60/C-C-70: loss-mitigation and hazardous-space Guides strengthened with gas detector, ventilation, alarm, SCBA, toxic-gas, and evacuation boundaries
C-C-65/C-C-78: semiconductor specialty-gas and refinery-operation Guides assigned exclusive process/equipment boundaries to prevent generic fire/electrical overexposure
C-C-75/C-C-76/C-C-79: corrosion-risk, integrity-monitoring, and CCD Guides normalized under corrosion/damage-mechanism/IOW profiles
```

## Codex Manual Batch 016

Batch 016 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-016.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-016.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 148
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 3
SR link candidates needing review 66
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
C-C-8/C-C-90/C-C-94: flange/gasket, safety-valve, and rupture-disc Guides grounded in pressure equipment, leakage, set-pressure, relief-capacity, and maintenance cues
C-C-83/D-1/D-16/D-12: deflagration vent, low-pressure venting, explosion suppression, and dust explosion Guides assigned exclusive explosion-protection boundaries
C-C-84/C-C-85/C-C-87: VOC oxidizer, inert-gas purge, and gas detector Guides strengthened with LEL, flame arrester, purge, calibration, alarm, and emergency-power cues
C-C-88/C-C-89/C-C-93/D-21/D-30/D-32: dike, fireproofing, atmospheric tank, foam fire protection, pressure-vessel heat protection, and control-room design separated from generic fire defaults
D-13/D-2/D-3/D-20/D-24/D-28: chlorine storage, activated-carbon adsorption, solvent extraction, rubber lining, safe design, and small-workplace fire/explosion mapped to chemical equipment/emergency protection
C-C-80/C-C-81/C-C-86/C-C-92/D-22: M&A, Dow/Mond, integrated form, self-audit, and explosion-limit calculation kept as document/analysis profiles with conservative SR candidates
```

## Codex Manual Batch 017

Batch 017 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-017.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-017.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 175
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 6
SR link candidates needing review 79
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
D-33/D-4/D-42/D-43/P-1/P-112: gas/vapor, isolation, hydrogen vent, collector, pneumatic conveying, and magnesium dust explosion Guides separated by explosion-protection devices and static/grounding cues
D-34/D-38/K-1/P-109: ammonia, sulfuric/oleum, hazardous chemical, and organic peroxide storage Guides grounded in substance-specific tank, labeling, separation, corrosion, emergency, and containment cues
D-37/D-5/D-52/D-62/D-64: process vessel, system design, piping, check-valve, and centrifugal-pump Guides corrected from broad defaults into process-design/equipment profiles with conservative SR candidates where legal directness is weak
D-55/D-56: liquid chemical loading/unloading and blind installation/removal mapped to trench/sump/curb, spill control, isolation, purge, permit, and tag cues
D-58/D-7: MCFC and fuel-cell Guides separated into hydrogen/gas, electrical-output, shutdown, ventilation, and ex-proof boundaries
D-60/D-63/D-68: flare knockout drum, safety-valve discharge piping, and breaking-pin device grounded in relief/discharge/pressure-protection boundaries
D-46/P-104/P-11/P-114: chemical-plant fire prevention, VOC treatment, EPS pentane fire prevention, and static measurement/control strengthened with ignition, LEL, ventilation, grounding, and treatment-equipment cues
```

## Codex Manual Batch 018

Batch 018 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-018.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-018.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 189
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 13
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
P-115/P-116/P-117/P-12: petrochemical firefighting, process alarm/SIS management, chemical protective clothing, and electronics special-gas Guides separated from broad chemical/electrical defaults.
P-121/P-122/P-123/P-126/P-128: air-separation, semiconductor bulk gas, industrial furnace, carbon-disulfide drum, and metal-dust Guides grounded in oxygen/gas, burner, dip-leg, grounding, dust-collector, and explosion-protection cues.
P-131/P-132/P-133/P-134: dust explosion, runaway reaction, interlock management, and facility layout mapped to explosion venting, reactor safeguards, logic/P&ID, and safety-distance documents.
P-137/P-138/P-139/P-148/P-149/P-153: oxygen detector/enriched atmosphere, gas-cylinder emergency, wastewater sump, gas-cabinet storage, and toxic gas Guides corrected with detector, ventilation, CRV/SCBA, ESOV/RFO, PPE, and eyewash cues.
P-143/P-144/P-156/P-158/P-159/P-16/P-160: molten-metal furnace, agricultural food dust, sludge carbonization, transfer pipeline, oxygen/inert vent, semiconductor HPM fire protection, and nitrocellulose storage separated into equipment-specific domain profiles.
```

## Codex Manual Batch 019

Batch 019 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-019.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-019.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 244
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 5
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
P-161/P-162/P-164/P-165/P-167/P-17: waste solvent, water spray, pilot plant, atmospheric tank, chemical sampling, and dip-tank Guides separated from broad welding/fire defaults.
P-170/P-171/P-173/P-178/P-179: oxygen piping, automatic burner control, hydrogen equipment, hydrogen PSA, and mixed-gas explosibility calculation grounded in oxygen/hydrogen/burner/control/document cues.
P-18/P-180/P-2/P-21/P-22: flammable-liquid leak, waste-plastic pyrolysis, tank overfill prevention, hydrofluoric acid, and dry-cleaning Guides strengthened with detector, ventilation, level, PPE, and process-equipment cues.
P-25/P-26/P-27/P-28/P-3: fire-wall/barrier, flammable-liquid mixing, waste-solvent recovery, ship-vessel gas hazard, and small-tank cleaning mapped to fire barrier, explosion vent, distiller, tankship, inerting, and gas measurement cues.
P-30/P-31/P-32/P-33/P-34/P-35/P-36/P-38/P-39: hydrogen station, tank vehicle, oxygen supply, dry chlorine piping, drum storage, hot work, pulp/paper, exothermic reaction, and dangerous-goods transport boundaries corrected with equipment-specific triggers.
```

## Codex Manual Batch 020

Batch 020 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-020.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-020.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 226
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 2
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
P-4/P-41/P-42/P-43/P-44/P-46: factory building risk, dust deflagration vent, ethanol distillation, fire-water pump, toy fireworks, and cleanroom Guides separated from broad chemical/fire defaults.
P-47/P-48/P-49/P-5/P-50/P-52/P-53/P-54/P-55: hydrogen fuel-cell, cylinder PRD, dust process selection, printing solvent, hazardous waste, isolation, runaway reaction, acetylene, and sulfur process boundaries grounded in equipment/procedure cues.
P-57/P-58/P-59/P-6/P-60/P-62/P-63/P-64/P-65: fire door/window, hazmat response, acid tank, spray booth, ammonia refrigeration, organic paint, HVAC, iron sulfide, and rupture-disc sizing profiles corrected with visible devices and documents.
P-68/P-7/P-72/P-74/P-75/P-76: aluminum dust, portable flammable liquid containers, outdoor fireworks, packaged dangerous-goods warehouse, flammable liquid handling, and chemical laboratory Guides assigned usage-boundary cues for runtime exclusion/penalty.
```

## Codex Manual Batch 021

Batch 021 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-021.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-021.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 195
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 25
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
P-77/C-103/C-108/C-11/C-113/C-114: remote shutoff, excavation instrumentation, hot work, temporary stairs, seasonal construction, and dump/cargo truck boundaries separated from broad fire/general construction defaults.
C-14/C-16/C-17/C-18/C-2/C-21/C-22: confined waterproofing, plastering, light steel ceiling, design-for-safety, barge construction, suspension bridge, and cable-stayed bridge cues grounded in visible equipment/documents.
C-25/C-26/C-27/C-29/C-36/C-41/C-45: temporary equipment performance, falling-object net/shelf/vertical net, bridge formwork cart, PSC bridge, and NATM tunnel profiles corrected for exclusive/domain-specific runtime guard use.
C-47/C-48/C-49/C-50/C-52/C-53/C-54/C-55/C-56/C-57: demolition, construction machinery, safety harness, asphalt paving, night construction, PC assembly, tower deep foundation, curtain wall, remodeling, and stonework Guide boundaries added with candidate-only SR links.
```

## Codex Manual Batch 022

Batch 022 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-022.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-022.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 213
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 24
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
C-59/C-60/C-61/C-62/C-64/C-66: roof work, top-down basement, Shield-TBM, gondola, masonry, and interior construction separated from broad construction/fire defaults.
C-68/C-70/C-71/C-74/C-75/C-77: reinforced earth wall, cold-storage insulation fire prevention, pile driving, MEWP, landscaping/tree planting, and suspension-bridge pylon profiles grounded in equipment and work-area cues.
C-78/C-79/C-80/C-81/C-82/C-83/C-84/C-85: retaining wall, high-rise construction, steel arch bridge, front jacking, offshore RCD, PCT girder, truss girder, and truck-mounted crane boundaries added with candidate-only SR links.
C-88/C-89/C-91/C-93/C-94/C-96/C-98/D-27/D-61/D-C-1: NTR tunnel, immersed tunnel, high-rise fire, well foundation, Rahmen bridge, temporary-structure design change, tower construction, hydrogen storage, flare backfire prevention, and earth-retaining technical support profiles corrected.
```

## Codex Manual Batch 023

Batch 023 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-023.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-023.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 153
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 75
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
D-C-11/D-C-12/D-C-13/D-C-14/D-C-15: excavation/earthwork, assembled steel post, exterior wall painting, elevator shaft platform, and concrete/formwork technical-support boundaries grounded in work-area and temporary-structure cues.
D-C-3/D-C-4/D-C-5/D-C-6/D-C-8/D-C-9: steel erection, excavator, excavation slope, blasting, gang/system/slip form, and formwork/shoring profiles corrected with SR candidates from construction-specific registries.
A-1/A-10/A-11: metal workplace measurement Guides separated from field improvement procedures and kept as sampling/analysis document profiles.
A-100~A-118 subset: organic solvent/toxic substance workplace measurement Guides constrained to pump, adsorption tube, GC/FID, AAS, hood, PPE, and lab-analysis evidence so they do not over-rank as generic chemical corrective procedures.
```

## Codex Manual Batch 024

Batch 024 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-024.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-024.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 118
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 118
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
A-119/A-120/A-122/A-145: glycol ether and glycol measurement Guides constrained to adsorption-tube, GC/FID, desorption, calibration, and lab-analysis cues.
A-12/A-13: tin and zirconium measurement Guides separated from field metal-control procedures and kept as membrane-filter/AAS/acid-digestion profiles.
A-121/A-123~A-131/A-133/A-135~A-137/A-139/A-140/A-144: acrylate, acetate, ether, alcohol, and allyl glycidyl ether measurement Guides bounded by charcoal/Tenax tubes, GC/FID, volatile/flammable lab handling, hood, and PPE evidence.
A-132/A-134/A-138/A-141/A-142/A-143/A-146: amine/alkanolamine measurement Guides bounded by coated sorbent tubes, HPLC or GC/FID, derivatization/neutralization, irritation/corrosion cues, hood, and PPE evidence.
```

## Codex Manual Batch 025

Batch 025 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-025.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-025.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 120
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 1
SR link candidates needing review 120
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
A-147/A-148/A-149/A-150/A-163/A-164/A-165/A-166/A-167/A-168/A-170/A-171/A-172: amine, epoxy, solvent, chlorinated organic, phthalate, and aromatic amine measurement Guides constrained to sorbent tube, GC/HPLC/LC, calibration, hood, and PPE analysis cues.
A-151/A-152/A-153/A-154/A-155/A-156/A-157/A-169: acid, oxidizer, halogen acid gas, caustic alkali, and TMAH measurement Guides bounded by IC/AAS/ICP/UV analysis, filter/tube media, and lab-preprocessing cues; eyewash/leak-response overlinking kept low-confidence and needs_review.
A-158/A-159/A-160: cyanide measurement Guides kept as high-toxicity sampling/analysis profiles, not asserted field corrective-action bases.
A-16/A-17/A-18/A-161/A-162: metal and particulate elemental-carbon measurement Guides separated from generic dust/metal-control procedures and tied to filter sampling, acid digestion, AAS, quartz filter, and thermal-optical analyzer cues.
A-180: broad work-environment measurement program Guide marked domain_specific so it penalizes unrelated field photos rather than excluding all non-lab contexts.
```

## Codex Manual Batch 026

Batch 026 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-026.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-026.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 130
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 130
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
A-181/A-4/A-43: indium, magnesium, and barium Guides kept as filter/cyclone sampling plus ICP/AAS metal-analysis profiles, not generic metal-control procedures.
A-182~A-187: acrylic acid, hydrogen chloride, phosphoric acid, nitric acid, acetic acid, and trichloroacetic acid Guides constrained to acid/corrosive measurement, IC/HPLC/GC, hood, and PPE analysis cues.
A-190~A-193: passive sampler Guides require passive sampler and GC/FID analysis context before affecting top procedure ranking.
A-21/A-23/A-25~A-34/A-36~A-39/A-41/A-42: PCB, chlorinated/halogenated solvent, freon, and glycol-ether acetate Guides bounded by adsorption media, GC/FID or GC/ECD, calibration, desorption efficiency, and lab-document cues.
```

## Codex Manual Batch 027

Batch 027 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-027.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-027.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 150
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 150
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
A-45/A-47/A-50/A-51/A-52/A-6/A-8: antimony, tungsten, organotin, arsenic/arsine, platinum, and selenium Guides kept as metal/metalloid measurement profiles requiring filter/cassette/tube and AAS/ICP/HPLC cues.
A-53/A-54/A-55/A-58/A-59: metalworking fluid, glutaraldehyde, and acetaldehyde Guides constrained to PTFE/DNPH media, extraction, HPLC or GC-NPD, hood, and PPE analysis cues.
A-60/A-61/A-62/A-80/A-81/A-82/A-87: carcinogenic/toxic aromatic amine, hydrazine, nitroaromatic, pentachlorophenol, and dihydroxybenzene Guides preserve toxic signals but do not become asserted corrective-action bases.
A-67/A-68/A-86: nitroglycerin, ethylene glycol dinitrate, and nitromethane fire/explosion cues are low-confidence SR candidates because the documents are measurement methods.
A-71/A-73/A-74/A-75/A-78/A-83/A-84/A-85: solvent, phenol/cresol, isocyanate, epoxide, pyridine, and epichlorohydrin Guides require adsorption media and GC/HPLC analysis context before ranking.
```

## Codex Manual Batch 028

Batch 028 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-028.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-028.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 145
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 41
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
A-89/A-9/A-92/A-93/A-94/A-95/A-97/A-98: final A-series measurement Guides constrained to filter/tube media, GC/HPLC/AAS, calibration, and lab-analysis cues.
E-G-1/E-G-4: musculoskeletal prevention Guides mapped to ergonomic burden work, hazard-factor survey, work-environment improvement, and posture/heavy-lifting controls.
E-G-10~E-G-16/E-G-8: diving, decompression, breathing gas, chamber, surface-supplied diving, and underwater cutting Guides made exclusive to diving/pressure/chamber context.
E-G-17/E-G-18/E-G-19/E-G-20/E-G-21/E-G-22/E-G-23: reproductive toxicants, confined space, respirator, asbestos, ventilation, heat, and vibration Guides separated into their own domain profiles with direct but non-asserted SR candidates.
E-G-2/E-G-5: job-stress Guides expose a taxonomy/SR gap, so their secondary ergonomic feature and management SR links remain weak `needs_review` candidates.
E-G-3/E-G-6/E-G-7: VDT office, office air quality, and waste-incineration facility Guides bounded by office/air-quality or incinerator ash/maintenance context.
```

## Codex Manual Batch 029

Batch 029 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-029.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-029.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 110
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 0
SR link candidates needing review 45
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
E-G-9: diving emergency gas cylinder Guide made exclusive to diving emergency cylinder inspection, not generic gas-cylinder handling.
E-H-1~E-H-4: workplace measurement/analysis support Guides kept as sampling-analysis protocols with weak `needs_review` SR links.
E-M-1/E-M-2: hearing conservation and noise-induced hearing-loss management mapped to noise program, hearing protection, and medical follow-up SR candidates.
E-M-3/E-M-5: healthcare needlestick and formaldehyde exposure Guides separated into sharps/blood exposure and healthcare chemical exposure profiles.
E-M-6~E-M-8/E-T-1~E-T-9: biological monitoring and toxicology/animal-test protocols separated from workplace corrective procedures despite chemical hazard wording.
H-100~H-104/H-109/H-111/H-112/H-113: PCBs waste, lab QC, chemical management, refrigeration machine-room, dry-cleaning, and named chemical worker-health Guides tied to explicit workplace management contexts.
```

## Codex Manual Batch 030

Batch 030 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-030.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-030.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 148
visual trigger candidates 60
guides with no SR candidate 0
feature candidates needing review 2
SR link candidates needing review 30
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
H-114/H-119/H-120/H-121/H-124/H-125/H-126/H-132/H-133/H-134/H-135/H-136/H-137: named chemical worker-health Guides bounded to explicit chemical exposure, biological monitoring, medical follow-up, and control-program contexts.
H-118/H-122: grain/flour dust and wood-dust health-management Guides tied to dust source, local exhaust, respirator, housekeeping, and worker-health cues.
H-116/H-117/H-123: nitrogen dioxide, hydrogen sulfide, and hydrofluoric-acid emergency Guides made exclusive to toxic/corrosive gas response, detection, SCBA, evacuation, decontamination, and first-aid cues.
H-127/H-129/H-130/H-138: radon, spirometry, contact dermatitis, and specimen-contamination Guides separated into radiation/health-test/dermatitis/biosafety profiles instead of generic chemical response.
H-141/H-142/H-145/H-148/H-149/H-15/H-152: biological exposure indicator analysis Guides kept as lab-analysis protocols with weak `needs_review` SR links.
H-147: special-management-substance Guide kept as a domain_specific chemical-control program rather than a single-material exposure Guide.
```

## Codex Manual Batch 031

Batch 031 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-031.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-031.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 148
visual trigger candidates 60
guides with no SR candidate 2
feature candidates needing review 16
SR link candidates needing review 31
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
H-155: hot-work default corrected to radiation nondestructive testing, radiation management area, shielding, dosimeter, and collimator context.
H-158: bounded to SDS/MSDS education, warning labels, and chemical-handling training.
H-16/H-17: kept as biological exposure indicator analysis protocols, not field emergency response Guides.
H-160/H-177: separated into hearing-protection and hand-arm vibration tool management profiles.
H-171/H-180~H-184: TMAH and named acute-poisoning clinical response Guides kept exclusive to visible/named chemical emergency context.
H-172/H-173/H-170/H-192/H-193: asphalt fume, dye dust, indium/ITO dust, smelting, and asbestos removal boundaries separated from generic construction/chemical defaults.
H-191: livestock culling/burial health Guide linked to biohazard plus burial excavation context.
H-162/H-163/H-188~H-190/H-194: health-management and assessment Guides kept weak/no-SR where the registry has no direct legal SR, to avoid overclaiming.
```

## Codex Manual Batch 032

Batch 032 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-032.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-032.md
```

Counts:

```text
guides reviewed 30
feature candidates 60
SR link candidates 104
visual trigger candidates 60
guides with no SR candidate 5
feature candidates needing review 38
SR link candidates needing review 39
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
H-197/H-220: bounded to workplace tuberculosis and emerging airborne infectious disease response, not generic mask photos.
H-199: asbestos removal supervision separated from generic demolition and tied to 감리인, 석면농도, 폐석면, 작업중지/시정 cues.
H-209/H-21: kept as biological exposure indicator analysis protocols, not field exposure-control Guides.
H-207/H-213: lead and 1,2-dichloropropane worker health-management Guides connected to named chemical/PPE/SR candidates.
H-212: call-center infection office-environment profile tied to cubicles, HVAC, background noise, and hygiene cues.
H-25/H-26: cleaner and cooking worker Guides mapped to ergonomic, slip, heat, cleaning, and kitchen work context.
H-201/H-203/H-204/H-211/H-37: management or psychosocial Guides kept no-SR where registry coverage is absent.
```

## Codex Manual Batch 033

Batch 033 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-033.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-033.md
```

Counts:

```text
guides reviewed 30
feature candidates 62
SR link candidates 85
visual trigger candidates 60
guides with no SR candidate 9
feature candidates needing review 40
SR link candidates needing review 16
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
H-42/H-51: protective gloves and skin sensitizer Guides bounded to chemical skin-exposure context, not generic glove photos.
H-53: hospital anesthetic gas profile requires operating room, anesthesia machine, scavenging, and ventilation cues.
H-62/H-78: ionizing radiation worker management separated from UV sterilizer exposure evaluation; UV remains weak because taxonomy/SR coverage is thin.
H-70: asbestos removal kept exclusive to asbestos, HEPA, negative pressure, glove bag, warning sign, PPE, and waste cues.
H-72/H-74/H-81/H-83: analytical chemistry and toxicology lab protocols kept no-SR to avoid converting test methods into field corrective actions.
H-4/H-43/H-47/H-50/H-75: health-exam, fit-for-work, long-working-hour, and work-environment evaluation Guides kept weak/no-SR where registry coverage is indirect.
```

## Codex Manual Batch 034

Batch 034 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-034.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-034.md
```

Counts:

```text
guides reviewed 30
feature candidates 63
SR link candidates 33
visual trigger candidates 60
guides with no SR candidate 21
feature candidates needing review 55
SR link candidates needing review 13
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
H-92: electroplating profile strengthened around plating bath, acid pickling, cyanide compounds, local exhaust, PPE, and emergency washing cues.
H-93: healthcare airborne infectious disease Guide requires hospital, isolation ward, vaccination, exposure follow-up, or return-to-work infection-management context.
H-94: livestock epidemic disinfection keeps both biological and disinfectant chemical exposure cues, but requires foot-and-mouth/livestock disinfection context.
H-99/T-* /W-10: biological exposure indicator, toxicology, animal test, and pathology protocols are bounded as laboratory/test-method Guides, not field corrective-action Guides.
T-9: asbestos body/fiber in biological samples separated from asbestos removal work.
```

## Codex Manual Batch 035

Batch 035 has been upgraded from generated draft to source-JSON manual review.

Output:

```text
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-035.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-batch-035.md
```

Counts:

```text
guides reviewed 18
feature candidates 38
SR link candidates 42
visual trigger candidates 36
guides with no SR candidate 5
feature candidates needing review 23
SR link candidates needing review 15
visual trigger candidates needing review 0
asserted mapping updates 0
external API calls 0
```

Manual correction examples:

```text
W-15/W-16/W-2/W-6: SDS, GHS, reliability evaluation, and chemical hazard/risk assessment kept as document profiles, not direct field corrective-action Guides.
W-17: cold-work management bounded to equivalent cooling temperature, cold PPE, hypothermia, frostbite, rest, and warm shelter cues.
W-19: pesticide work requires pesticide, fumigation, pesticide PPE, warning sign, or restricted-entry context before chemical/confined-space candidates apply.
W-20/W-24/W-25: nanomaterial handling, airborne nanomaterial exposure assessment, and CNT concentration management separated.
W-21/W-3: BSL-3 and BSL-1/2 lab biosafety separated as exclusive lab profiles.
W-26: institutional food-service ventilation requires cafeteria kitchen hood, duct, exhaust fan, airflow, or hood face velocity cues.
```

## Next Handoff

1. Run a global audit/normalization pass over `manual-enrichment-domain-guard-index.json` and batches 001-035.
2. Review weak areas first: 76 Guides with no SR candidate, 240 feature candidates needing review, 1,541 SR candidates needing review, 10 visual triggers needing review.
3. Normalize repeated lab/test-method profiles and taxonomy-gap notes before import preview.
4. Flatten candidates into an import preview, keeping asserted mapping updates at 0.
5. Run OHS 240 actual replay and v10 synthetic smoke before enabling the candidate data in runtime scoring.
6. If external API use is approved later, run an LLM pilot and compare it against the manual batches rather than replacing them blindly.

## Broad SR Policy + Import Preview Implementation (2026-05-09)

Implemented the bridge between the 1,038 manual domain-guard batches and OHS serving. No asserted mapping table was updated.

Outputs:

```text
koshaontology/pipe-B/scripts/build_manual_domain_import_preview.py
koshaontology/pipe-B/scripts/export_manual_domain_serving_artifacts.py
koshaontology/pipe-B/data/manual-enrichment-domain-guard-import-preview.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-import-preview.md
koshaontology/pipe-B/data/manual-enrichment-domain-guard-review-queues.json
koshaontology/pipe-B/data/manual-enrichment-domain-guard-review-queues.md
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/broad_sr_policy.json
OHS/backend/app/services/broad_sr_policy.py
```

Import preview summary:

```text
batches 35
unique Guides 1,038
feature rows 2,083 / serving eligible 1,839
SR rows 4,317 / serving eligible 2,759
visual rows 2,076 / serving eligible 2,066
asserted mapping updates 0
missing required fields 0
invalid review_status 0
invalid SR id 0
non-catalog feature code 0
entity FK violation 0
```

Important import note: `guide_sr_link_candidates` has two mergeable duplicate unique keys (`A-67-2018`, `A-68-2018` with `SR-FIRE_EXPLOSION-015`). A real DB import should pre-aggregate/merge evidence for same `(entity_type, entity_id, sr_id, method)` before insert. Use replace-per-method import, not `GREATEST(confidence)`, so confidence demotions and `needs_review` corrections survive.

Review queues:

```text
operational-looking no-SR Guides 17
  SR 보강 3
  taxonomy_gap 6
  domain_guard_only 1
  document_only 7
exclusive broad-feature-only Guides 333
```

OHS runtime changes:

```text
review_status serving gate: candidate/asserted only
broad SR policy artifact loaded from OHS/backend/app/data/broad_sr_policy.json
broad SR cannot create standard procedure/fallback by itself
get_standard_guides() and get_immediate_checklist_items() now receive direct_sr_ids
Guide domain profile evaluation reads OHS/backend/app/data/guide_domain_profiles.json
legacy hardcoded watch rules remain as fallback/override
```

Validation:

```text
Python compile: OK
OHS backend compileall: OK
frontend npm run build: OK
v10 synthetic smoke: SHE recall 100.0%, FN 0, FP 0
actual response 240 replay: status changed 0, negative_false_positive 10, positive_missed 2, ambiguous_over_promoted 5
A-G-18 top procedure: 33 -> 3 vs pipeb1038 comparison; residual 3 are all 항만 하역업
watch Guide top procedure total: 57 -> 39 (31.6% reduction)
```

New reports:

```text
pictures-json/reports/synthetic_observations_v10_domain_guard_broad_sr_policy_report.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy.md
pictures-json/reports/actual_response_samples_v1_v10_domain_guard1_vs_pipeb1038_broad_sr_policy_watch_summary.md
```
## Synthetic v1~v10 Guide Recommendation Usage Profile Evaluation (2026-05-09)

This pass made `synthetic_observations_v1~v10.jsonl` the main Guide recommendation quality set. The old SHE/SR synthetic evaluator remains unchanged; the new Guide-specific evaluator is:

```text
OHS/backend/scripts/evaluate_synthetic_guide_recommendations.py
```

New Pipe-B/OHS materialization:

```text
koshaontology/pipe-B/scripts/build_manual_guide_usage_profiles.py
koshaontology/pipe-B/data/manual-guide-usage-profiles.json
koshaontology/pipe-B/data/manual-guide-usage-profiles.md
OHS/backend/app/data/guide_domain_profiles.json
```

`guide_domain_profiles.json` now carries recommendation-boundary fields for 1,038 Guides:

```text
usage_summary
intended_workplaces
intended_tasks
observable_required_cues
negative_boundaries
procedure_role
primary_work_process_ids
primary_work_process_titles
usage_profile_evidence
usage_profile_review_status
```

Runtime changes:

```text
- manual 1,038 Guide profiles are preferred over old hardcoded term rules
- broad SRs remain secondary-only
- broad/generic features cannot create top standard procedures alone
- industry alignment alone is not a Guide-specific signal
- domain_mismatch Guides are excluded from standard_procedure candidates
- measurement/test/health/risk-method/document Guides require explicit method context
- WorkProcess steps are ranked by profile primary WP ids, SR support, and context terms instead of first-8 order
```

Synthetic Guide evaluation report:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile1_20260509_230048.json
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile1_20260509_230048.md
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile1_20260509_230048.csv
```

Result:

```text
total samples 2,360
legacy obvious top Guide mismatch 1,149
current obvious top Guide mismatch 533
reduction 616 / 53.61%
current failure queues:
  broad_sr_overreach 1
  industry_boundary_gap 476
  missing_usage_profile 342
  workprocess_mismatch 56
```

Regression reports:

```text
pictures-json/reports/synthetic_observations_v10_usage_profile1_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile1_vs_pipeb1038.md
```

Regression result:

```text
v10 synthetic SHE recall 100.0%, false negative 0, false positive 0
actual response 240 status changed 0
negative_false_positive 10
positive_missed 2
ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

Remaining structural queue:

```text
1. Reclassify general/document-like Guides that still behave as field procedures: C-18, C-C-92, A-G-15, G-32, C-C-16, etc.
2. Add domain-specific visual/usage boundaries for electrical substation, warehouse/steel stacking, emergency-plan, chemical health-management, and fall-protection Guides that still rise via asserted WP-SR/CI-SR.
3. Split positive missing_usage_profile cases into true taxonomy gaps vs Guide usage profile gaps.
4. Improve WorkProcess matching for the 56 workprocess_mismatch cases.
5. Treat negative safe cases with valid work context but no observable violation as no standard procedure unless a Guide-specific violation cue exists.
```

## Usage Profile Attention Correction v2 (2026-05-09)

Implemented a first structural correction pass against the usage_profile1 attention queues.

Changed files/scripts:

```text
koshaontology/pipe-B/scripts/apply_usage_profile_attention_corrections.py
koshaontology/pipe-B/scripts/build_manual_guide_usage_profiles.py
OHS/backend/app/services/guide_domain_profile.py
OHS/backend/app/services/guide_recommendation_service.py
OHS/backend/app/data/guide_domain_profiles.json
```

Corrected 8 high-impact Guide boundaries in the source manual batches:

```text
B-E-3-2025  변전실 양압유지
C-C-16-2026 세안설비/비상샤워
A-G-1-2025  추락방호망
B-M-32-2026 철강제품 적재
G-32-2016   임산부 근로자 유해위험요인
A-G-15-2026 비상조치계획
C-C-92-2026 PSM 자체감사
C-18-2015   건설공사 안전보건 설계
```

Runtime policy change:

```text
- manual 1,038 Guide profiles are evaluated before legacy hardcoded rules
- legacy hardcoded watch rules remain fallback only when manual profile is general
- ELECTRICAL_WORK is broad/generic for domain-rule matching
- exclusive Guides cannot gain usage-profile score from feature-only hits
- management_program is treated like a reference role unless explicit context is present
```

Validation:

```text
synthetic Guide v1~v10 total 2,360
legacy obvious top Guide mismatch 1,150
usage_profile2 obvious top Guide mismatch 361
reduction 789 / 68.61%
current failure queues:
  broad_sr_overreach 1
  industry_boundary_gap 313
  missing_usage_profile 367
  workprocess_mismatch 47
v10 synthetic smoke: SHE recall 100.0%, FN 0, FP 0
actual response 240: status changed 0, negative_false_positive 10, positive_missed 2, ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

New reports:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile2_20260509_233015.md
pictures-json/reports/synthetic_observations_v10_usage_profile2_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile2_vs_pipeb1038.md
```

Next structural queue:

```text
1. Reduce NO_TOP/missing_usage_profile 367 by separating true no-procedure cases from taxonomy/profile gaps.
2. Continue attention corrections for remaining top overexposed Guides: A-G-12, A-G-9, C-70, H-100, A-R-2, H-187, A-G-14, E-M-4.
3. Fix workprocess_mismatch top set: D-C-7, E-G-22, H-116, M-62.
4. Add a negative safe-case gate so valid work_context without observable violation does not force a standard procedure.
5. Audit profiles whose industry_alignment still contains generic or wrong domains such as `construction`, `healthcare`, `electrical_maintenance`, or `manufacturing`.
```

## Actionable SHE Guide Gate + Usage Profile v11 (2026-05-10)

Implemented the safe-case structural gate from the queue above. The accepted runtime baseline is now `usage_profile11`.

Key runtime decision:

```text
- Standard procedures and immediate checklist items use actionable SHE matches as direct recommendation evidence.
- Non-actionable/context-only SHE matches may still contribute to finding reasoning, but they no longer create Guide procedures by themselves.
- Broad risk-feature alias expansion was tested and rejected because it changed status/penalty boundaries in the actual 240 replay.
- The accepted fix keeps risk/SHE status behavior stable and moves the guard to the Guide recommendation boundary.
```

Evaluation harness fixes kept:

```text
- synthetic Guide evaluator reads `scene_description` as a fallback to `photo_description`.
- expected_corrective_direction is not fed into runtime full_description; it remains scoring/evaluation text only.
- no-top queue analyzer also reads `scene_description`.
```

Validation:

```text
synthetic Guide v1~v10 total 2,360
legacy obvious top Guide mismatch 1,145
usage_profile11 obvious top Guide mismatch 165
reduction 980 / 85.59%
current failure queues:
  broad_sr_overreach 1
  industry_boundary_gap 160
  missing_usage_profile 395
  workprocess_mismatch 4
NO_TOP 395:
  other_taxonomy_gap 141
  chemical_profile_gap 64
  construction_fall_profile_gap 57
  service_sector_taxonomy_gap 49
  machine_profile_gap 43
  burn_heat_profile_gap 25
  material_handling_profile_gap 9
  electrical_profile_gap 7
v10 synthetic smoke: SHE recall 100.0%, FN 0, FP 0
actual response 240: status changed 0, negative_false_positive 10, positive_missed 2, ambiguous_over_promoted 5
backend compileall OK
frontend npm run build OK
```

Accepted reports:

```text
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.md
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.md
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.md
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.md
```

Rejected intermediate attempts:

```text
usage_profile8/9/10 improved some NO_TOP coverage but expanded risk-feature/status behavior.
usage_profile10 reached 197 obvious Guide mismatches, but failed acceptance with actual 240 status changed 15 and v10 SHE FN 1.
Do not solve Guide coverage by broadening hazard_normalizer/hazard_rule_engine unless actual 240 status changed remains 0.
```

Next structural queue:

```text
1. Treat usage_profile11 as the current accepted runtime baseline.
2. Work the NO_TOP 395 queue by adding Guide usage-profile/WorkProcess coverage, not by adding broad risk aliases.
3. Prioritize profile gaps: chemical, construction fall, service-sector taxonomy, machine, burn/heat.
4. Audit remaining general/document Guides that still appear as field procedures, especially `C-C-80-2026`, `G-93-2012`, and other CI-SR fallback-driven cases.
5. Candidate DB import is still pending: pre-aggregate duplicate SR candidates and use replace-per-method, asserted mapping update 0.
```
