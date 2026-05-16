# Shared

3팀이 공유하는 reference data와 단계 간 인터페이스 contract를 보관한다.

## 내용

| 파일/디렉토리 | 용도 |
|---|---|
| [reference/hazard-taxonomy-unified.json](reference/hazard-taxonomy-unified.json) | 위험 분류 통합 reference (데이터팀 1~4단계 + 서빙팀 8단계 모두 참조) |

## 정책

- 한 팀이 일방적으로 수정하지 않는다. 변경 시 3팀의 합의 필요.
- 향후 repo 분리 시점에 이 디렉토리는 **3 repo 모두에 mirror** 또는 별도 공통 repo (`kosha-shared`)로 분리될 수 있음.
- 단계 간 PG schema contract는 [docs/architecture/inter-stage-interfaces.md](../docs/architecture/inter-stage-interfaces.md)에 명세.
