# Phase 2 — Step 1: SR 조회 인덱스 생성

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 전체 Guide JSON 추출 완료 후 SR/Guide/CI 연결 품질과 candidateSR 조문 키 정합성을 다시 검증한다.

> 완료: 2026-04-12

## 목표

Pipe-A PostgreSQL DB에서 3종 역인덱스를 자동 생성하여 CI→SR basedOn 링킹의 사전 후보 계산에 사용한다.

## 실행

```bash
cd data-team/02-extraction/pipe-B
python3 scripts/step2_build_sr_index.py
```

## 산출물

- `data/sr-article-index.json` — 626 조문코드 → SR 매핑
- `data/sr-category-index.json` — 12 위험유형 카테고리 → SR 매핑
- `data/sr-keyword-index.json` — 47 키워드 → SR 매핑 + 626 SR 전체 목록

## 검증 결과

- DB 연결: kosha@localhost 성공
- SR 총 수: 626개
- SR-Article 매핑: 626개
- 위험유형 카테고리: 12개
- 키워드 패턴: 47개
