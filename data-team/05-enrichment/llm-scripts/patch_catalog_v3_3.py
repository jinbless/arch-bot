#!/usr/bin/env python3
"""F.2 Day 2 — catalog v3.2 → v3.3: hardcoded matcher constants + synthetic-frequent codes 등재.

Day 2 발견: catalog v3.2가 ppe_state/environmental axis는 있으나 codes 부족.
- `she_matcher.py` UNSAFE_PPE_STATES (8) + UNSAFE_ENVIRONMENTAL_STATES (8) + NORMAL_PPE_STATES (8) = 24 hardcoded
- `synthetic_observations_v*.jsonl` ppe_states (87 unique) + environmental (318 unique) 사용
- 이 codes들이 catalog에 없으면 SHE pattern matching/normalization 실패

정책 (v3.2 patch와 동일 + 신규 source):
- Source 1: hardcoded matcher constants (UNSAFE_PPE/UNSAFE_ENV/NORMAL_PPE) — 24 codes, 자동 등재
- Source 2: synthetic frequent codes — UPPER_SNAKE_CASE format + freq >= MIN_FREQ + not 'OTHER'
  · ppe_state freq >= 3
  · environmental freq >= 3
- 백업: risk_feature_catalog.v3.2.backup.json
- atomic write

ENV: 없음
사용:
  python patch_catalog_v3_3.py --dry-run    # 미리보기
  python patch_catalog_v3_3.py              # apply (with auto-backup)
  python patch_catalog_v3_3.py --min-freq 5 # 더 엄격
"""
from __future__ import annotations

import argparse
import json
import re
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
SYNTH_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
CATALOG_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
BACKUP_PATH = REPO_ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.v3.2.backup.json"

# Hardcoded matcher constants (she_matcher.py line 42-73) - source of truth
MATCHER_PPE_STATES = {
    # UNSAFE
    "HELMET_MISSING": "헬멧 미착용",
    "HARNESS_MISSING": "안전대 미착용",
    "HARNESS_UNTIED": "안전대 미체결",
    "GLOVES_MISSING": "장갑 미착용",
    "MASK_MISSING": "마스크 미착용",
    "GOGGLES_MISSING": "보안경 미착용",
    "SAFETY_SHOES_MISSING": "안전화 미착용",
    "VEST_MISSING": "안전조끼 미착용",
    # NORMAL
    "HELMET_WORN": "헬멧 착용",
    "HARNESS_WORN": "안전대 착용",
    "HARNESS_TIED": "안전대 체결",
    "GLOVE_WORN": "장갑 착용",
    "MASK_WORN": "마스크 착용",
    "GOGGLES_WORN": "보안경 착용",
    "VEST_WORN": "안전조끼 착용",
    "SAFETY_SHOES_WORN": "안전화 착용",
}
MATCHER_ENV_STATES = {
    # UNSAFE
    "WET_SURFACE": "젖은 표면",
    "OIL_CONTAMINATION": "유류 오염",
    "LOW_LIGHT": "조도 부족",
    "CLUTTERED": "정리 미흡",
    "WINDY_WEATHER": "강풍",
    "EXTREME_TEMPERATURE": "극한 온도",
    "NARROW_SPACE": "협소 공간",
    "UNSTABLE_GROUND": "불안정 지반",
}

UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
EXCLUDE_CODES = {"OTHER", "GLOVE_WON"}  # generic 또는 typo


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


def aggregate_synthetic_codes() -> tuple[Counter, Counter]:
    ppe: Counter = Counter()
    env: Counter = Counter()
    for p in sorted(SYNTH_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            exp = r.get("expected_features") or {}
            for code in (exp.get("ppe_states") or []):
                if isinstance(code, str):
                    ppe[code.strip()] += 1
            for code in (exp.get("environmental") or []):
                if isinstance(code, str):
                    env[code.strip()] += 1
    return ppe, env


def select_synthetic_to_add(
    counter: Counter, existing: set[str], min_freq: int
) -> dict[str, int]:
    """Filter: UPPER_SNAKE_CASE + freq >= min_freq + not in existing + not excluded."""
    out: dict[str, int] = {}
    for code, n in counter.items():
        if code in existing or code in EXCLUDE_CODES:
            continue
        if n < min_freq:
            continue
        if not UPPER_SNAKE_RE.match(code):
            continue  # skip lowercase free-form
        out[code] = n
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-freq", type=int, default=3)
    args = parser.parse_args()

    catalog = load_catalog()
    cur_version = catalog.get("version", "?")
    existing = collect_existing_codes(catalog)

    print("=" * 70)
    print(f"patch_catalog_v3_3 — current version: {cur_version}")
    print(f"  source 1: hardcoded matcher constants ({len(MATCHER_PPE_STATES)} ppe + {len(MATCHER_ENV_STATES)} env)")
    print(f"  source 2: synthetic UPPER_SNAKE codes, freq >= {args.min_freq}")
    print("=" * 70)

    # Source 1: hardcoded matcher constants
    to_add_ppe: dict[str, dict] = {}
    to_add_env: dict[str, dict] = {}
    existing_ppe = existing.get("ppe_state", set())
    existing_env = existing.get("environmental", set())

    for code, label in MATCHER_PPE_STATES.items():
        if code not in existing_ppe:
            to_add_ppe[code] = {"label": label, "_source": "she_matcher_hardcoded", "_freq": None}
    for code, label in MATCHER_ENV_STATES.items():
        if code not in existing_env:
            to_add_env[code] = {"label": label, "_source": "she_matcher_hardcoded", "_freq": None}

    print(f"\n  [Source 1] hardcoded matcher → catalog:")
    print(f"    ppe_state: {len(to_add_ppe)} (existing {len(existing_ppe)})")
    print(f"    environmental: {len(to_add_env)} (existing {len(existing_env)})")

    # Source 2: synthetic frequent
    ppe_counter, env_counter = aggregate_synthetic_codes()
    ppe_sel = select_synthetic_to_add(ppe_counter, existing_ppe | set(to_add_ppe.keys()), args.min_freq)
    env_sel = select_synthetic_to_add(env_counter, existing_env | set(to_add_env.keys()), args.min_freq)

    for code, freq in ppe_sel.items():
        to_add_ppe[code] = {"label": code.replace("_", " ").title(), "_source": "synthetic_frequent", "_freq": freq}
    for code, freq in env_sel.items():
        to_add_env[code] = {"label": code.replace("_", " ").title(), "_source": "synthetic_frequent", "_freq": freq}

    print(f"\n  [Source 2] synthetic frequent (freq >= {args.min_freq}) → catalog:")
    print(f"    ppe_state: +{len(ppe_sel)} (total to add: {len(to_add_ppe)})")
    print(f"    environmental: +{len(env_sel)} (total to add: {len(to_add_env)})")

    print(f"\n  PPE codes to add ({len(to_add_ppe)}):")
    for code, meta in sorted(to_add_ppe.items(), key=lambda kv: (kv[1]["_source"], -(kv[1]["_freq"] or 999999), kv[0])):
        src = meta["_source"][:25]
        freq = f"freq={meta['_freq']}" if meta["_freq"] else "hardcoded"
        print(f"    {code:38s} ({src}, {freq}) — {meta['label']}")

    print(f"\n  ENVIRONMENTAL codes to add ({len(to_add_env)}):")
    for code, meta in sorted(to_add_env.items(), key=lambda kv: (kv[1]["_source"], -(kv[1]["_freq"] or 999999), kv[0])):
        src = meta["_source"][:25]
        freq = f"freq={meta['_freq']}" if meta["_freq"] else "hardcoded"
        print(f"    {code:38s} ({src}, {freq}) — {meta['label']}")

    if args.dry_run:
        print("\n[dry-run] no changes written.")
        return 0

    # Backup
    print(f"\nBacking up to {BACKUP_PATH.relative_to(REPO_ROOT)}...")
    BACKUP_PATH.write_text(CATALOG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    # Patch
    axes = catalog["axes"]
    for code, meta in to_add_ppe.items():
        axes["ppe_state"]["codes"][code] = {
            "label": meta["label"],
            "sub": [],
            "_source": meta["_source"],
            "_freq": meta["_freq"],
            "_added_at": datetime.now(timezone.utc).isoformat(),
        }
    for code, meta in to_add_env.items():
        axes["environmental"]["codes"][code] = {
            "label": meta["label"],
            "sub": [],
            "_source": meta["_source"],
            "_freq": meta["_freq"],
            "_added_at": datetime.now(timezone.utc).isoformat(),
        }

    catalog["version"] = "3.3"
    base_desc = catalog.get("description", "")
    if "v3.3" not in base_desc:
        catalog["description"] = base_desc + f" | v3.3: +{len(to_add_ppe)+len(to_add_env)} ppe/env codes (matcher hardcoded + synthetic frequent)"
    catalog["_v3_3_changelog"] = {
        "patched_at": datetime.now(timezone.utc).isoformat(),
        "from_version": cur_version,
        "source_1": "she_matcher.py hardcoded constants (UNSAFE_PPE + UNSAFE_ENV + NORMAL_PPE)",
        "source_2": f"synthetic UPPER_SNAKE freq >= {args.min_freq}",
        "added_ppe_state": len(to_add_ppe),
        "added_environmental": len(to_add_env),
        "excluded": list(EXCLUDE_CODES),
    }

    # Atomic write
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CATALOG_PATH)

    print()
    print("=" * 70)
    print(f"Patched catalog v{cur_version} → v3.3 successfully.")
    print(f"  added ppe_state    : {len(to_add_ppe)}")
    print(f"  added environmental: {len(to_add_env)}")
    print(f"  backup             : {BACKUP_PATH.relative_to(REPO_ROOT)}")
    print()
    print("⚠️  Gate 3 regression 필수:")
    print("    make f1-regression  # 모든 metric delta ≤ 0.02")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
