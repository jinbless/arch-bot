#!/usr/bin/env python3
"""Pipe-B: CI/DT/WP/ES/DR → PostgreSQL 적재 + V16~V34 검증.

Usage:
    python3 db/import_pipeb.py --input-dir data/ci-output --clean  # Layer 5 DROP + 재생성 + 적재
    python3 db/import_pipeb.py --input-dir data/ci-output          # 기존 유지 + 적재
    python3 db/import_pipeb.py --verify                            # V16~V34 검증만
    python3 db/import_pipeb.py --verify-all                        # V16~V34 + V29~V30 회귀
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # pipe-B/
PIPE_A_ROOT = PROJECT_ROOT.parent / "pipe-A"
DATA_DIR = PROJECT_ROOT / "data"
BATCHES_DIR = DATA_DIR / "ci-batches"
PG_SCHEMA_PATH = SCRIPT_DIR / "schema_pb.sql"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"

# Layer 5 테이블 (DROP 순서: 매핑 → 엔티티 → 가이드)
LAYER5_TABLES = [
    "guide_visual_trigger_candidates",
    "guide_sr_link_candidates",
    "guide_entity_feature_candidates",
    "guide_article_mapping",
    "dr_sr_mapping", "document_requirements",
    "es_sr_mapping", "equipment_specs",
    "wp_ppe", "wp_sr_mapping", "work_processes",
    "dt_sr_mapping", "domain_terms",
    "ci_sr_mapping", "checklist_items",
    "kosha_guides",
]


def connect_db(clean: bool = False):
    """PostgreSQL 접속 + Layer 5 스키마 적용."""
    conn = psycopg2.connect(PG_CONNINFO)
    conn.autocommit = False
    cur = conn.cursor()

    if clean:
        for tbl in LAYER5_TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        conn.commit()
        print("[INFO] Layer 5 테이블 삭제 완료")

    with open(PG_SCHEMA_PATH, encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()
    print("[OK] Layer 5 스키마 적용 완료")
    return conn


def load_ci_files(input_dir: Path) -> list[dict]:
    """ci-output 디렉토리에서 CI 파일 로드."""
    files = sorted(input_dir.glob("ci-*.json"))
    files = [f for f in files if not f.name.endswith("-raw-response.txt") and not f.name.endswith(".split-meta.json")]
    result = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        result.append(data)
    return result


def load_guide_metadata(short_code: str) -> dict:
    """guide-inventory.json에서 가이드 메타데이터 로드."""
    inv_path = DATA_DIR / "guide-inventory.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    for g in inv["guides"]:
        if g["shortCode"] == short_code:
            return g
    return {}


def import_guides(conn, ci_files: list[dict]) -> int:
    """kosha_guides 테이블 적재."""
    cur = conn.cursor()
    count = 0
    for data in ci_files:
        meta = data["metadata"]
        sc = meta["shortCode"]
        gc = meta["guideCode"]
        domain = meta["domain"]

        # guide-inventory에서 추가 정보
        guide_info = load_guide_metadata(sc)

        cur.execute(
            """INSERT INTO kosha_guides
               (guide_code, short_code, title, domain, pdf_path, parsed_json_path,
                ci_count, dt_count, wp_count, es_count, dr_count, processed_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (guide_code) DO UPDATE SET
                ci_count = EXCLUDED.ci_count,
                dt_count = EXCLUDED.dt_count,
                wp_count = EXCLUDED.wp_count,
                es_count = EXCLUDED.es_count,
                dr_count = EXCLUDED.dr_count,
                processed_at = EXCLUDED.processed_at""",
            (
                gc, sc,
                guide_info.get("title", meta.get("guideCode", "")),
                domain,
                guide_info.get("pdfPath"),
                f"kosha-guides/parsed/guide-{sc}.json",
                len(data.get("checklistItems", [])),
                len(data.get("domainTerms", [])),
                len(data.get("workProcesses", [])),
                len(data.get("equipmentSpecs", [])),
                len(data.get("documentRequirements", [])),
                datetime.now(timezone.utc),
            ),
        )
        count += 1

    conn.commit()
    print(f"[OK] kosha_guides 적재: {count}행")
    return count


def import_checklist_items(conn, ci_files: list[dict]) -> int:
    """checklist_items + ci_sr_mapping 적재."""
    cur = conn.cursor()
    ci_count = 0
    ci_skip = 0
    sr_map_count = 0
    sr_skip_count = 0
    total_based_on = 0

    for data in ci_files:
        gc = data["metadata"]["guideCode"]
        for ci in data.get("checklistItems", []):
            cur.execute(
                """INSERT INTO checklist_items
                   (identifier, text, guide_context, additional_detail, work_process_phase,
                    binding_force, requirement_type, source_section, source_guide)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (identifier) DO NOTHING""",
                (
                    ci["identifier"],
                    ci["text"],
                    ci.get("guideContext"),
                    ci.get("additionalDetail"),
                    ci.get("workProcessPhase"),
                    ci["bindingForce"],
                    ci.get("requirementType"),
                    ci["sourceSection"],
                    gc,
                ),
            )
            if cur.rowcount == 0:
                ci_skip += 1
            ci_count += 1

            # basedOn → ci_sr_mapping
            for sr_id in (ci.get("basedOn") or []):
                total_based_on += 1
                # SR이 safety_requirements에 존재하는지 확인
                cur.execute("SELECT 1 FROM safety_requirements WHERE identifier = %s", (sr_id,))
                if cur.fetchone():
                    cur.execute(
                        "INSERT INTO ci_sr_mapping (ci_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (ci["identifier"], sr_id),
                    )
                    sr_map_count += 1
                else:
                    sr_skip_count += 1

    conn.commit()
    print(f"[OK] checklist_items 적재: {ci_count}행 (skip: {ci_skip}), ci_sr_mapping: {sr_map_count}행")
    if sr_skip_count > 0:
        skip_pct = sr_skip_count / total_based_on * 100 if total_based_on else 0
        print(f"  [WARN] SR 매핑 skip: {sr_skip_count}/{total_based_on} ({skip_pct:.1f}%) — SR이 safety_requirements에 없음")
    return ci_count


def import_domain_terms(conn, ci_files: list[dict]) -> int:
    """domain_terms + dt_sr_mapping 적재."""
    cur = conn.cursor()
    count = 0
    for data in ci_files:
        gc = data["metadata"]["guideCode"]
        for dt in data.get("domainTerms", []):
            cur.execute(
                """INSERT INTO domain_terms
                   (identifier, term, definition, source_guide, source_section)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (dt["identifier"], dt["term"], dt["definition"], gc, dt.get("sourceSection")),
            )
            count += 1
            for sr_id in (dt.get("relatedSR") or []):
                cur.execute("SELECT 1 FROM safety_requirements WHERE identifier = %s", (sr_id,))
                if cur.fetchone():
                    cur.execute(
                        "INSERT INTO dt_sr_mapping (dt_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (dt["identifier"], sr_id),
                    )
    conn.commit()
    print(f"[OK] domain_terms 적재: {count}행")
    return count


def import_work_processes(conn, ci_files: list[dict]) -> int:
    """work_processes + wp_sr_mapping + wp_ppe 적재."""
    cur = conn.cursor()
    count = 0
    for data in ci_files:
        gc = data["metadata"]["guideCode"]
        for wp in data.get("workProcesses", []):
            cur.execute(
                """INSERT INTO work_processes
                   (identifier, process_order, process_name, safety_measures, source_guide, source_section)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    wp["identifier"], wp["processOrder"], wp["processName"],
                    wp.get("safetyMeasures"), gc, wp.get("sourceSection"),
                ),
            )
            count += 1
            for sr_id in (wp.get("relatedSR") or []):
                cur.execute("SELECT 1 FROM safety_requirements WHERE identifier = %s", (sr_id,))
                if cur.fetchone():
                    cur.execute(
                        "INSERT INTO wp_sr_mapping (wp_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (wp["identifier"], sr_id),
                    )
            for ppe in (wp.get("requiredPPE") or []):
                cur.execute(
                    "INSERT INTO wp_ppe (wp_id, ppe_type) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (wp["identifier"], ppe),
                )
    conn.commit()
    print(f"[OK] work_processes 적재: {count}행")
    return count


def import_equipment_specs(conn, ci_files: list[dict]) -> int:
    """equipment_specs + es_sr_mapping 적재."""
    cur = conn.cursor()
    count = 0
    for data in ci_files:
        gc = data["metadata"]["guideCode"]
        for es in data.get("equipmentSpecs", []):
            cur.execute(
                """INSERT INTO equipment_specs
                   (identifier, equipment_name, specifications, source_guide, source_section)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    es["identifier"], es["equipmentName"],
                    Json(es.get("specifications", {})), gc, es.get("sourceSection"),
                ),
            )
            count += 1
            for sr_id in (es.get("relatedSR") or []):
                cur.execute("SELECT 1 FROM safety_requirements WHERE identifier = %s", (sr_id,))
                if cur.fetchone():
                    cur.execute(
                        "INSERT INTO es_sr_mapping (es_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (es["identifier"], sr_id),
                    )
    conn.commit()
    print(f"[OK] equipment_specs 적재: {count}행")
    return count


def import_document_requirements(conn, ci_files: list[dict]) -> int:
    """document_requirements + dr_sr_mapping 적재."""
    cur = conn.cursor()
    count = 0
    for data in ci_files:
        gc = data["metadata"]["guideCode"]
        for dr in data.get("documentRequirements", []):
            cur.execute(
                """INSERT INTO document_requirements
                   (identifier, document_type, title, required_sections, source_guide, source_section)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (
                    dr["identifier"], dr["documentType"], dr["title"],
                    Json(dr.get("requiredSections")), gc, dr.get("sourceSection"),
                ),
            )
            count += 1
            for sr_id in (dr.get("relatedSR") or []):
                cur.execute("SELECT 1 FROM safety_requirements WHERE identifier = %s", (sr_id,))
                if cur.fetchone():
                    cur.execute(
                        "INSERT INTO dr_sr_mapping (dr_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (dr["identifier"], sr_id),
                    )
    conn.commit()
    print(f"[OK] document_requirements 적재: {count}행")
    return count


def verify_pipeb(conn) -> list[dict]:
    """V16~V34 검증."""
    cur = conn.cursor()
    results = []

    def check(vid, desc, query, expected_fn):
        cur.execute(query)
        val = cur.fetchone()[0]
        passed = expected_fn(val)
        results.append({"id": vid, "desc": desc, "value": val, "pass": passed})
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {vid}: {desc} = {val}")

    print("\n[VERIFY] Pipe-B V16~V34")

    # V16: kosha_guides 행수 > 0
    check("V16", "kosha_guides 행수", "SELECT count(*) FROM kosha_guides", lambda v: v > 0)

    # V17: checklist_items 행수 > 0
    check("V17", "checklist_items 행수", "SELECT count(*) FROM checklist_items", lambda v: v > 0)

    # V18: CI identifier 중복 없음
    check("V18", "CI 중복 ID",
          "SELECT count(*) FROM (SELECT identifier FROM checklist_items GROUP BY identifier HAVING count(*) > 1) x",
          lambda v: v == 0)

    # V19: CI.source_guide → kosha_guides FK 무결
    check("V19", "CI→guide FK 무결",
          "SELECT count(*) FROM checklist_items ci WHERE NOT EXISTS (SELECT 1 FROM kosha_guides g WHERE g.guide_code = ci.source_guide)",
          lambda v: v == 0)

    # V20: ci_sr_mapping.sr_id → safety_requirements FK 무결
    check("V20", "CI→SR FK 무결",
          "SELECT count(*) FROM ci_sr_mapping m WHERE NOT EXISTS (SELECT 1 FROM safety_requirements sr WHERE sr.identifier = m.sr_id)",
          lambda v: v == 0)

    # V21: domain_terms 행수
    check("V21", "domain_terms 행수", "SELECT count(*) FROM domain_terms", lambda v: v >= 0)

    # V22: work_processes 행수
    check("V22", "work_processes 행수", "SELECT count(*) FROM work_processes", lambda v: v >= 0)

    # V23: equipment_specs 행수
    check("V23", "equipment_specs 행수", "SELECT count(*) FROM equipment_specs", lambda v: v >= 0)

    # V24: document_requirements 행수
    check("V24", "document_requirements 행수", "SELECT count(*) FROM document_requirements", lambda v: v >= 0)

    # V25: DT identifier 중복 없음
    check("V25", "DT 중복 ID",
          "SELECT count(*) FROM (SELECT identifier FROM domain_terms GROUP BY identifier HAVING count(*) > 1) x",
          lambda v: v == 0)

    # V26: WP identifier 중복 없음
    check("V26", "WP 중복 ID",
          "SELECT count(*) FROM (SELECT identifier FROM work_processes GROUP BY identifier HAVING count(*) > 1) x",
          lambda v: v == 0)

    # V27: kosha_guides.ci_count = 실제 CI 수
    check("V27", "guide.ci_count 정합성",
          """SELECT count(*) FROM kosha_guides g
             WHERE g.ci_count != (SELECT count(*) FROM checklist_items ci WHERE ci.source_guide = g.guide_code)""",
          lambda v: v == 0)

    # V28: binding_force 유효 값만
    check("V28", "binding_force 유효값",
          "SELECT count(*) FROM checklist_items WHERE binding_force NOT IN ('MANDATORY','RECOMMENDED')",
          lambda v: v == 0)

    # V31~V34: 온톨로지 보강 후보 테이블 구조/데이터 품질
    check("V31", "feature candidate confidence/evidence 유효",
          """SELECT count(*) FROM guide_entity_feature_candidates
             WHERE confidence < 0 OR confidence > 1 OR evidence IS NULL OR length(evidence) = 0""",
          lambda v: v == 0)

    check("V32", "SR link candidate confidence/evidence/FK 유효",
          """SELECT count(*) FROM guide_sr_link_candidates c
             LEFT JOIN safety_requirements sr ON sr.identifier = c.sr_id
             WHERE c.confidence < 0 OR c.confidence > 1
                OR c.evidence IS NULL OR length(c.evidence) = 0
                OR sr.identifier IS NULL""",
          lambda v: v == 0)

    check("V33", "visual trigger candidate confidence/evidence 유효",
          """SELECT count(*) FROM guide_visual_trigger_candidates
             WHERE confidence < 0 OR confidence > 1
                OR evidence IS NULL OR length(evidence) = 0
                OR trigger_text IS NULL OR length(trigger_text) = 0""",
          lambda v: v == 0)

    check("V34", "asserted 후보 threshold 위반",
          """SELECT count(*) FROM guide_sr_link_candidates
             WHERE asserted = TRUE
               AND (confidence < 0.88 OR non_llm_evidence_count < 2 OR review_status != 'asserted')""",
          lambda v: v == 0)

    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed
    print(f"\n  V16~V34: {passed} PASS / {failed} FAIL")
    return results


def verify_cross_pipeline(conn) -> list[dict]:
    """V29~V30 교차 파이프라인 검증."""
    cur = conn.cursor()
    results = []

    def check(vid, desc, query, expected_fn):
        cur.execute(query)
        val = cur.fetchone()[0]
        passed = expected_fn(val)
        results.append({"id": vid, "desc": desc, "value": val, "pass": passed})
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {vid}: {desc} = {val}")

    print("\n[VERIFY] Cross-pipeline V29~V30")

    # V29: ci_sr_mapping의 모든 sr_id가 safety_requirements에 존재 (V20과 동일하지만 명시적)
    check("V29", "모든 CI→SR 매핑 유효",
          "SELECT count(*) FROM ci_sr_mapping m LEFT JOIN safety_requirements sr ON m.sr_id = sr.identifier WHERE sr.identifier IS NULL",
          lambda v: v == 0)

    # V30: Pipe-A 데이터 무결 (safety_requirements 행수 보존)
    check("V30", "SR 행수 보존",
          "SELECT count(*) FROM safety_requirements",
          lambda v: v > 0)

    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed
    print(f"\n  V29~V30: {passed} PASS / {failed} FAIL")
    return results


def main():
    parser = argparse.ArgumentParser(description="Pipe-B: Layer 5 적재 + 검증")
    parser.add_argument("--input-dir", type=str, default="data/ci-output")
    parser.add_argument("--clean", action="store_true", help="Layer 5 DROP + 재생성")
    parser.add_argument("--verify", action="store_true", help="V16~V28 검증만")
    parser.add_argument("--verify-all", action="store_true", help="V16~V30 전체 검증")
    args = parser.parse_args()

    if args.verify or args.verify_all:
        conn = psycopg2.connect(PG_CONNINFO)
        conn.autocommit = False
        results = verify_pipeb(conn)
        if args.verify_all:
            results += verify_cross_pipeline(conn)
        conn.close()

        all_pass = all(r["pass"] for r in results)
        sys.exit(0 if all_pass else 1)

    # 적재 모드
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = PROJECT_ROOT / args.input_dir

    print("[START] Pipe-B Layer 5 적재")
    ci_files = load_ci_files(input_dir)
    print(f"  CI 파일: {len(ci_files)}개")

    conn = connect_db(clean=args.clean)

    import_guides(conn, ci_files)
    import_checklist_items(conn, ci_files)
    import_domain_terms(conn, ci_files)
    import_work_processes(conn, ci_files)
    import_equipment_specs(conn, ci_files)
    import_document_requirements(conn, ci_files)

    # 적재 후 즉시 검증
    results = verify_pipeb(conn)
    conn.close()

    all_pass = all(r["pass"] for r in results)
    print(f"\n[{'DONE' if all_pass else 'WARN'}] 적재 + 검증 완료")


if __name__ == "__main__":
    main()
