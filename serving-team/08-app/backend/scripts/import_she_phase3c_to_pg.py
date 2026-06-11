#!/usr/bin/env python3
"""Phase 3C — Import she_pattern_proposals.json into PG she_catalog.

Sets status='approved_auto' so SHE matcher will use these patterns immediately.

모드 (CAT-1/CAT-2, F16/F17):
- 기본: ON CONFLICT(she_id) DO NOTHING — 기존행 절대 무갱신. she_sr_mapping은
  이번 run에서 실제 insert된 she_id 한정으로만 파생.
- --reconcile: 소스(proposals.json)를 정본으로 기존행 동기화. 단 사람 큐레이션
  컬럼(status/reviewed_by/superseded_by/notes)은 보존. she_sr_mapping은 소스
  기준 prune+insert하되, she_sr_exclusions.json(사람 검토로 제거된 쌍)은
  소스가 회귀해도 절대 재삽입하지 않는다.
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
EXCLUSIONS = PROJECT_ROOT / "data-team/05-enrichment/runtime-artifacts/she_sr_exclusions.json"


def load_exclusions() -> set[tuple[str, str]]:
    """사람 검토로 제거된 (she_id, sr_id) 쌍 — reconcile이 절대 재삽입 금지."""
    if not EXCLUSIONS.exists():
        return set()
    data = json.loads(EXCLUSIONS.read_text(encoding="utf-8"))
    return {(e["she_id"], e["sr_id"]) for e in data.get("exclusions", [])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--status", default="approved_auto", choices=["draft", "approved_auto"])
    p.add_argument("--reconcile", action="store_true",
                   help="소스 정본 동기화: 기존행 UPDATE(사람 큐레이션 컬럼 보존) + "
                        "she_sr_mapping prune/insert (exclusions 존중)")
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
    inserted, kept, updated, errors = 0, 0, 0, 0
    inserted_ids: list[str] = []
    err_samples = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # CAT-2(F16): reconcile = 소스 정본 동기화. 기존행을 EXCLUDED 값으로 UPDATE하되
    # 사람 큐레이션 컬럼(status/reviewed_by/superseded_by/notes/approved_at)은 건드리지
    # 않는다 — orphan 강등(pending_review)·supersede 결정이 재적재로 뒤집히지 않게.
    # (xmax = 0) = PG upsert에서 '실제 INSERT였나' 판별 관용구.
    if args.reconcile:
        upsert_sql = """
            INSERT INTO she_catalog
              (she_id, name, name_pattern, features, rationale, status, broadness_score,
               source_model, source_prompt_hash, source_sr_ids, created_at)
            VALUES
              (:she_id, :name, :name_pattern, CAST(:features AS jsonb), :rationale,
               :status, :broadness, :source_model, :source_prompt_hash,
               CAST(:source_sr_ids AS jsonb), :created_at)
            ON CONFLICT (she_id) DO UPDATE SET
              name = EXCLUDED.name,
              name_pattern = EXCLUDED.name_pattern,
              features = EXCLUDED.features,
              rationale = EXCLUDED.rationale,
              broadness_score = EXCLUDED.broadness_score,
              source_model = EXCLUDED.source_model,
              source_prompt_hash = EXCLUDED.source_prompt_hash,
              source_sr_ids = EXCLUDED.source_sr_ids
            RETURNING she_id, (xmax = 0) AS was_insert
        """
    else:
        upsert_sql = """
            INSERT INTO she_catalog
              (she_id, name, name_pattern, features, rationale, status, broadness_score,
               source_model, source_prompt_hash, source_sr_ids, created_at)
            VALUES
              (:she_id, :name, :name_pattern, CAST(:features AS jsonb), :rationale,
               :status, :broadness, :source_model, :source_prompt_hash,
               CAST(:source_sr_ids AS jsonb), :created_at)
            ON CONFLICT (she_id) DO NOTHING
            RETURNING she_id, TRUE AS was_insert
        """
    try:
        for row in patterns:
            try:
                # CAT-1(F16/F17): RETURNING으로 '실제 insert'와 'conflict로 보존(kept)'을
                # 구분 — 이전 audit은 둘을 합쳐 inserted로 집계해 stale 재적재를 성공처럼
                # 보이게 했다. 기본 모드는 기존행을 절대 갱신하지 않는다(검토 반영분 보존;
                # 갱신은 reconcile 모드(CAT-2) 전용).
                res = session.execute(text(upsert_sql), {
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
                returned = res.first()
                if returned is None:
                    kept += 1
                elif returned.was_insert:
                    inserted += 1
                    inserted_ids.append(returned.she_id)
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                if len(err_samples) < 5:
                    err_samples.append({"she_id": row.get("she_id"), "error": str(exc)[:200]})
                session.rollback()
        # Populate she_sr_mapping from inserted patterns' source_sr_ids
        # (she_matcher uses she_sr_mapping for SR lookup, not catalog.source_sr_ids)
        # CAT-1(F16/F17): 기본 모드는 이번 run에서 실제 insert된 she_id 한정 — 이전의
        # source_model 전역 재스캔은 (a) :74 기본값('phase3c/direct-llm')과 필터
        # 리터럴('…-gpt-4.1')의 불일치로 일부 행이 영원히 SR 0이 되고, (b) 사람
        # 검토로 제거한 SR 링크를 재적재 때마다 부활시켰다.
        exclusions = load_exclusions()
        sr_link_count, sr_pruned, excluded_skipped = 0, 0, 0
        if args.reconcile:
            # CAT-2(F16): 소스 기준 desired 집합(exclusions 차감) → prune + insert.
            # prune은 source='phase3c' 링크에 한정 — 다른 출처(inversion 등) 링크 보존.
            for row in patterns:
                sid = row["she_id"]
                desired: list[str] = []
                for sr in row.get("source_sr_ids") or []:
                    if (sid, sr) in exclusions:
                        excluded_skipped += 1
                        continue
                    desired.append(sr)
                pruned = session.execute(text("""
                    DELETE FROM she_sr_mapping
                    WHERE she_id = :sid AND source = 'phase3c'
                      AND NOT (sr_id = ANY(CAST(:desired AS text[])))
                    RETURNING sr_id
                """), {"sid": sid, "desired": desired})
                sr_pruned += sum(1 for _ in pruned)
                for sr in desired:
                    ins = session.execute(text("""
                        INSERT INTO she_sr_mapping (she_id, sr_id, confidence, source)
                        VALUES (:sid, :sr, 0.75, 'phase3c')
                        ON CONFLICT DO NOTHING
                        RETURNING she_id
                    """), {"sid": sid, "sr": sr})
                    sr_link_count += sum(1 for _ in ins)
            print(f"  she_sr_mapping reconciled: +{sr_link_count} / -{sr_pruned} "
                  f"(exclusion 차단 {excluded_skipped}건)")
        elif inserted_ids:
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
        else:
            print(f"  she_sr_mapping populated: 0 rows (이번 run insert 0건 한정)")
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
        "mode": "reconcile" if args.reconcile else "insert-only",
        "source_file": str(PROPOSALS.relative_to(PROJECT_ROOT)),
        "total_proposals": len(patterns),
        "inserted": inserted,
        "kept_on_conflict": kept,
        "updated": updated,
        "sr_links_inserted": sr_link_count,
        "sr_links_pruned": sr_pruned,
        "sr_exclusions_applied": excluded_skipped,
        "errors": errors,
        "error_samples": err_samples,
        "status_assigned": args.status,
    }
    AUDIT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresult:")
    print(f"  inserted: {inserted} / kept on conflict (기존행 무갱신): {kept} / updated(reconcile): {updated}")
    print(f"  errors: {errors}")
    if err_samples:
        print(f"  error sample: {err_samples[0]}")
    print(f"  audit: {AUDIT.relative_to(PROJECT_ROOT)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
