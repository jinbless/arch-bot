# 프로젝트 정리 로그

정리일: 2026-05-05

## 정리 기준

현재 구조를 반영한 최신 문서만 루트에 남기고, 과거 설계 문서와 오래된 실험 리포트는 삭제했다.

원천 데이터, 실행 코드, 온톨로지 파일, 합성 테스트셋, 프론트 의존성은 보존했다.

## 남긴 최신 기준 문서

- `온톨로지_통합구조_및_흐름도.md`
- `온톨로지_법령레이어_상세도.md`
- `온톨로지_SR레이어_상세도.md`
- `온톨로지_위험상황레이어_상세도.md`
- `온톨로지_가이드레이어_상세도.md`
- `온톨로지_벌칙레이어_상세도.md`
- `needToChangeCode.md`
- `최종보고서_온톨로지_AI시스템_핵심요약.md`
- `PROJECT_CLEANUP_LOG.md`

## 삭제한 항목

- Python 캐시: `__pycache__`, `*.pyc`, `*.pyo`
- 프론트 빌드 산출물: `OHS/frontend/dist`
- 임시/백업 파일: `*.bak`, `*.tmp`, `*.old`, `*.orig`
- 오래된 합성 평가 중간 리포트: `pictures-json/reports`의 과거 실험 결과
- 과거 설계/평가 문서:
  - `koshaontology` 하위 Markdown 문서
  - `OHS/data/eval` 하위 과거 평가 Markdown 문서

정리 실행 결과:

```text
removed entries: 360
removed files: 637
removed size: 1499.95 MB
failed deletions: 0
```

## 보존한 항목

- `OHS/frontend/node_modules`
- `pictures-json/synthetic_observations_v1.jsonl`
- `pictures-json/synthetic_observations_v2.jsonl`
- `pictures-json/synthetic_observations_v3.jsonl`
- `pictures-json/synthetic_observations_v4.jsonl`
- `pictures-json/reports/synthetic_observations_v1_penaltypath_*`
- `pictures-json/reports/synthetic_observations_v2_penaltypath_*`
- `pictures-json/reports/synthetic_observations_v3_penaltypath_*`
- `pictures-json/reports/synthetic_observations_v4_penaltypath_*`
- `koshaontology/ontology/kosha-ontology.owl`
- `koshaontology/ontology/kosha-ontology.formatted.ttl`
- `koshaontology/ontology/kosha-instances.ttl`
- `koshaontology/ontology/kosha-rules.swrl`
- `legalize-kr`
- `kosha-guides`
- `최종보고서_온톨로지 기반 근로감독관 AI 지원시스템 구축 방안 연구_v1.pdf`

## 검증 결과

### 문서 정리 검증

```text
koshaontology markdown remaining: 0
OHS/data/eval markdown remaining: 0
pictures-json/reports file count: 12
```

남은 리포트는 `synthetic_observations_v1~v4_penaltypath`의 `json/md/csv` 12개뿐이다.

### 온톨로지 검증

```text
kosha-ontology.owl parse: OK, 1089 triples
kosha-ontology.formatted.ttl parse: OK, 1089 triples
kosha-instances.ttl parse: OK, 666334 triples

PenaltyRoute mentions: 0
penaltyForArticle mentions: 0
SeverityLevel mentions: 0
hasSeverityLevel mentions: 0

PenaltyRule instances: 4772
PenaltyCondition instances: 4772
violatedArticle triples: 4772
penaltyArticle triples: 4772
hasCondition triples: 4772
hasSanction triples: 4772
severityScore triples: 4772
```

### 코드 검증

```text
Python compile check: OK, 133 files
Frontend build: OK
```

Vite 빌드에서 큰 번들 경고는 있었지만 빌드는 성공했다. 검증 후 `OHS/frontend/dist`는 다시 삭제했다.

### 합성 테스트셋 검증

```text
v1: SHE recall 100.0%, SHE false positive 23, specificity 53.1%
v2: SHE recall 100.0%, SHE false positive 9,  specificity 70.0%
v3: SHE recall 97.4%,  SHE false positive 28, specificity 37.8%
v4: SHE recall 75.0%,  SHE false positive 0,  specificity 100.0%
```

PenaltyPath 3경로 지표:

```text
v1: general/death/serious = 97/101/101
v2: general/death/serious = 81/81/81
v3: general/death/serious = 182/182/182
v4: general/death/serious = 54/54/54
```

## 남은 후속 과제

- `v4` false negative를 줄이기 위한 `VisualTrigger` 세밀화
- `PenaltyPath` 카드 문구의 사업주용 표현 개선
- `app:` 실행 레이어 저장 구조 구현
