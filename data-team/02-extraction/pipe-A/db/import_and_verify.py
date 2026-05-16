#!/usr/bin/env python3
"""JSON → PostgreSQL 적재 + 참조 무결성 검증.

article-texts.json, penalty-routes.json, ns-batch-*.json을
PostgreSQL kosha DB에 직접 적재하고 9개 참조 무결성 규칙을 검증한다.

Usage:
    python3 db/import_and_verify.py              # 기존 데이터 유지 + 적재
    python3 db/import_and_verify.py --clean       # 테이블 DROP + 재생성 후 적재
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PG_SCHEMA_PATH = SCRIPT_DIR / "schema_pg.sql"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def create_db(clean: bool = False):
    """PostgreSQL 접속 및 스키마 적용."""
    conn = psycopg2.connect(PG_CONNINFO)
    conn.autocommit = False
    cur = conn.cursor()

    if clean:
        cur.execute("DROP TABLE IF EXISTS sr_article_mapping CASCADE")
        cur.execute("DROP TABLE IF EXISTS sr_ns_mapping CASCADE")
        cur.execute("DROP TABLE IF EXISTS safety_requirements CASCADE")
        cur.execute("DROP TABLE IF EXISTS norm_statements CASCADE")
        cur.execute("DROP TABLE IF EXISTS penalty_routes CASCADE")
        cur.execute("DROP TABLE IF EXISTS articles CASCADE")
        conn.commit()
        print("[INFO] 기존 테이블 삭제 완료 (Phase 1 + Phase 2)")

    with open(PG_SCHEMA_PATH, encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()

    print("[OK] PostgreSQL DB 초기화 완료: kosha")
    return conn


def import_articles(conn) -> int:
    """article-texts.json → articles 테이블 적재."""
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()
    count = 0
    for law_id, articles in data["laws"].items():
        for article_code, art in articles.items():
            cur.execute(
                """INSERT INTO articles (law_type, article_code, title, full_text, deleted, section, paragraph_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    law_id,
                    article_code,
                    art["title"],
                    art["fullText"],
                    art["deleted"],
                    art["section"],
                    art["paragraphCount"],
                ),
            )
            count += 1

    conn.commit()
    print(f"[OK] articles 적재: {count}행")
    return count


def import_penalty_routes(conn) -> int:
    """penalty-routes.json → penalty_routes 테이블 적재."""
    with open(DATA_DIR / "penalty-routes.json", encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()
    count = 0
    for article_code, route in data["routes"].items():
        criminal = route.get("criminal") or {}
        ve = criminal.get("violation_employer") or {}
        vc = criminal.get("violation_contractor") or {}
        death = criminal.get("death") or {}
        sa = criminal.get("seriousAccident") or {}
        admin = route.get("administrative") or {}

        cur.execute(
            """INSERT INTO penalty_routes
               (law_type, article_code, title, delegated_from, has_penalty, has_administrative_fine,
                criminal_employer_law, criminal_employer_penalty,
                criminal_contractor_law, criminal_contractor_penalty,
                criminal_death_law, criminal_death_penalty,
                criminal_serious_law, criminal_serious_death, criminal_serious_injury,
                admin_law, admin_max_fine, admin_fine_table_ref, admin_osha_article_ref)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (
                "RULE",
                article_code,
                route["title"],
                route.get("delegatedFrom"),
                route["hasPenalty"],
                route["hasAdministrativeFine"],
                ve.get("law"),
                ve.get("penalty"),
                vc.get("law"),
                vc.get("penalty"),
                death.get("law"),
                death.get("penalty"),
                sa.get("law"),
                sa.get("death"),
                sa.get("injury"),
                admin.get("law"),
                admin.get("maxFine"),
                admin.get("fineTableRef"),
                admin.get("oshaArticleRef"),
            ),
        )
        count += 1

    conn.commit()
    print(f"[OK] penalty_routes 적재: {count}행")
    return count


def import_norm_statements(conn) -> int:
    """ns-batch-*.json → norm_statements 테이블 적재. JSONB 컬럼은 Json() 래핑."""
    ns_dir = DATA_DIR / "norm-statements"
    ns_files = sorted(ns_dir.glob("ns-batch-*.json"))
    if not ns_files:
        print("[INFO] NS 파일 없음 — norm_statements 적재 건너뜀")
        return 0

    cur = conn.cursor()
    count = 0
    for ns_file in ns_files:
        with open(ns_file, encoding="utf-8") as f:
            data = json.load(f)

        for ns in data.get("normStatements", []):
            cur.execute(
                """INSERT INTO norm_statements
                   (identifier, article_code, law_id, paragraph_ref, text, has_modality,
                    has_subject_role, has_action, has_object, has_condition,
                    has_sanction, has_modification_link, role_guidance)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    ns["identifier"],
                    ns["articleCode"],
                    ns["lawId"],
                    ns["paragraphRef"],
                    ns["text"],
                    ns["hasModality"],
                    ns.get("hasSubjectRole"),
                    ns.get("hasAction"),
                    ns.get("hasObject"),
                    Json(ns["hasCondition"]) if ns.get("hasCondition") is not None else None,
                    Json(ns["hasSanction"]) if ns.get("hasSanction") is not None else None,
                    Json(ns["hasModificationLink"]) if ns.get("hasModificationLink") is not None else None,
                    Json(ns["roleGuidance"]) if ns.get("roleGuidance") is not None else None,
                ),
            )
            count += 1

    conn.commit()
    print(f"[OK] norm_statements 적재: {count}행 ({len(ns_files)}개 파일)")
    return count


def verify(conn) -> list[dict]:
    """9개 참조 무결성 규칙 검증."""
    cur = conn.cursor()
    errors = []

    cur.execute("""SELECT p.article_code FROM penalty_routes p
           WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.law_type = 'RULE' AND a.article_code = p.article_code)""")
    for row in cur.fetchall():
        errors.append({"rule": "V1_FK_PENALTY_TO_ARTICLE", "detail": f"articles(RULE)에 없음: {row[0]}"})

    cur.execute("""SELECT p.article_code, p.delegated_from FROM penalty_routes p
           WHERE p.delegated_from IS NOT NULL AND NOT EXISTS (SELECT 1 FROM articles a WHERE a.law_type = 'OSHA' AND a.article_code = p.delegated_from)""")
    for row in cur.fetchall():
        errors.append({"rule": "V2_FK_DELEGATION_TO_OSHA", "detail": f"{row[0]}.delegatedFrom={row[1]} → OSHA에 없음"})

    cur.execute("""SELECT law_type, article_code, COUNT(*) as cnt FROM articles GROUP BY law_type, article_code HAVING COUNT(*) > 1""")
    for row in cur.fetchall():
        errors.append({"rule": "V3_DUPLICATE_ARTICLE", "detail": f"{row[0]}.{row[1]} 중복 {row[2]}건"})

    cur.execute("""SELECT article_code, COUNT(*) as cnt FROM penalty_routes GROUP BY article_code HAVING COUNT(*) > 1""")
    for row in cur.fetchall():
        errors.append({"rule": "V4_DUPLICATE_PENALTY", "detail": f"{row[0]} 중복 {row[1]}건"})

    cur.execute("""SELECT p.article_code FROM penalty_routes p JOIN articles a ON a.law_type = 'RULE' AND a.article_code = p.article_code WHERE a.deleted = true""")
    for row in cur.fetchall():
        errors.append({"rule": "V5_DELETED_IN_PENALTY", "detail": f"삭제 조문이 penalty_routes에 있음: {row[0]}"})

    cur.execute("""SELECT article_code FROM penalty_routes WHERE has_penalty = true AND (criminal_employer_law IS NULL OR criminal_employer_penalty IS NULL)""")
    for row in cur.fetchall():
        errors.append({"rule": "V6_PENALTY_WITHOUT_CRIMINAL", "detail": f"hasPenalty=true인데 criminal_employer 없음: {row[0]}"})

    cur.execute("""SELECT article_code FROM penalty_routes WHERE has_administrative_fine = true AND admin_law IS NULL""")
    for row in cur.fetchall():
        errors.append({"rule": "V7_ADMIN_FINE_WITHOUT_LAW", "detail": f"hasAdministrativeFine=true인데 admin_law 없음: {row[0]}"})

    cur.execute("SELECT COUNT(*) FROM norm_statements")
    ns_count = cur.fetchone()[0]
    if ns_count > 0:
        cur.execute("""SELECT n.identifier, n.law_id, n.article_code FROM norm_statements n
               WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.law_type = n.law_id AND a.article_code = n.article_code)""")
        for row in cur.fetchall():
            errors.append({"rule": "V8_FK_NS_TO_ARTICLE", "detail": f"{row[0]}: articles에 없음 ({row[1]}.{row[2]})"})

        cur.execute("""SELECT identifier, COUNT(*) as cnt FROM norm_statements GROUP BY identifier HAVING COUNT(*) > 1""")
        for row in cur.fetchall():
            errors.append({"rule": "V9_DUPLICATE_NS", "detail": f"{row[0]} 중복 {row[1]}건"})

    return errors


def print_summary(conn, errors: list[dict]):
    """검증 결과 요약 출력."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    art_count = cur.fetchone()[0]
    cur.execute("SELECT law_type, COUNT(*) FROM articles GROUP BY law_type ORDER BY law_type")
    art_by_law = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM penalty_routes")
    penalty_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM penalty_routes WHERE has_penalty = true")
    penalty_yes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM penalty_routes WHERE has_administrative_fine = true")
    admin_yes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM articles WHERE deleted = true")
    deleted_count = cur.fetchone()[0]

    print("\n" + "=" * 50)
    print("DB 적재 + 참조 무결성 검증 리포트 (PostgreSQL)")
    print("=" * 50)
    print(f"\n[articles] 총 {art_count}행")
    for law, cnt in art_by_law:
        print(f"  {law}: {cnt}")
    print(f"  삭제: {deleted_count}")
    print(f"\n[penalty_routes] 총 {penalty_count}행")
    print(f"  형사벌 적용: {penalty_yes}, 미적용: {penalty_count - penalty_yes}")
    print(f"  과태료 적용: {admin_yes}, 미적용: {penalty_count - admin_yes}")

    cur.execute("SELECT COUNT(*) FROM norm_statements")
    ns_count = cur.fetchone()[0]
    if ns_count > 0:
        cur.execute("SELECT has_modality, COUNT(*) FROM norm_statements GROUP BY has_modality ORDER BY COUNT(*) DESC")
        ns_by_modality = cur.fetchall()
        cur.execute("SELECT COUNT(DISTINCT article_code) FROM norm_statements")
        ns_articles = cur.fetchone()[0]
        print(f"\n[norm_statements] 총 {ns_count}행 ({ns_articles}개 조문)")
        for mod, cnt in ns_by_modality:
            print(f"  {mod}: {cnt}")

    print(f"\n[검증 결과] ", end="")
    if not errors:
        print("ALL PASS (V1~V15, 에러 0건)")
    else:
        print(f"FAIL ({len(errors)}건)")
        for e in errors:
            print(f"  [{e['rule']}] {e['detail']}")

    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "articles": art_count,
        "articlesByLaw": dict(art_by_law),
        "deletedArticles": deleted_count,
        "penaltyRoutes": penalty_count,
        "penaltyWithPenalty": penalty_yes,
        "penaltyWithAdminFine": admin_yes,
        "passed": len(errors) == 0,
        "errorCount": len(errors),
        "errors": errors,
    }



# ══════════════════════════════════════════════════════════
# Phase 2: SR 적재 + V10~V15 검증
# ══════════════════════════════════════════════════════════

def import_safety_requirements(conn) -> int:
    """sr-batch-*.json → safety_requirements + sr_ns_mapping + sr_article_mapping 적재."""
    import glob

    sr_dir = DATA_DIR / "safety-requirements"
    sr_files = sorted(sr_dir.glob("sr-batch-*.json"))
    sr_files = [f for f in sr_files if not f.name.endswith("-input.json")]

    if not sr_files:
        print("[INFO] SR 파일 없음 — safety_requirements 적재 건너뜀")
        return 0

    cur = conn.cursor()
    sr_count = 0
    ns_map_count = 0
    art_map_count = 0

    for sr_file in sr_files:
        with open(sr_file, encoding="utf-8") as f:
            data = json.load(f)

        for sr in data.get("safetyRequirements", []):
            # safety_requirements 본체
            cur.execute(
                """INSERT INTO safety_requirements
                   (identifier, title, text, requirement_type, binding_force,
                    addresses_hazard, structural_requirements, has_sanction,
                    has_modification_link, requires_ppe, has_corrective_action,
                    has_incident_response, applicable_industry, hazard_assessment)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    sr["identifier"],
                    sr["title"],
                    sr["text"],
                    sr["requirementType"],
                    sr.get("bindingForce", "MANDATORY"),
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

            # sr_ns_mapping (mandatedBy)
            for ns_id in sr.get("mandatedBy", []):
                cur.execute(
                    """INSERT INTO sr_ns_mapping (sr_id, ns_id)
                       VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                    (sr["identifier"], ns_id),
                )
                ns_map_count += 1

            # sr_article_mapping (referencesArticle)
            for article_code in sr.get("referencesArticle", []):
                cur.execute(
                    """INSERT INTO sr_article_mapping (sr_id, law_type, article_code)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    (sr["identifier"], "RULE", article_code),
                )
                art_map_count += 1

    conn.commit()
    print(f"[OK] safety_requirements 적재: {sr_count}행 ({len(sr_files)}개 파일)")
    print(f"     sr_ns_mapping 적재: {ns_map_count}행")
    print(f"     sr_article_mapping 적재: {art_map_count}행")
    return sr_count


def verify_sr(conn) -> list[dict]:
    """V10~V15: SR 관련 참조 무결성 검증."""
    cur = conn.cursor()
    errors = []

    # V10: SR 행 수
    cur.execute("SELECT COUNT(*) FROM safety_requirements")
    sr_db = cur.fetchone()[0]
    if sr_db == 0:
        print("[INFO] safety_requirements 0행 — SR 검증 건너뜀")
        return errors

    # V11: sr_ns_mapping의 모든 ns_id가 norm_statements에 존재
    cur.execute("""SELECT m.ns_id FROM sr_ns_mapping m
           WHERE NOT EXISTS (SELECT 1 FROM norm_statements n WHERE n.identifier = m.ns_id)""")
    for row in cur.fetchall():
        errors.append({"rule": "V11_FK_SRNS_TO_NS", "detail": f"sr_ns_mapping.ns_id가 norm_statements에 없음: {row[0]}"})

    # V12: sr_ns_mapping의 모든 sr_id가 safety_requirements에 존재
    cur.execute("""SELECT m.sr_id FROM sr_ns_mapping m
           WHERE NOT EXISTS (SELECT 1 FROM safety_requirements s WHERE s.identifier = m.sr_id)""")
    for row in cur.fetchall():
        errors.append({"rule": "V12_FK_SRNS_TO_SR", "detail": f"sr_ns_mapping.sr_id가 safety_requirements에 없음: {row[0]}"})

    # V13: sr_article_mapping FK
    cur.execute("""SELECT m.sr_id, m.law_type, m.article_code FROM sr_article_mapping m
           WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.law_type = m.law_type AND a.article_code = m.article_code)""")
    for row in cur.fetchall():
        errors.append({"rule": "V13_FK_SRART_TO_ARTICLE", "detail": f"{row[0]}: articles에 없음 ({row[1]}.{row[2]})"})

    # V14: OBLIGATION NS 중 SR에 연결되지 않은 NS (커버리지)
    cur.execute("""SELECT n.identifier FROM norm_statements n
           WHERE n.has_modality IN ('OBLIGATION', 'PROHIBITION')
             AND n.law_id = 'RULE'
             AND NOT EXISTS (SELECT 1 FROM sr_ns_mapping m WHERE m.ns_id = n.identifier)""")
    unmapped = cur.fetchall()
    if unmapped:
        errors.append({"rule": "V14_NS_COVERAGE", "detail": f"SR에 연결되지 않은 OBLIGATION/PROHIBITION NS: {len(unmapped)}건"})

    # V15: SR identifier 중복
    cur.execute("""SELECT identifier, COUNT(*) FROM safety_requirements GROUP BY identifier HAVING COUNT(*) > 1""")
    for row in cur.fetchall():
        errors.append({"rule": "V15_DUPLICATE_SR", "detail": f"{row[0]} 중복 {row[1]}건"})

    return errors

def main():
    parser = argparse.ArgumentParser(description="JSON → PostgreSQL 적재 + 참조 무결성 검증")
    parser.add_argument("--clean", action="store_true", help="테이블 DROP 후 재생성")
    args = parser.parse_args()

    conn = create_db(clean=args.clean)

    try:
        import_articles(conn)
        import_penalty_routes(conn)
        import_norm_statements(conn)
        import_safety_requirements(conn)
        errors = verify(conn)
        sr_errors = verify_sr(conn)
        errors.extend(sr_errors)
        report = print_summary(conn, errors)

        report_path = DATA_DIR / "validation" / "db-verification-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 리포트 저장: {report_path}")

        if not report["passed"]:
            sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()

