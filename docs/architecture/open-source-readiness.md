# Open Source Readiness

6단계(`kosha-ontology-reasoning`) 오픈소스 공개 체크리스트.

## 공개 범위 (확정)

| 항목 | 공개 |
|---|---|
| Framework — Reasoner runner, SHACL shapes 패턴, OWL/SWRL 패턴, Fuseki 운영 노하우 | ✓ |
| KOSHA TBox — 클래스/속성/제약 정의 | ✓ |
| KOSHA ABox — 실제 SR/CI 인스턴스 (예: SR-PPE-002, CI-AG6-006) | ✓ |
| 도구 (시각화 dashboard, validation scripts) | ✓ |

다른 산업안전 도메인 ontology 엔지니어가 KOSHA를 reference로 자신의 도메인에 응용 가능하도록.

## 체크리스트 (Phase C 직전)

### 1. License 결정
- [ ] License 선택 (후보):
  - **CC BY-SA 4.0** — 데이터(TBox/ABox) 공개에 적합. 파생작은 동일 license 적용 강제.
  - **Apache 2.0** — 코드/도구에 적합. 특허 grant 명시. 상업 친화.
  - **MIT** — 가장 관대. 코드 + 데이터 모두 단순한 attribution.
  - **이중 license** — 코드는 Apache 2.0, 데이터는 CC BY-SA 4.0 (분리)
- [ ] LICENSE 파일 작성
- [ ] CONTRIBUTING.md에 license 동의 명시

### 2. Sensitive Data Review
- [ ] 개인정보 없는지 (KOSHA 인스턴스에 사람 이름·연락처 없는지)
- [ ] 내부 정보 없는지 (회사 이름·위치 등)
- [ ] 법령 인용은 공식 출처(`legalize-kr`) 표시 (`law:cites` 등)
- [ ] 외부 manifest 참조 (e.g. KOSHA PDF source) 공식 URL 또는 출처 표기

### 3. Documentation
- [ ] README.md (영문) — 프로젝트 목적, 빠른 시작, 사용 예시
- [ ] CONTRIBUTING.md — PR 정책, code style, ontology 변경 절차
- [ ] CODE_OF_CONDUCT.md — 표준 contributor covenant
- [ ] SECURITY.md — 취약점 reporting 절차
- [ ] CHANGELOG.md — 첫 release부터 시작
- [ ] (선택) docs/ — 한글 설계 문서 일부 영문 번역

### 4. Demo / Tutorial
- [ ] `examples/` 디렉토리 — 작은 ontology subset + 리즈너 실행 예제
- [ ] Jupyter notebook 또는 quickstart script
- [ ] 다른 도메인 응용 예시 (예: 식품안전 mini ontology에 KOSHA 패턴 적용)

### 5. CI/CD
- [ ] GitHub Actions workflow (`.github/workflows/`):
  - `validate-ontology.yml` — TBox/ABox syntax 검증, SHACL 통과
  - `reasoner-smoke.yml` — Openllet 또는 Pellet으로 추론 smoke test
  - `lint.yml` — Python/Java code lint
- [ ] Status badges in README (build / coverage / license)
- [ ] Release automation (semantic versioning + GitHub Releases)

### 6. 외부 의존
- [ ] Openllet 또는 reasoner의 license 호환성 확인
- [ ] Java/Python 의존 version pinning
- [ ] Docker image (Fuseki + reasoner) 공개 (Docker Hub 또는 GHCR)

### 7. Issue / Discussion 운영
- [ ] Issue templates (.github/ISSUE_TEMPLATE/) — bug, feature, ontology proposal
- [ ] Discussion forum 활성화 (GitHub Discussions)
- [ ] 첫 release 전 RFC 단계 (예: "v0.1 RFC: scope and license")

### 8. 학술/연구 인용 가능성
- [ ] CITATION.cff 파일 작성 (Zenodo DOI 부여 가능)
- [ ] Initial paper/preprint (선택) — KOSHA ontology design rationale
- [ ] [Awesome OWL/SHACL] 또는 ontology directory에 등록

### 9. Multilingual
- [ ] 클래스/속성 라벨 한/영 (rdfs:label `@ko`, `@en`)
- [ ] 주요 도큐먼트 한/영 병기 또는 영문 우선

### 10. 첫 release 절차
- [ ] v0.1.0 태그 — TBox/ABox 안정 snapshot
- [ ] GitHub Release notes
- [ ] (선택) Zenodo DOI 발급
- [ ] 커뮤니티 공지 (산업안전·온톨로지 관련 메일링 리스트, Slack 등)

## 진행 트리거

다음 조건 만족 시 위 체크리스트 시작:
1. 6단계 자체가 완성 — Reasoner로 5번 LLM enrichment를 대체 가능한 수준
2. KOSHA TBox/ABox가 stable한 baseline에 도달
3. KOSHA 측 또는 관련 기관의 공개 동의 (필요 시)

## 공개 후 운영

- 매 release마다 sensitive data review 반복
- 외부 contributor PR 처리 정책 명시
- KOSHA 갱신 시 ABox refresh 주기
