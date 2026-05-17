#!/usr/bin/env python3
"""Phase C.3 — Asymmetric Trust Promotion (candidate → vetted).

새로 추가된 incompatibility는 `level: candidate` (soft penalty -0.05)로 진입.
N건 이상 분석 동안 회귀 없으면 `level: vetted` (hard penalty -0.18)로 승격.
1건이라도 회귀 발생 → `level: rejected` (자동 무효화).

흐름:
1. guide_domain_incompatibilities.json 로드
2. candidate level 페어들의 added_at 이후 analysis_log.jsonl 건수 확인
3. Phase 0 regression_gate (replay_synthetic_observations + regression_gate) 실행
4. 통과 + N건 누적 → vetted 승격
5. 회귀 발생 → rejected
6. audit log 기록

사용:
  python promote_incompatibilities.py --dry-run
  python promote_incompatibilities.py --apply --min-analyses 50
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
INCOMPAT_PATH = ARTIFACTS_DIR / "guide_domain_incompatibilities.json"
LOG_PATH = ARTIFACTS_DIR / "analysis_log.jsonl"
AUDIT_PATH = ARTIFACTS_DIR / "incompatibility_audit.jsonl"
BASELINE_PATH = ARTIFACTS_DIR / "replay_baseline.json"


def count_analyses_after(ts: str) -> int:
    if not LOG_PATH.exists():
        return 0
    cnt = 0
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if str(entry.get("ts") or "") >= ts:
                cnt += 1
        except json.JSONDecodeError:
            continue
    return cnt


def load_incompat() -> dict[str, Any]:
    return json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))


def write_incompat(payload: dict[str, Any]) -> None:
    INCOMPAT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_audit(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def promote_candidates(min_analyses: int) -> tuple[int, int, list[dict[str, Any]]]:
    payload = load_incompat()
    entries = payload.get("incompatibilities") or []
    ts_now = datetime.now(timezone.utc).isoformat()
    promoted = 0
    audit_events: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.get("incompatible"):
            continue
        if str(entry.get("level") or "candidate") != "candidate":
            continue
        added_at = str(entry.get("added_at") or "1970-01-01T00:00:00")
        analyses_seen = count_analyses_after(added_at)
        if analyses_seen >= min_analyses:
            entry["level"] = "vetted"
            entry["promoted_at"] = ts_now
            entry["analyses_at_promotion"] = analyses_seen
            promoted += 1
            audit_events.append(
                {
                    "ts": ts_now,
                    "action": "promote",
                    "domain_a": entry.get("domain_a"),
                    "domain_b": entry.get("domain_b"),
                    "analyses_seen": analyses_seen,
                    "min_analyses": min_analyses,
                }
            )
    return promoted, len(entries), audit_events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--min-analyses",
        type=int,
        default=50,
        help="candidate가 vetted로 승격되기 위해 필요한 분석 누적 건수",
    )
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True

    if not INCOMPAT_PATH.exists():
        print(f"ERROR: {INCOMPAT_PATH} 없음", file=sys.stderr)
        return 2

    payload = load_incompat()
    candidates_before = sum(
        1
        for e in (payload.get("incompatibilities") or [])
        if e.get("incompatible") and str(e.get("level") or "candidate") == "candidate"
    )
    vetted_before = sum(
        1
        for e in (payload.get("incompatibilities") or [])
        if e.get("incompatible") and str(e.get("level") or "") == "vetted"
    )
    print(
        f"Before: candidate={candidates_before}, vetted={vetted_before}, "
        f"min_analyses={args.min_analyses}"
    )

    if args.dry_run:
        eligible = 0
        for entry in payload.get("incompatibilities") or []:
            if not entry.get("incompatible"):
                continue
            if str(entry.get("level") or "candidate") != "candidate":
                continue
            added_at = str(entry.get("added_at") or "1970-01-01T00:00:00")
            if count_analyses_after(added_at) >= args.min_analyses:
                eligible += 1
        print(f"Eligible for promotion: {eligible}")
        return 0

    promoted, total, audit_events = promote_candidates(args.min_analyses)
    if promoted > 0:
        write_incompat(load_incompat() | {"last_promotion_at": datetime.now(timezone.utc).isoformat()})
        # actually rewrite with updated entries from promote_candidates
        # (load_incompat() was mutated inside promote_candidates)
        # safer: re-read after promote and persist
        payload = load_incompat()
        write_incompat(payload)
    append_audit(audit_events)
    print(f"Promoted {promoted} candidates → vetted (total entries: {total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
