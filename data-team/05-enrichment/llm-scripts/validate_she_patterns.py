#!/usr/bin/env python3
"""Phase 3 Step 2 — SHACL-style validation of Phase 3C SHE patterns.

Checks each SHE pattern (from PG she_catalog where source_model='phase3c/direct-llm-gpt-4.1')
against:
1. features.accident_type ∈ catalog v4 accident_type
2. features.hazardous_agent ∈ catalog v4 hazardous_agent
3. features.work_context ∈ catalog v4 work_context
4. features.ppe_state ∈ known PPE enum
5. features.environmental ∈ known environmental enum
6. features.agent_state ∈ known agent_state enum
7. features.work_activity ∈ known work_activity enum
8. features.temporal_stage ∈ known temporal_stage enum
9. source_sr_ids ⊆ existing PG safety_requirements identifiers

Outputs: runtime-artifacts/phase3_step2_validation_report.json
Optionally: removes invalid patterns from PG (with --remove)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
OUT = ROOT / "data-team/05-enrichment/runtime-artifacts/phase3_step2_validation_report.json"

# Known enums (from existing SHE patterns in PG; not in catalog v4)
PPE_VALID = {"OTHER", "HELMET_MISSING", "HELMET_WORN", "HARNESS_MISSING", "HARNESS_UNTIED",
             "GLOVES_MISSING", "GLOVE_WORN", "MASK_MISSING", "SAFETY_SHOES_MISSING",
             "VEST_MISSING", "GOGGLES_MISSING", "FACE_SHIELD_MISSING"}
ENV_VALID = {"OTHER", "WET_SURFACE", "HIGH_ELEVATION", "EXTREME_TEMPERATURE", "NARROW_SPACE",
             "DARK", "DUSTY", "VENTILATION_POOR", "NOISE_HIGH", "VIBRATION", "OUTDOOR"}
AGENT_STATE_VALID = {"OTHER", "LIVE_VOLTAGE", "FLAMMABLE_EXPOSED", "PRESSURIZED", "MOVING",
                     "STATIC", "HOT", "COLD", "CORROSIVE", "TOXIC"}
TEMPORAL_VALID = {"BEFORE_WORK", "DURING_WORK", "AFTER_WORK"}
WORK_ACT_VALID = {"OTHER", "WELDING", "CLEANING", "LIFTING", "CUTTING", "MIXING",
                  "INSPECTION", "INSTALLATION", "TRANSPORT", "OPERATION", "REPAIR",
                  "ASSEMBLY", "PACKAGING", "PROCESSING"}


def query_pg():
    from sqlalchemy import create_engine, text
    db = os.environ.get("DATABASE_URL", "postgresql://kosha:1229@localhost:5432/kosha")
    eng = create_engine(db)
    # Get Phase 3C she_catalog patterns
    she_patterns = []
    sr_universe = set()
    with eng.connect() as conn:
        rows = conn.execute(text("""
            SELECT she_id, name, features, source_sr_ids
            FROM she_catalog
            WHERE source_model = 'phase3c/direct-llm-gpt-4.1'
        """))
        for r in rows:
            she_patterns.append({
                "she_id": r[0], "name": r[1],
                "features": r[2] if isinstance(r[2], dict) else json.loads(r[2]) if r[2] else {},
                "source_sr_ids": r[3] if isinstance(r[3], list) else json.loads(r[3]) if r[3] else [],
            })
        # All SR identifiers
        sr_rows = conn.execute(text("SELECT identifier FROM safety_requirements"))
        sr_universe = {r[0] for r in sr_rows}
    eng.dispose()
    return she_patterns, sr_universe


def validate_pattern(p: dict, catalog: dict, sr_universe: set) -> tuple[list[str], list[str]]:
    """Returns (warnings, errors). errors are blocking; warnings are notes."""
    warnings = []
    errors = []
    f = p.get("features") or {}
    cat_codes = {axis: set(info.get("codes", {}).keys()) for axis, info in catalog.get("axes", {}).items()}

    def chk(field, valid_set, severity="error"):
        v = f.get(field, "")
        if v and v != "OTHER" and v not in valid_set:
            msg = f"features.{field}='{v}' not in valid set"
            (errors if severity == "error" else warnings).append(msg)

    chk("accident_type", cat_codes.get("accident_type", set()))
    chk("hazardous_agent", cat_codes.get("hazardous_agent", set()))
    chk("work_context", cat_codes.get("work_context", set()))
    chk("ppe_state", PPE_VALID, "warning")
    chk("environmental", ENV_VALID, "warning")
    chk("agent_state", AGENT_STATE_VALID, "warning")
    chk("temporal_stage", TEMPORAL_VALID, "warning")
    chk("work_activity", WORK_ACT_VALID, "warning")

    sr_ids = p.get("source_sr_ids") or []
    invalid_srs = [s for s in sr_ids if s not in sr_universe]
    if invalid_srs:
        warnings.append(f"source_sr_ids invalid: {invalid_srs[:5]}")

    return warnings, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true", help="Delete error-level invalid patterns from PG")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    patterns, sr_universe = query_pg()
    print(f"loaded {len(patterns)} Phase 3C SHE patterns")
    print(f"SR universe: {len(sr_universe)} identifiers")

    valid = []
    invalid = []
    warnings_total = Counter()
    errors_total = Counter()
    for p in patterns:
        warnings, errors = validate_pattern(p, catalog, sr_universe)
        for w in warnings:
            warnings_total[w.split(":")[0] if ":" in w else w[:30]] += 1
        for e in errors:
            errors_total[e.split("'")[0] if "'" in e else e[:30]] += 1
        if errors:
            invalid.append({"she_id": p["she_id"], "name": p["name"][:60],
                            "errors": errors, "warnings": warnings})
        else:
            valid.append({"she_id": p["she_id"], "warnings": warnings})

    print(f"\n=== Validation Results ===")
    print(f"  valid patterns           : {len(valid)} ({100*len(valid)/max(len(patterns),1):.1f}%)")
    print(f"  invalid (error-blocking) : {len(invalid)} ({100*len(invalid)/max(len(patterns),1):.1f}%)")
    print(f"\nError types (top 10):")
    for k, n in errors_total.most_common(10):
        print(f"  [{n}] {k}")
    print(f"\nWarning types (top 10):")
    for k, n in warnings_total.most_common(10):
        print(f"  [{n}] {k}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_patterns": len(patterns),
            "valid": len(valid),
            "invalid_error": len(invalid),
            "error_types": dict(errors_total),
            "warning_types": dict(warnings_total),
        },
        "invalid_patterns": invalid[:50],  # sample
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT.relative_to(ROOT)}")

    if args.remove and invalid and not args.dry_run:
        from sqlalchemy import create_engine, text
        db = os.environ.get("DATABASE_URL", "postgresql://kosha:1229@localhost:5432/kosha")
        eng = create_engine(db)
        with eng.connect() as conn:
            ids = [p["she_id"] for p in invalid]
            # Delete from she_sr_mapping first (FK cascade)
            conn.execute(text("DELETE FROM she_sr_mapping WHERE she_id = ANY(:ids)"), {"ids": ids})
            conn.execute(text("DELETE FROM she_catalog WHERE she_id = ANY(:ids)"), {"ids": ids})
            conn.commit()
        eng.dispose()
        print(f"\nRemoved {len(invalid)} invalid patterns from PG.")


if __name__ == "__main__":
    main()
