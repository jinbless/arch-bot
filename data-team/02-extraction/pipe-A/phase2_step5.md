# Phase 2 Step 5: SR 검증

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 SR 위험 연결은 `risk:RiskFeature`, `sr:addressesFeature`, 구체 위험 관계를 함께 물질화하는 구조로 확장되었다.

> 최종 업데이트: 2026-04-12
> 산출물: `data/validation/sr-validation-report.json`
> 스크립트: `scripts/step6_validate_sr.py`
> 선행: Step 4 (sr-batch-*.json 48파일, 626 SR)

---

## 1. 목적

생성된 626개 SR에 대해 14개 규칙(구조적 10 + 의미적 4)으로 검증하고, 검증 리포트를 생성한다. Phase 1의 `step4_validate_ns.py`와 동일한 패턴.

## 2. 전제조건

- Step 4 완료: `sr-batch-*.json` 48파일 (626 SR)
- Phase 1 출력: `ns-batch-*.json` (mandatedBy FK 검증용)
- Phase 1 출력: `article-texts.json` (referencesArticle FK 검증용)
- Phase 1 출력: `penalty-routes.json` (hasSanction SSOT 검증용)

## 3. 검증 규칙 14개

### 구조적 검증 (Hard Error, 0건이어야 PASS)

| 규칙 | 검증 내용 |
|------|----------|
| R1_SCHEMA | JSON Schema 필수 필드 존재 확인 |
| R2_DUPLICATE_ID | identifier 중복 없음 |
| R3_ID_FORMAT | identifier 정규식 `^SR-[A-Z_]+-[0-9]+$` |
| R4_FK_NS | mandatedBy의 모든 NS ID가 norm_statements에 존재 |
| R5_FK_ARTICLE | referencesArticle의 모든 조문이 articles에 존재 |
| R6_SANCTION_MISMATCH | hasSanction이 penalty-routes.json과 일치 |
| R7_MODALITY_FILTER | mandatedBy에 OBLIGATION/PROHIBITION NS만 포함 |
| R8_EMPTY_TEXT | text 비어있지 않음 |
| R9_INVALID_TYPE | requirementType enum 유효성 |
| R10_INVALID_HAZARD | addressesHazard가 12개 표준 키워드 내 |

### 의미적 검증 (Warning, 수동 확인)

| 규칙 | 검증 내용 |
|------|----------|
| R11_QUANT_MISSING | QUANTITATIVE 조건 수치가 structuralRequirements에 포함 |
| R12_SPLIT_ARTICLE | 동일 조문이 여러 SR에 분산된 경우 경고 |
| R13_TITLE_TEXT_MISMATCH | title 키워드가 text에 포함 (30% 미만 시 경고) |
| R14_MOD_TARGET_MISSING | hasModificationLink 대상 SR 존재 |

## 4. 최종 검증 결과

```
============================================================
SR 검증 결과 (2026-04-12 재생성 후)
============================================================
  총 SR: 626개
  ERROR: 0건
  WARNING: 14건
    R11_QUANT_MISSING: 1건
      SR-RIGGING-001: 안전계수 값이 법 조문 각호(별표)에 있어 NS 텍스트 미포함
    R13_TITLE_TEXT_MISMATCH: 13건
      한국어 조사 변화에 의한 false positive (예: "국소배기장치의" vs "국소배기장치를")

✅ PASS — 구조적 에러 0건 (경고 14건)
```

---

## 5. 재현 방법

```bash
cd koshaontology/pipe-A

python3 scripts/step6_validate_sr.py

# 결과 확인
cat data/validation/sr-validation-report.json | python3 -m json.tool | head -10
```

---

*다음 스텝: phase2_step6.md (DB 스키마 확장)*
