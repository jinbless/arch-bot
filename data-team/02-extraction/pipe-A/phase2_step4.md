# Phase 2 Step 4: SR 생성 실행

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 SR 위험 연결은 `risk:RiskFeature`, `sr:addressesFeature`, 구체 위험 관계를 함께 물질화하는 구조로 확장되었다.

> 최종 업데이트: 2026-04-12
> 산출물: `data/safety-requirements/sr-batch-*.json` (48파일, 626 SR)
> 선행: Step 2 (배치 입력 48개), Step 3 (에이전트 가이드)

---

## 1. 목적

48개 SR 배치 입력을 LLM에 병렬 투입하여 626개 SafetyRequirement를 생성한다.

## 2. 전제조건

- Step 2 완료: `sr-batch-*-input.json` 48개 파일
- Step 3 완료: `agents/step5-sr-generation.md` 에이전트 가이드
- Step 1 완료: `sr-file.schema.json` (검증용)

## 3. 실행 전략

### 3.1 단계적 실행 (재생성: 4라운드)

> 카테고리 매칭 버그 수정 후 48배치 전량 재생성 (2026-04-12)

| 라운드 | 배치 수 | 목적 | 결과 |
|--------|---------|------|------|
| 파일럿 | 5 | 프롬프트 품질 검증 | PASS (ERROR 0) |
| 2차 | 15 | 대규모 카테고리 병렬 | PASS (ERROR 0) |
| 3차 | 15 | 중규모 카테고리 병렬 | PASS (ERROR 0) |
| 4차 | 13 | 소규모 + 나머지 전체 | PASS (ERROR 0) |

### 3.2 파일럿 배치 선택 기준

카테고리 다양성 확보:
- 소규모 단일: FALL (20개)
- 중규모 단일: SCAFFOLD (17개)
- 대규모 분할: CHEMICAL-01 (20개)
- 혼합 소규모: PPE-WELFARE (8개)
- 보건: DUST (9개)

### 3.3 병렬 실행 방식

각 배치를 독립 Agent로 병렬 실행. 각 Agent가:
1. 에이전트 가이드 읽기
2. 배치 입력 읽기
3. SR 생성 + 파일 저장
4. JSON Schema 검증

## 4. 최종 결과

```
✅ PASS — 구조적 에러 0건 (경고 14건)
```

- **48/48 배치 완료, 626/626 SR 생성 (100%)**
- ERROR: 0건
- WARNING: 14건
  - R11_QUANT_MISSING: 1건 (SR-RIGGING-001, 안전계수 값이 별표에 있어 NS 텍스트 미포함)
  - R13_TITLE_TEXT_MISMATCH: 13건 (한국어 조사 변화 false positive)

---

## 5. 재현 방법

```bash
cd koshaontology/pipe-A

# 전체 재생성 시 (기존 출력 삭제 필요)
# LLM 에이전트에 다음을 전달:
# 1. agents/step5-sr-generation.md (가이드)
# 2. data/safety-requirements/sr-batch-{CATEGORY}-input.json (입력)
# 3. schemas/sr-file.schema.json (검증용)
# 출력: data/safety-requirements/sr-batch-{CATEGORY}.json

# PATHOGEN 배치는 재생성 시 서브에이전트로 정상 통과

# 검증
python3 scripts/step6_validate_sr.py
```

---

*다음 스텝: phase2_step5.md (SR 검증)*
