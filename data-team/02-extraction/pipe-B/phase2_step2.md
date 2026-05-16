# Phase 2 — Step 2: CI 스키마 + 배치 준비

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product 기준에서는 CI를 최종 조치 본체로만 보지 않고 즉시 조치/보조 단서/검색 색인으로 사용한다.

> 완료: 2026-04-12

## 목표

CI 출력 스키마를 확정하고, 분야별 배치 입력 JSON을 생성한다.

## 실행

```bash
cd koshaontology/pipe-B
# 특정 도메인
python3 scripts/step3_prepare_ci_batch.py --domain D --batch-size 5
# 전체
python3 scripts/step3_prepare_ci_batch.py
```

## 산출물

- `schemas/ci-file.schema.json` — 5종 엔티티 출력 스키마
- `data/ci-batches/pipeb-batch-{domain}-{NNN}-input.json` — 배치 입력

## 스키마 요약

`ci-file.schema.json`은 6개 최상위 키를 정의:
- `metadata`: guideCode, shortCode, domain, extractedAt, extractedBy
- `checklistItems[]`: CI (identifier, text, bindingForce, sourceSection, basedOn)
- `domainTerms[]`: DT (identifier, term, definition)
- `workProcesses[]`: WP (identifier, processOrder, processName)
- `equipmentSpecs[]`: ES (identifier, equipmentName, specifications)
- `documentRequirements[]`: DR (identifier, documentType, title)

모든 레벨에 `additionalProperties: false` 적용.

## 배치 로직

- 가이드 크기별 분류: 소형(~15p)/중형(15~40p)/대형(40p+)
- 소형: batch-size개/배치, 중형: 60%/배치, 대형: 1개/배치
- D 분야 테스트: 73개 → 18배치 (소형 67, 중형 3, 대형 3)
- candidateSR: 파싱된 가이드만 인용 조문→SR 후보 계산 가능

## 주의사항

- P1-Step 2 (PDF 파싱) 완료 후 배치를 재생성해야 candidateSR이 채워짐
- 현재는 파싱된 7개 가이드만 candidateSR 보유 (legacy 호환 3개 + 기존 파싱 4개)
