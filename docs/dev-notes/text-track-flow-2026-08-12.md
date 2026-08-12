# 텍스트 트랙 앵커→흐름 개통 (2026-08-12)

> 사용자 발견: 텍스트 분석 트랙이 새 흐름 구조를 안 타고 과거 아키텍처를 바라보고 있었다.
> 확인 결과 사실 — `analysis_pipeline.py`의 `analysis_type == "image"` 게이트(당시 "사진 전제
> 구조" 스코프 결정) 때문에 텍스트는 work_flow 없음 → AI 제안 대조·불비 원장 적립 없음 →
> '지금 당장'이 잡음 실측된 CI 광역 매칭으로 폴백 → 화면도 구 골격이었다.

## 적용

- **백엔드**: [analysis_pipeline.py](../../serving-team/08-app/backend/app/services/analysis_pipeline.py)
  흐름 게이트에서 image 조건 제거 — `flow_service.enabled()`만 남김. analyze_text 결과도 같은
  형태(visual_observations·cues·hazards)라 scene_text→RESOLVE→흐름이 그대로 작동.
- **프론트**: 사진 전제 문구를 `analysis_type` 분기 — ResultPage(1단계 제목 "서술에서 파악한 것"),
  WorkFlowPanel(`inputNoun` prop — 한 시점/기인물/대안/지금 당장/신뢰 고지/AI 대조 8곳),
  FindingsCard(근거 고지), OwnerResources·ImmediateActions(중립화). AnchorPicker 태그는
  '사진 지목 불가'→'기인물 아님'(양 매체 공용).

## 검증

- **오프라인 스모크 4/4** (analyze_text→flow, 실제 프롬프트·카탈로그): 지게차→관2 지게차(77건) /
  강관비계→절3(14건) / 병원 검사실→절2 설비기준 등(13건 — miss11 레버 ②가 텍스트에서도 적중) /
  흡연·화기→절2 화기 등의 관리(27건 — **사진에선 4.1 지각 한계로 놓치던 케이스가 텍스트에선 정확**.
  텍스트 트랙이 이 클래스의 우회로가 된다).
- **프로덕션 E2E**: /analysis/text 35s, work_flow 6칸 77건 + alignments 3 + immediate_actions가
  rule:Article(검수 조문 선별) — CI 폴백 아님. 브라우저에서 "서술에서 파악한 것"·"서술은 작업의
  한 시점"·"서술에서 확인된 기인물" 등 분기 문구 전부 확인.

## 한계(명시)

- 텍스트 트랙 **gold 계측 없음** — 앵커 수치(0.784/0.961)는 감독관 사진 51장 기준. 텍스트 정확도는
  스모크 수준 확인만 된 상태다. 텍스트 gold를 만들려면 서술-조문 라벨 세트가 따로 필요.
- 텍스트 엔드포인트는 JSON 본문(멀티파트 아님 — E2E에서 422로 실측).
