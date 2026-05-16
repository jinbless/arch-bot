# Stage 7 — Materialization (Serving Team)

보정된 온톨로지 내용을 PG로 재물질화하는 단계.

## 현재 상태

**현재 이 디렉토리는 빈 placeholder입니다.** 실제 PG sync 스크립트는 Phase B에서 다음에서 이동 예정:

| 현재 위치 | 향후 위치 |
|---|---|
| `serving-team/08-app/backend/scripts/import_guide_usage_profiles_to_pg.py` | `serving-team/07-materialization/pg-sync-scripts/` |
| `serving-team/08-app/backend/scripts/import_ci_sr_link_candidates.py` | 동일 |
| `serving-team/08-app/backend/scripts/reindex_articles.py` | 동일 |
| `ontology-team/06-reasoning/ontology/scripts/validate_serving_snapshot.py` | `serving-team/07-materialization/validation-scripts/` |
| `ontology-team/06-reasoning/ontology/scripts/audit_serving_workprocess_alignment.py` | 동일 |

## 책임

- 온톨로지팀(6단계)이 보정한 ABox TTL을 받아 PG materialized tables로 적재
- Validation: 적재 후 일관성 검증, 옛 행 정리
- 출력: `guide_usage_profiles`, `guide_sr_link_candidates`, `ci_sr_mapping` 등 PG 테이블 갱신

## 다른 팀과의 인터페이스

- **← 온톨로지팀 (6단계)**: 보정된 ABox TTL + validation report 입력
- **→ 서빙팀 (8단계)**: 갱신된 PG 테이블을 OHS backend가 직접 조회

자세한 단계별 위치 매핑: [docs/architecture/stage-mapping.md](../../docs/architecture/stage-mapping.md)
