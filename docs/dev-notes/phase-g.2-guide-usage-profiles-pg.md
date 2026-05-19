# Phase G Sprint G.2 — guide_usage_profiles PG materialization + GuideUsageProfile ontology (Runbook)

> Phase G의 두 번째 sprint. **Ontology 가장 큰 갭 보강** (`guide:GuideUsageProfile` class 전체 신규) + 기존 PG `guide_usage_profiles` (1,038 rows, 이전 sprint에서 적재) + `guide_domain_profile.py` runtime PG primary.
> **Status**: G.2 Day 0-5 완료 (2026-05-18). 20/20 sample equality, Gate 3 PASS (false_negative_rate -0.0189 개선).

## TL;DR

```bash
make phase-g2-verify                  # G.1 + G.2 sample equality (20/20 PASS)
make f1-regression                    # Gate 3
```

## Ontology TBox 보강 (가장 큰 갭)

`kosha-ontology-v3-guide-profile-patch.ttl`:
- **`guide:GuideUsageProfile` class** (전체 신규)
- 14 properties: profileOfGuide / hasProfile (inverse) / profileLevel / domainFamily / procedureRole / intendedWorkplaces / intendedTasks / observableRequiredCues / negativeBoundaries / photoMatchability / topProcedurePolicy / followupPolicy / usageSummary / reviewStatus / baselineId
- Cardinality restrictions (profileOfGuide / profileLevel / procedureRole / photoMatchability — each 정확히 1개)
- 결과: +117 triples, SHACL conforms 유지

핵심 효과: `serving-validation-shapes-v3.ttl:20`의 `sh:targetClass guide:GuideUsageProfile` SHACL shape이 이제 정합한 OWL class target을 가짐. 이전엔 SHACL shape만 있고 class 정의가 없는 모순 상태였음.

## PG materialization

- 기존 PG `guide_usage_profiles` (1,038 rows, ORM `PgGuideUsageProfile` 이전 sprint에서 적재)
- 신규 import script 불필요 (기존 `import_guide_usage_profiles_to_pg.py` 활용 가능)

## Backend 전환

`app/services/guide_domain_profile.py`:
- `_load_profiles_from_pg()` 신규 (PG primary)
- `_load_manual_profiles()` 수정: PG 시도 → PG empty 시 JSON fallback
- `get_guide_domain_profile()` 시그니처 변경 없음 (drop-in)

## Verification

| 항목 | 결과 |
|---|---|
| Ontology consistency (rdflib + SHACL) | ✅ +117 triples, conforms True |
| Sample equality (PG vs JSON, 10 samples) | ✅ 10/10 PASS |
| Gate 3 vs baseline_v3 | ✅ PASS (she_accuracy -0.0013, **false_negative_rate -0.0189 개선**, 다른 metric 0) |
| 누적 (G.1 + G.2) | ✅ 20/20 sample equality |

## Related

- [phase-g.1-domain-incompatibilities-pg.md](phase-g.1-domain-incompatibilities-pg.md) — Sprint G.1
- [workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)
