# Stage 7 — Materialization (Serving Team)

보정된 온톨로지 내용을 PG로 재물질화하는 단계.

## 현재 상태

이 디렉토리는 **활성 PG-sync + schema 스크립트**를 보유한다 (Track A ② reasoning vertical slice 반영, 2026-06-14).

`pg-sync-scripts/`:

| 스크립트 | 역할 |
|---|---|
| `import_sr_inferred_relations_to_pg.py` | 3종 inferred TTL → `kosha-pg.sr_inferred_relations` 적재 (R-1 / K-R2 / K-R4) |
| `schema_sr_inferred_relations.sql` | `sr_inferred_relations` DDL |
| `schema_materialization_runs.sql` | `materialization_runs` (PROV run-tracking) DDL |
| (기존 Phase G importer / validation 스크립트) | Guide/CI 후보 적재 + 적재 후 검증 |

### Materialized 출력

| PG 테이블 | 내용 |
|---|---|
| `sr_inferred_relations` | reasoner inferred SR 관계 **103,295행** (R-1 `exemptedBy` 107 + K-R2 `coApplicable` 32,858 + K-R4 `dependsOn` 70,330) |
| `materialization_runs` | PROV run-tracking (`run_id`, `rule_set`, `ontology_commit`=git rev, `source_ttl_sha256`=content-hash, `triple_count`, `status`) |
| `guide_usage_profiles` 등 | 기존 Guide 보강 후보 테이블 |

> R-3 HighSeverityPenalty(3,579)는 `sr_inferred_relations`에 저장하지 않고 `penalty_rule_index.severity_score >= 5` SQL로 재현한다. R-2 strict coApplicable은 SR↔Article 1:1이라 0행이다.

### Stage-7 재물질화 파이프라인 (entrypoint)

```bash
# 1) reasoner inferred TTL emit (ontology-team)
make reasoning-emit            # R-1 strict (kosha-inferred-relations.ttl)
make reasoning-emit-chapter    # K-R2 same-Chapter (kosha-coapplicable-chapter.ttl)
make reasoning-emit-hazard     # K-R4 same-Hazard (kosha-dependson-hazard.ttl)

# 2) 일회성 DDL — materialization_runs + sr_inferred_relations
make phase-g5-schema

# 3) PG 적재 (R-1 → K-R2 → K-R4)
make phase-g5-import  ARGS=--apply   # R-1 exemptedBy
make phase-g5b-import ARGS=--apply   # K-R2 coApplicable
make phase-g5c-import ARGS=--apply   # K-R4 dependsOn

# 4) gate
make phase-g5-verify                 # + phase-g5b-verify / phase-g5c-verify
```

## 책임

- 온톨로지팀(6단계)이 보정한 ABox TTL + reasoner inferred TTL을 받아 PG materialized tables로 적재
- Validation: 적재 후 일관성 검증, 옛 행 정리, PROV run-tracking(`materialization_runs`) 기록
- 출력: `sr_inferred_relations`, `materialization_runs`, `guide_usage_profiles`, `guide_sr_link_candidates`, `ci_sr_mapping` 등 PG 테이블 갱신

## 다른 팀과의 인터페이스

- **← 온톨로지팀 (6단계)**: 보정된 ABox TTL + validation report 입력
- **→ 서빙팀 (8단계)**: 갱신된 PG 테이블을 OHS backend가 직접 조회

자세한 단계별 위치 매핑: [docs/architecture/stage-mapping.md](../../docs/architecture/stage-mapping.md)
