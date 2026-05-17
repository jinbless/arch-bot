# LLM 의존 단계적 폐지 path

> arch-bot의 LLM 의존도 진화 — 5단계 hybrid에서 6-7단계 reasoner + materialization으로.
> Vision LLM만 영구 잔존, semantic reasoning은 reasoner로 이전.

## 현재 시스템 = LLM 의존 hybrid (1-5단계)

```
사진 → Vision LLM → text
        ↓
text → Normalizer (alias dict) → canonical code
        ↓
SHE 매칭 (PG, 수백 패턴) ← 1차
        ↓
보완 1: llm_enrichment.json substring 매칭 (5번)  ← 사전 LLM 빌드
        ↓
보완 2: Phase B embedding + LLM rerank             ← runtime LLM
        ↓
보완 3: Phase A LLM-mined incompatibility KB        ← LLM mined
```

**성능을 좌우하는 핵심 변수 = SHE 데이터 풍부도**
- SHE 부족 → enrichment json → Phase B LLM rerank → Phase A KB 순차 보완
- 각 보완 layer가 LLM 호출 추가 + 비용/지연 증가

## 목표 시스템 = declarative reasoning (6-7단계, LLM runtime 0)

```
사진 → Vision LLM → BFO Photo/Observation instance (ABox persist) ← Vision만
        ↓
OWL DL reasoner (Openllet)
  ├─ DisjointClasses (2,232 vetted, Phase A.2 → axiom 변환)
  ├─ SubClassOf hierarchy (BFO + LKIF Layer A+B + bridge)
  ├─ SWRL rules (R-1~R-30, alethic + deontic + bridge chain)
  └─ SHACL shapes (30개, constraint validation)
        ↓
정형 추론 결과 (runtime LLM 호출 없이)
  ├─ Hazard → applicable SR (deontic chain)
  ├─ Photo industry → relevant Guide (domain match)
  └─ Violation → PenaltyRule (legal chain)
        ↓
[7단계 PG 재물질화]
        ↓
reasoner 추론 결과를 PG로 적재
  ├─ she_patterns (수백 → 수천)
  ├─ guide_usage_profiles (json → table)
  ├─ guide_domain_incompatibilities (json → table)
  ├─ ci_sr_mapping (수동 → 추론 확장)
  └─ penalty_rules + penalty_conditions (자동 도출)
        ↓
서빙 = PG SELECT만 (ms 단위, LLM 0회)
```

## LLM 종류별 진화

| LLM 종류 | 6단계 안정화 후 | 이유 |
|---|---|---|
| **Vision LLM** (gpt-4.1) | 🔵 **영구 유지** | reasoner 영역 밖 (AI 인식) |
| **Phase B LLM rerank** (gpt-5.4-nano, 회색영역) | 🟡 **점진 폐지** | OWL DisjointClasses + SHACL이 같은 일 deterministic 수행 |
| **5번 LLM enrichment** (`guide_domain_profiles.json` lookup) | 🟢 **폐지** | OWL TBox + SWRL이 같은 일 정형화 |
| **Phase C self-refine** (자동 신규 페어 mining) | 🟡 **유지** | 새 도메인/사진 추가 시 자율 학습 가치 영구 (Layer 4.7) |

## 7단계 PG 재물질화 — 구체적 대상

| PG 테이블 | 현재 상태 → 7단계 |
|---|---|
| `she_patterns` | 수백 개 → **수천 개+** (reasoner 추론 신규 패턴) |
| `guide_usage_profiles` | JSON lookup → **PG SELECT** |
| `guide_domain_incompatibilities` (신규) | JSON → **PG SELECT** |
| `ci_sr_mapping` | 일부만 → **추론 확장** |
| `penalty_rules` / `penalty_conditions` | 수동 정의 → **자동 도출** (deontic chain) |
| `she_visual_triggers` | 일부 → **확장** |

**적재 패턴 (기존 재사용)**:
- `serving-team/08-app/backend/scripts/import_guide_usage_profiles_to_pg.py` 패턴 확장
- 신규: `import_domain_incompatibilities_to_pg.py`, `import_reasoner_outputs_to_pg.py`

**backend `analysis_pipeline.py`는 변경 없음** — 데이터 source가 풍부해져서 같은 코드가 더 정확한 답을 빠르게 반환.

## Layer 1 (Normalizer) 진화

**현재 한계**: alias 사전 follow-up 게임
- LLM이 새 표현 만들면 매핑 실패 ("매핑 불가 코드" 로그)
- 우리 catalog 확장 187개로 일부 해결 (she_accuracy +4.9%p)

**개선 3가지** (Phase F 후보):

| 방향 | 장점 | 단점 |
|---|---|---|
| **closed vocabulary** — Vision LLM prompt에 valid enum 전체 명시 | 매핑 100%, Normalizer 부담 0 | prompt token +, LLM 자유도 ↓, **새 도메인 못 학습** (사용자 기각) |
| **자동 alias 학습** (Phase F.1, Module 4.1) | 새 표현 자율 등재, long-tail 적응 | 위험 (false positive 가능) → 4-gate 검증 필수 |
| **임베딩 기반 매핑** (Phase F.7 KGE) | semantic 매칭, exact match 한계 극복 | embedding 학습 비용, threshold tuning |

**선택**: **자동 alias 학습 + 임베딩 기반 매핑 hybrid** (closed vocabulary 기각).

## Layer 4 (Ontology Learning) — LLM이 어디로 가는가

LLM은 사라지지 않고 **runtime → 빌드/학습 시점으로 이동**:

```
[Runtime] LLM 호출 → [학습 시점] LLM 호출
   ↓
runtime LLM 호출 거의 0 (vision만)
빌드/학습 시점 LLM은 cron으로 자율 학습 루프 운영
```

**Layer 4 학습 시점 LLM 호출 (영구)**:
- Module 4.1: vocabulary auto-registration
- Module 4.2: TBox class learning
- Module 4.3: Relation mining (Phase A.2 + Phase C.2 영구화)
- Module 4.4: SWRL/SHACL Discovery
- Module 4.5: CQ generation
- Module 4.7: Continual adaptation

**비용 전략**:
- Runtime LLM (사진당) → ~$0 (vision만, ~$0.005/사진)
- 학습 LLM (cron, 100건당) → ~$0.05 (배치, 무관)
- **사용자 응답 시간 무관** (학습은 비동기)

## 한 줄 요약

> "현재는 SHE 부족분을 LLM 보강 JSON으로 메꾸고, 그 JSON이 정형 OWL/SWRL/SHACL로 점진 대체되면, 6단계 reasoner가 runtime LLM 없이도 같은 (실은 더 정밀한) 답을 deterministic하게 줌. 7단계에서 추론 결과를 PG로 재물질화하면 서빙은 PG SELECT만 (ms 단위, LLM 0회). Vision LLM만 영구 잔존. Layer 4 (Ontology Learning)는 학습 시점 LLM으로 long-tail 도메인 자율 적응."

## 참고 문서

- [4-Layer Architecture](4-layer-architecture.md)
- [Ontology Learning Layer 상세](ontology-learning-layer.md)
- [Workplan (정식)](../workplans/llm-accelerated-ontology-engineering.md)
