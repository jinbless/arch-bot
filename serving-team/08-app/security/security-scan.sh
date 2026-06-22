#!/usr/bin/env bash
# OHS SAST 스캔 — 서버(semgrep 설치됨)에서 실행. 정적 보안점검 일괄.
# semgrep(registry 룰셋 + OHS 커스텀) + pip-audit(Py 의존성 CVE) + npm audit(FE) + gitleaks(시크릿).
# 미설치 도구는 건너뜀(|| true). 결과는 security/reports/.
#
# 사용: bash serving-team/08-app/security/security-scan.sh
set -uo pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"          # .../08-app
OUT="$APP/security/reports"; mkdir -p "$OUT"
SRC=("$APP/backend/app" "$APP/frontend/src")
CUSTOM="$APP/security/semgrep-ohs.yml"

echo "================ OHS SAST ($(date -u +%FT%TZ)) ================"

if command -v semgrep >/dev/null 2>&1; then
  echo "[1/4] semgrep (registry + 커스텀)"
  RULES=(--config p/owasp-top-ten --config p/python --config p/javascript \
         --config p/typescript --config p/react --config p/secrets --config "$CUSTOM")
  semgrep scan "${RULES[@]}" --sarif --output "$OUT/semgrep.sarif" "${SRC[@]}" || true
  semgrep scan "${RULES[@]}" --json  --output "$OUT/semgrep.json"  "${SRC[@]}" >/dev/null 2>&1 || true
  # 심각도 요약
  semgrep scan "${RULES[@]}" "${SRC[@]}" 2>/dev/null | tail -25 || true
else
  echo "[1/4] semgrep 미설치 — 건너뜀 (pip install semgrep)"
fi

echo "[2/4] pip-audit (Python 의존성 CVE)"
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit -r "$APP/backend/requirements.txt" -f json -o "$OUT/pip-audit.json" || true
  pip-audit -r "$APP/backend/requirements.txt" || true
else
  echo "  미설치 — pip install pip-audit"
fi

echo "[3/4] npm audit (frontend 의존성)"
if [ -f "$APP/frontend/package.json" ] && command -v npm >/dev/null 2>&1; then
  ( cd "$APP/frontend" && npm audit --json > "$OUT/npm-audit.json" 2>/dev/null; npm audit || true )
else
  echo "  npm/package.json 없음 — 건너뜀"
fi

echo "[4/4] gitleaks (하드코딩 시크릿)"
if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --source "$APP" --report-path "$OUT/gitleaks.json" --no-banner --redact || true
else
  echo "  미설치 — https://github.com/gitleaks/gitleaks"
fi

echo "================ 완료 → $OUT ================"
echo "다음: semgrep.json 의 High/Med 를 security/SECURITY-REVIEW.md 에 병합 triage."
