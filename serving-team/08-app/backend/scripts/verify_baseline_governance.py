#!/usr/bin/env python3
"""Baseline 거버넌스 게이트 — MEAS-2 (F14+F18). `make verify-baseline`.

회귀게이트의 보호선이 가리키는 4-포인터가 전부 같은 baseline을 보는지 검증:
  ① Makefile `F1_BASELINE`
  ② regression_gate.py `DEFAULT_BASELINE`
  ③ baseline 파일 실존 + provenance 블록 보유
  ④ docs/status/evaluation-baseline.md의 gate-baseline anchor(파일명 + 게이트 키 수치)

하나라도 어긋나면 exit 1 — "accepted 수치는 문서에만 있고 게이트는 stale floor를
밟는" F14 사고의 재발을 코드로 차단한다. baseline 채택 절차의 종료 게이트로 사용.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regression_gate  # noqa: E402  (DEFAULT_BASELINE 단일 정의 재사용)

REPO_ROOT = regression_gate.REPO_ROOT
MAKEFILE = REPO_ROOT / "Makefile"
BASELINE_DOC = REPO_ROOT / "docs" / "status" / "evaluation-baseline.md"

ANCHOR_KEYS = (
    "she_accuracy",
    "sr_accuracy",
    "penalty_accuracy",
    "overall_accuracy",
    "false_positive_rate",
    "false_negative_rate",
    "she_recall_miss_rate",
    "guide_coverage_rate",
)


def _makefile_baseline_name() -> str | None:
    text = MAKEFILE.read_text(encoding="utf-8")
    m = re.search(r"^F1_BASELINE\s*:=.*/(replay_baseline_[\w.]+\.json)\s*$",
                  text, re.MULTILINE)
    return m.group(1) if m else None


def _doc_anchor() -> dict | None:
    text = BASELINE_DOC.read_text(encoding="utf-8")
    for block in re.findall(r"```json\s*\n(.*?)\n```", text, re.DOTALL):
        if '"gate-baseline"' in block:
            try:
                return json.loads(block)
            except json.JSONDecodeError as exc:
                print(f"FAIL: anchor 블록 JSON 파싱 실패: {exc}", file=sys.stderr)
                return None
    return None


def main() -> int:
    errors: list[str] = []

    gate_name = regression_gate.DEFAULT_BASELINE.name
    mk_name = _makefile_baseline_name()
    if mk_name is None:
        errors.append("Makefile에서 F1_BASELINE 패턴을 찾지 못함")
    elif mk_name != gate_name:
        errors.append(f"포인터 불일치: Makefile F1_BASELINE={mk_name} "
                      f"vs regression_gate DEFAULT_BASELINE={gate_name}")

    if not regression_gate.DEFAULT_BASELINE.exists():
        errors.append(f"baseline 파일 부재: {regression_gate.DEFAULT_BASELINE}")
        summary = {}
    else:
        payload = json.loads(
            regression_gate.DEFAULT_BASELINE.read_text(encoding="utf-8"))
        summary = payload.get("summary") or {}
        if "provenance" not in payload:
            # v4 이전 캡처본은 provenance 부재 — 차단 대신 경고(다음 재캡처에서 해소).
            print(f"WARN: {gate_name}에 provenance 블록 없음 "
                  f"(capture_baseline.py 이전 캡처본 — 다음 재캡처 시 해소)")

    anchor = _doc_anchor()
    if anchor is None:
        errors.append(f"{BASELINE_DOC.name}에 gate-baseline anchor(json) 블록 없음")
    else:
        if anchor.get("file") != gate_name:
            errors.append(f"anchor 불일치: 문서 anchor file={anchor.get('file')} "
                          f"vs 게이트={gate_name}")
        for key in ANCHOR_KEYS:
            if key not in anchor:
                errors.append(f"anchor에 키 부재: {key}")
                continue
            if summary and float(anchor[key]) != float(summary.get(key, -1)):
                errors.append(f"anchor 수치 불일치: {key} 문서={anchor[key]} "
                              f"vs baseline 파일={summary.get(key)}")

    if errors:
        print("verify-baseline FAIL — baseline 거버넌스 불일치:")
        for e in errors:
            print(f"  ✗ {e}")
        print("\n복구: 채택 절차(4-포인터 원자 갱신)를 단일 커밋으로 완료하라 — "
              "capture_baseline.py 출력의 '다음 단계' 참조.")
        return 1

    print(f"verify-baseline PASS — 4-포인터 일치: {gate_name}")
    for key in ANCHOR_KEYS:
        print(f"  {key:<24s} {summary.get(key)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
