# Phase G Sprint G.1 — guide_domain_incompatibilities PG materialization (Operator Runbook)

> Phase G의 첫 sprint. **Ontology TBox `core:Incompatibility` 보강** + JSON 2,240 entries → PG `guide_domain_incompatibilities` (2,016 unique rows after dedup) + `shadow_reasoner.py` runtime이 PG primary (JSON fallback).
> **Status**: G.1 Day 1-5 완료 (2026-05-18 저녁). vetted 8 (T2.D 결과), candidate 2,008.

## TL;DR — Quick Start

```bash
# 1회성 schema 적용
make phase-g1-schema

# JSON → PG 적재
make phase-g1-import                          # dry-run
make phase-g1-import ARGS='--apply'           # 실제 UPSERT
make phase-g1-import ARGS='--apply --filter-level vetted'   # vetted만

# 검증
make phase-g1-verify                          # 10 sample query equality (PG vs JSON)
make f1-regression                            # Gate 3
```

## Architecture

```
[Ontology TBox source of truth]
    kosha-ontology-v3-incompat-patch.ttl
    ├── core:Incompatibility (class)
    ├── core:incompatibleDomainA / domainB (object properties)
    └── core:axiomConfidence / axiomLevel / axiomSource / axiomReason / axiomPromotedAt
                  │
                  ▼ surface representation
[JSON ABox]
    guide_domain_incompatibilities.json (2,240 entries)
                  │
                  ▼ idempotent UPSERT
[PG materialized table]
    guide_domain_incompatibilities (2,016 unique by (a, b, source))
       ├── vetted: 8 (T2.D 8/8 PASS)
       ├── candidate: 2,008
       └── source distribution: 1,977 unknown + 31 self_refine + 8 f32_axiom_miner
                  │
                  ▼ runtime SELECT (lazy module cache)
[Backend runtime]
    shadow_reasoner.shadow_validate(industry, candidate_codes)
    └── analysis_log.reasoner_rejects 필드 기록 (실제 reject X, shadow only)
```

## File Layout

| Path | Purpose |
|---|---|
| `ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl` | Ontology TBox 보강 (Day 0) |
| `serving-team/07-materialization/pg-sync-scripts/schema_guide_domain_incompatibilities.sql` | PG DDL (12 cols + 5 indexes + trigger) |
| `serving-team/07-materialization/pg-sync-scripts/import_domain_incompatibilities_to_pg.py` | Import script (UPSERT + dedup + audit) |
| `serving-team/07-materialization/validation-scripts/sample_query_equality.py` | PG vs JSON 동등성 검증 (10 samples) |
| `serving-team/08-app/backend/scripts/bench_shadow_reasoner.py` | Latency bench (p50/p95/p99) |
| `serving-team/08-app/backend/app/db/models.py` | `PgGuideDomainIncompatibility` ORM |
| `serving-team/08-app/backend/app/services/shadow_reasoner.py` | PG primary + JSON fallback (Day 3) |

## Day 0-5 Sprint Summary (2026-05-18 저녁)

| Day | 작업 | 결과 |
|---|---|---|
| Day 0 (오전) | Ontology TBox 보강 (incompat patch TTL) | +51 triples, core:Incompatibility class + 7 properties, SHACL conforms |
| Day 0 (오후) | local_consistency_check.py PASS | rdflib parse OK, SHACL conforms True |
| Day 1 | PG schema DDL + ORM model | 12 cols, 5 indexes, ORM imports OK |
| Day 2 | Import script (484-line template 축약) | dry-run 2,240 entries, dedup 224 → 2,016 unique, --apply PASS, idempotent |
| Day 3 | shadow_reasoner PG primary + JSON fallback | 2014 axiom pairs loaded from PG, B-M-32-2026×METAL level=vetted (T2.D 반영) |
| Day 4 | Gate 3 + sample equality + latency bench | Gate 3 PASS (noise만), 10/10 sample match, PG p50 0.4μs (target 10ms) |
| Day 5 | Makefile + runbook + commit | phase-g1-* targets + 본 문서 |

## Verification

### 검증 1: Ontology consistency
```bash
PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/local_consistency_check.py \
  --skip-instances --skip-sparql
# 기대: parse OK, SHACL conforms True
```

### 검증 2: PG schema + 적재
```bash
PYTHONIOENCODING=utf-8 DATABASE_URL=postgresql://kosha:1229@localhost:5432/kosha \
  python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    r = c.execute(text('SELECT level, COUNT(*) FROM guide_domain_incompatibilities GROUP BY level'))
    print(dict(r.fetchall()))
"
# 기대: {'vetted': 8, 'candidate': 2008}
```

### 검증 3: Sample query equality (PG vs JSON)
```bash
make phase-g1-verify
# 기대: 10/10 PASS
```

### 검증 4: Gate 3 regression
```bash
make f1-regression
# 기대: 모든 metric delta noise 수준 (she_accuracy ±0.0013), PASS
```

### 검증 5: Latency bench
```bash
cd serving-team/08-app/backend
PYTHONIOENCODING=utf-8 DATABASE_URL=... python scripts/bench_shadow_reasoner.py
# 기대: PG p50 < 10ms (실측 0.4μs after cache warm)
```

## Rollback

### shadow_reasoner JSON 강제 (PG 무시)
```python
# app/services/shadow_reasoner.py에서 임시 monkey-patch
shadow_reasoner._load_axioms_from_pg = lambda: None
shadow_reasoner.reset_cache()
```

### PG table 비우기 (재적재 위해)
```sql
TRUNCATE guide_domain_incompatibilities RESTART IDENTITY;
```

### PG table 삭제 (Phase G 자체 rollback)
```sql
DROP TABLE guide_domain_incompatibilities CASCADE;
```

### Ontology patch 제거
```bash
rm ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl
# Fuseki sources 미반영 상태 (G.3 완료 시 통합 rebuild 예정)
```

## Acceptance Criteria

| 항목 | 통과 기준 | 결과 (2026-05-18) |
|---|---|---|
| Ontology parse + SHACL | local_consistency_check PASS | ✅ PASS |
| PG schema | 12 cols, 5 indexes | ✅ 12 cols, 5 indexes |
| Idempotency | --apply 2회 row count 동일 | ✅ 2,016 → 2,016 |
| Sample equality | 10/10 PASS | ✅ 10/10 |
| Gate 3 | 모든 metric noise | ✅ delta -0.0013 ~ +0.0014 |
| Latency | PG p50 < 10ms | ✅ 0.4μs (25,000x margin) |
| T2.D vetted 반영 | 8 axioms vetted | ✅ 8 (BUTCHER×CONSTRUCTION 등) |

## Known Limitations

| 항목 | 영향 | 대응 |
|---|---|---|
| 224 duplicates (domain_a, domain_b, source) | source field 누락된 entries가 unknown으로 통합 | dedup 시 vetted/높은 confidence 우선 |
| Fuseki에 incompat patch 미반영 | SPARQL `?x a core:Incompatibility` 결과 0 | G.3 완료 시 KoshaFusekiServer.java sources + rebuild 일괄 |
| JSON file 백업 유지 | disk 50KB | Phase G 완료 시 deprecated marker (별도) |
| Cache invalidation | backend restart 필요 (catalog/KB 갱신 시) | Phase G 후 PG NOTIFY/LISTEN 검토 (Tier 4) |

## Related Documents

- [docs/dev-notes/F.3-axiom-discovery.md](F.3-axiom-discovery.md) — Tier 2 F.3 closing (선행)
- [docs/status/t2d-per-candidate-promotion-2026-05-18.md](../status/t2d-per-candidate-promotion-2026-05-18.md) — 8 vetted 출처
- [docs/workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) — Phase G 전체 roadmap
- [docs/architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Layer 4 Module 4.4
- [docs/architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md) — 7단계 PG 재물질화

## Future Sprints (Phase G 잔여)

- **G.2**: `guide:GuideUsageProfile` 보강 + guide_usage_profiles JSON → PG (1주, ontology 가장 큰 갭)
- **G.3**: penalty relations 보강 + penalty_rules/penalty_conditions unified (1주)
- **G.4**: she_patterns 확장 + Openllet reasoner-derived facts (1주, 선행 Openllet inferred=0 조사)
