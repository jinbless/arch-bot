# Phase 1 — Step 1: v2 스키마 설계 + Legacy 호환성

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product 기준에서는 `Guide/WorkProcess`를 표준 개선 절차 중심으로, `ChecklistItem`을 즉시 조치/보조 단서/검색 색인으로 사용한다.

> 완료: 2026-04-12

## 목표

guide-text JSON v2 스키마를 확정하고, legacy 파싱 결과 47개의 v2 호환성을 확인한다.

## 산출물

- `schemas/guide-text-v2.schema.json` — v2 스키마 (JSON Schema Draft 2020-12)
- `data/legacy-compatibility-report.json` — legacy 호환성 보고서

## v2 스키마 설계 요약

**최상위**: `metadata` (필수) + `sections[]` (필수, 1개 이상)

**metadata 필수 필드**:
- guideCode, shortCode, title, totalPages, pdfPath, parsedAt, parsedBy, tocSections[]

**section 필수 필드**:
- sectionNumber, sectionTitle, text, tables[], images[]
- 선택: pages (start/end 배열), subsections[] (재귀 구조)

**tables[] 항목**: tableNumber, caption, content (필수), page (선택)
**images[] 항목**: imageNumber, caption (필수), description, page (선택)

**전체 적용**: `additionalProperties: false`, `minLength: 1` (빈 문자열 금지)

## Legacy 호환성 결과

- 총 legacy 파일: **47개** (guide-pdf-index.json 제외)
- v2 호환: **3개** (AG10, BE7, D28)
- v2 비호환: **44개**

**비호환 주요 원인**:
1. images 필드명 차이: `imageId`/`extractedData`/`pageNumber` → v2의 `imageNumber`/`caption`
2. tables 필드명 차이: `headers`/`rows`/`tableIndex` → v2의 `tableNumber`/`content`/`caption`
3. subsections에 tables/images 필수 필드 누락
4. 빈 sectionNumber ("" → minLength: 1 위반)

## P1-Step 2 영향

- v2 호환 3개는 그대로 재사용 (LLM 파싱 불필요)
- 비호환 44개 + 미파싱 991개 = **1,035개를 LLM으로 신규 파싱** 필요
- 계획 추정치 ~960개 → 실제 1,035개 (legacy 호환율이 낮아 증가)
