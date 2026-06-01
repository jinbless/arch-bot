#!/usr/bin/env python3
"""Phase 1 — 위험 코드 정본(canonical) 어휘 + fine→canonical rollup SSOT 생성.

근본 원인: catalog(세밀 161/99/204) / SR(거친 7/9/35) / GUIDE·seed(세밀) / 온톨로지가
서로 다른 코드 어휘를 써서 매칭이 깨진다. SR 실사용 코드를 canonical backbone으로,
catalog 계층(sub→parent) + 휴리스틱으로 모든 코드를 canonical로 환원하는 rollup을 만든다.

canonical backbone = PG safety_requirements 실사용 코드 (= 매칭 보장되는 유일 어휘).
출력: shared/reference/canonical-code-vocabulary.json
      + 미매핑 리포트(stdout) — 0 될 때까지 휴리스틱/LLM 보강.

사용: PYTHONIOENCODING=utf-8 python data-team/05-enrichment/llm-scripts/build_canonical_vocabulary.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "serving-team/08-app/backend/app/data"
ART = REPO / "data-team/05-enrichment/runtime-artifacts"
OUT = REPO / "shared/reference/canonical-code-vocabulary.json"
PG = "dbname=kosha user=kosha password=1229 host=localhost"
AXES = ["accident_type", "hazardous_agent", "work_context"]
COL = {"accident_type": "accident_types", "hazardous_agent": "hazardous_agents", "work_context": "work_contexts"}

# work_context의 관리/기타 의사코드 — 위험축 아님(별도 meta). canonical에서 제외하되 rollup은 자기 자신.
WC_META = {"OTHER", "PPE_MGMT", "SAFETY_MGMT", "WELFARE", "WASTE_MGMT", "SPECIAL_WORKER", "GENERAL_WORKPLACE"}

# accident_type 정본 = KOSHA-22 공식 (사용자 확정). kosha_reference_parsed.json accident_types_22 en_suggested.
KOSHA22 = [
    "FALL", "SLIP_TRIP", "COLLISION", "STRUCK_BY", "COLLAPSE", "CAUGHT_IN", "CUT_LACERATION",
    "ELECTRIC_SHOCK", "EXPLOSION", "FIRE_INJURY", "CRUSHED_OVERTURNED", "TEMP_EXTREME_CONTACT",
    "DROWNING", "ERGONOMIC_STRAIN", "CHEMICAL_EXPOSURE", "OXYGEN_DEFICIENCY", "WORKPLACE_TRAFFIC",
    "OFF_SITE_TRAFFIC", "SPORTS_EVENT_INJURY", "VIOLENCE", "ANIMAL_INJURY", "OTHER_ACCIDENT", "UNCLASSIFIED",
]
# 순서 중요(먼저 매칭 우선): (정규식 토큰, canonical). substring/token 매칭.
ACC_RULES = [
    (r"SLIP|TRIP|STUMBL|미끄", "SLIP_TRIP"),
    (r"FALLING_OBJECT|STRUCK|HIT_BY|FALLING_|ICE_FRAGMENT|TV_FALL|OBJECT_FALL", "STRUCK_BY"),
    (r"FALL|FROM_HEIGHT|TIPOVER_FALL|OVERBOARD", "FALL"),
    (r"OFF_SITE|COMMUT|ROAD_TRAFFIC|DELIVERY_TRAFFIC", "OFF_SITE_TRAFFIC"),
    (r"WORKPLACE_TRAFFIC|VEHICLE_ACCIDENT|FORKLIFT_ACCIDENT|IN_PLANT_TRAFFIC", "WORKPLACE_TRAFFIC"),
    (r"COLLIS|COLLIDE|BUMP|부딪", "COLLISION"),
    (r"OVERTURN|ROLLOVER|TIPOVER|CRUSHED_BY|깔림|뒤집", "CRUSHED_OVERTURNED"),
    (r"CAUGHT|ENTANGLE|PINCH|NIP|JAM|ROLLED_IN|끼", "CAUGHT_IN"),
    (r"CRUSH|COMPRESS|압착", "CAUGHT_IN"),
    (r"COLLAPSE|CAVE_IN|무너", "COLLAPSE"),
    (r"CUT|LACERAT|STAB|AMPUT|SHARP|BLADE|KNIFE|GLASS|절단|베임|찔림", "CUT_LACERATION"),
    (r"ELECTRIC|SHOCK|ARC_FLASH|감전", "ELECTRIC_SHOCK"),
    (r"EXPLOS|BLAST|폭발", "EXPLOSION"),
    (r"FIRE|FLAME|IGNIT|COMBUST|BURN_FROM_FIRE|화재", "FIRE_INJURY"),
    (r"BURN|SCALD|HOT_|COLD_|CRYO|FROST|THERMAL|TEMP_EXTREME|EXTREME_COLD|HIGH_HEAT|화상", "TEMP_EXTREME_CONTACT"),
    (r"DROWN|익사", "DROWNING"),
    (r"ERGONOM|MUSCULO|STRAIN|POSTURE|REPETITIVE|근골격", "ERGONOMIC_STRAIN"),
    (r"ASPHYXIA|OXYGEN|SUFFOCAT|질식", "OXYGEN_DEFICIENCY"),
    (r"CHEMICAL|TOXIC|POISON|INHAL|IRRITAT|CORROS|ACID|VAPOR|GAS_|_GAS|FUME|EXPOSURE|중독|화학", "CHEMICAL_EXPOSURE"),
    (r"ANIMAL|BITE|STING|교상", "ANIMAL_INJURY"),
    (r"VIOLENC|ASSAULT|폭행", "VIOLENCE"),
    (r"SPORT|EXERCISE|체육", "SPORTS_EVENT_INJURY"),
    (r"TRAFFIC", "WORKPLACE_TRAFFIC"),
    (r"CONTAMINAT|FOOD_POISON", "CHEMICAL_EXPOSURE"),
]
# hazardous_agent 정본 = SR 9 + OTHER_AGENT 버킷
AGENT_EXTRA = {"UNKNOWN_AGENT"}  # pending/open class (continual learning 대상)
AGENT_RULES = [
    (r"DUST|PARTICUL|MOLD|FIBER|ASBESTOS|분진", "DUST"),
    (r"BENZENE|ACID|ALKALI|SOLVENT|FORMALDEHYDE|GLUTARALDEHYDE|DETERGENT|PESTICID|PAINT|FRAGRANCE|DEVELOPER|AMALGAM|RESIN|MERCURY|CHLORINE|AMMONIA|LEACHATE|REACTION|화학", "CHEMICAL"),
    (r"TOXIC|POISON|GASOLINE|FUEL|GAS|VAPOR|METHANE|COMBUSTION_GAS|TOBACCO|SMOKE|독성", "TOXIC"),
    (r"ELECTRIC|VOLTAGE|OUTLET|CAPACITOR|WIRE|DISTRIBUTION_BOARD|감전|전기", "ELECTRICITY"),
    (r"FIRE|FLAME|IGNIT|화재", "FIRE"),
    (r"HOT|COLD|CRYO|HEAT|THERMAL|TEMP|온도", "HEAT_COLD"),
    (r"NOISE|SOUND|EARPHONE|소음", "NOISE"),
    (r"RADIAT|XRAY|X_RAY|\bUV\b|방사", "RADIATION"),
    (r"BIO|PATHOGEN|INFECT|VIRUS|BLOOD|MEDICAL_WASTE|BACTERIA|VACCIN|감염|병원", "BIOLOGICAL"),
]
# 교차축 rollup: 잘못된 축에 적재된 코드를 올바른 축 canonical로. 값 형식 "axis:CODE".
AGENT_CROSS = [
    (r"SHARP|BLADE|KNIFE|GLASS|FRAGMENT|FOREIGN_OBJECT|FASTENER|PROTRUSION|SHEET_EDGE|BONING|UNGUARDED", "accident_type:CUT_LACERATION"),
    (r"HEAVY_OBJECT|UNSTABLE_DISPLAY_SHELF|UNSTABLE_SHELF|ROD_", "accident_type:STRUCK_BY"),
    (r"OXYGEN_DEFICIENCY|ASPHYXIA", "accident_type:OXYGEN_DEFICIENCY"),
    (r"VIOLENT_CUSTOMER|VIOLENCE", "accident_type:VIOLENCE"),
    (r"WET_FLOOR", "accident_type:SLIP_TRIP"),
]
CROSS = {"hazardous_agent": AGENT_CROSS, "accident_type": [], "work_context": []}

WC_EXTRA = {"UNKNOWN_CONTEXT"}  # pending/open class (SR의 deliberate "OTHER"와 구분)
WC_RULES = [
    (r"FORKLIFT|VEHICLE|TRUCK|DELIVERY_RIDER|차량|지게차", "VEHICLE"),
    (r"WELD|GRIND|SAND|SAW|PRESS|NAIL_GUN|CUTTER|MACHINE|LATHE|기계|용접", "MACHINE"),
    (r"CONVEYOR|컨베이어", "CONVEYOR"),
    (r"CRANE|HOIST|크레인", "CRANE"),
    (r"SCAFFOLD|LADDER|HIGH_RISE|ROPE_ACCESS|EXTERIOR_ROPE|비계|사다리", "SCAFFOLD"),
    (r"EXCAVAT|TRENCH|굴착", "EXCAVATION"),
    (r"CONFINED|TANK|PIT|밀폐", "CONFINED_SPACE"),
    (r"CHEMICAL|SOLVENT|SPRAY|DRY_CLEAN|PAINT|VAPOR|OIL_DRAIN|화학", "CHEMICAL_WORK"),
    (r"ELECTRIC|LIVE_POWER|전기", "ELECTRICAL_WORK"),
    (r"HEAVY|LIFT|LOADING|HANDLING|BOX|PACKAGE|SORTING|STORAGE|SHELF|HANDCART|적재|운반", "MATERIAL_HANDLING"),
    (r"COOK|FRY|KITCHEN|FOOD|BEVERAGE|조리", "HEAT_COLD_WORK"),
    (r"PATHOGEN|MEDICAL|DENTAL|EMBALM|병원|의료", "PATHOGEN_WORK"),
    (r"DUST|분진", "DUST_WORK"),
    (r"NOISE|소음", "NOISE_WORK"),
    (r"COLD|FREEZ|HOT_|DRYER|냉동", "HEAT_COLD_WORK"),
    (r"SLICER|GUILLOTINE|CUTTER|ROLLER|HOPPER|LAMINAT|LATHE", "MACHINE"),
    (r"HIGH_SHELF|HIGH_RISE|CLIMB|ROOFTOP|EXTERIOR_ROPE", "SCAFFOLD"),
    (r"AISLE|OBSTRUCTION|통로", "PASSAGE"),
    (r"POSTURE|MOTION_RANGE", "ERGONOMIC_WORK"),
    (r"FIRE_DETECT|FIRE_EXTINGUISH|FIRE_EVAC|EVACUATION|FIRE_", "FIRE_EXPLOSION_WORK"),
    (r"FUEL|GAS_APPLIANCE|GASOLINE", "CHEMICAL_WORK"),
    (r"AUTOCLAVE|STERIL|EMBALM|MORTUARY|CREMATION|FUNERAL|BODY_TRANSPORT|MEDICAL|DENTAL|ACUPUNCTURE|HARVEST_BLOOD", "PATHOGEN_WORK"),
    (r"VENTIL|환기", "VENTILATION"),
]


def _rule_match(code, rules):
    import re as _re
    for pat, canon in rules:
        if _re.search(pat, code):
            return canon
    return None


def pg_distinct(cur, table, col):
    cur.execute(f"SELECT DISTINCT jsonb_array_elements_text({col}) FROM {table} WHERE {col} IS NOT NULL")
    return set(r[0] for r in cur.fetchall())


def main():
    conn = psycopg2.connect(PG)
    cur = conn.cursor()

    # 1) canonical backbone = SR 실사용
    sr = {a: pg_distinct(cur, "safety_requirements", COL[a]) for a in AXES}
    ci = {a: pg_distinct(cur, "checklist_items", COL[a]) for a in AXES}
    gf = {a: set() for a in AXES}
    freq = {a: {} for a in AXES}  # PG 출현 빈도(continual 승격 신호): CI + GUIDE
    for a in AXES:
        cur.execute("SELECT DISTINCT feature_code FROM guide_entity_feature_candidates WHERE entity_type='GUIDE' AND axis=%s", (a,))
        gf[a] = set(r[0] for r in cur.fetchall())
        cur.execute(f"SELECT v, count(*) FROM checklist_items, jsonb_array_elements_text({COL[a]}) v GROUP BY v")
        for code, n in cur.fetchall():
            freq[a][code] = freq[a].get(code, 0) + int(n)
        cur.execute("SELECT feature_code, count(*) FROM guide_entity_feature_candidates WHERE entity_type='GUIDE' AND axis=%s GROUP BY feature_code", (a,))
        for code, n in cur.fetchall():
            freq[a][code] = freq[a].get(code, 0) + int(n)
    conn.close()

    # 2) catalog: top-level codes + sub→parent edges
    cat = json.load(open(DATA / "risk_feature_catalog.json", encoding="utf-8"))
    cat_codes = {a: set() for a in AXES}
    sub_parent = {a: {} for a in AXES}
    for a in AXES:
        node = cat["axes"][a]["codes"]
        for parent, v in node.items():
            cat_codes[a].add(parent)
            for s in (v.get("sub") or []) if isinstance(v, dict) else []:
                code = s.get("code") if isinstance(s, dict) else s
                if code:
                    cat_codes[a].add(code)
                    sub_parent[a][code] = parent

    # 3) aliases target codes ({code:[aliases]}) + hazard_name_seed codes
    alias_codes = {a: set() for a in AXES}
    ap = DATA / "risk_feature_aliases.json"
    if ap.exists():
        al = json.load(open(ap, encoding="utf-8"))
        for a in AXES:
            alias_codes[a] |= set((al.get("tier1", {}).get(a, {}) or {}).keys())
    seed_codes = {a: set() for a in AXES}
    sp = ART / "hazard_name_seed.json"
    if sp.exists():
        for m in json.load(open(sp, encoding="utf-8")).get("mappings", []):
            if m.get("axis") in seed_codes and m.get("code"):
                seed_codes[m["axis"]].add(m["code"])

    # canonical = SR ∪ catalog-parents-that-SR-uses; work_context는 SR 거친 세트(meta 제외)
    canonical = {
        "accident_type": set(KOSHA22),
        "hazardous_agent": set(sr["hazardous_agent"]) | AGENT_EXTRA,
        "work_context": (set(sr["work_context"]) - WC_META) | WC_EXTRA,
    }
    RULES = {"accident_type": ACC_RULES, "hazardous_agent": AGENT_RULES, "work_context": WC_RULES}
    # pending/open class — 억지 배정 대신 여기로. continual learning이 빈도+클러스터로 승격.
    OTHER = {"accident_type": "UNCLASSIFIED", "hazardous_agent": "UNKNOWN_AGENT", "work_context": "UNKNOWN_CONTEXT"}

    # LLM-curated overrides (regen-safe): rules가 OTHER로 떨어뜨리는 fine 코드의 canonical 배정 보존.
    # 생성: curate_wc_rollup.py → shared/reference/wc_rollup_overrides.json ({axis:{code:canonical}})
    _ovp = OUT.parent / "wc_rollup_overrides.json"
    _ov_raw = json.load(open(_ovp, encoding="utf-8")) if _ovp.exists() else {}
    OVERRIDES = {a: _ov_raw.get(a, {}) for a in AXES}

    def resolve(a, code):
        if code in canonical[a]:
            return code, "identity"
        # 1) 룰 매칭(코드 자체)
        r = _rule_match(code, RULES[a])
        if r:
            return r, "rule"
        # 2) catalog 부모로 룰 매칭
        p = sub_parent[a].get(code)
        if p:
            if p in canonical[a]:
                return p, "parent"
            r = _rule_match(p, RULES[a])
            if r:
                return r, "parent_rule"
        # 3) 교차축 rollup (잘못된 축 → 올바른 축 canonical)
        x = _rule_match(code, CROSS[a])
        if x:
            return x, "cross"
        # 3.5) LLM-curated override (rules 미해결분, regen-safe — curate_wc_rollup 산출)
        ov = OVERRIDES.get(a, {}).get(code)
        if ov and ov in canonical[a]:
            return ov, "override"
        # 4) OTHER 버킷 (저신뢰 — LLM/리뷰 대상)
        return OTHER[a], "other"

    universe = {a: cat_codes[a] | sr[a] | ci[a] | gf[a] | alias_codes[a] | seed_codes[a] for a in AXES}
    rollup = {a: {} for a in AXES}
    unmapped = {a: [] for a in AXES}  # OTHER로 떨어진 저신뢰(리뷰 대상)
    for a in AXES:
        for code in sorted(universe[a]):
            if a == "work_context" and code in WC_META:
                rollup[a][code] = code
                continue
            r, how = resolve(a, code)
            rollup[a][code] = r
            if how == "other":
                unmapped[a].append(code)

    out = {
        "version": "1.0",
        "description": "위험 코드 정본 어휘 SSOT. canonical=SR 실사용 backbone, rollup=모든 코드→canonical.",
        "casing": {"pg_serving": "UPPER_SNAKE", "ontology_iri": "CamelCase (via code_iri_mapper)"},
        "axes": {
            a: {
                "canonical": sorted(canonical[a]),
                "pending_bucket": OTHER[a],  # 미분류 open-class (continual learning 승격 대상)
                "wc_meta": sorted(WC_META & universe[a]) if a == "work_context" else [],
                "rollup": dict(sorted(rollup[a].items())),
                # PG 실사용 pending 코드 + 빈도(승격 신호). catalog-only 죽은코드는 freq=0.
                "pending": sorted(
                    ({"code": c, "freq": freq[a].get(c, 0)} for c in unmapped[a] if freq[a].get(c, 0) > 0),
                    key=lambda x: -x["freq"],
                ),
            }
            for a in AXES
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT.relative_to(REPO)}")
    for a in AXES:
        print(f"\n[{a}] canonical={len(canonical[a])} universe={len(universe[a])} "
              f"rolled={len(rollup[a])} UNMAPPED={len(unmapped[a])}")
        print("  canonical:", ", ".join(sorted(canonical[a])))
        if unmapped[a]:
            print(f"  UNMAPPED({len(unmapped[a])}):", ", ".join(unmapped[a][:60]))


if __name__ == "__main__":
    main()
