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
  - `risk_feature_candidates`: axis(accident_type/hazardous_agent/work_context)별 후보 코드

**특성**:
- 영구 잔존 (현실세계 인식은 reasoner로 대체 불가)
- prompt에 enum 코드 전체 명시 안 함 (현재 설계 — Phase F.7에서 closed vocabulary 옵션 검토)

## Layer 1 — Normalizer

**역할**: Layer 0의 free-form text → catalog의 canonical enum code

**구현**:
- 코드: `serving-team/08-app/backend/app/services/hazard_normalizer.py:_resolve_alias_code`
- 데이터:
  - `app/data/risk_feature_catalog.json` — 178 canonical enum codes (이번 세션 +66 work_context)
  - `app/data/risk_feature_aliases.json` — tier1 alias dictionary (이번 세션 +187개)

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
- **SWRL rules** (이번 세션 8 → 30개):
  - `kosha-rules.swrl` (기존 8개)
  - `kosha-rules-v2.swrl` (신규 22개, alethic 5 + bridge 5 + deontic 5 + violation 4 + penalty 3)
- **SHACL shapes** (이번 세션 4 → 30개):
  - `serving-validation-shapes-v3.ttl` (Conforms: True 검증 완료)
  - 카테고리: alethic 7 / deontic 7 / bridge 6 / cardinality 3 / domain 3

**BFO + LKIF-Core 2-layer** (이번 세션 정형화):
- **Layer A (alethic)**: Photo, VisualObservation, RiskFeature, Equipment, Worker → `rdfs:subClassOf bfo:*`
- **Layer B (deontic)**: law:Article, sr:SafetyRequirement, lkif:Obligation/Permission/Prohibition → `rdfs:subClassOf lkif:*`
- **Bridge property**: `core:violatesObligation`, `core:observedIn`, `core:appliesTo`

## Layer 3 — PG Materialization

**역할**: Layer 2 추론 결과 → PG table cache (runtime ms 응답)

**현재 운영 (5단계 일부)**:
- `kosha_guides`, `work_processes`, `she_patterns`, `safety_requirements`, `ci_sr_mapping`, `penalty_rules`, `penalty_conditions`
- 이미 운영 중

**7단계 (목표) — 추가 재물질화 대상**:
| PG 테이블 | 재물질화 내용 | 현재 → 7단계 |
|---|---|---|
| `she_patterns` | reasoner 추론 신규 패턴 | 1,616 (Phase 3 validation 후) → 수천 |
| `guide_usage_profiles` | 현재 `guide_domain_profiles.json` | JSON lookup → PG SELECT |
| `guide_domain_incompatibilities` (신규) | LLM-mined KB (2,232 vetted + 8 F.3.2 candidate = **2,240**) | JSON → PG SELECT |
| `ci_sr_mapping` | reasoner 도출 매핑 확장 | 수동 → 자동 추론 |
| `penalty_rules` + `penalty_conditions` | deontic chain | 수동 → 자동 도출 |

**적재 패턴** (기존):
- `serving-team/08-app/backend/scripts/import_guide_usage_profiles_to_pg.py` 패턴 확장
- 새 import 스크립트: `import_domain_incompatibilities_to_pg.py`, `import_reasoner_outputs_to_pg.py`

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
2. Layer 0: Vision LLM → JSON
   ↓
3. Layer 1: Normalizer → canonical code
   ↓
4. Layer 2: SHE matcher → matched SHE patterns
   ↓
5. Layer 3: PG SELECT (SR/Guide/Penalty)
   ↓
6. Phase B (Layer 2 보강): embedding pre-filter + LLM rerank (회색영역만)
   ↓
7. Phase A.4 (Layer 2 보강): dynamic incompatibility KB lookup
   ↓
8. 응답 JSON 반환
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
[현재 (2026-05-17)]
    Layer 0-3 + Phase E.2 (Openllet 통합 완료) + Phase 3 (1,616 SHE, reasoning 1,902건 차단)
    + Layer 4 일부 (Phase C incompatibility + F.3.0 분류 + F.3.2 first batch 8 candidate + A hook)
    ─ LLM 의존 hybrid → Layer 4 본격 진입 중
[Phase F.1] Layer 1 Normalizer auto-registration (다음 우선순위, 1주)
[Phase F.3 본격] Layer 4 closed loop (F.3.1 reasoner channel + F.3.4 compile + F.3.5 cron)
[Phase G/7단계] PG materialize (reasoner 결과 → 서빙 ms 응답)
[Phase J] OBO Foundry 등재 (오픈소스, 국제 표준)
```

## 참고 문서

- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
- [Ontology Learning Layer 상세](ontology-learning-layer.md)
- [LLM 의존 폐지 path](llm-dependency-evolution.md)
- [학계 reference 9 paper](../governance/ontology-learning-references.md)
