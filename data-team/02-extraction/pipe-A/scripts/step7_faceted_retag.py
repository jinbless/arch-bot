#!/usr/bin/env python3
"""SR 626개 faceted 다축 태깅: addresses_hazard(flat) → accident_types/hazardous_agents/work_contexts(3축).

전략:
  Step 1: identifier prefix → work_contexts (자동, 42 prefix→축 매핑)
  Step 2: addresses_hazard → accident_type/hazardous_agent 분리 (규칙 기반)
  Step 3: STRUCK_BY → COLLISION/FALLING_OBJECT 키워드 세분화
  Step 4: CAUGHT_IN → CRUSH/CUT 키워드 세분화
  Step 5: CHEMICAL_EXPOSURE → prefix 기반 세분화 (DUST/TOXIC/RADIATION 등)
  Step 6: PostgreSQL 컬럼 업데이트
"""

import json
import psycopg2

DB_PARAMS = dict(dbname="kosha", user="kosha", password="1229", host="localhost")

# ═══ Step 1: SR identifier prefix → work_context 매핑 ═══
PREFIX_TO_CONTEXT = {
    "SCAFFOLD":           "SCAFFOLD",
    "CONFINED":           "CONFINED_SPACE",
    "EXCAVATION":         "EXCAVATION",
    "SHORING":            "EXCAVATION",
    "MACHINE":            "MACHINE",
    "VEHICLE":            "VEHICLE",
    "CRANE":              "CRANE",
    "LIFTING":            "CRANE",
    "RIGGING":            "CRANE",
    "CONVEYOR":           "CONVEYOR",
    "ROBOT":              "ROBOT",
    "CONSTRUCTION_EQUIP": "CONSTRUCTION_EQUIP",
    "RAIL":               "RAIL",
    "PRESSURE":           "PRESSURE_VESSEL",
    "STEELWORK":          "STEELWORK",
    "CARGO":              "MATERIAL_HANDLING",
    "HEAVY_LOAD":         "MATERIAL_HANDLING",
    "WORKPLACE":          "GENERAL_WORKPLACE",
    "OFFICE":             "GENERAL_WORKPLACE",
    "PASSAGE":            "PASSAGE",
    "FIRE_EXPLOSION":     "FIRE_EXPLOSION_WORK",
    "CHEMICAL":           "CHEMICAL_WORK",
    "HAZMAT":             "CHEMICAL_WORK",
    "PROHIBITED_CHEM":    "CHEMICAL_WORK",
    "ELECTRIC":           "ELECTRICAL_WORK",
    "RADIATION":          "RADIATION_WORK",
    "DUST":               "DUST_WORK",
    "NOISE":              "NOISE_WORK",
    "HEAT":               "HEAT_COLD_WORK",
    "PATHOGEN":           "PATHOGEN_WORK",
    "VENTILATION":        "VENTILATION",
    "DEMOLITION":         "DEMOLITION",
    "LOGGING":            "LOGGING",
    "FALL":               "FALL_PROTECTION",
    "COLLAPSE":           "COLLAPSE_PREVENTION",
    "ERGONOMIC":          "ERGONOMIC_WORK",
    "PPE":                "PPE_MGMT",
    "WASTE":              "WASTE_MGMT",
    "MGMT":               "SAFETY_MGMT",
    "SPECIAL_WORKER":     "SPECIAL_WORKER",
    "OTHER_HAZARD":       "OTHER",
    "WELFARE":            "WELFARE",
}

# ═══ Step 2: addresses_hazard → 축 분리 (직접 매핑 가능한 것) ═══
HAZARD_DIRECT_MAP = {
    # accident_type으로 직접 이동
    "FALL":       ("accident_type", "FALL"),
    "COLLAPSE":   ("accident_type", "COLLAPSE"),
    "ERGONOMIC":  ("accident_type", "ERGONOMIC"),
    # hazardous_agent로 직접 이동
    "FIRE_EXPLOSION":  ("hazardous_agent", "FIRE"),
    "ELECTRIC_SHOCK":  ("hazardous_agent", "ELECTRICITY"),
    "NOISE_VIBRATION": ("hazardous_agent", "NOISE"),
    "HEAT_COLD":       ("hazardous_agent", "HEAT_COLD"),
    # work_context로 이동 (hazard 축에서 제거)
    "SCAFFOLDING":    ("work_context", "SCAFFOLD"),
    "CONFINED_SPACE": ("work_context", "CONFINED_SPACE"),
}

# ═══ Step 3: STRUCK_BY 키워드 세분화 ═══
# 기본: FALLING_OBJECT (크레인/양중기/낙하 관련) vs COLLISION (차량/충돌/접촉 관련)
FALLING_OBJECT_KEYWORDS = [
    "낙하", "떨어", "비래", "날아", "투하", "하물", "하중", "달기구",
    "와이어로프", "체인", "슬링", "권과", "해지장치", "매달", "인양",
]
COLLISION_KEYWORDS = [
    "충돌", "접촉", "운행", "운전", "주행", "속도", "후진", "유도",
    "전조등", "신호", "교통", "보행", "건널", "통행",
]

# ═══ Step 4: CAUGHT_IN 키워드 세분화 ═══
CUT_KEYWORDS = [
    "절단", "톱", "칼날", "절삭", "날", "원형톱", "띠톱", "둥근톱",
    "모서리", "연삭", "그라인더", "연마", "분쇄",
]
CRUSH_KEYWORDS = [
    "끼임", "압착", "회전", "롤러", "프레스", "밀착", "방호덮개",
    "맞물림", "물림",
]


def extract_prefix(identifier: str) -> str:
    """SR-MACHINE-001 → MACHINE, SR-CONSTRUCTION_EQUIP-002 → CONSTRUCTION_EQUIP"""
    parts = identifier.split("-")
    # SR-XXX-NNN: prefix = parts[1:-1] joined
    return "-".join(parts[1:-1]) if len(parts) >= 3 else parts[1] if len(parts) >= 2 else ""


def classify_struck_by(title: str, text: str, prefix: str) -> list:
    """STRUCK_BY → COLLISION / FALLING_OBJECT 세분화."""
    combined = title + " " + text
    has_falling = any(kw in combined for kw in FALLING_OBJECT_KEYWORDS)
    has_collision = any(kw in combined for kw in COLLISION_KEYWORDS)

    # prefix 기반 힌트
    if prefix in ("CRANE", "LIFTING", "RIGGING"):
        has_falling = True
    if prefix in ("VEHICLE", "CONSTRUCTION_EQUIP", "CONVEYOR", "RAIL"):
        has_collision = True

    if has_falling and has_collision:
        return ["COLLISION", "FALLING_OBJECT"]
    elif has_falling:
        return ["FALLING_OBJECT"]
    elif has_collision:
        return ["COLLISION"]
    else:
        # 기본: prefix 기반 추론
        if prefix in ("CRANE", "LIFTING", "RIGGING", "CARGO", "HEAVY_LOAD"):
            return ["FALLING_OBJECT"]
        elif prefix in ("VEHICLE", "CONSTRUCTION_EQUIP", "RAIL", "CONVEYOR"):
            return ["COLLISION"]
        else:
            return ["COLLISION", "FALLING_OBJECT"]  # 둘 다 가능


def classify_caught_in(title: str, text: str, prefix: str) -> list:
    """CAUGHT_IN → CRUSH / CUT 세분화."""
    combined = title + " " + text
    has_cut = any(kw in combined for kw in CUT_KEYWORDS)
    has_crush = any(kw in combined for kw in CRUSH_KEYWORDS)

    if has_cut and has_crush:
        return ["CRUSH", "CUT"]
    elif has_cut:
        return ["CUT"]
    elif has_crush:
        return ["CRUSH"]
    else:
        # 기본: CRUSH (더 일반적)
        return ["CRUSH"]


def classify_chemical(prefix: str) -> list:
    """CHEMICAL_EXPOSURE → prefix 기반 세분화."""
    if prefix == "DUST":
        return ["DUST"]
    elif prefix == "RADIATION":
        return ["RADIATION"]
    elif prefix == "PATHOGEN":
        return ["BIOLOGICAL"]  # 생물학적 → hazardous_agent
    elif prefix in ("HAZMAT", "PROHIBITED_CHEM"):
        return ["TOXIC"]
    elif prefix == "CHEMICAL":
        return ["CHEMICAL"]  # 일반 화학물질
    else:
        return ["CHEMICAL"]  # 기본


def retag_sr(identifier, title, text, addresses_hazard):
    """단일 SR에 대해 3축 facet 태깅 수행."""
    prefix = extract_prefix(identifier)

    accident_types = set()
    hazardous_agents = set()
    work_contexts = set()

    # Step 1: prefix → work_context
    ctx = PREFIX_TO_CONTEXT.get(prefix)
    if ctx:
        work_contexts.add(ctx)

    # Step 2-5: addresses_hazard 처리
    hazards = addresses_hazard if isinstance(addresses_hazard, list) else []

    for haz in hazards:
        if haz in HAZARD_DIRECT_MAP:
            axis, code = HAZARD_DIRECT_MAP[haz]
            if axis == "accident_type":
                accident_types.add(code)
            elif axis == "hazardous_agent":
                hazardous_agents.add(code)
            elif axis == "work_context":
                work_contexts.add(code)
        elif haz == "STRUCK_BY":
            for code in classify_struck_by(title, text, prefix):
                accident_types.add(code)
        elif haz == "CAUGHT_IN":
            for code in classify_caught_in(title, text, prefix):
                accident_types.add(code)
        elif haz == "CHEMICAL_EXPOSURE":
            for code in classify_chemical(prefix):
                hazardous_agents.add(code)

    return {
        "accident_types": sorted(accident_types) if accident_types else None,
        "hazardous_agents": sorted(hazardous_agents) if hazardous_agents else None,
        "work_contexts": sorted(work_contexts) if work_contexts else None,
    }


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    print("=== SR Faceted Retagging ===")
    cur.execute("SELECT identifier, title, text, addresses_hazard FROM safety_requirements ORDER BY identifier")
    rows = cur.fetchall()
    print(f"  Total SRs: {len(rows)}")

    stats = {"tagged": 0, "no_accident": 0, "no_agent": 0, "no_context": 0}
    results = []

    for identifier, title, text, addresses_hazard in rows:
        facets = retag_sr(identifier, title, text, addresses_hazard)
        results.append((identifier, facets))

        if facets["accident_types"]:
            stats["tagged"] += 1
        else:
            stats["no_accident"] += 1
        if not facets["hazardous_agents"]:
            stats["no_agent"] += 1
        if not facets["work_contexts"]:
            stats["no_context"] += 1

    # DB 업데이트
    print("\nUpdating PostgreSQL...")
    update_sql = """
        UPDATE safety_requirements
        SET accident_types = %s::jsonb,
            hazardous_agents = %s::jsonb,
            work_contexts = %s::jsonb
        WHERE identifier = %s
    """
    for identifier, facets in results:
        cur.execute(update_sql, (
            json.dumps(facets["accident_types"]) if facets["accident_types"] else None,
            json.dumps(facets["hazardous_agents"]) if facets["hazardous_agents"] else None,
            json.dumps(facets["work_contexts"]) if facets["work_contexts"] else None,
            identifier,
        ))
    conn.commit()

    # 검증
    print("\n=== Verification ===")
    cur.execute("SELECT COUNT(*) FROM safety_requirements WHERE accident_types IS NOT NULL OR hazardous_agents IS NOT NULL OR work_contexts IS NOT NULL")
    tagged = cur.fetchone()[0]
    print(f"  SRs with at least 1 axis: {tagged}/{len(rows)}")

    cur.execute("SELECT COUNT(*) FROM safety_requirements WHERE accident_types IS NULL AND hazardous_agents IS NULL AND work_contexts IS NULL")
    orphan = cur.fetchone()[0]
    print(f"  SRs with NO axis (orphan): {orphan}")

    # 축별 분포
    print("\n=== Axis Distribution ===")

    print("\n  [accident_type]")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(accident_types) as val FROM safety_requirements WHERE accident_types IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    print("\n  [hazardous_agent]")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(hazardous_agents) as val FROM safety_requirements WHERE hazardous_agents IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    print("\n  [work_context]")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(work_contexts) as val FROM safety_requirements WHERE work_contexts IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    # STRUCK_BY 세분화 결과
    print("\n=== STRUCK_BY Split Results ===")
    cur.execute("""
        SELECT identifier, accident_types, substring(title, 1, 50) as title
        FROM safety_requirements
        WHERE addresses_hazard::text LIKE '%STRUCK_BY%'
        ORDER BY identifier LIMIT 15
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]} — {row[2]}")

    # CAUGHT_IN 세분화 결과
    print("\n=== CAUGHT_IN Split Results ===")
    cur.execute("""
        SELECT identifier, accident_types, substring(title, 1, 50) as title
        FROM safety_requirements
        WHERE addresses_hazard::text LIKE '%CAUGHT_IN%'
        ORDER BY identifier LIMIT 15
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]} — {row[2]}")

    cur.close()
    conn.close()
    print(f"\n=== Done: {len(rows)} SRs tagged ===")


if __name__ == "__main__":
    main()
