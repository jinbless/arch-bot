# 폐쇄망(air-gap) Docker 배포 플레이북

> **대상 독자:** 동일 폐쇄망 서버에 새 서비스(예: **for-ceo**)를 Docker로 올리려는 작업 세션.
> **이 문서의 목적:** OHS(`serving-team/08-app`) 폐쇄망 배포에서 **실제로 검증된 패턴과 함정**을 정리해, 다른 서비스가 같은 실수를 반복하지 않게 한다.
> **레퍼런스 구현(그대로 베껴 쓸 것):** `serving-team/08-app/deploy/server/` (자립형: 전용 PG 포함) · `serving-team/08-app/deploy/airgap/` (기존 PG 가정).

---

## 0. 30초 요약

- 폐쇄망 서버 = 인터넷/레지스트리/GitHub **차단**. 서버엔 **Docker + docker compose v2**만 있으면 된다(소스/GitHub 불요 — 코드는 이미지에 포함).
- 방식: **인터넷 되는 PC에서 빌드 → 이미지·데이터를 파일(tar/dump)로 만든다 → USB로 서버에 옮긴다 → 서버에서 `docker load` + compose 기동.**
- 서버엔 **공용 edge nginx(:80) 1개**가 경로로 각 서비스에 라우팅한다(`/ohs/`, `/for-ceo`). 새 서비스는 자기 edge를 또 띄우지 말고 **기존 `edge-net`에 frontend만 가입** + `edge/conf.d/*.conf` 한 개 추가.
- 자체 DB가 필요한 서비스는 **PG 컨테이너 + 데이터 dump까지 번들에 포함**한다(서버에 DB가 전혀 없어도 동작).
- ⚠️ 서비스가 **OpenAI 등 외부 API를 런타임에 호출**하면, 그 도메인 **아웃바운드만은 방화벽에서 열려 있어야** 한다(완전차단이면 동작 불가).

---

## 1. 서버 아키텍처 (모든 서비스가 공유)

```
                         [폐쇄망 서버 — Docker만]
  브라우저 ──:80──►  edge-proxy (nginx:alpine, 공용 1개)   ── edge-net (external) ──┐
                       /ohs/      → ohs-frontend:80                                  │
                       /for-ceo   → for-ceo-frontend:3000                            │
                                                                                     │
   ┌──────────────── ohs 스택 ────────────────┐   ┌──────────── for-ceo 스택 ───────┐
   │ ohs-frontend (edge-net + internal)        │   │ for-ceo-frontend (edge-net+int) │
   │ ohs-backend  (internal)                   │   │ for-ceo-backend  (internal)     │
   │ ohs-postgres (internal, 전용 DB)          │   │ (DB 필요시 전용 PG, internal)   │
   └───────────────────────────────────────────┘   └─────────────────────────────────┘
        외부로 나가는 건 api.openai.com (HTTPS 아웃바운드)만
```

- **edge-proxy**: `nginx:alpine`. `:80` 소유. `edge/conf.d/*.conf`로 서비스별 라우팅. **OHS를 먼저 배포했으면 이미 떠 있다.**
- **edge-net**: external docker network. 최초 1회만 `docker network create edge-net`.
- 각 서비스: 자기 `internal` 네트워크(외부 차단). **frontend 컨테이너만 `edge-net`에 가입**하고, 그 컨테이너명이 edge conf의 upstream과 일치해야 한다(예: `for-ceo-frontend`).

---

## 2. 전제조건 체크

```bash
# 서버
docker compose version                  # v2 필요
# 외부 API 아웃바운드(서비스가 OpenAI 등 쓰면) — 401이면 도달 OK(키만 없음), 000/timeout이면 방화벽 막힘
curl -s -o /dev/null -w "%{http_code}\n" https://api.openai.com/v1/models
```
- 인터넷 PC: `docker` + 인터넷(베이스 이미지·패키지 pull용).

---

## 3. 번들 만들기 (인터넷 PC) — `build_bundle.sh` 패턴

**번들에 담아야 하는 것:**

| 산출물 | 무엇 | 왜 |
|---|---|---|
| `all-images.tar.gz` | `docker save`로 **서비스 이미지 + 베이스 이미지(postgres·nginx·node 등) 전부** | 서버는 레지스트리 못 감 → 베이스까지 넣어야 함 (★함정 7) |
| 데이터 tar | 런타임 bind-mount 자원(벡터DB·업로드 등) | 이미지에 안 굽히고 볼륨으로 주입 |
| 런타임-import 자원 tar | 이미지 COPY 범위 밖이지만 코드가 import하는 파일 | ★함정 5 |
| DB dump | 자체 PG 쓰면 `pg_dump -Fc` | 서버에 데이터 없음 → 같이 옮겨 restore |

**OHS 실제 예시:** `bash deploy/server/build_bundle.sh` →
`dist/all-images.tar.gz`(backend+frontend+postgres:15+nginx) · `ohs-chromadb.tar.gz` · `ohs-shared-reference.tar.gz` · `ohs-kosha.dump`.

핵심 코드(레퍼런스):
```bash
docker build -t <svc>-backend:airgap  <repo>/backend
docker build -t <svc>-frontend:airgap <repo>/frontend
docker pull postgres:15 nginx:alpine           # 서비스가 쓰는 베이스 전부
docker save <svc>-backend:airgap <svc>-frontend:airgap postgres:15 nginx:alpine | gzip > dist/all-images.tar.gz
# DB dump (★함정 2 — stdout 리다이렉트!)
docker exec -e PGPASSWORD=<pw> <local-pg> pg_dump -U <u> -d <db> -Fc -Z6 > dist/<svc>.dump
```

---

## 4. USB로 전송

- 인터넷 PC에서 **`deploy/<변형>` 폴더 통째로** USB에 복사 (그 안에 `dist/` + 서비스 compose 폴더 + `edge/`(필요시) + `load_and_up.sh`).
- 서버에서 작업 폴더로 복사:
```bash
lsblk                                              # USB 마운트 위치 확인
sudo mkdir -p /srv/<svc>/deploy
sudo cp -r /media/<user>/<USB>/<폴더>/. /srv/<svc>/deploy/
cd /srv/<svc>/deploy
```

---

## 5. 서버 기동 — `load_and_up.sh` 패턴

순서(레퍼런스):
```
docker load -i dist/all-images.tar.gz          # 1) 이미지 적재(레지스트리 불요)
docker network create edge-net 2>/dev/null||true  # 2) 공용 네트워크(있으면 무시)
tar xzf dist/<data>.tar.gz -C <host-dir>       # 3) 데이터·자원 배치
( cd <svc> && docker compose up -d postgres )  # 4) 전용 PG 기동 후
docker exec ... pg_restore ... < dump          #    데이터 restore (이미 있으면 skip = 재실행 안전)
( cd <svc> && docker compose up -d )           # 5) backend/frontend
( cd edge  && docker compose up -d )           # 6) edge (이미 떠 있으면: conf 추가 후 reload)
```
**OHS 실제:** `cp ohs/.env.example ohs/.env` → 값 채우고 → `sudo bash load_and_up.sh`. 접속 `http://<서버IP>/ohs/`.

---

## 6. ★★ 핵심 함정 — 반드시 읽을 것 (전부 실제로 겪음) ★★

**함정 1 — 외부 API 아웃바운드.** 서비스가 OpenAI 등을 런타임 호출하면 그 방화벽이 열려야 한다. 방화벽 닫힌 채 기동하면 **startup 임베딩/배치 실패** 로그가 뜬다(보통 비치명적, backend는 뜸). 방화벽 연 뒤 `docker restart <svc>-backend`. *완전차단(OpenAI도 못 나감)이면 현 구조로 동작 불가 — Azure/사내 프록시 endpoint override 별도 작업.*

**함정 2 — Git Bash에서 `pg_dump -f /tmp/x` 실패.** MSYS가 `/tmp/...`를 `C:\Users\...\Temp\...`로 변환해 컨테이너 안에서 그 경로를 못 연다. → **stdout 리다이렉트** 사용: `docker exec ... pg_dump -Fc -Z6 > host.dump` (`-f`·`docker cp` 불필요).

**함정 3 — docker 경로 변환.** Git Bash에서 `docker -v`/`cp`/`exec`의 **컨테이너 측 경로**(`/app`, `/tmp` 등)도 변환된다 → 명령 앞에 **`MSYS_NO_PATHCONV=1`** 붙일 것. (docker cp **목적지**는 상대경로로.)

**함정 4 — `.dockerignore` 중첩 미적용 → stale `.pyc`에 비밀 굽힘.** `__pycache__/`·`*.py[cod]`는 **빌드 컨텍스트 루트만** 매칭한다. 중첩(`app/__pycache__/`)이 안 빠져, 옛 자격증명이 든 `.pyc`가 이미지에 구워진다(소스에선 지웠어도!). → **`**/__pycache__/`** 와 **`**/*.py[cod]`** 사용. 검증:
```bash
docker run --rm --entrypoint /bin/sh <img> -c "find . -name '*.pyc' | wc -l"   # 0이어야
```

**함정 5 — 런타임 import 자원이 이미지에 없음.** Dockerfile `COPY . .`는 **빌드 컨텍스트(예: `backend/`) 밖**의 파일을 포함하지 않는다. repo 루트의 공용 모듈/설정을 코드가 런타임에 import하면(OHS의 `shared/reference` = canonical_vocab SSOT) **이미지에 없어서** 실제 요청 때 터진다(import는 lazy라 startup은 통과 → 발견이 늦다). → 그 자원을 **별도 tar로 번들 + compose에서 bind-mount**(+ 필요시 경로 env). 검증: `docker run --rm --entrypoint /bin/sh <img> -c "ls /app/<그경로> || echo MISSING"`.

**함정 6 — 하드코딩 자격증명.** 소스에 DB URL/키 기본값을 두지 말 것. `.env`/환경변수로 주입하고, **미설정 시 기동 차단(fail-safe)**. 자립형 PG는 dump에 비번이 없고 `POSTGRES_PASSWORD`가 컨테이너 init 시 role 비번을 정한다 → `.env`의 `POSTGRES_PASSWORD`와 `DATABASE_URL`을 같은 값으로 일치시킬 것(OHS compose는 `${POSTGRES_PASSWORD}`로 자동 일치).

**함정 7 — 베이스 이미지 누락.** 서버는 Docker Hub에 못 간다. `docker save`에 **서비스 이미지뿐 아니라 베이스(postgres·nginx·node 등)도 함께** 넣어야 서버에서 `up` 된다.

**함정 8 — edge 충돌.** edge nginx는 서버에 **1개**(`:80` 소유). 새 서비스가 자기 edge를 또 띄우면 포트 충돌. → 기존 `edge-net`에 frontend만 가입 + `edge/conf.d/<svc>.conf` 추가 + `docker exec edge-proxy nginx -s reload`.

---

## 7. for-ceo 적용 체크리스트

> for-ceo = **별도 repo**(Next.js frontend + 백엔드). 로컬 이미지 이미 존재: `for-ceo-frontend:airgap`, `for-ceo-backend:airgap`.
> **edge에 `/for-ceo` 라우팅이 이미 있다**(OHS의 `deploy/server/edge/conf.d/ohs.conf` 28~29줄, `for-ceo-frontend:3000`로 프록시). → for-ceo는 **edge를 새로 만들지 말고** 그 edge-net에 합류만.

- [ ] **DB 유무 결정.** for-ceo가 자체 DB를 쓰면 → OHS `deploy/server` 패턴 복제(전용 PG 컨테이너 + `pg_dump` 번들 + restore). 안 쓰면 PG 부분 생략.
- [ ] **build_bundle 작성**(for-ceo repo에): for-ceo backend/frontend 빌드 + **베이스(node/postgres 등) pull** → `docker save ... | gzip` (함정 7). DB 있으면 dump(함정 2).
- [ ] **런타임-import 자원 확인**(함정 5): for-ceo 코드가 repo 루트나 컨텍스트 밖 파일을 import하면 번들+마운트.
- [ ] **compose 작성**: `frontend`만 `edge-net`(external) 가입, 나머지 `internal`. **frontend container_name = `for-ceo-frontend`**(edge conf upstream과 일치) + Next.js라 컨테이너 내부 포트 `3000` 노출.
- [ ] **`.dockerignore` 점검**(함정 4): `**/__pycache__/`, `**/node_modules/`, `.env` 등 — stale 캐시/시크릿 안 굽히게.
- [ ] **자격증명**(함정 6): API 키·DB 비번은 `.env`로, 소스 기본값 금지.
- [ ] **load_and_up 작성**: `docker load` → (PG restore) → `compose up`. edge는 **이미 있으면** `conf.d/for-ceo.conf` 확인 후 `nginx -s reload`만; 없으면 OHS `edge/` 복제.
- [ ] **방화벽**(함정 1): for-ceo가 외부 API 쓰면 그 아웃바운드 확인.
- [ ] USB 전송 → 서버 `load_and_up.sh` → **`http://<서버IP>/for-ceo`** 확인.

---

## 8. 검증 (서버)

```bash
docker ps                                  # 서비스 컨테이너들 Up + edge-proxy Up
docker logs -f <svc>-backend               # 'startup complete' / 에러 확인
docker network inspect edge-net            # frontend가 edge-net에 들어있나
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/<prefix>/   # edge 경유 200
# DB 있으면: docker exec <svc>-postgres psql -U <u> -d <db> -c "select count(*) from <표>"
```

---

## 9. 레퍼런스 파일 (OHS — 그대로 베껴 쓰기)

| 파일 | 역할 |
|---|---|
| `serving-team/08-app/deploy/server/build_bundle.sh` | 인터넷 PC: 이미지+베이스 save + 데이터 tar + shared-ref tar + PG dump |
| `serving-team/08-app/deploy/server/load_and_up.sh` | 서버: load → 배치 → PG 기동+restore → up → edge |
| `serving-team/08-app/deploy/server/ohs/docker-compose.yml` | 자립형 스택(postgres+backend+frontend), edge-net 가입, 마운트 |
| `serving-team/08-app/deploy/server/ohs/.env.example` | `.env` 템플릿(키·경로·PG 비번) |
| `serving-team/08-app/deploy/server/edge/` | 공용 edge(nginx) compose + conf.d 라우팅(이미 `/for-ceo` 포함) |
| `serving-team/08-app/deploy/server/README.md` | OHS 자립형 배포 상세 |
| `serving-team/08-app/deploy/airgap/` | 변형: 서버에 **이미 PG가 있을 때**(전용 PG 없이) |
| `serving-team/08-app/security/SECURITY-REVIEW.md` | 배포 전 보안 조치(자격증명 제거·fail-safe·레이트리밋 등) |

> 작성 근거: OHS(serving-team/08-app)를 동일 폐쇄망 서버에 자립형으로 배포하며 함정 1~8을 모두 겪고 수정 완료한 결과.
