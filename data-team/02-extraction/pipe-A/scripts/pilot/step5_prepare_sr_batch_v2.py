#!/usr/bin/env python3
"""Step 5 v2 (Multi-SR Pilot): article 안의 NS를 paragraph 단위로 분할.

원본 step5_prepare_sr_batch.py 대비 변경:
  - article_groups → para_groups (key=(article_code, normalized_para))
  - pilot 샘플 article만 처리 (--articles-from sample-articles.json)
  - SR ID prefix: SR-PILOT_<CAT>-<seq>
  - 출력 dir 격리: data/pilot/safety-requirements-v2/
  - srGroup에 paragraphKey 필드 추가 (LLM 컨텍스트)
  - exemptionNS는 article 전체 그대로 (paragraph로 좁히면 누락 위험)

Usage:
  python3 step5_prepare_sr_batch_v2.py --articles-from data/pilot/sample-articles.json
  python3 step5_prepare_sr_batch_v2.py --articles-from data/pilot/sample-articles.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # pipe-A/
DATA_DIR = PROJECT_ROOT / "data"
NS_DIR = DATA_DIR / "norm-statements"
CONFIG_DIR = PROJECT_ROOT / "config"

DEFAULT_OUT_DIR = DATA_DIR / "pilot" / "safety-requirements-v2"

PARA_NORM_RE = re.compile(r"^(제\d+조(?:의\d+)? 제\d+항)")

SMALL_CATEGORY_MERGES = {
    frozenset(["PPE", "WELFARE"]): "PPE-WELFARE",
    frozenset(["STEELWORK", "DEMOLITION"]): "STEELWORK-DEMOLITION",
    frozenset(["ROBOT", "SPECIAL_WORKER", "CONVEYOR"]): "ROBOT-CONVEYOR-SPECIAL",
    frozenset(["WASTE"]): "WASTE",
}

CATEGORY_DESCRIPTIONS = {
    "WORKPLACE": "작업장 바닥·조명·환기 등", "PASSAGE": "통로·사다리·계단",
    "PPE": "보호구 지급·관리", "MGMT": "관리감독자 직무",
    "FALL": "추락 방지", "COLLAPSE": "붕괴·도괴 방지",
    "SCAFFOLD": "비계 재료·구조·조립", "VENTILATION": "환기장치",
    "WELFARE": "휴게시설·세면", "WASTE": "잔재물 조치",
    "MACHINE": "기계·기구 안전", "CRANE": "크레인 안전",
    "LIFTING": "양중기 총칙·리프트", "RIGGING": "달기기구·와이어로프",
    "VEHICLE": "지게차·운반차·화물차", "CONVEYOR": "컨베이어",
    "CONSTRUCTION_EQUIP": "건설기계·항타기", "ROBOT": "산업용 로봇",
    "FIRE_EXPLOSION": "폭발·화재·위험물", "ELECTRIC": "전기기계·배선·전기작업",
    "SHORING": "거푸집·동바리", "EXCAVATION": "굴착·발파·터널",
    "STEELWORK": "철골 조립", "DEMOLITION": "해체작업",
    "HEAVY_LOAD": "중량물 취급", "CARGO": "화물취급·항만하역",
    "LOGGING": "벌목작업", "RAIL": "궤도·열차",
    "CHEMICAL": "유해물질 취급·보호", "HAZMAT": "허가대상 유해물질·석면",
    "PROHIBITED_CHEM": "금지유해물질", "NOISE": "소음·진동",
    "PRESSURE": "이상기압·잠수", "HEAT": "고열·한냉·폭염",
    "RADIATION": "방사선", "PATHOGEN": "병원체·감염",
    "DUST": "분진", "CONFINED": "밀폐공간",
    "OFFICE": "사무실 공기질", "ERGONOMIC": "근골격계 부담작업",
    "OTHER_HAZARD": "기타 유해인자", "SPECIAL_WORKER": "특수형태근로종사자",
}


def normalize_para(pref: str | None) -> str:
    if not pref:
        return "본문"
    m = PARA_NORM_RE.match(pref)
    return m.group(1) if m else pref


def load_all_ns():
    all_ns = []
    for f in sorted(NS_DIR.glob("ns-batch-*.json")):
        with open(f, encoding="utf-8") as fh:
            all_ns.extend(json.load(fh).get("normStatements", []))
    return all_ns


def load_category_map():
    return json.load(open(CONFIG_DIR / "sr-section-category-map.json", encoding="utf-8"))


def load_articles():
    return json.load(open(DATA_DIR / "article-texts.json", encoding="utf-8"))


def load_sample_articles(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {s["articleCode"] for s in data["samples"]}


def match_category(section: str, cat_map: dict):
    entry = cat_map.get(section)
    if entry:
        return {"category": entry["category"], "skipSR": entry.get("skipSR", False)}
    return {"category": "UNCATEGORIZED", "skipSR": False}


def build_sr_id_pilot(cat: str, seq: int) -> str:
    return f"SR-PILOT_{cat}-{seq:03d}"


def build_sanction(ns_list):
    for ns in ns_list:
        s = ns.get("hasSanction")
        if s:
            return s
    return None


def para_sort_key(k: tuple[str, str]):
    ac, para = k
    m_ac = re.search(r"\d+", ac)
    m_p = re.search(r"제(\d+)항", para)
    return (int(m_ac.group()) if m_ac else 0,
            int(m_p.group(1)) if m_p else 0)


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Pilot Step 5 v2: paragraph 단위 multi-SR 배치 생성")
    parser.add_argument("--articles-from", type=Path, required=True,
                        help="sample-articles.json 경로 (Step 1 출력)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--small-threshold", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sample_codes = load_sample_articles(args.articles_from)
    print(f"[1/5] Sample articles: {len(sample_codes)}건")
    for ac in sorted(sample_codes, key=lambda x: int(re.search(r"\d+", x).group())):
        print(f"         {ac}")

    print("\n[2/5] NS 데이터 로드...")
    all_ns = load_all_ns()
    cat_map = load_category_map()
    articles_data = load_articles()
    print(f"       총 NS: {len(all_ns)}개")

    target_ns = [ns for ns in all_ns
                 if ns.get("hasModality") in {"OBLIGATION", "PROHIBITION"}
                 and ns.get("articleCode") in sample_codes]
    print(f"\n[3/5] OBLIGATION/PROHIBITION + sample article 필터: {len(target_ns)}개")

    # ─── 핵심 변경: paragraph 단위 그룹화 ───
    para_groups: dict[tuple[str, str], list] = defaultdict(list)
    for ns in target_ns:
        key = (ns["articleCode"], normalize_para(ns.get("paragraphRef")))
        para_groups[key].append(ns)
    print(f"       paragraph group: {len(para_groups)}개 (article {len(sample_codes)}건에서)")

    # 카테고리별 SR 그룹 생성
    cat_sr: dict[str, list] = defaultdict(list)
    cat_counters: dict[str, int] = defaultdict(int)

    for (ac, para_key) in sorted(para_groups, key=para_sort_key):
        ns_list = para_groups[(ac, para_key)]
        rule_art = articles_data["laws"].get("RULE", {}).get(ac, {})
        section = rule_art.get("section", "")
        ci = match_category(section, cat_map)
        if ci["skipSR"]:
            continue

        cat = ci["category"]
        cat_counters[cat] += 1
        sr_id = build_sr_id_pilot(cat, cat_counters[cat])
        sanction = build_sanction(ns_list)

        # exemption은 article 전체에서 (paragraph 단위로 좁히면 단서 NS 누락 위험)
        all_art_ns = [n for n in all_ns if n["articleCode"] == ac]
        exempt_ns = [n for n in all_art_ns
                     if n.get("hasModality") == "EXEMPTION"
                     and n.get("hasModificationLink")]

        quant = [{"nsId": n["identifier"], "text": n["hasCondition"]["text"]}
                 for n in ns_list
                 if isinstance(n.get("hasCondition"), dict)
                 and n["hasCondition"].get("conditionType") == "QUANTITATIVE"]

        cat_sr[cat].append({
            "preAssignedId": sr_id,
            "articleCode": ac,
            "paragraphKey": para_key,                 # ← 신규 (LLM 컨텍스트)
            "title": rule_art.get("title", ""),
            "section": section,
            "category": cat,
            "nsGroup": [{"identifier": n["identifier"],
                         "paragraphRef": n["paragraphRef"],
                         "text": n["text"],
                         "hasModality": n["hasModality"],
                         "hasSubjectRole": n.get("hasSubjectRole"),
                         "hasAction": n.get("hasAction"),
                         "hasObject": n.get("hasObject"),
                         "hasCondition": n.get("hasCondition")}
                        for n in ns_list],
            "exemptionNS": [{"identifier": n["identifier"],
                             "text": n["text"],
                             "hasModificationLink": n["hasModificationLink"]}
                            for n in exempt_ns],
            "quantitativeConditions": quant,
            "hasSanction": sanction,
        })

    total_sr = sum(len(v) for v in cat_sr.values())
    print(f"\n[4/5] SR 그룹: {total_sr}개 ({len(cat_sr)}개 카테고리)")
    for c in sorted(cat_sr, key=lambda c: -len(cat_sr[c])):
        n = len(cat_sr[c])
        print(f"         {c}: {n}개")

    # 소규모 카테고리 병합
    small_cats = {c for c, g in cat_sr.items() if len(g) <= args.small_threshold}
    merged: OrderedDict[str, list] = OrderedDict()
    already: set[str] = set()
    for merge_set, label in SMALL_CATEGORY_MERGES.items():
        cats_in = merge_set & set(cat_sr) & small_cats
        if cats_in:
            combined = []
            for c in sorted(cats_in):
                combined.extend(cat_sr[c])
                already.add(c)
            if combined:
                merged[label] = combined
    remaining = []
    for c in small_cats - already:
        remaining.extend(cat_sr[c])
    if remaining:
        merged["MISC-SMALL"] = remaining
    for c in sorted(cat_sr, key=lambda c: -len(cat_sr[c])):
        if c not in small_cats:
            merged[c] = cat_sr[c]

    # 배치 생성 (PILOT prefix)
    batches = []
    for label, groups in merged.items():
        nb = max(1, math.ceil(len(groups) / args.batch_size))
        desc_cats = sorted(set(g["category"] for g in groups))
        desc = " + ".join(CATEGORY_DESCRIPTIONS.get(c, c) for c in desc_cats)
        for bi in range(nb):
            bg = groups[bi * args.batch_size: (bi + 1) * args.batch_size]
            bid = f"sr-batch-PILOT-{label}" if nb == 1 else f"sr-batch-PILOT-{label}-{bi+1:02d}"
            batches.append((bid, {
                "metadata": {"batchId": bid,
                             "totalGroups": len(bg),
                             "articles": sorted(set(g["articleCode"] for g in bg))},
                "categoryContext": {"categories": desc_cats,
                                    "totalSRsInCategory": len(groups),
                                    "batchNumber": bi + 1,
                                    "totalBatches": nb,
                                    "description": desc},
                "srGroups": bg,
            }))

    print(f"\n[5/5] 총 배치: {len(batches)}개")
    for bid, bd in batches:
        print(f"         {bid}: {bd['metadata']['totalGroups']}개 SR, cats={bd['categoryContext']['categories']}")

    if args.dry_run:
        print("\n[DRY-RUN] 파일 생성 없이 종료")
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for bid, bd in batches:
        p = args.out_dir / f"{bid}-input.json"
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(bd, fh, ensure_ascii=False, indent=2)
        print(f"  [OK] {p.relative_to(PROJECT_ROOT)}: {bd['metadata']['totalGroups']} SR")

    print(f"\n[DONE] {len(batches)} 배치, 총 {total_sr} SR groups → {args.out_dir.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
