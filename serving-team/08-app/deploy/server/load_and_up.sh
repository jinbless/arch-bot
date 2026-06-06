#!/usr/bin/env bash
# ── 서버에서 실행:  sudo bash load_and_up.sh ──────────────────────────────
# 이미지 load → edge-net → ChromaDB 배치 → 전용 PG 기동+데이터 restore → backend/frontend → edge.
# 큰 파일(all-images.tar.gz, ohs-chromadb.tar.gz, ohs-kosha.dump)은 이 스크립트 옆 또는 dist/ 하위 둘 다 인식.
set -euo pipefail
cd "$(dirname "$0")"

# 산출물 위치 자동 인식 (옆 or dist/)
DIST="."
if [ -f dist/all-images.tar.gz ]; then DIST="dist"; fi
for f in all-images.tar.gz ohs-chromadb.tar.gz ohs-kosha.dump; do
  [ -f "$DIST/$f" ] || { echo "!! $f 를 못 찾음(여기 또는 dist/). 업로드 확인."; exit 1; }
done

[ -f ohs/.env ] || { echo "!! ohs/.env 없음 — 'cp ohs/.env.example ohs/.env' 후 OPENAI_API_KEY 채우기"; exit 1; }
CHROMADB_HOST_DIR="$(grep -E '^CHROMADB_HOST_DIR=' ohs/.env | tail -1 | cut -d= -f2-)"
PGPW="$(grep -E '^POSTGRES_PASSWORD=' ohs/.env | tail -1 | cut -d= -f2-)"; PGPW="${PGPW:-1229}"
: "${CHROMADB_HOST_DIR:?ohs/.env에 CHROMADB_HOST_DIR 필요}"

echo "[1/6] 이미지 load (레지스트리 불요)..."
docker load -i "$DIST/all-images.tar.gz"

echo "[2/6] edge-net 생성 (있으면 무시)..."
docker network create edge-net 2>/dev/null || true

echo "[3/6] ChromaDB 배치 → ${CHROMADB_HOST_DIR}"
mkdir -p "$(dirname "${CHROMADB_HOST_DIR}")"
tar xzf "$DIST/ohs-chromadb.tar.gz" -C "$(dirname "${CHROMADB_HOST_DIR}")"
test -d "${CHROMADB_HOST_DIR}" || { echo "!! ${CHROMADB_HOST_DIR} 생성 실패"; exit 1; }

echo "[4/6] 전용 PG 기동 + 데이터 restore..."
( cd ohs && docker compose up -d postgres )
for i in $(seq 1 40); do
  docker exec ohs-postgres pg_isready -U kosha -d kosha >/dev/null 2>&1 && break
  sleep 2
done
if docker exec -e PGPASSWORD="$PGPW" ohs-postgres psql -U kosha -d kosha -tAc "SELECT to_regclass('public.kosha_guides')" 2>/dev/null | grep -q kosha_guides; then
  echo "  이미 데이터 있음 → restore 건너뜀 (재실행 안전)"
else
  echo "  restore 중 ($DIST/ohs-kosha.dump, 수 분)..."
  docker cp "$DIST/ohs-kosha.dump" ohs-postgres:/tmp/kosha.dump
  docker exec -e PGPASSWORD="$PGPW" ohs-postgres pg_restore -U kosha -d kosha --no-owner --clean --if-exists /tmp/kosha.dump || true
  docker exec ohs-postgres rm -f /tmp/kosha.dump
  CNT="$(docker exec -e PGPASSWORD="$PGPW" ohs-postgres psql -U kosha -d kosha -tAc 'SELECT count(*) FROM kosha_guides' 2>/dev/null || echo 0)"
  echo "  restore 완료 — kosha_guides=${CNT} (기대 1038)"
fi

echo "[5/6] backend + frontend 기동... (첫 부팅 수 분: legacy 인덱스 빌드)"
( cd ohs && docker compose up -d )

echo "[6/6] edge 기동..."
( cd edge && docker compose up -d )

echo; echo "=== 상태 ==="
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E 'ohs-|edge-' || true
echo
echo "접속: http://<서버IP>/ohs/    (백엔드 헬스: docker logs -f ohs-backend → 'Application startup complete')"
