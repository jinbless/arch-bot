#!/usr/bin/env bash
# ── 로컬(인터넷 가능 PC)에서 실행 ──────────────────────────────────────────
# OHS 이미지 빌드 + 전체 이미지 save + ChromaDB tar + kosha 데이터 dump → 서버 전송용 산출물.
# 전제: Docker + 인터넷(빌드/베이스 이미지 pull). 로컬 kosha PG 컨테이너(kosha-pg)가 떠 있으면 dump도 자동.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$(cd "$HERE/../.." && pwd)"          # serving-team/08-app
OUT="$HERE/dist"; mkdir -p "$OUT"

echo "[1/5] OHS 이미지 빌드 (backend, frontend)..."
docker build -t ohs-backend:airgap "$APP/backend"
docker build -t ohs-frontend:airgap --build-arg VITE_API_BASE_URL=/api/v1 "$APP/frontend"

echo "[2/5] 베이스 이미지 확보 (postgres:15, nginx:alpine)..."
docker pull postgres:15
docker pull nginx:alpine

echo "[3/5] 전체 이미지 save → all-images.tar.gz (backend+frontend+postgres+nginx)..."
docker save ohs-backend:airgap ohs-frontend:airgap postgres:15 nginx:alpine | gzip > "$OUT/all-images.tar.gz"

echo "[4/5] ChromaDB tar..."
if [ -d "$APP/backend/data/chromadb" ]; then
  tar czf "$OUT/ohs-chromadb.tar.gz" -C "$APP/backend/data" chromadb
else
  echo "  !! $APP/backend/data/chromadb 없음 — 컬렉션 먼저 확보" >&2; exit 1
fi

echo "[5/5] kosha 데이터 dump (로컬 kosha-pg 컨테이너 필요)..."
if docker ps --format '{{.Names}}' | grep -qx 'kosha-pg'; then
  docker exec -e PGPASSWORD=1229 kosha-pg pg_dump -U kosha -d kosha -Fc -Z6 -f /tmp/kosha.dump
  docker cp kosha-pg:/tmp/kosha.dump "$OUT/ohs-kosha.dump"
  docker exec kosha-pg rm -f /tmp/kosha.dump
elif [ -f "$OUT/ohs-kosha.dump" ]; then
  echo "  kosha-pg 미실행이나 기존 dist/ohs-kosha.dump 재사용."
else
  echo "  !! kosha-pg 미실행 + dump 없음 — 로컬 PG 켜고 재실행" >&2; exit 1
fi

echo; echo "완료. 서버로 업로드할 산출물:"
ls -lh "$OUT"
echo "  + 같은 폴더의 ohs/, edge/, load_and_up.sh"
