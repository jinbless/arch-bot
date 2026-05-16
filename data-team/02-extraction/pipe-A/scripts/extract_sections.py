#!/usr/bin/env python3
"""128개 고유 RULE section을 전수 추출하여 section→category 매핑 템플릿을 생성.

편/장/절/관 계층 구조를 정규식으로 파싱하여 규칙 기반으로 카테고리를 결정한다.
외부 config 파일 의존 없이 독립 실행 가능.

Usage:
    python3 extract_sections.py
"""

import json, re
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"

# ── 규칙 테이블 ──────────────────────────────────────────────
# (편, 장, 절, 관, category, description [, skipSR])
# 구체적 패턴(관>절>장>편)이 먼저 매칭되도록 정렬.
SECTION_RULES = [
    # 편1 총칙
    ("편1", "장1",  None,  None, "GENERAL",     "정의·적용범위",                True),
    ("편1", "장2",  None,  None, "WORKPLACE",   "작업장 바닥·조명·환기 등 일반 기준"),
    ("편1", "장3",  None,  None, "PASSAGE",     "통로·사다리·계단 설치 기준"),
    ("편1", "장4",  None,  None, "PPE",         "보호구 지급·관리·전용"),
    ("편1", "장5",  None,  None, "MGMT",        "관리감독자 직무, 사용 제한"),
    ("편1", "장6",  "절1", None, "FALL",        "추락 방지 (안전난간, 방호망, 안전대)"),
    ("편1", "장6",  "절2", None, "COLLAPSE",    "붕괴·도괴 방지"),
    ("편1", "장7",  None,  None, "SCAFFOLD",    "비계 재료·구조·조립·해체"),
    ("편1", "장8",  None,  None, "VENTILATION", "환기장치 설치·관리"),
    ("편1", "장9",  None,  None, "WELFARE",     "휴게시설·세면·세척"),
    ("편1", "장10", None,  None, "WASTE",       "잔재물 조치 기준"),
    # 편2 안전기준 — 장1 기계 (관/절 단위)
    ("편2", "장1", "절9",  "관2", "CRANE",             "크레인 안전 조치"),
    ("편2", "장1", "절9",  "관3", "CRANE",             "이동식 크레인"),
    ("편2", "장1", "절9",  "관7", "RIGGING",           "달기기구·와이어로프 안전계수"),
    ("편2", "장1", "절9",  None,  "LIFTING",           "양중기 총칙·리프트·곤돌라·승강기"),
    ("편2", "장1", "절10", None,  "VEHICLE",           "지게차·구내운반차·고소작업대·화물차"),
    ("편2", "장1", "절11", None,  "CONVEYOR",          "컨베이어 안전"),
    ("편2", "장1", "절12", None,  "CONSTRUCTION_EQUIP","차량계 건설기계·항타기·굴착기"),
    ("편2", "장1", "절13", None,  "ROBOT",             "산업용 로봇 안전"),
    ("편2", "장1", None,   None,  "MACHINE",           "기계·기구 일반 안전 기준 (기본값)"),
    # 편2 안전기준 — 장2~8
    ("편2", "장2", None,  None, "FIRE_EXPLOSION", "폭발·화재·위험물·화학설비·건조설비·용접"),
    ("편2", "장3", None,  None, "ELECTRIC",       "전기기계·배선·전기작업·정전기"),
    ("편2", "장4", "절1", None, "SHORING",        "거푸집·동바리 재료·조립·콘크리트"),
    ("편2", "장4", "절2", None, "EXCAVATION",     "노천굴착·발파·터널·교량·채석·잠함·가설도로"),
    ("편2", "장4", "절3", None, "STEELWORK",      "철골 조립·승강로·가설통로"),
    ("편2", "장4", "절4", None, "DEMOLITION",     "해체작업 위험방지"),
    ("편2", "장5", None,  None, "HEAVY_LOAD",     "중량물 취급 위험방지"),
    ("편2", "장6", None,  None, "CARGO",          "화물취급·항만하역"),
    ("편2", "장7", None,  None, "LOGGING",        "벌목작업 위험방지"),
    ("편2", "장8", None,  None, "RAIL",           "궤도·열차 관련 작업"),
    # 편3 보건기준
    ("편3", "장1",  None, None, "CHEMICAL",       "관리대상 유해물질 취급·보호"),
    ("편3", "장2",  None, None, "HAZMAT",         "허가대상 유해물질·석면·베릴륨"),
    ("편3", "장3",  None, None, "PROHIBITED_CHEM","금지유해물질 취급"),
    ("편3", "장4",  None, None, "NOISE",          "소음·진동 건강장해 예방"),
    ("편3", "장5",  None, None, "PRESSURE",       "이상기압·잠수 작업"),
    ("편3", "장6",  None, None, "HEAT",           "고열·한냉·폭염 작업"),
    ("편3", "장7",  None, None, "RADIATION",      "방사선 건강장해 예방"),
    ("편3", "장8",  None, None, "PATHOGEN",       "병원체·혈액·감염 예방"),
    ("편3", "장9",  None, None, "DUST",           "분진 건강장해 예방"),
    ("편3", "장10", None, None, "CONFINED",       "밀폐공간 작업 안전"),
    ("편3", "장11", None, None, "OFFICE",         "사무실 공기질·건강"),
    ("편3", "장12", None, None, "ERGONOMIC",      "근골격계 부담작업·중량물 인력운반"),
    ("편3", "장13", None, None, "OTHER_HAZARD",   "기타 유해인자"),
    # 편4
    ("편4", None, None, None, "SPECIAL_WORKER", "특수형태근로종사자 안전·보건"),
]

# ── 정규식: section 문자열에서 편/장/절/관 번호 추출 ──────────
_RE_LEVEL = {
    "편": re.compile(r"편(\d+)"),
    "장": re.compile(r"장(\d+)"),
    "절": re.compile(r"절(\d+)"),
    "관": re.compile(r"관(\d+)"),
}


def _parse_levels(section: str) -> dict:
    """section 문자열에서 편/장/절/관 번호를 추출하여 dict 반환."""
    result = {}
    for level, pat in _RE_LEVEL.items():
        m = pat.search(section)
        if m:
            result[level] = level + m.group(1)   # "편1", "장10" 등
    return result


def classify_section(section: str):
    """규칙 테이블에서 가장 구체적으로 매칭되는 카테고리를 반환.
    반환: (category, description, skipSR)
    """
    levels = _parse_levels(section)

    best = None
    best_specificity = -1

    for rule in SECTION_RULES:
        r_편, r_장, r_절, r_관 = rule[0], rule[1], rule[2], rule[3]
        category, description = rule[4], rule[5]
        skip = rule[6] if len(rule) > 6 else False

        # 각 수준이 일치하는지 확인
        specificity = 0
        match = True

        for level_key, r_val in [("편", r_편), ("장", r_장), ("절", r_절), ("관", r_관)]:
            if r_val is None:
                continue
            if levels.get(level_key) == r_val:
                specificity += 1
            else:
                match = False
                break

        if match and specificity > best_specificity:
            best_specificity = specificity
            best = (category, description, skip)

    if best is None:
        return "NEEDS_ASSIGNMENT", "", False
    return best


def load_articles():
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        return json.load(f)


def extract_unique_sections(articles):
    """RULE 조문에서 고유 section 전수 추출. section별 조문 수도 집계."""
    rules = articles["laws"].get("RULE", {})
    section_articles = defaultdict(list)
    for ac, art in rules.items():
        sec = art.get("section", "")
        if sec:
            section_articles[sec].append(ac)
    return section_articles


def main():
    articles = load_articles()
    section_articles = extract_unique_sections(articles)

    print(f"고유 section 수: {len(section_articles)}")
    print()

    template = {}
    stats = {"matched": 0, "unmatched": 0}

    for section in sorted(section_articles.keys()):
        art_codes = sorted(section_articles[section],
                          key=lambda x: int(re.search(r"\d+", x).group()))
        cat, desc, skip = classify_section(section)

        entry = {
            "category": cat,
            "description": desc,
            "articleCount": len(art_codes),
            "articles": art_codes[:5],
        }
        if skip:
            entry["skipSR"] = True

        template[section] = entry

        if cat == "NEEDS_ASSIGNMENT":
            stats["unmatched"] += 1
        else:
            stats["matched"] += 1

    print(f"=== 분류 결과 ===")
    print(f"  matched:   {stats['matched']}건")
    print(f"  unmatched: {stats['unmatched']}건")
    print()

    if stats["unmatched"] > 0:
        for section, entry in template.items():
            if entry["category"] == "NEEDS_ASSIGNMENT":
                print(f"  [unmatched] {section} ({entry['articleCount']}조문)")

    # 템플릿 저장
    out_path = CONFIG_DIR / "sr-section-category-map-template.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"\n템플릿 저장: {out_path}")

    # 카테고리별 요약
    cat_counts = defaultdict(int)
    for entry in template.values():
        cat_counts[entry["category"]] += 1
    print(f"\n=== 카테고리별 section 수 ===")
    for cat in sorted(cat_counts, key=lambda c: -cat_counts[c]):
        print(f"  {cat}: {cat_counts[cat]}")


if __name__ == "__main__":
    main()
