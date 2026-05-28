# 4-Layer Architecture

> arch-bot 시스템의 전체 architecture. Layer 4 (Ontology Learning, cross-cutting)는 [ontology-learning-layer.md](ontology-learning-layer.md) 참고.

## Overview

```
┌────────────────────────────────────────────────────┐
│ Layer 0: Vision LLM                                │
│   gpt-4.1 (사진 → 관찰사실)                         │
│   영구 잔존 (AI 인식 영역)                          │
├────────────────────────────────────────────────────┤
│ Layer 1: Normalizer                                │
│   alias dict + catalog enum match                  │
│   text → canonical code                            │
├────────────────────────────────────────────────────┤
│ Layer 2: Semantic Reasoning                        │
│   SHE matcher (PG, deterministic)                  │
│   + OWL DL reasoner (Openllet, Phase E.2 후)        │
│   + SWRL/SHACL                                     │
├────────────────────────────────────────────────────┤
│ Layer 3: PG Materialization                        │
│   reasoner 결과 → PG table cache                   │
│   runtime은 SELECT만 (ms)                           │
├────────────────────────────────────────────────────┤
│ ★ Layer 4: Ontology Learning (cross-cutting) ★      │
│   학습기 (Layer 1-3의 데이터를 학습 대상으로)        │
│   상세: ontology-learning-layer.md                  │
└────────────────────────────────────────────────────┘
```

## Layer 0 — Vision LLM

**역할**: 사진(이미지) → 구조화된 관찰사실 JSON

**구현**:
- 모델: `gpt-4.1` (OpenAI Vision API)
- 코드: `serving-team/08-app/backend/app/integrations/openai_client.py:analyze_image`
- 출력 스키마: `ONTOLOGY_OBSERVATION_SCHEMA`
  - `visual_observations`: 사진 관찰사실 (한국어 text + severity)
  - `visual_cues`: 짧은 시각 단서 (SHE 매칭용)
  - `hazards`: ⭐ 자연어 위험요소 카테고리 (Hazard-Direct Pivot, 2026-05-19) — name/risk_level/location/description/preventive_measures
  - `risk_feature_candidates`: axis(accident_type/hazardous_agent/work_context/ppe_state/environmental)별 후보 코드

**특성**:
- 영구 잔존 (현실세계 인식은 reasoner로 대체 불가)
- `risk_feature_candidates.text`는 catalog 529 enum 강제 (Tier 3.A, 2026-05-18 — free-create 76→4)
- `hazards[].name`은 자연어 (moellab 스타일). 후속 Layer 1에서 catalog code로 alias 매핑

## Layer 1 — Normalizer

**역할**: Layer 0의 free-form text → catalog의 canonical enum code

**구현**:
- 코드: `serving-team/08-app/backend/app/services/hazard_normalizer.py`
  - `_resolve_alias_code` — `risk_feature_candidates` axis별 코드 정규화
  - `normalize_hazards_array` — ⭐ Hazard-Direct `hazards[].name` 자연어 → canonical 3축 (2026-05-19)
- 데이터:
  - `app/data/risk_feature_catalog.json` — catalog v3.3, 529 canonical enum codes (5 axes)
  - `app/data/risk_feature_aliases.json` — tier1 alias dictionary (Hazard-Direct에서 자연어 hazard alias 21건 추가)

**매칭 우선순위**:
1. 직접 enum match (영문 code)
2. STAGE2_V2_AXIS_ALIASES (env 활성 시)
3. work_context 부분 단어 매칭 (env 활성 시)
4. tier1 alias 사전 (exact match)
5. Contained term fallback (env 활성 시, substring)

**한계 + 개선 방향** (Phase F.1, Layer 4.1):
- 현재: alias 사전을 따라잡는 게임 (LLM이 새 표현 만들면 매핑 실패)
- 개선: "매핑 불가 코드" 로그 mining → LLM 검증 → 자동 alias 등재

## Layer 2 — Semantic Reasoning

**역할**: canonical features → SHE 매칭 + OWL DL 추론 + SWRL/SHACL

**구현**:
- **SHE matcher** (deterministic, 현재 운영): `app/services/she_matcher.py`
  - PG `she_patterns` 테이블 (수백 개)
  - canonical code overlap + 차원별 점수
- **OWL DL reasoner** (Phase E.2 후 정식 통합):
  - Openllet engine
  - `ontology-team/06-reasoning/ontology/docker/` (이미 설정됨, `REASONER_MODE=openllet`)
  - 추론 대상: TBox + ABox + SWRL + SHACL
- **SWRL rules** (axiom-100% Sprint 후 — R-1/R-3만 Pellet native):
  - `kosha-rules-r1-r3-swrl.ttl` (R-1 exemptedBy **107** + R-3 HighSeverityPenalty **3,579** inferred, Pellet 정상)
  - R-9~R-13 / R-14~R-30 SWRL ttl은 디스크에 존재하나 **R-14~R-30은 Java sources에서 주석 처리** (12개 SWRL 조합 시 Pellet NEXPTIME blowup) → SHACL CONSTRUCT로 대체
- **SHACL rules/shapes** (axiom-100% Sprint — SWRL 대체 + 일반화):
  - `kosha-rules-r14-r30-shacl-construct.ttl` (R-14~R-30 = **12 sh:rule CONSTRUCT**, Pellet 회피)
  - `kosha-rules-k-general-shacl.ttl` (R-2 `coApplicable` 16,429 + R-4 `dependsOn` 36,949 = **53,378 pair**, on-demand)
  - `kosha-vetted-disjoint-shapes.ttl` + `kb-candidates.ttl` (2,192 industry shapes) + `serving-validation-shapes-v3.ttl` (24 shapes)
  - 총 **sh:NodeShape 1,964**

**BFO + LKIF-Core 2-layer** (이번 세션 정형화):
- **Layer A (alethic)**: Photo, VisualObservation, RiskFeature, Equipment, Worker → `rdfs:subClassOf bfo:*`
- **Layer B (deontic)**: law:Article, sr:SafetyRequirement, lkif:Obligation/Permission/Prohibition → `rdfs:subClassOf lkif:*`
- **Bridge property**: `core:violatesObligation`, `core:observedIn`, `core:appliesTo`

## Layer 3 — PG Materialization

**역할**: Layer 2 추론 결과 → PG table cache (runtime ms 응답)

**현재 운영 (5단계 일부)**:
- `kosha_guides`, `work_processes`, `she_patterns`, `safety_requirements`, `ci_sr_mapping`, `penalty_rules`, `penalty_conditions`
- 이미 운영 중

**Phase G 완료 (2026-05-19) — PG 재물질화 3 table + 1 view**:
| PG 객체 | 재물질화 내용 | 상태 |
|---|---|---|
| `guide_domain_incompatibilities` | LLM-mined KB → PG (G.1) | ✅ 2,016 rows, `core:Incompatibility` ontology backed |
| `guide_usage_profiles` | `guide_domain_profiles.json` → PG (G.2) | ✅ 1,038 rows, `guide:GuideUsageProfile` 신규 OWL class |
| `penalty_rule_index` | kosha-instances.ttl → PG (G.3) | ✅ 4,076 SR→PenaltyRule mappings, **penalty_accuracy +27.16%p** |
| `she_patterns_reasoner_derived` (view) | 77 F.2 v3.1 link SHE 노출 (G.4) | ✅ read-only architectural layer |

모두 **PG primary + JSON/TTL fallback** 패턴. 기존 `kosha_guides`/`safety_requirements`/`ci_sr_mapping`/`penalty_rules` 등은 이미 운영 중.

**적재 패턴**:
- import 스크립트: `import_domain_incompatibilities_to_pg.py`, `import_penalty_to_pg.py`

## Layer 4 — Ontology Learning (cross-cutting)

상세: [ontology-learning-layer.md](ontology-learning-layer.md)

**역할**: Layer 1-3의 데이터를 학습 대상으로 → vocabulary/class/rule 자동 등재

**7 module 구성**:
- 4.1 Term & Type Extraction (Task A) — Layer 1 alias auto-registration
- 4.2 Taxonomy Discovery (Task B) — Layer 2 TBox class learning
- 4.3 Relation Mining (Task C) — Layer 2 incompatibility KB (★ 우리 학계 SOTA)
- 4.4 Axiom Discovery (Task D) — Layer 2 SWRL/SHACL Discovery (★ 학계 미답)
- 4.5 CQ Reverse Engineering — Layer 3 PG → CQ → SPARQL
- 4.6 GraphRAG — Layer 2/3 vector + SPARQL fusion
- 4.7 Continual Adaptation — Phase C 영구화

## 전체 흐름 — Runtime (시연 시)

```
1. 사용자 사진 업로드
   ↓
2. Layer 0: Vision LLM → JSON (hazards[] + risk_feature_candidates[])
   ↓
3. Layer 1: Normalizer
   ├─ risk_feature_candidates → canonical (기존 path)
   └─ ⭐ hazards[].name → normalize_hazards_array → canonical (Hazard-Direct path)
   ↓
4. Layer 2:
   ├─ SHE matcher → matched SHE patterns (기존 path)
   └─ ⭐ hazard_to_guide_service → hazard별 SR → Guide grouping (Hazard-Direct path)
   ↓
5. Layer 3: PG SELECT (SR/Guide/Penalty) — 양쪽 path 공통
   ↓
6. Phase B (Layer 2 보강): embedding pre-filter + LLM rerank (회색영역만)
   ↓
7. Phase A.4 (Layer 2 보강): dynamic incompatibility KB lookup
   ↓
8. 응답 JSON 반환 (standard_procedures + ⭐ hazards[] + hazard_guide_relations[])
   ↓
9. Layer 4 hook: analysis_log.jsonl append (자율 학습 데이터 누적)
   - 기본 필드: scene_hash, industry, candidate_count, filter_keep/gray/drop, excluded[]
   - **A 신규 필드 (2026-05-17, commit `ebe1011` + hot-fix `a841a0b`)**:
     `normalizer_unknown_codes` (Layer 1 매핑 실패 raw text),
     `she_match_count` (Layer 2 SHE matcher 매치 수, 0이면 새 SHE 패턴 후보),
     `raw_vision_features` (Layer 0 Vision LLM 원본 출력)
   - 한계: `LLM_RERANK_MODE=off` 또는 `knowledge.guide_rows` 비어있는 early-return 시 hook 미실행 (별도 후속)
```

## 진화 path

상세: [llm-dependency-evolution.md](llm-dependency-evolution.md)

```
[현재 (2026-05-28, origin/main `4aa3cca`)]
    Layer 0-3 + Phase E.2 (Openllet) + Phase 3 + F.1/F.2/F.3 + Tier 1-3.A
    + Phase G (PG materialization 3 table + 1 view) + Tier 4 (SWRL Pellet R-1/R-3 실행기)
    + ⭐ Hazard-Direct Pivot (hazards[] 자연어 직접 출력 → catalog 매핑 → ontology Guide 추천)
    + ⭐ axiom-100% Sprint (v4 TBox 9패치 + SWRL R-14~R-30 → SHACL CONSTRUCT + K-general 53,378)
    + ⭐ guide-accuracy Sprint (CI 변별력 guide_frequency + Guide 직접 위험 매핑 레이어)
[완료] Phase F.1 Normalizer auto-registration + F.3 closed loop + Phase G/7단계 PG materialize
[후행] SHE matcher broadness-aware refactor (별도 sprint, she-matcher-broadness-refactor.md)
[Phase J] OBO Foundry 등재 (오픈소스, 국제 표준)
```

## 참고 문서

- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
- [Ontology Learning Layer 상세](ontology-learning-layer.md)
- [LLM 의존 폐지 path](llm-dependency-evolution.md)
- [학계 reference 9 paper](../governance/ontology-learning-references.md)
