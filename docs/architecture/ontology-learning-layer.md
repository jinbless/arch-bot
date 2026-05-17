# Ontology Learning Layer (Layer 4) — 정밀 설계

> arch-bot의 cross-cutting Layer 4 상세 명세.
> 학계 9 paper reference 기반 + 우리 KOSHA 도메인 차별점 통합.
> [4-Layer Architecture](4-layer-architecture.md) 참고.

## 왜 Layer 4가 필요한가

**Layer 1-3은 추론기**, Layer 4는 **학습기**. 별도 component:

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

**대상**: SWRL rules + SHACL shapes 자동 생성

**학계 reference**:
- LLMs4OL Task 6 (Axiom Discovery): 학계 empirical 검증 부재
- **우리 Phase E.3**: 22 SWRL + 26 SHACL 자동 생성 — 학계 미답 영역 첫 구현

**개선 (Phase F.3)**:
- OOPS! Pitfall Scanner 통합 (Lippolis 4-dim eval)
- Ensemble verification (multi-LLM)
- LinkML schema 기반 SHACL 자동 export

**구현**:
- 기존: `build_swrl_rules.py`, `build_shacl_shapes.py`, `fix_shacl_shapes.py`
- 추가: `validate_axioms_oops.py` (OOPS! 통합)

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
- Phase C analysis_log.jsonl 영구 누적 (현재 2,528건)
- Phase C.2 cron mining (100건 누적 시)
- Phase C.3 asymmetric trust promotion

**개선**:
- cron 자동화 + audit log + drift detection
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

| Phase | Module | 작업 |
|---|---|---|
| F.1 | 4.1 | Vocabulary auto-registration cron + 4-gate |
| F.2 | 4.2 | TBox class learning (LLM4OL Task B + Ontogenia) |
| F.3 | 4.4 | SWRL/SHACL Discovery 자동화 + ensemble |
| F.4 | 4.5 | CQ Reverse + Photo persist + SPARQL coverage 회복 |
| F.5 | 4.6 | GraphRAG (Salovsky Dual Memory) |
| F.6 | 4.7 | Continual Adaptation (cron + drift detection) |
| F.7 | (전체) | Small model fine-tune (Aggarwal Dolphin-Mistral-7B) |
| F.8 | (전체) | OBO Foundry/IOF 등재 + LegalRuleML |

## 즉시 적용 권장 (ROI 큼)

1. **OntoGPT 직접 통합** — `pip install ontogpt`
2. **Two-way CoT + Metacognitive prompt** — 기존 LLM-scripts 전환
3. **OOPS! Pitfall Scanner + LinkML schema 검증**

## 참고 문서

- [4-Layer Architecture](4-layer-architecture.md)
- [LLM 의존 폐지 path](llm-dependency-evolution.md)
- [9 paper reference](../governance/ontology-learning-references.md)
- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
