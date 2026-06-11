#!/usr/bin/env python3
"""Baseline capture — MEAS-2 (F14).

replay_synthetic_observations.py 결과 JSON을 회귀게이트 baseline 파일
(replay_baseline_vN.json)로 박제한다. summary만 추출하고 provenance
(git sha·캡처 시각·소스 결과 파일·사유)를 함께 기록해, "어떤 코드 상태의
어떤 실행이 이 보호선을 만들었나"를 파일 자체가 증언하게 한다.

거버넌스 규칙 (정본: docs/status/evaluation-baseline.md):
- 발행된 baseline_vN 파일은 불변 — 덮어쓰기는 --force로만(재캡처 사고 방지).
- baseline 채택 = 4-포인터 원자 갱신: ① 이 파일 생성 ② Makefile F1_BASELINE
  ③ regression_gate.DEFAULT_BASELINE ④ evaluation-baseline.md anchor 블록.
  일치 여부는 `make verify-baseline`(verify_baseline_governance.py)이 검증.

사용:
  python scripts/capture_baseline.py --results <replay_results.json> \
      --version v5 --note "MEAS-1 ecd 오염 제거 후 정직 baseline" \
      [--config-json '{"semantic_recall":"on","rerank":"off"}'] [--force]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"

# 게이트가 실제로 비교하는 키(regression_gate.py와 동기) — 캡처 시 존재 검증.
REQUIRED_SUMMARY_KEYS = (
    "she_accuracy",
    "sr_accuracy",
    "penalty_accuracy",
    "overall_accuracy",
    "false_positive_rate",
    "false_negative_rate",
    "she_recall_miss_rate",
    "guide_coverage_rate",
)


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True,
                        help="replay_synthetic_observations.py 산출 JSON")
    parser.add_argument("--version", required=True,
                        help="baseline 버전 태그 (예: v5) → replay_baseline_v5.json")
    parser.add_argument("--note", required=True,
                        help="이 baseline의 의미(무엇이 바뀐 뒤의 보호선인가) — provenance.reason")
    parser.add_argument("--config-json", default=None,
                        help="실행 구성 기록 (예: '{\"semantic_recall\":\"on\",\"rerank\":\"off\"}')")
    parser.add_argument("--force", action="store_true",
                        help="기존 baseline 파일 덮어쓰기 허용(기본 거부 — 발행본 불변)")
    args = parser.parse_args()

    if not args.results.exists():
        print(f"results not found: {args.results}", file=sys.stderr)
        return 2
    version = args.version if args.version.startswith("v") else f"v{args.version}"
    out_path = ARTIFACTS_DIR / f"replay_baseline_{version}.json"
    if out_path.exists() and not args.force:
        print(f"REFUSE: {out_path.name} 이미 존재 — 발행된 baseline은 불변. "
              f"새 버전 번호를 쓰거나 --force(사고 복구 전용).", file=sys.stderr)
        return 1

    payload = json.loads(args.results.read_text(encoding="utf-8"))
    summary = payload.get("summary") or {}
    missing = [k for k in REQUIRED_SUMMARY_KEYS if k not in summary]
    if missing:
        print(f"summary에 게이트 키 부재: {missing} — 구버전 replay 산출물?", file=sys.stderr)
        return 1
    errored = summary.get("errored", 0)
    if errored:
        print(f"REFUSE: errored={errored} — 에러 케이스가 있는 실행은 baseline 부적격.",
              file=sys.stderr)
        return 1

    config = json.loads(args.config_json) if args.config_json else None
    baseline = {
        "generated_at": payload.get("generated_at"),
        "tool": payload.get("tool", "replay_synthetic_observations.py"),
        "note": args.note,
        **({"config": config} if config else {}),
        "provenance": {
            "git_sha": _git_sha(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source_results": args.results.name,
            "reason": args.note,
        },
        "summary": summary,
    }
    out_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"Captured: {out_path}")
    print("gated keys:")
    for k in REQUIRED_SUMMARY_KEYS:
        print(f"  {k:<24s} {summary[k]}")
    print("\n다음 단계(4-포인터 원자 갱신, 단일 커밋):")
    print(f"  1. Makefile F1_BASELINE → replay_baseline_{version}.json")
    print(f"  2. regression_gate.py DEFAULT_BASELINE → replay_baseline_{version}.json")
    print(f"  3. docs/status/evaluation-baseline.md anchor 블록 갱신")
    print(f"  4. make verify-baseline 으로 일치 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
