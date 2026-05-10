# Pipe-C 교차검증 계획

> 최종 갱신: 2026-04-25
> 상태: ✅ 코드 완성, Step 0~5 완료 (DB 796가이드 기준, V-C1~V-C10 PASS).

> 현재 기준 참고 (2026-05-07): 최신 product 기준에서는 Pipe-C 결과를 `SHE -> SR -> Guide/WorkProcess/CI` 추천 품질 개선에 사용한다. 전체 Guide JSON 추출 완료 후 faceted 교차검증과 Guide 레이어 리빌딩을 다시 수행한다.

## 목적

Pipe-A(법령→SR 626)와 Pipe-B(가이드→CI)의 데이터를 교차 비교·검증·통합하여 온톨로지 품질을 확정한다.
DB에 796가이드 기준 CI 35,206건 적재 완료, ci_sr_mapping 9,164건, V-C1~V-C10 PASS.

## Phase 1: DB 기반 교차검증 (결정론적)

### Step 0: SR 커버리지 갭 분석
- 626 SR 중 ci_sr_mapping 연결이 있는 SR 수 집계
- 도메인별·requirement_type별 커버리지 분석
- 정규화 커버리지 (처리 가이드 비율 보정)

### Step 1: basedOn 기존 매핑 정확성 감사
- ci_sr_mapping의 CI↔SR 텍스트 키워드 겹침 계산
- overlap=0 → 의심 매핑, 1~2 → 약함, 3+ → 정상
- 도메인별 매칭 품질 분리 분석

### Step 2: DT 중복 탐지
- 도메인 내(intra-domain) 완전 일치 중복 우선
- 교차 도메인 중복 참고용
- 유사 용어 (앞 3글자 동일) 탐지

## Phase 2: basedOn 복원 + 통합

### Step 3: basedOn null 복원 (도메인별 전략)
- 1차: RECOMMENDED(법령 근거 미확인) CI vs SR 626개 키워드 매칭
- 겹침 5+ → 자동 복원 후보, 3~4 → 약한 후보
- 2차 (선택): LLM 의미 확인 (`--llm-verify`)
- `--apply`로 DB 적용

### Step 4: sr-registry.json 최종 빌드
- Pipe-A SR + Pipe-B CI/DT/WP + Pipe-C 검증 결과 통합
- 626 SR 전체 포함 단일 JSON

## Phase 3: 텍스트 기반 분석 (후순위)

### Step 5: GuideInterLink 가이드 상호참조
- 파싱 가이드 텍스트에서 "KOSHA GUIDE", "참조" 패턴 regex 탐지
- guide_inter_links 테이블 적재

## 검증: V-C1~V-C10

`db/import_pipec.py`로 실행. 전체 PASS가 성공 기준.

## 비판적 분석 반영

1. basedOn이 도메인별로 극단적으로 다름 → 도메인별 전략 분리
2. candidateSR 매칭률 3~20% → 정규화 해석
3. GuideInterLink 후순위 → DB 작업 먼저
4. DT 중복은 도메인 내 중심
5. SR 커버리지는 처리 가이드 대비 정규화
