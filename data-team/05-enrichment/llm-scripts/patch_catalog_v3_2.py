#!/usr/bin/env python3
"""F.2 Day 1 — catalog v3.1 → v3.2: ppe_state/environmental axis 신설 + 161 후보 재검토.

v3.1에서 deferred 됐던 사항 정리:
- axes 신설: ppe_state (보호구 상태), environmental (환경 조건)
- 161 new_subcode_candidates 전체 재검토 (이번엔 conf ≥ 0.7로 완화)
  · v3.1에서는 conf ≥ 0.8 + 3 axis만 → 94 codes 등재
  · v3.2에서는 conf ≥ 0.7 + 5 axis 모두 → 더 많이 등재
- 이미 v3.1에 등재된 codes는 dedup으로 자동 skip

정책 (patch_catalog_v3_1.py 그대로 + 확장):
- 각 신규 code는 main code로 등재 (sub=[], label=Korean from_code)
- catalog version 3.1 → 3.2, _v3_2_changelog 메타 추가
- 원본 백업: risk_feature_catalog.v3.1.backup.json
- atomic write (.tmp + replace)

ENV: 없음

사용:
  python patch_catalog_v3_2.py --dry-run    # 미리보기
  python patch_catalog_v3_2.py              # apply (with auto-backup)
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
BACKUP_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.v3.1.backup.json"

# F.2 변경: 5 axes 허용 (ppe_state, environmental 신설)
ALLOWED_AXES = {"accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"}
NEW_AXIS_LABELS = {
    "ppe_state": "보호구 상태",
    "environmental": "환경 조건",
}
MIN_CONFIDENCE = 0.7  # v3.2는 v3.1(0.8)보다 적극적 채택


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def collect_existing_codes(catalog: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for axis, axis_def in catalog.get("axes", {}).items():
        if not isinstance(axis_def, dict):
            continue
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


def ensure_axes(catalog: dict) -> int:
    """Add ppe_state, environmental axes if missing. Return # added."""
    axes = catalog.setdefault("axes", {})
    added = 0
    for axis_name, label in NEW_AXIS_LABELS.items():
        if axis_name not in axes:
            axes[axis_name] = {
                "label": label,
                "codes": {},
                "_source": "f2_taxonomy_discovery",
                "_added_at": datetime.now(timezone.utc).isoformat(),
            }
            added += 1
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="show plan without writing")
    parser.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE)
    args = parser.parse_args()

    catalog = load_catalog()
    cur_version = catalog.get("version", "?")
    candidates = load_candidates()

    print("=" * 70)
    print(f"patch_catalog_v3_2 — current version: {cur_version}")
    print(f"  candidates loaded: {len(candidates)}")
    print(f"  filter: axis ∈ {sorted(ALLOWED_AXES)} (5 axes), conf ≥ {args.min_confidence}")
    print("=" * 70)

    # Step 1: ensure ppe_state/environmental axes exist
    if args.dry_run:
        new_axes_to_add = [ax for ax in NEW_AXIS_LABELS if ax not in catalog.get("axes", {})]
        print(f"  [Step 1] would add {len(new_axes_to_add)} new axes: {new_axes_to_add}")
    else:
        n_axes = ensure_axes(catalog)
        print(f"  [Step 1] added {n_axes} new axes (ppe_state, environmental)")

    existing = collect_existing_codes(catalog)

    # Step 2: filter candidates
    skip_reasons: Counter = Counter()
    accepted_pairs: dict[tuple[str, str], dict] = {}
    for e in candidates:
        axis = e["correct_axis"]
        code = (e.get("suggested_code") or "").strip()
        conf = float(e.get("confidence", 0.0))
        label = e["from_code"]
        if axis not in ALLOWED_AXES:
            skip_reasons[f"axis_unknown:{axis}"] += 1
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
        if key in accepted_pairs and accepted_pairs[key]["confidence"] >= conf:
            continue
        accepted_pairs[key] = {
            "label": label,
            "confidence": conf,
            "reason": e.get("reason", ""),
            "from_axis": e.get("from_axis"),
            "from_code": e.get("from_code"),
        }

    print()
    print(f"  [Step 2] candidates → catalog filter:")
    print(f"    accepted: {len(accepted_pairs)}")
    print(f"    skipped breakdown:")
    for r, n in skip_reasons.most_common():
        print(f"      {r:35s}: {n}")
    print()

    if not accepted_pairs:
        print("Nothing to patch (only axis additions, if any).")
        if args.dry_run:
            return 0

    # Group by axis for printout
    by_axis: dict[str, list] = defaultdict(list)
    for (axis, code), meta in accepted_pairs.items():
        by_axis[axis].append((code, meta))

    for axis in sorted(by_axis):
        lst = by_axis[axis]
        lst.sort(key=lambda x: -x[1]["confidence"])
        marker = " ⭐" if axis in NEW_AXIS_LABELS else ""
        print(f"  [{axis}{marker}] will add {len(lst)} codes (top 5):")
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
            "_source": "f2_taxonomy_discovery",
            "_confidence": round(meta["confidence"], 3),
            "_added_at": datetime.now(timezone.utc).isoformat(),
        }

    catalog["version"] = "3.2"
    base_desc = catalog.get("description", "")
    if "v3.2" not in base_desc:
        catalog["description"] = base_desc + f" | v3.2: +{len(accepted_pairs)} codes + 2 axes (F.2 Taxonomy Discovery)"
    catalog["_v3_2_changelog"] = {
        "patched_at": datetime.now(timezone.utc).isoformat(),
        "from_version": cur_version,
        "source": "data-team/05-enrichment/runtime-artifacts/new_subcode_candidates.jsonl",
        "filter": f"axis ∈ {sorted(ALLOWED_AXES)} (5 axes), conf ≥ {args.min_confidence}",
        "added_codes": len(accepted_pairs),
        "added_axes": list(NEW_AXIS_LABELS.keys()),
        "skipped_count": sum(skip_reasons.values()),
        "by_axis": {ax: len(lst) for ax, lst in by_axis.items()},
    }

    # Atomic write
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CATALOG_PATH)

    print()
    print("=" * 70)
    print(f"Patched catalog v{cur_version} → v3.2 successfully.")
    print(f"  added codes : {len(accepted_pairs)}")
    print(f"  added axes  : {list(NEW_AXIS_LABELS.keys())} (each only if not pre-existing)")
    print(f"  backup      : {BACKUP_PATH.relative_to(REPO_ROOT)}")
    print(f"  rollback    : cp {BACKUP_PATH.name} risk_feature_catalog.json")
    print()
    print("⚠️  Gate 3 regression 필수:")
    print("    make f1-regression  # 모든 metric delta ≤ 0.02")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
