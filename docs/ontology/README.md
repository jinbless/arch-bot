# 온톨로지 레이어별 구조 설계

여기에 있는 문서는 `arch-bot`의 온톨로지 5개 레이어를 구조적으로 이해하기 위해 작성된 별도 설계 문서다.
런타임 코드의 일부가 아니다 — 코드와 데이터의 의미를 사람이 이해하기 위한 참고 자료다.

## 읽는 순서

1. [00-integrated-structure.md](00-integrated-structure.md) — 5개 레이어의 통합 구조와 데이터 흐름
2. [01-law-layer.md](01-law-layer.md) — 법령 레이어 (law:Article / law:NormStatement)
3. [02-sr-layer.md](02-sr-layer.md) — SR 레이어 (sr:SafetyRequirement)
4. [03-risk-situation-layer.md](03-risk-situation-layer.md) — 위험상황 레이어 (she:SituationalHazardPattern + risk:RiskFeature)
5. [04-guide-layer.md](04-guide-layer.md) — 가이드 레이어 (guide:KoshaGuide / WorkProcess / ChecklistItem)
6. [05-penalty-layer.md](05-penalty-layer.md) — 벌칙 레이어 (PenaltyRule / PenaltyPath)

## 관련 자료

- 시스템 아키텍처 / PROV-O 출처 레이어 — [../architecture/source-provenance.md](../architecture/source-provenance.md)
- 온톨로지 정의 파일 (TTL/OWL/SWRL) — `../../ontology-team/06-reasoning/ontology/`
- 파이프라인별 작업 가이드 — `../../data-team/02-extraction/pipe-A,B,C/CLAUDE.md`
