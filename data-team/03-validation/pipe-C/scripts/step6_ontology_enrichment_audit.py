#!/usr/bin/env python3
"""Audit 1,038-guide ontology enrichment coverage.

This is intentionally read-only. It reports whether the serving graph has
enough evidence-bearing links to support the intended flow:
risk feature -> SHE/SR -> Guide/WorkProcess/ChecklistItem.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2


SCRIPT_DIR = Path(__file__).resolve().parent
PIPE_C_ROOT = SCRIPT_DIR.parent
DEFAULT_REPORT = PIPE_C_ROOT / "data" / "ontology-enrichment-audit-report.json"
PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()[0] or 0)


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (table,))
    return cur.fetchone()[0] is not None


def mapping_summary(cur, table: str, entity_col: str) -> dict[str, int]:
    if not table_exists(cur, table):
        return {"rows": 0, "distinct_entities": 0, "distinct_sr": 0}
    cur.execute(f"SELECT count(*), count(DISTINCT {entity_col}), count(DISTINCT sr_id) FROM {table}")
    rows, entities, srs = cur.fetchone()
    return {"rows": int(rows or 0), "distinct_entities": int(entities or 0), "distinct_sr": int(srs or 0)}


def candidate_summary(cur, table: str) -> dict[str, int]:
    if not table_exists(cur, table):
        return {"rows": 0, "asserted": 0, "serving_candidates": 0, "missing_evidence": 0}
    asserted_expr = "asserted = TRUE" if table == "guide_sr_link_candidates" else "review_status = 'asserted'"
    cur.execute(f"""
        SELECT
          count(*),
          count(*) FILTER (WHERE {asserted_expr}),
          count(*) FILTER (WHERE confidence >= 0.65),
          count(*) FILTER (WHERE evidence IS NULL OR length(evidence) = 0)
        FROM {table}
    """)
    rows, asserted, serving, missing = cur.fetchone()
    return {
        "rows": int(rows or 0),
        "asserted": int(asserted or 0),
        "serving_candidates": int(serving or 0),
        "missing_evidence": int(missing or 0),
    }


def build_report(cur) -> dict[str, Any]:
    totals = {
        "guides": scalar(cur, "SELECT count(*) FROM kosha_guides"),
        "safety_requirements": scalar(cur, "SELECT count(*) FROM safety_requirements"),
        "checklist_items": scalar(cur, "SELECT count(*) FROM checklist_items"),
        "work_processes": scalar(cur, "SELECT count(*) FROM work_processes"),
        "equipment_specs": scalar(cur, "SELECT count(*) FROM equipment_specs"),
        "document_requirements": scalar(cur, "SELECT count(*) FROM document_requirements"),
        "domain_terms": scalar(cur, "SELECT count(*) FROM domain_terms"),
    }

    mappings = {
        "ci_sr_mapping": mapping_summary(cur, "ci_sr_mapping", "ci_id"),
        "wp_sr_mapping": mapping_summary(cur, "wp_sr_mapping", "wp_id"),
        "es_sr_mapping": mapping_summary(cur, "es_sr_mapping", "es_id"),
        "dr_sr_mapping": mapping_summary(cur, "dr_sr_mapping", "dr_id"),
        "dt_sr_mapping": mapping_summary(cur, "dt_sr_mapping", "dt_id"),
    }

    cur.execute("""
        SELECT count(DISTINCT ci.source_guide)
        FROM checklist_items ci
        JOIN ci_sr_mapping m ON m.ci_id = ci.identifier
    """)
    guides_with_ci_sr = int(cur.fetchone()[0] or 0)
    cur.execute("""
        SELECT count(DISTINCT wp.source_guide)
        FROM work_processes wp
        JOIN wp_sr_mapping m ON m.wp_id = wp.identifier
    """)
    guides_with_wp_sr = int(cur.fetchone()[0] or 0)

    facet_coverage = {}
    for name, table, cols in [
        ("checklist_items", "checklist_items", ["accident_types", "hazardous_agents", "work_contexts"]),
        ("work_processes", "work_processes", ["accident_types", "work_contexts"]),
        ("equipment_specs", "equipment_specs", ["work_contexts"]),
        ("domain_terms", "domain_terms", ["hazardous_agents", "work_contexts"]),
    ]:
        where = " OR ".join(f"{col} IS NOT NULL" for col in cols)
        facet_coverage[name] = {
            "total": scalar(cur, f"SELECT count(*) FROM {table}"),
            "with_any_axis": scalar(cur, f"SELECT count(*) FROM {table} WHERE {where}"),
        }

    candidates = {
        "guide_entity_feature_candidates": candidate_summary(cur, "guide_entity_feature_candidates"),
        "guide_sr_link_candidates": candidate_summary(cur, "guide_sr_link_candidates"),
        "guide_visual_trigger_candidates": candidate_summary(cur, "guide_visual_trigger_candidates"),
    }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "mappings": mappings,
        "guideCoverage": {
            "with_ci_sr": guides_with_ci_sr,
            "without_ci_sr": totals["guides"] - guides_with_ci_sr,
            "with_wp_sr": guides_with_wp_sr,
            "without_wp_sr": totals["guides"] - guides_with_wp_sr,
        },
        "facetCoverage": facet_coverage,
        "candidateCoverage": candidates,
        "baselines": {
            "ci_sr_distinct_sr_before_enrichment": 130,
            "ci_sr_rows_before_enrichment": 10676,
            "ci_feature_coverage_before_enrichment": 43465,
            "wp_feature_coverage_before_enrichment": 4606,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ontology enrichment coverage audit")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--print", action="store_true", help="print report JSON")
    args = parser.parse_args()

    conn = psycopg2.connect(PG_CONNINFO)
    try:
        cur = conn.cursor()
        report = build_report(cur)
    finally:
        conn.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.print:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] wrote {args.output}")


if __name__ == "__main__":
    main()
