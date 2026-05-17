#!/usr/bin/env python3
"""Phase F.1 — Normalizer alias auto-registration (정식 4-Gate).

Layer 4 Module 4.1. F.1-light (auto_register_aliases_light.py)이 생성한
synthetic 기반 proposals + (향후) analysis_log.jsonl[normalizer_unknown_codes]
mining 결과를 입력으로 4-Gate 검증을 거친 alias를 candidate file에 등재한다.

4-Gate:
  Gate 1 (embedding similarity): text-embedding-3-small cosine ≥ 0.7 vs 기존 alias
                                  (Day 3 추가 예정)
  Gate 2 (LLM verify):           light이 이미 confidence 부여 — threshold ≥ 0.8 필터
                                  (재호출 불필요, 비용 절약)
  Gate 3 (regression):           별도 호출 (`scripts/replay_synthetic_observations.py`
                                  + `scripts/regression_gate.py`, Day 5 통합)
  Gate 4 (asymmetric trust):     candidate file에 level=candidate로 작성,
                                  50회 사용 후 promote_aliases.py로 vetted 승격 (Day 7)

입력 우선순위:
  1. f1_light_proposals.json (synthetic 기반 LLM 제안 1,235개)
  2. analysis_log.jsonl[normalizer_unknown_codes] (production miss — 현재 0건, 향후 누적)

산출:
  - risk_feature_aliases_candidates.json    (Normalizer cascade step 4.5에서 startup load)
  - runtime-artifacts/alias_candidate_meta.jsonl (sidecar: uses, last_used_at, source)
  - runtime-artifacts/alias_audit.jsonl     (Gate 1/2/3 결과 + accept/reject 사유)

ENV:
  OPENAI_API_KEY     (Gate 1 embedding 호출용, Day 3부터 필수)

사용:
  python auto_register_aliases.py                              # dry-run (stats 표시)
  python auto_register_aliases.py --apply                      # 4-Gate 실행 + write
  python auto_register_aliases.py --apply --min-confidence 0.7 # threshold 조정
  python auto_register_aliases.py --skip-light                 # light proposals 무시
  python auto_register_aliases.py --skip-log                   # analysis_log 무시

상태: Day 1 — scaffold + input verification. Gate 1/3/4는 Day 3/5/7에서 추가.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
LIGHT_PROPOSALS_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f1_light_proposals.json"
)
ANALYSIS_LOG_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "analysis_log.jsonl"
)
ALIAS_MAIN_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases.json"
)
ALIAS_CANDIDATES_PATH = (
    REPO_ROOT
    / "serving-team"
    / "08-app"
    / "backend"
    / "app"
    / "data"
    / "risk_feature_aliases_candidates.json"
)
CATALOG_PATH = (
    REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
)
META_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_candidate_meta.jsonl"
)
AUDIT_PATH = (
    REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_audit.jsonl"
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_light_proposals() -> dict[str, Any]:
    """Return light proposals JSON or empty stub."""
    if not LIGHT_PROPOSALS_PATH.is_file():
        return {"stats": {}, "proposals": {}}
    return json.loads(LIGHT_PROPOSALS_PATH.read_text(encoding="utf-8"))


def load_analysis_log_unknowns() -> list[dict[str, Any]]:
    """Parse `normalizer_unknown_codes` from analysis_log.jsonl entries.

    Format per entry: `"RAW_TEXT (axis_name)"` (per A hook commit ebe1011).
    Returns list of {raw: str, failed_axis: str, ts: str, scene_hash: str}.
    """
    out: list[dict[str, Any]] = []
    if not ANALYSIS_LOG_PATH.is_file():
        return out
    with ANALYSIS_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            unknowns = entry.get("normalizer_unknown_codes") or []
            if not unknowns:
                continue
            ts = entry.get("ts", "")
            scene_hash = entry.get("scene_hash", "")
            for raw in unknowns:
                parsed = parse_unknown(raw)
                if parsed is None:
                    continue
                text, axis = parsed
                out.append({"raw": raw, "text": text, "failed_axis": axis, "ts": ts, "scene_hash": scene_hash})
    return out


def parse_unknown(raw: str) -> tuple[str, str] | None:
    """Parse `"TEXT (axis)"` format → (text, axis). Return None if shape unexpected."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not raw.endswith(")") or "(" not in raw:
        return None
    text, _, axis_part = raw.rpartition("(")
    text = text.strip()
    axis = axis_part.rstrip(")").strip()
    if not text or not axis:
        return None
    return text, axis


def load_existing_aliases() -> dict[str, dict[str, set[str]]]:
    """Return {axis: {code: set(aliases)}} merging main + candidates files."""
    out: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for path in (ALIAS_MAIN_PATH, ALIAS_CANDIDATES_PATH):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        tier1 = data.get("tier1", {})
        for axis, code_map in tier1.items():
            if not isinstance(code_map, dict):
                continue
            for code, aliases in code_map.items():
                if isinstance(aliases, list):
                    for a in aliases:
                        if isinstance(a, str) and a.strip():
                            out[axis][code].add(a.strip())
                        elif isinstance(a, dict) and isinstance(a.get("alias"), str):
                            # future schema extension support
                            out[axis][code].add(a["alias"].strip())
    return out


def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        return {"axes": {}}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Dry-run summary
# ---------------------------------------------------------------------------


def summarize_light(proposals: dict[str, Any], min_confidence: float) -> dict[str, Any]:
    """Aggregate light proposals at given threshold."""
    by_axis: dict[str, list[dict]] = defaultdict(list)
    conf_dist: Counter = Counter()
    code_pool: set[tuple[str, str]] = set()
    total = 0
    passing = 0
    for axis, code_map in proposals.get("proposals", {}).items():
        for code, entries in code_map.items():
            for e in entries:
                total += 1
                conf = float(e.get("confidence", 0.0))
                if conf >= 0.9:
                    conf_dist[">=0.9"] += 1
                elif conf >= 0.8:
                    conf_dist["0.8-0.9"] += 1
                elif conf >= 0.7:
                    conf_dist["0.7-0.8"] += 1
                elif conf >= 0.6:
                    conf_dist["0.6-0.7"] += 1
                else:
                    conf_dist["<0.6"] += 1
                if conf >= min_confidence:
                    by_axis[axis].append({**e, "code": code})
                    code_pool.add((axis, code))
                    passing += 1
    return {
        "total_proposals": total,
        "passing_count": passing,
        "passing_unique_codes": len(code_pool),
        "by_axis": by_axis,
        "confidence_dist": dict(conf_dist),
    }


def summarize_log_unknowns(unknowns: list[dict]) -> dict[str, Any]:
    """Aggregate analysis_log unknowns by (text, axis)."""
    freq: Counter = Counter()
    axes: Counter = Counter()
    for u in unknowns:
        freq[(u["text"], u["failed_axis"])] += 1
        axes[u["failed_axis"]] += 1
    return {
        "total_unknowns": len(unknowns),
        "unique_text_axis": len(freq),
        "by_axis": dict(axes),
        "top": [
            {"text": t, "failed_axis": a, "freq": n}
            for (t, a), n in freq.most_common(20)
        ],
    }


def print_dry_run(
    light_summary: dict,
    log_summary: dict,
    existing: dict,
    min_confidence: float,
    skip_light: bool,
    skip_log: bool,
) -> None:
    print("=" * 70)
    print("F.1 auto_register_aliases — DRY RUN")
    print("=" * 70)
    print(f"min_confidence (Gate 2 threshold): {min_confidence}")
    print()

    print("[Existing aliases — main + candidates merged]")
    total_codes = 0
    total_aliases = 0
    for axis, code_map in existing.items():
        n_codes = len(code_map)
        n_aliases = sum(len(s) for s in code_map.values())
        total_codes += n_codes
        total_aliases += n_aliases
        print(f"  {axis:25s}  codes={n_codes:4d}  aliases={n_aliases:5d}")
    print(f"  {'TOTAL':25s}  codes={total_codes:4d}  aliases={total_aliases:5d}")
    print()

    if skip_light:
        print("[Source 1: light proposals] SKIPPED (--skip-light)")
    else:
        print("[Source 1: f1_light_proposals.json]")
        print(f"  total proposals          : {light_summary['total_proposals']}")
        print(f"  passing @ conf>={min_confidence}: {light_summary['passing_count']}")
        print(f"  unique codes affected    : {light_summary['passing_unique_codes']}")
        print(f"  confidence distribution  :")
        for bucket in [">=0.9", "0.8-0.9", "0.7-0.8", "0.6-0.7", "<0.6"]:
            n = light_summary["confidence_dist"].get(bucket, 0)
            print(f"    {bucket:10s}: {n:5d}")
        print(f"  passing by axis          :")
        for axis, entries in light_summary["by_axis"].items():
            print(f"    {axis:25s}  {len(entries):4d}")
    print()

    if skip_log:
        print("[Source 2: analysis_log unknowns] SKIPPED (--skip-log)")
    else:
        print("[Source 2: analysis_log.jsonl[normalizer_unknown_codes]]")
        print(f"  total unknowns logged    : {log_summary['total_unknowns']}")
        print(f"  unique (text, failed_axis): {log_summary['unique_text_axis']}")
        if log_summary["by_axis"]:
            print(f"  by failed_axis           :")
            for axis, n in log_summary["by_axis"].items():
                print(f"    {axis:25s}  {n:4d}")
        if log_summary["top"]:
            print(f"  top 20 (text, failed_axis, freq):")
            for r in log_summary["top"]:
                print(f"    freq={r['freq']:4d}  axis={r['failed_axis']:20s}  text={r['text']!r}")
        else:
            print(f"  (no unknowns found — A hook may not have produced traffic yet)")
    print()

    print("[Next steps for --apply]")
    print(f"  Gate 1 (embedding) — Day 3 (not yet implemented)")
    print(f"  Gate 2 (LLM verify) — already applied via light proposals confidence")
    print(f"  Gate 3 (regression) — Day 5 (call replay_synthetic + regression_gate)")
    print(f"  Gate 4 (candidate write) — Day 5 (atomic write to candidates file)")
    print()
    print("=" * 70)


# ---------------------------------------------------------------------------
# Apply (Day 5+)
# ---------------------------------------------------------------------------


def apply_pipeline(args: argparse.Namespace) -> int:
    print("--apply is not yet implemented (Day 1 scaffold).", file=sys.stderr)
    print("Planned: Gate 1 (Day 3) + Gate 3+4 (Day 5).", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="run 4-Gate pipeline + write candidates (Day 5+)")
    parser.add_argument("--dry-run", action="store_true", help="print stats only (default when --apply not given)")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Gate 2 threshold for light proposals (default 0.8; F.3.2 used 0.7)",
    )
    parser.add_argument("--skip-light", action="store_true", help="ignore f1_light_proposals.json")
    parser.add_argument("--skip-log", action="store_true", help="ignore analysis_log.jsonl unknowns")
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True
    return args


def main() -> int:
    args = parse_args()
    light = load_light_proposals() if not args.skip_light else {"stats": {}, "proposals": {}}
    unknowns = load_analysis_log_unknowns() if not args.skip_log else []
    existing = load_existing_aliases()

    light_summary = summarize_light(light, args.min_confidence)
    log_summary = summarize_log_unknowns(unknowns)

    if args.dry_run:
        print_dry_run(
            light_summary,
            log_summary,
            existing,
            args.min_confidence,
            args.skip_light,
            args.skip_log,
        )
        return 0

    return apply_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
