#!/usr/bin/env python3
"""Step 0: KOSHA 가이드 인벤토리 생성 → guide-inventory.json + guide-pdf-index.json

100% 결정론적 스크립트. LLM 불필요.
kosha-guides/{A~E}/ 디렉토리 스캔 → 1,038개 가이드 전수 목록.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Pipe-B lib 로드
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.paths import SCHEMA_DIR, DATA_DIR, GUIDES_PDF, PIPE_A_ROOT
from lib.guide_code import parse_guide_filename

KOSHA_GUIDES_DIR = GUIDES_PDF

# Pipe-A schema_validator 재사용 (lib 이름 충돌 방지: spec_from_file_location 사용)
import importlib.util
_sv_path = PIPE_A_ROOT / "scripts" / "lib" / "schema_validator.py"
_spec = importlib.util.spec_from_file_location("pipe_a_schema_validator", _sv_path)
_sv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sv)
validate_and_write = _sv.validate_and_write

# 처리 순서: D(건설, 최소) → A(일반) → B(기계/전기) → C(화학) → E(보건, 최대)
PROCESSING_ORDER = ["D", "A", "B", "C", "E"]
DOMAINS = ["A", "B", "C", "D", "E"]


def scan_domain(domain: str) -> list[dict]:
    """도메인 디렉토리의 PDF 파일을 스캔하여 가이드 목록 생성."""
    domain_dir = KOSHA_GUIDES_DIR / domain
    if not domain_dir.is_dir():
        print(f"[WARN] 디렉토리 없음: {domain_dir}")
        return []

    guides = []
    skipped = []
    for pdf_file in sorted(domain_dir.iterdir()):
        if not pdf_file.name.lower().endswith(".pdf"):
            continue

        result = parse_guide_filename(pdf_file.name, domain)
        if result is None:
            skipped.append(pdf_file.name)
            continue

        result["pdfPath"] = f"{domain}/{pdf_file.name}"
        guides.append(result)

    if skipped:
        print(f"[WARN] {domain} 도메인 파싱 실패 {len(skipped)}건:")
        for s in skipped[:5]:
            print(f"  - {s}")
        if len(skipped) > 5:
            print(f"  ... 외 {len(skipped) - 5}건")

    return guides


def check_duplicate_short_codes(guides: list[dict]) -> list[str]:
    """shortCode 중복 검사."""
    counter = Counter(g["shortCode"] for g in guides)
    duplicates = [code for code, count in counter.items() if count > 1]
    return sorted(duplicates)


def build_pdf_index(guides: list[dict]) -> dict:
    """shortCode → PDF 경로 매핑 (guide-pdf-index.json)."""
    index = {}
    for g in guides:
        sc = g["shortCode"]
        if sc in index:
            # 중복 시 최신 연도 우선
            existing_year = next(
                (gg["year"] for gg in guides if gg["shortCode"] == sc and gg["pdfPath"] == index[sc]),
                0,
            )
            if g["year"] > existing_year:
                index[sc] = g["pdfPath"]
        else:
            index[sc] = g["pdfPath"]
    return dict(sorted(index.items()))


def build_domain_batch_plan(domain_counts: dict[str, int]) -> list[dict]:
    """분야별 배치 계획 생성."""
    plan = []
    for domain in PROCESSING_ORDER:
        count = domain_counts.get(domain, 0)
        plan.append({
            "domain": domain,
            "guideCount": count,
            "order": PROCESSING_ORDER.index(domain) + 1,
        })
    return plan


def main():
    print(f"[START] KOSHA 가이드 인벤토리 생성")
    print(f"  가이드 디렉토리: {KOSHA_GUIDES_DIR}")

    if not KOSHA_GUIDES_DIR.is_dir():
        print(f"[ERROR] 가이드 디렉토리 없음: {KOSHA_GUIDES_DIR}")
        sys.exit(1)

    # 1. 전 도메인 스캔
    all_guides = []
    domain_counts = {}
    for domain in DOMAINS:
        guides = scan_domain(domain)
        domain_counts[domain] = len(guides)
        all_guides.extend(guides)
        print(f"  [{domain}] {len(guides)}개 가이드")

    print(f"\n  총 가이드: {len(all_guides)}개")

    # 2. shortCode 중복 검사
    duplicates = check_duplicate_short_codes(all_guides)
    if duplicates:
        print(f"\n[WARN] shortCode 중복 {len(duplicates)}건:")
        for dup in duplicates:
            matching = [g for g in all_guides if g["shortCode"] == dup]
            for m in matching:
                print(f"  {dup}: {m['guideCode']} ({m['domain']}/{m['pdfPath']})")

    # 3. 인벤토리 JSON 구성
    inventory = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalGuides": len(all_guides),
            "domainCounts": domain_counts,
            "processingOrder": PROCESSING_ORDER,
            "duplicateShortCodes": duplicates,
        },
        "guides": all_guides,
    }

    # 4. 스키마 검증 후 저장
    schema_path = SCHEMA_DIR / "guide-inventory.schema.json"
    output_path = DATA_DIR / "guide-inventory.json"

    errors = validate_and_write(inventory, schema_path, output_path)
    if errors:
        print(f"\n[FAIL] guide-inventory.json 스키마 검증 실패 ({len(errors)}건)")
        sys.exit(1)

    # 5. guide-pdf-index.json 저장
    pdf_index = build_pdf_index(all_guides)
    index_path = DATA_DIR / "guide-pdf-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(pdf_index, f, ensure_ascii=False, indent=2)
    print(f"[OK] 저장 완료: {index_path} ({index_path.stat().st_size:,} bytes)")

    # 6. domain-batch-plan.json 저장
    batch_plan = build_domain_batch_plan(domain_counts)
    plan_path = DATA_DIR / "domain-batch-plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(batch_plan, f, ensure_ascii=False, indent=2)
    print(f"[OK] 저장 완료: {plan_path} ({plan_path.stat().st_size:,} bytes)")

    # 7. 요약
    print(f"\n[DONE] 인벤토리 생성 완료")
    print(f"  총 가이드: {len(all_guides)}")
    for domain in DOMAINS:
        print(f"  {domain}: {domain_counts[domain]}개")
    print(f"  shortCode 중복: {len(duplicates)}건")
    print(f"  처리 순서: {' → '.join(PROCESSING_ORDER)}")


if __name__ == "__main__":
    main()
