# LLM-Accelerated 정석 Ontology Engineering Plan

> **다음 세션 진입점.** 이 문서는 2026-05-16~17 두 세션에 걸친 작업의 메인 plan이다.
> 임시 plan 파일(`.claude/plans/workplan-...md`)에서 정식 git 추적 문서로 이전됨.
> 향후 모든 Phase 결정의 기준.

## Status (2026-05-28 갱신 — ⭐ axiom-100% Sprint(Phase A~K) + ⭐ guide-accuracy Sprint(P0~P3) 완료, origin/main `4aa3cca`. 이전: Phase G + Tier 4 + Hazard-Direct, `3502eff`)

> **2026-06-14 갱신 — ⭐ Track A ② reasoning vertical slice 완료 + main push** (commits `87d9e63`/`7c50304`/`e6140bb`). 6단계 reasoner 산출(R-1/R-3 + relaxed-key K-R2/K-R4)을 PG로 재물질화하고 서빙 경로를 Fuseki→PG로 전환했다. 신규 PG 테이블 `sr_inferred_relations` = **103,295 rows** (R-1 exemptedBy 107 / K-R2 coApplicable 16,429쌍→32,858 / K-R4 dependsOn 35,165쌍→70,330), `materialization_runs` PROV run-tracking 신설. 상세 [신규 산출물 (2026-06-14)](#신규-산출물-2026-06-14--track-a--reasoning-slice) 참조. 미커밋: A4/A5 governance (license 이원화 + ontology version **2.0.0** + VoID + SKOS — 이 문서 업데이트 직후 커밋 예정).
>
> 최신 두 스프린트(axiom-100%, guide-accuracy)는 별도 plan/runbook으로 추적: [ontology-axiom-100pct.md](ontology-axiom-100pct.md) + [../dev-notes/axiom-100pct-phase-c-j.md](../dev-notes/axiom-100pct-phase-c-j.md) + [../dev-notes/guide-recommendation-accuracy.md](../dev-notes/guide-recommendation-accuracy.md). 아래 Status 표는 ~2026-05-19 (Phase G/Tier 4) 기준.
>
> **2026-05-31 facet 구조 audit + 수정** (Fix A canonical⊑axis floating 480→0 / B1 라벨 / B2 dead·alias / B3a 축 disjoint, origin/main `678a7d1`)은 별도 정본 [../backlog/ontology-structural-findings.md](../backlog/ontology-structural-findings.md)로 추적. 남은 B3b~B6.

| Phase | 상태 | 비고 |
|---|---|---|
| Phase 0 (Synthetic Replay 인프라) | ✅ 완료 | `replay_synthetic_observations.py` + `regression_gate.py` |
| Phase B (Runtime LLM rerank) | ✅ 완료 + 검증 | positive avg_procedures −26.4% |
| Phase A (Domain pair mining) | ✅ 완료 | 2,232 incompatibility (vetted 0 + candidate 2,201 + self_refine 31) |
| Phase C (Self-refine loop) | ✅ 작동 검증 | analysis_log 2,536+건 + 자율 채택 |
| Catalog/alias 확장 | ✅ 완료 | 187개 신규 alias + 66개 신규 work_context, she_accuracy +4.9%p |
| Phase E-prep (6 step) | ✅ 완료 | BFO+LKIF 2-layer, 22 SWRL, 26 SHACL, OntoClean 13→1 |
| Phase E.2 (Openllet 실제 통합) | ✅ 완료 | Fuseki Java가 v2 + disjoint + SHACL + 172 subClassOf 로드 (commit `3520cab`) |
| Phase 3 (catalog v4 + SHE 1,616 + reasoning catch) | ✅ 완료 | reasoning이 LLM 환각 1,902건 차단 (보고: `reasoning-catch-effectiveness-2026-05-17.md`) |
| **F.3.0 (Reject reason classifier)** | ✅ 완료 | `axiom_missing 36.44%` (920건/210 pair), commit `8ff40d7` |
| **A (Runtime 4번 채널 hook + Hot-fix)** | ✅ 완료 | analysis_log 3 신규 필드, commit `ebe1011` + hot-fix `a841a0b` |
| **C (KB incompat KO→EN cleanup)** | ✅ 완료 | 2,232 entries 100% translated, commit `2ea800d` |
| **F.3.2 (Missing-axiom miner first batch)** | ✅ 완료 | 49 verify → 8 accepted candidate (KB 2,232→2,240), commit `9219c7c` |
| **F.3.3 (Gate 3 regression)** | ✅ PASS | 2,360 valid 0 errored, vs baseline_v3 delta 0/-0.0013, commit `eb7843f` |
| F.1 (Vocabulary auto-registration, Module 4.1) | ✅ 완료 | 5 vetted aliases, closed loop. Runbook: `dev-notes/F.1-auto-register-aliases.md` |
| F.2 (Taxonomy Discovery, Module 4.2) | ✅ 완료 | catalog v3.3 481 codes × 5 axes, 790 SHE enriched. Runbook: `dev-notes/F.2-taxonomy-discovery.md` |
| **Tier 1 재포함** (T1.A/B/C, 2026-05-18 저녁) | ✅ 완료 | `b66fa36` 누락 발견 + 재commit `93c49fe`. T1.A rollback fix + T1.B npz code + T1.C usage tracking |
| **T2.A F.3.1 pyshacl reasoner shadow** | ✅ 완료 | `pyshacl_shadow_validator.py` + `shadow_reasoner.py` + analysis_log.reasoner_rejects, commit `93c49fe` |
| **T2.B F.3.4 KB compile + Fuseki reload** | ✅ 완료 | `compile_kb_to_ttl.py` → kb-candidates.ttl 2192 shapes + Java edit + docker rebuild + container restart + **SPARQL 2216 NodeShapes 검증**, commit `ac98d4c` → main `325ad37` |
| **T2.C F.3.5 cron + drift detection** | ✅ 완료 | `f3_drift_check.py` + Makefile `f3-weekly-cycle`, commit `78886b3` |
| **T2.D F.3.2 vetted promotion** | ✅ 완료 | 8/8 PASS 1-by-1 + Gate 3 wrap (예상 5-6 대비 100%), commit `ac98d4c` |
| **Tier 3.A Closed Vocab Schema Enum** | ✅ 완료 | `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text` 529 codes enum, free-creates 76→4 (-94.7%), commit `b237e78` |
| **Phase G.1 PG materialization** | ✅ 완료 | `core:Incompatibility` ontology + `guide_domain_incompatibilities` PG (2,016 rows), feat commit `b9de6f0`, merge `d6b4589` |
| **Phase G.2 GuideUsageProfile ontology + PG** | ✅ 완료 | ontology 가장 큰 갭 해결, 14 properties, commit `2f7ef92` |
| **Phase G.3 penalty_rule_index PG** | ✅ 완료 ⭐ | 4,076 rules, **penalty_accuracy +27.16%p, overall +18.81%p**, commit `8ddc2c7` |
| **Phase G.4 reasoner-derived view + Openllet 분석** | ✅ 완료 | `she_patterns_reasoner_derived` view (77 SHE) + Openllet `inferred=0` root cause, commit `434f35f` |
| **Tier 4 AsymmetricProperty 패치** | ✅ 완료 | `law:modifies` owl:AsymmetricProperty 제거 → FunInv 경고 해소 + SPARQL 추론 검증, fix commit `03f6afe`, merge `5edae0b` |
| **Tier 4 #4 Pellet reporting 명시화** | ✅ 완료 | `KoshaFusekiServer.java` `getDeductionsModel()` + lazy materialization 안내, commit `1bacd44` |
| **Tier 4 #2 AdministrativeFine TTL enrichment** | 🟡 Skip | Design intent (RULE은 OSHA 38/39 위임으로 criminal-only). OSHA 175조 admin은 별도 Pipe-A 확장 후보 |
| **Tier 4 #1 77 SHE matcher 통합** | 🟡 별도 sprint 이관 | 5 SHE batch → -7.07%p VETOED. matcher refactor 필요. rollback 정상 |
| **Tier 4 #3 SWRL Pellet 실행기 통합** | ✅ 완료 ⭐ | R-1 exemptedBy: **107 inferred** + R-3 HighSeverityPenalty: **3,579 inferred** (severityScore ≥ 5와 100% 일치), commit `448a8d0` |
| **T4 #1 후속 sprint (77 SHE manual review + matcher refactor plan)** | ✅ 완료 | approve 57 / modify 19 / defer 1, batch 1 promote -10.17%p VETOED → matcher 자체 로직 문제 입증. patch proposal 19/19 PG-only. 7-day sprint plan: `she-matcher-broadness-refactor.md`. feat commit `a26c888`, merge `1bfd6b8` |
| **moellab.info/ohs 위험요소 비교 분석** | ✅ 완료 ⭐ | 8 사진 / 37 hazards 합리적, GPT 직접 출력 정확. **architecture pivot 후보 식별**: hazard-direct (Vision LLM → catalog → 우리 Guide → procedure). feat commit `833dcd7`, merge `3502eff` |
| **hazard-direct architecture pivot** | ✅ **완료 (단일 세션 완주)** ⭐ | [`hazard-direct-architecture-pivot.md`](hazard-direct-architecture-pivot.md) — Phase 1-5 일괄 구현. **Phase 5 8 photo 실호출: 25/25 (100%) catalog 매핑** (AC-2 ≥85% PASS), 25 hazard_guide_relations, 14 penalty paths (Phase G.3 보존), legacy 48 procedures 병행 (호환성 OK). Commits `acd2303` → `5256573` (5 commits). [eval JSON](../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json) |
| **SHE matcher broadness-aware refactor** | ⏳ 후행 별도 sprint (사용자 결정) | hazard-direct sprint 종료 후 별도 진행. plan: [`she-matcher-broadness-refactor.md`](she-matcher-broadness-refactor.md) |
| **Track A ② reasoning vertical slice** (2026-06-14) | ✅ **완료 + main push** ⭐ | `sr_inferred_relations` PG **103,295 rows** (R-1 exemptedBy 107 / K-R2 coApplicable 16,429쌍 same-Chapter / K-R4 dependsOn 35,165쌍 same-Hazard 양방향) + `materialization_runs` PROV. 서빙 Fuseki→PG SELECT 전환 + `/depends-on` 신규 + `enrich_sr_with_pg`. R-3 HighSeverityPenalty 3,579는 `penalty_rule_index.severity_score>=5` SQL 재현. 3 신규 TTL + `emit_inferred_relations.py` + phase-g5* Makefile. **Gates 전부 PASS** (f1-regression all-metric delta 0.0000 / latency / verify-baseline / phase-g5·g5b·g5c-verify). Commits `87d9e63`/`7c50304`/`e6140bb`. 상세 [신규 산출물 (2026-06-14)](#신규-산출물-2026-06-14--track-a--reasoning-slice) |
| F.4 (CQ Reverse, Module 4.5) | ⏳ 후속 (Tier 4 중장기) | 3-4주, Photo persist ORM 선행 필요 |
| F.5-F.8 (GraphRAG / Maintenance / fine-tune / OBO) | ⏳ 후속 (Tier 4 중장기) | Phase J OBO 별도 plan 예정 |

## Context

**시작 문제**: 8 real-test-photo 시연에서 5번 LLM enrichment의 over-promote 5건 (지게차→가공목재, 식당→사장교, 영세제조→급식실 등). 원인은 `guide_domain_profile.py`의 9개 hard-coded keyword 매칭.

**목표**: LLM-Accelerated 정석 ontology engineering (NeOn + OntoClean + Layer 4 cross-cutting). 사람 개입 최소화, LLM이 axiom/rule/shape 자동 생성·검증·refine.

**원칙**:
- 모든 LLM = **gpt-5.4-nano** (단일 모델, 비용·일관성)
- **Embedding pre-filter** (text-embedding-3-small) → LLM 호출 70% 감소
- **Scene-hash 캐시** → 재분석 시 0회
- **Asymmetric trust** (candidate -0.05 → vetted -0.18)
- **2,360 synthetic ground truth** = regression backbone (사람 개입 대체)

## 4-Layer Architecture

상세: [architecture/4-layer-architecture.md](../architecture/4-layer-architecture.md)

```
Layer 0: Vision LLM       (gpt-4.1, 영구 잔존)
Layer 1: Normalizer       (alias dict + catalog)
Layer 2: Semantic Reasoning (SHE + OWL DL + SWRL/SHACL)
Layer 3: PG Materialization (cache, ms 응답)
─────────────────────────────────────────────────
Layer 4: Ontology Learning (cross-cutting, 학습기)
  ├─ 4.1 Term & Type Extraction (Task A)
  ├─ 4.2 Taxonomy Discovery (Task B)
  ├─ 4.3 Relation Mining (Task C) ★ 우리 학계 SOTA
  ├─ 4.4 Axiom Discovery (Task D) ★ 학계 미답
  ├─ 4.5 CQ Reverse Engineering
  ├─ 4.6 GraphRAG
  └─ 4.7 Continual Adaptation
```

상세: [architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md)

## 핵심 결과 (이번 세션)

### Phase 0-C (LLM 자율 도메인 보강)

| metric | baseline_v1 | baseline_v2 (catalog 확장) | active_v2 (Phase B+) | 비고 |
|---|---|---|---|---|
| she_accuracy | 55.81% | **60.72%** (+4.9%p) | 60.72% | catalog 확장 효과 |
| sr_accuracy | 76.36% | 76.48% | 76.48% | |
| overall_accuracy | 13.31% | **15.25%** (+1.9%p) | 15.25% | |
| false_positive_rate | 87.32% | 87.32% | 87.32% | actions 기반 metric 한계 |
| **positive avg_procedures** | **3.02** | 3.07 | **2.26** (−26.4%) | LLM rerank 효과 |
| regression_gate | n/a | PASS | PASS | false_negative_rate +0.07%p 미미 |

**8 real-test-photo**: 4/5 over-promote 차단 확인 (지게차/영세제조/포크레인/음식점)

### Phase E-prep

| 단계 | 산출물 | 검증 |
|---|---|---|
| 1. CQ + Layer 분류 | 50 CQ + 55 class layer | LLM 3-task 성공 |
| 2. BFO+LKIF 매핑 | `kosha-ontology-v2.owl` (62 class, 5 imports, 64 subClassOf) | rdflib parse ✅ |
| 3a. Disjoint Axioms | `kosha-disjoint-axioms.ttl` (84 industries, 2,192 disjoint) | rdflib parse ✅ |
| 3b. SWRL Rules | `kosha-rules-v2.swrl` (R-9~R-30, 22개) | 5 카테고리 균형 |
| 3c. SHACL Shapes | `serving-validation-shapes-v3.ttl` (26개) | **SHACL Conforms: True** ✅ |
| 4. OntoClean | 55 class 라벨링 (R/I/U/D), violation 13→**1** (92% 자동 수정) | LKIF Role 패턴 ACCEPT |
| 5. CQ → SPARQL | 50 query | 2% coverage (ABox 본질 한계, Photo persist 시 해결) |

### 학계 reference 통합 (9 paper)

상세: [governance/ontology-learning-references.md](../governance/ontology-learning-references.md)

**학계 5/5 합의**:
1. Hybrid neuro-symbolic (LLM + reasoner)
2. Task A/B/C/D 분해
3. Decomposed CoT prompting
4. Human-in-the-loop
5. CQ-driven 검증

**우리 차별점 (학계 contribution potential)**:
- LKIF-Core × BFO 2-layer (학계 deontic 도메인 부재)
- 한국어 법령 처리 (학계 0건)
- Asymmetric trust pattern (학계 미언급)
- Phase A 2,232 incompatibility = Task C SOTA (LLMs4OL F1 0.078 vs 우리 24%)
- 자동 SWRL/SHACL 생성 = Task D 학계 미답

## 신규 산출물 (이번 세션, git 추적 대상)

### Ontology files (`ontology-team/06-reasoning/ontology/`)
- `kosha-ontology-v2.owl` — BFO+LKIF imports + 64 subClassOf
- `kosha-ontology-v2.formatted.ttl`
- `kosha-disjoint-axioms.ttl` — 84 industries + 2,192 disjoint
- `kosha-rules-v2.swrl` — 8 + 22 = 30 SWRL rules
- `serving-validation-shapes-v2.ttl` (v2 결함, v3 사용 권장)
- `serving-validation-shapes-v3.ttl` — SHACL Conforms: True
- `kosha-ontology-v3-restructure-patch.ttl` — OntoClean patch
- **`kb-candidates.ttl` (T2.B 신규, 2026-05-18)** — F.3.2 SHACL shapes (sh:Info severity), 2192 NodeShapes, 80 industries. Fuseki 로드 +17,618 triples (총 981,409).
- **`docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java` (T2.B 수정)** — sources array에 `kb-candidates.ttl` 추가. docker image rebuild (`docker-fuseki:latest` sha256 `08837972`).

### Backend code (`serving-team/08-app/backend/`)
- `app/services/guide_embedding_filter.py` (신규)
- `app/services/llm_validator_cache.py` (신규)
- `app/integrations/prompts/guide_validator_prompt.py` (신규)
- `app/services/analysis_pipeline.py` (수정: `_apply_llm_rerank`, `_append_analysis_log` + **T2.A `reasoner_rejects` kwarg + `_log_skipped_analysis`** (Quick Win Task 2 A hook always-on + T2.A))
- `app/services/guide_domain_profile.py` (수정: dynamic incompat KB layer)
- `app/integrations/openai_client.py` (수정: `validate_guide_relevance` + **T3.A `_load_catalog_codes()` + ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text enum 529 codes**)
- `app/models/analysis.py` (수정: `ExcludedCandidate`)
- `app/data/risk_feature_aliases.json` (확장 +187)
- `app/data/risk_feature_catalog.json` (확장 +66 work_context)
- `scripts/replay_synthetic_observations.py` (신규)
- `scripts/regression_gate.py` (신규)
- `scripts/merge_replay_partials.py` (신규)
- `scripts/test_real_photos.py` (신규)
- **`app/services/shadow_reasoner.py` (T2.A 신규, 2026-05-18)** — serving runtime KB axiom shadow validate (lazy module cache, ~50μs/photo)
- **`app/services/hazard_normalizer.py` (T1.C 수정, 2026-05-18)** — step 4.5 `_log_alias_usage()` candidate match 시 meta.jsonl append

### Data team scripts (`data-team/05-enrichment/llm-scripts/`)
- `build_competency_questions.py`
- `build_layer_mapping.py`
- `build_disjoint_axioms.py`
- `build_swrl_rules.py`
- `build_shacl_shapes.py`
- `build_guide_domain_embeddings.py`
- `build_guide_llm_domains.py`
- `extend_normalizer_aliases.py`
- `fix_shacl_shapes.py`
- `local_consistency_check.py`
- `mine_domain_incompatibilities.py`
- `mine_overpromote_patterns.py`
- `ontoclean_auto_fix.py`
- `ontoclean_validator.py`
- `promote_incompatibilities.py`
- `regenerate_sparql_queries.py`
- **`classify_reject_reasons.py` (F.3.0, 2026-05-17)**
- **`translate_incompat_industries.py` (C cleanup, 2026-05-17)**
- **`mine_missing_axioms.py` (F.3.2, 2026-05-17)**
- **`pyshacl_shadow_validator.py` (T2.A F.3.1, 2026-05-18)** — offline batch + pyshacl cross-check
- **`compile_kb_to_ttl.py` (T2.B F.3.4, 2026-05-18)** — candidate axiom → kb-candidates.ttl (SHACL sh:Info)
- **`f3_drift_check.py` (T2.C F.3.5, 2026-05-18)** — 6 metric drift 모니터
- **`promote_f32_per_candidate.py` (T2.D, 2026-05-18)** — 1-by-1 + Gate 3 wrap (8/8 PASS)
- **`_migrate_embedding_cache_to_npz.py` (T1.B 1회성, 2026-05-18)** — JSON → npz 95MB → 12MB

### Phase G + Tier 4 산출 (2026-05-19)
**PG sync scripts (`serving-team/07-materialization/pg-sync-scripts/`)**:
- `schema_guide_domain_incompatibilities.sql` + `import_domain_incompatibilities_to_pg.py` (G.1, 2,016 rows)
- `schema_penalty_rule_index.sql` + `import_penalty_to_pg.py` (G.3, 4,076 rules from TTL)
- `schema_she_patterns_reasoner_derived.sql` (G.4 view, 77 SHE)

**Validation/bench scripts**:
- `serving-team/07-materialization/validation-scripts/sample_query_equality.py` (G.1 + G.2 sample equality)
- `serving-team/08-app/backend/scripts/bench_shadow_reasoner.py` (G.1 latency bench)

**Ontology TBox patches (`ontology-team/06-reasoning/ontology/`)**:
- `kosha-ontology-v3-incompat-patch.ttl` (G.1, `core:Incompatibility` n-ary class)
- `kosha-ontology-v3-guide-profile-patch.ttl` (G.2, `guide:GuideUsageProfile` class 신규)
- `kosha-ontology-v3-penalty-relations-patch.ttl` (G.3, penalty relation properties)
- `kosha-rules-r1-r3-swrl.ttl` (T4 #3, R-1 + R-3 SWRL OWL serialization)

**Ontology v2 수정**: `kosha-ontology-v2.owl` + `.formatted.ttl` — `law:modifies`의 `owl:AsymmetricProperty` 제거 (T4 AsymmetricProperty 패치, FunInv 경고 해소).

**Fuseki Java 수정**: `KoshaFusekiServer.java` sources array에 kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 추가, Pellet `getDeductionsModel()` 명시 호출.

**Backend code (PG primary 전환)**:
- `app/services/shadow_reasoner.py` (G.1, JSON fallback 유지)
- `app/services/guide_domain_profile.py` (G.2)
- `app/services/hazard_rule_engine.py` (G.3 `_load_penalty_index_from_pg()`)

**Backend ORM** (`app/db/models.py`): `PgGuideDomainIncompatibility`, `PgPenaltyRoute`, `PgPenaltyRuleIndex` (3 신규 classes).

**Runbook + 결정 문서** (`docs/dev-notes/`):
- `phase-g.{1,2,3,4}-*.md` (4 runbooks)
- `t4-administrative-fine-scope-decision.md` (T4 #2 skip 결정)
- `t4-77-she-matcher-integration-decision.md` (T4 #1 별도 sprint 이관)
- `t4-swrl-pellet-integration.md` (T4 #3 SWRL 통합)

**Manual review 자산**: `data-team/05-enrichment/runtime-artifacts/pending_review_she_for_manual_review.json` (77 SHE 8-axis + visual_triggers, T4 #1 후속용)

### 신규 산출물 (2026-06-14) — Track A ② reasoning slice

> commits `87d9e63` (R-1/R-2 슬라이스 + 서빙 소비) → `7c50304` (K-R2 same-Chapter coApplicable) → `e6140bb` (K-R4 same-Hazard dependsOn). **전부 main push 완료.** 6단계 reasoner 산출을 7단계 PG로 재물질화하고 서빙을 PG SELECT로 전환한 첫 vertical slice.

**신규 PG 테이블 (2개)**:
- `sr_inferred_relations` = **103,295 rows total**, `rule_id`로 strict/relaxed 구분:
  - **R-1 exemptedBy**: 107 rows (95 distinct SR) — strict DL (NS→exempt-NS), SR별 served
  - **K-R2 coApplicable**: 16,429 distinct pairs → 32,858 rows (same-Chapter relaxation, 양방향)
  - **K-R4 dependsOn**: 35,165 distinct pairs → 70,330 rows (same-Hazard relaxation, 양방향)
  - R-2 strict coApplicable = 0 (SR↔Article 1:1 — Phase A 발견과 일치). `rule_id`가 strict R-1 vs relaxed K-R2/K-R4를 구분.
- `materialization_runs` = PROV run-tracking (`run_id`, `rule_set`, `ontology_commit`=git rev, `source_ttl_sha256`=content-hash, `triple_count`, `status`). runs #1-4.
- **R-3 HighSeverityPenalty (3,579)**는 `sr_inferred_relations`에 저장하지 않고 `penalty_rule_index.severity_score>=5` SQL로 재현.

**신규 TTL (`ontology-team/06-reasoning/ontology/`)**: `kosha-inferred-relations.ttl`, `kosha-coapplicable-chapter.ttl`, `kosha-dependson-hazard.ttl`.

**신규 스크립트**:
- `ontology-team/06-reasoning/ontology/scripts/emit_inferred_relations.py` (`--mode strict|chapter|hazard`)
- `serving-team/07-materialization/pg-sync-scripts/import_sr_inferred_relations_to_pg.py`
- `serving-team/08-app/backend/scripts/verify_inferred_relations.py`

**서빙 (`serving-team/08-app/backend`) — Fuseki→PG 전환**:
- `/api/v1/sparql/sr/{id}/exemptions`, `/co-applicable`, `/article/{code}/inferred-graph` → Fuseki 대신 PG SELECT
- **신규** `/api/v1/sparql/sr/{id}/depends-on`
- 신규 `app/services/sr_inferred_service.py`
- `hazard_rule_engine.py`의 dead `enrich_sr_with_sparql` → PG-backed `enrich_sr_with_pg`로 교체
- **이 reasoner 산출들은 더 이상 Fuseki 요청경로가 아니며 서빙은 PG를 읽는다.**

**신규 Makefile 타깃**: `reasoning-emit`, `reasoning-emit-chapter`, `reasoning-emit-hazard`, `phase-g5-schema`, `phase-g5-import`, `phase-g5-verify`, `phase-g5b-import`, `phase-g5b-verify`, `phase-g5c-import`, `phase-g5c-verify`.

**Gates**: f1-regression all-metric delta = **0.0000** (analysis hot-path UNCHANGED, 3 slices 전부) / latency-gate PASS / verify-baseline PASS / phase-g5·g5b·g5c-verify PASS.

**OLD 수치 reconciliation**:
- 이전 "K-general dependsOn 36,949" (on-demand SHACL count)은 지금 materialize된 **K-R4 = 35,165 pairs**와 다른 값이다.
- coApplicable 16,429은 이전에 "미적재/on-demand/gitignore"로 표기됐으나 **이제 PG로 materialize**됨.

**A4/A5 governance (DONE, 미커밋 — 이 문서 업데이트 직후 커밋 예정)**:
- A4 dual license: `LICENSE`(Apache-2.0 code) + `LICENSE-ontology.md`(CC-BY-4.0 ontology/data) + README license section + `CITATION.cff`(CFF 1.2.0) + `kosha-ontology-metadata.ttl`.
- Ontology RELEASE VERSION = **2.0.0** (`owl:versionIRI .../ontology/2.0.0`, `owl:versionInfo "2.0.0"`, kosha-ontology-v2.owl lineage 정렬; CITATION version 2.0.0). **1.0.0 아님.**
- VoID (`kosha-ontology-metadata.ttl`, full consistency assembly scope): `void:triples` **1,049,862**, `void:classes` **625** (named owl:Class, facet fine class 포함 — core 개념 TBox는 ~62), `void:properties` **164** (ObjectProperty 119 + DatatypeProperty 45).
- A5 SKOS: `gen_skos_scheme.py` + `kosha-codes-skos.ttl` = 3 SKOS ConceptSchemes (axis별: accident-type/hazardous-agent/work-context), **504 concepts, 2,659 triples**. `skos:broader` 418 (same-axis rollup→canonical), `skos:relatedMatch` 21 (cross-axis agent→accident-type associative), `rdfs:seeAlso` 62 (canonical→OWL class). `broadMatch/exactMatch`은 punning/hierarchy 오선언 회피로 미사용. Makefile `gen-skos`.
- **Namespace는 여전히 `cashtoss.info`** (`w3id.org/ohs-kr` migration은 FUTURE step A2 — IRI 변경 없음).

### Runtime artifacts (`data-team/05-enrichment/runtime-artifacts/`)
- 모든 산출 JSON (CQ, layer assignment, disjoint, SHACL, OntoClean 등)
- `analysis_log.jsonl` (2,536+ entries, A 신규 3 필드 포함 + **T2.A `reasoner_rejects` 필드**)
- `guide_domain_embeddings.npz` (3.75MB)
- `replay_baseline.json` / `replay_baseline_v2.json` / `replay_baseline_v3.json` / `replay_active_b.json` / `replay_active_v2.json`
- **`reject_reason_classified.jsonl` (F.3.0, 2,525 entries)**
- **`reject_reason_distribution.json` / `reject_reason_sample_100.jsonl` (F.3.0)**
- **`replay_post_f32.json` (F.3.3 Gate 3 input, 2,360 cases, 0 errored)**
- **`guide_domain_incompatibilities.json` (T2.D 후: 2,232 vetted + **8 F.3.2 vetted (T2.D 100% PASS)** = 2,240, EN-normalized)**
- **`incompatibility_audit.jsonl` (+49 F.3.2 verify entries + **T2.D per_candidate_promote_pass 8 entries**)**
- **`shadow_reasoner_log.jsonl` (T2.A 신규)** — offline batch CLI 산출, 2580 rows → 859 reasoner_rejects
- **`f32_per_candidate_promotion_results.json` (T2.D 신규)** — 8/8 PASS summary
- **`f3_drift_log.jsonl` (T2.C 신규)** — drift check 시계열 (cron weekly)
- **`kb_candidates_compile_audit.json` (T2.B 신규)** — kb-candidates.ttl compile audit
- **`alias_embedding_cache.npz` / `.meta.json` (T1.B 신규)** — JSON 50.9MB → npz 6.4MB (87.3% 축소)
- **`catalog_label_embedding_cache.npz` / `.meta.json` (T1.B 신규)** — JSON 44.3MB → npz 5.2MB (88.1% 축소)

### Frontend (`serving-team/08-app/frontend/`)
- `src/components/results/SourceBadge.tsx` (신규, 10개 source type)
- 5개 panel 수정 (badge 표시)

### Reference (`ontology-team/reference-article/`, 사용자 추가)
- 9개 학계 PDF (LLMs4OL, OntoGPT/SPIRES, NeOn-GPT, 2024-2025 최신)

## Phase F+ 로드맵 (Layer 4 본격 구현)

| Phase | 작업 | 학계 reference | 시간/비용 | 상태 |
|---|---|---|---|---|
| ~~E.2~~ | Fuseki Java 수정 + Openllet 정식 통합 | LLMs4Life Pellet | 1시간 | ✅ 완료 (`3520cab`) |
| **F.3.0** | Reject reason classifier (5 카테고리) | Tsaneva ensemble | 3-4h | ✅ 완료 (`8ff40d7`) |
| **F.3.2** | Missing-axiom miner (Disjoint-only first batch) | 4-Gate | 1-2일 | ✅ 완료 (`9219c7c`, 8 candidate) |
| **F.3.3** | Gate 3 regression (counter-example) | 4-Gate | 수십 분 | ✅ PASS (`eb7843f`) |
| **F.1** | Vocabulary auto-registration (Module 4.1) | SPIRES IDSpaces/ValueSets | 1주 | ✅ 완료 (5 vetted, closed loop) |
| **F.2** | TBox class learning (Module 4.2, Taxonomy Discovery) | Two-way CoT + Ontogenia | 1주 | ✅ 완료 (catalog v3.3, 481 codes × 5 axes) |
| **T2.A F.3.1** | Reasoner reject channel (pyshacl shadow) | LLMs4Life Pellet | 1-2일 | ✅ 완료 (`93c49fe`, pyshacl + shadow_reasoner) |
| **T2.B F.3.4** | KB compilation hook (TTL + Fuseki reload) | — | 1일 | ✅ 완료 (`ac98d4c` → `325ad37`, kb-candidates.ttl 2192 shapes, SPARQL 2216 NodeShapes 검증) |
| **T2.C F.3.5** | Cron + drift detection (`Makefile f3-weekly-cycle`) | SLR challenges | 1일 | ✅ 완료 (`78886b3`, f3_drift_check.py) |
| **T2.D** | F.3.2 vetted promotion (1-by-1 + Gate 3 wrap) | 4-Gate | 1일 | ✅ 완료 (`ac98d4c`, 8/8 PASS) |
| **Tier 3.A** | Closed Vocab Schema Enum (Layer 0 catalog enforce) | LLMs4OL TaskA | 1주 | ✅ 완료 (`b237e78`, 76→4 free-creates -94.7%) |
| **Phase G.1** | guide_domain_incompatibilities PG + `core:Incompatibility` ontology | — | 1주 | ✅ 완료 (`d6b4589`, 2,016 rows) |
| **Phase G.2** | guide_usage_profiles PG + `guide:GuideUsageProfile` ontology (가장 큰 갭) | — | 1주 | ✅ 완료 (`2f7ef92`) |
| **Phase G.3** | penalty_rule_index PG + penalty relations ontology | — | 1주 | ✅ 완료 ⭐ (`8ddc2c7`, +27.16%p) |
| **Phase G.4** | she_patterns_reasoner_derived view + Openllet 분석 | — | 1주 | ✅ 완료 (`434f35f`) |
| **Tier 4 fix** | AsymmetricProperty 패치 (Openllet `inferred=0` 근본 해결) | — | 0.5일 | ✅ 완료 (`5edae0b`) |
| **Tier 4 #4** | Pellet inferred count reporting 명시화 | — | 0.5일 | ✅ 완료 (`1bacd44`) |
| **Tier 4 #3** | SWRL Pellet 실행기 통합 (R-1 + R-3) | LLMs4Life Pellet SWRL | 1일 | ✅ 완료 ⭐ (`448a8d0`, R-1: 107 + R-3: 3,579 inferred) |
| F.4 | CQ Reverse + SPARQL 회복 (Module 4.5) | RETROFIT-CQ 75% | 1주 + Photo persist | ⏳ 후속 (Tier 4 중장기) |
| F.5 | GraphRAG 통합 (Module 4.6) | Salovsky Dual Memory | 2주 | ⏳ Tier 4 중장기 |
| F.6 | Maintenance phase (Module 4.7) | SLR challenges #4 #5 | 영구 cron | ⏳ Tier 4 중장기 |
| F.7 | Small model fine-tune | Aggarwal Dolphin-Mistral-7B | 2-3주 | ⏳ Tier 4 중장기 |
| F.8 (Phase J) | OBO Foundry/IOF 등재 + LegalRuleML | SLR Lifecycle | 1-3개월 | ⏳ 별도 plan (사용자 명시) |
| **R-4~R-30 SWRL 변환** | 의사코드 → OWL/RDF SWRL serialization 일괄 변환 | — | 1-2주 | ⏳ T4 후속 |
| **SHE matcher broadness-aware refactor** | 77 pending_review SHE 통합 가능 | — | 1-2주 | ⏳ T4 #1 후속 |
| **OSHA admin penalty Pipe-A 확장** | 제175조 administrative fines (6단계) 추출 | — | 4-6h | ⏳ T4 #2 후속 |

## 즉시 적용 권장 3가지 (ROI 큼)

1. **OntoGPT 직접 통합** — `pip install ontogpt` + `monarch-initiative/ontogpt`의 LinkML 템플릿 50+ 활용
2. **Two-way CoT + Metacognitive prompt** — `build_*.py` prompt template 전환 (Aggarwal +0.2 F1)
3. **OOPS! Pitfall Scanner + LinkML schema 검증** — Phase E.3 산출물 4-dim eval gate

## LLM 의존 단계적 폐지 path

상세: [architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md)

| LLM 종류 | 6단계 안정화 후 | 이유 |
|---|---|---|
| Vision LLM (gpt-4.1) | 🔵 영구 유지 | AI 인식 영역 |
| Phase B LLM rerank (gpt-5.4-nano) | 🟡 점진 폐지 | OWL DisjointClasses + SHACL이 같은 일 수행 |
| 5번 LLM enrichment | 🟢 폐지 | OWL TBox + SWRL 정형화 |
| Phase C self-refine | 🟡 유지 | 새 도메인 자율 학습 가치 영구 |

## 7단계 PG 재물질화 대상

| PG 테이블 | 재물질화 내용 |
|---|---|
| `she_patterns` | reasoner 추론 신규 패턴 (수백 → 수천) |
| `guide_usage_profiles` | 현재 `guide_domain_profiles.json` → table |
| `guide_domain_incompatibilities` ✅ (G.1 완료) | LLM-mined KB (vetted 2,232 + 8 F.3.2 T2.D vetted = 2,240) → **PG 2,016 rows materialized** (Phase G.1, `d6b4589`). shadow_reasoner PG primary. kb-candidates.ttl 2,192 SHACL shapes (sh:Info) 병행 layer |
| `guide_usage_profiles` ✅ (G.2 완료) | 기존 PG 1,038 rows + `guide:GuideUsageProfile` OWL class 신규 정의 (ontology 가장 큰 갭 해결). guide_domain_profile.py PG primary |
| `penalty_rule_index` ✅ (G.3 완료) ⭐ | kosha-instances.ttl → PG 4,076 SR→PenaltyRule mappings. hazard_rule_engine PG primary. **penalty_accuracy +27.16%p** |
| `she_patterns_reasoner_derived` ✅ (G.4 완료) | view (77 pending_review SHE 노출, F.2 v3.1 link derived). Future matcher integration 의사결정 별도 sprint |
| `sr_inferred_relations` ✅ (Track A ② 완료, 2026-06-14) ⭐ | **추론된 SR↔SR 관계 materialized** — R-1 exemptedBy 107 + K-R2 coApplicable 16,429쌍(same-Chapter) + K-R4 dependsOn 35,165쌍(same-Hazard) = **PG 103,295 rows**. 서빙 Fuseki→PG SELECT 전환 (`/exemptions`·`/co-applicable`·`/depends-on`). `materialization_runs` PROV run-tracking 병행. commits `87d9e63`/`7c50304`/`e6140bb` |
| `ci_sr_mapping` | reasoner 도출 정식 매핑 |
| `penalty_rules` / `penalty_conditions` | deontic chain 추론 |

## Verification (각 Step 끝)

1. **rdflib parse** ✅
2. **Openllet consistency check** — Phase E.2 후
3. **기존 SHACL validation 회귀** ✅ (Conforms: True)
4. **CQ SPARQL coverage ≥ 80%** — Phase F.4 (Photo persist) 후
5. **8 photo + 2,360 synthetic regression** — Phase 0 인프라 통과
6. **OntoClean meta-property error = 0** ✅ (1 ACCEPT 권장)

## 핵심 통찰 한 줄 요약

> "현재는 SHE 부족분을 LLM 보강 JSON으로 메꾸고, 그 JSON이 정형 OWL/SWRL/SHACL로 점진 대체되면, 6단계 reasoner가 runtime LLM 없이도 같은 (실은 더 정밀한) 답을 deterministic하게 줌. 7단계에서 추론 결과를 PG로 재물질화하면 서빙은 PG SELECT만 (ms 단위, LLM 0회). Vision LLM만 영구 잔존. **Layer 4 (Ontology Learning)는 long-tail 도메인 적응을 위해 cross-cutting concern으로 architecture에 별도 명시되어야 함.**"

## 다음 세션 시작 가이드

```
1. CLAUDE.md (자동 로드)
2. docs/status/current-session.md (이 plan 진입점 명시)
3. 이 문서 (workplans/llm-accelerated-ontology-engineering.md)
4. 선택:
   - architecture/4-layer-architecture.md
   - architecture/ontology-learning-layer.md (Layer 4 상세)
   - architecture/llm-dependency-evolution.md
   - governance/ontology-learning-references.md (9 paper)
```

## 미해결 / 다음 세션 주의사항

1. **이번 세션 모든 산출물 origin/main push 완료** (Phase G.1-4 `d6b4589`/`5ee1709` + T4 fix `5edae0b` + T4 #1-4 `448a8d0`). 19 commits ahead of previous origin/main, 모두 push 완료. main HEAD = `448a8d0`.
2. **plan 임시 파일** (`.claude/plans/workplan-...md`)은 무시 가능 (이 정식 문서로 이전 완료)
3. **Phase E.2 (Openllet 정식 통합) 완료** (commit `3520cab`). **T2.B에서 kb-candidates.ttl 추가** + Fuseki container restart + SPARQL 검증 완료 (2216 NodeShapes).
4. **API 키 — 새 키 필요 시 `serving-team/08-app/backend/.env`에 갱신** (이전 5개 키는 사용자가 2026-05-17 회수 완료)
5. **T3.A 잔존 4 free-creates** (THF, CO, MOBILE_EQUIPMENT, WAREHOUSE): OpenAI strict mode enum의 edge-case (~99.6% 강제력). 별도 분석 또는 normalizer hard reject 후보.
6. **Fuseki Java v2 read-only blocker 해결됨**: T2.B `KoshaFusekiServer.java` sources array에 신규 TTL 추가 → docker rebuild → container recreate 패턴 정립. 다음 TTL 추가 시 동일.
7. **T2.D 1차 unicode bug** (Windows cp949): 처리됨 (모든 ✓✗→— → ASCII). 후속 sprint 스크립트 작성 시 동일 가이드 (PYTHONIOENCODING=utf-8 + python -u 또는 ASCII-only print).
