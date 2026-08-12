# OHS 서버 배포 (air-gap, , 자급자족 스택)

깨끗한 Docker 서버(레지스트리/GitHub 불가, , 수동 업로드)에 OHS를 **자급자족 스택**으로 올린다.
서버엔 **Docker만** 있으면 되고, , OHS는 자기 PG·데이터·앱을 모두 포함한다. moellab 등 기존 인프라와 격리.

```
[이 PC: 인터넷 O]  build_bundle.sh                         [수동 업로드]        [서버: Docker만]
  ohs-backend/frontend 빌드 ─┐                                                  sudo bash load_and_up.sh
  postgres:15 + nginx:alpine ─┼─ all-images.tar.gz ───────────────────────────►  → 이미지 load
  backend/data/chromadb ──────── ohs-chromadb.tar.gz ──────────────────────────►  → ChromaDB 배치
  kosha-pg(PG15) ───────────────── ohs-kosha.dump ─────────────────────────────►  → 전용 PG restore
                                  + ohs/ edge/ load_and_up.sh                      → ohs + edge up
```

## 구성 (서버에서 뜨는 컨테이너)
| 컨테이너 | 이미지 | 역할 | 네트워크 |
|---|---|---|---|
| `edge-proxy` | nginx:alpine | :80, , `/ohs`·`/api` 라우팅 (공용 edge, 1개) | edge-net |
| `ohs-frontend` | ohs-frontend:airgap | React SPA + 내부 nginx | internal, , edge-net |
| `ohs-backend` | ohs-backend:airgap | FastAPI | internal |
| `ohs-postgres` | postgres:15 | 전용 kosha DB | internal |

---

## ⚠️ 전제
- 서버가 **api.openai.com** 으로 아웃바운드 가능 (Vision/임베딩/rerank 런타임 필수). 레지스트리/GitHub는 막혀도 됨.
- 서버에 **Docker + `docker compose` v2**.

## 1. 이 PC에서 — 번들 생성
```bash
cd serving-team/08-app
bash deploy/server/build_bundle.sh
# → deploy/server/dist/ : all-images.tar.gz, ohs-chromadb.tar.gz, ohs-shared-reference.tar.gz, ohs-cartoons.tar.gz, ohs-kosha.dump
```
> 로컬 `kosha-pg` 컨테이너가 떠 있으면 dump도 자동. (이미 만들어진 dist/ 산출물이 있으면 재사용)

## 2. 서버로 업로드 (scp/USB 등)
서버의 한 폴더(예: `/srv/ohs/deploy`)에 — **dist 3개 + ohs/ + edge/ + load_and_up.sh**:
```bash
DEP=/mnt/c/project/arch-bot/serving-team/08-app/deploy/server
ssh <user>@<server> "mkdir -p /srv/ohs/deploy"
scp -r "$DEP/dist/." "$DEP/ohs" "$DEP/edge" "$DEP/load_and_up.sh" <user>@<server>:/srv/ohs/deploy/
```
(업로드 후 서버에서 `/srv/ohs/deploy` 안에 `all-images.tar.gz`, `ohs-chromadb.tar.gz`, `ohs-shared-reference.tar.gz`, `ohs-cartoons.tar.gz`, `ohs-kosha.dump`, `ohs/`, `edge/`, `load_and_up.sh`가 나란히 있어야 함)

## 3. 서버에서 — .env 작성 + 기동
```bash
cd /srv/ohs/deploy
cp ohs/.env.example ohs/.env
nano ohs/.env          # OPENAI_API_KEY(진짜 키), , CHROMADB_HOST_DIR, SHARED_REF_HOST_DIR, POSTGRES_PASSWORD
sudo bash load_and_up.sh
```
`load_and_up.sh`가: 이미지 load → `edge-net` 생성 → ChromaDB 해제 → 전용 PG 기동+**데이터 restore**(kosha_guides 1038 확인) → backend/frontend → edge.

접속: **`http://<서버IP>/ohs/`** → 사진 업로드 → 4패널.

> 첫 부팅은 article/guide legacy 인덱스를 OpenAI 임베딩으로 1회 빌드(수 분)→캐시. `docker logs -f ohs-backend`에 `Application startup complete` 뜨면 준비 완료.

---

## 다른 서비스(svcA/B) 추가 방법
1. `/srv/<svc>/`에 그 서비스 스택(frontend+backend+전용 PG) compose — **frontend만 `edge-net`에 가입**.
2. `edge/conf.d/<svc>.conf` 추가 (ohs.conf 복제 → prefix·upstream 변경). `/api` 충돌나면 서비스별 prefix(`/svcA/api`) 권장.
3. `cd edge && docker compose restart` (또는 `docker exec edge-proxy nginx -s reload`).

## 갱신/재배포
- 코드 변경 → 이 PC `build_bundle.sh` 재실행 → 새 `all-images.tar.gz` 업로드 → `docker load` 후 `cd ohs && docker compose up -d`.
- 데이터(PG/ChromaDB) 변경 → 해당 tar/dump만 교체. restore는 재실행 안전(이미 있으면 건너뜀; 강제 재적재는 `docker volume rm ohs_ohs-pgdata` 후 재실행).

## 트러블슈팅
| 증상 | 조치 |
|---|---|
| `ohs-backend` 부팅 후 종료 | `sudo docker logs ohs-backend` — 대개 OPENAI_API_KEY 누락/오류 또는 PG 미준비 |
| 추천 결과 빈약 | restore 확인: `sudo docker exec ohs-postgres psql -U kosha -d kosha -c "select count(*) from kosha_guides"` (1038?) |
| ChromaDB 경고 | `sudo docker exec ohs-backend ls /app/data/chromadb` (6 컬렉션?) — CHROMADB_HOST_DIR/압축해제 확인 |
| `/ohs` 502 | ohs-frontend 미기동 또는 edge-net 미가입. `sudo docker network inspect edge-net` |
| 첫 부팅 느림 | 정상 — legacy 인덱스 빌드(이후 캐시) |
