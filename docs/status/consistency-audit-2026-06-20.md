# 전수 일치성 조사 보고서 — 코드 ↔ 문서 ↔ PG ↔ 온톨로지 (2026-06-20)

> 목적: 실제 코드·각종 문서(md/html)·PostgreSQL 값·온톨로지(TTL) 값이 서로 일치하는지 전수 대조.
> 방법: 파일 기반 3차원(온톨로지 TTL / 문서 정합 / 코드·config)은 read-only subagent 병렬 fan-out,
> PG·교차정합은 `docker exec kosha-pg psql`로 직접 질의. 정정 조치는 commit `8f7eb8e` 참조.

## 총평

**데이터 무결성은 매우 높음.** 수십 개 수치(PG·온톨로지·코드)가 정확히 일치했고, 핵심 버그픽스도 라이브 확인됐다.
🔴 실데이터 격차로 1차 분류했던 **유일 항목(SHE 965↔1,754)은 false positive로 해소**(퇴역 파일 측정 착오) — 실제로는 정합.
빌드·서빙을 깨는 ❌하드 결함 **0건**. 발견된 것은 (1) doc-stale(수정 완료), (2) PG orphan/legacy 위생(백로그)뿐.

> ⚠️ **메타 교훈**: 1차 감사가 SHE에서 "789 갭"을 보고한 것은 **문서가 퇴역 파일(`kosha-instances-she.ttl` 965)을
> 현재처럼 서술**해 감사가 그 파일을 측정했기 때문. 즉 "데이터 갭"의 실체는 "문서 갭"이었다. → **활성 산출물은
> 항상 manifest 프로파일로 교차확인**(파일명·문서 서술만 믿지 말 것). manifest가 SoT.

## 검증 범위 & 방법

| 차원 | 방법 | 대상 |
|---|---|---|
| A. PG 값 ↔ 문서 | `docker exec kosha-pg psql` 직접 카운트 | sr_inferred_relations·penalty_rule_index·GEFC·she_catalog·kosha_guides 등 |
| B. 온톨로지 TTL ↔ 문서 | subagent grep 카운트(주석 제거 후) | 48 TTL: she/guide-fine/skos/VoID/disjoint/restriction/facet |
| C. 문서 ↔ 문서 | subagent grep | 메트릭 anchor 정본 / 폐기용어 / 링크 무결성 |
| D. 코드·config ↔ 문서 | subagent grep+read | 백엔드 버전 / Makefile 타깃 / HITL 스키마↔ORM / 폐기용어 |
| ★ PG ↔ 온톨로지 교차 | 직접(IRI 교집합·facet) | SHE 패턴·guide facet·A-G-18 fix |

## ✅ 정합 확인 (실측값 — 향후 감사 diff 기준선)

### PG (kosha-pg)
- `sr_inferred_relations` **103,295** = R-1 exemptedBy 107 / K-R2 coApplicable 32,858 / K-R4 dependsOn 70,330. `materialization_runs` 4 (runs #1–4).
- `penalty_rule_index` **4,076** (distinct pair 4,076, 100% CriminalSanction).
- `checklist_items` 54,631, `guide_frequency` max **130**. `canonical_checklist_items` **51,263** (boilerplate 71, max degree 130).
- `guide_entity_feature_candidates` GUIDE 14,676 = guide_hazard_weighted_majority **2,115/659** + codex_manual_pilot 2,084/1,038 + llm_enriched_acc 4,226/914 + llm_enriched_agt 2,396/859 + llm_enriched_wc 3,424/938 + taxonomy_alias 431/306.
- `guide_usage_profiles` **1,038**. `kosha_guides` **1,038** (facet populated: accident 996 / agent 986 / context 979).
- `safety_requirements` **626** (= canonical SR). `she_sr_mapping` 2,383 / `she_ci_mapping` 34,833.
- **A-G-18 accident facet = `["COLLAPSE","CRUSHED_OVERTURNED","FALL","STRUCK_BY"]`** — 2dd19b2 항만하역 과태깅 수정이 PG에 라이브 반영 확인.
- `ohs_analysis_records` 71. `mapping_review_verdicts` 0 (HITL MVP 구축 완료·실코퍼스 미실행 = 정합).

### 온톨로지 (TTL)
- **SHE 활성 ABox `kosha-instances-she-full.ttl` 1,675 = PG `v_she_active` 1,675** ✅ (아래 §SHE 참조).
- `kosha-instances-guide-fine.ttl` 957 guide / 9,415 fine triple. `kosha-codes-skos.ttl` 3 scheme / 504 concept / 2,659 triple (broader 418 / relatedMatch 21 / seeAlso 62).
- VoID(`kosha-ontology-metadata.ttl`): triples **1,049,862** / classes 625 / properties 164 / version **2.0.0**.
- `kosha-facet-axis-disjoint.ttl` **9축**(haz:Hazard 제외). `haz:Hazard` 클래스 폐지(라이브 참조 0). facet-taxonomy punning 62 / fine⊑canonical 418.
- `sr:addressesHazard` 0(F20 hard merge). owl:AsymmetricProperty 1 / NaturalLanguageHazardCategory 21.

### 코드·config·문서
- 백엔드 FastAPI `version="3.1.0"`(main.py 2곳) = 커밋 c6f1d09. 프론트 package.json 1.0.0(독립 축).
- Makefile 약 40 타깃의 스크립트 **누락 0**. HITL `schema_mapping_review.sql` ↔ ORM `MappingReviewVerdict` 컬럼 **15/15** 일치. requirements.txt openpyxl 존재.
- 활성 app 코드에 폐기 ontology 용어(PenaltyRoute/penaltyForArticle/SeverityLevel/hasSeverityLevel/ContextFeature/SituationalHazardEvent) **활성 사용 0**.
- 메트릭 anchor(v6: she 0.5915/sr 0.7797/penalty 0.4903/overall 0.3479/fpr 0.0906/fnr 0.1489/she_recall_miss 0.3994/guide_coverage 0.6718)는 **evaluation-baseline.md 단 한 곳**, 타 문서가 현행값으로 모순 단언하는 곳 없음. 핵심 5문서 마크다운 링크 전부 유효. HTML 폐기용어 0.

## 발견 & 조치

| # | 발견 | 분류 | 조치 |
|---|---|---|:--|
| 1 | `kosha-instances-guide-hazard.ttl`(659/2,115)을 활성처럼 참조 | doc-stale | ✅ 정정 `8f7eb8e` — archive 이동·guide-fine(957/9,415) 대체 주석 (6곳) |
| 2 | F21 "미수정"(r14-r30 haz:Hazard 본문) | doc-stale(모순) | ✅ 정정 — WS-GATE-7로 AccidentType repoint 완료, 라이브 0 확인 |
| 3 | GF acc/agt 4,857/1,765 | 수치 stale | ✅ 정정 — 4,226/2,396 (cross-axis 631 재분류, 합 6,622 보존) |
| 4 | owl:Restriction 35 / sh:NodeShape 1,964 | 드리프트/스코프 | ✅ Restriction 37 정정. ⚠️ NodeShape 1,964 스코프 주석(아래 잔여) |
| 5 | kosha_guides accident facet 832 guide | 예상된 변화 미반영 | ✅ 정정 — 2dd19b2 재물질화로 996 |
| 6 | she_recall_miss_rate 0.4168(v4) | stale lineage | ✅ 정정 — 현행 anchor v6 0.3994 포인터 |
| 7 | **SHE 965 ↔ PG 1,754 (789 갭)** | **false positive** | ✅ 규명 — 퇴역 파일 측정 착오. 실제 정합(아래 §SHE). doc 6곳 정정 |
| 8 | `safety_requirements_v2`·`sr_article_mapping_v2`·`sr_ns_mapping_v2`(각 42) | PG orphan | 📋 백로그(refactor-candidates.md) — pipe-A SR-v2 pilot, 서빙 비소비 |
| 9 | `penalty_routes`(656) | PG legacy | 📋 백로그 — penalty_rule_index가 대체, ORM dormant(쿼리 0). build_dashboard_data.py 의존 확인 후 정리 |

## §SHE 965 ↔ 1,754 격차 규명 (false positive)

| 측정 대상 | 값 | 상태 |
|---|---|---|
| `kosha-instances-she.ttl` | 965 | **퇴역 2026-06-12**(manifest 프로파일 공집합) |
| `kosha-instances-she-l2tune.ttl` | 37 | 퇴역(full에 포함) |
| `kosha-instances-she-full.ttl` | **1,675** | **활성**(manifest SRV/CON/MAT/FAC) |
| PG `v_she_active` | **1,675** | — |
| **온톨로지 활성 ↔ PG 활성** | **1,675 == 1,675** | ✅ 정합 |

- 커밋 **68cc76b**(2026-06-12) "CAT-4 — SSOT=PG 확정, SHE ABox 전량(1675) 단일화"에서 이미 정합. `export_she_catalog_to_abox.py --scope active`가 PG 활성 전량 emit, `full ⊇ 965`(diff 0).
- IRI 교집합 검증: 퇴역 965 ⊂ PG 1,754 완전 부분집합(TTL-only 0). pending_review 79는 HITL 원칙대로 ontology 미발행(1,675 + 79 = 1,754).
- 1차 감사가 965를 잰 이유 = current-session.md L48 등이 2026-06-12 CAT-4를 누락해 965를 현재처럼 서술 → 정정 완료.

## 잔여 / 후속

- ⚠️ **sh:NodeShape 1,964 스코프**: 전체 48 TTL raw grep 4,407(kb-candidates 2,192 + vetted-disjoint-shapes 2,161 후보 KB 포함). "1,964"는 axiom-100% 어셈블리 스코프로 추정되나 정확 산정식 미확인 — `verify_axiom_100pct.py` 측정 정의 대조 권장.
- 📋 **PG 위생**(refactor-candidates.md): `_v2` pilot 3종·`penalty_routes` legacy 정리(파괴적 → 사용자 확인 후).
- 🔧 **운영**: `kosha-fuseki` 컨테이너 unhealthy(최신 ABox 반영 위해 Openllet reload 필요할 수 있음) — 데이터 일관성과 별개의 운영 이슈.

## 재현 방법

```bash
# PG 직접 (kosha-pg 컨테이너)
docker exec kosha-pg psql -U kosha -d kosha -c "SELECT rule_id,rel_type,count(*) FROM sr_inferred_relations GROUP BY 1,2;"
docker exec kosha-pg psql -U kosha -d kosha -c "SELECT count(*) FROM v_she_active;"   # 1675
# 온톨로지 활성 SHE = manifest 프로파일로 확인 (파일명 아님)
grep -n 'abox-she' ontology-team/06-reasoning/ontology/assembly/manifest_source.py
grep -c 'a she:SituationalHazardPattern' ontology-team/06-reasoning/ontology/kosha-instances-she-full.ttl  # 1675
```

> ⚠️ `mcp__postgres__query` MCP는 kosha DB가 **아니다**(다른 서버) — PG 검증은 반드시 `docker exec kosha-pg`.
