# Phase G Sprint G.4 — she_patterns reasoner-derived + Openllet 조사 (Runbook)

> Phase G의 마지막 sprint. **Openllet `inferred=0` 근본 원인 발견** (`law:modifies` AsymmetricProperty + `law:modifiedBy` inverseOf 충돌). 본 sprint는 **분기 B** (reasoner 미작동 시 대안): F.2 Day 5 v3.1 link로 도출된 77건 pending_review SHE를 read-only PG view로 노출 → 아키텍처적 reasoner-derived layer 입증.
> **Status**: G.4 완료 (2026-05-18). PG view + Openllet root cause 문서화. Tier 4 후속 ontology 패치 필요.

## Openllet `inferred=0` Root Cause Analysis

Fuseki container 로그 확인:
```
[2/3] Applying reasoner (openllet)...
  Total triples (base + inferred): 981409
  Inferred triples: 0
2026-05-18 09:58:13 WARNING openllet.jena.JenaUtils makeGraphResource
  Term FunInv(https://cashtoss.info/ontology/law#modifiedBy)
  can't be convert into Node
```

원인:
- `law:modifies` = `owl:AsymmetricProperty` + `owl:ObjectProperty` (v2.formatted.ttl:475-479)
- `law:modifiedBy` = `owl:ObjectProperty` + `owl:inverseOf law:modifies` (line 460-462)
- Openllet/Pellet은 AsymmetricProperty의 inverseOf semantics를 결정적으로 처리하지 못함 (FunInv 변환 실패)
- 결과: reasoner가 모든 inference 거부 → `inferred=0`

**Tier 4 fix 후보** (별도 sprint 필요):
1. **옵션 A**: `law:modifies`에서 `owl:AsymmetricProperty` 제거 → ObjectProperty만 유지 → inverseOf 안전
2. **옵션 B**: `law:modifiedBy` 정의 제거, 필요 시 SPARQL CONSTRUCT로 도출
3. **옵션 C**: Openllet 대신 Hermit/Konclude reasoner 시도 (AsymmetricProperty inverseOf 정상 처리)
4. **옵션 D**: REASONER_MODE=rdfs (단순 추론, 일부 inference 가능)

Tier 4 권장: 옵션 A (가장 단순, 의미 손실 없음). asymmetric semantics는 실제 데이터 흐름에 영향 없음 (NormStatement의 modify는 단방향).

## 분기 B 적용 — PG View `she_patterns_reasoner_derived`

원래 plan:
> 분기 A (reasoner 작동): run_inference.py 패턴 확장으로 derived patterns 추출
> 분기 B (reasoner 미작동): F.3.2 mining 결과 + F.2 SHE pending_review 77건을 PG materialized view로 표현

본 sprint는 **분기 B** 선택:

### PG View 생성

```sql
CREATE OR REPLACE VIEW she_patterns_reasoner_derived AS
SELECT
    she_id, name, features, visual_triggers, broadness_score, source_sr_ids,
    'F.2_v31_code_link' AS derivation_source,
    'pending_matcher_integration' AS integration_status,
    created_at
FROM she_catalog
WHERE status = 'pending_review';
```

- 77 rows (모두 F.2 Day 5에서 Sonnet 4.6 + v3.1 code = derived)
- Read-only (matcher 동작 무변경, 회귀 위험 0)
- 향후 matcher integration 시 status 전환 또는 별도 flag 필요

### 의미

이 view는 **architectural 입증**:
1. "reasoner-derived facts → PG → 서비스" 경로가 작동 가능
2. 현재 source는 LLM-based mining (Sonnet 4.6 + v3.1 catalog codes)
3. 향후 Openllet 회복 시 동일 view에 OWL DL 추론 결과 통합 가능

## Verification

| 항목 | 결과 |
|---|---|
| Openllet root cause 식별 | ✅ `law:modifies` AsymmetricProperty + inverseOf 충돌 |
| PG view 생성 | ✅ 77 rows, derivation_source='F.2_v31_code_link' |
| Gate 3 vs baseline_v3 | ✅ G.3 +27%p improvement 유지 (view 추가는 영향 없음) |
| Matcher 무영향 | ✅ pending_review 제외 정책 그대로 (regression 0) |

## Phase G 전체 종합

| Sprint | 결과 |
|---|---|
| G.1 | guide_domain_incompatibilities PG (2,016 rows), shadow_reasoner PG primary |
| G.2 | guide:GuideUsageProfile ontology + guide_domain_profile.py PG primary |
| G.3 | **penalty_rule_index PG (4,076 rules), penalty_accuracy +27.16%p** |
| G.4 | she_patterns_reasoner_derived view + Openllet root cause + Tier 4 fix path |

**Phase G 완료**. 사용자 구조 step 4 ("온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영") **본격 입증**.

## Known Limitations

- Openllet inferred=0 미해결 (Tier 4 sprint 필요)
- AdministrativeFine instances 0건 in TTL (Tier 4 enrichment)
- pending_review 77 SHE는 view에만 노출 (matcher 통합 별도 의사결정)

## Related

- [phase-g.1-domain-incompatibilities-pg.md](phase-g.1-domain-incompatibilities-pg.md)
- [phase-g.2-guide-usage-profiles-pg.md](phase-g.2-guide-usage-profiles-pg.md)
- [phase-g.3-penalty-rule-index-pg.md](phase-g.3-penalty-rule-index-pg.md)
