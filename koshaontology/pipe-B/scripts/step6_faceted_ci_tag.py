#!/usr/bin/env python3
"""CI 35,206개 faceted 다축 태깅.

전략:
  Track 1: SR 매핑된 CI (~10,000개) → SR facet 상속
  Track 2: 고아 CI (~25,000개) → guide title + CI text 키워드 기반 독립 태깅
"""

import json
import re
import psycopg2

DB_PARAMS = dict(dbname="kosha", user="kosha", password="1229", host="localhost")

# ═══ 가이드 제목 → facet 매핑 키워드 ═══

# accident_type 키워드
ACCIDENT_KEYWORDS = {
    "FALL": ["추락", "떨어짐", "높이", "고소", "지붕", "사다리", "개구부", "추락방호", "추락방지", "안전난간", "안전대"],
    "SLIP": ["미끄러", "넘어짐", "슬립", "전도"],
    "COLLISION": ["충돌", "접촉", "운행", "운전", "주행", "차량", "건설기계"],
    "FALLING_OBJECT": ["낙하물", "비래", "투하", "낙하", "양중", "인양", "하물"],
    "CRUSH": ["끼임", "압착", "회전", "롤러", "프레스", "파쇄", "혼합기", "교반", "압축", "밀림", "끼인"],
    "CUT": ["절단", "톱", "절삭", "연삭", "연마", "그라인더", "선반", "밀링", "드릴"],
    "COLLAPSE": ["붕괴", "무너짐", "도괴", "해체", "철거"],
    "ERGONOMIC": ["근골격", "인력운반", "중량물", "허리", "반복작업"],
}

# hazardous_agent 키워드
AGENT_KEYWORDS = {
    "CHEMICAL": ["화학물질", "유해물질", "관리대상", "특별관리물질", "유기화합물", "시약", "용제", "용액"],
    "DUST": ["분진", "석면", "광물성", "금속분진", "용접흄"],
    "TOXIC": ["독성", "중독", "유독", "발암", "특정화학물질", "허용농도", "산화에틸렌", "톨루엔"],
    "CORROSION": ["부식", "산성", "알칼리", "강산"],
    "RADIATION": ["방사선", "비전리", "전리", "자외선", "레이저", "X선"],
    "FIRE": ["화재", "폭발", "인화", "발화", "가연", "산소", "위험물", "연소", "방폭"],
    "ELECTRICITY": ["전기", "감전", "정전기", "전압", "배선", "접지", "전격", "누전", "개폐기"],
    "ARC_FLASH": ["아크", "용접"],
    "NOISE": ["소음", "진동", "청력", "이어플러그"],
    "HEAT_COLD": ["온도", "고열", "한랭", "냉동", "동상", "열사병", "열중증"],
    "BIOLOGICAL": ["병원체", "감염", "세균", "바이러스", "혈액매개"],
}

# work_context 키워드
CONTEXT_KEYWORDS = {
    "SCAFFOLD": ["비계", "틀비계", "달비계", "강관비계", "이동식비계"],
    "CONFINED_SPACE": ["밀폐공간", "밀폐", "맨홀", "탱크내부", "지하피트"],
    "EXCAVATION": ["굴착", "굴삭", "터파기", "흙막이", "지보공"],
    "MACHINE": ["기계", "공작기계", "프레스", "전단기", "선반", "밀링", "드릴", "파쇄기", "혼합기", "교반기", "원심기", "사출"],
    "VEHICLE": ["차량", "지게차", "포크리프트", "화물차", "덤프"],
    "CRANE": ["크레인", "양중기", "호이스트", "리프트", "곤돌라", "달기구", "체인블록"],
    "CONVEYOR": ["컨베이어", "벨트"],
    "ROBOT": ["로봇", "산업용로봇"],
    "CONSTRUCTION_EQUIP": ["건설기계", "굴삭기", "불도저", "항타기", "항발기"],
    "RAIL": ["철도", "궤도", "트롤리"],
    "PRESSURE_VESSEL": ["압력용기", "보일러", "증기", "고압가스", "아세틸렌"],
    "STEELWORK": ["철골", "강구조물"],
    "MATERIAL_HANDLING": ["하역", "운반", "적재", "화물"],
    "GENERAL_WORKPLACE": ["작업장", "사업장"],
    "PASSAGE": ["통로", "계단", "사다리"],
    "FIRE_EXPLOSION_WORK": ["위험물저장", "도장작업", "건조설비"],
    "CHEMICAL_WORK": ["화학설비", "특수화학설비", "배관"],
    "ELECTRICAL_WORK": ["전기설비", "배전반", "변전소", "수전설비"],
    "RADIATION_WORK": ["방사선작업", "밀봉선원"],
    "DUST_WORK": ["분진작업", "제분", "목재가공"],
    "DEMOLITION": ["해체", "철거", "폐기물"],
    "LOGGING": ["벌목", "벌채", "조림"],
    "VENTILATION": ["환기", "국소배기", "전체환기"],
}

# 가이드 도메인별 기본 facet
DOMAIN_DEFAULTS = {
    "A": {"hazardous_agents": ["CHEMICAL"]},   # A: 화학물질 측정/분석 가이드
    "B": {},                                     # B: 기계/장비 (다양)
    "C": {},                                     # C: 건설 (다양)
    "D": {},                                     # D: 기타
    "E": {},                                     # E: 보건 (다양)
}


def extract_facets_from_text(text: str) -> dict:
    """텍스트에서 facet 키워드 매칭."""
    accident_types = set()
    hazardous_agents = set()
    work_contexts = set()

    for code, keywords in ACCIDENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            accident_types.add(code)

    for code, keywords in AGENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            hazardous_agents.add(code)

    for code, keywords in CONTEXT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            work_contexts.add(code)

    return {
        "accident_types": sorted(accident_types) if accident_types else None,
        "hazardous_agents": sorted(hazardous_agents) if hazardous_agents else None,
        "work_contexts": sorted(work_contexts) if work_contexts else None,
    }


def merge_facets(a: dict, b: dict) -> dict:
    """두 facet dict를 합침."""
    result = {}
    for key in ("accident_types", "hazardous_agents", "work_contexts"):
        vals = set()
        if a.get(key):
            vals.update(a[key])
        if b.get(key):
            vals.update(b[key])
        result[key] = sorted(vals) if vals else None
    return result


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # ═══ Step 0: 가이드 제목 로드 + 가이드별 facet 캐시 ═══
    print("=== Loading guide titles ===")
    cur.execute("SELECT guide_code, title, domain FROM kosha_guides")
    guide_facets = {}
    for guide_code, title, domain in cur.fetchall():
        facets = extract_facets_from_text(title)
        # 도메인 기본값 적용
        defaults = DOMAIN_DEFAULTS.get(domain, {})
        for key, vals in defaults.items():
            if not facets.get(key):
                facets[key] = vals
        guide_facets[guide_code] = facets
    print(f"  {len(guide_facets)} guides processed")

    # ═══ Step 1: SR 매핑된 CI → SR facet 상속 ═══
    print("\n=== Track 1: SR-mapped CI (inherit from SR) ===")
    cur.execute("""
        SELECT csm.ci_id, array_agg(sr.accident_types), array_agg(sr.hazardous_agents), array_agg(sr.work_contexts)
        FROM ci_sr_mapping csm
        JOIN safety_requirements sr ON sr.identifier = csm.sr_id
        GROUP BY csm.ci_id
    """)

    sr_inherited = {}
    for ci_id, acc_list, agent_list, ctx_list in cur.fetchall():
        accident = set()
        agents = set()
        contexts = set()
        for acc in acc_list:
            if acc:
                for v in acc:
                    accident.add(v)
        for ag in agent_list:
            if ag:
                for v in ag:
                    agents.add(v)
        for ct in ctx_list:
            if ct:
                for v in ct:
                    contexts.add(v)
        sr_inherited[ci_id] = {
            "accident_types": sorted(accident) if accident else None,
            "hazardous_agents": sorted(agents) if agents else None,
            "work_contexts": sorted(contexts) if contexts else None,
        }
    print(f"  {len(sr_inherited)} CIs with SR-inherited facets")

    # ═══ Step 2: 전체 CI 로드 + 태깅 ═══
    print("\n=== Track 2: All CI tagging ===")
    cur.execute("SELECT identifier, text, source_guide FROM checklist_items ORDER BY identifier")
    rows = cur.fetchall()
    print(f"  Total CIs: {len(rows)}")

    stats = {"sr_only": 0, "text_only": 0, "both": 0, "guide_only": 0, "none": 0}
    updates = []

    for identifier, text, source_guide in rows:
        final = {"accident_types": None, "hazardous_agents": None, "work_contexts": None}

        # SR 상속
        sr_facet = sr_inherited.get(identifier)
        has_sr = sr_facet and any(sr_facet.get(k) for k in ("accident_types", "hazardous_agents", "work_contexts"))

        # CI text 키워드 매칭
        text_facet = extract_facets_from_text(text)
        has_text = any(text_facet.get(k) for k in ("accident_types", "hazardous_agents", "work_contexts"))

        # 가이드 제목 기반
        guide_facet = guide_facets.get(source_guide, {})
        has_guide = any(guide_facet.get(k) for k in ("accident_types", "hazardous_agents", "work_contexts"))

        # 합산
        if has_sr:
            final = merge_facets(final, sr_facet)
        if has_text:
            final = merge_facets(final, text_facet)
        if has_guide:
            final = merge_facets(final, guide_facet)

        # 통계
        if has_sr and has_text:
            stats["both"] += 1
        elif has_sr:
            stats["sr_only"] += 1
        elif has_text:
            stats["text_only"] += 1
        elif has_guide:
            stats["guide_only"] += 1
        else:
            stats["none"] += 1

        updates.append((identifier, final))

    print(f"\n=== Tagging Stats ===")
    print(f"  SR+Text: {stats['both']}")
    print(f"  SR only: {stats['sr_only']}")
    print(f"  Text only: {stats['text_only']}")
    print(f"  Guide only: {stats['guide_only']}")
    print(f"  None: {stats['none']}")

    # ═══ Step 3: DB 업데이트 ═══
    print("\n=== Updating PostgreSQL ===")
    update_sql = """
        UPDATE checklist_items
        SET accident_types = %s::jsonb,
            hazardous_agents = %s::jsonb,
            work_contexts = %s::jsonb
        WHERE identifier = %s
    """

    batch_size = 1000
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        for identifier, facets in batch:
            cur.execute(update_sql, (
                json.dumps(facets["accident_types"]) if facets["accident_types"] else None,
                json.dumps(facets["hazardous_agents"]) if facets["hazardous_agents"] else None,
                json.dumps(facets["work_contexts"]) if facets["work_contexts"] else None,
                identifier,
            ))
        conn.commit()
        if (i + batch_size) % 5000 == 0 or i + batch_size >= len(updates):
            print(f"  Updated {min(i + batch_size, len(updates))}/{len(updates)}")

    # ═══ Step 4: 검증 ═══
    print("\n=== Verification ===")
    cur.execute("SELECT COUNT(*) FROM checklist_items WHERE accident_types IS NOT NULL OR hazardous_agents IS NOT NULL OR work_contexts IS NOT NULL")
    tagged = cur.fetchone()[0]
    total = len(updates)
    print(f"  CIs with at least 1 axis: {tagged}/{total} ({tagged*100//total}%)")

    cur.execute("SELECT COUNT(*) FROM checklist_items WHERE accident_types IS NULL AND hazardous_agents IS NULL AND work_contexts IS NULL")
    orphan = cur.fetchone()[0]
    print(f"  CIs with NO axis (still orphan): {orphan} ({orphan*100//total}%)")

    # 축별 분포 (상위 10)
    print("\n  [accident_type] top 10:")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(accident_types) as val FROM checklist_items WHERE accident_types IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    print("\n  [hazardous_agent] top 10:")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(hazardous_agents) as val FROM checklist_items WHERE hazardous_agents IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    print("\n  [work_context] top 10:")
    cur.execute("""
        SELECT val, COUNT(*) FROM (
            SELECT jsonb_array_elements_text(work_contexts) as val FROM checklist_items WHERE work_contexts IS NOT NULL
        ) t GROUP BY val ORDER BY count DESC LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    cur.close()
    conn.close()
    print(f"\n=== Done: {len(updates)} CIs processed ===")


if __name__ == "__main__":
    main()
