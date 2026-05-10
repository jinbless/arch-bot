#!/usr/bin/env python3
"""P1-Step 3: 가이드 파싱 품질 검증.

guide-text-v2.schema.json으로 전수 검증하고, 빈 섹션·섹션 커버리지를 분석한다.

Usage:
    python3 scripts/step0_validate_parsing.py [--domain D]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 경로 설정 ──
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import PARSED_DIR, SCHEMA_DIR, DATA_DIR, PIPE_A_ROOT

SCHEMA_PATH = SCHEMA_DIR / "guide-text-v2.schema.json"
INVENTORY_PATH = DATA_DIR / "guide-inventory.json"
REPORT_PATH = DATA_DIR / "parsing-report.json"

# ── Pipe-A schema_validator 재사용 ──
import importlib.util
_sv_path = PIPE_A_ROOT / "scripts" / "lib" / "schema_validator.py"
_spec = importlib.util.spec_from_file_location("pipe_a_schema_validator", _sv_path)
_sv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sv)
validate_json = _sv.validate


def count_empty_sections(sections: list, depth: int = 0) -> tuple[int, int]:
    """빈 섹션 수와 전체 섹션 수를 재귀적으로 카운트."""
    total = 0
    empty = 0
    for s in sections:
        total += 1
        raw_text = s.get("text", "")
        text = raw_text.strip() if isinstance(raw_text, str) else str(raw_text)
        tables = s.get("tables", [])
        images = s.get("images", [])
        if not text and not tables and not images:
            empty += 1
        # subsections 재귀
        subs = s.get("subsections", [])
        if subs:
            sub_total, sub_empty = count_empty_sections(subs, depth + 1)
            total += sub_total
            empty += sub_empty
    return total, empty


def main():
    parser = argparse.ArgumentParser(description="가이드 파싱 품질 검증")
    parser.add_argument("--domain", type=str, help="특정 도메인만 검증 (A/B/C/D/E)")
    args = parser.parse_args()

    print("[START] 가이드 파싱 품질 검증")

    # 인벤토리 로드
    if not INVENTORY_PATH.exists():
        print(f"[ERROR] 인벤토리 없음: {INVENTORY_PATH}")
        sys.exit(1)
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    guides = inventory["guides"]

    # 도메인 필터
    if args.domain:
        guides = [g for g in guides if g["domain"] == args.domain.upper()]
        print(f"  도메인 필터: {args.domain.upper()} ({len(guides)}개)")

    # 스키마 로드
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # 결과 구조
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalExpected": len(guides),
        "totalFound": 0,
        "totalMissing": 0,
        "schemaPass": 0,
        "schemaFail": 0,
        "totalSections": 0,
        "emptySections": 0,
        "emptySectionRatio": 0.0,
        "byDomain": {},
        "missing": [],
        "schemaErrors": [],
        "emptySectionDetails": [],
    }

    for g in guides:
        sc = g["shortCode"]
        domain = g["domain"]
        fp = PARSED_DIR / f"guide-{sc}.json"

        # 도메인별 집계 초기화
        if domain not in report["byDomain"]:
            report["byDomain"][domain] = {
                "expected": 0, "found": 0, "missing": 0,
                "schemaPass": 0, "schemaFail": 0,
                "sections": 0, "emptySections": 0,
                "avgSections": 0.0, "avgTables": 0.0,
            }
        dom_stat = report["byDomain"][domain]
        dom_stat["expected"] += 1

        if not fp.exists():
            report["totalMissing"] += 1
            dom_stat["missing"] += 1
            report["missing"].append({"shortCode": sc, "domain": domain})
            continue

        report["totalFound"] += 1
        dom_stat["found"] += 1

        # 스키마 검증
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            report["schemaFail"] += 1
            dom_stat["schemaFail"] += 1
            report["schemaErrors"].append({
                "shortCode": sc,
                "domain": domain,
                "error": f"JSON parse error: {e}",
            })
            continue

        errors = validate_json(doc, schema)
        if errors:
            report["schemaFail"] += 1
            dom_stat["schemaFail"] += 1
            report["schemaErrors"].append({
                "shortCode": sc,
                "domain": domain,
                "errorCount": len(errors),
                "errors": errors[:5],
            })
        else:
            report["schemaPass"] += 1
            dom_stat["schemaPass"] += 1

        # 섹션 분석
        sections = doc.get("sections", [])
        sec_total, sec_empty = count_empty_sections(sections)
        report["totalSections"] += sec_total
        report["emptySections"] += sec_empty
        dom_stat["sections"] += sec_total
        dom_stat["emptySections"] += sec_empty

        # 표 수 집계
        table_count = sum(len(s.get("tables", [])) for s in sections)
        dom_stat["avgTables"] = (
            dom_stat.get("_totalTables", 0) + table_count
        )
        dom_stat["_totalTables"] = dom_stat.get("_totalTables", 0) + table_count

        if sec_empty > 0:
            report["emptySectionDetails"].append({
                "shortCode": sc,
                "domain": domain,
                "totalSections": sec_total,
                "emptySections": sec_empty,
            })

    # 집계 계산
    if report["totalSections"] > 0:
        report["emptySectionRatio"] = round(
            report["emptySections"] / report["totalSections"] * 100, 2
        )

    for domain, stat in report["byDomain"].items():
        if stat["found"] > 0:
            stat["avgSections"] = round(stat["sections"] / stat["found"], 1)
            stat["avgTables"] = round(stat.get("_totalTables", 0) / stat["found"], 1)
        # 임시 키 제거
        stat.pop("_totalTables", None)

    # Phase 1 완료 조건 판정
    all_exist = report["totalMissing"] == 0
    all_schema_pass = report["schemaFail"] == 0
    empty_ok = report["emptySectionRatio"] < 5.0
    report["phase1Complete"] = all_exist and all_schema_pass and empty_ok

    # 출력
    print(f"  기대: {report['totalExpected']}개")
    print(f"  발견: {report['totalFound']}개")
    print(f"  누락: {report['totalMissing']}개")
    print(f"  스키마 PASS: {report['schemaPass']}개")
    print(f"  스키마 FAIL: {report['schemaFail']}개")
    print(f"  전체 섹션: {report['totalSections']}개")
    print(f"  빈 섹션: {report['emptySections']}개 ({report['emptySectionRatio']}%)")
    print(f"  Phase 1 완료: {'YES' if report['phase1Complete'] else 'NO'}")

    if report["schemaErrors"]:
        print(f"\n  스키마 에러 상세 ({len(report['schemaErrors'])}건):")
        for e in report["schemaErrors"][:10]:
            print(f"    [{e['domain']}] {e['shortCode']}: {e.get('errorCount', 1)}건")

    # 보고서 저장
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[DONE] 보고서 저장: {REPORT_PATH}")


if __name__ == "__main__":
    main()
