#!/usr/bin/env python3
"""Step 6 검증: SR 파일에 대한 14개 규칙 검증.

구조적 검증 (Hard Error, R1~R10) + 의미적 검증 (Warning, R11~R14).

Usage:
    python3 step6_validate_sr.py
    python3 step6_validate_sr.py --sr-dir data/safety-requirements
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
SR_DIR = DATA_DIR / "safety-requirements"
NS_DIR = DATA_DIR / "norm-statements"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
CONFIG_DIR = PROJECT_ROOT / "config"

sys.path.insert(0, str(SCRIPT_DIR))
# schema_validator not used directly in validation loop

# ── 상수 ──

VALID_REQUIREMENT_TYPES = {
    "PHYSICAL_PROTECTION", "PPE_REQUIREMENT", "PROCEDURAL", "TRAINING",
    "EQUIPMENT_STANDARD", "ENVIRONMENTAL", "MANAGEMENT_SYSTEM", "EMERGENCY_RESPONSE"
}

VALID_HAZARD_KEYWORDS = {
    "FALL", "COLLAPSE", "STRUCK_BY", "CAUGHT_IN", "ELECTRIC_SHOCK",
    "FIRE_EXPLOSION", "CHEMICAL_EXPOSURE", "ERGONOMIC", "CONFINED_SPACE",
    "SCAFFOLDING", "NOISE_VIBRATION", "HEAT_COLD"
}

SR_ID_PATTERN = re.compile(r"^SR-[A-Z_]+-[0-9]+$")
NS_ID_PATTERN = re.compile(r"^NS-[A-Z0-9]+-[0-9A-Z]+$")
ARTICLE_CODE_PATTERN = re.compile(r"^제\d+조(의\d+)?$")


def load_all_sr():
    """sr-batch-*.json 파일에서 전체 SR 로드."""
    all_sr = []
    for sr_file in sorted(SR_DIR.glob("sr-batch-*.json")):
        if sr_file.name.endswith("-input.json"):
            continue
        with open(sr_file, encoding="utf-8") as f:
            data = json.load(f)
        all_sr.extend(data.get("safetyRequirements", []))
    return all_sr


def load_all_ns():
    """ns-batch-*.json 파일에서 전체 NS 로드."""
    all_ns = {}
    for ns_file in sorted(NS_DIR.glob("ns-batch-*.json")):
        with open(ns_file, encoding="utf-8") as f:
            data = json.load(f)
        for ns in data.get("normStatements", []):
            all_ns[ns["identifier"]] = ns
    return all_ns


def load_articles():
    """article-texts.json에서 RULE 조문코드 집합 로드."""
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        data = json.load(f)
    codes = set()
    for law_id, articles in data["laws"].items():
        for code in articles:
            codes.add((law_id, code))
    return codes


def load_penalty_routes():
    """penalty-routes.json 로드."""
    path = DATA_DIR / "penalty-routes.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, rule: str, sr_id: str, message: str):
        self.errors.append({"rule": rule, "srId": sr_id, "message": message})

    def warn(self, rule: str, sr_id: str, message: str):
        self.warnings.append({"rule": rule, "srId": sr_id, "message": message})


def validate(all_sr: list, all_ns: dict, article_codes: set, penalties: dict) -> ValidationReport:
    report = ValidationReport()
    seen_ids = set()
    sr_ids = {sr["identifier"] for sr in all_sr}

    for sr in all_sr:
        sr_id = sr.get("identifier", "UNKNOWN")

        # R1: JSON Schema (별도 실행, 여기서는 필수 필드 존재만 확인)
        for field in ["identifier", "title", "text", "requirementType",
                       "bindingForce", "referencesArticle", "mandatedBy", "addressesHazard"]:
            if field not in sr:
                report.error("R1_SCHEMA", sr_id, f"필수 필드 누락: {field}")

        # R2: identifier 중복
        if sr_id in seen_ids:
            report.error("R2_DUPLICATE_ID", sr_id, "identifier 중복")
        seen_ids.add(sr_id)

        # R3: identifier 정규식
        if not SR_ID_PATTERN.match(sr_id):
            report.error("R3_ID_FORMAT", sr_id, f"identifier 형식 불일치: {sr_id}")

        # R4: mandatedBy FK → norm_statements
        for ns_id in sr.get("mandatedBy", []):
            if ns_id not in all_ns:
                report.error("R4_FK_NS", sr_id, f"mandatedBy NS 미존재: {ns_id}")

        # R5: referencesArticle FK → articles
        for article_code in sr.get("referencesArticle", []):
            if not ARTICLE_CODE_PATTERN.match(article_code):
                report.error("R5_FK_ARTICLE", sr_id, f"조문코드 형식 오류: {article_code}")
            elif ("RULE", article_code) not in article_codes:
                report.error("R5_FK_ARTICLE", sr_id, f"articles 테이블에 미존재: RULE.{article_code}")

        # R6: hasSanction ↔ penalty-routes.json 일치
        sanction = sr.get("hasSanction")
        if sanction:
            for article_code in sr.get("referencesArticle", []):
                route = penalties.get("routes", {}).get(article_code)
                if route:
                    route_sanction = {
                        "criminal": route.get("criminal"),
                        "administrative": route.get("administrative"),
                    }
                    if route.get("hasPenalty") and not sanction.get("criminal"):
                        report.error("R6_SANCTION_MISMATCH", sr_id,
                                     f"penalty-routes에 형사벌 있으나 SR에 없음: {article_code}")

        # R7: mandatedBy에 OBLIGATION/PROHIBITION만 포함
        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns and ns.get("hasModality") not in {"OBLIGATION", "PROHIBITION"}:
                report.error("R7_MODALITY_FILTER", sr_id,
                             f"mandatedBy에 {ns['hasModality']} NS 포함: {ns_id}")

        # R8: text 비어있지 않음
        if not sr.get("text", "").strip():
            report.error("R8_EMPTY_TEXT", sr_id, "text가 비어있음")

        # R9: requirementType enum
        if sr.get("requirementType") not in VALID_REQUIREMENT_TYPES:
            report.error("R9_INVALID_TYPE", sr_id,
                         f"유효하지 않은 requirementType: {sr.get('requirementType')}")

        # R10: addressesHazard 표준 키워드
        for hazard in sr.get("addressesHazard", []):
            if hazard not in VALID_HAZARD_KEYWORDS:
                report.error("R10_INVALID_HAZARD", sr_id,
                             f"비표준 hazard 키워드: {hazard}")

        # ── 의미적 검증 (Warning) ──

        # R11: QUANTITATIVE 조건 수치가 structuralRequirements에 포함
        struct_req = sr.get("structuralRequirements")
        for ns_id in sr.get("mandatedBy", []):
            ns = all_ns.get(ns_id)
            if ns:
                cond = ns.get("hasCondition")
                if cond and cond.get("conditionType") == "QUANTITATIVE":
                    has_items = False
                    if isinstance(struct_req, dict):
                        has_items = bool(struct_req.get("items"))
                    elif isinstance(struct_req, list):
                        has_items = len(struct_req) > 0
                    if not has_items:
                        report.warn("R11_QUANT_MISSING", sr_id,
                                    f"QUANTITATIVE 조건 있으나 structuralRequirements 없음: {ns_id}")

        # R12: 같은 조문 NS가 같은 SR에 통합
        ns_article_map = defaultdict(set)
        for other_sr in all_sr:
            for ns_id in other_sr.get("mandatedBy", []):
                ns = all_ns.get(ns_id)
                if ns:
                    ns_article_map[ns["articleCode"]].add(other_sr["identifier"])
        for article_code in sr.get("referencesArticle", []):
            srs_for_article = ns_article_map.get(article_code, set())
            if len(srs_for_article) > 1 and sr_id in srs_for_article:
                report.warn("R12_SPLIT_ARTICLE", sr_id,
                            f"조문 {article_code}이 여러 SR에 분산: {srs_for_article}")

        # R13: title ↔ text 일관성 (간이 체크: title 키워드가 text에 포함)
        title_words = [w for w in sr.get("title", "").split() if len(w) > 1]
        text = sr.get("text", "")
        if title_words:
            match_ratio = sum(1 for w in title_words if w in text) / len(title_words)
            if match_ratio < 0.3:
                report.warn("R13_TITLE_TEXT_MISMATCH", sr_id,
                            f"title 키워드의 {match_ratio:.0%}만 text에 포함")

        # R14: hasModificationLink 대상 SR 존재
        mod_link = sr.get("hasModificationLink")
        if mod_link and mod_link.get("modifiesSR"):
            target_sr = mod_link["modifiesSR"]
            if target_sr not in sr_ids:
                report.warn("R14_MOD_TARGET_MISSING", sr_id,
                            f"hasModificationLink 대상 SR 미존재: {target_sr}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Step 6 SR 검증")
    parser.add_argument("--sr-dir", type=str, default=str(SR_DIR), help="SR 파일 디렉토리")
    args = parser.parse_args()


    print("[1/4] SR 파일 로드...")
    all_sr = load_all_sr()
    print(f"       총 SR: {len(all_sr)}개")

    if not all_sr:
        print("[INFO] SR 파일이 없습니다. Step 4 완료 후 다시 실행하세요.")
        return

    print("[2/4] NS 데이터 로드...")
    all_ns = load_all_ns()
    print(f"       총 NS: {len(all_ns)}개")

    print("[3/4] 참조 데이터 로드...")
    article_codes = load_articles()
    penalties = load_penalty_routes()

    print("[4/4] 14개 규칙 검증 중...")
    report = validate(all_sr, all_ns, article_codes, penalties)

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"SR 검증 결과")
    print(f"{'='*60}")
    print(f"  총 SR: {len(all_sr)}개")
    print(f"  ERROR: {len(report.errors)}건")
    print(f"  WARNING: {len(report.warnings)}건")

    if report.errors:
        print(f"\n{'─'*60}")
        print("ERRORS (반드시 수정 필요):")
        for e in report.errors[:50]:
            print(f"  [{e['rule']}] {e['srId']}: {e['message']}")
        if len(report.errors) > 50:
            print(f"  ... 외 {len(report.errors) - 50}건")

    if report.warnings:
        print(f"\n{'─'*60}")
        print("WARNINGS (수동 확인 권장):")
        # 규칙별 그룹핑
        warn_by_rule = defaultdict(list)
        for w in report.warnings:
            warn_by_rule[w["rule"]].append(w)
        for rule, warns in sorted(warn_by_rule.items()):
            print(f"  {rule}: {len(warns)}건")
            for w in warns[:3]:
                print(f"    {w['srId']}: {w['message']}")
            if len(warns) > 3:
                print(f"    ... 외 {len(warns) - 3}건")

    # 결과 파일 저장
    report_path = DATA_DIR / "validation" / "sr-validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "totalSR": len(all_sr),
        "totalErrors": len(report.errors),
        "totalWarnings": len(report.warnings),
        "errors": report.errors,
        "warnings": report.warnings,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"\n검증 리포트 저장: {report_path}")

    # PASS/FAIL 판정
    if report.errors:
        print(f"\n❌ FAIL — {len(report.errors)}개 에러를 수정하세요.")
        sys.exit(1)
    else:
        print(f"\n✅ PASS — 구조적 에러 0건 (경고 {len(report.warnings)}건)")


if __name__ == "__main__":
    main()
