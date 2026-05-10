#!/usr/bin/env python3
"""Step 6 v2 검증 (Multi-SR Pilot): R1~R11, R13, R14 (v1 동일) + R12V2, R15, R16 (v2 신규).

v1 R12 (같은 article의 NS가 여러 SR에 분산되면 warning) → v2에서는 의도된 결과이므로 제거.
대신:
  - R12V2_PARA_SPLIT (ERROR): 같은 paragraph의 NS가 여러 SR에 분산되면 paragraph 단위 무결성 위반
  - R15_TITLE_PARAGRAPH_PREFIX (WARNING): title이 "제N조 제M항:" 또는 "제N조:" prefix로 시작하지 않으면 인위 분할 의심
  - R16_HAZARD_DIVERSITY (INFO): 같은 article의 모든 v2 SR이 동일 hazard set만 가지면 분리 효과 의문

Usage:
    PYTHONUTF8=1 python scripts/pilot/step6_validate_sr_v2.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPE_A_ROOT = SCRIPT_DIR.parent.parent  # pipe-A/
DATA_DIR = PIPE_A_ROOT / "data"
SR_DIR_V2 = DATA_DIR / "pilot" / "safety-requirements-v2"

sys.path.insert(0, str(PIPE_A_ROOT / "scripts"))
from step6_validate_sr import (  # noqa: E402
    ARTICLE_CODE_PATTERN,
    SR_ID_PATTERN,
    VALID_HAZARD_KEYWORDS,
    VALID_REQUIREMENT_TYPES,
    ValidationReport,
    load_all_ns,
    load_articles,
    load_penalty_routes,
)

PARA_NORM_RE = re.compile(r"^(제\d+조(?:의\d+)? 제\d+항)")
TITLE_PREFIX_RE = re.compile(r"^제\d+조(?:의\d+)?(?:\s+제\d+항)?:")


def normalize_para(pref: str | None) -> str:
    if not pref:
        return "본문"
    m = PARA_NORM_RE.match(pref)
    return m.group(1) if m else pref


def load_all_sr_v2(sr_dir: Path = SR_DIR_V2) -> list[dict]:
    all_sr: list[dict] = []
    for sr_file in sorted(sr_dir.glob("sr-batch-PILOT-*.json")):
        if sr_file.name.endswith("-input.json"):
            continue
        with open(sr_file, encoding="utf-8") as f:
            data = json.load(f)
        all_sr.extend(data.get("safetyRequirements", []))
    return all_sr


def validate_v2(all_sr, all_ns, article_codes, penalties) -> ValidationReport:
    """v2 검증: R1~R11, R13, R14 그대로 + R12V2, R15, R16 추가."""
    report = ValidationReport()
    seen_ids: set[str] = set()
    sr_ids = {sr["identifier"] for sr in all_sr}

    # 사전 계산: paragraph → SR 집합
    para_to_srs: dict[tuple[str, str], set[str]] = defaultdict(set)
    article_to_sr_hazards: dict[str, list[set[str]]] = defaultdict(list)
    article_to_sr_ids: dict[str, set[str]] = defaultdict(set)
    for sr in all_sr:
        sr_id = sr["identifier"]
        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns:
                key = (ns["articleCode"], normalize_para(ns.get("paragraphRef")))
                para_to_srs[key].add(sr_id)
        for ac in sr.get("referencesArticle", []):
            article_to_sr_ids[ac].add(sr_id)
            article_to_sr_hazards[ac].append(frozenset(sr.get("addressesHazard", [])))

    for sr in all_sr:
        sr_id = sr.get("identifier", "UNKNOWN")

        # R1 ~ R10 (v1 동일)
        for field in ["identifier", "title", "text", "requirementType",
                      "bindingForce", "referencesArticle", "mandatedBy", "addressesHazard"]:
            if field not in sr:
                report.error("R1_SCHEMA", sr_id, f"필수 필드 누락: {field}")

        if sr_id in seen_ids:
            report.error("R2_DUPLICATE_ID", sr_id, "identifier 중복")
        seen_ids.add(sr_id)

        if not SR_ID_PATTERN.match(sr_id):
            report.error("R3_ID_FORMAT", sr_id, f"identifier 형식 불일치: {sr_id}")

        for ns_id in sr.get("mandatedBy", []):
            if ns_id not in all_ns:
                report.error("R4_FK_NS", sr_id, f"mandatedBy NS 미존재: {ns_id}")

        for article_code in sr.get("referencesArticle", []):
            if not ARTICLE_CODE_PATTERN.match(article_code):
                report.error("R5_FK_ARTICLE", sr_id, f"조문코드 형식 오류: {article_code}")
            elif ("RULE", article_code) not in article_codes:
                report.error("R5_FK_ARTICLE", sr_id, f"articles 테이블에 미존재: RULE.{article_code}")

        sanction = sr.get("hasSanction")
        if sanction:
            for article_code in sr.get("referencesArticle", []):
                route = penalties.get("routes", {}).get(article_code)
                if route and route.get("hasPenalty") and not sanction.get("criminal"):
                    report.error("R6_SANCTION_MISMATCH", sr_id,
                                 f"penalty-routes에 형사벌 있으나 SR에 없음: {article_code}")

        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns and ns.get("hasModality") not in {"OBLIGATION", "PROHIBITION"}:
                report.error("R7_MODALITY_FILTER", sr_id,
                             f"mandatedBy에 {ns['hasModality']} NS 포함: {ns_id}")

        if not sr.get("text", "").strip():
            report.error("R8_EMPTY_TEXT", sr_id, "text가 비어있음")

        if sr.get("requirementType") not in VALID_REQUIREMENT_TYPES:
            report.error("R9_INVALID_TYPE", sr_id,
                         f"유효하지 않은 requirementType: {sr.get('requirementType')}")

        for hazard in sr.get("addressesHazard", []):
            if hazard not in VALID_HAZARD_KEYWORDS:
                report.error("R10_INVALID_HAZARD", sr_id, f"비표준 hazard 키워드: {hazard}")

        # R11: QUANTITATIVE 조건 → structuralRequirements
        struct_req = sr.get("structuralRequirements")
        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns:
                cond = ns.get("hasCondition")
                if cond and cond.get("conditionType") == "QUANTITATIVE":
                    has_items = (isinstance(struct_req, dict) and bool(struct_req.get("items"))) \
                        or (isinstance(struct_req, list) and len(struct_req) > 0)
                    if not has_items:
                        report.warn("R11_QUANT_MISSING", sr_id,
                                    f"QUANTITATIVE 조건 있으나 structuralRequirements 없음: {ns_id}")

        # ── R12V2 (신규, ERROR): paragraph 무결성 ──
        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns:
                key = (ns["articleCode"], normalize_para(ns.get("paragraphRef")))
                srs = para_to_srs.get(key, set())
                if len(srs) > 1 and sr_id in srs:
                    report.error("R12V2_PARA_SPLIT", sr_id,
                                 f"같은 paragraph {key}의 NS가 여러 SR에 분산: {srs}")
                    break  # 같은 SR 안에서 같은 위반은 1번만 보고

        # R13: title-text 일관성 (v1 동일)
        title_words = [w for w in sr.get("title", "").split() if len(w) > 1]
        text = sr.get("text", "")
        if title_words:
            match_ratio = sum(1 for w in title_words if w in text) / len(title_words)
            if match_ratio < 0.3:
                report.warn("R13_TITLE_TEXT_MISMATCH", sr_id,
                            f"title 키워드의 {match_ratio:.0%}만 text에 포함")

        # R14: hasModificationLink target 존재
        mod_link = sr.get("hasModificationLink")
        if mod_link and mod_link.get("modifiesSR"):
            target_sr = mod_link["modifiesSR"]
            if target_sr not in sr_ids:
                report.warn("R14_MOD_TARGET_MISSING", sr_id,
                            f"hasModificationLink 대상 SR 미존재: {target_sr}")

        # ── R15 (신규, WARNING): title prefix 검사 ──
        title = sr.get("title", "")
        if not TITLE_PREFIX_RE.match(title):
            report.warn("R15_TITLE_PARAGRAPH_PREFIX", sr_id,
                        f"title이 '제N조 제M항:' prefix로 시작하지 않음 — 인위 분할 의심: {title[:40]}")

    # ── R16 (신규, INFO): article별 hazard 다양성 ──
    for ac, hazards_list in article_to_sr_hazards.items():
        if len(hazards_list) > 1:
            unique_hazard_sets = set(hazards_list)
            if len(unique_hazard_sets) == 1:
                # 같은 article의 모든 SR이 동일 hazard set 사용
                sample_sr = sorted(article_to_sr_ids[ac])[0]
                report.warn("R16_HAZARD_DIVERSITY", sample_sr,
                            f"article {ac}의 SR {len(hazards_list)}개 모두 동일 hazard "
                            f"{set(hazards_list[0])} — 분리 효과 의문")

    return report


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Step 6 v2 SR 검증 (Pilot)")
    parser.add_argument("--sr-dir", type=Path, default=SR_DIR_V2)
    args = parser.parse_args()

    print(f"[1/4] Pilot SR 파일 로드 ({args.sr_dir})...")
    all_sr = load_all_sr_v2(args.sr_dir)
    print(f"       총 SR: {len(all_sr)}개")
    if not all_sr:
        print("[INFO] SR 파일 없음. Step 3 (LLM agent) 완료 후 다시 실행.")
        return

    print("[2/4] NS 데이터 로드...")
    all_ns = load_all_ns()
    print(f"       총 NS: {len(all_ns)}개")

    print("[3/4] 참조 데이터 로드...")
    article_codes = load_articles()
    penalties = load_penalty_routes()

    print("[4/4] 검증 (R1~R11, R12V2, R13~R16)...")
    report = validate_v2(all_sr, all_ns, article_codes, penalties)

    print(f"\n{'='*60}")
    print(f"v2 SR 검증 결과 (Pilot)")
    print(f"{'='*60}")
    print(f"  총 SR: {len(all_sr)}개")
    print(f"  ERROR: {len(report.errors)}건")
    print(f"  WARNING: {len(report.warnings)}건")

    if report.errors:
        print(f"\nERRORS:")
        for e in report.errors[:50]:
            print(f"  [{e['rule']}] {e['srId']}: {e['message']}")
        if len(report.errors) > 50:
            print(f"  ... 외 {len(report.errors) - 50}건")

    if report.warnings:
        print(f"\nWARNINGS by rule:")
        warn_by_rule: dict[str, list] = defaultdict(list)
        for w in report.warnings:
            warn_by_rule[w["rule"]].append(w)
        for rule in sorted(warn_by_rule):
            ws = warn_by_rule[rule]
            print(f"  [{rule}] {len(ws)}건")
            for w in ws[:5]:
                print(f"      {w['srId']}: {w['message']}")
            if len(ws) > 5:
                print(f"      ... 외 {len(ws) - 5}건")

    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
