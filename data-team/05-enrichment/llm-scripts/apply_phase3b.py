#!/usr/bin/env python3
"""Phase 3B — Apply audit decisions to catalog v4 + aliases + Phase 3D mapping.

Policies (user-approved 추천 default):
- Q1: NEW_CODE_NEEDED freq>=5 채택 (~200)
- Q2: WRONG_AXIS — target axis ∈ {accident_type, hazardous_agent, work_context} 만 적용,
  LLM이 제안한 새 axis (accident_cause 등)는 SKIP (synthetic 변환 시 DROP)
- Q3: HUMAN queue freq>=3 만 user 검토 대상 (이 스크립트는 처리 안 함; 별도 surfacing)
- Q4: SUB_CLASS_OF 181건 모두 catalog `sub` 계층 + OWL subClassOf
- Q5: EXISTING_EQUIV 59건 모두 alias 추가

Outputs:
- serving-team/.../risk_feature_catalog.json (v4: +NEW codes + sub hierarchies)
- serving-team/.../risk_feature_aliases.json (+EXISTING + SUB aliases)
- ontology-team/.../kosha-ontology-v3.owl.patch.ttl (subClassOf 추가용 patch)
- data-team/05-enrichment/runtime-artifacts/synthetic_ko_to_en_final.json
  (Phase 3D 입력: 모든 KO code → EN code 또는 DROP)
- data-team/05-enrichment/runtime-artifacts/phase3b_apply_audit.json
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
AUDIT_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_v1.json"
CATALOG_PATH = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
ALIASES_PATH = ROOT / "serving-team/08-app/backend/app/data/risk_feature_aliases.json"
PATCH_TTL_PATH = ROOT / "ontology-team/06-reasoning/ontology/kosha-ontology-v3-subclass-patch.ttl"
FINAL_MAPPING = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_ko_to_en_final.json"
APPLY_AUDIT = ROOT / "data-team/05-enrichment/runtime-artifacts/phase3b_apply_audit.json"

VALID_CATALOG_AXES = {"accident_type", "hazardous_agent", "work_context"}
ENUM_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
NEW_CODE_MIN_FREQ = 5
HUMAN_REVIEW_MIN_FREQ = 3


def normalize_en_code(s: str) -> str:
    """LLM 출력의 잡음 정제: 비-ASCII 제거, UPPER_SNAKE_CASE 강제."""
    if not isinstance(s, str):
        return ""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s.strip())
    s = re.sub(r"_+", "_", s).strip("_").upper()
    return s if ENUM_PATTERN.match(s) else ""


def axis_from_synth(axis_synth: str) -> str:
    """synthetic plural axis → singular catalog axis."""
    return {
        "accident_types": "accident_type",
        "hazardous_agents": "hazardous_agent",
        "work_contexts": "work_context",
        "ppe_states": "ppe_state",
        "ppe_missing": "ppe_missing",
        "environmental": "environmental",
    }.get(axis_synth, axis_synth)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="실제 파일 작성")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True

    print(f"mode: {'DRY' if args.dry_run else 'APPLY'}")
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    aliases = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))

    results = audit["results"]
    print(f"loaded audit: {len(results)} decisions")

    # === Decision categorization ===
    new_codes: list[dict] = []          # to add to catalog
    sub_codes: list[dict] = []          # to add as sub-class
    existing_aliases: list[dict] = []   # to add as alias to existing code
    reloc_applies: list[dict] = []      # WRONG_AXIS within valid catalog axes
    reloc_skips: list[dict] = []        # WRONG_AXIS to non-catalog axis → DROP
    drops: list[dict] = []              # NOT_A_CODE
    human_freq_high: list[dict] = []    # HUMAN with freq>=3
    human_freq_low: list[dict] = []     # HUMAN with freq<3

    # Catalog snapshot for collision detection
    existing_catalog_codes = {axis: set(d.get("codes", {}).keys()) for axis, d in catalog.get("axes", {}).items()}

    proposed_new_codes_by_axis: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    # axis -> en_code -> [audit entries] (dedup if multiple KO synthetic codes mapped to same EN)

    for r in results:
        c = r["consensus"]
        status = c["status"]
        cat = c["category"]
        axis = r["axis"]  # already singular catalog form

        if status == "HUMAN":
            if r["freq"] >= HUMAN_REVIEW_MIN_FREQ:
                human_freq_high.append(r)
            else:
                human_freq_low.append(r)
            continue

        if cat == "EXISTING_EQUIV":
            en_code = normalize_en_code(c.get("canonical_label_en", ""))
            if en_code and axis in VALID_CATALOG_AXES and en_code in existing_catalog_codes.get(axis, set()):
                existing_aliases.append({**r, "_target_axis": axis, "_target_code": en_code})
            # else: LLM said EXISTING but code doesn't exist in catalog → treat as NEW
            else:
                if en_code and r["freq"] >= NEW_CODE_MIN_FREQ and axis in VALID_CATALOG_AXES:
                    proposed_new_codes_by_axis[axis][en_code].append(r)
                    new_codes.append({**r, "_target_axis": axis, "_target_code": en_code})
                else:
                    drops.append(r)

        elif cat == "NEW_CODE_NEEDED":
            en_code = normalize_en_code(c.get("canonical_label_en", ""))
            if not en_code:
                drops.append(r)
                continue
            if axis not in VALID_CATALOG_AXES:
                # 비-catalog axis (ppe_state, environmental, ppe_missing) → DROP (Q2)
                reloc_skips.append({**r, "_reason": f"axis '{axis}' not in catalog"})
                continue
            # LLM이 NEW로 분류했어도 이미 catalog에 존재하면 EXISTING_EQUIV로 처리 (alias 추가)
            if en_code in existing_catalog_codes.get(axis, set()):
                existing_aliases.append({**r, "_target_axis": axis, "_target_code": en_code, "_was_new_but_existing": True})
                continue
            if r["freq"] < NEW_CODE_MIN_FREQ:
                drops.append({**r, "_reason": f"freq {r['freq']} < {NEW_CODE_MIN_FREQ}"})
                continue
            proposed_new_codes_by_axis[axis][en_code].append(r)
            new_codes.append({**r, "_target_axis": axis, "_target_code": en_code})

        elif cat == "SUB_CLASS_OF":
            en_code = normalize_en_code(c.get("canonical_label_en", ""))
            parent_code = normalize_en_code(c.get("parent_code", ""))
            if not en_code or not parent_code:
                drops.append({**r, "_reason": "missing canonical_label_en or parent_code"})
                continue
            if axis not in VALID_CATALOG_AXES:
                reloc_skips.append({**r, "_reason": f"axis '{axis}' not in catalog"})
                continue
            # SUB child가 이미 catalog에 존재하면 alias만 추가 (중복 방지)
            if en_code in existing_catalog_codes.get(axis, set()):
                existing_aliases.append({**r, "_target_axis": axis, "_target_code": en_code, "_was_sub_but_existing": True})
                continue
            if parent_code not in existing_catalog_codes.get(axis, set()):
                # parent doesn't exist → treat as NEW
                if r["freq"] >= NEW_CODE_MIN_FREQ:
                    proposed_new_codes_by_axis[axis][en_code].append(r)
                    new_codes.append({**r, "_target_axis": axis, "_target_code": en_code, "_orphan_sub": True})
                else:
                    drops.append({**r, "_reason": f"parent '{parent_code}' missing + freq<{NEW_CODE_MIN_FREQ}"})
                continue
            sub_codes.append({**r, "_target_axis": axis, "_target_code": en_code, "_parent": parent_code})
            # Sub also adds to catalog
            proposed_new_codes_by_axis[axis][en_code].append(r)

        elif cat == "WRONG_AXIS":
            correct_axis = c.get("correct_axis", "").strip()
            # Q2: only apply if correct_axis ∈ valid 3
            if correct_axis not in VALID_CATALOG_AXES:
                reloc_skips.append({**r, "_reason": f"target axis '{correct_axis}' not in catalog (Q2 skip)"})
                continue
            en_code = normalize_en_code(c.get("canonical_label_en", ""))
            if not en_code:
                drops.append({**r, "_reason": "WRONG_AXIS missing canonical_label_en"})
                continue
            if r["freq"] < NEW_CODE_MIN_FREQ:
                drops.append({**r, "_reason": f"WRONG_AXIS freq {r['freq']} < {NEW_CODE_MIN_FREQ}"})
                continue
            # Treat as NEW in correct axis
            if en_code in existing_catalog_codes.get(correct_axis, set()):
                # already exists → alias addition
                existing_aliases.append({**r, "_target_axis": correct_axis, "_target_code": en_code, "_reloc": True})
            else:
                proposed_new_codes_by_axis[correct_axis][en_code].append(r)
                new_codes.append({**r, "_target_axis": correct_axis, "_target_code": en_code, "_reloc_from": axis})
                reloc_applies.append({**r, "_target_axis": correct_axis, "_target_code": en_code})

        elif cat == "NOT_A_CODE":
            drops.append(r)

    # Dedup proposed_new_codes (same EN may appear from multiple KO)
    unique_new_by_axis = {axis: dict(d) for axis, d in proposed_new_codes_by_axis.items()}

    print(f"\n=== Decision routing ===")
    print(f"  EXISTING_EQUIV → aliases   : {len(existing_aliases)}")
    print(f"  NEW_CODE (freq>=5)         : {len(new_codes)} entries, {sum(len(c) for c in unique_new_by_axis.values())} unique codes by axis")
    print(f"  SUB_CLASS_OF               : {len(sub_codes)} (parent 누락 시 NEW로 흡수)")
    print(f"  WRONG_AXIS applied (valid) : {len(reloc_applies)}")
    print(f"  WRONG_AXIS skipped (non-3) : {len(reloc_skips)}")
    print(f"  DROPS (NOT_A_CODE etc)     : {len(drops)}")
    print(f"  HUMAN freq>=3 (review queue): {len(human_freq_high)}")
    print(f"  HUMAN freq<3 (auto-skip)   : {len(human_freq_low)}")

    # Cumulative new code count per axis
    print(f"\n=== New codes to add per axis ===")
    for axis, codes_map in unique_new_by_axis.items():
        print(f"  {axis:20s} +{len(codes_map)} codes")
        for code, entries in sorted(codes_map.items(), key=lambda x: -sum(e['freq'] for e in x[1]))[:5]:
            total_freq = sum(e['freq'] for e in entries)
            print(f"    {code:40s} (freq sum {total_freq}, {len(entries)} KO sources)")

    # === Build catalog v4 ===
    new_catalog_axes = catalog.get("axes", {})
    for axis, codes_map in unique_new_by_axis.items():
        ax = new_catalog_axes.setdefault(axis, {"label": axis, "codes": {}})
        codes_dict = ax.setdefault("codes", {})
        for code, entries in codes_map.items():
            if code in codes_dict:
                continue  # already in catalog
            # Pick best label from highest-freq entry
            best_entry = max(entries, key=lambda e: e["freq"])
            label_ko = best_entry["ko_code"]  # KO label = synthetic KO code itself
            codes_dict[code] = {"label": label_ko}
    # SUB_CLASS_OF: add to parent's `sub` list
    for sub in sub_codes:
        axis = sub["_target_axis"]
        parent = sub["_parent"]
        child = sub["_target_code"]
        ax = new_catalog_axes.get(axis)
        if not ax or parent not in ax.get("codes", {}):
            continue
        parent_entry = ax["codes"][parent]
        sub_list = parent_entry.setdefault("sub", [])
        if child not in sub_list:
            sub_list.append(child)

    catalog.setdefault("_phase3b_audit", []).append({
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "new_codes_added": sum(len(c) for c in unique_new_by_axis.values()),
        "sub_relations_added": len(sub_codes),
        "source": "Phase 3A audit hybrid ensemble",
        "policies": {"new_min_freq": NEW_CODE_MIN_FREQ, "reloc_to_3_axes_only": True, "human_min_freq": HUMAN_REVIEW_MIN_FREQ},
    })

    # === Build aliases v? ===
    new_aliases_tier1 = aliases.setdefault("tier1", {})
    alias_count = 0
    for e in existing_aliases:
        axis = e["_target_axis"]
        code = e["_target_code"]
        ko = e["ko_code"]
        ax_aliases = new_aliases_tier1.setdefault(axis, {})
        ko_list = ax_aliases.setdefault(code, [])
        if ko not in ko_list:
            ko_list.append(ko)
            alias_count += 1
    # Also add aliases for NEW codes (KO source → new EN code)
    for axis, codes_map in unique_new_by_axis.items():
        ax_aliases = new_aliases_tier1.setdefault(axis, {})
        for code, entries in codes_map.items():
            ko_list = ax_aliases.setdefault(code, [])
            for e in entries:
                if e["ko_code"] not in ko_list:
                    ko_list.append(e["ko_code"])
                    alias_count += 1
    aliases.setdefault("_phase3b_audit", []).append({
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "aliases_added": alias_count,
    })

    # === Build OWL TBox subClassOf patch ===
    NS = "https://cashtoss.info/ontology/risk/"
    PREFIX_MAP = {
        "accident_type": "hazard#",
        "hazardous_agent": "agent#",
        "work_context": "context#",
    }
    ttl_lines = [
        "# Phase 3B — SUB_CLASS_OF patch (auto-generated from synthetic_audit_v1.json)",
        "# Apply: load alongside kosha-ontology-v2.owl in Fuseki",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix hazard: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix context: <https://cashtoss.info/ontology/risk/context#> .",
        "",
    ]
    for sub in sub_codes:
        axis = sub["_target_axis"]
        parent = sub["_parent"]
        child = sub["_target_code"]
        prefix = PREFIX_MAP.get(axis, "hazard#").split("#")[0]
        ttl_lines.append(f"{prefix}:{child} a owl:Class ; rdfs:subClassOf {prefix}:{parent} ; rdfs:label \"{sub['ko_code']}\"@ko .")
    ttl_text = "\n".join(ttl_lines) + "\n"

    # === Build Phase 3D mapping (synthetic_ko_to_en_final.json) ===
    # CRITICAL: only emit mapping if target_code is actually in catalog v4
    # (existing OR newly added in this Phase 3B run). Otherwise synthetic will
    # contain codes that Normalizer can't recognize → matching failures.
    AXIS_SYNTH_TO_CATALOG = {
        "accident_types": "accident_type",
        "hazardous_agents": "hazardous_agent",
        "work_contexts": "work_context",
        "ppe_states": "ppe_state",
        "ppe_missing": "ppe_missing",
        "environmental": "environmental",
    }
    # Catalog v4 codes = existing + newly added
    catalog_v4_codes: dict[str, set[str]] = {}
    for axis in VALID_CATALOG_AXES:
        catalog_v4_codes[axis] = set(existing_catalog_codes.get(axis, set())) | set(unique_new_by_axis.get(axis, {}).keys())

    final_mappings: dict[str, dict[str, str]] = defaultdict(dict)
    drop_list: dict[str, list[str]] = defaultdict(list)
    reloc_map: dict[str, dict[str, dict]] = defaultdict(dict)
    catalog_miss_drops = 0
    for r in results:
        c = r["consensus"]
        cat = c["category"]
        axis_synth = r["axis_synth"]
        axis_cat = AXIS_SYNTH_TO_CATALOG.get(axis_synth, axis_synth)
        ko = r["ko_code"]
        target_code = normalize_en_code(c.get("canonical_label_en", ""))

        if c["status"] == "HUMAN":
            drop_list[axis_synth].append(ko)
            continue

        if cat == "NOT_A_CODE":
            drop_list[axis_synth].append(ko)
            continue

        if cat in ("EXISTING_EQUIV", "NEW_CODE_NEEDED", "SUB_CLASS_OF"):
            if not target_code:
                drop_list[axis_synth].append(ko)
                continue
            # Verify target exists in catalog v4 (after this Phase 3B run)
            if axis_cat in VALID_CATALOG_AXES and target_code in catalog_v4_codes.get(axis_cat, set()):
                final_mappings[axis_synth][ko] = target_code
            else:
                drop_list[axis_synth].append(ko)
                catalog_miss_drops += 1
            continue

        if cat == "WRONG_AXIS":
            target_axis = c.get("correct_axis", "").strip()
            if target_axis not in VALID_CATALOG_AXES or not target_code:
                drop_list[axis_synth].append(ko)
                continue
            if target_code in catalog_v4_codes.get(target_axis, set()):
                reloc_map[axis_synth][ko] = {"target_axis": target_axis, "target_code": target_code}
            else:
                drop_list[axis_synth].append(ko)
                catalog_miss_drops += 1
    print(f"  catalog_miss_drops (target not in v4): {catalog_miss_drops}")

    final_mapping_payload = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Phase 3A audit + Phase 3B policy filters (freq>=5 NEW, valid 3 axes only)",
        "policies": {
            "new_min_freq": NEW_CODE_MIN_FREQ,
            "human_min_freq": HUMAN_REVIEW_MIN_FREQ,
            "reloc_valid_axes_only": list(VALID_CATALOG_AXES),
        },
        "mappings": {k: dict(v) for k, v in final_mappings.items()},
        "reloc": {k: dict(v) for k, v in reloc_map.items()},
        "drop_list": {k: list(set(v)) for k, v in drop_list.items()},
        "human_review_remaining": [
            {"axis_synth": r["axis_synth"], "ko_code": r["ko_code"], "freq": r["freq"]}
            for r in human_freq_high
        ],
    }

    apply_audit = {
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "existing_aliases_added": len(existing_aliases),
            "new_codes_added": sum(len(c) for c in unique_new_by_axis.values()),
            "sub_relations_added": len(sub_codes),
            "wrong_axis_applied": len(reloc_applies),
            "wrong_axis_skipped_non3": len(reloc_skips),
            "drops": len(drops),
            "human_review_queued": len(human_freq_high),
            "human_dropped_low_freq": len(human_freq_low),
            "alias_count_added": alias_count,
        },
    }

    if args.dry_run:
        print(f"\nDRY RUN — files NOT written.")
        print(f"  apply summary: {apply_audit['summary']}")
        return 0

    # Backups
    shutil.copy(CATALOG_PATH, CATALOG_PATH.with_suffix(".json.bak.phase3b"))
    shutil.copy(ALIASES_PATH, ALIASES_PATH.with_suffix(".json.bak.phase3b"))

    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ALIASES_PATH.write_text(json.dumps(aliases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PATCH_TTL_PATH.write_text(ttl_text, encoding="utf-8")
    FINAL_MAPPING.parent.mkdir(parents=True, exist_ok=True)
    FINAL_MAPPING.write_text(json.dumps(final_mapping_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    APPLY_AUDIT.write_text(json.dumps(apply_audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== APPLIED ===")
    for k, v in apply_audit["summary"].items():
        print(f"  {k}: {v}")
    print(f"\nWritten:")
    print(f"  {CATALOG_PATH.relative_to(ROOT)}")
    print(f"  {ALIASES_PATH.relative_to(ROOT)}")
    print(f"  {PATCH_TTL_PATH.relative_to(ROOT)}")
    print(f"  {FINAL_MAPPING.relative_to(ROOT)}")
    print(f"  {APPLY_AUDIT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
