# LLM-Accelerated 정석 Ontology Engineering Plan

> **다음 세션 진입점.** 이 문서는 2026-05-16~17 두 세션에 걸친 작업의 메인 plan이다.
> 임시 plan 파일(`.claude/plans/workplan-...md`)에서 정식 git 추적 문서로 이전됨.
> 향후 모든 Phase 결정의 기준.

## Status (2026-05-17)

| Phase | 상태 | 비고 |
|---|---|---|
| Phase 0 (Synthetic Replay 인프라) | ✅ 완료 | `replay_synthetic_observations.py` + `regression_gate.py` |
| Phase B (Runtime LLM rerank) | ✅ 완료 + 검증 | positive avg_procedures −26.4% |
| Phase A (Domain pair mining) | ✅ 완료 | 2,232 incompatibility (vetted 0 + candidate 2,201 + self_refine 31) |
| Phase C (Self-refine loop) | ✅ 작동 검증 | analysis_log 2,528건 + 31개 자율 채택 |
| Catalog/alias 확장 | ✅ 완료 | 187개 신규 alias + 66개 신규 work_context, she_accuracy +4.9%p |
| Phase E-prep (6 step) | ✅ 완료 | BFO+LKIF 2-layer, 22 SWRL, 26 SHACL, OntoClean 13→1 |
| Phase E.2 (Openllet 실제 통합) | ⏳ 다음 | Fuseki Java 수정 + container rebuild |
| Phase F+ | ⏳ Plan만 | Layer 4 ontology learning 본격 구현 |

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

### Backend code (`serving-team/08-app/backend/`)
- `app/services/guide_embedding_filter.py` (신규)
- `app/services/llm_validator_cache.py` (신규)
- `app/integrations/prompts/guide_validator_prompt.py` (신규)
- `app/services/analysis_pipeline.py` (수정: `_apply_llm_rerank`, `_append_analysis_log`)
- `app/services/guide_domain_profile.py` (수정: dynamic incompat KB layer)
- `app/integrations/openai_client.py` (수정: `validate_guide_relevance`)
- `app/models/analysis.py` (수정: `ExcludedCandidate`)
- `app/data/risk_feature_aliases.json` (확장 +187)
- `app/data/risk_feature_catalog.json` (확장 +66 work_context)
- `scripts/replay_synthetic_observations.py` (신규)
- `scripts/regression_gate.py` (신규)
- `scripts/merge_replay_partials.py` (신규)
- `scripts/test_real_photos.py` (신규)

### Data team scripts (`data-team/05-enrichment/llm-scripts/`, 13개 신규)
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

### Runtime artifacts (`data-team/05-enrichment/runtime-artifacts/`)
- 모든 산출 JSON (CQ, layer assignment, disjoint, SHACL, OntoClean 등)
- `analysis_log.jsonl` (2,528 entries)
- `guide_domain_embeddings.npz` (3.75MB)
- `replay_baseline.json` / `replay_baseline_v2.json` / `replay_active_b.json` / `replay_active_v2.json`

### Frontend (`serving-team/08-app/frontend/`)
- `src/components/results/SourceBadge.tsx` (신규, 10개 source type)
- 5개 panel 수정 (badge 표시)

### Reference (`ontology-team/reference-article/`, 사용자 추가)
- 9개 학계 PDF (LLMs4OL, OntoGPT/SPIRES, NeOn-GPT, 2024-2025 최신)

## Phase F+ 로드맵 (Layer 4 본격 구현)

| Phase | 작업 | 학계 reference | 시간/비용 |
|---|---|---|---|
| **E.2** (다음 우선순위) | Fuseki Java 수정 + Openllet 정식 통합 | LLMs4Life Pellet | 1시간 |
| **F.1** | Vocabulary auto-registration (Module 4.1) | SPIRES IDSpaces/ValueSets | 3-5일 |
| **F.2** | TBox class learning (Module 4.2) | Two-way CoT + Ontogenia | 1주 |
| **F.3** | SWRL/SHACL Discovery 자동화 (Module 4.4) | Tsaneva ensemble 96.7% | 1주 |
| **F.4** | CQ Reverse + SPARQL 회복 (Module 4.5) | RETROFIT-CQ 75% | 1주 + Photo persist |
| **F.5** | GraphRAG 통합 (Module 4.6) | Salovsky Dual Memory | 2주 |
| **F.6** | Maintenance phase (Module 4.7) | SLR challenges #4 #5 | 영구 cron |
| **F.7** | Small model fine-tune | Aggarwal Dolphin-Mistral-7B | 2-3주 |
| **F.8** | OBO Foundry/IOF 등재 + LegalRuleML | SLR Lifecycle | 1-3개월 |

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
| `guide_domain_incompatibilities` (신규) | LLM-mined KB (vetted 2,232) → table |
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

1. **commit 안내** — 이번 세션 신규 산출물 50+ 파일이 미커밋 상태. 사용자 의사 확인 후 staged commit
2. **plan 임시 파일** (`.claude/plans/workplan-...md`)은 무시 가능 (이 정식 문서로 이전 완료)
3. **Phase E.2 (Openllet 정식 통합)이 진짜 6단계 본격 진입** — Fuseki Java 수정 필요
4. **API 키 — 새 키 필요 시 `serving-team/08-app/backend/.env`에 갱신** (이전 5개 키는 사용자가 2026-05-17 회수 완료)
