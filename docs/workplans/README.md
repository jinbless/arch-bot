# 활성 워크플랜

현재 진행 중인 단일 큰 작업의 상세 운영 문서를 보관한다.

다주제 후보 큐는 [../backlog/](../backlog/)로 분리한다.

## 활성 워크플랜

| 워크플랜 | 상태 | 비고 |
|---|---|---|
| **[llm-accelerated-ontology-engineering.md](llm-accelerated-ontology-engineering.md)** ⭐ | **활성 (메인, 2026-05-17~)** | Phase 0~F.3 + Tier 1-3.A + Phase G + Tier 4 + Hazard-Direct Pivot 완주 통합. 모든 정본 진행 기록 |
| [hazard-direct-architecture-pivot.md](hazard-direct-architecture-pivot.md) | ✅ 완료 (2026-05-19) | Vision LLM `hazards[]` 직접 출력 → catalog 매핑 → ontology Guide 추천. 8 photo 25/25 (100%) 매핑 PASS |
| [she-matcher-broadness-refactor.md](she-matcher-broadness-refactor.md) | ⏳ 후행 sprint plan | SHE matcher broadness-aware refactor (hazard-direct 후행 별도 sprint) |
| [llm-domain-guard.md](llm-domain-guard.md) | 보존 (선행) | `ci_cross_guide_broad_only_guard1`. 메인 워크플랜이 흡수·확장 |
| [part3-synthetic-en-cleanup.md](part3-synthetic-en-cleanup.md) | ✅ 완료 (2026-05-17) | Phase 3D synthetic transform + C cleanup으로 마무리 |

**`llm-accelerated-ontology-engineering`** (현재 메인): Phase 0/B/A/C + Phase E-prep + Layer 4 ontology learning 정밀 설계 + Phase G PG materialization + Tier 4 SWRL + Hazard-Direct Pivot. NeOn + OntoClean + LLM 가속. BFO + LKIF-Core 2-layer. 학계 9 paper reference 기반.

`llm-domain-guard`는 `A-G-18-2026` 항만 컨텍스트 가드를 재사용 가능한 Guide domain/profile guard로 일반화한 선행 워크스트림. baseline `ci_cross_guide_broad_only_guard1`까지 진행됨. 현재 메인 워크플랜이 이를 흡수·확장.

## 평가 기준선 정본

baseline 메트릭 변경 전 반드시 [../status/evaluation-baseline.md](../status/evaluation-baseline.md)에서 현재 accepted 메트릭을 확인한다.

## 승격 정책

[../backlog/](../backlog/) 항목이 다음 조건을 만족하면 여기로 승격한다:

- 단일 일관된 워크스트림으로 정리됨
- 적용 단계와 검증 baseline이 명확
- 작업 시작 시점이 정해짐
