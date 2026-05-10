#!/usr/bin/env python3
"""DT/ES/WP faceted 태깅: 텍스트 키워드 + 가이드 title 기반.

- DomainTerm: term+definition → hazardous_agents, work_contexts
- EquipmentSpec: equipment_name → work_contexts
- WorkProcess: process_name+safety_measures → accident_types, work_contexts
"""

import json
import psycopg2

DB_PARAMS = dict(dbname="kosha", user="kosha", password="1229", host="localhost")

# 키워드 사전 (step6과 동일 기반)
AGENT_KEYWORDS = {
    "CHEMICAL": ["화학물질", "유해물질", "관리대상", "시약", "용제", "용액", "유기화합물"],
    "DUST": ["분진", "석면", "광물성", "금속분진", "용접흄"],
    "TOXIC": ["독성", "중독", "유독", "발암", "특정화학물질", "허용농도"],
    "CORROSION": ["부식", "산성", "알칼리", "강산"],
    "RADIATION": ["방사선", "비전리", "전리", "자외선", "레이저", "X선"],
    "FIRE": ["화재", "폭발", "인화", "발화", "가연", "위험물", "연소", "방폭"],
    "ELECTRICITY": ["전기", "감전", "정전기", "전압", "배선", "접지", "누전"],
    "ARC_FLASH": ["아크", "용접"],
    "NOISE": ["소음", "진동", "청력"],
    "HEAT_COLD": ["온도", "고열", "한랭", "냉동", "동상", "열사병"],
    "BIOLOGICAL": ["병원체", "감염", "세균", "바이러스", "혈액매개"],
}

CONTEXT_KEYWORDS = {
    "SCAFFOLD": ["비계", "틀비계", "달비계", "강관비계"],
    "CONFINED_SPACE": ["밀폐공간", "밀폐", "맨홀", "탱크내부"],
    "EXCAVATION": ["굴착", "굴삭", "터파기", "흙막이", "지보공"],
    "MACHINE": ["기계", "공작기계", "프레스", "전단기", "선반", "밀링", "드릴", "파쇄기", "혼합기", "교반기", "원심기", "사출"],
    "VEHICLE": ["차량", "지게차", "포크리프트", "화물차", "덤프"],
    "CRANE": ["크레인", "양중기", "호이스트", "리프트", "곤돌라", "달기구", "체인블록"],
    "CONVEYOR": ["컨베이어", "벨트"],
    "ROBOT": ["로봇", "산업용로봇"],
    "CONSTRUCTION_EQUIP": ["건설기계", "굴삭기", "불도저"],
    "RAIL": ["철도", "궤도"],
    "PRESSURE_VESSEL": ["압력용기", "보일러", "증기", "고압가스", "아세틸렌"],
    "STEELWORK": ["철골", "강구조물"],
    "MATERIAL_HANDLING": ["하역", "운반", "적재", "화물"],
    "ELECTRICAL_WORK": ["전기설비", "배전반", "변전소", "수전설비"],
    "CHEMICAL_WORK": ["화학설비", "특수화학설비", "배관"],
    "VENTILATION": ["환기", "국소배기", "전체환기"],
    "DEMOLITION": ["해체", "철거"],
}

ACCIDENT_KEYWORDS = {
    "FALL": ["추락", "떨어짐", "높이", "고소", "추락방호", "추락방지", "안전난간"],
    "COLLISION": ["충돌", "접촉", "운행", "주행", "차량"],
    "FALLING_OBJECT": ["낙하물", "비래", "투하", "낙하", "양중"],
    "CRUSH": ["끼임", "압착", "회전", "롤러", "프레스", "파쇄"],
    "CUT": ["절단", "톱", "절삭", "연삭", "연마", "그라인더"],
    "COLLAPSE": ["붕괴", "무너짐", "도괴"],
    "ERGONOMIC": ["근골격", "인력운반", "중량물", "허리"],
}


def extract_from_text(text, keyword_dict):
    """텍스트에서 키워드 매칭하여 코드 집합 반환."""
    found = set()
    for code, keywords in keyword_dict.items():
        if any(kw in text for kw in keywords):
            found.add(code)
    return sorted(found) if found else None


def main():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    # 가이드 제목 로드
    cur.execute("SELECT guide_code, title FROM kosha_guides")
    guide_titles = {gc: t for gc, t in cur.fetchall()}

    # ═══ DomainTerm 태깅 ═══
    print("=== DomainTerm Tagging ===")
    cur.execute("SELECT identifier, term, definition, source_guide FROM domain_terms ORDER BY identifier")
    dt_rows = cur.fetchall()
    dt_tagged = 0
    for identifier, term, definition, source_guide in dt_rows:
        combined = term + " " + (definition or "") + " " + guide_titles.get(source_guide, "")
        agents = extract_from_text(combined, AGENT_KEYWORDS)
        contexts = extract_from_text(combined, CONTEXT_KEYWORDS)
        if agents or contexts:
            dt_tagged += 1
        cur.execute(
            "UPDATE domain_terms SET hazardous_agents = %s::jsonb, work_contexts = %s::jsonb WHERE identifier = %s",
            (json.dumps(agents) if agents else None, json.dumps(contexts) if contexts else None, identifier)
        )
    conn.commit()
    print(f"  Total: {len(dt_rows)}, Tagged: {dt_tagged} ({dt_tagged*100//len(dt_rows)}%)")

    # ═══ EquipmentSpec 태깅 ═══
    print("\n=== EquipmentSpec Tagging ===")
    cur.execute("SELECT identifier, equipment_name, source_guide FROM equipment_specs ORDER BY identifier")
    es_rows = cur.fetchall()
    es_tagged = 0
    for identifier, equipment_name, source_guide in es_rows:
        combined = equipment_name + " " + guide_titles.get(source_guide, "")
        contexts = extract_from_text(combined, CONTEXT_KEYWORDS)
        if contexts:
            es_tagged += 1
        cur.execute(
            "UPDATE equipment_specs SET work_contexts = %s::jsonb WHERE identifier = %s",
            (json.dumps(contexts) if contexts else None, identifier)
        )
    conn.commit()
    print(f"  Total: {len(es_rows)}, Tagged: {es_tagged} ({es_tagged*100//len(es_rows)}%)")

    # ═══ WorkProcess 태깅 ═══
    print("\n=== WorkProcess Tagging ===")
    cur.execute("SELECT identifier, process_name, safety_measures, source_guide FROM work_processes ORDER BY identifier")
    wp_rows = cur.fetchall()
    wp_tagged = 0
    for identifier, process_name, safety_measures, source_guide in wp_rows:
        combined = process_name + " " + (safety_measures or "") + " " + guide_titles.get(source_guide, "")
        accidents = extract_from_text(combined, ACCIDENT_KEYWORDS)
        contexts = extract_from_text(combined, CONTEXT_KEYWORDS)
        if accidents or contexts:
            wp_tagged += 1
        cur.execute(
            "UPDATE work_processes SET accident_types = %s::jsonb, work_contexts = %s::jsonb WHERE identifier = %s",
            (json.dumps(accidents) if accidents else None, json.dumps(contexts) if contexts else None, identifier)
        )
    conn.commit()
    print(f"  Total: {len(wp_rows)}, Tagged: {wp_tagged} ({wp_tagged*100//len(wp_rows)}%)")

    # ═══ 검증 ═══
    print("\n=== Summary ===")
    for table, cols in [
        ("domain_terms", ["hazardous_agents", "work_contexts"]),
        ("equipment_specs", ["work_contexts"]),
        ("work_processes", ["accident_types", "work_contexts"]),
    ]:
        where = " OR ".join(f"{c} IS NOT NULL" for c in cols)
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}")
        tagged = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        print(f"  {table}: {tagged}/{total} ({tagged*100//total}%)")

    cur.close()
    conn.close()
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
