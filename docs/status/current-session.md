# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: **2026-05-18 (저녁)** — **Tier 1 재포함 + Tier 2 F.3 closing 완료 (T2.A-D) + Tier 3.A enum 완료**. 메인 HEAD `b237e78`.

이전 갱신: F.3 first batch + F.1 sprint (5 vetted aliases) + F.2 sprint (catalog v3.3 5 axes × 481 codes).

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

> "Phase 0/B/A/C + E-prep + E.2 + Phase 3 + F.3 first batch + F.1 + F.2 (이전) + **F.3 closing 완료 (T2.A pyshacl reasoner shadow + T2.B Fuseki SPARQL 2216 NodeShapes 검증 + T2.C drift detection + T2.D 8/8 candidates vetted promotion PASS)** + **Tier 3.A Closed Vocab Schema Enum (529 codes, free-creates 76→4 = −94.7%, Gate 3 PASS)**. Layer 4 Module 4.4 (Axiom Discovery) closed loop 완성. 다음: T3.A 잔존 4건 조사 / 8-photo real eval / Tier 3 후속 (3B F.4 CQ 또는 3C Phase G PG)."

## 🎯 핵심 성과

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

1. **현재 작업 worktree**: `.claude/worktrees/trusting-chandrasekhar-7b2041/` (claude/trusting-chandrasekhar-7b2041 branch). main에 머지·push 완료, 정리 시 worktree 제거 가능
2. **API 키**: `serving-team/08-app/backend/.env`에 OPENAI_API_KEY 설정됨. 정상 작동 확인 (T2.D 8회 replay 모두 성공)
3. **8 F.3.2 candidate axiom 모두 vetted 승격 완료** (T2.D 8/8 PASS). vetted_count 0 → 8. 잔여 candidate-only 진행 시 동일 `promote_f32_per_candidate.py --apply` 패턴.
4. **Fuseki container 새 image 적용 중**: `docker-fuseki:latest` sha256 `08837972` (kb-candidates.ttl 17,618 triples 로드, 총 981,409 triples). `docker compose up -d`에 동일 image 자동 사용. 다음 TTL 추가 시 동일 (Java sources 수정 + rebuild + recreate).
5. **T2.D 1차 cp949 unicode bug 처리됨**: `promote_f32_per_candidate.py` 모든 ✓✗→— → ASCII 교체. 재실행 시 `PYTHONIOENCODING=utf-8 python -u` 권장.
6. **T3.A 잔존 4 free-creates**: THF, CO, MOBILE_EQUIPMENT, WAREHOUSE — OpenAI strict mode enum의 edge-case (~99.6% 강제력, 0.4% 누락). 별도 분석 후보 (또는 normalizer step에서 hard reject 가능).
7. **편의점 KO unmapped** (이전 sprint에서 발견): `industry_ko_to_en_map.json`에 `편의점 → CONVENIENCE_STORE` 매핑 추가됨 (Quick Win Task 3). T2.D 후보 [6/8] 편의점×METAL_MACHINING가 vetted 통과 확인.
8. **A hook 항상 실행됨** (Quick Win Task 2 + T2.A): `_apply_llm_rerank`의 early-return 3 경로 모두 `_log_skipped_analysis` 호출 → analysis_log에 `mode=off_skipped_*` 기록. T2.A `reasoner_rejects` field도 happy + skipped path 모두 추가됨.
9. **stash@{0}**: `WIP on main: ca55ac6` (이전 세션 8 real-test-photo PNG/JPG untracked). 무관함, 보존

## 🛣️ 다음 작업 우선순위

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

### 다음 작업 우선순위 (Tier 1-3.A 완료 후):

**1순위 (각 30분~수시간, ROI 큼)**:
- **T3.A 잔존 4건 조사**: THF, CO, MOBILE_EQUIPMENT, WAREHOUSE 왜 OpenAI strict enum을 빠져나갔는지. 재현 + analysis_log scene_hash 분석. 필요 시 normalizer step에서 hard reject 추가.
- **8-photo real-test eval** (`make f1-eval`, ~$0.40 + 8분): T3.A 효과 실제 사진 검증.
- **promote_she_review.py**: F.2 Day 5의 77 pending_review SHE 신중 승격 (5-10건씩 + Gate 3). T1.A rollback fix 적용된 상태.

**2순위: Tier 3 후속 path** (1-4주, 택1):
- **3B F.4 CQ Reverse + Photo persist** (3-4주, ~$5) — Module 4.5, CQ coverage 2% → 80%. 학계 paper용.
- **3C Phase G PG materialization** (3-4주, ~$0) — 7단계, reasoner 결과 → PG (5 tables: she_patterns, guide_domain_incompatibilities, guide_usage_profiles, ci_sr_mapping, penalty_rules). 시연/서빙 성능 가속.

**3순위 (Tier 4 중장기, 1-3개월)**:
- F.5 GraphRAG (Module 4.6, 2주)
- Phase J OBO Foundry 등재 (1-3개월)
- Two-way CoT prompt 전환 (1일, +0.2 F1 기대)
- OOPS! Pitfall Scanner 통합 (2-3h)

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
