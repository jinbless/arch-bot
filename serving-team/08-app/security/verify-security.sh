#!/usr/bin/env bash
# OHS 보안수정 런타임 검증 — 구동 중 백엔드에 업로드거부·레이트리밋·보안헤더 확인.
# 로컬 스테이징(직접 백엔드) 권장. 사용: bash verify-security.sh [BACKEND_BASE]
#   로컬: bash verify-security.sh http://127.0.0.1:8000
#   prod: nginx 경로라 BASE=https://moellab.info (업로드는 /api/v1/analysis/image, 레이트리밋 IP는 X-Forwarded-For 의존)
set -uo pipefail
BASE="${1:-http://127.0.0.1:8000}"
TMP="$(mktemp -d)"
echo "================ 보안 검증 → $BASE ================"

echo "[1] 보안 응답헤더 (F7)"
H=$(curl -sI "$BASE/" 2>/dev/null || true)
for h in "X-Content-Type-Options" "X-Frame-Options" "Referrer-Policy"; do
  echo "$H" | grep -qi "^$h:" && echo "  ✅ $h" || echo "  ❌ $h 없음"
done

echo "[2] 과대 업로드 거부 (F2, 기대 413)"
head -c 11000000 /dev/zero > "$TMP/big.png" 2>/dev/null
code=$(curl -s -o /dev/null -w "%{http_code}" -F "image=@$TMP/big.png;type=image/png" "$BASE/api/v1/analysis/image" 2>/dev/null || echo "ERR")
[ "$code" = "413" ] && echo "  ✅ HTTP $code" || echo "  ⚠️  HTTP $code (기대 413)"

echo "[3] 비이미지 거부 (F6, 기대 415)"
echo "this is not an image" > "$TMP/fake.png"
code=$(curl -s -o /dev/null -w "%{http_code}" -F "image=@$TMP/fake.png;type=image/png" "$BASE/api/v1/analysis/image" 2>/dev/null || echo "ERR")
[ "$code" = "415" ] && echo "  ✅ HTTP $code" || echo "  ⚠️  HTTP $code (기대 415)"

echo "[4] 레이트리밋 (F1, 기본 120/분 → 빠른 반복 시 429)"
got=no
for i in $(seq 1 135); do
  c=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/" 2>/dev/null || echo ERR)
  if [ "$c" = "429" ]; then echo "  ✅ ${i}번째 요청에서 429"; got=yes; break; fi
done
[ "$got" = no ] && echo "  ⚠️  135회 내 429 없음 — 한도/키(X-Forwarded-For)·SlowAPIMiddleware 확인"

rm -rf "$TMP"
echo "================ 완료 ================"
echo "정상 이미지 업로드(200)는 데이터/PG 필요 → 별도 수동확인. 거부·레이트리밋·헤더가 핵심."
