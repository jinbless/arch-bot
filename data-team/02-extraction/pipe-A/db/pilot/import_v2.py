#!/usr/bin/env python3
"""Pilot v2 적재: pipe-A/data/pilot/safety-requirements-v2/sr-batch-PILOT-*.json
→ safety_requirements_v2 / sr_ns_mapping_v2 / sr_article_mapping_v2.

원본 db/import_and_verify.py의 import_safety_requirements()를 fork.
변경: 테이블명 *_v2, 입력 dir, identifier VARCHAR(40) 허용 (SR-PILOT_<CAT>-<seq> prefix 길이).

Usage:
    PYTHONUTF8=1 python db/pilot/import_v2.py
    PYTHONUTF8=1 python db/pilot/import_v2.py --clean   (기존 v2 데이터 모두 삭제)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

PIPE_A_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPE_A_ROOT / "data"
SR_DIR_V2 = DATA_DIR / "pilot" / "safety-requirements-v2"
SCHEMA_FILE = Path(__file__).resolve().parent / "schema_v2.sql"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def apply_schema(conn) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"[OK] schema_v2.sql 적용 완료")


def clean_v2(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS sr_article_mapping_v2 CASCADE")
        cur.execute("DROP TABLE IF EXISTS sr_ns_mapping_v2 CASCADE")
        cur.execute("DROP TABLE IF EXISTS safety_requirements_v2 CASCADE")
    conn.commit()
    print(f"[OK] v2 테이블 삭제 (CASCADE)")


def import_v2(conn) -> tuple[int, int, int]:
    sr_files = sorted(SR_DIR_V2.glob("sr-batch-PILOT-*.json"))
    sr_files = [f for f in sr_files if not f.name.endswith("-input.json")]
    if not sr_files:
        print(f"[ERR] {SR_DIR_V2}에 sr-batch-PILOT-*.json 없음")
        return 0, 0, 0

    cur = conn.cursor()
    sr_count = ns_map_count = art_map_count = 0
    for sr_file in sr_files:
        with open(sr_file, encoding="utf-8") as f:
            data = json.load(f)
        for sr in data.get("safetyRequirements", []):
            cur.execute(
                """INSERT INTO safety_requirements_v2
                   (identifier, title, text, requirement_type, binding_force,
                    addresses_hazard, structural_requirements, has_sanction,
                    has_modification_link, requires_ppe, has_corrective_action,
                    has_incident_response, applicable_industry, hazard_assessment)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    sr["identifier"], sr["title"], sr["text"],
                    sr["requirementType"], sr.get("bindingForce", "MANDATORY"),
                    Json(sr.get("addressesHazard")) if sr.get("addressesHazard") is not None else None,
                    Json(sr.get("structuralRequirements")) if sr.get("structuralRequirements") is not None else None,
                    Json(sr.get("hasSanction")) if sr.get("hasSanction") is not None else None,
                    Json(sr.get("hasModificationLink")) if sr.get("hasModificationLink") is not None else None,
                    Json(sr.get("requiresPPE")) if sr.get("requiresPPE") is not None else None,
                    Json(sr.get("hasCorrectiveAction")) if sr.get("hasCorrectiveAction") is not None else None,
                    Json(sr.get("hasIncidentResponse")) if sr.get("hasIncidentResponse") is not None else None,
                    Json(sr.get("applicableIndustry")) if sr.get("applicableIndustry") is not None else None,
                    Json(sr.get("hazardAssessment")) if sr.get("hazardAssessment") is not None else None,
                ),
            )
            sr_count += 1
            for ns_id in sr.get("mandatedBy", []):
                cur.execute(
                    "INSERT INTO sr_ns_mapping_v2 (sr_id, ns_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (sr["identifier"], ns_id),
                )
                ns_map_count += 1
            for ac in sr.get("referencesArticle", []):
                cur.execute(
                    "INSERT INTO sr_article_mapping_v2 (sr_id, law_type, article_code) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (sr["identifier"], "RULE", ac),
                )
                art_map_count += 1
    conn.commit()
    print(f"[OK] safety_requirements_v2: {sr_count}행 ({len(sr_files)} 파일)")
    print(f"[OK] sr_ns_mapping_v2: {ns_map_count}행")
    print(f"[OK] sr_article_mapping_v2: {art_map_count}행")
    return sr_count, ns_map_count, art_map_count


def verify(conn) -> None:
    """v2 무결성 + v1 무손상 + multi-SR 발생 확인."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM safety_requirements")
    v1_cnt = cur.fetchone()[0]
    print(f"\n[VERIFY] v1 safety_requirements: {v1_cnt}행 (무손상 기대: 626)")
    assert v1_cnt == 626, f"v1 SR이 626이 아닙니다: {v1_cnt}"

    cur.execute("SELECT COUNT(*) FROM safety_requirements_v2")
    v2_cnt = cur.fetchone()[0]
    print(f"[VERIFY] v2 safety_requirements_v2: {v2_cnt}행 (기대: 42)")

    cur.execute("""SELECT article_code, COUNT(DISTINCT sr_id)
                   FROM sr_article_mapping_v2
                   GROUP BY article_code ORDER BY 2 DESC""")
    rows = cur.fetchall()
    print(f"\n[VERIFY] article별 v2 SR 수:")
    for ac, cnt in rows:
        marker = "OK" if cnt >= 2 else "FAIL"
        print(f"  [{marker}] {ac}: {cnt} SR")

    multi_sr_articles = sum(1 for _, cnt in rows if cnt >= 2)
    rate = multi_sr_articles / max(1, len(rows))
    print(f"\n[VERIFY] Multi-SR 발생률: {multi_sr_articles}/{len(rows)} ({rate:.0%}) — G1 ≥80%")

    cur.execute("""SELECT COUNT(*) FROM (
                     SELECT a.sr_id, b.sr_id, a.article_code
                     FROM sr_article_mapping_v2 a
                     JOIN sr_article_mapping_v2 b USING(article_code)
                     WHERE a.sr_id < b.sr_id
                   ) p""")
    pair_cnt = cur.fetchone()[0]
    print(f"[VERIFY] coApplicable 후보 쌍: {pair_cnt} (G3: ≥ 2 × multi-SR article 수 = ≥ {2*multi_sr_articles})")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Pilot v2 적재")
    parser.add_argument("--clean", action="store_true", help="기존 v2 테이블 DROP 후 재생성")
    args = parser.parse_args()

    with psycopg2.connect(PG_CONNINFO) as conn:
        if args.clean:
            clean_v2(conn)
        apply_schema(conn)
        import_v2(conn)
        verify(conn)


if __name__ == "__main__":
    main()
