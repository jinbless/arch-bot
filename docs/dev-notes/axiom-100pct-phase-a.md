# Phase A Runbook — Tier 1 SWRL (R-2, R-4) + ABox 정합성 발견

**Date**: 2026-05-19
**Commit**: `5be7dc1`
**Plan**: [ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md) Phase A
**Sprint context**: Ontology Axiom 100% — current orthodox score ~75-80% → target 100%.

> 본 dev-note는 commit `5be7dc1` 이후 retroactive로 작성됨 (Phase B의 dev-note 패턴 정렬).

---

## 결과 요약

| 항목 | 결과 |
|---|---|
| TBox 신규 ObjectProperty | 1 (`core:dependsOn`) |
| SWRL 정형 rule | 2 (R-2 coApplicable, R-4 dependsOn) |
| Pellet load | OK (981,571 base triples) |
| R-2 inferred | 626 |
| R-4 inferred | 626 |
| 새 발견 | ABox SR-Article 1:1 매핑 (Phase K 후보) |

---

## 신규 파일

### 1. `ontology-team/06-reasoning/ontology/kosha-ontology-v4-deps-patch.ttl`

**TBox 추가** (+6 triples):

```turtle
core:dependsOn a owl:ObjectProperty ;
    rdfs:label "의존 관계"@ko ;
    rdfs:comment "R-4 결과: 같은 Hazard + 같은 Article을 다루는 SR 간 의존."@ko ;
    rdfs:domain sr:SafetyRequirement ;
    rdfs:range sr:SafetyRequirement .
```

### 2. `ontology-team/06-reasoning/ontology/kosha-rules-r2-r4-swrl.ttl`

**SWRL formal serialization** (+80 triples):

- **R-2**: `SafetyRequirement ∧ SafetyRequirement ∧ appliesToArticle(sr1,art) ∧ appliesToArticle(sr2,art) → coApplicable(sr1,sr2)`
- **R-4**: `SafetyRequirement ∧ SafetyRequirement ∧ addressesHazard(sr1,haz) ∧ addressesHazard(sr2,haz) ∧ appliesToArticle(sr1,art) ∧ appliesToArticle(sr2,art) → dependsOn(sr1,sr2)`

**`swrlb:notEqual` 회피 사유**:
- Pellet/Openllet에서 `swrlb:notEqual`을 individual variable에 적용하면 "unsafe variable" 에러 발생
- UNA (Unique Name Assumption) 없는 OWA 환경에서 individual identity 비교는 undecidable
- DL-safe pattern 채택: `?sr1 = ?sr2` self-loop 허용 (의미적 무해, redundant triple만 추가)
- `core:coApplicable`은 `owl:SymmetricProperty` (kosha-ontology-v2.formatted.ttl L71-73) → 양방향 자동

---

## 수정 파일

### `ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java`

`sources` 배열에 2 entry 추가:
- `/kosha-ontology-v4-deps-patch.ttl` (TURTLE)
- `/kosha-rules-r2-r4-swrl.ttl` (TURTLE)

Docker rebuild + container recreate 완료.

---

## 검증

```bash
# Docker rebuild + recreate
cd ontology-team/06-reasoning/ontology/docker
docker compose build fuseki
docker compose up -d --force-recreate fuseki
# Pellet prepare ~18분 대기

# R-2 inferred
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?s1 <https://cashtoss.info/ontology#coApplicable> ?s2 }'
# → 626

# R-4 inferred
curl -X POST http://localhost:3030/kosha/sparql \
  -H "Content-Type: application/sparql-query" \
  --data 'SELECT (COUNT(*) AS ?c) WHERE { ?s1 <https://cashtoss.info/ontology#dependsOn> ?s2 }'
# → 626
```

✅ Pellet `FunInv` 경고 없음 (Openllet AsymmetricProperty 패치 T4 이후 안정).

---

## ⚠️ ABox 정합성 새 발견 (Phase K 후보)

R-2/R-4가 fire하지만 **cross-pair inferred = 0** (self-loop 626건만):

```sparql
# SR-Article 매핑 분포
SELECT (COUNT(?sr) AS ?totalSR) (COUNT(DISTINCT ?art) AS ?distinctArt)
WHERE { ?sr <https://cashtoss.info/ontology/sr#appliesToArticle> ?art . }
# → totalSR=626, distinctArt=626 (1:1 매핑)
```

**원인**: ABox 구축 시 SR별로 unique Article instance 생성 — 실제 도메인의 N:1 관계 (한 Article → 여러 SR) 표현 안 됨.

**의미**:
- R-2/R-4 SWRL은 정형 OK + Pellet inference fire 정상
- 하지만 ABox에서 "같은 Article을 공유하는 SR pair" = 0건 → cross-pair 추론 0
- self-loop ?sr1=?sr2 매칭 626건만 발생 (semantic 무해, redundant)

**Phase K (별도 sprint 후보)**:
- Article instance unification — 같은 조항을 공유하는 SR을 같은 Article URI로 통합
- 또는 `sr:appliesToArticle`을 `sr:basedOnArticleIdentifier` (datatype) + skolemization으로 derived
- 본 sprint 범위 외 (TBox axiom이 아니라 ABox 데이터 통합 + skolemization)

---

## Acceptance

- ✅ SWRL R-2 + R-4 OWL/RDF serialization 완료 (Pellet load + inference fire)
- ✅ Pellet `FunInv` 경고 없음
- ⚠️ Cross-pair inferred = 0 (ABox 정합성 별도 sprint)
- **결론**: SWRL formalization acceptance 진입. 의미적 발견은 Phase K로.

정석 점수 변화: ~75-80% → ~78-82% (SWRL formal 2 → 4 actual rules).

---

## Related

- [ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md) — sprint plan
- [axiom-100pct-phase-b.md](axiom-100pct-phase-b.md) — Phase B runbook (R-9~R-13)
- [t4-swrl-pellet-integration.md](t4-swrl-pellet-integration.md) — R-1/R-3 패턴 (재사용)
- commit [`5be7dc1`](https://github.com/jinbless/arch-bot/commit/5be7dc1)
