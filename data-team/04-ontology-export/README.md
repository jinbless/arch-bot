# Stage 4 — Ontology Export (Data Team)

PG에 적재된 NS/SR/CI를 다시 OWL/TTL로 export하는 단계.

## 현재 상태

**현재 이 디렉토리는 빈 placeholder입니다.** 실제 export 스크립트는 Phase B에서 다음에서 이동 예정:

| 현재 위치 | 향후 위치 |
|---|---|
| `ontology-team/06-reasoning/ontology/scripts/export_owl.py` | `data-team/04-ontology-export/export-scripts/` |
| `ontology-team/06-reasoning/ontology/scripts/export_serving_snapshot.py` | 동일 |
| `ontology-team/06-reasoning/ontology/scripts/sync_fuseki.sh` | 동일 |

## 책임

- PG의 `safety_requirements`, `checklist_items`, `ci_sr_mapping` 등 → TBox/ABox TTL
- Fuseki SPARQL endpoint에 동기화
- 출력: `ontology-team/06-reasoning/ontology/kosha-instances.ttl`, `serving-snapshot-*.ttl`

## 다음 팀과의 인터페이스

- **→ 온톨로지팀 (6단계)**: 생성된 TBox/ABox TTL을 입력으로 사용

자세한 단계별 위치 매핑: [docs/architecture/stage-mapping.md](../../docs/architecture/stage-mapping.md)
