# Air-gap Docker 배포 (GitHub 불가 · 수동 업로드)

개인 서버가 외부 레지스트리/GitHub에 접근 불가할 때, **이 PC에서 이미지를 빌드해 파일로 옮겨** 서버에서 기동한다.
서버에는 GitHub도, 소스코드도 필요 없다(코드는 이미지에 포함). PG는 서버에 이미 있는 것을 사용한다.

```
[이 PC: 인터넷 O]  build → docker save → tar          [수동 업로드]        [서버: air-gap]  docker load → up
  ohs-backend:airgap  ─┐                                                    ┌─ 기존 PG(kosha, docker)
  ohs-frontend:airgap  ├─ ohs-images.tar.gz  ───────────────────────────►  ├─ ChromaDB(bind-mount)
  backend/data/chromadb ─ ohs-chromadb.tar.gz ──────────────────────────►  └─ .env(OPENAI_API_KEY)
```

---

## ⚠️ 0. 전제 — 런타임에 OpenAI API가 필요하다 (필수 확인)

이 서비스는 요청 시 **api.openai.com**을 호출한다: Vision(gpt-4.1, 사진분석) · 임베딩(text-embedding-3-small, hybrid 검색·§근거) · rerank(gpt-4.1-mini). 즉 **서버가 api.openai.com으로 아웃바운드 HTTPS가 가능해야** 동작한다.

- "레지스트리/GitHub만 차단, OpenAI는 허용" → **그대로 진행 가능**.
- "OpenAI도 완전 차단(진짜 air-gap)" → **현 아키텍처로는 동작 불가**. (사내 OpenAI 프록시/Azure OpenAI가 있으면 endpoint override가 필요 — 별도 작업.)

서버에서 먼저 확인:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.openai.com/v1/models   # 401이면 도달 OK(키만 없을 뿐)
```

---

## 1. 이 PC에서 — 빌드 + 패키징

```bash
cd serving-team/08-app
bash deploy/airgap/build_and_save.sh
# → deploy/airgap/dist/ohs-images.tar.gz, ohs-chromadb.tar.gz 생성
```
> `backend/.dockerignore`가 `.venv`·`data/`·`.env`를 제외하므로 이미지가 가볍고 **API 키가 굽히지 않는다**.

## 2. 서버로 업로드 (scp/rsync/USB 등 가능한 수단)

서버의 한 폴더(예: `/srv/ohs/deploy`)에 아래를 모은다:
| 파일 | 출처 |
|---|---|
| `ohs-images.tar.gz` | 1단계 산출 (~0.5–1GB) |
| `ohs-chromadb.tar.gz` | 1단계 산출 (~0.6–0.8GB) |
| `ohs-shared-reference.tar.gz` | 1단계 산출 (~0.1MB, canonical_vocab+JSON) |
| `docker-compose.airgap.yml` | `deploy/airgap/` |
| `load_and_up.sh` | `deploy/airgap/` |
| `.env.example` | `deploy/airgap/` |

## 3. 서버에서 — .env 작성 + 기동

```bash
cd /srv/ohs/deploy
cp .env.example .env
nano .env          # OPENAI_API_KEY, DATABASE_URL, CHROMADB_HOST_DIR, SHARED_REF_HOST_DIR 채우기
bash load_and_up.sh
```
`load_and_up.sh`가: 이미지 `docker load` → ChromaDB를 `CHROMADB_HOST_DIR`에 풀기 → `docker compose up -d`.

접속: `http://<서버IP>:3000/ohs/`

---

## PG 연결 (서버의 기존 dockerized PG)

`.env`의 `DATABASE_URL`을 서버 상황에 맞게:

- **(A) PG가 호스트 5432를 publish** (`docker run -p 5432:5432 ...`):
  ```
  DATABASE_URL=postgresql://kosha:<DB_PASSWORD>@host.docker.internal:5432/kosha
  ```
  (compose의 `extra_hosts: host.docker.internal:host-gateway`로 동작. 운영은 강한 비번 사용)

- **(B) PG가 docker 네트워크에만 있음** (포트 미publish): 그 네트워크를 compose에 붙인다.
  ```bash
  docker inspect <pg-컨테이너> -f '{{range $k,$_ := .NetworkSettings.Networks}}{{$k}} {{end}}'   # 네트워크명 확인
  ```
  `docker-compose.airgap.yml`에서 `kosha-shared`(또는 실제 이름) 네트워크 + backend의 두번째 네트워크 주석 해제, 그리고:
  ```
  DATABASE_URL=postgresql://kosha:<DB_PASSWORD>@<pg-컨테이너명>:5432/kosha
  ```

확인: `docker exec ohs-backend python -c "import psycopg2,os;psycopg2.connect(os.environ['DATABASE_URL']);print('PG OK')"`

> ChromaDB의 guide_code/IRI는 PG(kosha_guides·safety_requirements 등)에 **존재 검증(SSOT)**된다.
> 서버 PG가 이 ChromaDB를 만든 데이터와 동일 baseline이어야 부착이 정상 동작한다(다르면 일부 후보가 SSOT 거부됨).

---

## 갱신(재배포)
코드/ChromaDB가 바뀌면 1단계부터 재실행 → 새 tar 업로드 →
`docker load` 후 `docker compose -f docker-compose.airgap.yml up -d`(이미지 교체 시 자동 재생성). ChromaDB만 바뀌면 tar만 교체·재압축해제 후 `docker restart ohs-backend`.

## 첫 부팅 동작 (정상)
backend startup(`main.py` lifespan)이 **legacy 인덱스 2개**(article 검색 / guide 섹션 검색)를 OpenAI 임베딩으로
빌드한다 — 전송된 `ohs_*`(핵심 4패널용)와 **별개**다. 최초 1회만 수 분 + 소액 임베딩 비용이 들고, 결과는
chromadb 볼륨에 캐시되어 이후 부팅은 빠르다. 이 빌드가 끝나야 `Application startup complete`가 찍히고
`/docs`가 200을 준다(그 전엔 503/무응답이 정상). **핵심 4패널 서빙은 전송된 `ohs_*` 컬렉션으로 즉시 동작.**
- 첫 부팅을 빠르게/무비용으로 하려면: 로컬에서 backend를 진짜 키로 1회 기동해 article/guide 인덱스를 chromadb에
  채운 뒤 `ohs-chromadb.tar.gz`를 다시 만들어 전송(권장, air-gap에 유리). 또는 두 기능을 안 쓰면 lifespan에서 비활성.

## 트러블슈팅
| 증상 | 원인/조치 |
|---|---|
| 첫 부팅이 느림(수 분)·OpenAI 호출 다수 | 정상 — 위 "첫 부팅 동작"(legacy 인덱스 최초 빌드, 이후 캐시) |
| `ohs-backend` 부팅 후 즉시 종료 | `docker logs ohs-backend` — 대개 DATABASE_URL(PG 도달 불가) 또는 .env 누락 |
| 추천 결과 비어있음 / 500 | OpenAI 도달 불가(0번) 또는 ChromaDB 미mount(`docker exec ohs-backend ls /app/data/chromadb` 확인) |
| `[SectionEvidence]`/hybrid 경고 | ChromaDB 컬렉션 0개 — `CHROMADB_HOST_DIR` 경로/압축해제 확인 |
| frontend `/api` 502 | backend 미기동 또는 같은 `ohs-network` 아님(nginx `proxy_pass http://backend:8000`) |
| `network kosha-shared not found` | (B) 경로인데 네트워크명 불일치 — 실제 이름으로 수정 |
