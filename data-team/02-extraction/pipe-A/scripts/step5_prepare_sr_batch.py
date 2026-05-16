#!/usr/bin/env python3
"""Step 5 준비: LLM 에이전트용 SR 배치 입력 JSON 생성 (카테고리 기반).

배치 전략: 같은 카테고리의 SR은 같은 배치(들)에 연속 배치.
소규모(5개 이하) 카테고리는 관련 카테고리와 묶음.

Usage:
    python3 step5_prepare_sr_batch.py --all --batch-size 20
    python3 step5_prepare_sr_batch.py --all --batch-size 20 --dry-run
"""

import argparse, json, math, re, sys
from collections import defaultdict, OrderedDict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
NS_DIR = DATA_DIR / "norm-statements"
SR_DIR = DATA_DIR / "safety-requirements"
CONFIG_DIR = PROJECT_ROOT / "config"

SMALL_CATEGORY_MERGES = {
    frozenset(["PPE", "WELFARE"]): "PPE-WELFARE",
    frozenset(["STEELWORK", "DEMOLITION"]): "STEELWORK-DEMOLITION",
    frozenset(["ROBOT", "SPECIAL_WORKER", "CONVEYOR"]): "ROBOT-CONVEYOR-SPECIAL",
    frozenset(["WASTE"]): "WASTE",
}

CATEGORY_DESCRIPTIONS = {
    "WORKPLACE":"작업장 바닥·조명·환기 등","PASSAGE":"통로·사다리·계단","PPE":"보호구 지급·관리",
    "MGMT":"관리감독자 직무","FALL":"추락 방지","COLLAPSE":"붕괴·도괴 방지",
    "SCAFFOLD":"비계 재료·구조·조립","VENTILATION":"환기장치","WELFARE":"휴게시설·세면",
    "WASTE":"잔재물 조치","MACHINE":"기계·기구 안전","CRANE":"크레인 안전",
    "LIFTING":"양중기 총칙·리프트","RIGGING":"달기기구·와이어로프","VEHICLE":"지게차·운반차·화물차",
    "CONVEYOR":"컨베이어","CONSTRUCTION_EQUIP":"건설기계·항타기","ROBOT":"산업용 로봇",
    "FIRE_EXPLOSION":"폭발·화재·위험물","ELECTRIC":"전기기계·배선·전기작업",
    "SHORING":"거푸집·동바리","EXCAVATION":"굴착·발파·터널","STEELWORK":"철골 조립",
    "DEMOLITION":"해체작업","HEAVY_LOAD":"중량물 취급","CARGO":"화물취급·항만하역",
    "LOGGING":"벌목작업","RAIL":"궤도·열차","CHEMICAL":"유해물질 취급·보호",
    "HAZMAT":"허가대상 유해물질·석면","PROHIBITED_CHEM":"금지유해물질",
    "NOISE":"소음·진동","PRESSURE":"이상기압·잠수","HEAT":"고열·한냉·폭염",
    "RADIATION":"방사선","PATHOGEN":"병원체·감염","DUST":"분진",
    "CONFINED":"밀폐공간","OFFICE":"사무실 공기질","ERGONOMIC":"근골격계 부담작업",
    "OTHER_HAZARD":"기타 유해인자","SPECIAL_WORKER":"특수형태근로종사자",
}


def load_all_ns():
    all_ns = []
    for f in sorted(NS_DIR.glob("ns-batch-*.json")):
        with open(f, encoding="utf-8") as fh:
            all_ns.extend(json.load(fh).get("normStatements", []))
    return all_ns

def load_penalties():
    p = DATA_DIR / "penalty-routes.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}

def load_category_map():
    return json.load(open(CONFIG_DIR / "sr-section-category-map.json", encoding="utf-8"))

def load_articles():
    return json.load(open(DATA_DIR / "article-texts.json", encoding="utf-8"))

def match_category(section, cat_map):
    entry = cat_map.get(section)
    if entry:
        return {"category": entry["category"], "description": entry.get("description",""), "skipSR": entry.get("skipSR", False)}
    return {"category": "UNCATEGORIZED", "description": "매칭 실패: " + section, "skipSR": False}

def build_sr_id(cat, seq):
    return f"SR-{cat}-{seq:03d}"

def build_sanction(ns_list):
    for ns in ns_list:
        s = ns.get("hasSanction")
        if s: return s
    return None


def main():
    parser = argparse.ArgumentParser(description="Step 5 SR 배치 (카테고리 기반)")
    parser.add_argument("--all", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--small-threshold", type=int, default=5)
    args = parser.parse_args()

    print("[1/5] NS 데이터 로드...")
    all_ns = load_all_ns()
    print(f"       총 NS: {len(all_ns)}개")

    print("[2/5] 설정 파일 로드...")
    penalties = load_penalties()
    cat_map = load_category_map()
    articles_data = load_articles()

    # 커버리지 검증: 모든 RULE section이 카테고리 맵에 있는지 확인
    rule_sections = set(a.get("section","") for a in articles_data["laws"].get("RULE",{}).values() if a.get("section"))
    map_sections = set(k for k in cat_map if not k.startswith("_"))
    uncovered = rule_sections - map_sections
    if uncovered:
        print(f"  WARNING: {len(uncovered)} sections not in category map:")
        for s in sorted(uncovered):
            print(f"    - {s}")
    else:
        print(f"       카테고리 맵 커버리지: {len(rule_sections)}/{len(rule_sections)} (100%)")

    target_ns = [ns for ns in all_ns if ns.get("hasModality") in {"OBLIGATION","PROHIBITION"}]
    print(f"[3/5] OBLIGATION/PROHIBITION 필터: {len(target_ns)}개")

    article_groups = defaultdict(list)
    for ns in target_ns:
        article_groups[ns["articleCode"]].append(ns)

    # 카테고리별 SR 그룹 생성
    cat_sr = defaultdict(list)
    cat_counters = defaultdict(int)

    for ac in sorted(article_groups, key=lambda x: int(re.search(r"\d+", x).group())):
        ns_list = article_groups[ac]
        rule_art = articles_data["laws"].get("RULE",{}).get(ac,{})
        section = rule_art.get("section","")
        ci = match_category(section, cat_map)
        if ci["skipSR"]: continue

        cat = ci["category"]
        cat_counters[cat] += 1
        sr_id = build_sr_id(cat, cat_counters[cat])
        sanction = build_sanction(ns_list)

        all_art_ns = [ns for ns in all_ns if ns["articleCode"]==ac]
        exempt_ns = [ns for ns in all_art_ns if ns.get("hasModality")=="EXEMPTION" and ns.get("hasModificationLink")]

        quant = [{"nsId":ns["identifier"],"text":ns["hasCondition"]["text"]}
                 for ns in ns_list if ns.get("hasCondition",{}) and
                 isinstance(ns.get("hasCondition"), dict) and
                 ns["hasCondition"].get("conditionType")=="QUANTITATIVE"]

        cat_sr[cat].append({
            "preAssignedId": sr_id, "articleCode": ac, "title": rule_art.get("title",""),
            "section": section, "category": cat,
            "nsGroup": [{"identifier":n["identifier"],"paragraphRef":n["paragraphRef"],
                         "text":n["text"],"hasModality":n["hasModality"],
                         "hasSubjectRole":n.get("hasSubjectRole"),"hasAction":n.get("hasAction"),
                         "hasObject":n.get("hasObject"),"hasCondition":n.get("hasCondition")}
                        for n in ns_list],
            "exemptionNS": [{"identifier":n["identifier"],"text":n["text"],
                             "hasModificationLink":n["hasModificationLink"]} for n in exempt_ns],
            "quantitativeConditions": quant,
            "hasSanction": sanction,
        })

    total_sr = sum(len(v) for v in cat_sr.values())
    print(f"[4/5] SR 그룹: {total_sr}개 ({len(cat_sr)}개 카테고리)")

    print("\n       카테고리별 SR 수:")
    for c in sorted(cat_sr, key=lambda c: -len(cat_sr[c])):
        n = len(cat_sr[c])
        nb = max(1, math.ceil(n/args.batch_size))
        sm = " (소규모)" if n <= args.small_threshold else ""
        print(f"         {c}: {n}개 → {nb}배치{sm}")

    # 소규모 카테고리 묶기
    small_cats = {c for c,g in cat_sr.items() if len(g) <= args.small_threshold}
    merged = OrderedDict()
    already = set()

    for merge_set, label in SMALL_CATEGORY_MERGES.items():
        cats_in = merge_set & set(cat_sr) & small_cats
        if cats_in:
            combined = []
            for c in sorted(cats_in): combined.extend(cat_sr[c]); already.add(c)
            if combined: merged[label] = combined

    remaining = []
    for c in small_cats - already: remaining.extend(cat_sr[c])
    if remaining: merged["MISC-SMALL"] = remaining

    for c in sorted(cat_sr, key=lambda c: -len(cat_sr[c])):
        if c not in small_cats: merged[c] = cat_sr[c]

    # 배치 생성
    batches = []
    for label, groups in merged.items():
        nb = max(1, math.ceil(len(groups)/args.batch_size))
        desc_cats = sorted(set(g["category"] for g in groups))
        desc = " + ".join(CATEGORY_DESCRIPTIONS.get(c,c) for c in desc_cats)

        for bi in range(nb):
            bg = groups[bi*args.batch_size : (bi+1)*args.batch_size]
            bid = f"sr-batch-{label}" if nb==1 else f"sr-batch-{label}-{bi+1:02d}"

            batches.append((bid, {
                "metadata": {"batchId": bid, "totalGroups": len(bg),
                             "articles": [g["articleCode"] for g in bg]},
                "categoryContext": {"categories": desc_cats, "totalSRsInCategory": len(groups),
                                    "batchNumber": bi+1, "totalBatches": nb, "description": desc},
                "srGroups": bg,
            }))

    print(f"\n       총 배치: {len(batches)}개")
    for bid, bd in batches:
        print(f"         {bid}: {bd['metadata']['totalGroups']}개 SR, cats={bd['categoryContext']['categories']}")

    if args.dry_run:
        print("\n[DRY-RUN] 파일 생성 없이 종료"); return

    SR_DIR.mkdir(parents=True, exist_ok=True)
    for bid, bd in batches:
        p = SR_DIR / f"{bid}-input.json"
        with open(p, "w", encoding="utf-8") as fh: json.dump(bd, fh, ensure_ascii=False, indent=2)
        print(f"  [OK] {p.name}: {bd['metadata']['totalGroups']} SR")

    print(f"\n[5/5] {len(batches)}개 배치 완료 (총 {total_sr} SR)")

if __name__ == "__main__":
    main()
