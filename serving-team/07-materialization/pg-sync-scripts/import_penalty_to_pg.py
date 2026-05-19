#!/usr/bin/env python3
"""Phase G Sprint G.3 — Sync penalty rule index from kosha-instances.ttl to PG.

Source: ontology-team/06-reasoning/ontology/kosha-instances.ttl (TTL ABox)
Target: PG penalty_rule_index (Ontology: penalty:PenaltyRule + sr/article 매핑)

Logic:
  1. Parse instances.ttl with rdflib
  2. For each sr:derivedFromNS, find ns_uri
  3. For each ns_uri, find pen:hasPenaltyRule → pr_uri
  4. Extract pr metadata (sanction type, severity, basis_text 등)
  5. Insert (sr_id, penalty_rule_id, ...) into PG with UPSERT

기존 hazard_rule_engine._load_penalty_index와 동일 로직, 결과를 PG에 저장.

사용:
  python import_penalty_to_pg.py                # dry-run
  python import_penalty_to_pg.py --apply
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BACKEND_DIR = REPO_ROOT / "serving-team" / "08-app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import PgPenaltyRuleIndex  # noqa: E402


DEFAULT_INSTANCES_TTL = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology" / "kosha-instances.ttl"


def _local_id(uri) -> str | None:
    if uri is None:
        return None
    s = str(uri)
    return s.rsplit("#", 1)[-1] if "#" in s else s.rsplit("/", 1)[-1]


def extract_penalty_rules(ttl_path: Path) -> list[dict]:
    """Parse TTL, return list of row dicts for PG insert."""
    from rdflib import Graph, URIRef, RDF
    from rdflib.namespace import Namespace

    SR = Namespace("https://cashtoss.info/ontology/sr#")
    PEN = Namespace("https://cashtoss.info/ontology/penalty#")

    print(f"Parsing {ttl_path.name} ({ttl_path.stat().st_size / 1024 / 1024:.1f} MB)...")
    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    print(f"  triples: {len(g)}")

    rows: list[dict] = []
    for sr_uri, ns_uri in g.subject_objects(SR.derivedFromNS):
        sr_id = _local_id(sr_uri)
        if not sr_id:
            continue
        for pr_uri in g.objects(ns_uri, PEN.hasPenaltyRule):
            pr_id = _local_id(pr_uri)
            if not pr_id:
                continue

            sanction_uri = g.value(pr_uri, PEN.hasSanction)
            condition_uri = g.value(pr_uri, PEN.hasCondition)

            subject_role = _local_id(g.value(condition_uri, PEN.requiresSubjectRole)) if condition_uri else None
            accident_outcome = _local_id(g.value(condition_uri, PEN.requiresAccidentOutcome)) if condition_uri else None

            sanction_type = None
            if sanction_uri:
                for type_uri in g.objects(sanction_uri, RDF.type):
                    sanction_type = _local_id(type_uri)
                    if sanction_type and sanction_type != "PenaltyRule":  # skip self-type
                        break

            severity = g.value(sanction_uri, PEN.severityScore) if sanction_uri else None
            try:
                severity_score = int(str(severity)) if severity is not None else None
            except (ValueError, TypeError):
                severity_score = None

            penalty_desc = g.value(sanction_uri, PEN.penaltyDescription) if sanction_uri else None

            rows.append({
                "sr_id": sr_id,
                "penalty_rule_id": pr_id,
                "article_code": _local_id(g.value(pr_uri, PEN.violatedArticle)),
                "sanction_type": sanction_type,
                "penalty_description": str(penalty_desc) if penalty_desc else None,
                "severity_score": severity_score,
                "subject_role": subject_role,
                "accident_outcome": accident_outcome,
                "violated_norm_id": _local_id(g.value(pr_uri, PEN.violatedNorm)),
                "violated_article_id": _local_id(g.value(pr_uri, PEN.violatedArticle)),
                "delegated_from_article_id": _local_id(g.value(pr_uri, PEN.delegatedFrom)),
                "penalty_article_id": _local_id(g.value(pr_uri, PEN.penaltyArticle)),
                "basis_text": str(g.value(pr_uri, PEN.penaltyBasisText) or "") or None,
            })

    return rows


def upsert_rows(rows: list[dict]) -> int:
    if not rows:
        return 0

    # Deduplicate by (sr_id, penalty_rule_id)
    dedup: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r["sr_id"], r["penalty_rule_id"])
        dedup[key] = r
    rows = list(dedup.values())

    table = PgPenaltyRuleIndex.__table__
    total = 0
    BATCH = 500
    with engine.begin() as conn:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            stmt = pg_insert(table).values(chunk)
            update_columns = {
                c.name: getattr(stmt.excluded, c.name)
                for c in table.columns
                if c.name not in {"id", "created_at", "updated_at"}
            }
            update_columns["updated_at"] = func.now()
            stmt = stmt.on_conflict_do_update(
                index_elements=["sr_id", "penalty_rule_id"],
                set_=update_columns,
            )
            result = conn.execute(stmt)
            total += result.rowcount or 0
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instances-ttl", type=Path, default=DEFAULT_INSTANCES_TTL)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.instances_ttl.exists():
        print(f"ERROR: instances TTL not found: {args.instances_ttl}", file=sys.stderr)
        return 1

    start = time.time()
    rows = extract_penalty_rules(args.instances_ttl)
    elapsed = time.time() - start
    print(f"\nExtracted {len(rows)} (sr_id, penalty_rule_id) rows in {elapsed:.1f}s")

    if not rows:
        print("Nothing to import.")
        return 0

    # Sample first 3
    print("Sample (first 3):")
    for r in rows[:3]:
        print(f"  {r['sr_id']:15s} → {r['penalty_rule_id']:25s} type={r['sanction_type']!r:30s} severity={r['severity_score']}")

    # Distribution
    from collections import Counter
    types = Counter(r["sanction_type"] for r in rows)
    print(f"Sanction type distribution: {dict(types)}")

    # Pre-import
    with SessionLocal() as s:
        n_before = s.query(func.count(PgPenaltyRuleIndex.id)).scalar() or 0
    print(f"\nPG rows before: {n_before}")

    if not args.apply:
        print(f"\n[DRY-RUN] {len(rows)} rows would be UPSERTed.")
        return 0

    print(f"\n--- Applying UPSERT ---")
    rowcount = upsert_rows(rows)
    elapsed = time.time() - start
    print(f"UPSERT rowcount: {rowcount} ({elapsed:.1f}s)")

    with SessionLocal() as s:
        n_after = s.query(func.count(PgPenaltyRuleIndex.id)).scalar() or 0
    print(f"PG rows after: {n_after}")

    print(f"\nStatus: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
