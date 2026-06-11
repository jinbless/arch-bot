#!/usr/bin/env python3
"""Phase 3C — Import she_pattern_proposals.json into PG she_catalog.

Sets status='approved_auto' so SHE matcher will use these patterns immediately.
Conflicts on she_id: SKIP (preserve existing).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
# walk up to find repo root (data-team/05-enrichment/eval-data marker)
def _find_repo_root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return a
    raise RuntimeError("repo root not found")
PROJECT_ROOT = _find_repo_root()
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


PROPOSALS = PROJECT_ROOT / "data-team/05-enrichment/runtime-artifacts/she_pattern_proposals.json"
AUDIT = PROJECT_ROOT / "data-team/05-enrichment/runtime-artifacts/phase3c_import_audit.json"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status", default="approved_auto", choices=["draft", "approved_auto"])
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True

    data = json.loads(PROPOSALS.read_text(encoding="utf-8"))
    patterns = data.get("patterns") or []
    print(f"loaded {len(patterns)} proposals from {PROPOSALS.name}")

    if args.dry_run:
        print(f"DRY: would upsert {len(patterns)} rows with status='{args.status}'")
        return 0

    session = SessionLocal()
    inserted, kept, errors = 0, 0, 0
    inserted_ids: list[str] = []
    err_samples = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        for row in patterns:
            try:
                # CAT-1(F16/F17): RETURNING으로 '실제 insert'와 'conflict로 보존(kept)'을
                # 구분 — 이전 audit은 둘을 합쳐 inserted로 집계해 stale 재적재를 성공처럼
                # 보이게 했다. 기존행은 절대 갱신하지 않는다(검토 반영분 보존; 갱신은
                # reconcile 모드(CAT-2) 전용).
                res = session.execute(text("""
                    INSERT INTO she_catalog
                      (she_id, name, name_pattern, features, rationale, status, broadness_score,
                       source_model, source_prompt_hash, source_sr_ids, created_at)
                    VALUES
                      (:she_id, :name, :name_pattern, CAST(:features AS jsonb), :rationale,
                       :status, :broadness, :source_model, :source_prompt_hash,
                       CAST(:source_sr_ids AS jsonb), :created_at)
                    ON CONFLICT (she_id) DO NOTHING
                    RETURNING she_id
                """), {
                    "she_id": row["she_id"],
                    "name": row["name"],
                    "name_pattern": row.get("name_pattern", "")[:200],
                    "features": json.dumps(row["features"], ensure_ascii=False),
                    "rationale": row.get("rationale", ""),
                    "status": args.status,
                    "broadness": row.get("broadness_score", 0.7),
                    "source_model": row.get("source_model", "phase3c/direct-llm"),
                    "source_prompt_hash": row.get("source_prompt_hash", "")[:32],
                    "source_sr_ids": json.dumps(row.get("source_sr_ids") or [], ensure_ascii=False),
                    "created_at": now,
                })
                returned = res.scalar()
                if returned:
                    inserted += 1
                    inserted_ids.append(returned)
                else:
                    kept += 1
            except Exception as exc:
                errors += 1
                if len(err_samples) < 5:
                    err_samples.append({"she_id": row.get("she_id"), "error": str(exc)[:200]})
                session.rollback()
        # Populate she_sr_mapping from inserted patterns' source_sr_ids
        # (she_matcher uses she_sr_mapping for SR lookup, not catalog.source_sr_ids)
        # CAT-1(F16/F17): 이번 run에서 실제 insert된 she_id 한정 — 이전의
        # source_model 전역 재스캔은 (a) :74 기본값('phase3c/direct-llm')과 필터
        # 리터럴('…-gpt-4.1')의 불일치로 일부 행이 영원히 SR 0이 되고, (b) 사람
        # 검토로 제거한 SR 링크를 재적재 때마다 부활시켰다.
        sr_link_count = 0
        if inserted_ids:
            from sqlalchemy import bindparam  # noqa: PLC0415
            stmt = text("""
                INSERT INTO she_sr_mapping (she_id, sr_id, confidence, source)
                SELECT she_id, jsonb_array_elements_text(source_sr_ids), 0.75, 'phase3c'
                FROM she_catalog
                WHERE she_id IN :ids
                ON CONFLICT DO NOTHING
                RETURNING she_id
            """).bindparams(bindparam("ids", expanding=True))
            sr_link_result = session.execute(stmt, {"ids": inserted_ids})
            sr_link_count = sum(1 for _ in sr_link_result)
        print(f"  she_sr_mapping populated: {sr_link_count} rows (이번 run insert {len(inserted_ids)}건 한정)")
        session.commit()

        # CAT-1 종료 게이트: 서빙 status인데 SR 링크 0건(orphan) — 법령 근거 없는
        # SHE가 서빙되는 것을 import 시점에 차단. (단독 실행: make verify-she-links)
        orphans = session.execute(text("""
            SELECT c.she_id FROM she_catalog c
            LEFT JOIN she_sr_mapping m ON m.she_id = c.she_id
            WHERE c.status IN ('approved_auto', 'approved_manual')
            GROUP BY c.she_id HAVING COUNT(m.sr_id) = 0
        """)).scalars().all()
        if orphans:
            print(f"  ✗ ORPHAN GATE FAIL: 서빙 SHE 중 SR 링크 0건 {len(orphans)}건 — {orphans[:5]}")
            print(f"    → source_sr_ids 채움 또는 status='pending_review' 강등 후 재실행")
            errors += 1
    finally:
        session.close()

    summary = {
        "applied_at": now.isoformat() + "Z",
        "source_file": str(PROPOSALS.relative_to(PROJECT_ROOT)),
        "total_proposals": len(patterns),
        "inserted": inserted,
        "kept_on_conflict": kept,
        "errors": errors,
        "error_samples": err_samples,
        "status_assigned": args.status,
    }
    AUDIT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresult:")
    print(f"  inserted: {inserted} / kept on conflict (기존행 무갱신): {kept}")
    print(f"  errors: {errors}")
    if err_samples:
        print(f"  error sample: {err_samples[0]}")
    print(f"  audit: {AUDIT.relative_to(PROJECT_ROOT)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
