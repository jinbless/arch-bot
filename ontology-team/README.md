# Ontology Team

온톨로지팀은 6단계(OWL/SHACL/리즈너)를 담당한다. **향후 public `kosha-ontology-reasoning` repo로 분리되어 오픈소스 공개 예정** (Framework + KOSHA TBox + ABox 모두).

## 단계

| 단계 | 디렉토리 | 역할 |
|---|---|---|
| 6. Reasoning | [06-reasoning/](06-reasoning/) | 공리/OWL/SHACL → 온톨로지 리즈너로 문제 발견·수정 |

## 책임

- 데이터팀이 만든 TBox/ABox를 받아 **공리 적용 + OWL DL 추론** (Openllet 등)
- SHACL shapes로 일관성 검증
- 부정확한 매핑/관계를 찾아내고, 6번 완성 시 5번(LLM enrichment)을 자연스럽게 대체
- 시각화 도구 ([06-reasoning/visualization/](06-reasoning/visualization/)) 운영

## 다른 팀과의 인터페이스

- **← 데이터팀 (4단계)**: [data-team/04-ontology-export/](../data-team/04-ontology-export/)가 export한 TBox/ABox TTL을 입력으로 받음
- **→ 서빙팀 (7단계)**: 보정된 TBox/ABox를 [serving-team/07-materialization/](../serving-team/07-materialization/)이 PG로 재물질화

## 오픈소스 공개 범위

| 항목 | 공개 |
|---|---|
| Framework (Reasoner runner, SHACL shapes, OWL/SWRL 패턴) | ✓ |
| KOSHA TBox (클래스/속성 정의) | ✓ |
| KOSHA ABox (실제 SR/CI 인스턴스) | ✓ |

다른 산업안전 도메인 ontology 엔지니어가 reference로 활용 가능. 자세한 공개 절차는 [docs/architecture/open-source-readiness.md](../docs/architecture/open-source-readiness.md).

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
