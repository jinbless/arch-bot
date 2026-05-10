# 프로젝트 정리 로그

최신 갱신일: 2026-05-07

## 현재 정리 기준

문서는 최신 구조를 기준으로 유지한다. 과거 phase 실행 문서는 삭제하지 않고, 역사 문서로 보존하되 현재 product 기준과 다르면 상단 안내나 Pipe 상태 문서에서 차이를 명시한다.

원천 데이터, 실행 코드, 온톨로지 파일, 합성 테스트셋, 프론트 의존성은 보존한다.

## 현재 기준 문서

루트 기준 문서:

- `README.md`
- `NEXT_SESSION_INSTRUCTIONS.md`
- `온톨로지_통합구조_및_흐름도.md`
- `온톨로지_법령레이어_상세도.md`
- `온톨로지_SR레이어_상세도.md`
- `온톨로지_위험상황레이어_상세도.md`
- `온톨로지_가이드레이어_상세도.md`
- `온톨로지_벌칙레이어_상세도.md`
- `needToChangeCode.md`
- `최종보고서_온톨로지_AI시스템_핵심요약.md`

하위 프로젝트 기준 문서:

- `OHS/README.md`
- `koshaontology/pipe-A/CLAUDE.md`
- `koshaontology/pipe-A/status_pipea.md`
- `koshaontology/pipe-A/plan_pipea.md`
- `koshaontology/pipe-B/CLAUDE.md`
- `koshaontology/pipe-B/status_pipeb.md`
- `koshaontology/pipe-B/plan_pipeb.md`
- `koshaontology/pipe-C/CLAUDE.md`
- `koshaontology/pipe-C/status_pipec.md`
- `koshaontology/pipe-C/plan_pipec.md`

## 보존 대상

- `OHS/frontend/node_modules`
- `pictures-json/synthetic_observations_v1.jsonl` ~ `synthetic_observations_v10.jsonl`
- `pictures-json/reports`의 최신 합성 평가 리포트
- `koshaontology/ontology/kosha-ontology.owl`
- `koshaontology/ontology/kosha-ontology.formatted.ttl`
- `koshaontology/ontology/kosha-instances.ttl`
- `koshaontology/ontology/kosha-rules.swrl`
- `legalize-kr`
- `kosha-guides`
- `최종보고서_온톨로지 기반 근로감독관 AI 지원시스템 구축 방안 연구_v1.pdf`

## 최근 product 정리 상태

`OHS`는 레거시 resource/video/category 중심 구조를 제거하고 현재 온톨로지 흐름에 맞춰 정리하는 중이다.

현재 product 흐름:

```text
사진/텍스트 입력
→ 관찰 사실/시각 단서 추출
→ risk:RiskFeature 정규화
→ she:SituationalHazardPattern 매칭
→ SR / Guide / CI / PenaltyPath 조회
→ 사업주용 조치 중심 결과 화면
```

대표 변경:

- `article_chapters.json`, `resources.json`, `safety_videos.json` 기반 런타임 경로 제거
- `risk_feature_aliases.json`, `risk_feature_catalog.json` 도입
- `analysis_pipeline.py` 중심 분석 오케스트레이션 도입
- `GuideProcedurePanel`, `ImmediateActionsPanel`, `PenaltyPathPanel`, `ReasoningTracePanel`, `RiskOverviewPanel` 도입

## 최근 검증 결과

코드 검증:

```text
Python compile: OK
frontend npm run build: OK
```

브라우저/서버 확인:

```text
홈 화면: 최신 product 문구 확인
분석 페이지: HTTP 200 확인
브라우저 자동화: 분석 페이지 상세 확인은 타임아웃 이력 있음
```

합성 테스트 smoke:

```text
report: pictures-json/reports/synthetic_observations_v10_product_refactor1_report.md
cases: 330
SHE recall: 100.0%
SHE false negative: 0
SHE false positive: 0
normal suppression: 100.0%
confirmed risk recall / precision: 44.4% / 58.5%
confirmation candidate capture: 100.0%
```

## 문서 최신성 검증 기준

문서 검색 대상:

- 루트 `*.md`
- `OHS`의 authored `*.md`
- `koshaontology`의 authored `*.md`

제외:

- `OHS/frontend/node_modules/**`
- `pictures-json/reports/**`의 과거 생성 리포트
- 외부 dependency 문서

폐기 용어는 본문 설명에 새 구조처럼 남아 있으면 안 된다. 단, “제거됨”, “폐기됨”, “과거 명칭” 문맥은 허용한다.

폐기 용어:

```text
폐기 용어: PenaltyRoute
폐기 용어: penaltyForArticle
폐기 용어: SeverityLevel
폐기 용어: hasSeverityLevel
폐기 용어: she:ContextFeature
폐기 용어: she:SituationalHazardEvent
```

최신 핵심 용어:

```text
risk:RiskFeature
risk:RiskPattern
she:SituationalHazardPattern
VisualTrigger
PenaltyPath
violatedArticle
penaltyArticle
Guide/WorkProcess
```

## 남은 후속 과제

1. `확정 위험`과 `확인 필요 후보`의 표시 경계 조정
2. 전체 KOSHA Guide JSON 추출 완료 후 Guide 레이어 리빌딩
3. `VisualTrigger`를 SR + Guide + WorkProcess + ChecklistItem 기반으로 더 구체화
4. 실제 서비스 API에서 `app:` 요약 RDF 저장 구조 구현
5. 브라우저 자동화 타임아웃 없이 분석 화면까지 smoke test 재확인
