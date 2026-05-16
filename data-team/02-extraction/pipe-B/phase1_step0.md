# Phase 1 — Step 0: 가이드 인벤토리 생성

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 전체 Guide JSON 추출 완료 후 Guide 레이어와 추천 로직을 현재 product 기준으로 리빌딩한다.

> 완료: 2026-04-12

## 목표

KOSHA 가이드 PDF 전수 목록을 생성하여 shortCode 기반 식별 체계를 확립한다.

## 입력

- `kosha-guides/{A,B,C,D,E}/` — 1,038개 PDF 파일

## 실행

```bash
cd koshaontology/pipe-B
python3 scripts/step0_build_inventory.py
```

## 산출물

- `data/guide-inventory.json` — 1,038개 가이드 메타데이터 (306 KB)
- `data/guide-pdf-index.json` — shortCode → PDF 경로 매핑 (97 KB)
- `data/domain-batch-plan.json` — 분야별 배치 처리 순서

## 검증 결과

- 총 가이드: **1,038개** (계획 추정치 1,041 → 실제 1,038)
- 도메인별: A=124 / B=232 / C=238 / D=73 / E=371
- shortCode 중복: **0건**
- PDF 경로 실존: 전수 확인
- 스키마 검증: `guide-inventory.schema.json` PASS

## 파일명 파싱 특이사항

47개 PDF가 표준 파일명 형식(공백 구분)을 따르지 않았다. `guide_code.py`에 3가지 추가 패턴을 구현하여 전수 파싱에 성공:

1. **밑줄 구분** (40건): `E-182-2021_정전기에 의한...` → code `E-182-2021`, title `정전기에 의한...`
2. **가이드코드 내 공백** (1건): `D-27- 2021 수소...` → 공백 제거 후 `D-27-2021`
3. **숫자ID 접두사** (3건): `347896_P-79-2011.pdf` → 접두사 제거 후 `P-79-2011`
4. **코드 내 공백 + 숫자접두사** (3건): `352869_C - 73 - 2012.pdf` → `C-73-2012`

제목이 없는 3개 파일(숫자ID 접두사 파일)은 가이드코드를 제목으로 사용.

## 스크립트/유틸리티

- `scripts/step0_build_inventory.py` — 메인 스크립트
- `scripts/lib/guide_code.py` — 가이드코드 파싱 유틸리티 (shortCode 생성 포함)
- `schemas/guide-inventory.schema.json` — 출력 JSON Schema
- Pipe-A `schema_validator.py` — 직접 import (복사 금지)

## 주의사항

- 계획서의 1,041개는 추정치. 실제 PDF 수는 **1,038개**.
- C 분야가 계획 241 → 실제 238 (3개 차이).
- shortCode는 가이드코드에서 하이픈과 연도를 제거: `A-G-4-2025` → `AG4`
