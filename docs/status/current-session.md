# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: **2026-05-19** — **Phase G PG materialization (G.1-4) + Tier 4 SWRL Pellet + T4 #1 후속 + moellab 비교 + ⭐ Hazard-Direct Architecture Pivot 완주 (Phase 1-5 + 8 photo 효과성 검증 PASS)**. 메인 HEAD `d63e25a`, worktree HEAD `5256573` (8 commits ahead).

## 🎯 Hazard-Direct Pivot — 단일 세션 완주 (2026-05-19) ⭐

본 세션의 핵심 성과. 23일 plan을 단일 세션에서 완주:

- **Phase 1 Day 1**: `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 추가 + 14개 표준 라벨 prompt (commit `acd2303`)
- **Phase 2 Day 1**: `generate_hazard_name_seed.py` (Sonnet 4.6 자동 seed) (commit `7a17b47`)
- **Phase 2-5 통합** (commit `7c97118`):
  - Phase 2 Day 2-7: Sonnet 19/21 accepted + 2 manual override → 21 vetted alias 등재
  - Phase 2 Day 3-4: `normalize_hazards_array()` 신규 함수 (hazard_normalizer.py)
  - Phase 3 Day 1-3: `hazard_to_guide_service.py` + analysis_pipeline `HAZARD_DIRECT_MODE` 통합
  - Phase 4 Day 1: `HazardItem` + `GuideRef` + `HazardGuideRelation` Pydantic + AnalysisResponse 확장
  - **Phase 5 Day 1**: 8 real-test-photo 실호출 → **25/25 (100%) 매핑** ⭐ (AC-2 ≥85% **PASS**)
- **Phase 4 Day 2** (commit `5256573`): Frontend `RiskOverviewPanel` 확장 + `HazardGuideRelationsPanel` 신규

8 photo eval 핵심 수치:
- 8/8 photos analyzed
- 25 hazards / **25 mapped (100%)** / 25 relations
- 48 standard_procedures (legacy 병행, 호환성 OK)
- 14 penalty paths (Phase G.3 차별점 보존)
- moellab overlap 18/37 (자연어 표현 차이)

Sprint plan + 결과: [../workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)
효과성 raw 데이터: [../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json](../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json)

이전 갱신:
- 2026-05-18 (저녁): Tier 1 재포함 + Tier 2 F.3 closing (T2.A-D) + Tier 3.A enum
- 2026-05-18 (오전): F.3 first batch + F.1 sprint (5 vetted aliases) + F.2 sprint (catalog v3.3, 5 axes × 481 codes)

이 문서는 다른 Claude/Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

불변 메타 규칙(팀 구조, 9단계 작업 모델, 폐기 용어, 절대 금지)은 루트 [../../CLAUDE.md](../../CLAUDE.md) 참고.

## 🚀 다음 세션 시작 시 먼저 읽을 문서 순서

### 즉시 (5분 내 컨텍스트 파악)
1. **[../../CLAUDE.md](../../CLAUDE.md)** — 자동 로드 (불변 규칙 + 팀 구조)
2. **이 문서** (status/current-session.md) — 현재 상태 + 다음 작업
3. **[../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)** ⭐ — **메인 plan, 이번 두 세션의 핵심 성과**

### 깊이 (필요 시)
4. [../architecture/4-layer-architecture.md](../architecture/4-layer-architecture.md) — Layer 0-4 전체 구조
5. [../architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Layer 4 7-module 정밀 설계
6. [../architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md) — LLM 의존 폐지 path
7. [../governance/ontology-learning-references.md](../governance/ontology-learning-references.md) — 9 학계 paper 요약

### 기존 baseline / 디렉토리 구조
8. [evaluation-baseline.md](evaluation-baseline.md) — 5번 enrichment baseline (변화 없음)
9. [../architecture/team-structure.md](../architecture/team-structure.md), [stage-mapping.md](../architecture/stage-mapping.md)
10. [../governance/repositories.md](../governance/repositories.md), [data-governance.md](../governance/data-governance.md)

## 📍 현재 상태 한 문장 요약

> "Phase 0/B/A/C + E-prep + E.2 + Phase 3 + F.3 first batch + F.1 + F.2 (이전) + Tier 1-3.A + **Phase G PG materialization (G.1: guide_domain_incompatibilities 2,016 rows + G.2: guide_usage_profiles 1,038 PG primary + G.3: penalty_rule_index 4,076 rows → penalty_accuracy +27.16%p ⭐ + G.4: she_patterns_reasoner_derived view)** + **Tier 4 후속 (AsymmetricProperty 패치로 Openllet 정상화 + SWRL Pellet 실행기 통합 → R-1: 107 + R-3: 3,579 inferred ⭐ + Pellet reporting 명시화)** + **T4 #1 후속 sprint (approve 57 / modify 19 / defer 1, batch promote -10.17%p VETOED → matcher refactor sprint plan 작성) + moellab.info/ohs 위험요소 비교 (37/37 합리적, architecture pivot 후보 식별: hazard-direct)**. 사용자 구조 step 4 본격 입증. 다음 1순위: hazard-direct architecture pivot (sprint plan 작성 TBD)."

## 🎯 핵심 성과

### Phase G PG materialization + Tier 4 후속 (2026-05-19)

**사용자 구조 step 4 본격 입증**: "온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영" 완성.

- **Phase G.1** (commit `d6b4589`) — `core:Incompatibility` ontology TBox 보강 + `guide_domain_incompatibilities` PG (2,016 rows: 8 vetted + 2,008 candidate, T2.D 8/8 PASS 자동 반영) + `shadow_reasoner.py` PG primary + JSON fallback. 10/10 sample equality. PG p50 0.4μs (cache warm).
- **Phase G.2** (commit `2f7ef92`) — `guide:GuideUsageProfile` OWL class **전체 신규 정의** (14 properties, ontology 가장 큰 갭 해결: SHACL shape는 있었으나 OWL class 부재) + 기존 PG `guide_usage_profiles` (1,038 rows) ontology backed + `guide_domain_profile.py` PG primary. Gate 3 PASS, `false_negative_rate -0.0189` 개선.
- **Phase G.3** (commit `8ddc2c7`) — `penalty:appliesTo/penaltyType/maxFine/maxPrisonYears` ontology 보강 + 신규 PG `penalty_rule_index` (**4,076 SR→PenaltyRule mappings**, kosha-instances.ttl → PG 자동 추출) + `hazard_rule_engine._load_penalty_index` PG primary. **penalty_accuracy +27.16%p ⭐, overall_accuracy +18.81%p ⭐** (TTL parse 우회 + 더 완전한 mapping).
- **Phase G.4** (commit `434f35f`) — 신규 PG view `she_patterns_reasoner_derived` (77 F.2 v3.1 link SHE 노출, read-only architectural layer) + Openllet `inferred=0` 근본 원인 분석 (law:modifies AsymmetricProperty + inverseOf 충돌 = FunInv 경고).
- **Tier 4 AsymmetricProperty 패치** (commit `5edae0b`) — `kosha-ontology-v2.owl` + `.formatted.ttl`에서 `law:modifies`의 `owl:AsymmetricProperty` 제거 + Fuseki rebuild + container recreate. **FunInv 경고 사라짐 + SPARQL 추론 작동 검증** (`hazard:FALL_FROM_HEIGHT rdfs:subClassOf+ ?super` → `owl:Thing` + `hazard:FALL`).
- **Tier 4 #4 Pellet reporting** (commit `1bacd44`) — `KoshaFusekiServer.java`에 `getDeductionsModel()` 명시 호출 + lazy materialization 안내 부연.
- **Tier 4 #2 AdministrativeFine** (commit `70d2862` 일부) — Decision Skip: `withAdministrativeFine: 0`은 design intent (RULE 조문은 OSHA 제38/39 위임으로 criminal-only). OSHA 제175조 admin은 별도 Pipe-A 확장 sprint. 문서: `docs/dev-notes/t4-administrative-fine-scope-decision.md`.
- **Tier 4 #1 77 SHE matcher 통합** (commit `70d2862` 일부) — 5 SHE batch 시도 → she_accuracy -7.07%p VETOED (~1.4%p/SHE), rollback 정상 작동 + utf-8 fix. 근본 원인: matcher의 broadness 처리 (promote만으로 해결 불가). 별도 sprint 이관. 문서: `docs/dev-notes/t4-77-she-matcher-integration-decision.md`.
- **Tier 4 #3 SWRL Pellet 실행기 통합** (commit `448a8d0`) ⭐ — 신규 `kosha-rules-r1-r3-swrl.ttl` (R-1 exemptedBy + R-3 HighSeverityPenalty, OWL/RDF SWRL serialization) + KoshaFusekiServer.java sources + docker rebuild. **SPARQL 검증**: R-1 `?s core:exemptedBy ?o` → **107 inferred**, R-3 `?s a penalty:HighSeverityPenalty` → **3,579 inferred** (severityScore ≥ 5와 100% 일치, swrlb:greaterThanOrEqual built-in 정상 평가).

**4-Layer 흐름 완전 입증** (Phase G + T4 후):
```
Vision LLM (T3.A enum) → normalizer → PG (G.1-3 materialized) → 답변
                                       ↑
       Fuseki + Pellet ← TTL ← Ontology TBox (G.1-3 patches) ← Mining (F.3.0/3.2)
                                                              + SWRL rules R-1/R-3 (T4 #3)
                                                              + SHACL shapes (T2.B)
```

main HEAD: `3502eff` (T4 #1 후속 + moellab 비교 후). origin/main 동기화 완료.

### T4 #1 후속 sprint + moellab 위험요소 비교 (2026-05-19)

**T4 #1 후속 sprint** (commits `a26c888` → main `1bfd6b8`) — 77 pending_review SHE matcher 통합의 별도 sprint 전 단계 1차 정리:
- 77 SHE manual review (사용자 1차 분류, single-file HTML UI 도구):
  - **approve 57 / modify 19 / defer 1 / reject 0** (사용자가 패턴 폐기할 만큼 비현실적인 것은 없다 판정)
  - modify 19 → 5개 테마 자동 분류 (PPE 과도 8 + 사진불가 3 + 좁은조건 4 + 비현실 3 + 도메인불일치 1)
- Step 2 approve 57 batch promote 재시도: **Batch 1 (5 SHE) → she_accuracy -10.17%p VETOED, rollback 자동**. 5회 audit history 모두 동일 패턴 (-7~-10%p) → **matcher 자체 로직 문제 입증**
- Step 3 patch proposal 자동 생성 (19/19 PG-only patch, ontology 영향 없음)
- 다음 sprint plan: [`she-matcher-broadness-refactor.md`](../workplans/she-matcher-broadness-refactor.md) — 7-day plan (broadness-aware ranking + PPE state weakening + `approved_derived` 신규 + SHACL shape + PG→TTL export)
- Runbook: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)

**moellab.info/ohs 위험요소 비교 분석** (commit `833dcd7` → main `3502eff`) — 우리 프로젝트의 초안과 dev server 비교:
- 비교 범위: GPT 직접 출력 `hazards[]` 만 (외부 시스템 부속 legal_reference / related_guides / checklist / resources 제외)
- 8개 사진 / **37 hazards 식별 모두 합리적** (false positive 없음, 자연어 카테고리 직관적: "끼임/협착", "전도/미끄럼", "추락" 등)
- `preventive_measures` 평균 3-4개 / hazard, 사진 context 반영
- **architecture pivot 후보 식별** ⭐:
  - Vision LLM HAZARD_DIRECT_SCHEMA → hazards[] 그대로 표시 (moellab 스타일)
  - hazard.name → catalog 529 codes 매핑 (T1.C alias 활용)
  - 우리 ontology reasoning으로 Guide 추천 (moellab title_match 한계 회피)
  - Guide procedure + GPT preventive 병기 (사용자 화면)
  - SHE matcher 회귀 부담 본질적 감소 (Step 2 -10.17%p 우회)
- 다음 sprint plan: `docs/workplans/hazard-direct-architecture-pivot.md` (TBD, 별도 plan)
- Runbook: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)

### Tier 1 재포함 + Tier 2 F.3 closing + Tier 3.A (2026-05-18 저녁)

- **Tier 1 재포함** (commit `93c49fe`): 직전 `b66fa36` commit이 T1.B npz 바이너리 + 마이그레이션 스크립트만 staged하고 T1.A/T1.C 코드 working tree만 잔존했던 누락 발견 + 재포함:
  - T1.A `promote_she_review.py` — `rollback_batch` `result.rowcount` + 사후 verification + `stuck_ids` 검출 (5 stuck SHE bug 재발 방지)
  - T1.B `auto_register_aliases.py` + `recover_catalog_mismatch.py` — numpy `load/save_embedding_cache` (~87% 크기 축소 적용)
  - T1.C `hazard_normalizer.py` step 4.5 `_log_alias_usage()` + `promote_aliases.load_meta_latest` 'used' action 집계 (`promote_aliases --auto` production-ready)
- **T2.A F.3.1 pyshacl reasoner shadow channel** (commit `93c49fe`): 신규 `pyshacl_shadow_validator.py` (offline batch CLI) + `shadow_reasoner.py` (serving runtime, lazy module cache, ~50μs/photo) + `analysis_pipeline.py` `_append_analysis_log`에 `reasoner_rejects` kwarg 추가. **2580 analysis_log rows → 859 reasoner_rejects** (62.8% processable rows). Gate 3 PASS.
- **T2.B F.3.4 KB compile + Fuseki reload** (commit `78886b3` + `ac98d4c`): 신규 `compile_kb_to_ttl.py` → `kb-candidates.ttl` (2200 → 2192 shapes after T2.D, sh:Info severity). `KoshaFusekiServer.java` sources array에 kb-candidates.ttl 추가. docker image rebuild (`docker-fuseki:latest` sha256 `08837972`). container `docker compose up -d --force-recreate fuseki` 완료. **SPARQL 검증**: `SELECT COUNT(?s) WHERE { ?s a sh:NodeShape }` → **2216 NodeShapes** (kb-candidates 2192 + serving 24). Fuseki Java v2 read-only blocker 해결 (rebuild + recreate 패턴).
- **T2.C F.3.5 drift detection + Makefile f3-* 통합** (commit `78886b3`): 신규 `f3_drift_check.py` (6 metric 추적, exit code 0/1/2). `Makefile` f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle targets. cron 권장: `0 2 * * 0 cd /path && make f3-weekly-cycle`.
- **T2.D 8 F.3.2 candidates 1-by-1 vetted promotion** (commit `ac98d4c` → main `325ad37`): 신규 `promote_f32_per_candidate.py` (1-by-1 + full replay + Gate 3 wrap + 자동 rollback). **8/8 candidate PASS** (예상 5-6 PASS 대비 100% 통과). 모든 F.3.2 axiom vetted 승격 (vetted_count 0 → 8). 1차 실행 시 cp949 unicode bug 발견 → 모든 ✓✗→— 를 ASCII로 교체 후 PYTHONIOENCODING=utf-8 + python -u 로 재실행 성공.
- **Tier 3.A Closed Vocab Schema Enum** (commit `606b91f` → main `b237e78`): `openai_client.py` `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum. `_load_catalog_codes()` lazy module-level load (12.6KB schema JSON, OpenAI strict mode 한도 내). Gate 3 PASS (delta noise 수준). **analysis_log normalizer_unknown_codes 76 → 4 (−94.7%)**. 잔존 4건 (THF, CO, MOBILE_EQUIPMENT, WAREHOUSE) — OpenAI strict mode enum의 edge-case 누락 (강제력 ~99.6%).

**효과 정리** (Layer 4 Module 4.4 closed loop 완성):
```
mining (F.3.0/3.2)   →   verify (F.3.3 Gate 3)   →   compile (T2.B compile_kb_to_ttl.py)
                                                     ↓
monitor (T2.C f3_drift_check.py)   ←   deploy (Fuseki container restart + SPARQL endpoint)
```

main HEAD: `b237e78` (Tier 3.A merge), 직전 `325ad37` (Tier 2 merge).

## 🎯 핵심 성과 (2026-05-16 ~ 17)

### Phase 0/B/A/C (LLM 자율 도메인 보강) — 완료
- **baseline_v2**: she_accuracy 55.81% → **60.72%** (+4.9%p), overall 13.31% → **15.25%** (+1.94%p)
- **active_v2**: positive avg_procedures 3.07 → **2.26** (−26.4%) — LLM rerank 효과
- **8 real-test-photo**: 4/5 over-promote 차단 확인 (지게차/영세제조/포크레인/음식점)
- **Phase C 자율 학습**: 2,528 analysis_log + 31개 신규 incompatibility 자율 채택

### Phase E-prep + E.2 (Openllet 통합) — 완료
- **Step 1**: 50 CQ + 55 class layer (B 26/A 20/Bridge 9) + 7 reuse scorecard
- **Step 2**: kosha-ontology-v2.owl (BFO + LKIF imports + 64 subClassOf)
- **Step 3**: kosha-disjoint-axioms.ttl (84 industries, 2,192 disjoint) + 22 SWRL + 26 SHACL
- **Step 4**: OntoClean 13 violations → **1** (92% 자동 수정)
- **E.2**: Fuseki Java가 v2 ontology + disjoint + SHACL + 172 subClassOf 로드 (commit `3520cab`)
- **Verification**: SHACL Conforms: True ✅, Openllet inference 정상

### Phase 3 (catalog v4 + SHE patterns + reasoning catch) — 완료
- **Phase 3A audit**: 1,914 synthetic codes hybrid ensemble 검증
- **Phase 3B catalog v4**: +170 신규 codes + 169 sub + 193 aliases
- **Phase 3C direct LLM SHE patterns**: 498 신규 → validation 후 누적 **1,616** PG she_patterns
- **Phase 3D**: synthetic v1~v10 EN enum transform + baseline_v3
- **Phase 3 validation**: ontology reasoning이 LLM 환각/과대추정 **1,902건 catch** (보고서 `docs/status/reasoning-catch-effectiveness-2026-05-17.md`)
- **8 real-test-photo 라이브**: 평균 사진당 1건 부적절 추천을 reasoning이 사용자 앞에서 reject

### Phase F.3 자율 axiom learning loop — 첫 정식 단계 완료 ⭐
- **F.3.0 (commit `8ff40d7`)**: 2,525 excluded entries 5 카테고리 분류 — `axiom_missing 36.44%` (920건, **210 unique pair**) → PROCEED_F3
- **F.3.5-prep (commit `ebe1011`)**: `analysis_log.jsonl`에 Runtime 4번 환류 채널 3 신규 필드 (`normalizer_unknown_codes`, `she_match_count`, `raw_vision_features`)
- **C cleanup (commit `2ea800d`)**: `guide_domain_incompatibilities.json` 2,232 entries 100% KO→EN translated (mining 정확도 normalize)
- **F.3.2 first batch (commit `9219c7c`)**: 49 LLM verify → **8 accepted candidate axiom** (incompatible_count 2,232 → 2,240)
- **Merge `11e46c6`** + GitHub push 완료
- **A hot-fix (commit `a841a0b` → main `d0b2262`)**: `raw_vision_features` 타입을 `dict` → `list`로 수정. ebe1011에서 dict() 변환 시 `risk_feature_candidates`(array)를 받아 `ValueError: dictionary update sequence element #0 has length 4; 2 is required` 발생. 2,360 synthetic replay에서 1,700 errored 원인. 3-case quick test로 0 errored 검증 후 push.
- **F.3.3 Gate 3 regression PASS (commit `eb7843f` → main `5b10980`)**: 2,360 synthetic replay 전체 valid, 0 errored. she_accuracy delta `-0.0013` (노이즈 범위), 모든 metric 회귀 없음. 8 candidate axiom **production-safe 검증 완료** — 수동 vetted 승격 가능 (50회 대기 불필요). 보고서 `docs/status/f33-gate3-regression-2026-05-17.md`.
- **14-docs sweep (commit `af26e13` → main `f5bde60`, HEAD)**: F.3 first batch + hot-fix + F.3.3을 14개 docs 전 영역(README/architecture/status/workplans/governance/backlog) 반영. 메타 일관성(current-session ↔ evaluation-baseline ↔ workplans) cross-check 완료.

### 학계 reference 통합 — 완료
- 9 paper 분석 (`ontology-team/reference-article/`)
- Layer 4 = 7 module 정밀 구성
- 우리 차별점: deontic 도메인 + 한국어 + asymmetric trust + Task C SOTA + Task D 학계 미답

## 📦 신규 산출물 (2026-05-19 Phase G + T4 — origin/main push 완료)

**Phase G 신규 산출**:
- Ontology TBox 4 patches:
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl` (G.1: `core:Incompatibility` class + 5 metadata properties)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-guide-profile-patch.ttl` (G.2: `guide:GuideUsageProfile` class + 14 properties + cardinality restrictions)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-penalty-relations-patch.ttl` (G.3: 4 relation/datatype properties)
  - `ontology-team/06-reasoning/ontology/kosha-rules-r1-r3-swrl.ttl` (T4 #3: R-1 exemptedBy + R-3 HighSeverityPenalty SWRL OWL serialization)
- Ontology TBox 1 수정: `kosha-ontology-v2.owl` + `.formatted.ttl` (`law:modifies`의 `owl:AsymmetricProperty` 제거, T4 fix)
- PG schema 3 신규:
  - `serving-team/07-materialization/pg-sync-scripts/schema_guide_domain_incompatibilities.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_penalty_rule_index.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_she_patterns_reasoner_derived.sql`
- PG import scripts 2 신규:
  - `serving-team/07-materialization/pg-sync-scripts/import_domain_incompatibilities_to_pg.py`
  - `serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py`
- Validation scripts 1 신규: `serving-team/07-materialization/validation-scripts/sample_query_equality.py`
- Bench script 1 신규: `serving-team/08-app/backend/scripts/bench_shadow_reasoner.py`
- PG ORM 3 신규 (`app/db/models.py`): `PgGuideDomainIncompatibility`, `PgPenaltyRoute`, `PgPenaltyRuleIndex`
- Backend code 4 수정 (PG primary):
  - `app/services/shadow_reasoner.py` (G.1, JSON fallback 유지)
  - `app/services/guide_domain_profile.py` (G.2)
  - `app/services/hazard_rule_engine.py` (G.3, `_load_penalty_index_from_pg()`)
  - `app/services/openai_client.py` (T3.A enum, 이전 sprint)
- Fuseki Java 수정: `KoshaFusekiServer.java` (kb-candidates + SWRL TTL sources 추가 + Pellet reporting 명시화)
- Makefile: `phase-g-help/phase-g1-schema/import/verify/phase-g-verify` targets
- Manual review 자산: `data-team/05-enrichment/runtime-artifacts/pending_review_she_for_manual_review.json` (77 SHE 8-axis + visual_triggers)

**신규 dev-notes (이번 세션, 7 runbooks/decisions)**:
- [phase-g.1-domain-incompatibilities-pg.md](../dev-notes/phase-g.1-domain-incompatibilities-pg.md)
- [phase-g.2-guide-usage-profiles-pg.md](../dev-notes/phase-g.2-guide-usage-profiles-pg.md)
- [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md)
- [phase-g.4-she-patterns-reasoner-derived.md](../dev-notes/phase-g.4-she-patterns-reasoner-derived.md)
- [t4-administrative-fine-scope-decision.md](../dev-notes/t4-administrative-fine-scope-decision.md)
- [t4-77-she-matcher-integration-decision.md](../dev-notes/t4-77-she-matcher-integration-decision.md)
- [t4-swrl-pellet-integration.md](../dev-notes/t4-swrl-pellet-integration.md)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-19 T4 #1 후속 + moellab 비교 — origin/main push 완료)

**T4 #1 후속 산출 (commit `a26c888` → main `1bfd6b8`)**:
- 신규 dev-note: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)
- 신규 sprint plan: [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day, hazard-direct pivot 후 보조 track으로 통합 또는 후행)
- 신규 script 2개:
  - `data-team/05-enrichment/llm-scripts/patch_she_visual_triggers.py` (Step 3 patch proposal 생성)
  - `data-team/05-enrichment/runtime-artifacts/she_review_ui.html` (94KB single-file 검토 UI)
- 신규 정본 자산:
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_REVIEWED.json` (77/77 사용자 검토 결과)
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_PATCH_PROPOSAL.json` (19/19 자동 patch)
- 수정: `data-team/05-enrichment/llm-scripts/promote_she_review.py` (`--only-from-review-json` 옵션)

**moellab 비교 산출 (commit `833dcd7` → main `3502eff`)**:
- 신규 dev-note: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)
- 보조 (git 미추적, 다음 세션 재현 자산): `.compare_moellab/*.json` (8개 사진 raw API 응답)
- 수정 1개: `.gitignore` (외부 raw 캡처 + manual review 보조 파일 + auto-gen logs 추가)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-18 저녁 Tier 1-3.A — main에 push 완료)

**신규 파일**:
- `data-team/05-enrichment/llm-scripts/pyshacl_shadow_validator.py` (T2.A offline batch)
- `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` (T2.B)
- `data-team/05-enrichment/llm-scripts/f3_drift_check.py` (T2.C)
- `data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py` (T2.D)
- `data-team/05-enrichment/llm-scripts/_migrate_embedding_cache_to_npz.py` (T1.B 1회성)
- `serving-team/08-app/backend/app/services/shadow_reasoner.py` (T2.A serving runtime)
- `ontology-team/06-reasoning/ontology/kb-candidates.ttl` (T2.B output, 2192 SHACL shapes)
- `data-team/05-enrichment/runtime-artifacts/f32_per_candidate_promotion_results.json` (T2.D summary)
- `data-team/05-enrichment/runtime-artifacts/f3_drift_log.jsonl` (T2.C 시계열)
- `data-team/05-enrichment/runtime-artifacts/kb_candidates_compile_audit.json` (T2.B audit)

**수정 파일**:
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` (T2.A: happy + skipped path 모두 `shadow_validate` + `reasoner_rejects` kwarg)
- `serving-team/08-app/backend/app/services/hazard_normalizer.py` (T1.C: step 4.5 `_log_alias_usage`)
- `serving-team/08-app/backend/app/integrations/openai_client.py` (T3.A: 529 codes enum + `_load_catalog_codes()`)
- `ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java` (T2.B: sources array + kb-candidates.ttl)
- `data-team/05-enrichment/llm-scripts/promote_she_review.py` (T1.A: rollback verification + stuck_ids)
- `data-team/05-enrichment/llm-scripts/auto_register_aliases.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/recover_catalog_mismatch.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/promote_aliases.py` (T1.C: 'used' action 집계)
- `Makefile` (T2.A-D: f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle)

**신규 docs (이번 세션 저녁)**:
- [F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — T2.A/B/C/D 통합 runbook
- [T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md) — T3.A runbook
- [t2d-per-candidate-promotion-2026-05-18.md](t2d-per-candidate-promotion-2026-05-18.md) — T2.D 8/8 PASS 보고
- [t3a-closed-vocab-schema-enum-2026-05-18.md](t3a-closed-vocab-schema-enum-2026-05-18.md) — T3.A 76→4 분석

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (오늘 후반 — main에 push 완료, 2026-05-17~18 오전)

오늘 후반 (F.3 sprint + F.3.3 + sweep) commits + merge:
- `classify_reject_reasons.py` + 산출 jsonl/json + sample_100 (F.3.0)
- `analysis_pipeline.py` 수정 (Runtime 4번 hook 3 필드, A) + hot-fix (`raw_vision_features` list)
- `translate_incompat_industries.py` + KB 변환 (C)
- `mine_missing_axioms.py` + 8 candidate (B)
- `data-team/05-enrichment/runtime-artifacts/replay_post_f32.json` (F.3.3 replay)
- `docs/status/f30-reject-reason-classification-2026-05-17.md` (F.3.0 보고서)
- `docs/status/f33-gate3-regression-2026-05-17.md` (F.3.3 PASS 보고서)
- `docs/` 전반 14 docs sweep (`af26e13`): README/architecture/status/workplans/governance/backlog

## ⚠️ 다음 세션 시작 시 주의사항

1. **현재 작업 worktree**: `.claude/worktrees/trusting-chandrasekhar-7b2041/` (claude/trusting-chandrasekhar-7b2041 branch). **origin/main 동기화 완료** (`448a8d0`). 정리 시 worktree 제거 가능.
2. **PG materialization runtime path**: shadow_reasoner (G.1) + guide_domain_profile (G.2) + hazard_rule_engine._load_penalty_index (G.3) 모두 **PG primary + JSON/TTL fallback** 패턴. PG cache 갱신 = backend restart 필요. PG row 변경 시 `_load_*_from_pg()` 캐시 reset 또는 service 재시작.
3. **Fuseki container 상태**: `kosha-fuseki` 신규 image (`docker-fuseki:latest`, 981,485 triples 로드, kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 포함). SWRL R-1: 107 + R-3: 3,579 inferred triples 검증됨. 다음 docker compose 시 동일 image 자동 사용.
4. **Pellet inferred count log "0"은 정상**: `infModel.size()` lazy materialization quirk. 실제 추론은 SPARQL query 시 on-demand 실행 (검증 완료). 로그 메시지에 안내 포함.
2. **API 키**: `serving-team/08-app/backend/.env`에 OPENAI_API_KEY 설정됨. 정상 작동 확인 (T2.D 8회 replay 모두 성공)
3. **8 F.3.2 candidate axiom 모두 vetted 승격 완료** (T2.D 8/8 PASS). vetted_count 0 → 8. 잔여 candidate-only 진행 시 동일 `promote_f32_per_candidate.py --apply` 패턴.
4. **Fuseki container 새 image 적용 중**: `docker-fuseki:latest` sha256 `08837972` (kb-candidates.ttl 17,618 triples 로드, 총 981,409 triples). `docker compose up -d`에 동일 image 자동 사용. 다음 TTL 추가 시 동일 (Java sources 수정 + rebuild + recreate).
5. **T2.D 1차 cp949 unicode bug 처리됨**: `promote_f32_per_candidate.py` 모든 ✓✗→— → ASCII 교체. 재실행 시 `PYTHONIOENCODING=utf-8 python -u` 권장.
6. **T3.A 잔존 4 free-creates**: THF, CO, MOBILE_EQUIPMENT, WAREHOUSE — OpenAI strict mode enum의 edge-case (~99.6% 강제력, 0.4% 누락). 별도 분석 후보 (또는 normalizer step에서 hard reject 가능).
7. **편의점 KO unmapped** (이전 sprint에서 발견): `industry_ko_to_en_map.json`에 `편의점 → CONVENIENCE_STORE` 매핑 추가됨 (Quick Win Task 3). T2.D 후보 [6/8] 편의점×METAL_MACHINING가 vetted 통과 확인.
8. **A hook 항상 실행됨** (Quick Win Task 2 + T2.A): `_apply_llm_rerank`의 early-return 3 경로 모두 `_log_skipped_analysis` 호출 → analysis_log에 `mode=off_skipped_*` 기록. T2.A `reasoner_rejects` field도 happy + skipped path 모두 추가됨.
9. **stash@{0}**: `WIP on main: ca55ac6` (이전 세션 8 real-test-photo PNG/JPG untracked). 무관함, 보존

## 🛣️ 다음 작업 우선순위

### ✅ 완료: Phase G — PG 재물질화 (G.1-4, 2026-05-19)
- G.1: `guide_domain_incompatibilities` PG (2,016 rows, ontology `core:Incompatibility`)
- G.2: `guide_usage_profiles` PG + `guide:GuideUsageProfile` 신규 OWL class (ontology 가장 큰 갭 해결)
- G.3: `penalty_rule_index` PG (4,076 rules) — **penalty_accuracy +27.16%p ⭐**
- G.4: `she_patterns_reasoner_derived` view + Openllet root cause 분석
- Runbooks: `docs/dev-notes/phase-g.{1,2,3,4}-*.md`

### ✅ 완료: Tier 4 후속 (2026-05-19)
- AsymmetricProperty 패치 (Openllet SPARQL 추론 검증)
- T4 #4 Pellet reporting 명시화
- T4 #2 AdministrativeFine: Skip (design intent)
- T4 #1 77 SHE: 별도 sprint 이관
- T4 #3 SWRL Pellet 실행기 통합 (R-1: 107 + R-3: 3,579 inferred) ⭐
- Runbooks: `docs/dev-notes/t4-{administrative-fine,77-she-matcher,swrl-pellet}-*.md`

### ✅ 완료: Tier 1 재포함 (T1.A/B/C, 2026-05-18 저녁)
- T1.A promote_she_review rollback verification + stuck_ids 검출
- T1.B npz cache load/save (95MB → 12MB, 87% 축소)
- T1.C hazard_normalizer step 4.5 alias usage tracking + promote_aliases 'used' 집계

### ✅ 완료: Tier 2 F.3 closing (T2.A/B/C/D, 2026-05-18 저녁, Module 4.4 closed loop)
- T2.A pyshacl reasoner shadow channel (offline batch + serving runtime)
- T2.B KB compile to TTL + Fuseki Java edit + docker rebuild + container restart + **SPARQL 2216 NodeShapes 검증**
- T2.C drift detection + Makefile f3-* 통합
- T2.D 8/8 F.3.2 candidates vetted (예상 5-6 대비 100% 통과)
- Runbook: [../dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md)
- Makefile: `make f3-help` 참고

### ✅ 완료: Tier 3.A Closed Vocab Schema Enum (2026-05-18 저녁)
- `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum
- **free-creates 76 → 4 (-94.7%)** (Hybrid Day 3 partial → 본격 schema-level enum)
- Gate 3 PASS (delta noise 수준)
- Runbook: [../dev-notes/T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md)

### ✅ 완료: Phase F.1 — Vocabulary auto-registration (Day 1-7, 2026-05-18 오전)
- 5 vetted aliases (FALL_FROM_HEIGHT, FINGER_AMPUTATION 등) + 1 candidate
- 4-Gate closed loop: embedding + LLM verify + regression + asymmetric trust
- Runbook: [docs/dev-notes/F.1-auto-register-aliases.md](../dev-notes/F.1-auto-register-aliases.md)
- Makefile: `make f1-help` 참고

### ✅ 완료: Phase F.2 — Taxonomy Discovery (Day 1-7, 2026-05-18 오전)
- catalog v3.1 (404 codes, 3 axes) → **v3.3 (481 codes, 5 axes)**
- 신규 axis: ppe_state (50 codes), environmental (18 codes)
- 790 SHE OTHER → specific (Sonnet 4.6, Gate 3 PASS)
- 79 v3.1-link SHE (status=pending_review, 수동 승격 대기)
- Runbook: [../dev-notes/F.2-taxonomy-discovery.md](../dev-notes/F.2-taxonomy-discovery.md)
- Makefile: `make f2-help` 참고

### 다음 작업 우선순위 (T4 #1 후속 + moellab 비교 완료 후):

**1순위: hazard-direct architecture pivot** ⭐ (sprint plan 작성 완료, Phase 1 즉시 시작 가능):
- 📄 **Plan: [docs/workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)** (3주, 5 Phase × 평균 5일)
- 핵심 가설: Vision LLM이 위험요소(hazards) 자연어로 직접 출력 → 우리 ontology로 Guide 추천 → SHE matcher 의존도 본질 감소
- moellab(우리 초안)의 GPT 직접 hazard 식별이 8/8 사진 / 37/37 합리적 (Step 2 SHE matcher -10.17%p VETOED와 대조)
- Phase 1: HAZARD_DIRECT_SCHEMA + GPT prompt 갱신 (~3일)
- Phase 2: hazard.name → catalog 529 codes alias 매핑 (T1.C 확장 + Sonnet 4.6 seed, ~1주, ~$0.20)
- Phase 3: hazards-based Guide 추천 layer + A/B 검증 (parallel/primary/off mode, ~1주)
- Phase 4: 응답 schema 확장 + Frontend `RiskOverviewPanel`/`HazardGuideRelationsPanel` (~3일)
- Phase 5: Gate 3 통합 + 정본 문서 + Architectural debt 3가지 해소 (~3일)
- 결정 완료: seed = Sonnet 4.6 자동 + 사용자 vetted / SHE matcher refactor = 후행 별도 sprint

**2순위: SHE matcher broadness-aware refactor** (T4 #1 후속, 보조 track):
- [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day plan)
- hazard-direct pivot의 Phase 3 보조 track으로 통합 또는 후행 (SHE matcher 의존도는 본질적으로 감소하지만 fallback으로 유지)

**3순위: OSHA admin penalty Pipe-A 확장** (T4 #2 후속, 4-6h):
- 제175조 administrative fines (6단계, 5천만원~300만원) 추출. `step1_extract_penalties.py` 확장. 결과 → penalty_rule_index에 sanction_type='AdministrativeFine' rows 추가.

**4순위: SWRL 확장 + 학계 작업**:
- **R-4~R-30 SWRL OWL 변환** (1-2주): `kosha-rules-v2.swrl` 의사코드 30개 모두 OWL/RDF SWRL serialization으로 변환 (T4 #3 패턴 답습). 각 rule fired triple count 검증.
- **8-photo real-test eval** (`make f1-eval`, ~$0.40 + 8분): Phase G + T4 효과 실제 사진 검증.

**3순위 (Tier 4 중장기, 1-3개월) — 별도 plan**:
- F.5 GraphRAG (Module 4.6, 2주)
- F.4 CQ Reverse + Photo persist (Module 4.5, 3-4주)
- Phase J OBO Foundry 등재 (1-3개월) — **사용자 명시: 나중에 별도 계획**
- Two-way CoT prompt 전환 (1일, +0.2 F1 기대)
- OOPS! Pitfall Scanner 통합 (2-3h)

**T3.A 잔존 4건** (THF/CO/MOBILE_EQUIPMENT/WAREHOUSE): 별도 sprint 또는 normalizer hard reject로 점진 보강.

**비채택** (도메인 부적합 — 2026-05-17 결정):
- **OntoGPT 통합** — F.1 alias mining에 자체 LLM verify(`mine_missing_axioms.py` 패턴)로 충분, 추가 가치 없음
- **OntoClean 메타-validation** — 170 atomic codes / 498 SHE patterns에 비용 비대칭. BFO+LKIF 62-class TBox 통합(Phase E-prep)에서만 유효했으며 이미 13→1 완료. F.1은 taxonomy 변경 없는 alias 등재 작업이므로 적용 영역 외

## 🔧 OHS 실행 (시연용)

PG + Fuseki 컨테이너 (이미 동작 중):
```bash
docker ps | grep -E 'kosha-pg|kosha-fuseki'
```

backend + frontend dev-up (WSL):
```bash
cd /mnt/c/project/arch-bot
# baseline 시연 (LLM rerank off, 비용 0)
make dev-up
# 또는 LLM rerank 활성 시연 (Phase B+A.4 효과 시각화)
LLM_RERANK_MODE=active make dev-up
make dev-check
```

브라우저: http://127.0.0.1:5173/ohs/

8 real-test-photo: `C:\project\arch-bot\real-test-photo\`

## 📊 검증 명령 (회귀 확인)

```bash
# rdflib parse + Local consistency check
cd /mnt/c/project/arch-bot
/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/local_consistency_check.py --skip-instances --skip-sparql

# 2,360 synthetic replay (baseline 측정)
cd /mnt/c/project/arch-bot/serving-team/08-app/backend
DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
.venv/bin/python -u scripts/replay_synthetic_observations.py \
  --output /tmp/replay_check.json

# regression gate (baseline vs current)
.venv/bin/python scripts/regression_gate.py /tmp/replay_check.json
```

## 🌟 핵심 통찰 (다음 세션 결정 기준)

1. **현재 SHE 부족분 = LLM 보강 JSON으로 메꿈** → 정형 OWL/SWRL/SHACL로 점진 대체
2. **Vision LLM만 영구 유지** (인식 영역). Semantic reasoning은 reasoner로 이전
3. **Layer 4 (Ontology Learning) 별도 layer 필수** — long-tail 도메인 자율 적응
4. **closed vocabulary 기각** (사용자 결정) — 학계 SOTA와 일치
5. **자율 등재 위험성** — 4-gate 검증 (embedding + multi-LLM + counter-example + asymmetric trust)
6. **우리 시스템의 학계 차별점** = LKIF-Core × BFO + 한국어 + asymmetric trust + Task C SOTA + Task D 미답
7. **7단계 PG 재물질화** = reasoner 추론 결과 → PG → 서빙 ms 응답

## 5단계/6단계 전환 시각화

```
[현재 5단계] LLM 의존 hybrid
   Vision LLM → Normalizer → SHE 매칭 → LLM enrichment lookup → Phase B LLM rerank → dynamic KB

[Phase E.2 후 6단계] declarative reasoning
   Vision LLM → BFO Photo instance → Openllet OWL DL → SWRL/SHACL → 정형 추론

[Phase F+ Layer 4] cross-cutting 자율 학습
   Layer 1-3 데이터 → 7 module → vocabulary/class/rule 자동 등재 → asymmetric trust

[Phase G 7단계] PG materialize
   reasoner 결과 → PG table → 서빙 PG SELECT only (ms, LLM 0회)
```
