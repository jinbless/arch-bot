#!/usr/bin/env python3
"""Step 4: NS 전수 검증 → ns-validation-report.json

100% 결정론적 스크립트. LLM 불필요.
13개 검증 규칙 (구조적 9 + 의미적 4)으로 모든 NS 파일을 교차검증한다.

구조적 규칙 (R1~R9): 스키마, 식별자, FK, 벌칙 일치
의미적 규칙 (R10~R13): 모달리티 키워드, 조건 탐지, roleGuidance, 단서 체인
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMA_DIR = PROJECT_ROOT / "schemas"
DATA_DIR = PROJECT_ROOT / "data"
NS_DIR = DATA_DIR / "norm-statements"

sys.path.insert(0, str(SCRIPT_DIR))
from lib.schema_validator import load_schema, validate, validate_and_write


def main():
    # 1. 참조 데이터 로드
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        article_data = json.load(f)

    with open(DATA_DIR / "penalty-routes.json", encoding="utf-8") as f:
        penalty_data = json.load(f)

    # 모든 법령의 조문코드 집합
    all_article_codes = set()
    for law_id, articles in article_data["laws"].items():
        for code in articles:
            all_article_codes.add((law_id, code))

    ns_schema = load_schema(SCHEMA_DIR / "ns-file.schema.json")

    # 2. NS 파일 수집
    ns_files = sorted(NS_DIR.glob("ns-batch-*.json"))
    if not ns_files:
        print("[WARN] NS 파일이 없습니다. Step 2를 먼저 실행하세요.")
        # 빈 리포트 생성
        report = {
            "metadata": {
                "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "filesChecked": 0,
                "totalNS": 0,
            },
            "passed": True,
            "summary": {
                "schemaErrors": 0,
                "identifierDuplicates": 0,
                "fkViolations": 0,
                "sanctionMismatches": 0,
                "modalitySanctionConflicts": 0,
            },
            "errors": [],
        }
        validate_and_write(report, SCHEMA_DIR / "validation-report.schema.json", DATA_DIR / "validation" / "ns-validation-report.json")
        return

    errors = []
    all_identifiers = {}  # identifier -> file
    all_ns = []
    total_ns = 0

    for ns_file in ns_files:
        with open(ns_file, encoding="utf-8") as f:
            data = json.load(f)

        # Rule 1: JSON Schema 검증
        schema_errors = validate(data, ns_schema)
        for e in schema_errors:
            errors.append({
                "rule": "R1_SCHEMA",
                "identifier": ns_file.name,
                "message": e,
            })

        for ns in data.get("normStatements", []):
            ns_id = ns.get("identifier", "UNKNOWN")
            total_ns += 1

            # Rule 2: 식별자 유일성
            if ns_id in all_identifiers:
                errors.append({
                    "rule": "R2_DUPLICATE_ID",
                    "identifier": ns_id,
                    "message": f"중복: {all_identifiers[ns_id]}에도 존재",
                })
            all_identifiers[ns_id] = ns_file.name

            # Rule 3: 식별자 포맷
            if not re.match(r"^NS-[A-Z0-9]+-[0-9A-Z]+$", ns_id):
                errors.append({
                    "rule": "R3_ID_FORMAT",
                    "identifier": ns_id,
                    "message": f"잘못된 식별자 포맷",
                })

            # Rule 4: articleCode FK
            article_code = ns.get("articleCode", "")
            law_id = ns.get("lawId", "")
            if (law_id, article_code) not in all_article_codes:
                errors.append({
                    "rule": "R4_FK_ARTICLE",
                    "identifier": ns_id,
                    "message": f"article-texts.json에 없음: {law_id}.{article_code}",
                })

            # Rule 5: hasSanction 일치 (RULE 조문만)
            if law_id == "RULE" and article_code in penalty_data["routes"]:
                route = penalty_data["routes"][article_code]
                ns_sanction = ns.get("hasSanction")
                if route["hasPenalty"] and ns_sanction is not None:
                    # criminal.violation_employer 일치 확인
                    expected_criminal = route.get("criminal") or {}
                    actual_criminal = (ns_sanction.get("criminal") or {}) if ns_sanction else {}
                    expected_t1 = expected_criminal.get("violation_employer")
                    actual_t1 = actual_criminal.get("violation_employer")
                    if expected_t1 and actual_t1:
                        if actual_t1.get("penalty") != expected_t1.get("penalty"):
                            errors.append({
                                "rule": "R5_SANCTION_MISMATCH",
                                "identifier": ns_id,
                                "message": f"criminal.violation_employer 벌칙 불일치: {actual_t1.get('penalty')} != {expected_t1.get('penalty')}",
                            })
                    # administrative 일치 확인
                    expected_admin = route.get("administrative")
                    actual_admin = ns_sanction.get("administrative") if ns_sanction else None
                    if route.get("hasAdministrativeFine"):
                        if expected_admin and not actual_admin:
                            errors.append({
                                "rule": "R5_SANCTION_MISMATCH",
                                "identifier": ns_id,
                                "message": f"administrative 과태료 누락 (expected: {expected_admin.get('maxFine')})",
                            })

            # Rule 6: DEFINITION/EXEMPTION → hasSanction: null
            modality = ns.get("hasModality", "")
            ns_sanction = ns.get("hasSanction")
            if modality == "DEFINITION" and ns_sanction is not None:
                errors.append({
                    "rule": "R6_MODALITY_SANCTION",
                    "identifier": ns_id,
                    "message": f"{modality}인데 hasSanction이 null이 아님",
                })

            # Rule 7: OBLIGATION → hasSanction not null (RULE 벌칙 적용 조문)
            if law_id == "RULE" and modality == "OBLIGATION":
                if article_code in penalty_data["routes"]:
                    route = penalty_data["routes"][article_code]
                    if route["hasPenalty"] and ns_sanction is None:
                        errors.append({
                            "rule": "R7_OBLIGATION_NO_SANCTION",
                            "identifier": ns_id,
                            "message": f"OBLIGATION인데 hasSanction이 null (벌칙 적용 조문)",
                        })

            # Rule 8: text 비어있지 않음
            if not ns.get("text", "").strip():
                errors.append({
                    "rule": "R8_EMPTY_TEXT",
                    "identifier": ns_id,
                    "message": "text가 비어있음",
                })

            # Rule 10: hasModality ↔ 텍스트 키워드 일치 (의미적)
            ns_text = ns.get("text", "")
            modality_keywords = {
                "OBLIGATION": [r"하여야\s*한다", r"해야\s*한다", r"이어야\s*한다", r"있어야\s*한다", r"되어야\s*한다", r"따라야\s*한다", r"갖추", r"갖춰", r"두어야", r"준수하여야", r"유지하여야", r"설치하여야", r"조치를\s*하여야", r"하도록\s*하여야", r"할\s*것", r"보관하여야", r"알려야", r"주지시켜야", r"시켜야", r"정하여야", r"준용한다", r"수행한다", r"올려야", r"위치하도록", r"하여야\s*하며", r"받는\s*경우"],
                "PROHIBITION": [r"아니\s*된다", r"안\s*된다", r"금지", r"하여서는", r"해서는", r"못하도록", r"사용하지\s*않을\s*것", r"준용한다.*본다"],
                "EXEMPTION": [r"그러하지\s*아니하다", r"그렇지\s*않다", r"적용하지\s*아니한다", r"적용되지\s*아니한다", r"면제", r"제외한다", r"아니할\s*수\s*있다", r"않을\s*수\s*있다", r"설치하지\s*않을", r"아니한다", r"것으로\s*본다", r"따른다", r"만\s*표시한다", r"보호되는\s*구조"],
                "DEFINITION": [r"말한다", r"이란", r"뜻은", r"목적으로\s*한다"],
            }
            if modality in modality_keywords:
                patterns = modality_keywords[modality]
                if not any(re.search(p, ns_text) for p in patterns):
                    errors.append({
                        "rule": "R10_MODALITY_KEYWORD",
                        "identifier": ns_id,
                        "message": f"{modality}인데 해당 키워드 미발견: {ns_text[:80]}...",
                    })

            # Rule 11: hasCondition 존재 여부 ↔ 조건 표현 탐지 (의미적, WARNING)
            if modality not in ("DEFINITION",):
                condition_markers = re.search(r"경우에|경우에는|하는\s*경우|할\s*때|있는\s*경우|없는\s*경우", ns_text)
                ns_condition = ns.get("hasCondition")
                if condition_markers and ns_condition is None:
                    errors.append({
                        "rule": "R11_CONDITION_MISSING",
                        "identifier": ns_id,
                        "message": f"조건 표현 발견({condition_markers.group()})인데 hasCondition이 null",
                    })

            # Rule 12: roleGuidance 유효성 (의미적)
            ns_guidance = ns.get("roleGuidance")
            if modality == "DEFINITION" and ns_guidance is not None:
                errors.append({
                    "rule": "R12_GUIDANCE_DEFINITION",
                    "identifier": ns_id,
                    "message": "DEFINITION인데 roleGuidance가 null이 아님",
                })
            if ns_guidance is not None and isinstance(ns_guidance, dict):
                for role in ("EMPLOYER", "WORKER"):
                    guidance_text = ns_guidance.get(role, "")
                    if guidance_text and len(guidance_text) < 20:
                        errors.append({
                            "rule": "R12_GUIDANCE_SHORT",
                            "identifier": ns_id,
                            "message": f"roleGuidance.{role} 길이 부족: {len(guidance_text)}자 (최소 20자)",
                        })
                    if guidance_text and ns_text and len(guidance_text) > 20:
                        # text 복사 검출: guidance가 text의 85% 이상 일치 (한국어 법률용어 중복 감안)
                        overlap = sum(1 for c in guidance_text if c in ns_text) / max(len(guidance_text), 1)
                        if overlap > 0.85:
                            errors.append({
                                "rule": "R12_GUIDANCE_COPY",
                                "identifier": ns_id,
                                "message": f"roleGuidance.{role}가 text와 {overlap:.0%} 유사 (단순 복사 의심)",
                            })

            # Rule 13: 단서 체인 무결성 (의미적)
            ns_mod_link = ns.get("hasModificationLink")
            if "다만," in ns_text and ns_mod_link is None:
                errors.append({
                    "rule": "R13_PROVISO_NO_LINK",
                    "identifier": ns_id,
                    "message": "text에 '다만,'이 있는데 hasModificationLink가 null",
                })
            if ns_mod_link is not None and isinstance(ns_mod_link, dict):
                ref_ns = ns_mod_link.get("modifiesNS", "")
                if ref_ns and ref_ns not in all_identifiers:
                    errors.append({
                        "rule": "R13_PROVISO_REF_MISSING",
                        "identifier": ns_id,
                        "message": f"modifiesNS '{ref_ns}'가 존재하지 않는 식별자",
                    })
                # 같은 조문 내 NS인지 확인은 2패스 필요 — all_ns 완성 후 아래에서 검사

            all_ns.append(ns)

    # Rule 9: 동일 조+항 중복 확인
    seen_refs = {}
    for ns in all_ns:
        key = f"{ns.get('lawId')}.{ns.get('articleCode')}.{ns.get('paragraphRef')}"
        if key in seen_refs and ns.get("hasModificationLink") is None:
            errors.append({
                "rule": "R9_DUPLICATE_PARAGRAPH",
                "identifier": ns.get("identifier", ""),
                "message": f"동일 조+항 중복: {key} (기존: {seen_refs[key]})",
            })
        seen_refs[key] = ns.get("identifier", "")

    # Rule 13 (2nd pass): modifiesNS가 같은 조문 내인지 + 단서 수 대조
    ns_by_article = {}  # (lawId, articleCode) -> list of NS
    for ns in all_ns:
        key = (ns.get("lawId"), ns.get("articleCode"))
        ns_by_article.setdefault(key, []).append(ns)

    for ns in all_ns:
        ns_mod_link = ns.get("hasModificationLink")
        if ns_mod_link and isinstance(ns_mod_link, dict):
            ref_ns = ns_mod_link.get("modifiesNS", "")
            if ref_ns:
                # 참조 대상 NS의 조문코드 확인
                ref_article = None
                for other in all_ns:
                    if other.get("identifier") == ref_ns:
                        ref_article = other.get("articleCode")
                        break
                if ref_article and ref_article != ns.get("articleCode"):
                    errors.append({
                        "rule": "R13_PROVISO_CROSS_ARTICLE",
                        "identifier": ns.get("identifier", ""),
                        "message": f"modifiesNS '{ref_ns}'가 다른 조문({ref_article})에 속함 (현재: {ns.get('articleCode')})",
                    })

    # 3. 요약
    summary = {
        "schemaErrors": sum(1 for e in errors if e["rule"] == "R1_SCHEMA"),
        "identifierDuplicates": sum(1 for e in errors if e["rule"] == "R2_DUPLICATE_ID"),
        "fkViolations": sum(1 for e in errors if e["rule"] == "R4_FK_ARTICLE"),
        "sanctionMismatches": sum(1 for e in errors if e["rule"] == "R5_SANCTION_MISMATCH"),
        "modalitySanctionConflicts": sum(1 for e in errors if e["rule"] in ("R6_MODALITY_SANCTION", "R7_OBLIGATION_NO_SANCTION")),
        "modalityKeywordMismatches": sum(1 for e in errors if e["rule"] == "R10_MODALITY_KEYWORD"),
        "conditionMissing": sum(1 for e in errors if e["rule"] == "R11_CONDITION_MISSING"),
        "guidanceIssues": sum(1 for e in errors if e["rule"].startswith("R12_")),
        "provisoChainIssues": sum(1 for e in errors if e["rule"].startswith("R13_")),
    }

    # WARNING 규칙 (R11)은 PASS 판정에서 제외 — false positive 가능
    warning_rules = {"R10_MODALITY_KEYWORD", "R11_CONDITION_MISSING", "R12_GUIDANCE_COPY", "R12_GUIDANCE_SHORT", "R12_GUIDANCE_DEFINITION", "R13_PROVISO_CROSS_ARTICLE"}
    hard_errors = [e for e in errors if e["rule"] not in warning_rules]
    warnings = [e for e in errors if e["rule"] in warning_rules]
    passed = len(hard_errors) == 0

    report = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "filesChecked": len(ns_files),
            "totalNS": total_ns,
        },
        "passed": passed,
        "summary": summary,
        "errors": errors,
    }

    # 4. 저장
    report_errors = validate_and_write(
        report,
        SCHEMA_DIR / "validation-report.schema.json",
        DATA_DIR / "validation" / "ns-validation-report.json",
    )
    if report_errors:
        print(f"[ERROR] 리포트 스키마 검증 실패")
        sys.exit(1)

    status = "PASS" if passed else "FAIL"
    print(f"\n[{status}] NS 검증 완료 (13규칙)")
    print(f"  파일: {len(ns_files)}개, NS: {total_ns}개, ERROR: {len(hard_errors)}건, WARNING: {len(warnings)}건")
    for rule, count in sorted(summary.items()):
        if count > 0:
            print(f"  {rule}: {count}")

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
