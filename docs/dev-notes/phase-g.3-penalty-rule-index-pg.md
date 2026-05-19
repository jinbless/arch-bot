# Phase G Sprint G.3 — penalty_rule_index PG materialization + penalty relations ontology (Runbook)

> Phase G의 세 번째 sprint. Ontology `penalty:appliesTo/penaltyType/maxFine/maxPrisonYears` 보강 + `kosha-instances.ttl`에서 추출한 SR→PenaltyRule mapping을 신규 PG `penalty_rule_index` table에 materialize + `hazard_rule_engine._load_penalty_index()` PG primary.
> **Status**: G.3 완료 (2026-05-18). **penalty_accuracy +27.16%p, overall_accuracy +18.81%p**. 4,076 penalty rules PG 적재.

## TL;DR — 핵심 결과

| metric | baseline_v3 | G.3 PG | delta |
|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | -0.0013 (noise) |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 |
| **penalty_accuracy** | **0.1835** | **0.4551** | **+0.2716 (+27.16%p) ⭐** |
| **overall_accuracy** | **0.1377** | **0.3258** | **+0.1881 (+18.81%p) ⭐** |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 |
| false_negative_rate | 0.0625 | 0.0436 | -0.0189 (개선) |

→ PG가 TTL 대비 더 완전한 penalty 매핑 제공 → backend가 더 많은 정확한 SR→penalty 경로 발견.

## Ontology TBox 보강

`kosha-ontology-v3-penalty-relations-patch.ttl`:
- `penalty:appliesTo` (PenaltyRule → Article ObjectProperty)
- `penalty:appliesToViaSr` (PenaltyRule → SafetyRequirement)
- `penalty:penaltyType` (PenaltyRule → SanctionType FunctionalProperty)
- `penalty:maxFine` (DatatypeProperty, decimal)
- `penalty:maxPrisonYears` (DatatypeProperty, decimal, CriminalSanction 한정)
- `penalty:fineDescription` (DatatypeProperty, raw 한국어 텍스트)

기존 v2.owl의 PenaltyRule / SanctionType / CriminalSanction / AdministrativeFine classes는 재정의하지 않음.

## PG materialization

**신규 table** `penalty_rule_index`:
- 14 cols (sr_id / penalty_rule_id / article_code / sanction_type / penalty_description / severity_score / subject_role / accident_outcome / violated_norm_id / violated_article_id / delegated_from_article_id / penalty_article_id / basis_text + timestamps)
- 4 indexes (sr_id / penalty_rule_id / article_code / sanction_type)
- UNIQUE(sr_id, penalty_rule_id)
- updated_at trigger

**적재**: `import_penalty_to_pg.py`
- Input: `kosha-instances.ttl` (TTL ABox, 1.06M lines)
- Logic: SR.derivedFromNS → ns_uri → PEN.hasPenaltyRule → pr_uri → extract metadata
- 결과: **4,076 rows** (4,076 unique (sr_id, penalty_rule_id) pairs), 모두 CriminalSanction
- Idempotent (UPSERT on UNIQUE constraint)

## Backend 전환

`app/services/hazard_rule_engine.py:_load_penalty_index`:
- `_load_penalty_index_from_pg()` 신규 (PG primary, ORM PgPenaltyRuleIndex query)
- `_load_penalty_index()` 수정: PG 시도 → empty/error 시 TTL fallback
- 결과: TTL parse 우회 (시작 시간 ~25초 → ~수 ms)
- 데이터 source의 일관성/완전성으로 인해 penalty_accuracy 대폭 개선

## Verification

| 항목 | 결과 |
|---|---|
| Ontology consistency | ✅ patch parse OK |
| PG schema | ✅ 14 cols, 4 indexes |
| Idempotency | ✅ --apply 2회 row count 동일 (4,076) |
| Gate 3 vs baseline_v3 | ✅ **penalty_accuracy +27.16%p, overall +18.81%p** (regression 없음) |
| Sanction type distribution | 100% CriminalSanction (TTL에 AdministrativeFine 미반영, future enrichment 후보) |

## Known Limitations

- AdministrativeFine instances 0개 in TTL (criminal만 추출됨) — 향후 TTL 보강 필요
- penalty_routes (656 rows article-level) + penalty_rule_index (4,076 rows sr-level)는 별도 table — 향후 통합 schema 검토
- TTL fallback 경로 유지 (PG fail-safe), 단 production runs는 모두 PG path

## Related

- [phase-g.1-domain-incompatibilities-pg.md](phase-g.1-domain-incompatibilities-pg.md)
- [phase-g.2-guide-usage-profiles-pg.md](phase-g.2-guide-usage-profiles-pg.md)
- [workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)
