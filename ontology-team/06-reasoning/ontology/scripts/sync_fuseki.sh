#!/bin/bash
# PG → TTL → Fuseki 동기화 스크립트
# Usage: ./sync_fuseki.sh
#
# 1. export_owl.py 실행 → kosha-instances.ttl 재생성
# 2. docker restart kosha-fuseki (TTL은 기동 시 로드)
# 3. curl 확인: triple count 검증

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ONTOLOGY_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ONTOLOGY_DIR/docker"

echo "=== KOSHA Fuseki 동기화 시작 ==="

# Step 1: TTL 재생성
echo "[1/3] kosha-instances.ttl 재생성..."
cd "$SCRIPT_DIR"
if [ -f "export_owl.py" ]; then
    python3 export_owl.py
    echo "  → TTL 내보내기 완료"
else
    echo "  → export_owl.py 없음, TTL 재생성 건너뜀"
fi

# Step 2: Fuseki 재시작
echo "[2/3] kosha-fuseki 컨테이너 재시작..."
cd "$DOCKER_DIR"
sudo docker compose restart fuseki
echo "  → 재시작 요청 완료, 기동 대기 중..."
sleep 10

# Step 3: 검증
echo "[3/3] Fuseki 상태 검증..."
MAX_RETRIES=12
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    RESULT=$(curl -sf "http://localhost:3030/kosha/sparql?query=SELECT%20(COUNT(*)%20AS%20%3Fcnt)%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D" \
        -H "Accept: application/sparql-results+json" 2>/dev/null || echo "FAIL")

    if [ "$RESULT" != "FAIL" ]; then
        COUNT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['bindings'][0]['cnt']['value'])" 2>/dev/null || echo "0")
        echo "  → Fuseki 응답 확인: ${COUNT} triples"
        if [ "$COUNT" -gt 0 ]; then
            echo "=== 동기화 완료: ${COUNT} triples 로드됨 ==="
            exit 0
        fi
    fi

    RETRY=$((RETRY + 1))
    echo "  → 대기 중... ($RETRY/$MAX_RETRIES)"
    sleep 10
done

echo "=== 경고: Fuseki가 응답하지 않습니다 ==="
exit 1
