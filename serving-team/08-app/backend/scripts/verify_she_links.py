#!/usr/bin/env python3
"""SHE→SR 링크 무결성 게이트 — CAT-1 (F17). `make verify-she-links`.

서빙 status(approved_auto/approved_manual)인 SHE 패턴 중 she_sr_mapping이
0건인 orphan을 검출한다. SHE→SR은 법령 근거 연결의 1차 관문 — orphan은
"매칭은 되지만 법적 근거를 하나도 제시하지 못하는" 패턴이므로 서빙 부적격.
orphan > 0 이면 exit 1.

복구 선택지: (a) 근거 SR을 찾아 source_sr_ids 채움 + she_sr_mapping insert,
(b) status='pending_review' 강등(서빙 제외, 재적재 시 ON CONFLICT가 status
보존하므로 강등 유지).
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


def main() -> int:
    session = SessionLocal()
    try:
        rows = session.execute(text("""
            SELECT c.she_id, c.source_model
            FROM she_catalog c
            LEFT JOIN she_sr_mapping m ON m.she_id = c.she_id
            WHERE c.status IN ('approved_auto', 'approved_manual')
            GROUP BY c.she_id, c.source_model
            HAVING COUNT(m.sr_id) = 0
            ORDER BY c.she_id
        """)).all()
        total = session.execute(text("""
            SELECT COUNT(*) FROM she_catalog
            WHERE status IN ('approved_auto', 'approved_manual')
        """)).scalar()
    finally:
        session.close()

    if rows:
        print(f"verify-she-links FAIL — 서빙 SHE {total}건 중 SR 링크 0건(orphan) {len(rows)}건:")
        for she_id, source_model in rows[:20]:
            print(f"  ✗ {she_id}  ({source_model})")
        if len(rows) > 20:
            print(f"  … 외 {len(rows) - 20}건")
        print("\n복구: source_sr_ids 채움(+she_sr_mapping) 또는 status='pending_review' 강등.")
        return 1

    print(f"verify-she-links PASS — 서빙 SHE {total}건 전부 SR 링크 ≥1 (orphan 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
