# 백로그

활성 워크플랜으로 승격되기 전, 검토 대기 중인 다주제 리팩토링 후보 큐.

## 활성 워크플랜과의 차이

| 측면 | [../workplans/](../workplans/) | 여기 (backlog/) |
|---|---|---|
| 단위 | 단일 워크스트림의 상세 운영 문서 | 다주제 후보 모음 |
| 상태 | 활성 — 현재 baseline까지 이어지는 일관된 작업 | 백로그 — 아직 코드에 완전히 반영하지 않음 |
| 구조 | Phase / baseline 진행 추적 | 주제별 섹션 누적 |
| 다음 행동 | 단계대로 진행 | 검토 후 별도 워크플랜으로 승격 |

## 현재 항목

- [refactor-candidates.md](refactor-candidates.md) — 신규 리팩토링 후보 모음 (risk: 중심 위험 지식 계층, PenaltyRule 중심 벌칙 모델, SeverityLevel 제거, SHE 브릿지, Guide/WorkProcess 중심 등 다주제)

## 승격 정책

백로그 항목이 다음 조건을 만족하면 `../workplans/`로 승격한다:

- 단일 일관된 워크스트림으로 정리됨
- 적용 단계와 검증 baseline이 명확
- 작업 시작 시점이 정해짐
