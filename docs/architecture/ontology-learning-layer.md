# Ontology Learning Layer (Layer 4) — 정밀 설계

> arch-bot의 cross-cutting Layer 4 상세 명세.
> 학계 9 paper reference 기반 + 우리 KOSHA 도메인 차별점 통합.
> [4-Layer Architecture](4-layer-architecture.md) 참고.

## 왜 Layer 4가 필요한가

**Layer 1-3은 추론기**, Layer 4는 **학습기**. 별도 component (현재 analysis_log 누적 2,536+건, F.3.0/F.3.2 first batch 완료):

- **OWL DL reasoner** = deductive (TBox + ABox → 결론 도출)
- **Ontology Learning** = inductive (데이터 → 새 vocabulary/class/rule 발견)

**KOSHA 산업안전은 long-tail 도메인**:
- 78 industry, 272 work_context는 절대 모든 산업 cover X
- 새 산업/장비/위험요소 계속 등장 (반려동물 미용업, 드론 배송, EV 배터리 등)
- closed vocabulary = 영원한 blind spot

→ **자율 등재 메커니즘** 필수. 학계 정설 (Cimiano 2006, LLMs4OL 2023+, OntoGPT 2023).

## 7 Module 구성

```
┌──────────────────────────────────────────────────────────┐
│ Layer 4 — Ontology Learning (cross-cutting)              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ [4.1] Term & Type Extraction (Task A)                    │
│   • SPIRES LinkML schema-driven recursion                │
│   • IDSpaces + ValueSets grounding (hallucination ↓)     │
│   • vocabulary auto-registration (Phase F.1)             │
│   • Count metric guidance (LLMs4Life)                    │
│                                                          │
│ [4.2] Taxonomy Discovery (Task B)                        │
│   • Two-way CoT + Metacognitive prompt (+0.2 F1)         │
│   • Embedding cosine subsumption pre-check               │
│   • TBox class learning (Phase F.2)                      │
│                                                          │
│ [4.3] Relation Mining (Task C) ★ 학계 SOTA               │
│   • mine_domain_incompatibilities (Phase A.2)            │
│   • Multi-LLM ensemble (Tsaneva 92.2→96.7%)              │
│   • Phase C self-refine 영구화                           │
│                                                          │
│ [4.4] Axiom Discovery (Task D) ★ 학계 미답               │
│   • SWRL/SHACL 자동 생성 (Phase E.3)                     │
│   • OOPS! Pitfall Scanner 통합                           │
│   • Ensemble verification (Lippolis 4-dim eval)          │
│                                                          │
│ [4.5] CQ Reverse Engineering                             │
│   • ABox 102k → CQ 자동 생성 (RETROFIT-CQ 75% executable)│
│   • CQ → SPARQL (Phase E.5 확장)                         │
│   • Maintenance phase (SLR 최약점)                       │
│                                                          │
│ [4.6] GraphRAG                                           │
│   • vector + SPARQL fusion                               │
│   • C(q) = Fuse(R_vect, R_graph, R_tool, M_user)         │
│   • 사진 분석 시 historical case lookup                  │
│                                                          │
│ [4.7] Continual Adaptation & Maintenance                 │
│   • Phase C 자율 학습 루프 영구화                         │
│   • SLR challenges #4 #5 대응                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Module별 상세

### Module 4.1 — Term & Type Extraction (Task A)

**대상**: Layer 1 alias 사전 + catalog enum

**학계 reference**:
- LLMs4OL Task A (Term Typing): cloze prompt, 11 LLM 비교
- OntoGPT/SPIRES: LinkML schema-driven, IDSpaces/ValueSets grounding (Caufield 2023)
- LLMs4Life: Count metric-guided prompt

**우리 입력 source**:
- `[Normalizer] 매핑 불가 코드` 로그
- 새 synthetic_observations에서 발견된 미지 코드

**처리 flow**:
```
"매핑 불가 코드" cron mining (1일 1회)
   ↓
Gate 1: Embedding similarity ≥ 0.7 (기존 enum label과)
   ↓
Gate 2: Multi-LLM consensus (GPT + Claude + Gemini 2/3)
   ↓
Gate 3: Counter-example test (2,360 synthetic regression)
   ↓
Gate 4: Asymmetric trust
  ├─ candidate (soft) → 100 분석 동안 회귀 통과
  └─ vetted (hard) → Layer 1 alias 사전에 영구 적용
```

**구현**:
- 신규 스크립트: `data-team/05-enrichment/llm-scripts/auto_register_aliases.py`
- 활용 패턴: `mine_overpromote_patterns.py` (Phase C.2)와 동일

### Module 4.2 — Taxonomy Discovery (Task B)

**대상**: Layer 2 TBox class hierarchy

**학계 reference**:
- LLMs4OL Task B (Taxonomy Discovery)
- Aggarwal Two-way CoT (+0.2 F1)
- Ontogenia Metacognitive Prompt + ODP 주입

**우리 입력 source**:
- 새 industry/work_context instance 누적 패턴
- Layer 4.1에서 등재된 신규 vocabulary

**처리 flow**:
```
신규 instance pattern (예: "드론 배송업" 50건 누적)
   ↓
LLM이 OWL Class 제안 (BFO super 자동 매핑)
   ↓
OntoClean 자동 검증 (Phase E Step 4 패턴 재사용)
   ↓
embedding subsumption check (기존 class와 hierarchy)
   ↓
asymmetric trust → TBox candidate class 등재
```

**구현**:
- 신규: `data-team/05-enrichment/llm-scripts/learn_tbox_classes.py`
- 재사용: `build_layer_mapping.py`, `ontoclean_validator.py`

### Module 4.3 — Relation Mining (Task C) ★ 우리 학계 SOTA

**대상**: Layer 2 incompatibility KB / non-taxonomic relations

**학계 reference**:
- LLMs4OL Task C: F1 0.078 (학계 매우 낮음)
- **우리 Phase A**: 2,232 incompatibility, confidence ≥ 0.7 acceptance 24% — 학계 SOTA 정량적 앞섬

**현재 운영**:
- `mine_domain_incompatibilities.py` (Phase A.2)
- `mine_overpromote_patterns.py` (Phase C.2)
- `promote_incompatibilities.py` (Phase C.3, asymmetric trust)

**개선 (Phase F.3+)**:
- Multi-LLM ensemble (Tsaneva 92.2→96.7%)
- Subsumption pre-check 강화 (embedding cosine + LKIF Role 패턴)

### Module 4.4 — Axiom Discovery (Task D) ★ 학계 미답

**대상**: SWRL rules + SHACL shapes + DisjointClasses axioms 자동 생성

**학계 reference**:
- LLMs4OL Task 6 (Axiom Discovery): 학계 empirical 검증 부재
- **우리 Phase E.3**: 22 SWRL + 26 SHACL 자동 생성 — 학계 미답 영역 첫 구현
- **우리 Phase F.3.2 first batch** (2026-05-17, commit `9219c7c`): F.3.0 분류 결과의
  axiom_missing pair (freq ≥ 5) → LLM verify → 8 candidate disjoint axiom KB 머지
  (`mine_missing_axioms.py`). incompatible_count 2,232 → 2,240. F.3.3 Gate 3
  regression PASS (commit `eb7843f`).

**진행 (2026-05-17)**:
- F.3.0 `classify_reject_reasons.py` — analysis_log 2,525 entries 5 카테고리 분류 →
  axiom_missing 36.44% (920건, 210 unique pair) → F.3 PROCEED 결정
- F.3.2 `mine_missing_axioms.py` — 49 LLM verify → 8 accepted (16% rate)
- F.3.3 Gate 3 — 2,360 synthetic replay PASS (delta -0.0013 노이즈 수준)
- 4-Gate 검증: Gate 1 embedding pre-filter (mine 단계), Gate 2 LLM verify ✅,
  Gate 3 regression ✅, Gate 4 asymmetric trust (`level=candidate`, 50회 후 자동 승격)

**Phase G + Tier 4 후속 완료 (2026-05-19, main `448a8d0`)** — Layer 4.4 **reasoner-derived facts 실제 입증**:

- **Phase G.3** (`8ddc2c7`): kosha-instances.ttl → PG `penalty_rule_index` (4,076 rules) → backend PG SELECT. **penalty_accuracy +27.16%p ⭐** (TTL parse 우회 + 완전 mapping)
- **Tier 4 AsymmetricProperty 패치** (`5edae0b`): `law:modifies`의 `owl:AsymmetricProperty` 제거로 Openllet `FunInv` 경고 해소 + SPARQL 추론 정상 검증 (`hazard:FALL_FROM_HEIGHT rdfs:subClassOf+ ?super` → `owl:Thing` + `hazard:FALL`)
- **Tier 4 #3 SWRL Pellet** (`448a8d0`) ⭐: `kosha-rules-r1-r3-swrl.ttl` (OWL/RDF SWRL) → Pellet native 실행 → **R-1 exemptedBy 107 inferred + R-3 HighSeverityPenalty 3,579 inferred** (severityScore >= 5 100% 일치, swrlb:greaterThanOrEqual built-in 정확)

→ Layer 4 Module 4.4 = **mining → verify → compile → reason → PG → 서비스** 전체 흐름 실제 동작 검증 완료.

**Tier 2 F.3 closing 완료 (2026-05-18 저녁, main `b237e78`)** — Layer 4.4 closed loop:

```
mining (F.3.0/3.2)   →   verify (F.3.3 Gate 3)   →   compile (T2.B compile_kb_to_ttl.py → kb-candidates.ttl)
                                                     ↓
monitor (T2.C f3_drift_check.py)   ←   deploy (Fuseki container restart + SPARQL endpoint)
```

- **T2.A F.3.1** (`93c49fe`): pyshacl reasoner shadow channel (offline `pyshacl_shadow_validator.py` + serving `shadow_reasoner.py`). 2,580 analysis_log rows → 859 reasoner_rejects. `analysis_log[reasoner_rejects]` 신규 필드 (Layer 2.5 shadow channel).
- **T2.B F.3.4** (`ac98d4c` → `325ad37`): `compile_kb_to_ttl.py` → `kb-candidates.ttl` (2,192 SHACL NodeShape, sh:Info severity). Fuseki Java sources array 수정 + docker rebuild + container recreate. SPARQL `COUNT(?s a sh:NodeShape)` → **2,216 NodeShapes** 검증 완료.
- **T2.C F.3.5** (`78886b3`): `f3_drift_check.py` (6 metric drift, exit 0/1/2) + Makefile `f3-weekly-cycle` (cron-able). `f3_drift_log.jsonl` 시계열.
- **T2.D F.3.2 vetted promotion** (`ac98d4c`): `promote_f32_per_candidate.py` (1-by-1 + full replay + Gate 3 wrap + 자동 rollback). **8/8 PASS** (예상 5-6 대비 100%). F.3.2 mining quality 검증.

**개선 후속**:
- OOPS! Pitfall Scanner 통합 (Lippolis 4-dim eval) — Tier 4
- Ensemble verification (multi-LLM, 현재 single-LLM) — Tier 4
- Phase G PG materialization — `guide_domain_incompatibilities` JSON → table (Tier 3 후속 3C)

**구현 (전체)**:
- 기존: `build_swrl_rules.py`, `build_shacl_shapes.py`, `fix_shacl_shapes.py`
- F.3 2026-05-17: `classify_reject_reasons.py`, `mine_missing_axioms.py`, `translate_incompat_industries.py`
- **Tier 2 2026-05-18 저녁**: `pyshacl_shadow_validator.py`, `compile_kb_to_ttl.py`, `f3_drift_check.py`, `promote_f32_per_candidate.py`, `shadow_reasoner.py` (serving runtime)
- Runbook: [docs/dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md)

### Module 4.5 — CQ Reverse Engineering

**대상**: ABox → Competency Questions → SPARQL

**학계 reference**:
- RETROFIT-CQ: 75% executable SPARQL
- AgOCQs: 80% expert pass
- LLMs4Life: CQ generation pipeline

**현재 상태**:
- `build_competency_questions.py` (Phase E.1): 50 CQ 생성
- `build_sparql_queries.py` + `regenerate_sparql_queries.py` (Phase E.5): 50 SPARQL
- coverage: 2% (Photo persist 미구현으로 ABox 본질 한계)

**개선 (Phase F.4)**:
- Photo/Observation ABox persist 후 alethic CQ 답 가능
- coverage 80%+ 목표

### Module 4.6 — GraphRAG

**대상**: vector + SPARQL fusion

**학계 reference**:
- Salovsky Dual Memory: `C(q) = Fuse(R_vect, R_graph, R_tool, M_user)`
- DRAGON-AI RAG (LLMs4OL 2024)
- MCP/Agent orchestration

**우리 적용 (Phase F.5)**:
- Phase B embedding pre-filter 위에 SPARQL retrieval 추가
- 사진 분석 시 historical similar case lookup
- backend의 `guide_recommendation_service` 확장

### Module 4.7 — Continual Adaptation & Maintenance

**대상**: 영구 자율 학습 루프

**학계 reference**:
- SLR (Li 2025) 5대 challenge 중 #4 Continual Learning, #5 Real-World Robustness
- Maintenance phase는 학계 최약점 (Documentation 2.4%만 다룸)

**우리 현재 운영**:
- Phase C analysis_log.jsonl 영구 누적 (현재 2,536+건)
- Phase C.2 cron mining (100건 누적 시)
- Phase C.3 asymmetric trust promotion
- **A Runtime 4번 채널 hook (2026-05-17, commit `ebe1011` + hot-fix `a841a0b`)** —
  analysis_log 각 entry에 3 신규 필드 (`normalizer_unknown_codes`, `she_match_count`,
  `raw_vision_features`). F.3.5 환류 input pool로 "매칭 안 된 새 SHE 후보" 식별 가능.
- **F.3.0 reject reason classifier (2026-05-17, commit `8ff40d7`)** — analysis_log를
  5 카테고리로 분류해 mining 신호 분기 (domain_mismatch / axiom_missing /
  normalizer_gap / data_quality / ambiguous)

**개선**:
- A hook always-on (현재 `_apply_llm_rerank` early-return 시 미실행 — 별도 hook 필요)
- F.3.5 cron 자동화 (`Makefile learn-axioms` chain: F.3.0 → 3.2 → 3.3 → 3.4 → replay)
- audit log + drift detection (주간 false_negative_rate 비교, +2pp 초과 시 알림)
- 사용자 explicit feedback UI (Phase H)

## 학계 reference 5/5 합의 (Layer 4 필수 구성)

1. **Hybrid neuro-symbolic** — LLM 생성 + SHACL/OWL reasoner 검증
2. **Task A/B/C/D 분해**
3. **Decomposed CoT prompting** (Two-way CoT, Metacognitive)
4. **Human-in-the-loop** (완전 자율 위험)
5. **CQ-driven 검증**

## 우리 차별점 (학계 contribution potential)

| 항목 | 학계 현재 | 우리 |
|---|---|---|
| Deontic domain | 부재 (Wine/Pizza/SAR/SNOMED/GO 등 alethic) | LKIF-Core × BFO 2-layer |
| 한국어 법령 | 0건 | KOSHA + 산업안전보건법 |
| Task C (relation) | F1 0.078 (LLMs4OL 2024) | 24% acceptance @ confidence ≥ 0.7 |
| Task D (axiom) | empirical 검증 부재 | Phase E.3 첫 구현 |
| Asymmetric trust | 미언급 | candidate → vetted promotion |

## 4-Gate 위험 검증 (모든 Module 공통)

자율 등재의 false positive 위험을 방지하는 4-layer 검증:

```
신규 학습 대상 (vocabulary, class, axiom, ...)
   ↓
[Gate 1] Embedding similarity
   • 기존 entity와 cosine ≥ threshold
   • semantic 거리 너무 크면 reject
   ↓
[Gate 2] Multi-LLM consensus
   • GPT-4o + Claude + Gemini 3-way
   • < 2/3 합의 → reject
   ↓
[Gate 3] Counter-example test (regression)
   • 2,360 synthetic 회귀
   • false_negative_rate > +1%p → reject
   ↓
[Gate 4] Asymmetric trust
   • candidate (soft penalty, 100 분석 동안 monitoring)
   • vetted (hard penalty, runtime LLM 불필요)
```

## Phase F+ 로드맵 (Module별)

| Phase | Module | 작업 | 상태 |
|---|---|---|---|
| F.1 | 4.1 | Vocabulary auto-registration cron + 4-gate | ✅ 완료 (5 vetted, closed loop) |
| F.2 | 4.2 | TBox class learning (Taxonomy Discovery) | ✅ 완료 (catalog v3.3, 481 codes × 5 axes) |
| **F.3.0** | **4.7** | **Reject reason classifier** | ✅ 완료 (2026-05-17, `8ff40d7`) |
| **F.3.2** | **4.4** | **Missing-axiom miner (Disjoint-only first batch)** | ✅ 완료 (2026-05-17, `9219c7c`, 8 candidate) |
| **F.3.3** | **4.4** | **Gate 3 regression PASS** | ✅ 완료 (2026-05-17, `eb7843f`) |
| **T2.A F.3.1** | **4.4** | **Reasoner shadow channel (pyshacl + serving runtime)** | ✅ 완료 (2026-05-18, `93c49fe`, analysis_log.reasoner_rejects 859/2580) |
| **T2.B F.3.4** | **4.4** | **KB compilation + Fuseki reload (kb-candidates.ttl)** | ✅ 완료 (2026-05-18, `ac98d4c` → `325ad37`, SPARQL 2216 NodeShapes 검증) |
| **T2.C F.3.5** | **4.7** | **Drift detection + Makefile f3-weekly-cycle** | ✅ 완료 (2026-05-18, `78886b3`) |
| **T2.D** | **4.4** | **F.3.2 8 candidates 1-by-1 vetted promotion** | ✅ 완료 (2026-05-18, `ac98d4c`, 8/8 PASS) |
| **Tier 3.A** | **4.1/4.2** | **Closed Vocab Schema Enum (Layer 0 catalog enforce)** | ✅ 완료 (2026-05-18, `b237e78`, 76→4 -94.7%) |
| **Phase G.1** | **4.3/4.4** | **guide_domain_incompatibilities PG (2,016 rows) + core:Incompatibility ontology** | ✅ 완료 (2026-05-19, `d6b4589`) |
| **Phase G.2** | **4.2/4.3** | **guide_usage_profiles PG + guide:GuideUsageProfile ontology (가장 큰 갭 해결)** | ✅ 완료 (2026-05-19, `2f7ef92`) |
| **Phase G.3** | **(7단계)** | **penalty_rule_index PG (4,076 rules) — penalty_accuracy +27.16%p ⭐** | ✅ 완료 (2026-05-19, `8ddc2c7`) |
| **Phase G.4** | **4.4/4.7** | **she_patterns_reasoner_derived view + Openllet 분석** | ✅ 완료 (2026-05-19, `434f35f`) |
| **Tier 4 fix** | **4.4** | **AsymmetricProperty 패치 → Openllet SPARQL 추론 정상 검증** | ✅ 완료 (2026-05-19, `5edae0b`) |
| **Tier 4 #3** | **4.4** | **SWRL Pellet 실행기 통합 (R-1: 107 + R-3: 3,579 inferred ⭐)** | ✅ 완료 (2026-05-19, `448a8d0`) |
| F.4 | 4.5 | CQ Reverse + Photo persist + SPARQL coverage 회복 | ⏳ Tier 4 중장기 |
| F.5 | 4.6 | GraphRAG (Salovsky Dual Memory) | ⏳ Tier 4 중장기 |
| F.6 | 4.7 | Continual Adaptation 확장 | ⏳ Tier 4 중장기 |
| F.7 | (전체) | Small model fine-tune (Aggarwal Dolphin-Mistral-7B) | ⏳ Tier 4 중장기 |
| F.8 (Phase J) | (전체) | OBO Foundry/IOF 등재 + LegalRuleML | ⏳ 별도 plan (사용자 명시) |
| **R-4~R-30 SWRL 변환** | 4.4 | 의사코드 → OWL/RDF SWRL serialization 일괄 | ⏳ T4 #3 후속 |
| **SHE matcher broadness-aware refactor** | 4.4 | 77 pending_review SHE 통합 가능 | ⏳ T4 #1 후속 |
| **OSHA admin penalty Pipe-A 확장** | (Pipe-A) | 제175조 administrative fines 추출 | ⏳ T4 #2 후속 |

## 즉시 적용 권장 (ROI 큼)

1. **OntoGPT 직접 통합** — `pip install ontogpt`
2. **Two-way CoT + Metacognitive prompt** — 기존 LLM-scripts 전환
3. **OOPS! Pitfall Scanner + LinkML schema 검증**

## 참고 문서

- [4-Layer Architecture](4-layer-architecture.md)
- [LLM 의존 폐지 path](llm-dependency-evolution.md)
- [9 paper reference](../governance/ontology-learning-references.md)
- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
