#!/usr/bin/env python3
"""Phase G — Sample query equality test (JSON vs PG path).

각 sprint에서 적재 후 backend service 동작 일치 검증.
G.1: shadow_reasoner.shadow_validate(industry, codes) → JSON 결과 == PG 결과

사용:
  PYTHONIOENCODING=utf-8 DATABASE_URL=... python sample_query_equality.py
  python sample_query_equality.py --sprint g1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _setup_path():
    here = Path(__file__).resolve()
    # .../serving-team/07-materialization/validation-scripts/this.py
    # parents[3] = repo root
    repo = here.parents[3]
    backend = repo / "serving-team" / "08-app" / "backend"
    sys.path.insert(0, str(backend))


_setup_path()


def test_g1_shadow_reasoner() -> tuple[int, int, list[dict]]:
    """G.1: shadow_reasoner 동등성 — PG vs JSON.

    Returns: (passed, total, mismatches)
    """
    import importlib
    from app.services import shadow_reasoner

    # Build 10 sample test cases
    samples = [
        ("건설", ["B-M-32-2026", "X-61-2013", "A-G-4-2025"]),
        ("건설", []),  # empty
        ("건설", ["NONEXISTENT-CODE"]),
        ("미지", ["B-M-32-2026"]),  # unmapped industry
        ("일반", ["A-G-4-2025"]),
        ("건설", ["B-M-32-2026"] * 5),  # duplicate codes
        ("건설", ["B-M-32-2026", "X-61-2013"]),
        ("일반", ["B-M-32-2026"]),
        ("건설", ["B-M-32-2026", "X-61-2013", "A-G-4-2025", "A-101-2018"]),
        ("건설", ["A-G-4-2025"]),
    ]

    passed = 0
    mismatches = []

    for ind, codes in samples:
        # PG result
        shadow_reasoner.reset_cache()
        pg_result = sorted(
            shadow_reasoner.shadow_validate(ind, codes),
            key=lambda r: (r["guide_code"], r["guide_domain"]),
        )

        # JSON fallback result: monkey-patch _load_axioms_from_pg to return None
        shadow_reasoner.reset_cache()
        original_pg_loader = shadow_reasoner._load_axioms_from_pg
        try:
            shadow_reasoner._load_axioms_from_pg = lambda: None
            json_result = sorted(
                shadow_reasoner.shadow_validate(ind, codes),
                key=lambda r: (r["guide_code"], r["guide_domain"]),
            )
        finally:
            shadow_reasoner._load_axioms_from_pg = original_pg_loader
            shadow_reasoner.reset_cache()

        # Compare keys (guide_code + domain)
        pg_keys = {(r["guide_code"], r["guide_domain"]) for r in pg_result}
        json_keys = {(r["guide_code"], r["guide_domain"]) for r in json_result}

        if pg_keys == json_keys:
            passed += 1
            print(f"  [PASS] industry={ind!r} codes={len(codes)} → {len(pg_result)} rejects (match)")
        else:
            mismatches.append({
                "industry": ind,
                "codes": codes,
                "pg_only": sorted(pg_keys - json_keys),
                "json_only": sorted(json_keys - pg_keys),
            })
            print(f"  [FAIL] industry={ind!r} codes={len(codes)}")
            print(f"    PG only:   {sorted(pg_keys - json_keys)}")
            print(f"    JSON only: {sorted(json_keys - pg_keys)}")

    return passed, len(samples), mismatches


def test_g2_guide_profile() -> tuple[int, int, list[dict]]:
    """G.2: guide_domain_profile 동등성 — PG vs JSON.

    Returns: (passed, total, mismatches)
    """
    from app.services import guide_domain_profile as gdp

    samples = [
        "A-1-2018", "A-104-2018", "B-1-2018", "B-M-32-2026", "X-61-2013",
        "A-G-4-2025", "A-G-20-2026", "A-101-2018", "A-102-2018", "A-103-2018",
    ]
    passed = 0
    mismatches = []

    for code in samples:
        # PG result
        gdp._load_manual_profiles.cache_clear()
        pg_profile = gdp.get_guide_domain_profile(code)

        # JSON fallback: monkey-patch
        gdp._load_manual_profiles.cache_clear()
        original_pg = gdp._load_profiles_from_pg
        try:
            gdp._load_profiles_from_pg = lambda: None
            json_profile = gdp.get_guide_domain_profile(code)
        finally:
            gdp._load_profiles_from_pg = original_pg
            gdp._load_manual_profiles.cache_clear()

        # Compare core fields (profile_level + domain_family + procedure_role)
        if not pg_profile and not json_profile:
            passed += 1
            print(f"  [PASS] {code}: both None (no profile)")
            continue
        if not pg_profile or not json_profile:
            mismatches.append({"code": code, "pg": bool(pg_profile), "json": bool(json_profile)})
            print(f"  [FAIL] {code}: PG={bool(pg_profile)} JSON={bool(json_profile)}")
            continue

        core_fields = ["profile_level", "domain_family", "procedure_role", "photo_matchability"]
        diff_fields = [f for f in core_fields if pg_profile.get(f) != json_profile.get(f)]
        if not diff_fields:
            passed += 1
            print(f"  [PASS] {code}: profile_level={pg_profile.get('profile_level')} (core fields match)")
        else:
            mismatches.append({"code": code, "diff_fields": diff_fields,
                               "pg_values": {f: pg_profile.get(f) for f in diff_fields},
                               "json_values": {f: json_profile.get(f) for f in diff_fields}})
            print(f"  [FAIL] {code}: diff in {diff_fields}")

    return passed, len(samples), mismatches


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sprint", choices=("g1", "g2", "g3", "g4", "all"), default="g1")
    args = ap.parse_args()

    print(f"=== Phase G Sample Query Equality — Sprint {args.sprint.upper()} ===\n")

    total_passed = 0
    total_count = 0
    all_mismatches = []

    if args.sprint in ("g1", "all"):
        print(f"--- G.1: shadow_reasoner (PG vs JSON) ---")
        p, t, m = test_g1_shadow_reasoner()
        total_passed += p
        total_count += t
        all_mismatches.extend(m)
        print(f"  → {p}/{t} PASS")

    if args.sprint in ("g2", "all"):
        print(f"\n--- G.2: guide_domain_profile (PG vs JSON) ---")
        p, t, m = test_g2_guide_profile()
        total_passed += p
        total_count += t
        all_mismatches.extend(m)
        print(f"  → {p}/{t} PASS")

    # G.3-4 placeholders (future sprints)
    if args.sprint in ("g3", "g4", "all"):
        if args.sprint != "all":
            print(f"\n--- G.{args.sprint[1]}: (not yet implemented) ---")

    print(f"\n=== Summary: {total_passed}/{total_count} PASS ===")
    if all_mismatches:
        print(f"Mismatches: {len(all_mismatches)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
