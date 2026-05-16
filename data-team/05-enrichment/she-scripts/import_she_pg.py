"""Phase 2.3 — SHE catalog → PG 적재.

Inputs:
  - she-approved-v1.jsonl (validator pass, status='approved_auto')
  - sr-registry.json (linkedCI/linkedGuides enrichment용)

Outputs (PG kosha database):
  - she_catalog (SHE 본체)
  - she_sr_mapping (SHE × SR)
  - she_ci_mapping (SHE × CI, sr-registry의 linkedCI 자동 follow)

Usage:
  PYTHONUTF8=1 python koshaontology/scripts/she/import_she_pg.py \
      --schema koshaontology/db/she/schema_she.sql \
      --input koshaontology/data/she/she-approved-v1.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SR_REGISTRY = ROOT / "koshaontology" / "pipe-C" / "data" / "sr-registry.json"
DEFAULT_SCHEMA = ROOT / "koshaontology" / "db" / "she" / "schema_she.sql"
DEFAULT_INPUT = ROOT / "koshaontology" / "data" / "she" / "she-approved-v1.jsonl"

PG_DSN = "dbname=kosha user=kosha password=1229 host=localhost port=5432"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--sr-registry", type=Path, default=DEFAULT_SR_REGISTRY)
    parser.add_argument("--clean", action="store_true",
                        help="기존 SHE 테이블 DROP 후 재생성")
    args = parser.parse_args()

    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # 1. Schema 적용
    if args.clean:
        print("[STEP] DROP existing SHE tables")
        cur.execute("""
            DROP TABLE IF EXISTS she_ci_mapping CASCADE;
            DROP TABLE IF EXISTS she_sr_mapping CASCADE;
            DROP VIEW IF EXISTS v_she_active CASCADE;
            DROP TABLE IF EXISTS she_catalog CASCADE;
        """)

    print(f"[STEP] Apply schema: {args.schema}")
    schema_sql = args.schema.read_text(encoding="utf-8")
    cur.execute(schema_sql)
    conn.commit()

    # 2. SR linkedCI 인덱스 (sr_id → linkedCI[]) — sr-registry에서
    print(f"[STEP] Load sr-registry for linkedCI enrichment")
    registry_data = json.loads(args.sr_registry.read_text(encoding="utf-8"))
    sr_to_cis: dict[str, list[str]] = {}
    for sr in registry_data.get("registry", []):
        pb = sr.get("pipeB") or {}
        sr_to_cis[sr["identifier"]] = pb.get("linkedCI") or []
    print(f"[INFO]   {len(sr_to_cis)} SRs with linkedCI map")

    # 3. SHE rows 적재
    print(f"[STEP] Load SHE from: {args.input}")
    she_rows = []
    with args.input.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            she_rows.append(json.loads(line))
    print(f"[INFO]   {len(she_rows)} SHE rows")

    # 4. Bulk insert: she_catalog
    print(f"[STEP] Insert into she_catalog")
    catalog_rows = []
    for s in she_rows:
        catalog_rows.append((
            s["she_id"],
            s.get("name", ""),
            s.get("name_pattern"),
            json.dumps(s["features"], ensure_ascii=False),
            json.dumps(s.get("visual_triggers", []), ensure_ascii=False),
            s.get("rationale"),
            s.get("status", "approved_auto"),
            s.get("broadness_score"),
            s.get("source_model"),
            s.get("source_prompt_hash"),
            json.dumps(s.get("source_sr_ids", [])),
            None,  # valid_from
            None,  # valid_until
            None,  # superseded_by
        ))
    psycopg2.extras.execute_values(cur, """
        INSERT INTO she_catalog (
            she_id, name, name_pattern, features, visual_triggers, rationale,
            status, broadness_score, source_model, source_prompt_hash, source_sr_ids,
            valid_from, valid_until, superseded_by
        ) VALUES %s
        ON CONFLICT (she_id) DO UPDATE SET
            name = EXCLUDED.name,
            features = EXCLUDED.features,
            visual_triggers = EXCLUDED.visual_triggers,
            broadness_score = EXCLUDED.broadness_score
    """, catalog_rows)
    print(f"[INFO]   {cur.rowcount} catalog rows inserted/updated")

    # 5. Bulk insert: she_sr_mapping
    print(f"[STEP] Insert into she_sr_mapping")
    sr_mapping_rows = []
    ci_mapping_rows = []
    seen_ci: set[tuple] = set()  # (she_id, ci_id) dedup
    for s in she_rows:
        for sr_id in s.get("source_sr_ids", []):
            sr_mapping_rows.append((s["she_id"], sr_id, 1.0, "inversion"))
            # CI enrichment from sr-registry
            for ci_id in sr_to_cis.get(sr_id, []):
                key = (s["she_id"], ci_id)
                if key not in seen_ci:
                    seen_ci.add(key)
                    ci_mapping_rows.append((s["she_id"], ci_id, 0.7, "inferred_from_sr"))

    if sr_mapping_rows:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO she_sr_mapping (she_id, sr_id, confidence, source) VALUES %s
            ON CONFLICT (she_id, sr_id) DO NOTHING
        """, sr_mapping_rows)
        print(f"[INFO]   {len(sr_mapping_rows)} SR mappings inserted")

    if ci_mapping_rows:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO she_ci_mapping (she_id, ci_id, confidence, source) VALUES %s
            ON CONFLICT (she_id, ci_id) DO NOTHING
        """, ci_mapping_rows)
        print(f"[INFO]   {len(ci_mapping_rows)} CI mappings inserted")

    conn.commit()

    # 6. 검증 통계
    cur.execute("SELECT COUNT(*), AVG(broadness_score) FROM she_catalog WHERE status = 'approved_auto'")
    n_app, avg_broad = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM v_she_active")
    n_active, = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM she_sr_mapping")
    n_sr, = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM she_ci_mapping")
    n_ci, = cur.fetchone()

    # work_context 분포
    cur.execute("""
        SELECT features->>'work_context' AS wc, COUNT(*) FROM she_catalog
        WHERE status = 'approved_auto'
        GROUP BY wc ORDER BY COUNT(*) DESC LIMIT 20
    """)
    wc_dist = cur.fetchall()

    # orphan 검증
    cur.execute("""
        SELECT COUNT(*) FROM she_catalog c
        LEFT JOIN she_sr_mapping m ON c.she_id = m.she_id
        WHERE c.status = 'approved_auto' AND m.she_id IS NULL
    """)
    n_orphan, = cur.fetchone()

    print(f"\n[OK] Import complete")
    print(f"     approved SHE:        {n_app}")
    print(f"     active SHE (view):   {n_active}")
    print(f"     avg broadness:       {avg_broad:.3f}" if avg_broad else "     avg broadness: N/A")
    print(f"     SR mappings:         {n_sr}")
    print(f"     CI mappings:         {n_ci}")
    print(f"     orphan SHE (no SR):  {n_orphan}")

    print(f"\n[work_context distribution]:")
    for wc, n in wc_dist:
        print(f"  {wc:25s} {n:5d}")

    # Pilot 3 wc 검증
    cur.execute("""
        SELECT COUNT(*) FROM she_catalog
        WHERE status = 'approved_auto'
          AND features->>'work_context' IN ('SCAFFOLD', 'EXCAVATION', 'MACHINE')
    """)
    n_pilot, = cur.fetchone()
    print(f"\n[Pilot 3 wc] approved: {n_pilot}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
