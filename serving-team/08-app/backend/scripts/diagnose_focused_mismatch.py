#!/usr/bin/env python3
"""focused 오정렬 근본원인 추적: case → expected_features → SHE 매칭(패턴 facets) → focused SR(facets/조) 체인 출력.

어디서 어긋나는지(잘못된 facet? 잘못된 SHE 패턴 매칭? SHE→SR 큐레이션?)를 눈으로 본다.
사용: python scripts/diagnose_focused_mismatch.py [CASE_ID ...]
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import replay_synthetic_observations as R  # noqa: E402
from sqlalchemy import text  # noqa: E402


async def diagnose(db, case: dict) -> None:
    resp = await R.analysis_pipeline.run(
        db=db,
        run_input=R.AnalysisRunInput(
            result=R.build_fake_result(case), analysis_type="text",
            input_preview=f"diag:{case['case_id']}", full_description=case.get("photo_description", ""),
            declared_industry_text=case.get("industry_context"), persist=False,
        ),
    )
    print("=" * 90)
    print("CASE", case["case_id"], "| work_context:", case.get("work_context"))
    print("scene:", (case.get("photo_description") or "")[:95])
    print("expected_features:", json.dumps(case.get("expected_features") or {}, ensure_ascii=False))

    sms = getattr(resp, "situation_matches", None) or []
    print(f"\n매칭된 SHE 패턴 {len(sms)}개 (상위 8):")
    for m in sms[:8]:
        pid = getattr(m, "pattern_id", None)
        row = db.execute(text("SELECT name, features FROM she_catalog WHERE she_id=:i"), {"i": pid}).fetchone()
        feats = json.dumps(row[1], ensure_ascii=False) if (row and row[1]) else "?"
        print(f"  - {pid} status={getattr(m, 'status', None)} score={round(getattr(m, 'score', 0) or 0, 3)}")
        print(f"      matched_features(왜 매칭): {getattr(m, 'matched_features', None)}")
        print(f"      SHE name: {row[0] if row else '?'}")
        print(f"      SHE facets: {feats}")
        print(f"      applies_sr_ids: {getattr(m, 'applies_sr_ids', None)}")

    foc = []
    for m in sms:
        for s in getattr(m, "applies_sr_ids", None) or []:
            if s not in foc:
                foc.append(s)
    print(f"\nfocused SR {len(foc)}개 → facets / 조:")
    for s in foc[:12]:
        r = db.execute(text(
            "SELECT title, accident_types_canonical, work_contexts_canonical, hazardous_agents_canonical "
            "FROM safety_requirements WHERE identifier=:i"), {"i": s}).fetchone()
        art = db.execute(text("SELECT article_code FROM sr_article_mapping WHERE sr_id=:i"), {"i": s}).fetchone()
        if r:
            print(f"  {s} [{art[0] if art else '?'}] {r[0][:28]} | acc={r[1]} wc={r[2]} agt={r[3]}")
        else:
            print(f"  {s} (없음)")


async def main() -> None:
    ids = sys.argv[1:] or ["SYN-0053", "SYN-V2-0042"]
    cases = {c["case_id"]: c for c in R.load_synthetic_cases() if c.get("case_id") in ids}
    db = R.SessionLocal()
    try:
        for i in ids:
            if i in cases:
                await diagnose(db, cases[i])
            else:
                print(f"[case {i} 없음]")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
