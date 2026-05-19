# T4 #3 — SWRL Pellet 실행기 통합 결과 (2026-05-19)

> 기존 `kosha-rules-v2.swrl` (22+8 rules pseudo-code 문서)를 OWL/RDF SWRL serialization으로 변환하여 Pellet/Openllet에서 실제 추론 실행. R-1/R-3 우선 변환 + 발화 검증 완료.

## TL;DR — 핵심 결과

| SWRL Rule | 추론 결과 | 검증 |
|---|---|---|
| **R-1 exemptedBy** | **107 triples 발화** | NormStatement modifies + Exemption modality 패턴 매칭 |
| **R-3 HighSeverityPenalty** | **3,579 triples 발화** | severityScore ≥ 5와 100% 일치 (Pellet 정확한 swrlb:greaterThanOrEqual 평가) |

→ **Pellet/Openllet의 SWRL native 지원 입증**. 의사코드 문서가 실제 추론 가능 facts로 변환됨.

## Background

`kosha-rules-v2.swrl` 파일 (14KB)은 R-1~R-30 SWRL rules를 자연어 + Horn clause 의사코드로 기록한 **문서**. Pellet은 OWL/RDF SWRL serialization만 native 실행 가능.

## Conversion

신규 파일: `ontology-team/06-reasoning/ontology/kosha-rules-r1-r3-swrl.ttl`

**R-1 (Exemption inference)**:
```turtle
kr:R1_ExemptedByRule a swrl:Imp ;
  swrl:body ( ... ClassAtom NormStatement, hasModality Obligation/Exemption, modifies ... ) ;
  swrl:head ( ... IndividualPropertyAtom core:exemptedBy ... ) .
```

**R-3 (High-severity classification with built-in)**:
```turtle
kr:R3_HighSeverityRule a swrl:Imp ;
  swrl:body ( ... SanctionType, severityScore, swrlb:greaterThanOrEqual(?score, 5) ... ) ;
  swrl:head ( ... ClassAtom penalty:HighSeverityPenalty ... ) .
```

신규 OWL class: `penalty:HighSeverityPenalty` (sub of SanctionType).

## Fuseki Java Loader

`KoshaFusekiServer.java` sources array에 새 파일 추가:
```java
{"/kosha-rules-r1-r3-swrl.ttl", "TURTLE", "T4 #3 SWRL rules R-1/R-3 (OWL serialization)"},
```

Docker image rebuild + container recreate 후 자동 로드 (+76 triples).

## Verification (Pellet SWRL 발화)

SPARQL queries against Fuseki 3030:

```sparql
SELECT (COUNT(?s) AS ?n) WHERE { ?s a penalty:HighSeverityPenalty }
# → 3,579 (R-3 inferred)

SELECT (COUNT(*) AS ?n) WHERE { ?s core:exemptedBy ?o }
# → 107 (R-1 inferred)

SELECT (COUNT(*) AS ?n) WHERE { ?s penalty:severityScore ?v . FILTER(?v >= 5) }
# → 3,579 (sanity: matches HighSeverityPenalty count, R-3 100% correctness)
```

## Gate 3 vs baseline_v3

- she_accuracy: -0.0013 (noise)
- penalty_accuracy: +27.16%p (G.3 유지)
- overall_accuracy: +18.81%p (G.3 유지)
- false_negative_rate: -0.0189 (개선)

→ SWRL 추론은 batch/reasoner 영역, runtime path 직접 사용 없음 → backend metric 변화 0. T4 #3 의 목적은 reasoner correctness 검증.

## Known Limitations

- R-2 (coApplicable)는 이미 `run_inference.py`에서 SPARQL CONSTRUCT로 적용 중. SWRL 변환은 중복.
- R-4~R-30 변환 미완 (별도 sprint 시 점진). 각 rule은 OWL/RDF serialization 표준 패턴 답습.
- 의사코드 → SWRL 변환은 의미 보존하지만 syntax 보일러플레이트 큼 (1 rule ≈ 30-50 triples).

## Future Work

- 모든 22+8 SWRL rules → OWL serialization (별도 sprint)
- SHACL-AdvancedFeatures (sh:rule) 와 비교 (선언적 대안)
- Pellet에서 빠진 SWRL built-ins 처리 (e.g., string operations)

## Related

- `ontology-team/06-reasoning/ontology/kosha-rules-v2.swrl` (의사코드 원본)
- `ontology-team/06-reasoning/ontology/scripts/run_inference.py` (R-1/R-2 SPARQL CONSTRUCT 적용 — 운영 중)
- [phase-g.4-she-patterns-reasoner-derived.md](phase-g.4-she-patterns-reasoner-derived.md) — Openllet 환경 검증
- [t4-administrative-fine-scope-decision.md](t4-administrative-fine-scope-decision.md)
- [t4-77-she-matcher-integration-decision.md](t4-77-she-matcher-integration-decision.md)
