#!/usr/bin/env bash
# OHS DAST — OWASP ZAP baseline + 보안헤더/TLS 체크.
# ★ 스테이징 권장. 프로덕션(moellab.info) 직접 스캔은 침습 가능 → 사전 합의/저부하만.
#
# 사용: bash serving-team/08-app/security/dast-zap.sh [TARGET_URL]
#   예) bash .../dast-zap.sh http://127.0.0.1:8000        (스테이징 백엔드)
#       bash .../dast-zap.sh http://127.0.0.1:3000/ohs/   (스테이징 프론트)
set -uo pipefail
TARGET="${1:-http://127.0.0.1:8000}"
OUT="$(cd "$(dirname "$0")" && pwd)/reports"; mkdir -p "$OUT"

echo "================ OHS DAST → $TARGET ================"

echo "[1] OWASP ZAP baseline (passive + 기본 active 일부)"
if command -v docker >/dev/null 2>&1; then
  docker run --rm --network host -v "$OUT:/zap/wrk:rw" -t ghcr.io/zaproxy/zaproxy:stable \
    zap-baseline.py -t "$TARGET" -J zap-baseline.json -r zap-baseline.html -m 5 || true
  echo "  → $OUT/zap-baseline.html"
else
  echo "  docker 없음 — ZAP 데스크톱 또는 zaproxy 설치 필요"
fi

echo "[2] 보안 응답헤더 점검"
HDRS=$(curl -sI "$TARGET" || true)
for h in "Strict-Transport-Security" "Content-Security-Policy" "X-Frame-Options" \
         "X-Content-Type-Options" "Referrer-Policy"; do
  if echo "$HDRS" | grep -qi "^$h:"; then echo "  OK   $h"; else echo "  MISS $h"; fi
done

echo "[3] (공개 도메인 TLS는 별도) testssl.sh 권장:"
echo "    testssl.sh https://moellab.info   # 인증서·프로토콜·취약 cipher"

echo "================ 완료 → $OUT ================"
echo "수동 추가점검: 인증우회/IDOR/대용량업로드/레이트리밋 — API 엔드포인트별."
