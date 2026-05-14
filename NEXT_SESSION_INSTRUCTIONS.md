# 다음 세션 시작 지침

최신 갱신일: 2026-05-14

이 문서는 다른 Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

## 1. 현재 작업 디렉토리

```text
Windows path: C:\project\arch-bot
WSL path: /mnt/c/project/arch-bot
```

현재 기준은 root `arch-bot` monorepo `main` 브랜치다.

```text
branch: main
```

`OHS/`와 `koshaontology/`는 기존 child GitHub repo의 pushed baseline을 root로 snapshot import한 디렉토리다. `legalize-kr/`는 외부 의존 repo로 유지하며 root git에서 추적하지 않는다.

## 2. 먼저 읽을 문서 순서

1. `README.md`
2. `MONOREPO_TRANSITION_PLAN.md`
3. `DATA_GOVERNANCE.md`
4. `repositories.md`
5. `docs/status/evaluation-baseline.md`
6. `docs/architecture/source-provenance.md`
7. `WORKPLAN_LLM_DOMAIN_GUARD.md`
8. `온톨로지_통합구조_및_흐름도.md`
9. `OHS/README.md`
10. `needToChangeCode.md`
11. `koshaontology/pipe-A/status_pipea.md`
12. `koshaontology/pipe-B/status_pipeb.md`
13. `koshaontology/pipe-C/status_pipec.md`

레이어별 세부 구조:

```text
온톨로지_법령레이어_상세도.md
온톨로지_SR레이어_상세도.md
온톨로지_위험상황레이어_상세도.md
온톨로지_가이드레이어_상세도.md
온톨로지_벌칙레이어_상세도.md
```

## 3. Repository / Data Baseline

Snapshot import baseline:

```text
koshaontology imported baseline: 60d025ee873e071faf9c90cc0b1a89b05c4812bd
OHS imported baseline: 7eed7280e1ece9fa7bb32beb182017f5cfa96f5a
root pre-import baseline: 1565a9d14e76b7e3ceb6753354621f5d043c92de
legalize-kr observed upstream: 732764e9e8e116bbc40eb5278207e3a08b31297e
```

Tracked data policy:

```text
kosha-guides/parsed/**: tracked, 1,038 parsed Guide JSON files
kosha-guides/manifest/**: tracked provenance manifest
pictures-json/synthetic_observations_v*.jsonl: tracked
pictures-json/reports-manifest.json: tracked report index
pictures-json/reports/**: ignored local/external report bodies
kosha-guides raw PDFs: ignored external/LFS candidates
```

## 4. Product / Ontology Baseline

서비스 목적:

```text
사업주가 사진을 업로드하면
→ 사진 속 관찰 사실과 시각 단서를 추출하고
→ 위험 특징으로 정규화하고
→ 재사용 가능한 SHE 위험상황 패턴에 매칭하고
→ SR/법령/Guide/CI/PenaltyPath를 조회해
→ 즉시 조치, 표준 개선 절차, 벌칙 3경로, 근거를 보여준다.
```

핵심 온톨로지 기준:

```text
risk:RiskFeature = 위험 지식 공통 추상 계층
haz/agent/ctx = risk:RiskFeature 하위 분류 어휘
she:SituationalHazardPattern = 사진별 사건이 아니라 재사용 가능한 위험상황 패턴
VisualTrigger = 사진에서 보여야 하는 시각 단서
Guide/WorkProcess = 표준 개선 절차 중심
ChecklistItem = 즉시 조치/보조 단서/검색 색인
PenaltyPath = 사업주용 일반 위반 또는 일반 산재 / 사망 / 중대재해 3경로 안내
```

Source/provenance metadata는 별도 layer로 설계한다. `kosha-guides/manifest`를 운영 원천으로 보고, W3C PROV-O/DCAT/DCTERMS/SHACL 조합으로 `source-provenance.ttl`, `source-catalog.ttl`, `source-shapes.ttl`을 생성하는 방향이다. 이 provenance layer는 추천 점수에 직접 쓰지 않고 감사/debug/rebuild에 사용한다.

## 5. OHS 실행

백엔드:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

프론트:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저:

```text
http://127.0.0.1:5173/ohs/
```

주의:

- `OPENAI_API_KEY`가 없으면 실제 이미지/텍스트 분석은 503이 날 수 있다.
- PostgreSQL은 `postgresql://kosha:1229@localhost/kosha` 기준이다.

## 6. 현재 검증 기준선

Accepted runtime baseline: `corpus_gap_guard1`

Previous accepted baseline: `safe_scene_phrase_gate2`

```text
synthetic Stage 2~5 v1~v10 total: 2,360
SHE TP/FN/FP: 1,107 / 909 / 82
SR TP/FN/FP: 1,414 / 270 / 211
Guide mismatch: 22
Stage 2~5 NO_TOP: 85
industry_boundary_gap: 1
workprocess_mismatch: 20
broad_sr_overreach: 1
photo_unmatchable_top_count: 0
photo_unmatchable_suppressed_count: 29
followup_only_retained_count: 15
top_replaced_by_photo_actionable_count: 27
CI no_action: 482
CI context_mismatch: 11
CI broad_sr_only: 14
CI needs_review_used: 0
CI guide_boundary_mismatch: 26
v10 SHE recall: 100.0%
v10 SHE false negative: 0
v10 SHE false positive: 0
v1~v10 SHE smoke recall: 100.0%
v1~v10 SHE smoke false negative: 0
v1~v10 SHE smoke false positive: 67
actual response 240 status changed: 0
negative_false_positive: 10
positive_missed: 2
ambiguous_over_promoted: 5
```

`corpus_gap_guard1` keeps the previous status/penalty/SHE/SR boundary and changes only Stage 5 standard-procedure ranking. It preserves `safe_scene_phrase_gate2` safe-scene blocking and adds compound corpus-gap guards so lab exit checklists, medication preparation/disposal scenes, and recycling glass-shard walking scenes do not get filled by unrelated broad Guides. `safe_scene_phrase_gate2` remains the previous baseline.

Serving ontology validation snapshot:

```text
export script: koshaontology/ontology/scripts/export_serving_snapshot.py
validation script: koshaontology/ontology/scripts/validate_serving_snapshot.py
policy: koshaontology/ontology/serving-policy.ttl
snapshot: koshaontology/ontology/serving-snapshot-corpus_gap_guard1.ttl
shapes: koshaontology/ontology/serving-validation-shapes.ttl
report: koshaontology/ontology/serving-validation-report-corpus_gap_guard1.*
alignment report: koshaontology/ontology/serving-workprocess-alignment-corpus_gap_guard1.*
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 631 / 39 / 368
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 3
accepted photo-actionable role overrides: 10
```

해석: 2026-05-14에 PostgreSQL 기준으로 `kosha-instances.ttl`을 재생성해 base TTL을 1,038 Guide / 9,316 WorkProcess 기준으로 동기화했다. 이전 `primary_workprocess_not_in_base_ttl` 1,220건은 0건으로 해소됐다. 이후 `classification_reason` 근거가 있는 field-action role override 10건은 의도된 `photo_actionable` 예외로 수용했고, 남은 3건은 broad SR attention 1건과 반복 WorkProcess mismatch Guide 2건이다. TTL을 직접 고치지 말고 원천 Guide profile, Pipe-B/PG export, 또는 base TTL 생성 경로를 고친 뒤 재생성한다.

SituationFrame support-only artifact:

```text
classified Stage 3 candidates: 230
runtime SHE approved update: 0
asserted mapping update: 0
child contexts: 178
Guide support candidates v2 historical: 1
Guide support candidates v3: 127
Guide support candidates v4: 139
Guide support candidates v6: 144
Guide support candidates v7: 146
Guide support candidates v8: 152
Guide support candidates v9: 157
Guide support candidates v10: 163
Guide support candidates v11: 168
Guide support candidates v13: 188
Guide support candidates v14: 201
Guide support candidates v15: 206
Guide support candidates v16c: 212
Guide support candidates v17b: 220
Guide support candidates v19: 225
Guide support candidates v20: 227
NO_TOP support covered cases: Stage3 support 136, curated Stage2 support 20
Stage3 profile-alignment aliases: 18 aliases / 7 child contexts / 15 affected support rows
Stage2 support usage gate: 6 context updates / 2 new support rows / 5 trigger-only rows
Stage3 domain support v6: 3 new support rows for spray painting / dry-cleaning solvent / pesticide application
Stage2 service support v7 narrow1: 2 new trigger-backed support-only contexts for display electrical maintenance / floor cleaning machines
Stage2/3 support v8 narrow2: 6 new trigger-backed support-only contexts for X-ray radiation control / blasting / hot-work permit deviation / shipyard/internal welding / soldering / solvent-waste fire
Stage2/3 support v9 narrow4: 5 new trigger-backed support-only contexts for sports-facility slip/trip / powered cardio-equipment maintenance / needlestick-sharps disposal / blood-contaminated waste handling / flammable-chemical smoking
Stage2/3 support v10 narrow2: 6 new trigger-backed support-only contexts for powered food-slicer cleaning / bakery oven-hot-tray burn / small-server electrical overload / elevated welding fall control / automotive tire-wheel service / silica-dust blasting
Stage2/3 support v11 narrow3: 5 new trigger-backed support-only contexts for sharp glass manual handling / lead-paint grinding dust / ice-pick fragment eye exposure / climbing-wall fall surface / chair-stack manual carry
Stage3 gap support v12 narrow4: 13 new trigger-backed support-only contexts for SHE-gap-with-SR cases; first broad trial rejected safe PPE/high-heat/stair/electrical overmatches and EV battery CI-boundary regression
Stage2 taxonomy support v13 narrow5: 7 new trigger-backed support-only contexts for high-pressure waterjet PPE, UV lamp eye PPE, UV coating ozone respirator, formalin contact PPE, cold-room PPE, crematorium hot-surface PPE, and sharp-fragment hand PPE; broad cold-room wording and global short-token tightening trials were rejected
Stage3 SR gap support v14 narrow6b: 13 new trigger-backed support-only contexts for concrete Stage3 SHE-to-SR gaps; first trial rejected short trigger overmatches (`발판 없이`, generic `슬링/인양`, generic `용접 흄`, generic `보호 장갑 미착용`) and 2 stale reflow/soldering rows were marked rejected/review_only
Stage3 remaining gap support v16c narrow8c: 6 new trigger-backed support-only contexts for wafer-transfer robot sensor bypass, UV sterilizer PPE, silica-dust respirator misuse, yarn-winding hand entry, harvest squatting ergonomics, and adhesive splash eye/face PPE; EV battery support was held back after one top-Guide regression
Stage3 remaining gap support v17b narrow9b: 8 new trigger-backed support-only contexts for hair chemical eye exposure, hair-wash neck ergonomics, cashier prolonged standing, pet grooming bite/table fall, binding-machine LOTO, truck-coupling pretrip check, and steam-gun face burn PPE; the broader v17 trial was held back after generic `안전핀` and engine-overhaul waste-support regressions
Stage3 remaining gap support v18 narrow10: 4 new trigger-backed support-only contexts for industrial washer vibration/crush, garment sharp-object puncture, EV high-voltage battery PPE gap, and cold-room emergency-release failure; existing binding-machine LOTO trigger terms were tightened for actual `기계 미정지` and `용지 걸림 제거` wording
Stage3 remaining gap support v19 dropped-tool: 1 new support-only context, `MAINTENANCE_HEIGHT_DROPPED_TOOL`, for hospital/building high-place dropped-tool risk routed to `G-60-2012` and `G-44-2011`
Stage3 remaining gap support v20 actionable: 2 new support-only contexts, `GREENHOUSE_STRUCTURE_FALL` and `DRY_CLEANING_STEAM_PIPE_HOT_SURFACE`, routed to `C-49-2012` and `P-22-2012`; both remaining cases still lack immediate-action CI
Stage3 safe cue negation fix2: safe words are ignored in negated/contrastive phrases (`LOTO 미적용`, `밀착 미흡`, `동료 정상 착용과 대비`) and safe procedure phrases block trigger-only support (`압력 게이지 0`, `잔압 완전 방출`, `방열 장갑 착용`)
Stage3 confirmation gate: confirmation_required support can pass usage/domain gates only when trigger-backed, non-broad-SR-backed, and child/profile-aligned
SituationFrame safe-lock fix: generic `잠금` no longer counts as a safe cue for external-lock/entrapment wording
frame extraction:
  child_context_available: 528
  broad_parent_without_child: 241
  guide support hit samples: 8
photo matchability:
  photo_actionable: 631
  photo_conditional_followup: 39
  photo_unmatchable: 368
  non-field role overrides: 10
```

Tracked baseline summary:

```text
docs/status/evaluation-baseline.md
pictures-json/reports-manifest.json
```

NO_TOP root-cause audit:

```text
report: pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v20_actionable.*
total_no_top: 17
primary root causes:
  stage2_taxonomy_or_normalization_gap: 11
  stage3_she_to_sr_gap: 2
  synthetic_fixture_or_safe_controlled_positive: 2
  situation_frame_child_context_gap: 1
  stage3_she_gap_but_sr_available: 1
domain buckets:
  service_healthcare_people_gap: 7
  other_taxonomy_gap: 4
  chemical_profile_gap: 3
  construction_fall_profile_gap: 1
  machine_profile_gap: 1
  material_handling_profile_gap: 1
```

Local/external report bodies:

```text
pictures-json/reports/situation_frame_artifact_build.v2.*
pictures-json/reports/situation_frame_eval_report.v2_child_gate1.*
pictures-json/reports/guide_photo_matchability_audit_v1.*
pictures-json/reports/no_top_guide_support_candidates_v1.*
pictures-json/reports/stage2_no_top_support_candidates_v3.*
pictures-json/reports/stage3_support_alignment_aliases_v2.*
pictures-json/reports/stage2_support_usage_gate_artifacts_v2.*
pictures-json/reports/stage3_domain_support_v6_artifacts_tight1.*
pictures-json/reports/stage2_3_support_v10_artifacts_narrow2.*
pictures-json/reports/stage2_taxonomy_gap_support_v15_artifacts_narrow7b.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_gap_support_v15_narrow7b.*
pictures-json/reports/actual_response_samples_stage2_taxonomy_gap_support_v15_narrow7b.*
pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_gap_support_v15_narrow7b_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_gap_support_v15_narrow7b.*
pictures-json/reports/stage3_remaining_gap_support_v16c_artifacts_narrow8c.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v16c_narrow8c.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v16c_narrow8c.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v16c_narrow8c_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v16c_narrow8c.*
pictures-json/reports/stage3_remaining_gap_support_v17b_artifacts_narrow9b.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v17b_narrow9b.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v17b_narrow9b.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v17b_narrow9b_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v17b_narrow9b.*
pictures-json/reports/stage3_remaining_gap_support_v18_artifacts_narrow10.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v18_narrow10.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v18_narrow10.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v18_narrow10_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v18_narrow10.*
pictures-json/reports/stage3_remaining_gap_support_v19_artifacts.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_remaining_gap_support_v19_dropped_tool.*
pictures-json/reports/actual_response_samples_stage3_remaining_gap_support_v19_dropped_tool.*
pictures-json/reports/synthetic_observations_v10_stage3_remaining_gap_support_v19_dropped_tool_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_remaining_gap_support_v19_dropped_tool.*
pictures-json/reports/stage2_taxonomy_gap_triage_stage3_safe_cue_negation_fix2.*
pictures-json/reports/stage3_sr_gap_support_v14_artifacts_narrow6b.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_sr_gap_support_v14_narrow6b.*
pictures-json/reports/actual_response_samples_stage3_sr_gap_support_v14_narrow6b.*
pictures-json/reports/synthetic_observations_v10_stage3_sr_gap_support_v14_narrow6b_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_sr_gap_support_v14_narrow6b.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_taxonomy_support_v13_narrow5.*
pictures-json/reports/actual_response_samples_stage2_taxonomy_support_v13_narrow5.*
pictures-json/reports/synthetic_observations_v10_stage2_taxonomy_support_v13_narrow5_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_taxonomy_support_v13_narrow5.*
pictures-json/reports/stage2_3_support_v9_artifacts_narrow4.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v9_narrow4.*
pictures-json/reports/actual_response_samples_stage2_3_support_v9_narrow4.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v9_narrow4_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v9_narrow4.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support2_confirmation_gate2.*
pictures-json/reports/actual_response_samples_stage3_domain_support2_confirmation_gate2.*
pictures-json/reports/synthetic_observations_v10_stage3_domain_support2_confirmation_gate2_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support2_confirmation_gate2.*
pictures-json/reports/stage2_3_support_v8_artifacts_narrow2.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_3_support_v8_narrow2.*
pictures-json/reports/actual_response_samples_stage2_3_support_v8_narrow2.*
pictures-json/reports/synthetic_observations_v10_stage2_3_support_v8_narrow2_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_3_support_v8_narrow2.*
pictures-json/reports/stage2_service_support_v7_artifacts_narrow1.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_service_support_v7_narrow1.*
pictures-json/reports/actual_response_samples_stage2_service_support_v7_narrow1.*
pictures-json/reports/synthetic_observations_v10_stage2_service_support_v7_narrow1_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_service_support_v7_narrow1.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_domain_support1_tight1.*
pictures-json/reports/actual_response_samples_stage3_domain_support1_tight1.*
pictures-json/reports/synthetic_observations_v10_stage3_domain_support1_tight1_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_domain_support1_tight1.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_support_usage_gate3_safe_lock1.*
pictures-json/reports/actual_response_samples_stage2_support_usage_gate3_safe_lock1.*
pictures-json/reports/synthetic_observations_v10_stage2_support_usage_gate3_safe_lock1_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_support_usage_gate3_safe_lock1.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_support_usage_gate2b.*
pictures-json/reports/actual_response_samples_stage2_support_usage_gate2b.*
pictures-json/reports/synthetic_observations_v10_stage2_support_usage_gate2b_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_support_usage_gate2b.*
pictures-json/reports/pipeline_quality_v1_v10_stage3_support_alias2.*
pictures-json/reports/actual_response_samples_stage3_support_alias2.*
pictures-json/reports/synthetic_observations_v10_stage3_support_alias2_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage3_support_alias2.*
pictures-json/reports/pipeline_quality_v1_v10_stage2_no_top_support3.*
pictures-json/reports/actual_response_samples_stage2_no_top_support3.*
pictures-json/reports/synthetic_observations_v10_stage2_no_top_support3_report.*
pictures-json/reports/stage2_5_no_top_root_cause_stage2_no_top_support3.*
pictures-json/reports/pipeline_quality_v1_v10_no_top_support1.*
pictures-json/reports/stage2_5_no_top_root_cause_photo_matchability1.*
pictures-json/reports/pipeline_quality_v1_v10_situation_frame_support7.*
pictures-json/reports/actual_response_samples_situation_frame_support7.*
pictures-json/reports/synthetic_observations_v10_situation_frame_support7_report.*
pictures-json/reports/synthetic_guide_recommendations_v1_v10_usage_profile11_20260510_011317.*
pictures-json/reports/synthetic_guide_no_top_queue_usage_profile11_20260510_011333.*
pictures-json/reports/synthetic_observations_v10_usage_profile11_report.*
pictures-json/reports/actual_response_samples_v1_v10_usage_profile11_vs_pipeb1038.*
pictures-json/reports/pipeline_quality_v1_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate.*
pictures-json/reports/synthetic_observations_v10_ci_wp_relevance8d_profile_tight2_ci_safe_gate_report.*
pictures-json/reports/actual_response_samples_ci_wp_relevance8d_profile_tight2_ci_safe_gate.*
pictures-json/reports/pipeline_quality_v1_v10_industry_boundary_safe_suppress3.*
pictures-json/reports/industry_boundary_gap_triage_safe_suppress3.*
pictures-json/reports/synthetic_observations_v10_industry_boundary_safe_suppress3_report.*
pictures-json/reports/actual_response_samples_industry_boundary_safe_suppress3.*
pictures-json/reports/pipeline_quality_v1_v10_strict_profile_gate3.*
pictures-json/reports/industry_boundary_gap_triage_strict_profile_gate3.*
pictures-json/reports/synthetic_observations_v10_strict_profile_gate3_report.*
pictures-json/reports/actual_response_samples_strict_profile_gate3.*
pictures-json/reports/pipeline_quality_v1_v10_safe_scene_phrase_gate2.*
pictures-json/reports/industry_boundary_gap_triage_safe_scene_phrase_gate2.*
pictures-json/reports/synthetic_observations_v10_safe_scene_phrase_gate2_report.*
pictures-json/reports/actual_response_samples_safe_scene_phrase_gate2.*
pictures-json/reports/pipeline_quality_v1_v10_corpus_gap_guard1.*
pictures-json/reports/industry_boundary_gap_triage_corpus_gap_guard1.*
pictures-json/reports/synthetic_observations_v10_corpus_gap_guard1_report.*
pictures-json/reports/actual_response_samples_corpus_gap_guard1.*
pictures-json/reports/stage2_5_no_top_root_cause_corpus_gap_guard1.*
```

## 7. 검증 명령

Python 문법 검증:

```bash
cd /mnt/c/project/arch-bot/OHS/backend
python -c "import pathlib; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in pathlib.Path('.').rglob('*.py') if '__pycache__' not in p.parts]; print('compile ok')"
```

프론트 빌드:

```bash
cd /mnt/c/project/arch-bot/OHS/frontend
npm run build
```

Monorepo import 검증:

```bash
cd /mnt/c/project/arch-bot
git ls-files OHS | wc -l
git ls-files koshaontology | wc -l
git ls-files kosha-guides/parsed | wc -l
git ls-files | rg '\\.env|node_modules|\\.venv|\\.dev-logs|pictures-json/reports/|kosha-guides/.+\\.pdf'
```

기대 count:

```text
OHS: 161
koshaontology: 2268
kosha-guides/parsed: 1038
```

## 8. 바로 이어서 할 일

1. 새 작업은 root `arch-bot/main`에서 수행한다.
2. 작업 전 `git status --short --branch`로 clean 상태를 확인한다.
3. Guide 품질 작업은 `corpus_gap_guard1` 기준으로 이어간다.
4. `she-stage3-new-pattern-candidates-reference-guard1` 230건은 runtime SHE 확정으로 import하지 않는다. `true_new_she`도 첫 사이클에서는 review-only다.
5. NO_TOP 85건은 runtime repair보다 corpus/taxonomy/review boundary 성격이 크다. 억지로 broad alias/support를 추가하지 말고, exact source Guide가 생기거나 별도 public/customer/animal-safety taxonomy를 만들 때만 재검토한다.
6. 다음 구조적 보강 대상은 잔여 `C_corpus_or_followup_gap 1`, `CI no_action 482`, `CI guide_boundary_mismatch 26`, `workprocess_mismatch 20`이다. `B_wrong_guide_boundary`와 `D_safe_scene_overpromoted`는 0건이다.
7. parent context는 검색 확장에만 쓰고, parent-only match는 confirmed/status/penalty/direct SR/표준절차 top 후보를 만들 수 없다.
8. photo_matchability는 표준절차 top lane에만 적용한다. 즉시조치, SHE status, SR evidence, penalty path에는 적용하지 않는다.
9. 온톨로지 검증 경고는 `structure_issue`, `data_issue`, `algorithm_issue`, `corpus_gap`, `review_only`로 나눠 원천 artifact 쪽에서 정리한다.
