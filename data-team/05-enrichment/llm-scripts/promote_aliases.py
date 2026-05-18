#!/usr/bin/env python3
"""Phase F.1 Day 7 — promote candidate aliases → vetted (main file).

흐름:
  1. Read risk_feature_aliases_candidates.json (level=candidate aliases)
  2. Read alias_candidate_meta.jsonl (per-alias uses + gate2_confidence + ...)
  3. Determine promotable per criteria:
       --auto                : uses >= --min-uses (default 5)
       --by-confidence       : gate2_confidence >= --min-conf (default 0.85)
       --promote-all         : 모두 (수동 검토 후)
       --alias TEXT --axis AXIS --code CODE : 단일 alias
  4. Atomic moves:
       a. Add to risk_feature_aliases.json (main)
       b. Remove from risk_feature_aliases_candidates.json
       c. Append promoted_at to alias_candidate_meta.jsonl
       d. Append audit row to alias_audit.jsonl
  5. Rollback: --rollback CODE ... reverses (vetted → candidate)

ENV: 없음 (file I/O only)

사용:
  python promote_aliases.py                           # dry-run --auto
  python promote_aliases.py --apply --auto            # uses >= 5
  python promote_aliases.py --apply --by-confidence --min-conf 0.85
  python promote_aliases.py --apply --promote-all     # 수동 일괄
  python promote_aliases.py --apply --alias '고소추락' --axis accident_type --code FALL_FROM_HEIGHT
  python promote_aliases.py --apply --rollback FALL_FROM_HEIGHT
  python promote_aliases.py --list                    # 현황만

Day 7: 6 Day 5 candidates 중 conf>=0.85 = 5건 promote, conf 0.80 1건 candidate 유지.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
MAIN_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases.json"
CAND_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_aliases_candidates.json"
META_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_candidate_meta.jsonl"
AUDIT_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "alias_audit.jsonl"


def load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_meta_latest() -> dict[tuple[str, str, str], dict]:
    """Latest meta per (axis, code, alias) — uses, last_used_at, gate2_conf 등.

    T1.C 통합: action='used' 행 (normalizer step 4.5 match log)을 count로 집계.
    - 'used' 외 actions (original meta, promoted, ...): 최신 timestamp 우선
    - 'used': count + last_used_at 별도 집계
    """
    latest: dict[tuple[str, str, str], dict] = {}
    used_count: dict[tuple[str, str, str], int] = {}
    last_used_at: dict[tuple[str, str, str], str] = {}
    if not META_PATH.is_file():
        return latest
    with META_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = (r.get("axis", ""), r.get("code", ""), r.get("alias", ""))
            action = r.get("action") or ""
            if action == "used":
                # T1.C — usage tracking (normalizer step 4.5)
                used_count[key] = used_count.get(key, 0) + 1
                ts = r.get("ts", "")
                if ts and ts > last_used_at.get(key, ""):
                    last_used_at[key] = ts
                continue  # don't overwrite meta with bare "used" rows
            # Non-'used' actions (initial meta, promoted, etc.) — most recent wins
            existing = latest.get(key)
            if existing is None or r.get("ts", "") > existing.get("ts", ""):
                latest[key] = r
    # Inject computed uses + last_used_at into meta
    for key, count in used_count.items():
        if key in latest:
            latest[key]["uses"] = count
            latest[key]["last_used_at"] = last_used_at.get(key)
        else:
            # uses recorded but no original meta — placeholder
            axis, code, alias = key
            latest[key] = {
                "alias": alias, "axis": axis, "code": code,
                "uses": count, "last_used_at": last_used_at.get(key),
                "_no_original_meta": True,
            }
    return latest


def enumerate_candidates(cand: dict) -> list[tuple[str, str, str]]:
    """Return [(axis, code, alias)] for all current candidates."""
    out = []
    for axis, code_map in cand.get("tier1", {}).items():
        if not isinstance(code_map, dict):
            continue
        for code, aliases in code_map.items():
            for a in aliases or []:
                if isinstance(a, str) and a.strip():
                    out.append((axis, code, a.strip()))
    return out


def select_promotable(
    items: list[tuple[str, str, str]],
    meta: dict,
    mode: str,
    min_uses: int,
    min_conf: float,
    days_window: int,
) -> tuple[list[tuple[str, str, str, dict]], list[tuple[str, str, str, str]]]:
    """Return (promote_list, reject_list_with_reason)."""
    promote: list[tuple[str, str, str, dict]] = []
    reject: list[tuple[str, str, str, str]] = []
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days_window)).isoformat()
    for axis, code, alias in items:
        m = meta.get((axis, code, alias), {})
        if mode == "promote-all":
            promote.append((axis, code, alias, m))
            continue
        if mode == "by-confidence":
            conf = float(m.get("gate2_confidence") or 0)
            if conf >= min_conf:
                promote.append((axis, code, alias, m))
            else:
                reject.append((axis, code, alias, f"conf {conf:.2f} < {min_conf}"))
            continue
        # auto: uses-based
        uses = int(m.get("uses") or 0)
        last = m.get("last_used_at") or ""
        if uses < min_uses:
            reject.append((axis, code, alias, f"uses {uses} < {min_uses}"))
            continue
        if last and last < cutoff_ts:
            reject.append((axis, code, alias, f"last_used {last[:10]} > {days_window}d 이전"))
            continue
        promote.append((axis, code, alias, m))
    return promote, reject


def apply_promotions(
    main: dict, cand: dict, promote_list: list[tuple[str, str, str, dict]]
) -> tuple[dict, dict, int]:
    """Move (axis, code, alias) from cand to main. Return (new_main, new_cand, moved)."""
    main_tier1 = main.setdefault("tier1", {})
    cand_tier1 = cand.setdefault("tier1", {})
    moved = 0
    for axis, code, alias, _meta in promote_list:
        # Add to main
        axis_main = main_tier1.setdefault(axis, {})
        aliases_main = axis_main.setdefault(code, [])
        if alias not in aliases_main:
            aliases_main.append(alias)
            moved += 1
        # Remove from candidates
        ax_cand = cand_tier1.get(axis) or {}
        if code in ax_cand:
            new_list = [a for a in ax_cand[code] if a != alias]
            if new_list:
                ax_cand[code] = new_list
            else:
                ax_cand.pop(code, None)
            if not ax_cand:
                cand_tier1.pop(axis, None)
    main["_last_updated_at"] = datetime.now(timezone.utc).isoformat()
    cand["_last_updated_at"] = datetime.now(timezone.utc).isoformat()
    cand["_total_aliases"] = sum(
        sum(len(v) for v in code_map.values()) for code_map in cand_tier1.values()
    )
    return main, cand, moved


def append_meta_promoted(promote_list: list[tuple[str, str, str, dict]]) -> None:
    if not promote_list:
        return
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with META_PATH.open("a", encoding="utf-8") as f:
        for axis, code, alias, m in promote_list:
            row = {
                "ts": ts,
                "alias": alias,
                "axis": axis,
                "code": code,
                "promoted_at": ts,
                "promotion_source_uses": m.get("uses", 0),
                "promotion_source_conf": m.get("gate2_confidence"),
                "_origin_ts": m.get("ts"),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_audit_promoted(promote_list: list[tuple[str, str, str, dict]], mode: str) -> None:
    if not promote_list:
        return
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for axis, code, alias, m in promote_list:
            row = {
                "ts": ts,
                "alias": alias,
                "axis": axis,
                "code": code,
                "action": "promote_to_vetted",
                "mode": mode,
                "gate2_confidence": m.get("gate2_confidence"),
                "uses": m.get("uses", 0),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rollback(main: dict, cand: dict, codes: list[str]) -> tuple[dict, dict, int]:
    """Move ALL aliases of given codes from main → candidates (testing aid)."""
    main_tier1 = main.setdefault("tier1", {})
    cand_tier1 = cand.setdefault("tier1", {})
    moved = 0
    for axis, code_map in list(main_tier1.items()):
        for code in list(code_map.keys()):
            if code not in codes:
                continue
            aliases = code_map[code]
            cand_axis = cand_tier1.setdefault(axis, {})
            cand_list = cand_axis.setdefault(code, [])
            for a in aliases:
                if a not in cand_list:
                    cand_list.append(a)
                    moved += 1
            code_map.pop(code, None)
        if not code_map:
            main_tier1.pop(axis, None)
    return main, cand, moved


def list_state(cand: dict, meta: dict) -> None:
    print("=" * 70)
    print(f"Current candidate file: {CAND_PATH.relative_to(REPO_ROOT)}")
    print("=" * 70)
    items = enumerate_candidates(cand)
    if not items:
        print("  (empty)")
        return
    print(f"  total candidates: {len(items)}")
    print()
    print(f"  {'axis':18s}  {'code':32s}  {'alias':24s}  uses  conf")
    by_axis: dict[str, list] = defaultdict(list)
    for axis, code, alias in items:
        by_axis[axis].append((code, alias))
    for axis, lst in by_axis.items():
        for code, alias in sorted(lst):
            m = meta.get((axis, code, alias), {})
            uses = m.get("uses", "-")
            conf = m.get("gate2_confidence") or "-"
            conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else str(conf)
            print(f"  {axis:18s}  {code:32s}  {alias:24s}  {str(uses):4s}  {conf_s}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="apply changes (default: dry-run)")
    p.add_argument("--list", action="store_true", help="현재 candidate state만 출력")
    p.add_argument("--auto", action="store_true", help="default mode: uses >= --min-uses + within window")
    p.add_argument("--by-confidence", action="store_true", help="gate2_confidence >= --min-conf")
    p.add_argument("--promote-all", action="store_true", help="all candidates (수동 검토 후)")
    p.add_argument("--alias", type=str, help="단일 promote (--axis, --code 동반)")
    p.add_argument("--axis", type=str, help="단일 promote의 axis")
    p.add_argument("--code", type=str, help="단일 promote의 code")
    p.add_argument("--rollback", nargs="+", help="vetted → candidate (codes 목록)")
    p.add_argument("--min-uses", type=int, default=5)
    p.add_argument("--min-conf", type=float, default=0.85)
    p.add_argument("--days-window", type=int, default=14, help="auto 모드 last_used_at 윈도우")
    args = p.parse_args()
    if args.rollback:
        return args
    mode_flags = [args.auto, args.by_confidence, args.promote_all, bool(args.alias)]
    if sum(mode_flags) == 0:
        args.auto = True  # default
    if sum(mode_flags) > 1 and not (args.alias and (args.auto or args.by_confidence)):
        print("ERROR: multiple mode flags. choose one of --auto/--by-confidence/--promote-all/--alias", file=sys.stderr)
        sys.exit(2)
    return args


def main() -> int:
    args = parse_args()
    main_data = load_json(MAIN_PATH, {"version": "1.0", "tier1": {}})
    cand_data = load_json(CAND_PATH, {"tier1": {}})
    meta = load_meta_latest()

    if args.list:
        list_state(cand_data, meta)
        return 0

    if args.rollback:
        print(f"[rollback] moving {args.rollback} from main → candidates...")
        main_new, cand_new, n = rollback(main_data, cand_data, args.rollback)
        if not args.apply:
            print(f"  would move: {n} aliases")
            print("  re-run with --apply to commit")
            return 0
        write_json_atomic(MAIN_PATH, main_new)
        write_json_atomic(CAND_PATH, cand_new)
        print(f"  moved: {n} aliases")
        return 0

    if args.alias:
        if not (args.axis and args.code):
            print("ERROR: --alias requires --axis AND --code", file=sys.stderr)
            return 2
        items = [(args.axis, args.code, args.alias)]
        promote_list = [(args.axis, args.code, args.alias, meta.get((args.axis, args.code, args.alias), {}))]
        reject_list = []
        mode_label = "single"
    else:
        items = enumerate_candidates(cand_data)
        mode = "promote-all" if args.promote_all else ("by-confidence" if args.by_confidence else "auto")
        promote_list, reject_list = select_promotable(
            items, meta, mode, args.min_uses, args.min_conf, args.days_window
        )
        mode_label = mode

    print("=" * 70)
    print(f"promote_aliases — mode={mode_label}, candidates={len(items)}")
    print("=" * 70)
    print(f"  → promote: {len(promote_list)}")
    for axis, code, alias, m in promote_list:
        conf = m.get("gate2_confidence")
        conf_s = f"{conf:.2f}" if isinstance(conf, (int, float)) else "-"
        print(f"    {axis:18s}  {code:32s}  {alias:24s}  conf={conf_s}  uses={m.get('uses', 0)}")
    if reject_list:
        print(f"  → keep candidate: {len(reject_list)}")
        for axis, code, alias, reason in reject_list:
            print(f"    {axis:18s}  {code:32s}  {alias:24s}  ({reason})")

    if not promote_list:
        print("\n  Nothing to promote.")
        return 0

    if not args.apply:
        print("\n  [dry-run] re-run with --apply to commit.")
        return 0

    new_main, new_cand, moved = apply_promotions(main_data, cand_data, promote_list)
    write_json_atomic(MAIN_PATH, new_main)
    write_json_atomic(CAND_PATH, new_cand)
    append_meta_promoted(promote_list)
    append_audit_promoted(promote_list, mode_label)

    print()
    print(f"  ✅ Promoted {moved} aliases to {MAIN_PATH.name}")
    print(f"     {len(promote_list) - moved} were already in main (dedup skip)")
    print(f"  Meta + audit appended.")
    print(f"\n  ⚠️  Gate 3 regression recommended after promotion:")
    print(f"     cd serving-team/08-app/backend")
    print(f"     .venv/bin/python -u scripts/replay_synthetic_observations.py --output /tmp/replay_post_promote.json")
    print(f"     .venv/bin/python scripts/regression_gate.py /tmp/replay_post_promote.json \\")
    print(f"       --baseline /mnt/c/project/arch-bot/data-team/05-enrichment/runtime-artifacts/replay_baseline_v3.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
