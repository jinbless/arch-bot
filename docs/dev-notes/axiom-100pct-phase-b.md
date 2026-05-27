# Phase B Runbook — Tier 2 SWRL alethic chain (R-9~R-13)

**Date**: 2026-05-27 (continuation of 2026-05-19 Phase A)
**Predecessor**: Phase A — SWRL R-2 + R-4 (commit `5be7dc1`)
**Plan**: [ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md) Phase B
**Sprint context**: Ontology Axiom 100% — current orthodox score ~75-80% → target 100%.

---

## 결과 요약

| 항목 | 결과 |
|---|---|
| TBox 신규 클래스 | 1 (`guide:Equipment`) |
| TBox 신규 ObjectProperty | 10 (9 plan + 1 보조 `guide:equipmentHasSpec`) |
| SWRL 정형 rule | 4 (R-10, R-11, R-12, R-13) |
| SWRL skip rule | 1 (R-9 — 의사코드 결함) |
| Pellet load | OK (981,761 base triples, prepare ~17분) |
| Pellet `FunInv` 경고 | 없음 |
| R-10/R-11/R-12/R-13 inferred | **모두 0** (사유: ABox에 body triple 부재) |
| ABox 분포 (SPARQL 실측) | RiskFeature 179, 나머지 0 |

---

## 신규 파일

### 1. `ontology-team/06-reasoning/ontology/kosha-ontology-v4-alethic-patch.ttl`

**TBox 추가 항목** (Class 1 + ObjectProperty 10):

| Namespace + name | Domain | Range | 사용처 |
|---|---|---|---|
| `guide:Equipment` (Class) | — | — | R-12 body |
| `guide:equipmentHasSpec` | guide:Equipment | guide:EquipmentSpec | R-12 body |
| `risk:hasRiskFeature` | app:VisualObservation | risk:RiskFeature | R-10 head, R-14/R-16/R-26 body |
| `risk:correspondsToHazard` | risk:RiskFeature | haz:Hazard | R-11 body |
| `risk:indicatesByCue` | risk:RiskFeature | app:VisualCue | R-10 body |
| `risk:appliesToEquipment` | risk:RiskFeature | guide:Equipment | R-12 head, R-17 body |
| `risk:compatibleWithSpec` | risk:RiskFeature | guide:EquipmentSpec | R-12 body |
| `haz:hasHazard` | risk:RiskFeature | haz:Hazard | R-11 head, R-14/R-15/R-16/R-26 body |
| `app:matchesProcess` | app:SituationMatch | guide:WorkProcess | R-13 body |
| `app:temporalStageForProcess` | guide:WorkProcess | ctx:TemporalStage | R-13 body |
| `app:hasTemporalStage` | app:SituationMatch | ctx:TemporalStage | R-13 head |

**namespace 충돌 확인**:
- `risk/situation#hasTemporalStage` 이미 존재 (domain SituationalHazardPattern, range TemporalStage, ttl L1352)
- 본 `app:hasTemporalStage` (domain SituationMatch)와 별개 — full IRI 다르므로 충돌 없음
- 둘 다 유지함으로써 SituationalHazardPattern(정적 패턴)과 SituationMatch(인스턴스 매칭) 분리 표현

### 2. `ontology-team/06-reasoning/ontology/kosha-rules-r9-r13-swrl.ttl`

**SWRL formal serialization** — Phase A pattern 답습 (DL-safe, swrlb:notEqual 미사용).

- **R-10**: `VisualObservation ∧ hasVisualCue(obs,cue) ∧ RiskFeature ∧ indicatesByCue(rf,cue) → hasRiskFeature(obs,rf)`
- **R-11**: `RiskFeature ∧ Hazard ∧ correspondsToHazard(rf,hazd) → hasHazard(rf,hazd)`
- **R-12**: `RiskFeature ∧ Equipment ∧ EquipmentSpec ∧ equipmentHasSpec(eq,spec) ∧ compatibleWithSpec(rf,spec) → appliesToEquipment(rf,eq)`
- **R-13**: `SituationMatch ∧ WorkProcess ∧ matchesProcess(sm,wp) ∧ temporalStageForProcess(wp,ts) → hasTemporalStage(sm,ts)`

각 rule은 ClassAtom + IndividualPropertyAtom 조합으로 구성, head는 단일 IndividualPropertyAtom.

---

## R-9 정형 SKIP — 사유

**원본 의사코드** (kosha-rules-v2.swrl L97):
```
observedIn(?obs, ?p) ← Photo(?p) AND hasVisualCue(?p, ?cue) AND VisualObservation(?obs)
```

**세 가지 결함** (SWRL로 정형 불가):

1. **`Photo` 클래스 TBox 미정의**
   - kosha-ontology-v2.formatted.ttl + 모든 patch 파일에 `Photo` class 부재
   - 신규 추가 시 ABox(kosha-instances.ttl)에 photo individual도 함께 등록해야 fire — 현재 사진은 PG에 저장하고 ontology ABox에 photo URI 등록하지 않는 설계 결정

2. **`hasVisualCue` domain mismatch**
   - `app:hasVisualCue`의 domain은 `app:VisualObservation` (ttl L170-173)
   - 의사코드의 `hasVisualCue(?p, ?cue)`에서 `?p`가 Photo이면 domain violation
   - 다른 namespace의 `hasVisualCue`도 존재하지 않음

3. **head가 individual 생성 의도**
   - R-9 head `observedIn(?obs, ?p)`는 VisualObservation `?obs`의 신규 생성을 의도
   - SWRL head는 existing individual 사이의 관계만 표현 가능 (no individual creation)
   - 이는 SWRL의 inherent limitation — Phase E의 R-27 (SHACL fallback) 패턴 참조

**대안**: R-9는 SHACL CONSTRUCT 또는 SPARQL UPDATE로 데이터 변환 단계에서 처리. Phase E (R-24~R-27)에서 R-27 SHACL `sh:not` 패턴과 함께 재검토.

**본 Phase B 범위에서는 정형 SKIP** + 본 사유 기록.

---

## 검증 (Pellet + SPARQL)

```bash
docker compose -f ontology-team/06-reasoning/ontology/docker/docker-compose.yml down
docker compose -f ontology-team/06-reasoning/ontology/docker/docker-compose.yml build fuseki
docker compose -f ontology-team/06-reasoning/ontology/docker/docker-compose.yml up -d
# Pellet prepare ~15-20분 대기 (981,761 base triples)

# R-10 inferred (hasRiskFeature)
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?o <https://cashtoss.info/ontology/risk#hasRiskFeature> ?r }'

# R-11 inferred (hasHazard)
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?r <https://cashtoss.info/ontology/risk/hazard#hasHazard> ?h }'

# R-12 inferred (appliesToEquipment)
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?r <https://cashtoss.info/ontology/risk#appliesToEquipment> ?e }'

# R-13 inferred (hasTemporalStage SituationMatch)
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?s <https://cashtoss.info/ontology/app#hasTemporalStage> ?t }'
```

---

## ABox 정합성 — Phase A 관찰의 연장선 + 실측

Phase A에서 발견한 "ABox SR-Article 1:1 매핑" 이슈는 R-2/R-4 cross-pair inference를 0으로 만들었다.
Phase B의 R-10~R-13는 **더 광범위한 ABox 부재**가 확인됨 (SPARQL 실측, 2026-05-27):

### Rule 별 body atom + ABox 실측

| Rule | Body atom | ABox 실측 (Pellet inferred 포함) |
|---|---|---|
| R-10 | VisualObservation × app:hasVisualCue + RiskFeature × risk:indicatesByCue | VO **0**, hasVisualCue **0**, RF 179, indicatesByCue **0** |
| R-11 | RiskFeature × risk:correspondsToHazard × Hazard | correspondsToHazard **0** |
| R-12 | RiskFeature × compatibleWithSpec + Equipment × equipmentHasSpec | compatibleWithSpec **0**, Equipment **0**, equipmentHasSpec **0** |
| R-13 | SituationMatch × matchesProcess + WorkProcess × temporalStageForProcess | SituationMatch **0**, matchesProcess **0**, temporalStageForProcess **0** |

### 해석

- 본 ontology ABox (`kosha-instances.ttl`, 957,293 base triples)는 **SR/Article/Hazard/Penalty 도메인 지식 위주**
- "사진 관찰 → VisualObservation → RiskFeature → Hazard → SR 매칭" 동적 chain은 **런타임에 PG에서 만들어짐** (FastAPI backend의 `analysis_pipeline`이 생성)
- 따라서 ontology ABox에는 alethic chain runtime instance가 0개 — 본 Phase B SWRL은 학습/추론 정합성 보장에는 적합하지만 **즉시 inference fire 0건**
- RiskFeature 179개는 정적 catalog (3-axis taxonomy: accident_type/hazardous_agent/work_context/ppe_state/environmental) — risk feature의 vocabulary

### 의미

Phase B SWRL formalization은 정석 점수(orthodox score) 향상에 즉시 기여 (SWRL **2 → 6**):
- formal serialization OK + Pellet load PASS + DL-safe pattern OK + no FunInv 경고
- "rule이 존재하므로 추후 ABox enrichment 시 자동 fire 가능" — 정석 OWL DL 관점에서 의미 있음

하지만 **실제 inference fire는 ABox enrichment를 별도 sprint로 진행해야 한다**:
- (a) 서비스 runtime에서 생성된 VisualObservation/SituationMatch instance를 ontology ABox에 등록
- (b) 또는 SWRL inference를 PG ETL로 대체 (4-Layer Architecture의 Layer 3 PG materialization 흐름과 일관)

→ Phase K 후보 또는 5번 LLM enrichment 단계 후속 작업.

---

## Acceptance

- ✅ TBox 11 추가 (Class 1 + Property 10) — kosha-ontology-v4-alethic-patch.ttl
- ✅ SWRL 4 rule formal serialization — kosha-rules-r9-r13-swrl.ttl
- ✅ R-9 정형 SKIP + 사유 명시 (의사코드 결함 인정)
- ✅ Pellet load OK (981,761 base triples, prepare ~17분, FunInv 없음)
- ✅ SPARQL 검증 완료 — 4 rule inferred 0건, ABox 분포 측정 완료
- ⚠️ Inferred count는 ABox 정합성에 의존 (별도 sprint 트래킹) — Phase A 발견의 연장선 + Phase B에서 더 광범위 확인

**결론**: SWRL formalization acceptance 진입. orthodox score SWRL slot **2 → 6** (R-1, R-3, R-2, R-4, R-10, R-11, R-12, R-13 모두 정형). 다음 Phase C (R-14~R-18 bridge chain) 진입.

---

## Related

- [ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md) — sprint plan
- [axiom-100pct-phase-a.md](../dev-notes/axiom-100pct-phase-a.md) — Phase A runbook (or commit `5be7dc1`)
- [kosha-rules-v2.swrl](../../ontology-team/06-reasoning/ontology/kosha-rules-v2.swrl) — 의사코드 원본
- [t4-swrl-pellet-integration.md](t4-swrl-pellet-integration.md) — R-1/R-3 패턴 (재사용)
