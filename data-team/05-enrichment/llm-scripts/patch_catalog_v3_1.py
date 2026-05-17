#!/usr/bin/env python3
"""F.1 후속 — catalog v3.0 → v3.1: 신규 main code 추가 (Sonnet 4.6 발견).

`new_subcode_candidates.jsonl`(F.1 recovery 산출)의 신규 enum 후보 중
- axis ∈ {accident_type, hazardous_agent, work_context}  (Phase 1, 기존 3 axis만)
- confidence ≥ 0.8                                          (Sonnet 자체 신뢰도)
- catalog 미존재 (dedup)
필터 통과한 후보를 catalog v3.1의 신규 main code로 등재.

추가 정책:
- 각 신규 code는 main code로 등재 (sub 없음, label = Korean from_code)
- catalog version 3.0 → 3.1, changelog 메타 추가
- 원본 백업: risk_feature_catalog.v3.0.backup.json
- atomic write (.tmp + replace)

Phase 2 (별도): ppe_state / environmental axis 자체 신설 — catalog 구조 변경, 별도 plan.

사용:
  python patch_catalog_v3_1.py                # apply (with auto-backup)
  python patch_catalog_v3_1.py --dry-run      # 미리보기만
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
SUBCODES_PATH = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "new_subcode_candidates.jsonl"
CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
BACKUP_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.v3.0.backup.json"

ALLOWED_AXES = {"accident_type", "hazardous_agent", "work_context"}
MIN_CONFIDENCE = 0.8


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def collect_existing_codes(catalog: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for axis, axis_def in catalog.get("axes", {}).items():
        for code, code_def in (axis_def.get("codes") or {}).items():
            out[axis].add(code)
            if isinstance(code_def, dict):
                for sub in (code_def.get("sub") or []) or []:
                    if isinstance(sub, str):
                        out[axis].add(sub)
    return out


def load_candidates() -> list[dict]:
    if not SUBCODES_PATH.is_file():
        return []
    out: list[dict] = []
    with SUBCODES_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="show plan without writing")
    parser.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE)
    args = parser.parse_args()

    catalog = load_catalog()
    cur_version = catalog.get("version", "?")
    existing = collect_existing_codes(catalog)
    candidates = load_candidates()

    print("=" * 70)
    print(f"patch_catalog_v3_1 — current version: {cur_version}")
    print(f"  candidates loaded: {len(candidates)}")
    print(f"  filter: axis ∈ {sorted(ALLOWED_AXES)}, conf ≥ {args.min_confidence}")
    print("=" * 70)

    # Filter
    skip_reasons: Counter = Counter()
    accepted_pairs: dict[tuple[str, str], dict] = {}
    for e in candidates:
        axis = e["correct_axis"]
        code = (e.get("suggested_code") or "").strip()
        conf = float(e.get("confidence", 0.0))
        label = e["from_code"]
        if axis not in ALLOWED_AXES:
            skip_reasons[f"axis_skip:{axis}"] += 1
            continue
        if conf < args.min_confidence:
            skip_reasons["low_confidence"] += 1
            continue
        if not code:
            skip_reasons["no_suggested_code"] += 1
            continue
        if code in existing.get(axis, set()):
            skip_reasons["already_in_catalog"] += 1
            continue
        key = (axis, code)
        # dedup within candidates — keep highest conf
        if key in accepted_pairs and accepted_pairs[key]["confidence"] >= conf:
            continue
        accepted_pairs[key] = {
            "label": label,
            "confidence": conf,
            "reason": e.get("reason", ""),
            "from_axis": e.get("from_axis"),
            "from_code": e.get("from_code"),
        }

    # Print summary
    print(f"  accepted (will be added)  : {len(accepted_pairs)}")
    print(f"  skipped breakdown:")
    for r, n in skip_reasons.most_common():
        print(f"    {r:35s}: {n}")
    print()

    if not accepted_pairs:
        print("Nothing to patch.")
        return 0

    # Group by axis for printout
    by_axis: dict[str, list] = defaultdict(list)
    for (axis, code), meta in accepted_pairs.items():
        by_axis[axis].append((code, meta))

    for axis, lst in by_axis.items():
        lst.sort(key=lambda x: -x[1]["confidence"])
        print(f"  [{axis}] will add {len(lst)} new main codes (top 5):")
        for code, meta in lst[:5]:
            print(f"    conf={meta['confidence']:.2f}  {code:35s}  label={meta['label']!r}")
        if len(lst) > 5:
            print(f"    ... {len(lst) - 5} more")
        print()

    if args.dry_run:
        print("[dry-run] no changes written.")
        return 0

    # Backup
    print(f"Backing up to {BACKUP_PATH.relative_to(REPO_ROOT)}...")
    BACKUP_PATH.write_text(CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    # Patch
    for (axis, code), meta in accepted_pairs.items():
        catalog["axes"][axis]["codes"][code] = {
            "label": meta["label"],
            "sub": [],
            "_source": "f1_recovery_sonnet_4_6",
            "_confidence": round(meta["confidence"], 3),
            "_added_at": datetime.now(timezone.utc).isoformat(),
        }

    catalog["version"] = "3.1"
    base_desc = catalog.get("description", "")
    if "v3.1" not in base_desc:
        catalog["description"] = base_desc + f" | v3.1: +{len(accepted_pairs)} main codes (F.1 recovery, Sonnet 4.6)"
    catalog["_v3_1_changelog"] = {
        "patched_at": datetime.now(timezone.utc).isoformat(),
        "from_version": cur_version,
        "source": "data-team/05-enrichment/runtime-artifacts/new_subcode_candidates.jsonl",
        "filter": f"axis ∈ {sorted(ALLOWED_AXES)}, conf ≥ {args.min_confidence}",
        "added_count": len(accepted_pairs),
        "skipped_count": sum(skip_reasons.values()),
        "deferred_axes": ["ppe_state", "environmental"],
        "by_axis": {ax: len(lst) for ax, lst in by_axis.items()},
    }

    # Atomic write
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CATALOG_PATH)

    print()
    print("=" * 70)
    print(f"Patched catalog v{cur_version} → v3.1 successfully.")
    print(f"  added : {len(accepted_pairs)} new main codes")
    print(f"  backup: {BACKUP_PATH.relative_to(REPO_ROOT)}")
    print(f"  rollback: cp {BACKUP_PATH.name} risk_feature_catalog.json")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
