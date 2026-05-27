# Ontology Axiom 100% 정석화 Sprint Plan

> **Status**: ✅ Phase A 완료 (2026-05-19) — SWRL R-2/R-4 정형 OK + ABox 정합성 이슈 식별 (별도 sprint 후보). Phase B 다음 세션 진입.
> **Trigger**: 직전 hazard-direct pivot 완주 후 정석 OWL DL 평가 → 현재 정석 점수 ~75-80%. SWRL formal rule 2/30, Restriction 6개, hazard-direct OWL 미격상, F.3.2 candidate 2,184 잔여, AsymmetricProperty 0.
> **Predecessor**: hazard-direct pivot (commit `164de5a`), 문서 전수 검증 (commit `6d3f431`)
> **Predicted duration**: ~4-6주 (10 Phase, hazard-direct pivot보다 큼)
> **Predicted cost**: ~$15-25 (Phase I F.3.2 batch LLM verify $10-20 + 기타)

---

## Context

### 현재 정석 점수 (직전 평가)

| 정석 기준 | 현재 | 비고 |
|---|---|---|
| TBox/ABox 분리 | 🟢 100% | kosha-ontology-v2 ↔ kosha-instances |
| Description Logic | 🟢 100% | 318 owl:Class + 90 ObjectProp + 65 DataProp |
| 계층 axioms | 🟢 100% | 314 subClassOf, dashboard 7-Layer |
| 관계 axiom (inverse/transitive/etc) | 🟡 70% | 9 inverse, 23 Functional, 2 Transitive, **0 Asymmetric** |
| Disjointness | 🟢 100% | 91 disjointWith |
| Cardinality Restrictions | 🟡 40% | **6개만** (G.2 GuideUsageProfile) |
| Rules | 🟡 60% | SWRL **2/30 actual** + 2,250 SHACL |
| Reasoner + OWA | 🟢 100% | Openllet + pyshacl shadow |
| **종합** | **~75-80%** | — |

### 정석 100%의 측정 가능한 정의

본 sprint 종료 시점에:

| 갭 | 현재 | 목표 |
|---|---:|---:|
| SWRL formal rules | 2 (R-1, R-3) | **28** (R-2 + R-4~R-30 모두 OWL/SWRL/SHACL/native 중 하나로 구현) |
| `owl:Restriction` | 6 | **≥ 30** |
| Missing ontology properties | ~22 | **0** (R-9~R-30 의사코드 prefix 모두 정의됨) |
| Hazard-Direct OWL Class | 0 (Pydantic) | **`risk:NaturalLanguageHazardCategory`** + instance hierarchy |
| F.3.2 candidate axioms | 8 vetted / 2,184 candidate | **잔여 < 100** (자동 batch 후 결판) |
| `owl:AsymmetricProperty` | 0 | **≥ 1** (`law:modifies` Openllet 호환 복원) |

---

## Acceptance Criteria

- **AC-1**: 28 SWRL/SHACL/native rules 모두 ontology 파일에 포함 + Fuseki 로드 + SPARQL 검증 inferred count ≥ 1
- **AC-2**: `owl:Restriction` ≥ 30 (SR/penalty/risk/guide 핵심 클래스)
- **AC-3**: `risk:NaturalLanguageHazardCategory` OWL Class + 21+ vetted alias가 instance로 등재
- **AC-4**: F.3.2 candidate < 100 (점진 promotion + auto batch)
- **AC-5**: `law:modifies`에 `owl:AsymmetricProperty` 복원 + Openllet `FunInv` 경고 없음
- **AC-6**: Gate 3 통과 — 2360 synthetic replay에서 모든 metric regression ≤ 0.02

---

## SWRL 의사코드 분류 (30개 rule)

### 이미 OWL native으로 구현 (정형화 불필요, 5개)
- R-5: `inverseOf` (`owl:inverseOf` 9개 이미 선언)
- R-6: `SymmetricProperty` (`owl:SymmetricProperty` 2개)
- R-7: `subClassOf` (314 subClassOf)
- R-8: `disjointWith` (91 disjointWith)
- R-29: R-3 derivative (penalty:HighSeverityPenalty 자동 분류)

### SWRL formal serialization 필요 (Tier별 23개)
- **Tier 1** (즉시, property 모두 정의됨): R-2 (coApplicable), R-4 (dependsOn)
- **Tier 2** (alethic, TBox 확장 필요): R-9, R-10, R-11, R-12, R-13
- **Tier 3** (bridge, namespace 정합): R-14, R-15, R-16, R-17, R-18
- **Tier 4** (deontic): R-19, R-20, R-21, R-22, R-23
- **Tier 5** (violation, R-27 SHACL fallback): R-24, R-25, R-26
- **Tier 6** (penalty chain): R-28, R-30

### SHACL constraint로 표현 (SWRL negation 한계, 1개)
- R-27 (ExcludeExempted) — Open World에서 부재 증명 불가, SHACL `sh:not` 사용

### 이미 정형 SWRL (재확인, 2개)
- R-1 (exemptedBy) ✅ 107 inferred
- R-3 (highSeverityPenalty) ✅ 3,579 inferred

---

## Phase별 상세

### Phase A — Tier 1 SWRL (R-2, R-4) ✅ 완료 (2026-05-19)

- ✅ **TBox 확장**: `core:dependsOn` 신규 ObjectProperty 정의 (`kosha-ontology-v4-deps-patch.ttl`, +6 triples)
- ✅ **SWRL TTL**: `kosha-rules-r2-r4-swrl.ttl` 신규 (+80 triples)
  - R-2: SafetyRequirement × appliesToArticle 공통 → coApplicable (SymmetricProperty 자동 양방향)
  - R-4: SafetyRequirement × addressesHazard ∩ appliesToArticle → dependsOn (신규 property)
  - **`swrlb:notEqual` 회피**: Pellet에서 individual variable에 "unsafe variable" 에러 → DL-safe 패턴 (self-loop 허용)
- ✅ **Fuseki Java**: `KoshaFusekiServer.java` sources +2 entries
- ✅ **Docker image rebuild** + container recreate, 총 981,571 base triples 로드
- ✅ **SPARQL 검증**:
  - R-2 `coApplicable`: **626 inferred** (Pellet load + fire 정상)
  - R-4 `dependsOn`: **626 inferred**

#### ⚠️ Phase A 새 발견: ABox 정합성 이슈 (Article instance unification)

- `sr:appliesToArticle` triple = 626 / distinct Article = **626** → SR-Article **1:1 매핑**.
- 즉 ABox에서 "같은 Article을 공유하는 SR pair" = **0건**.
- R-2/R-4 SWRL은 정형 OK + Pellet inference fire하지만 cross-pair는 매칭 불가 (self-loop 626건만).
- **원인**: ABox 구축 시 SR별로 unique Article instance 생성 (실제 도메인의 N:1 관계 표현 안 됨).
- **추후 sprint 후보 (Phase K)**: Article instance unification — 같은 조항을 공유하는 SR을 같은 Article URI로 통합.
  - 또는 `sr:appliesToArticle`을 `sr:basedOnArticleIdentifier` (datatype) + skolemization으로 derived.
  - **본 sprint 범위 외** — Phase A SWRL 정형 자체는 acceptance.

#### Acceptance 평가
- ✅ SWRL R-2 + R-4 OWL/RDF serialization 완료 (Pellet load + inference fire)
- ✅ Pellet `FunInv` 경고 없음
- ⚠️ Cross-pair inferred = 0 (ABox 정합성 별도 sprint)
- **결론**: SWRL formalization 진입 acceptance. 의미적 발견은 다음 sprint.

---

### Phase B — Tier 2 SWRL alethic chain (R-9~R-13)

#### Day 1: TBox 확장 (`kosha-ontology-v4-alethic-patch.ttl`)

Missing properties to add:
- `risk:hasRiskFeature` (Photo/Obs → RiskFeature)
- `risk:correspondsToHazard` (RiskFeature → Hazard)
- `risk:indicatesByCue` (RiskFeature → VisualCue)
- `risk:appliesToEquipment` (RiskFeature → Equipment)
- `risk:compatibleWithSpec` (RiskFeature → EquipmentSpec)
- `haz:hasHazard` (RiskFeature → Hazard)
- `app:matchesProcess` (SituationMatch → WorkProcess)
- `app:temporalStageForProcess` (WorkProcess → TemporalStage)
- `app:hasTemporalStage` (SituationMatch → TemporalStage)

#### Day 2-3: SWRL TTL `kosha-rules-r9-r13-swrl.ttl`

- R-09: Photo + hasVisualCue → observedIn(VisualObservation)
- R-10: VisualObservation + observesVisualCue + indicatesByCue → hasRiskFeature
- R-11: RiskFeature + correspondsToHazard → hasHazard
- R-12: RiskFeature + Equipment + compatibleWithSpec → appliesToEquipment
- R-13: SituationMatch + WorkProcess + temporalStageForProcess → hasTemporalStage

#### Day 4: 검증
- Fuseki rebuild + SPARQL inferred count
- Pellet consistency

#### Day 5: 문서 + commit

---

### Phase C — Tier 3 SWRL bridge chain (R-14~R-18)

TBox 추가:
- `bridge:observedIn`, `bridge:appliesTo` (Bridge namespace 신설)
- `sr:requiresFindingStatus`, `sr:appliesToEquipment`
- `app:Noncompliance`, `app:indicatesNoncompliance`

5 SWRL rules in `kosha-rules-r14-r18-swrl.ttl`.

---

### Phase D — Tier 4 SWRL deontic chain (R-19~R-23)

TBox 추가:
- `law:groundedBySR` (NS ← SR backward link)
- `law:appliesArticle` (강화된 SR → Article)
- `core:hasModality` (R-20에서 사용, `law:hasModality`와 alignment)
- `penalty:appliesToNormStatement`, `penalty:penalizesNorm`

5 SWRL rules in `kosha-rules-r19-r23-swrl.ttl`.

---

### Phase E — Tier 5 SWRL violation chain (R-24~R-26) + R-27 SHACL

TBox:
- `core:hasViolation`
- `agent:Worker` (또는 기존 클래스 매핑)
- `bridge:violatesObligation`

3 SWRL rules in `kosha-rules-r24-r26-swrl.ttl`.

R-27 SHACL shape: `kosha-r27-shacl-exempted.ttl` (`sh:not` constraint).

---

### Phase F — Tier 6 SWRL penalty chain (R-28~R-30)

TBox:
- `penalty:appliesToExposure`, `penalty:appliesPenaltyRule`, `penalty:resultsIn`
- `app:hasPenaltyLevel`, `app:hasPenaltyResult`, `app:HighSeverity`

3 SWRL rules in `kosha-rules-r28-r30-swrl.ttl`.

---

### Phase G — owl:Restriction 확대 (6 → 30+)

핵심 클래스별 cardinality / value restriction 추가:

| Class | Restriction |
|---|---|
| `sr:SafetyRequirement` | `addressesHazard min 1`, `appliesToArticle min 1` |
| `sr:SafetyRequirement` | `applicable_industry max 84` |
| `penalty:PenaltyRule` | `appliesToNormStatement exactly 1`, `severityScore exactly 1` |
| `penalty:CriminalSanction` | `maxFine min 0`, `maxPrisonYears min 0` |
| `risk:RiskFeature` | `correspondsToHazard min 1` |
| `risk:RiskFeature` | `axis exactly 1` (accident_type/hazardous_agent/work_context/ppe_state/environmental) |
| `she:SituationalHazardPattern` | `addressesHazard min 1`, `appliesToWorkContext min 1` |
| `guide:KoshaGuide` | `hasGuideSection min 1`, `domain exactly 1` |
| `law:Article` | `inChapter exactly 1` |
| `law:NormStatement` | `hasModality exactly 1` |

신규 `kosha-ontology-v4-restrictions-patch.ttl` (~24+ Restriction 추가).

---

### Phase H — Hazard-Direct OWL 격상

#### Day 1-2: TBox 신규 class
```turtle
risk:NaturalLanguageHazardCategory a owl:Class ;
    rdfs:subClassOf risk:RiskFeature ;
    rdfs:label "자연어 위험요소 카테고리"@ko ;
    rdfs:comment "Vision LLM이 자연어로 출력한 hazard.name (예: '추락', '끼임/협착')."@ko .

risk:mapsToCanonicalCode a owl:ObjectProperty ;
    rdfs:domain risk:NaturalLanguageHazardCategory ;
    rdfs:range risk:RiskFeature .

risk:catalogConfidence a owl:DatatypeProperty ;
    rdfs:domain risk:NaturalLanguageHazardCategory ;
    rdfs:range xsd:decimal .
```

#### Day 3: alias → instance 변환
- 21 vetted alias (`risk_feature_aliases.json` Phase 2 산출) → OWL instance triples
- `data-team/05-enrichment/llm-scripts/aliases_to_owl_instances.py` 신규
- 출력: `kosha-instances-hazard-direct.ttl` (21 NaturalLanguageHazardCategory + mapsToCanonicalCode)

#### Day 4: Backend 통합
- `hazard_normalizer.normalize_hazards_array()` 강화: alias DB 대신 ontology SPARQL 조회 옵션 (feature flag)
- `analysis_pipeline._build_hazard_items()`: `mapped_codes` audit가 ontology instance URI 참조

#### Day 5: 8 photo 재평가 + Gate 3

---

### Phase I — F.3.2 candidate 2,184 자동 batch

#### Day 1: auto-promotion 스크립트
- `data-team/05-enrichment/llm-scripts/promote_f32_auto_batch.py` 신규
- confidence threshold 0.85 + Gate 3 wrap
- 50개 batch 단위로 1-by-1 promotion 자동 실행

#### Day 2-3: 실행
- 2,184 candidate → confidence ≥ 0.85 selection (~500-800건 예상)
- Gate 3 통과 시 vetted, 회귀 시 자동 rollback
- 잔여 candidate (< 100 목표)

LLM cost: ~$10-20 (Sonnet 4.6 Gate 2 verify).

---

### Phase J — AsymmetricProperty 복원 + 최종 검증

#### Day 1: Openllet 호환 패턴 연구
- `law:modifies`의 AsymmetricProperty 복원
- inverseOf와의 충돌 회피: inverseOf 제거 + AsymmetricProperty 유지 또는 별도 property
- Pellet docker rebuild + `FunInv` 경고 모니터링

#### Day 2: 전체 sprint verification
- 정석 100% acceptance criteria 6개 모두 확인
- Gate 3 PASS (2360 synthetic)
- 8 photo real eval
- pyshacl shadow check 0 violation
- 정본 문서 + verify_session_docs.py 갱신

---

## Critical Files

### 신규 (예상 12+ files)
```
docs/workplans/ontology-axiom-100pct.md                          ← 본 문서
docs/dev-notes/axiom-100pct-phase-{a,b,c,d,e,f,g,h,i,j}.md       ← Phase별 runbook

ontology-team/06-reasoning/ontology/
  kosha-ontology-v4-deps-patch.ttl                ← Phase A (core:dependsOn)
  kosha-ontology-v4-alethic-patch.ttl             ← Phase B (risk:*, haz:*)
  kosha-ontology-v4-bridge-patch.ttl              ← Phase C
  kosha-ontology-v4-deontic-patch.ttl             ← Phase D
  kosha-ontology-v4-violation-patch.ttl           ← Phase E
  kosha-ontology-v4-penalty-extra-patch.ttl       ← Phase F
  kosha-ontology-v4-restrictions-patch.ttl        ← Phase G (24+ Restriction)
  kosha-ontology-v4-hazard-direct-patch.ttl       ← Phase H (NaturalLanguageHazardCategory)
  kosha-rules-r2-r4-swrl.ttl                      ← Phase A
  kosha-rules-r9-r13-swrl.ttl                     ← Phase B
  kosha-rules-r14-r18-swrl.ttl                    ← Phase C
  kosha-rules-r19-r23-swrl.ttl                    ← Phase D
  kosha-rules-r24-r26-swrl.ttl                    ← Phase E
  kosha-rules-r28-r30-swrl.ttl                    ← Phase F
  kosha-r27-shacl-exempted.ttl                    ← Phase E
  kosha-instances-hazard-direct.ttl               ← Phase H

data-team/05-enrichment/llm-scripts/
  aliases_to_owl_instances.py                     ← Phase H
  promote_f32_auto_batch.py                       ← Phase I
```

### 수정 (~5 files)
```
ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java
  └─ sources array에 신규 TTL 14+ 추가 (Phase A~J)
ontology-team/06-reasoning/ontology/kosha-ontology-v2.formatted.ttl
ontology-team/06-reasoning/ontology/kosha-ontology-v2.owl
  └─ Phase J: law:modifies AsymmetricProperty 복원
serving-team/08-app/backend/app/services/hazard_normalizer.py
  └─ Phase H: SPARQL alias lookup 옵션
docs/status/current-session.md
docs/workplans/llm-accelerated-ontology-engineering.md
scripts/verify_session_docs.py
```

---

## Verification

```bash
# Phase A
docker compose build fuseki && docker compose up -d --force-recreate fuseki
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?s1 <https://cashtoss.info/ontology#coApplicable> ?s2 }'
# expect ?c >= 1000

# Phase G (Restriction)
PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/local_consistency_check.py --skip-instances

# Phase H (Hazard-Direct OWL)
HAZARD_DIRECT_MODE=parallel HAZARD_DIRECT_OWL_LOOKUP=on \
  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe ../../../data-team/05-enrichment/llm-scripts/eval_hazard_direct_8photo.py

# Phase I (F.3.2 batch)
ANTHROPIC_API_KEY=... python data-team/05-enrichment/llm-scripts/promote_f32_auto_batch.py --apply --min-conf 0.85

# Phase J 최종 Gate 3
cd serving-team/08-app/backend
.venv/Scripts/python.exe -u scripts/replay_synthetic_observations.py --output /tmp/replay_100pct.json
.venv/Scripts/python.exe scripts/regression_gate.py /tmp/replay_100pct.json
```

---

## Risks + Mitigations

| Risk | Probability | 대응 |
|---|---|---|
| Pellet에서 신규 SWRL rule 충돌 (FunInv 등) | 중 | 각 rule batch마다 docker rebuild + 경고 모니터링 (T4 패턴) |
| R-27 SHACL 표현 어려움 (negation as failure) | 중 | `sh:not` + `sh:property` 조합 또는 별도 SPARQL CONSTRUCT |
| F.3.2 자동 batch 회귀 (Phase I) | 중 | 50개 batch 단위 + Gate 3 wrap (기존 pattern), 회귀 시 자동 rollback |
| Hazard-Direct OWL 격상으로 normalize 응답 latency 증가 | 중 | feature flag (`HAZARD_DIRECT_OWL_LOOKUP=on/off`), default off |
| Restriction 추가로 인한 ABox 위반 | 중 | 각 Restriction batch마다 pyshacl shadow check |
| AsymmetricProperty 복원으로 Pellet FunInv 재발 | 높 | inverseOf 별도 property로 분리 (`law:modifiedBy` 신규) |

---

## Limits / Scope

### 명시 포함
- 28 SWRL/SHACL 정형화 + missing TBox property 추가
- 24+ owl:Restriction 추가
- hazard-direct OWL Class 격상
- F.3.2 자동 batch promotion (사용자 결정)
- AsymmetricProperty 복원

### 명시 제외 (별도 sprint)
- BFO/LKIF imports 갱신
- Phase J OBO Foundry 등재 (별도 1-3개월 plan)
- F.4 CQ Reverse + F.5 GraphRAG (별도 plan)
- Frontend 변경 (Phase H의 backend만 변경)
- **Phase K Article instance unification** (Phase A 발견, ABox 정합성 sprint)
  - 626 SR이 모두 distinct Article에 매핑되어 R-2/R-4 cross-pair inference 무력화
  - 본질적으로 다른 작업 (TBox axiom이 아니라 ABox 데이터 통합 + skolemization)

---

## 사용자 결정 (2026-05-19)

1. ✅ **진행 방식**: 본 세션 = Plan 등록 + Phase A 완주
2. ✅ **Phase H** (hazard-direct OWL 격상): **포함**
3. ✅ **Phase I** (F.3.2 candidate 자동 batch): **포함** (LLM cost ~$10-20)

---

## Related

- [hazard-direct-architecture-pivot.md](hazard-direct-architecture-pivot.md) — 직전 sprint (완주)
- [F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — F.3.2 mining 인프라
- [t4-swrl-pellet-integration.md](../dev-notes/t4-swrl-pellet-integration.md) — R-1/R-3 정형 패턴 (재사용)
- [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md) — Phase G ontology TBox 확장 패턴
- [ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Layer 4.4 Axiom Discovery
