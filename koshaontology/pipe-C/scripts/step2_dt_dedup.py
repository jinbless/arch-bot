#!/usr/bin/env python3
"""P-C Step 2: DT 중복 탐지 + canonical_id 부여.

도메인 내(intra-domain) 완전 일치 중복 우선, 교차 도메인 참고용.

Usage:
    python3 scripts/step2_dt_dedup.py
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

    print("[START] DT 중복 탐지 (Pipe-C Step 2)")

    # 총 DT 수
    cur.execute("SELECT COUNT(*) FROM domain_terms")
    total_dt = cur.fetchone()[0]

    # 1) 도메인 내 완전 일치 중복
    cur.execute("""
        SELECT dt.term, g.domain, COUNT(*) as dup_count,
               array_agg(dt.identifier ORDER BY dt.identifier) as dt_ids,
               array_agg(g.short_code ORDER BY dt.identifier) as guides,
               array_agg(dt.definition ORDER BY dt.identifier) as definitions
        FROM domain_terms dt
        JOIN kosha_guides g ON dt.source_guide = g.guide_code
        GROUP BY dt.term, g.domain
        HAVING COUNT(*) > 1
        ORDER BY dup_count DESC
    """)
    intra_dups = []
    for row in cur.fetchall():
        intra_dups.append({
            "term": row[0], "domain": row[1],
            "count": row[2], "dtIds": row[3],
            "guides": row[4],
            "definitions": [d[:100] for d in row[5]],  # 100자로 잘라 보기
        })

    # 2) 교차 도메인 완전 일치 (참고용)
    cur.execute("""
        SELECT dt.term, COUNT(DISTINCT g.domain) as domain_count,
               array_agg(DISTINCT g.domain ORDER BY g.domain) as domains,
               COUNT(*) as total_count
        FROM domain_terms dt
        JOIN kosha_guides g ON dt.source_guide = g.guide_code
        GROUP BY dt.term
        HAVING COUNT(DISTINCT g.domain) > 1
        ORDER BY domain_count DESC, total_count DESC
    """)
    cross_dups = []
    for row in cur.fetchall():
        cross_dups.append({
            "term": row[0], "domainCount": row[1],
            "domains": row[2], "totalCount": row[3],
        })

    # 3) 유사 용어 (앞 3글자 동일 + 다른 정의, 같은 도메인)
    cur.execute("""
        SELECT a.term, b.term, a.identifier, b.identifier, g1.domain
        FROM domain_terms a
        JOIN domain_terms b ON a.identifier < b.identifier
        JOIN kosha_guides g1 ON a.source_guide = g1.guide_code
        JOIN kosha_guides g2 ON b.source_guide = g2.guide_code
        WHERE g1.domain = g2.domain
          AND left(a.term, 3) = left(b.term, 3)
          AND a.term != b.term
          AND length(a.term) >= 3
        ORDER BY g1.domain, a.term
        LIMIT 50
    """)
    similar = []
    for row in cur.fetchall():
        similar.append({
            "termA": row[0], "termB": row[1],
            "idA": row[2], "idB": row[3],
            "domain": row[4],
        })

    conn.close()

    # 보고서
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalDT": total_dt,
        "intraDomainDuplicates": intra_dups,
        "totalIntraDuplicateGroups": len(intra_dups),
        "totalIntraDuplicateTerms": sum(d["count"] for d in intra_dups),
        "crossDomainDuplicates": cross_dups,
        "totalCrossDomainTerms": len(cross_dups),
        "similarTerms": similar,
        "totalSimilarPairs": len(similar),
    }

    report_path = DATA_DIR / "dt-dedup-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # 출력
    print(f"\n  총 DT: {total_dt}")
    print(f"\n  도메인 내 완전 일치 중복: {len(intra_dups)}개 그룹 ({sum(d['count'] for d in intra_dups)}건)")
    for d in intra_dups[:10]:
        print(f"    [{d['domain']}] \"{d['term']}\" × {d['count']} ({', '.join(d['guides'])})")
    if len(intra_dups) > 10:
        print(f"    ... +{len(intra_dups) - 10}개 그룹")

    print(f"\n  교차 도메인 중복: {len(cross_dups)}개 용어")
    for c in cross_dups[:5]:
        print(f"    \"{c['term']}\" → {c['domains']} ({c['totalCount']}건)")

    print(f"\n  유사 용어 쌍: {len(similar)}개")
    for s in similar[:5]:
        print(f"    [{s['domain']}] \"{s['termA']}\" ↔ \"{s['termB']}\"")

    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
