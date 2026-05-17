# Ontology Learning 학계 References (9 paper)

> Phase E-prep 단계에서 분석한 학계 논문 9편 요약.
> 우리 KOSHA arch-bot Layer 4 구성의 학술적 근거.
> 원본 PDF: `ontology-team/reference-article/`

## 9 paper 요약

### 1. LLMs4OL (Babaei Giglou et al., ISWC 2023)
- **Framework**: 6 task decomposition (Corpus Preparation → Terminology Extraction → Term Typing → Taxonomy Construction → Relationship Extraction → Axiom Discovery)
- **검증**: 3 task (Term Typing, Taxonomy Discovery, Non-Taxonomic Relation Extraction) empirical
- **결론**: foundational LLM 단독 불충분, fine-tuning 필요. Task A 25% / B 18% / C 3% 개선
- **우리 적용**: Task A/B/C/D 분해를 **Layer 4 module 경계로 채택**

### 2. LLMs4OL 2024 Overview (Challenge writeup)
- **규모**: 8팀 / 13 ontology source
- **Hybrid strategy 우세**: Fine-tuning / Prompt-tuning / RAG / Rule+LLM
- **결과**: TSOTSALearning (BERT+rule) WordNet F1 0.9938 (1위)
- **인사이트**: 도메인 특화에서 fine-tuned smaller model > GPT-4
- **우리 적용**: hybrid (vision LLM + Phase B rerank) 일치, Rule+LLM 패턴 미시도 영역

### 3. LLMs4Life (Fathallah et al., 2024)
- **NeOn-GPT pipeline 5단계**: Requirements → Reuse → Conceptualization → Implementation → Verification
- **6 실험 점진 개선**: Baseline → Count metric → Merging → Re-prompting + persona → Reuse → Categorization
- **검증**: Pellet/HermiT + RDFLib + pitfall detection
- **결과**: matched entity 17 → 80 (concept similarity 0.85+ 유지)
- **우리 적용**: NeOn-GPT를 Layer 4 control flow, **Count metric-guided prompt** 즉시 적용

### 4. OntoGPT/SPIRES (Caufield et al., 2023, Mungall lab)
- **SPIRES**: Structured Prompt Interrogation and Recursive Extraction
- **5단계 algorithm**: GeneratePrompt → CompletePrompt → ParseCompletion (recursive) → Ground → TranslateToOWL
- **Grounding**: GPT-3.5 단독 3/100 → SPIRES 98/100 (mass hallucination 차단)
- **LinkML schema-driven**: JSON-Schema / SHACL / SQL DDL export
- **우리 적용**: **즉시 통합 가능** (`pip install ontogpt`), 50+ LinkML 템플릿 reference

### 5. LLM Ontology Engineering SLR (Li/Garijo/Poveda-Villalón 2025, UPM) ⭐
- **규모**: 11,985 → 30 paper / 41 experiment (Kitchenham SLR)
- **Task taxonomy (treemap 정량)**:
  - Implementation 63.4% (Conceptualization 22%, Encoding 19.5%, Matching 12.2%, Evaluation 9.8%)
  - Requirements 24.4%, Publication 9.8%, **Maintenance 2.4%** ← 미개척
- **LLM 4 role**: Ontology Engineer (지배) / Domain Expert / Evaluator (희소) / Human Eval
- **5대 future challenges**:
  1. Hybrid Neuro-Symbolic Reasoning
  2. Lifecycle Coverage Expansion
  3. Standardized Evaluation Frameworks
  4. Continual Learning & Dynamic Adaptation
  5. Real-World Robustness
- **우리 적용**: Layer 4가 5대 challenge 중 #1 #4 #5 직접 대응

### 6. Automatic Ontology Construction (Salovsky&Gorshkova 2025)
- **"Ontology as external memory"** + MCP orchestration
- **12-stage pipeline**: Ingest → NER → Relation → Normalization → Triple → SHACL/OWL → TTL → Graph DB → SPARQL+vector hybrid → graph-aware retrieval → LLM → fact extraction feedback
- **Dual memory**: `C(q) = Fuse(R_vect, R_graph, R_tool, M_user)`
- **결과**: Tower of Hanoi 3-disk 26.3→33.3%, 5-disk 33.3→45.5%
- **우리 적용**: **GraphRAG (Module 4.6)** 직접 reference

### 7. Ontology Generation LLMs (Lippolis 2025, Bologna)
- **Memoryless CQbyCQ**: 하나의 CQ씩 독립 처리 → context 60% 감소
- **Ontogenia**: Metacognitive Prompting + ODP (Ontology Design Pattern) 주입
- **Benchmark**: 10 ontology / 100 CQ / 29 user story
- **결과**: GPT-4o, **o1-preview**, LLaMA-3.1-405B 비교 → o1-preview + Ontogenia가 novice 능가
- **4-dim eval**: OOPS! + CQ modelled proportion + superfluous element + qualitative (Cohen κ=0.61)
- **우리 적용**: **Two-way CoT 패턴** + **OOPS! Pitfall Scanner 통합**

### 8. Exploring LLMs Ontology Learning (Perera&Liu 2024)
- **PRISMA**: 3편 추출 (LLMs4OL, Tang DKD, DRAGON-AI)
- **Discriminative (BERT 계열) vs Generative (GPT 계열)** 구분
- **Key tensions**: positional/majority bias, "novice can be tricked", butterfly effect
- **Future areas**: LLM-based OL architecture, fine-tuning, prompt generation, hybrid + eval
- **우리 적용**: **Explainability / human-in-the-loop** 필요성 강조 → Phase H (사용자 feedback UI)

### 9. Scholarly Ontology Generation Engineering (Aggarwal 2025, KMi OU)
- **IEEE-Rel-1K**: gold standard (broader/narrower/same-as/other, 1000 pair)
- **17 LLM × 4 zero-shot 전략**: direct, two-way, CoT, two-way CoT
- **결과**:
  - **Claude 3 Sonnet F1=0.967**
  - Mixtral-8×7B 0.847
  - **Dolphin-Mistral-7B 0.920** (양자화 소형 모델이 대형과 동급)
- **Two-way CoT 일관된 +0.2 F1**
- **우리 적용**: Phase F.7 (small model fine-tune) reference, **Two-way CoT 즉시 적용**

## 학계 5/5 합의 (= 우리 Layer 4 필수 구성)

1. **Hybrid neuro-symbolic** (LLM + SHACL/OWL reasoner) — 정설
2. **Task A/B/C/D 분해**
3. **Decomposed CoT prompting** (Two-way CoT, Metacognitive, CQbyCQ)
4. **Human-in-the-loop** (완전 자율 위험)
5. **CQ-driven 검증** (41/30 study 표준)

## 학계 분기점/논쟁

| 논점 | 한쪽 | 다른쪽 |
|---|---|---|
| 대형 vs 양자화 소형 | SLR/Lippolis: GPT-4/o1-preview 우세 | Aggarwal: Dolphin-Mistral-7B 양자화 동급 |
| End-to-end vs 모듈 | NeOn-GPT: 전체 lifecycle | Lippolis Memoryless CQbyCQ: fragment |
| RAG 입장 | Salovsky: graph-augmented 필수 | Lippolis: context 축소가 효과적 |

## 2024-2025 신 trend (이전과 차별)

- **MCP/Agent layer 도입** (Salovsky) — orchestrator로 LLM-graph-validator 결합
- **Metacognitive/two-way CoT** — 자기검증 prompt
- **Engineering KOS benchmark 등장** (IEEE-Rel-1K) — scholarly/bio → 공학 도메인 진입
- **ODP 명시적 주입** (Ontogenia)
- **양자화 모델 본격 활용**

## 우리 시스템 차별점 (학계 contribution potential)

| 항목 | 학계 현재 | 우리 |
|---|---|---|
| **Deontic domain** | 부재 (Wine/Pizza/SAR/SNOMED/GO/IEEE 등 alethic 위주) | **LKIF-Core × BFO 2-layer** |
| **한국어 법령 처리** | 0건 | KOSHA + 산업안전보건법 |
| **Asymmetric trust pattern** | 미언급 | candidate (-0.05) → vetted (-0.18) |
| **Task C (relation) 성능** | LLMs4OL 2024 F1 0.078 | confidence ≥ 0.7 acceptance **24%** |
| **Task D (axiom) 자동 생성** | empirical 검증 부재 | 22 SWRL + 26 SHACL 자동 (Phase E.3) |

## arch-bot Layer 4 권장사항 (우선순위, 학계 ref 기반)

| # | 권장 | 학계 ref | 우리 기존 코드 |
|---|---|---|---|
| 1 | CQ Reverse Engineering 추가 | RETROFIT-CQ (75% executable), AgOCQs (80% expert pass) | data-team/05-enrichment/eval-data |
| 2 | Two-way CoT + Metacognitive 전환 | Aggarwal (+0.2 F1), Lippolis | data-team/02-extraction/pipe-A,B prompt |
| 3 | OOPS! Pitfall Scanner 통합 | Lippolis 4-dim eval | ontology-team/06-reasoning |
| 4 | Ensemble axiom verification | Tsaneva 92.2 → 96.7% | self-refine 31 → ensemble 확장 |
| 5 | Domain-specific small model fine-tune | Aggarwal Dolphin-Mistral-7B 양자화 | KOSHA 1,038 guide + 102k ABox LoRA |
| 6 | GraphRAG (vector + SPARQL) | Salovsky `C(q)=Fuse(...)` | serving-team/08-app backend |
| 7 | CQbyCQ 모듈 분해 | Lippolis memoryless | pipe-B enrichment |
| 8 | Maintenance phase 신설 | SLR 최약점 | 자동 생성 산출물 회수 |
| 9 | Cohen κ 기반 expert qual eval | Lippolis κ=0.61 | docs/status/evaluation-baseline.md |
| 10 | ODP repo 연결 | Ontogenia | docs/ontology/ |

## Phase J 잠재 학계 contribution

만약 Phase J (OBO Foundry 등재) 시 paper 작성 가능 topic:
- **"LKIF-Core × BFO 2-layer for Korean Occupational Safety Regulation"**
- **"Asymmetric Trust Pattern for LLM-Mined Ontology Axioms"** (학계 미언급 mitigation)
- **"Cross-domain Adaptation: Bio-medical OL methodology to Korean Regulatory Domain"**
- SLR (Li 2025) 5대 challenge 중 **#1 Hybrid Neuro-Symbolic / #4 Continual Learning / #5 Real-World Robustness**에 사례 기여

## 원본 PDF 위치

`ontology-team/reference-article/`:
- `LLMs4OL_ISWC2023.pdf`
- `LLMs4OL_2024_Overview.pdf`
- `LLMs4Life_2024.pdf`
- `OntoGPT_SPIRES_2023.pdf`
- `LLM_Ontology_Engineering_SLR_2025.pdf` ⭐
- `Automatic_Ontology_Construction_LLMs_2025.pdf`
- `Ontology_Generation_LLMs_2025.pdf`
- `Exploring_LLMs_Ontology_Learning_2024.pdf`
- `Scholarly_Ontology_Generation_2025.pdf`

## 참고 문서

- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
- [Ontology Learning Layer 상세](../architecture/ontology-learning-layer.md)
- [4-Layer Architecture](../architecture/4-layer-architecture.md)
