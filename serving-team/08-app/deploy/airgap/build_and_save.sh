#!/usr/bin/env bash
# ── 로컬(인터넷 가능 PC)에서 실행 ──────────────────────────────────────────
# 이미지 빌드 + docker save + ChromaDB 묶기 → air-gap 서버로 업로드할 tar 생성.
# 전제: 이 PC에 Docker + 인터넷(Docker Hub/PyPI/npm). backend/.dockerignore 존재.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$(cd "$HERE/../.." && pwd)"          # serving-team/08-app
OUT="$HERE/dist"
mkdir -p "$OUT"

echo "[1/3] 이미지 빌드 (backend, frontend)..."
docker build -t ohs-backend:airgap "$APP/backend"
docker build -t ohs-frontend:airgap --build-arg VITE_API_BASE_URL=/api/v1 "$APP/frontend"

echo "[2/3] 이미지 저장 → $OUT/ohs-images.tar.gz"
docker save ohs-backend:airgap ohs-frontend:airgap | gzip > "$OUT/ohs-images.tar.gz"

echo "[3/3] ChromaDB 묶기 → $OUT/ohs-chromadb.tar.gz (~967MB, 압축 후 더 작음)"
if [ ! -d "$APP/backend/data/chromadb" ]; then
  echo "  !! $APP/backend/data/chromadb 없음 — 먼저 컬렉션을 빌드/확보하세요." >&2; exit 1
fi
tar czf "$OUT/ohs-chromadb.tar.gz" -C "$APP/backend/data" chromadb

echo
echo "완료. 서버로 업로드할 파일:"
ls -lh "$OUT/ohs-images.tar.gz" "$OUT/ohs-chromadb.tar.gz"
echo "  + 같은 폴더의 docker-compose.airgap.yml, load_and_up.sh, .env.example"
echo "  → 서버에서 .env 작성 후  bash load_and_up.sh"
