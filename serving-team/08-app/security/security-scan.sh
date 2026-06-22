#!/usr/bin/env bash
# OHS SAST 스캔 — 소스가 있는 곳(로컬/CI)에서 실행.
# ★ 프로덕션 서버(moellab.info)는 소스가 없음(빌드된 docker 이미지로 구동) → 거기선 못 돌린다.
#   SAST는 소스 위치(개발 PC/CI), DAST(dast-zap.sh)만 구동 중인 서버(스테이징) 대상.
#
# semgrep(로컬 설치 시 직접, 없으면 docker semgrep/semgrep 자동 폴백) + pip-audit + npm audit + gitleaks.
# 결과: serving-team/08-app/security/reports/
#
# 사용: bash serving-team/08-app/security/security-scan.sh
set -uo pipefail
APP_REL="serving-team/08-app"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"   # arch-bot 루트
cd "$REPO_ROOT"
OUT="$APP_REL/security/reports"; mkdir -p "$OUT"
SRC=("$APP_REL/backend/app" "$APP_REL/frontend/src")
RULES=(--config p/owasp-top-ten --config p/python --config p/javascript \
       --config p/typescript --config p/react --config p/secrets \
       --config "$APP_REL/security/semgrep-ohs.yml")

echo "================ OHS SAST ($(date -u +%FT%TZ)) @ $REPO_ROOT ================"

echo "[1/4] semgrep (registry + OHS 커스텀)"
if command -v semgrep >/dev/null 2>&1; then
  semgrep scan "${RULES[@]}" --json --output "$OUT/semgrep.json" --metrics off "${SRC[@]}" || true
  semgrep scan "${RULES[@]}" --metrics off "${SRC[@]}" 2>/dev/null | tail -20 || true
elif command -v docker >/dev/null 2>&1; then
  echo "  로컬 semgrep 없음 → docker(semgrep/semgrep) 사용"
  export DOCKER_CONFIG="$(mktemp -d)"   # Docker Desktop credsStore 오류 우회(공개이미지 익명 pull)
  docker run --rm -v "$REPO_ROOT:/src" -w /src semgrep/semgrep \
    semgrep scan "${RULES[@]}" --json --output "$OUT/semgrep.json" --metrics off "${SRC[@]}" 2>&1 | tail -20 || true
else
  echo "  semgrep·docker 모두 없음 — 건너뜀 (pip install semgrep)"
fi

echo "[2/4] pip-audit (Python 의존성 CVE)"
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit -r "$APP_REL/backend/requirements.txt" -f json -o "$OUT/pip-audit.json" || true
  pip-audit -r "$APP_REL/backend/requirements.txt" || true
else
  echo "  미설치 — pip install pip-audit (또는 osv-scanner)"
fi

echo "[3/4] npm audit (frontend 의존성)"
if [ -f "$APP_REL/frontend/package.json" ] && command -v npm >/dev/null 2>&1; then
  ( cd "$APP_REL/frontend" && npm audit --json > "$REPO_ROOT/$OUT/npm-audit.json" 2>/dev/null; npm audit || true )
else
  echo "  npm/package.json 없음 — 건너뜀"
fi

echo "[4/4] gitleaks (하드코딩 시크릿)"
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --source "$REPO_ROOT/$APP_REL" --report-path "$OUT/gitleaks.json" --no-banner --redact || true
else
  echo "  미설치 — 바이너리 설치 또는 docker run --rm -v \$PWD:/p zricethezav/gitleaks detect -s /p"
fi

echo "================ 완료 → $OUT ================"
echo "다음: $OUT/semgrep.json 의 High/Med 를 security/SECURITY-REVIEW.md 에 병합 triage."
