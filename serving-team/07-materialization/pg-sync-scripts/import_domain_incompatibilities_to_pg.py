#!/usr/bin/env python3
"""Phase G Sprint G.1 — Sync guide_domain_incompatibilities.json into PostgreSQL.

Source: data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json
Target: PG guide_domain_incompatibilities (Ontology: core:Incompatibility class)

기존 import_guide_usage_profiles_to_pg.py (484 lines, gold standard) 패턴 미러:
- pg_insert + on_conflict_do_update (idempotent UPSERT)
- collect_db_context / collect_after_counts / build_report
- dry-run / apply / filter level/source CLI

사용:
  python import_domain_incompatibilities_to_pg.py                   # dry-run
  python import_domain_incompatibilities_to_pg.py --apply           # 실제 적재
  python import_domain_incompatibilities_to_pg.py --apply --filter-level vetted
  python import_domain_incompatibilities_to_pg.py --report-json /tmp/g1-report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert


# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BACKEND_DIR = REPO_ROOT / "serving-team" / "08-app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import PgGuideDomainIncompatibility  # noqa: E402


DEFAULT_SOURCE = REPO_ROOT / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"
DEFAULT_REPORT_DIR = REPO_ROOT / "data-team/05-enrichment/runtime-artifacts"

ALLOWED_LEVELS = {"vetted", "candidate"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_source(path: Path) -> tuple[list[dict], dict]:
    """Load JSON. Return (incompatibilities list, meta)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("incompatibilities", []) or []
    meta = {k: v for k, v in data.items() if k != "incompatibilities"}
    return items, meta


def normalize_row(entry: dict) -> dict | None:
    """Convert source JSON entry → PG row dict. Return None if invalid."""
    if not entry.get("incompatible", False):
        return None
    domain_a = (entry.get("domain_a") or "").strip()
    domain_b = (entry.get("domain_b") or "").strip()
    level = (entry.get("level") or "candidate").strip()
    if not domain_a or not domain_b or domain_a == domain_b:
        return None
    if level not in ALLOWED_LEVELS:
        return None

    conf = entry.get("confidence")
    try:
        conf_val = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_val = None

    def _parse_ts(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    return {
        "domain_a": domain_a,
        "domain_b": domain_b,
        "level": level,
        "confidence": conf_val,
        "source": (entry.get("source") or "unknown").strip()[:50],
        "reason": (entry.get("reason") or "")[:2000] or None,
        "promoted_at": _parse_ts(entry.get("promoted_at")),
        "rollback_at": _parse_ts(entry.get("rollback_at")),
        "rollback_reason": (entry.get("rollback_reason") or "")[:500] or None,
    }


def upsert_rows(rows: list[dict]) -> int:
    """Insert or update rows in batches. Return rowcount sum.

    Uses PG ON CONFLICT (domain_a, domain_b, source) DO UPDATE.
    """
    if not rows:
        return 0
    table = PgGuideDomainIncompatibility.__table__
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
                index_elements=["domain_a", "domain_b", "source"],
                set_=update_columns,
            )
            result = conn.execute(stmt)
            total += result.rowcount or 0
    return total


def collect_db_context() -> dict:
    """Sample pre-import PG state."""
    with SessionLocal() as session:
        n_total = session.query(func.count(PgGuideDomainIncompatibility.id)).scalar() or 0
        n_vetted = session.query(func.count(PgGuideDomainIncompatibility.id)) \
            .filter(PgGuideDomainIncompatibility.level == "vetted").scalar() or 0
        n_candidate = session.query(func.count(PgGuideDomainIncompatibility.id)) \
            .filter(PgGuideDomainIncompatibility.level == "candidate").scalar() or 0
    return {
        "rows_before": int(n_total),
        "vetted_before": int(n_vetted),
        "candidate_before": int(n_candidate),
    }


def collect_after_counts() -> dict:
    """Sample post-import PG state."""
    with SessionLocal() as session:
        n_total = session.query(func.count(PgGuideDomainIncompatibility.id)).scalar() or 0
        n_vetted = session.query(func.count(PgGuideDomainIncompatibility.id)) \
            .filter(PgGuideDomainIncompatibility.level == "vetted").scalar() or 0
        n_candidate = session.query(func.count(PgGuideDomainIncompatibility.id)) \
            .filter(PgGuideDomainIncompatibility.level == "candidate").scalar() or 0
        # source distribution
        rows = session.execute(text(
            "SELECT source, COUNT(*) FROM guide_domain_incompatibilities GROUP BY source"
        )).fetchall()
        sources = {r[0]: r[1] for r in rows}
        # sample (top 5 by confidence within vetted)
        sample = session.execute(text(
            "SELECT domain_a, domain_b, level, confidence FROM guide_domain_incompatibilities "
            "WHERE level='vetted' ORDER BY confidence DESC NULLS LAST LIMIT 5"
        )).fetchall()
    return {
        "rows_after": int(n_total),
        "vetted_after": int(n_vetted),
        "candidate_after": int(n_candidate),
        "source_distribution": sources,
        "vetted_sample": [
            {"domain_a": r[0], "domain_b": r[1], "level": r[2],
             "confidence": float(r[3]) if r[3] is not None else None}
            for r in sample
        ],
    }


def build_report(
    args: argparse.Namespace,
    source_meta: dict,
    rows: list[dict],
    db_context_before: dict,
    db_context_after: dict | None,
    applied: bool,
    rowcount: int,
    elapsed_seconds: float,
) -> dict:
    """Build report dict (JSON-serializable)."""
    level_counts = Counter(r["level"] for r in rows)
    source_counts = Counter(r["source"] for r in rows)
    return {
        "generated_at": _now(),
        "source": str(args.source.relative_to(REPO_ROOT) if args.source.is_relative_to(REPO_ROOT) else args.source),
        "source_meta": {k: v for k, v in source_meta.items() if isinstance(v, (str, int, float, bool))},
        "filter_level": args.filter_level,
        "filter_source": args.filter_source,
        "rows_count": len(rows),
        "level_counts": dict(level_counts),
        "source_counts": dict(source_counts),
        "db_before": db_context_before,
        "db_after": db_context_after,
        "applied": applied,
        "rowcount_affected": rowcount,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "status": "PASS" if applied and rowcount > 0 else ("DRY_RUN" if not applied else "EMPTY"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                    help="source JSON (default: guide_domain_incompatibilities.json)")
    ap.add_argument("--apply", action="store_true",
                    help="실제 PG UPSERT 실행 (미지정 시 dry-run)")
    ap.add_argument("--filter-level", choices=("vetted", "candidate"), default=None,
                    help="특정 level만 적재 (기본: all)")
    ap.add_argument("--filter-source", default=None,
                    help="특정 source만 적재 (예: f32_axiom_miner)")
    ap.add_argument("--report-json", type=Path, default=None,
                    help="report JSON 출력 경로 (선택)")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    print(f"=== Phase G.1 Import — guide_domain_incompatibilities ===")
    print(f"Source: {args.source.name}")
    print(f"Mode:   {'APPLY' if args.apply else 'DRY-RUN'}")

    import time
    start = time.time()

    # Load + normalize
    items, source_meta = load_source(args.source)
    print(f"\nLoaded {len(items)} entries from source")

    rows: list[dict] = []
    skipped = 0
    for entry in items:
        row = normalize_row(entry)
        if row is None:
            skipped += 1
            continue
        if args.filter_level and row["level"] != args.filter_level:
            continue
        if args.filter_source and row["source"] != args.filter_source:
            continue
        rows.append(row)

    print(f"Normalized: {len(rows)} rows (skipped {skipped} invalid)")
    if args.filter_level or args.filter_source:
        print(f"After filters: {len(rows)} rows")

    # Deduplicate by (domain_a, domain_b, source) — PG unique constraint.
    # Keep the row with highest confidence (or last if equal).
    dedup: dict[tuple[str, str, str], dict] = {}
    for r in rows:
        key = (r["domain_a"], r["domain_b"], r["source"])
        prev = dedup.get(key)
        if prev is None:
            dedup[key] = r
        else:
            # Tie-break: vetted over candidate, then higher confidence, then later promoted_at
            prev_score = (1 if prev["level"] == "vetted" else 0, prev["confidence"] or 0)
            new_score = (1 if r["level"] == "vetted" else 0, r["confidence"] or 0)
            if new_score > prev_score:
                dedup[key] = r
    n_dedup_removed = len(rows) - len(dedup)
    if n_dedup_removed > 0:
        print(f"Deduplicated: removed {n_dedup_removed} duplicate (domain_a, domain_b, source) entries")
    rows = list(dedup.values())

    level_dist = Counter(r["level"] for r in rows)
    print(f"Level distribution: {dict(level_dist)}")
    source_dist = Counter(r["source"] for r in rows)
    print(f"Source distribution: {dict(source_dist)}")

    # Pre-import context
    print(f"\n--- DB state (before) ---")
    db_before = collect_db_context()
    print(f"Rows before: {db_before['rows_before']} (vetted={db_before['vetted_before']}, candidate={db_before['candidate_before']})")

    # Apply (or dry-run)
    if not args.apply:
        print(f"\n[DRY-RUN] {len(rows)} rows would be UPSERTed.")
        print(f"Re-run with --apply to commit.")
        report = build_report(args, source_meta, rows, db_before, None, False, 0, time.time() - start)
        if args.report_json:
            args.report_json.parent.mkdir(parents=True, exist_ok=True)
            args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            print(f"Report: {args.report_json}")
        return 0

    print(f"\n--- Applying UPSERT ---")
    rowcount = upsert_rows(rows)
    elapsed = time.time() - start
    print(f"UPSERT rowcount: {rowcount} ({elapsed:.1f}s)")

    # Post-import verification
    print(f"\n--- DB state (after) ---")
    db_after = collect_after_counts()
    print(f"Rows after: {db_after['rows_after']} (vetted={db_after['vetted_after']}, candidate={db_after['candidate_after']})")
    print(f"Source distribution: {db_after['source_distribution']}")
    if db_after["vetted_sample"]:
        print(f"Vetted sample (top 5 by confidence):")
        for s in db_after["vetted_sample"]:
            print(f"  {s['domain_a']:35s} x {s['domain_b']:35s} conf={s['confidence']}")

    # Verification: count consistency
    if db_after["rows_after"] != len(rows):
        print(f"\nWARN: row count mismatch — DB={db_after['rows_after']}, source={len(rows)}")
        print(f"      (이전 데이터 잔존 또는 conflict resolution 결과 가능)")

    report = build_report(args, source_meta, rows, db_before, db_after, True, rowcount, elapsed)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"\nReport: {args.report_json}")

    print(f"\nStatus: {report['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
