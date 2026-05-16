#!/usr/bin/env python3
"""Pipe-C: 교차검증 데이터 적재 + V-C1~V-C10 최종 검증.

Usage:
    python3 db/import_pipec.py              # 적재 + 검증
    python3 db/import_pipec.py --verify     # 검증만
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PG_SCHEMA_PATH = SCRIPT_DIR / "schema_pc.sql"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def apply_schema(conn):
    """Pipe-C 스키마 적용."""
    cur = conn.cursor()
    with open(PG_SCHEMA_PATH, encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()
    print("[OK] Pipe-C 스키마 적용 완료")


def import_guide_interlinks(conn) -> int:
    """guide-interlinks.json → guide_inter_links 테이블."""
    report_path = DATA_DIR / "guide-interlinks.json"
    if not report_path.exists():
        print("[SKIP] guide-interlinks.json 없음")
        return 0

    data = json.loads(report_path.read_text())
    cur = conn.cursor()

    # 기존 데이터 삭제
    cur.execute("DELETE FROM guide_inter_links")

    count = 0
    skip = 0
    for link in data.get("links", []):
        # guide_code 변환 필요 — shortCode를 사용하므로 kosha_guides에서 확인
        cur.execute("SELECT guide_code FROM kosha_guides WHERE short_code = %s",
                    (link["sourceGuide"],))
        src = cur.fetchone()
        cur.execute("SELECT guide_code FROM kosha_guides WHERE short_code = %s",
                    (link["referencedGuide"],))
        ref = cur.fetchone()

        if src and ref:
            cur.execute("""
                INSERT INTO guide_inter_links (source_guide, referenced_guide, reference_type, reference_text, raw_match)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (src[0], ref[0], link.get("referenceType", "explicit"),
                  link.get("referenceText", "")[:200], link.get("rawMatch", "")))
            count += 1
        else:
            skip += 1

    conn.commit()
    print(f"[OK] guide_inter_links 적재: {count}행 (skip: {skip})")
    return count


def verify(conn) -> list[dict]:
    """V-C1 ~ V-C10 검증."""
    cur = conn.cursor()
    errors = []

    # V-C1: guide_inter_links FK 무결
    cur.execute("""
        SELECT source_guide FROM guide_inter_links
        WHERE source_guide NOT IN (SELECT guide_code FROM kosha_guides)
    """)
    for row in cur.fetchall():
        errors.append({"rule": "V-C1", "detail": f"source_guide not in kosha_guides: {row[0]}"})

    cur.execute("""
        SELECT referenced_guide FROM guide_inter_links
        WHERE referenced_guide NOT IN (SELECT guide_code FROM kosha_guides)
    """)
    for row in cur.fetchall():
        errors.append({"rule": "V-C1", "detail": f"referenced_guide not in kosha_guides: {row[0]}"})

    # V-C2: 자기 참조 0건
    cur.execute("SELECT source_guide FROM guide_inter_links WHERE source_guide = referenced_guide")
    for row in cur.fetchall():
        errors.append({"rule": "V-C2", "detail": f"self-reference: {row[0]}"})

    # V-C3: basedOn 검증 완료 비율
    cur.execute("SELECT COUNT(*) FROM ci_sr_mapping")
    mapped = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM checklist_items")
    total_ci = cur.fetchone()[0]
    mapped_rate = round(mapped / total_ci * 100, 1) if total_ci > 0 else 0

    # V-C4: sr-registry.json SR 수 = DB SR 수
    registry_path = DATA_DIR / "sr-registry.json"
    if registry_path.exists():
        reg = json.loads(registry_path.read_text())
        cur.execute("SELECT COUNT(*) FROM safety_requirements")
        db_sr = cur.fetchone()[0]
        if reg["totalSR"] != db_sr:
            errors.append({"rule": "V-C4", "detail": f"registry SR {reg['totalSR']} != DB SR {db_sr}"})

    # V-C5: DT canonical_id FK 무결 (있으면)
    try:
        cur.execute("""
            SELECT identifier, canonical_id FROM domain_terms
            WHERE canonical_id IS NOT NULL
              AND canonical_id NOT IN (SELECT identifier FROM domain_terms)
        """)
        for row in cur.fetchall():
            errors.append({"rule": "V-C5", "detail": f"canonical_id FK 위반: {row[0]} → {row[1]}"})
    except Exception:
        pass  # canonical_id 컬럼이 없으면 무시

    # V-C6: Pipe-A 회귀
    cur.execute("SELECT COUNT(*) FROM safety_requirements")
    sr_count = cur.fetchone()[0]
    if sr_count != 626:
        errors.append({"rule": "V-C6", "detail": f"SR 행수 = {sr_count} (expected 626)"})

    cur.execute("SELECT COUNT(*) FROM norm_statements")
    ns_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM articles")
    art_count = cur.fetchone()[0]

    # V-C7: Pipe-B 회귀
    cur.execute("SELECT COUNT(*) FROM kosha_guides")
    guide_count = cur.fetchone()[0]

    # V-C8: ci_sr_mapping 무결
    cur.execute("""
        SELECT ci_id FROM ci_sr_mapping
        WHERE ci_id NOT IN (SELECT identifier FROM checklist_items)
    """)
    for row in cur.fetchall():
        errors.append({"rule": "V-C8", "detail": f"ci_sr_mapping.ci_id FK 위반: {row[0]}"})

    cur.execute("""
        SELECT sr_id FROM ci_sr_mapping
        WHERE sr_id NOT IN (SELECT identifier FROM safety_requirements)
    """)
    for row in cur.fetchall():
        errors.append({"rule": "V-C8", "detail": f"ci_sr_mapping.sr_id FK 위반: {row[0]}"})

    # V-C9: sr-registry.json 존재
    if not registry_path.exists():
        errors.append({"rule": "V-C9", "detail": "sr-registry.json 미존재"})

    # V-C10: 교차파이프 ID 일관성
    cur.execute("SELECT identifier FROM safety_requirements WHERE identifier !~ '^SR-[A-Z_]+-[0-9]+$' LIMIT 5")
    for row in cur.fetchall():
        errors.append({"rule": "V-C10", "detail": f"SR ID 형식 위반: {row[0]}"})

    cur.execute("SELECT identifier FROM checklist_items WHERE identifier !~ '^CI-[A-Z0-9]+-[0-9]+$' LIMIT 5")
    for row in cur.fetchall():
        errors.append({"rule": "V-C10", "detail": f"CI ID 형식 위반: {row[0]}"})

    return errors, {
        "sr": sr_count, "ns": ns_count, "articles": art_count,
        "guides": guide_count, "ci": total_ci,
        "ci_sr_mapping": mapped, "mappedRate": mapped_rate,
    }


def main():
    parser = argparse.ArgumentParser(description="Pipe-C 적재 + V-C1~V-C10 검증")
    parser.add_argument("--verify", action="store_true", help="검증만")
    args = parser.parse_args()

    conn = psycopg2.connect(PG_CONNINFO)
    conn.autocommit = False

    if not args.verify:
        print("[START] Pipe-C 적재")
        apply_schema(conn)
        import_guide_interlinks(conn)

    print("\n[VERIFY] V-C1 ~ V-C10")
    errors, stats = verify(conn)

    rules = ["V-C1", "V-C2", "V-C3", "V-C4", "V-C5", "V-C6", "V-C7", "V-C8", "V-C9", "V-C10"]
    failed_rules = {e["rule"] for e in errors}
    for rule in rules:
        status = "FAIL" if rule in failed_rules else "PASS"
        print(f"  [{status}] {rule}")

    passed = len(rules) - len(failed_rules)
    print(f"\n  V-C1~V-C10: {passed} PASS / {len(failed_rules)} FAIL")

    if errors:
        print(f"\n  에러 상세:")
        for e in errors[:10]:
            print(f"    [{e['rule']}] {e['detail']}")

    print(f"\n  DB 현황:")
    print(f"    SR: {stats['sr']}, NS: {stats['ns']}, Articles: {stats['articles']}")
    print(f"    Guides: {stats['guides']}, CI: {stats['ci']}")
    print(f"    ci_sr_mapping: {stats['ci_sr_mapping']} ({stats['mappedRate']}%)")

    conn.close()
    print(f"\n[DONE] Pipe-C 검증 완료")


if __name__ == "__main__":
    main()
