# OHS 보안 검토 보고서 (정적 1차 · 2026-06-21)

> 대상: `serving-team/08-app` (FastAPI backend + React/Vite frontend, moellab.info 배포)
> 기준: 행안부/KISA 「소프트웨어 개발보안 가이드」(7유형 47약점) · OWASP Top 10 (2021) · OWASP API Top 10 · CWE
> 방법: LLM 코드 정적리뷰(1차). 2차 = 서버 semgrep 스캔(`security-scan.sh`) + DAST(`dast-zap.sh`).
> ※ "국정원 8대" 별도 목록 미제공 → 행안부/KISA 7유형으로 매핑(국정원 보안성검토 참조 기준). 별도 목록 주시면 정밀 재매핑.

## 요약 (심각도순)

| # | 심각도 | 발견 | 위치 | 행안부유형 / OWASP / CWE |
|---|---|---|---|---|
| F1 | **High** | API 인증·레이트리밋 부재 → 업로드·OpenAI호출 남용(자원/비용 DoS) | main.py·api/v1/analysis.py | 보안기능·API오용 / API4 Unrestricted Resource Consumption / CWE-770 |
| F2 | **High** | 파일 크기검증을 **전체 read 후** 수행 → 대용량 업로드 메모리 DoS | utils/file_handler.py:26-31 | 입력검증 / A05 / CWE-400 |
| F3 | **High** | 이미지 디컴프레션 폭탄 무방비(`Image.MAX_IMAGE_PIXELS` 미설정) | utils/file_handler.py:40,76 | 입력검증 / A05 / CWE-409 |
| F4 | **Med** | 하드코딩 기본 DB 자격증명(`kosha:1229`) 소스 잔존 | config.py:29 | 보안기능 / A07 / CWE-798·521 |
| F5 | **Med** | CORS `allow_credentials=True` + methods/headers=`*` → ALLOWED_ORIGINS 오설정(`*`) 시 취약 | main.py:74-80 | 보안기능 / A05 / CWE-942 |
| F6 | **Med** | 업로드 확장자 검증이 `filename` 없으면 skip + 확장자-only(매직바이트 X) | utils/file_handler.py:20-23 | 입력검증 / A04 / CWE-434 |
| F7 | **Low** | 예외 메시지에 내부 정보 포함 가능(`f"...{str(e)}"`) + 전역 예외핸들러/보안헤더 미확인 | file_handler.py:62 외 | 에러처리 / A05 / CWE-209 |
| F8 | **Low** | LLM 프롬프트 인젝션(사용자 text/context → Vision/LLM) — 비에이전트라 영향 제한적 | openai_client.py | API오용 / OWASP LLM01 |
| F9 | **Med** | frontend 의존성 12건 → `npm audit fix` 후 **2건**(esbuild/vite 빌드툴 잔존, dev-time) | frontend/package-lock.json | SCA / A06:2021 / CWE-1395 |
| ✓ | — | **SQL 인젝션 없음**(text()/execute() 93곳 전부 파라미터 바인딩, f-string SQL 0) · eval/exec/os.system/pickle 0 · API키 env기반 · MD5는 캐시키(usedforsecurity=False) | — | 양호 |

## 상세 + 조치

### F1. API 인증·레이트리밋 부재 (High)
- `/api/v1/image`·`/text` 등이 인증 없이 공개. 각 요청이 OpenAI Vision/LLM 호출(비용) + 파일 처리.
- 위험: 익명 대량요청 → **비용 폭증·자원 고갈 DoS**.
- 조치: (1) 레이트리밋(slowapi/`limits` — IP·분당 N) (2) 업로드 엔드포인트에 최소 인증(API key 헤더 or 세션) 또는 캡차/토큰 (3) 동시요청·일일쿼터 상한. 공개 데모면 최소 레이트리밋+쿼터 필수.

### F2. 크기검증 전 전체 read (High)
- `contents = await file.read()` 후 크기 체크 → 1GB 업로드도 일단 메모리 적재.
- 조치: `Content-Length` 헤더 선검증 + 스트리밍 read로 임계 초과 시 즉시 중단. (ASGI/Starlette `request.headers["content-length"]` 또는 청크 누적 한도.)

### F3. 디컴프레션 폭탄 (High)
- `Image.open()` 전 픽셀 상한 미설정. 작은 파일이 수억 픽셀로 전개 → 메모리 폭발.
- 조치: 모듈 로드시 `Image.MAX_IMAGE_PIXELS = <안전치, 예: 24_000_000>` + `try: Image.open ... except Image.DecompressionBombError`. thumbnail 전에 `image.verify()`/크기 사전확인.

### F4. 하드코딩 기본 DB 자격증명 (Med)
- `DATABASE_URL = "postgresql://kosha:1229@localhost/kosha"` 기본값이 소스에. prod는 .env 오버라이드여도 약한 비번 노출/재사용 위험.
- 조치: 기본값을 빈 문자열/필수(`...`)로 → 미설정 시 기동 실패(fail-safe). prod .env에 **강한 비번**. git 이력의 비번도 회전 권장.

### F5. CORS 구성 (Med)
- `allow_credentials=True` + `allow_methods/headers=["*"]`. 기본 ALLOWED_ORIGINS=localhost(안전)이나 prod .env에서 `["*"]`로 두면 자격증명+와일드카드 취약.
- 조치: prod ALLOWED_ORIGINS를 **moellab.info 출처로 고정**(절대 `*` 금지). methods/headers도 필요한 것만 명시 권장.

### F6. 업로드 확장자 검증 (Med)
- `if file.filename:` 가드 → filename 없으면 검증 skip. 확장자만 보고 매직바이트 미확인.
- 조치: filename 없으면 거부. content-type + 매직바이트(`Pillow Image.format` 또는 `python-magic`)로 실제 타입 검증. (현재 Image.open 파싱이 일부 방어하나 명시 검증 권장.)

### F7. 에러 정보노출 / 보안헤더 (Low)
- 예외 메시지에 `str(e)` 포함 → 내부경로/스택 노출 가능. 전역 예외핸들러·보안헤더 미확인.
- 조치: 사용자응답은 일반화 메시지, 상세는 서버로그만. 보안헤더(CSP·HSTS·X-Frame-Options·X-Content-Type-Options·Referrer-Policy)는 nginx에 있어도 앱 미들웨어로 defense-in-depth.

### F8. LLM 프롬프트 인젝션 (Low)
- 사용자 text/`additional_context` → LLM 프롬프트. 비에이전트(출력=분석문)라 행동탈취 위험 낮음.
- 조치: 입력 길이제한·구분자 처리·시스템프롬프트 강화. 출력은 사람이 검토(이미 그러함).

## 2차(서버) — 도구
- **SAST**: `security/security-scan.sh` (semgrep p/owasp-top-ten·p/python·p/javascript·p/typescript·p/react·p/secrets + 커스텀 룰 `semgrep-ohs.yml` + pip-audit + npm audit + gitleaks)
- **DAST**: `security/dast-zap.sh` (OWASP ZAP baseline — **스테이징 권장**) + 보안헤더/TLS 체크
- **CI 게이트**: 배포 번들 빌드 전 semgrep High/Med 0 확인.

## 조치 현황 (2026-06-21)
- **F2·F3·F6·F7(부분)** ✅ `file_handler.py` — 크기 한도내 read(메모리DoS)·`MAX_IMAGE_PIXELS` 폭탄방지·filename/매직 검증·예외 메시지 일반화.
- **F1** ✅ `main.py` slowapi 레이트리밋(전역 120/분·1000/일). ※ 다중워커는 redis 공유저장, **이미지 엔드포인트 별도 강화(예: 10/분)** 권장, nginx가 `X-Forwarded-For` 전달해야 IP별 정확.
- **F5** ✅ `main.py` — ALLOWED_ORIGINS에 `*` 포함 시 `allow_credentials` 자동 비활성 가드.
- **F7** ✅ `main.py` — 보안헤더(X-Content-Type-Options·X-Frame-Options·Referrer-Policy) 미들웨어 + 미처리 예외 일반화 핸들러. (HSTS/CSP는 nginx 권장.)
- **F4** ⏸ 코드 변경 보류(로컬 dev 파괴 방지) → **ops**: prod `.env` 강한 비번 + git 이력 비번 회전. semgrep 룰이 지속 플래그.
- **F8** ⏸ 입력 길이제한·시스템프롬프트 강화 권장(미적용).
- **배포 주의**: main.py/file_handler는 서빙코드 → 재빌드 시 `requirements.txt`의 slowapi 설치 + 업로드/레이트리밋 동작 테스트 후 번들 배포.

## SAST/SCA 결과 (2026-06-21, 로컬 실행 — 서버엔 소스 없음)

> ※ 프로덕션 서버는 빌드 이미지로 구동(소스 없음) → SAST는 소스 위치(로컬)에서 docker semgrep으로 실행.

**semgrep** (166파일·273룰) → **4건** (MD5 수정 후 5→4). **수동리뷰 대비 신규 실취약점 0 (교차검증 통과):**
- `config.py:29` 하드코딩 DB자격증명(CWE-798) = F4 → ops(.env 강한비번+이력회전). 커스텀룰 정상 작동.
- `file_handler.py:41/60/100` Image.open(CWE-409, INFO×3) = MAX_IMAGE_PIXELS + 예외핸들러로 완화(어드바이저리).
- ✅ `sparql_client.py:59` MD5(CWE-327) = `_cache_key` 캐시키(보안 아님) → `usedforsecurity=False` 적용 후 **해소**.

**npm audit (frontend SCA)** → **F9: 의존성 취약점 12건 → `npm audit fix` 후 2건** (빌드 ✅ 성공):
- ✅ 수정 10건 — 런타임 영향분 포함: **axios·form-data**(high)·rollup·picomatch·react-router·postcss·uuid 등.
- ⏸ 잔존 2건 — **esbuild/vite**(빌드툴, dev-server SSRF = 개발시 위험, 배포 static 번들엔 무관). 해결엔 vite 5→8 **메이저 업글(breaking)** → 별도 마이그레이션·테스트 필요(후순위).

**백엔드 수정 검증(로컬):** file_handler 단위테스트 6/6 통과(정상통과·과대크기·비이미지·무filename·허용외확장자 거부). slowapi 설치·import OK(py3.14+3.11). main.py AST OK — 전체 런타임은 이미지 재빌드+verify-ohs.sh서 최종확인.

**미실행(미설치)**: pip-audit(Python 의존성 CVE) · gitleaks(시크릿). 설치 후 추가 스캔 권장.
**실행도구**: `security-scan.sh` (로컬 semgrep 없으면 docker 자동 폴백 + Docker credsStore 우회 내장).

## 다음
1. ✅ F9 `npm audit fix` 완료(12→2, 빌드 OK). 잔존 esbuild/vite는 vite 5→8 **메이저 업글(breaking)** — dev-time 위험이라 후순위·별도 마이그레이션.
2. **★ 재빌드+배포** — 위 수정(F1/F2/F3/F5/F6/F7/F9/MD5)은 **로컬 소스에만**. 이미지 재빌드(backend slowapi 포함)+프론트 재빌드 → 번들 → `update-ohs.sh` → `verify-ohs.sh`. **프로덕션은 아직 미수정 상태로 서비스 중**(우선).
3. **pip-audit·gitleaks 설치 후 재스캔** (Python CVE·하드코딩 시크릿)
4. **스테이징 `dast-zap.sh`** 런타임 검증 (인증우회/IDOR/업로드/레이트리밋)
5. 이미지 엔드포인트 레이트리밋 별도 강화(10/분) + nginx `X-Forwarded-For` 전달 확인
6. (요청 시) PDF 가이드 기준 행안부 47약점 **정밀 매핑표** 작성
