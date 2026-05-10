#!/usr/bin/env python3
"""P-C Step 0: SR 커버리지 갭 분석.

626개 SR 중 CI와 연결된 SR 수를 집계하고,
커버리지 갭(CI 0건 SR)을 도메인·카테고리별로 분석한다.

Usage:
    python3 scripts/step0_sr_coverage.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, PG_CONNINFO


def main():
    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor()

    print("[START] SR 커버리지 갭 분석 (Pipe-C Step 0)")

    # 1) 총 SR 수
    cur.execute("SELECT COUNT(*) FROM safety_requirements")
    total_sr = cur.fetchone()[0]

    # 2) 총 처리된 가이드 수
    cur.execute("SELECT COUNT(*) FROM kosha_guides")
    total_guides = cur.fetchone()[0]

    # 3) 절대 커버리지: ci_sr_mapping에 연결된 SR 수
    cur.execute("SELECT COUNT(DISTINCT sr_id) FROM ci_sr_mapping")
    covered_sr = cur.fetchone()[0]
    uncovered_sr = total_sr - covered_sr

    # 4) 도메인별 커버리지
    cur.execute("""
        SELECT g.domain,
               COUNT(DISTINCT ci.identifier) as total_ci,
               COUNT(DISTINCT m.sr_id) as linked_sr,
               COUNT(DISTINCT m.ci_id) as linked_ci
        FROM kosha_guides g
        JOIN checklist_items ci ON ci.source_guide = g.guide_code
        LEFT JOIN ci_sr_mapping m ON m.ci_id = ci.identifier
        GROUP BY g.domain
        ORDER BY g.domain
    """)
    domain_stats = []
    for row in cur.fetchall():
        domain_stats.append({
            "domain": row[0],
            "totalCI": row[1],
            "linkedSR": row[2],
            "linkedCI": row[3],
            "linkRate": round(row[3] / row[1] * 100, 1) if row[1] > 0 else 0,
        })

    # 5) requirement_type별 커버리지
    cur.execute("""
        SELECT sr.requirement_type,
               COUNT(*) as total,
               COUNT(m.sr_id) as covered
        FROM safety_requirements sr
        LEFT JOIN (SELECT DISTINCT sr_id FROM ci_sr_mapping) m ON sr.identifier = m.sr_id
        GROUP BY sr.requirement_type
        ORDER BY sr.requirement_type
    """)
    type_stats = []
    for row in cur.fetchall():
        type_stats.append({
            "type": row[0],
            "total": row[1],
            "covered": row[2],
            "rate": round(row[2] / row[1] * 100, 1) if row[1] > 0 else 0,
        })

    # 6) 커버리지 0건 SR 목록 (진짜 갭)
    cur.execute("""
        SELECT sr.identifier, sr.title, sr.requirement_type, sr.binding_force
        FROM safety_requirements sr
        WHERE NOT EXISTS (SELECT 1 FROM ci_sr_mapping m WHERE m.sr_id = sr.identifier)
        ORDER BY sr.identifier
    """)
    uncovered_list = []
    for row in cur.fetchall():
        uncovered_list.append({
            "id": row[0], "title": row[1],
            "type": row[2], "bindingForce": row[3],
        })

    # 7) 가장 많이 연결된 SR Top 10
    cur.execute("""
        SELECT m.sr_id, sr.title, COUNT(m.ci_id) as ci_count,
               array_agg(DISTINCT g.short_code) as guides
        FROM ci_sr_mapping m
        JOIN safety_requirements sr ON m.sr_id = sr.identifier
        JOIN checklist_items ci ON m.ci_id = ci.identifier
        JOIN kosha_guides g ON ci.source_guide = g.guide_code
        GROUP BY m.sr_id, sr.title
        ORDER BY ci_count DESC
        LIMIT 10
    """)
    top_covered = []
    for row in cur.fetchall():
        top_covered.append({
            "id": row[0], "title": row[1],
            "ciCount": row[2], "guides": row[3],
        })

    conn.close()

    # 보고서 생성
    coverage_rate = round(covered_sr / total_sr * 100, 1) if total_sr > 0 else 0
    normalized_rate = round(coverage_rate / (total_guides / 1038) * 100, 1) if total_guides > 0 else 0

    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalSR": total_sr,
        "totalGuides": total_guides,
        "totalGuidesExpected": 1038,
        "guideProcessingRate": round(total_guides / 1038 * 100, 1),
        "coveredSR": covered_sr,
        "uncoveredSR": uncovered_sr,
        "coverageRate": coverage_rate,
        "normalizedCoverageRate": min(normalized_rate, 100.0),
        "domainStats": domain_stats,
        "typeStats": type_stats,
        "topCoveredSR": top_covered,
        "uncoveredMandatorySR": [u for u in uncovered_list if u["bindingForce"] == "MANDATORY"],
        "uncoveredRecommendedSR": [u for u in uncovered_list if u["bindingForce"] != "MANDATORY"],
        "totalUncoveredMandatory": sum(1 for u in uncovered_list if u["bindingForce"] == "MANDATORY"),
        "totalUncoveredRecommended": sum(1 for u in uncovered_list if u["bindingForce"] != "MANDATORY"),
    }

    report_path = DATA_DIR / "sr-coverage-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # 출력
    print(f"\n  총 SR: {total_sr}")
    print(f"  처리된 가이드: {total_guides}/1,038 ({report['guideProcessingRate']}%)")
    print(f"  커버된 SR: {covered_sr}/{total_sr} ({coverage_rate}%)")
    print(f"  정규화 커버리지: {report['normalizedCoverageRate']}% (전체 가이드 처리 시 추정)")
    print(f"\n  미커버 MANDATORY SR: {report['totalUncoveredMandatory']}개")
    print(f"  미커버 RECOMMENDED SR: {report['totalUncoveredRecommended']}개")

    print(f"\n  도메인별:")
    for d in domain_stats:
        print(f"    {d['domain']}: CI {d['totalCI']}, SR연결 {d['linkedSR']}개, 연결률 {d['linkRate']}%")

    print(f"\n  Top 5 SR:")
    for t in top_covered[:5]:
        print(f"    {t['id']}: CI {t['ciCount']}건, 가이드 {t['guides']}")

    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
