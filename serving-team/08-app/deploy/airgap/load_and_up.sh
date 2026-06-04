#!/usr/bin/env bash
# ── air-gap 서버에서 실행 ──────────────────────────────────────────────────
# 업로드한 이미지 load + ChromaDB 배치 + compose 기동.
# 같은 폴더에 있어야 할 것: ohs-images.tar.gz, ohs-chromadb.tar.gz,
#                          docker-compose.airgap.yml, .env (직접 작성)
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "!! .env 없음 — .env.example을 복사해 작성하세요: cp .env.example .env" >&2; exit 1; }
# .env에서 CHROMADB_HOST_DIR 로드
CHROMADB_HOST_DIR="$(grep -E '^CHROMADB_HOST_DIR=' .env | tail -1 | cut -d= -f2-)"
: "${CHROMADB_HOST_DIR:?.env에 CHROMADB_HOST_DIR 지정 필요}"

echo "[1/3] 이미지 load (Docker Hub 접근 불요)..."
docker load -i ohs-images.tar.gz

echo "[2/3] ChromaDB 배치 → ${CHROMADB_HOST_DIR}"
PARENT="$(dirname "${CHROMADB_HOST_DIR}")"
mkdir -p "$PARENT"
tar xzf ohs-chromadb.tar.gz -C "$PARENT"      # 아카이브 내부가 'chromadb/' → $PARENT/chromadb 생성
test -d "${CHROMADB_HOST_DIR}" || { echo "!! ${CHROMADB_HOST_DIR} 생성 실패 — 경로/아카이브 확인" >&2; exit 1; }

echo "[3/3] 기동..."
docker compose -f docker-compose.airgap.yml up -d
docker compose -f docker-compose.airgap.yml ps
echo
echo "확인:"
echo "  - 백엔드:  curl -s http://127.0.0.1:8000/docs >/dev/null && echo OK"
echo "  - 프론트:  http://<서버IP>:3000/ohs/"
echo "  - 로그:    docker logs -f ohs-backend   (DB/OpenAI/ChromaDB 연결 확인)"
