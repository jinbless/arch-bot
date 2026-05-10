#!/usr/bin/env python3
"""Step 1: 벌칙 경로 추출 → penalty-routes.json

100% 결정론적 스크립트. LLM 불필요.
article-texts.json + 정적 config → 결정론적 벌칙 경로.

v2: criminal/administrative 분리 구조.
  - criminal: 형사벌 (제167~172조) — 제38조/제39조 위임 경로
  - administrative: 과태료 (제175조) — delegation-map의 OSHA 조문이 제175조에 참조되는 경우

과태료 매핑 로직:
  RULE 조문은 주로 제38조/제39조에 의해 위임되지만,
  delegation-map에는 제64조, 제77조 등 다른 OSHA 조문도 있다.
  이들 OSHA 조문이 제175조에 참조되면 해당 RULE 조문에도 과태료가 매핑된다.
  제38조/제39조 자체는 과태료 대상이 아니므로 (형사벌만 적용)
  대부분의 RULE 조문에는 과태료가 매핑되지 않는 것이 법적으로 올바르다.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from lib.schema_validator import validate_and_write


def build_admin_fine_map(penalty_map: dict) -> dict:
    """제175조 과태료 데이터 → {OSHA 조문번호(조 레벨): fine_info} 역매핑.

    동일 조문이 여러 항에 나타나면 가장 높은 과태료(낮은 항번호)를 사용.
    """
    fine_data = penalty_map.get("과태료_제175조")
    if not fine_data:
        return {}

    fine_table_ref = fine_data.get("fineTableRef", "시행령 별표35")
    osha_to_fine = {}

    for hang_key in ["항1", "항2", "항3", "항4", "항5", "항6"]:
        hang = fine_data.get(hang_key)
        if not hang:
            continue
        max_fine = hang["maxFine"]

        for ref in hang.get("referenced_articles", []):
            m = re.match(r"(제\d+조(?:의\d+)?)", ref)
            if not m:
                continue
            osha_art = m.group(1)

            if osha_art not in osha_to_fine:
                osha_to_fine[osha_art] = {
                    "law": f"산업안전보건법 제175조{hang_key.replace('항', '제')}항",
                    "maxFine": max_fine,
                    "fineTableRef": fine_table_ref,
                    "oshaArticleRef": ref,
                }

    return osha_to_fine


def main():
    # 1. 데이터 로드
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        article_data = json.load(f)

    with open(CONFIG_DIR / "delegation-map.json", encoding="utf-8") as f:
        delegation_map = json.load(f)

    with open(CONFIG_DIR / "penalty-article-map.json", encoding="utf-8") as f:
        penalty_map = json.load(f)

    rule_articles = article_data["laws"]["RULE"]
    delegation = delegation_map["RULE_TO_OSHA"]

    # 2. 과태료 역매핑 생성
    admin_fine_map = build_admin_fine_map(penalty_map)

    # 3. 각 RULE 조문의 벌칙 경로 결정
    routes = {}
    with_penalty = 0
    without_penalty = 0
    with_admin_fine = 0
    without_admin_fine = 0

    for article_code in sorted(rule_articles.keys(), key=lambda x: int(''.join(filter(str.isdigit, x.split('조')[0].replace('제', ''))))):
        article = rule_articles[article_code]

        if article["deleted"]:
            continue

        section = article.get("section", "") or ""
        delegated_from = None
        has_penalty = False
        has_admin_fine = False
        criminal_block = None
        admin_block = None

        # 총칙 규정 (벌칙 비적용)
        if "통칙" in section or article_code in ("제1조", "제2조"):
            delegated_from = None
            has_penalty = False
        else:
            # 보건 관련 편/장 여부로 위임 근거 결정
            is_health = any(kw in section for kw in ["보건", "건강", "유해", "환기", "분진", "소음", "진동", "이상기압", "온도", "방사선"])

            if is_health:
                delegated_from = "제39조"
            else:
                delegated_from = "제38조"

            has_penalty = True

            # Criminal block
            criminal_block = {
                "violation_employer": {
                    "law": f"산업안전보건법 제168조 제1호 (제{delegated_from[1:]} 경유)",
                    "penalty": "5년 이하의 징역 또는 5천만원 이하의 벌금",
                },
                "violation_contractor": {
                    "law": "산업안전보건법 제169조 제1호 (제63조 경유)",
                    "penalty": "3년 이하의 징역 또는 3천만원 이하의 벌금",
                },
                "death": {
                    "law": f"산업안전보건법 제167조 (제{delegated_from[1:]} 위반 + 사망)",
                    "penalty": "7년 이하의 징역 또는 1억원 이하의 벌금",
                },
                "seriousAccident": {
                    "law": "중대재해 처벌 등에 관한 법률 제6조",
                    "death": "1년 이상의 징역 또는 10억원 이하의 벌금",
                    "injury": "7년 이하의 징역 또는 1억원 이하의 벌금",
                },
            }

        # Administrative block:
        # 위임 근거 OSHA 조문이 과태료 대상인지 확인
        # 제38조/제39조 자체는 과태료 대상이 아니지만,
        # delegation-map의 다른 OSHA 조문(제64조, 제77조 등)은 과태료 대상일 수 있음
        if delegated_from and delegated_from in admin_fine_map:
            admin_block = admin_fine_map[delegated_from]
            has_admin_fine = True

        routes[article_code] = {
            "title": article["title"],
            "delegatedFrom": delegated_from,
            "hasPenalty": has_penalty,
            "hasAdministrativeFine": has_admin_fine,
            "criminal": criminal_block,
            "administrative": admin_block,
        }

        if has_penalty:
            with_penalty += 1
        else:
            without_penalty += 1

        if has_admin_fine:
            with_admin_fine += 1
        else:
            without_admin_fine += 1

    # 4. 출력 구성
    output = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalRoutes": len(routes),
            "withPenalty": with_penalty,
            "withoutPenalty": without_penalty,
            "withAdministrativeFine": with_admin_fine,
            "withoutAdministrativeFine": without_admin_fine,
        },
        "routes": routes,
    }

    # 5. 스키마 검증 후 저장
    errors = validate_and_write(output, SCHEMA_DIR / "penalty-routes.schema.json", DATA_DIR / "penalty-routes.json")
    if errors:
        print(f"\n[FAIL] 스키마 검증 실패 ({len(errors)}건)")
        for e in errors[:10]:
            print(f"  {e}")
        sys.exit(1)

    print(f"\n[DONE] penalty-routes.json 생성 완료")
    print(f"  형사벌 적용: {with_penalty}조, 미적용: {without_penalty}조")
    print(f"  과태료 적용: {with_admin_fine}조, 미적용: {without_admin_fine}조")
    if with_admin_fine == 0:
        print(f"  [참고] 제38조/제39조는 과태료 대상이 아님 — RULE 조문 대부분은 형사벌만 적용")


if __name__ == "__main__":
    main()
