from app.integrations.prompts.prompt_builder import build_system_prompt

SYSTEM_PROMPT = build_system_prompt()

IMAGE_ANALYSIS_PROMPT = """Analyze the workplace image as an observation extractor.

Workplace type: {workplace_type}
Additional context: {additional_context}

Return only what is visible or strongly implied by visible evidence:
- visual_observations: factual observations (한국어로 작성)
- visual_cues: short matching cues such as missing guardrail, exposed cable, wet floor (한국어로 작성)
- hazards: 사진에서 직접 식별되는 위험요소 (자연어 카테고리, ⭐ Hazard-Direct pivot Phase 1)
- risk_feature_candidates: candidate accident type, hazardous agent, or work context (영문 enum 코드 그대로: FALL, SCAFFOLD 등) — hazards[]와 병행 출력

## hazards[] 작성 지침 (한국어 자연어)

각 hazard 항목은 다음 요소를 포함:
- name: 자연어 카테고리. 가급적 표준 라벨 사용:
  '끼임/협착', '전도/미끄럼', '추락', '낙하물', '충돌', '감전',
  '유해물질', '화재/폭발', '화상', '인간공학', '기계적위험',
  '소음/진동', '온도극단', '폐쇄공간/질식'
  (사진에 다른 명확한 위험이 보이면 자유 자연어 가능)
- risk_level: high|medium|low (사진 단서 강도 + 노출 빈도 기반)
- location: 사진 어디서 보이는지 (예: '컨베이어 벨트 우측', '작업자 발 밑')
- description: 위험 상황 한 줄 설명 (한국어)
- preventive_measures: 사진 context 기반 예방조치 권고 3-4개 (한국어)

규칙:
- 사진에 명확한 단서가 있을 때만 hazard 추가 (가설 금지)
- 같은 사진에서 보통 3-5개 hazard 식별 (8 real-test-photo 평균 4.6)
- preventive_measures는 PPE / 작업절차 / 환경통제 / 점검 등 다각도
- name은 위험 발생 양상 자체 (사고형). PPE state 부족이나 환경 자체는 위험요소가 아님
  (예: '안전모 미착용' → '낙하물' 또는 '추락' name; '안전모 미착용'은 description/preventive_measures에 기재)

## 관찰 체크리스트 (v3, 2026-08-10 — v2 A/B exact 0.725→0.784·악화 0 + miss11 분해 후속)

다음 계통은 위험 판정의 결정적 단서인데 서술에서 자주 누락된다. 사진에 **보이면 반드시**
visual_observations와 visual_cues에 포함하라 (보이지 않으면 적지 말 것 — 부재 추정 금지):
- 소방·화기: 소화기·소화전·흡연 표지·용접 불꽃 흔적, 흡연 흔적(재떨이 또는 재떨이로 쓰인 그을린 깡통·담배꽁초·라이터·담뱃갑)
- 전기 계통: 분전반·배전반과 그 덮개 상태, 접지선·접지 단자, 누전차단기, 콘센트·멀티탭
- 밀폐·차단: 출입구를 덮은 비닐·시트 밀폐, 경고표지·출입금지 표지, 임시 차단막
- 환기·배기: 후드·덕트·국소배기장치
- 대형 설비의 부위: 크레인 마스트·지브·훅, 곤돌라, 리프트 — 일부만 보여도 부위를 명시
- 기계 회전부의 방호덮개 상태 (명확히 보이는 경우만)

모든 user-facing 텍스트(observations, cues, hazards, descriptions, preventive_measures)는 반드시 한국어로 작성.
JSON 필드명과 risk_feature_candidates enum 코드는 영어 유지.
Do not choose legal articles, penalties, KOSHA guide numbers, or final violations."""

TEXT_ANALYSIS_PROMPT = """Analyze the workplace description as an observation extractor.

Description: {description}
Workplace type: {workplace_type}
Industry sector: {industry_sector}

Return only observable facts and risk feature candidates:
- visual_observations (한국어로 작성)
- visual_cues (한국어로 작성)
- hazards: 텍스트에서 식별되는 위험요소 (자연어 카테고리, ⭐ Hazard-Direct pivot Phase 1)
- risk_feature_candidates (영문 enum 코드 그대로) — hazards[]와 병행 출력

## hazards[] 작성 지침 (한국어 자연어)

각 hazard 항목은 다음 요소를 포함:
- name: 자연어 카테고리. 가급적 표준 라벨 사용:
  '끼임/협착', '전도/미끄럼', '추락', '낙하물', '충돌', '감전',
  '유해물질', '화재/폭발', '화상', '인간공학', '기계적위험',
  '소음/진동', '온도극단', '폐쇄공간/질식'
- risk_level: high|medium|low
- location: 텍스트에 명시된 위치 (없으면 '미상')
- description: 위험 상황 한 줄 설명 (한국어)
- preventive_measures: context 기반 예방조치 권고 3-4개 (한국어)

규칙:
- 텍스트에 명확한 단서가 있을 때만 hazard 추가
- preventive_measures는 PPE / 작업절차 / 환경통제 / 점검 등 다각도

모든 user-facing 텍스트는 반드시 한국어로 작성. JSON 필드명과 enum 코드는 영어 유지.
Do not choose legal articles, penalties, KOSHA guide numbers, or final violations."""
