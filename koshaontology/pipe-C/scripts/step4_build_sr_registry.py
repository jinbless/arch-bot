#!/usr/bin/env python3
"""P-C Step 4: sr-registry.json 최종 빌드.

Pipe-A SR + Pipe-B CI/DT/WP + Pipe-C 검증 결과를 통합한 최종 레지스트리.

Usage:
    python3 scripts/step4_build_sr_registry.py
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, PG_CONNINFO


def main():
    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("[START] sr-registry.json 빌드 (Pipe-C Step 4)")

    # 1) SR 본체
    cur.execute("""
        SELECT identifier, title, text, requirement_type, binding_force,
               addresses_hazard, requires_ppe, has_corrective_action,
               has_incident_response, applicable_industry, hazard_assessment
        FROM safety_requirements
        ORDER BY identifier
    """)
    sr_rows = cur.fetchall()

    # 2) SR → NS 매핑
    cur.execute("SELECT sr_id, ns_id FROM sr_ns_mapping ORDER BY sr_id")
    sr_ns = defaultdict(list)
    for row in cur.fetchall():
        sr_ns[row["sr_id"]].append(row["ns_id"])

    # 3) SR → Article 매핑
    cur.execute("SELECT sr_id, law_type, article_code FROM sr_article_mapping ORDER BY sr_id")
    sr_articles = defaultdict(list)
    for row in cur.fetchall():
        sr_articles[row["sr_id"]].append(f"{row['law_type']}:{row['article_code']}")

    # 4) CI → SR 매핑
    cur.execute("""
        SELECT m.sr_id, m.ci_id, g.short_code, g.domain
        FROM ci_sr_mapping m
        JOIN checklist_items ci ON m.ci_id = ci.identifier
        JOIN kosha_guides g ON ci.source_guide = g.guide_code
        ORDER BY m.sr_id
    """)
    sr_ci = defaultdict(lambda: {"ciIds": [], "guides": set(), "domains": set()})
    for row in cur.fetchall():
        sr_ci[row["sr_id"]]["ciIds"].append(row["ci_id"])
        sr_ci[row["sr_id"]]["guides"].add(row["short_code"])
        sr_ci[row["sr_id"]]["domains"].add(row["domain"])

    conn.close()

    # Pipe-C 보고서 로드
    coverage_path = DATA_DIR / "sr-coverage-report.json"
    coverage = json.loads(coverage_path.read_text()) if coverage_path.exists() else {}

    audit_path = DATA_DIR / "basedon-audit-report.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}

    restore_path = DATA_DIR / "basedon-restore-report.json"
    restore = json.loads(restore_path.read_text()) if restore_path.exists() else {}

    # SR 레지스트리 빌드
    registry = []
    for sr in sr_rows:
        sr_id = sr["identifier"]
        ci_info = sr_ci.get(sr_id, {"ciIds": [], "guides": set(), "domains": set()})

        entry = {
            "identifier": sr_id,
            "title": sr["title"],
            "text": sr["text"][:200],  # 요약
            "requirementType": sr["requirement_type"],
            "bindingForce": sr["binding_force"],
            "addressesHazard": sr["addresses_hazard"],

            "pipeA": {
                "mandatedBy": sr_ns.get(sr_id, []),
                "referencesArticle": sr_articles.get(sr_id, []),
                "nsCount": len(sr_ns.get(sr_id, [])),
            },

            "pipeB": {
                "linkedCI": ci_info["ciIds"],
                "linkedGuides": sorted(ci_info["guides"]),
                "linkedDomains": sorted(ci_info["domains"]),
                "ciCount": len(ci_info["ciIds"]),
                "guideCount": len(ci_info["guides"]),
                "requiresPPE": sr["requires_ppe"],
                "hasCorrectiveAction": sr["has_corrective_action"],
                "hasIncidentResponse": sr["has_incident_response"],
                "applicableIndustry": sr["applicable_industry"],
                "hazardAssessment": sr["hazard_assessment"],
            },

            "pipeC": {
                "coverageGap": len(ci_info["ciIds"]) == 0,
                "verified": len(ci_info["ciIds"]) > 0,
            },
        }
        registry.append(entry)

    # 통계
    covered = sum(1 for r in registry if r["pipeB"]["ciCount"] > 0)
    uncovered = sum(1 for r in registry if r["pipeB"]["ciCount"] == 0)

    result = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalSR": len(registry),
        "coveredSR": covered,
        "uncoveredSR": uncovered,
        "coverageRate": round(covered / len(registry) * 100, 1) if registry else 0,
        "pipeC": {
            "auditSuspiciousRate": audit.get("suspiciousRate", 0),
            "restoreHighCount": restore.get("restoreHigh", 0),
            "restoreLowCount": restore.get("restoreLow", 0),
        },
        "registry": registry,
    }

    report_path = DATA_DIR / "sr-registry.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"\n  총 SR: {len(registry)}")
    print(f"  커버: {covered}/{len(registry)} ({result['coverageRate']}%)")
    print(f"  갭: {uncovered}개")
    print(f"  파일 크기: {report_path.stat().st_size // 1024}KB")
    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
