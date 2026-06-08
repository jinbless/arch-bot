# Air-gap 데모 배포 런북 (OWA→CWA 패턴 보강 반영)

> main 머지 후 air-gap OHS 데모에 SHE 패턴 보강을 **확실히 반영**하는 절차.
> 핵심 원리: **SHE 패턴은 외부 PG(`kosha-pg.she_catalog`) 데이터이지 이미지 콘텐츠가 아니다.**
> 따라서 이미지 rebuild만으로는 반영되지 않으며, **PG 재물질화(import) 단계가 필수**다.

## 무엇이 어디에 있나
| 산출물 | 위치 | 반영 방법 |
|---|---|---|
| SHE 패턴 37개 | `data-team/05-enrichment/runtime-artifacts/she_pattern_proposals.json` (git) → `kosha-pg.she_catalog` | **`make she-import ARGS='--apply'`** (재물질화) |
| she_sr_mapping | 위 import이 자동 생성 | 동일 |
| 사진 thumbnail 기능 | `serving-team/08-app/backend|frontend` (git) → 이미지 | **이미지 rebuild** |

## 배포 절차 (반드시 WSL에서)
```bash
# 0) 코드 최신화
git checkout main && git pull

# 1) PG 재물질화 — ★패턴 반영의 실제 단계★ (dry-run으로 먼저 확인 권장)
make she-import                                       # dry-run
make she-import ARGS='--apply --status approved_auto' # 실제 적재 (ON CONFLICT DO NOTHING)

# 2) 서빙 코드/프론트가 바뀐 경우에만 이미지 rebuild (패턴만이면 생략 가능)
docker build -t ohs-backend:airgap  serving-team/08-app/backend
docker build -t ohs-frontend:airgap serving-team/08-app/frontend

# 3) 스택 기동 — ★반드시 WSL에서★ (/mnt/c 마운트가 WSL에서만 해석됨)
cd serving-team/08-app/deploy/airgap
docker compose -p ohs -f docker-compose.airgap.yml --env-file .env up -d
```

## ⚠️ 흔한 함정
- **Windows/PowerShell에서 `docker compose up` 금지.** `.env`의 `SHARED_REF_HOST_DIR`/`CHROMADB_HOST_DIR`이 `/mnt/c/...` (WSL 경로)라, Windows에서 올리면 Docker VM이 경로를 못 찾아 **빈 디렉토리를 마운트** → `canonical_vocab` ModuleNotFoundError로 모든 분석 500. 반드시 WSL에서 기동.
  - (영구 대안: `.env` 경로를 Windows식 `C:\...` 또는 `//c/...`로 바꾸거나, `shared/reference`+chromadb를 이미지에 COPY로 굽기.)
- **PG 볼륨이 새로 만들어지면** 패턴이 사라지므로 1단계(import) 재실행 필요.

## 검증
```bash
make f1-regression          # 2360 replay + 회귀가드 (she/sr/fp/fn vs baseline_v3, tol 0.02)
# 라이브 확인: 백엔드에 식음료/칼작업 케이스 POST → situation_matches에 신규 패턴(-FG/-L2T/-ID) fire 확인
```

## 롤백 (패턴 보강 전체 제거)
```sql
DELETE FROM she_sr_mapping WHERE she_id LIKE 'SHE-%-L2T%' OR she_id LIKE 'SHE-%-FG__' OR she_id LIKE 'SHE-%-ID__';
DELETE FROM she_catalog    WHERE source_prompt_hash IN
  ('owacwa-l2tune-20260608','owacwa-foodgas-20260608','owacwa-ind-20260608');
```
(git: 해당 3커밋 revert.)
