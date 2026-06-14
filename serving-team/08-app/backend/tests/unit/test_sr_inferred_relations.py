"""Track A ② 단위 테스트 — sr_inferred_relations PG 서빙 (Fuseki 비의존).

리즈너 산출(R-1 exemptedBy / R-2 coApplicable)이 PG로 물질화돼 서빙 엔드포인트가
Fuseki 없이 동일 계약을 반환하는지 양성 증명. PG/데이터 미가용 시 SKIP(게이트는
make phase-g5-verify가 담당).

알려진 사실(현재 ABox): SR-MACHINE-018은 의무 NS(NS-RULE103-0/103-4)가
NS-RULE103-1, NS-RULE103-5에 의해 면제됨 → exemptions 2건.

실행:
  PYTHONIOENCODING=utf-8 python serving-team/08-app/backend/tests/unit/test_sr_inferred_relations.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.database import SessionLocal  # noqa: E402
from app.services import sr_inferred_service as svc  # noqa: E402


def _data_available() -> bool:
    try:
        with SessionLocal() as db:
            from sqlalchemy import text
            n = db.execute(text(
                "SELECT count(*) FROM sr_inferred_relations WHERE rel_type='exemptedBy'"
            )).scalar()
            return bool(n and n > 0)
    except Exception as e:  # PG down / table absent
        print(f"  (PG/데이터 미가용: {type(e).__name__}) — SKIP")
        return False


def test_get_exemptions_machine018():
    """R-1 exemptedBy: SR-MACHINE-018 → NS-RULE103-1, NS-RULE103-5 (조건 텍스트 포함)."""
    with SessionLocal() as db:
        ex = svc.get_exemptions(db, "SR-MACHINE-018")
    ns_ids = sorted(e["exempt_ns_id"] for e in ex)
    assert ns_ids == ["NS-RULE103-1", "NS-RULE103-5"], ns_ids
    assert all(e["article_code"] == "제103조" for e in ex), ex
    assert all(e["condition"] for e in ex), "면제 조건 텍스트 비어있음"


def test_get_co_applicable_type():
    """R-2 coApplicable: 현재 0건이지만 list 계약 유지(서빙 shape 불변)."""
    with SessionLocal() as db:
        co = svc.get_co_applicable(db, "SR-MACHINE-018")
    assert isinstance(co, list)


def test_article_inferred_graph_carries_exemptedBy():
    """inferred-graph(제103조): article+sr 노드 + exemptedBy 엣지(추론 관계 렌더 보존)."""
    with SessionLocal() as db:
        g = svc.get_article_inferred_graph(db, "제103조")
    groups = {n["group"] for n in g["nodes"]}
    edge_types = {e["edge_type"] for e in g["edges"]}
    assert "article" in groups and "sr" in groups, groups
    assert "exemptedBy" in edge_types, edge_types


def test_enrich_pg_backed_source():
    """enrich: Fuseki 미사용(source=pg_inferred) + 면제 보강 존재."""
    with SessionLocal() as db:
        enr = svc.enrich_sr_results(db, [{"identifier": "SR-MACHINE-018"}])
    assert enr["source"] == "pg_inferred", enr["source"]
    assert len(enr["exemptions"]) == 2, enr["exemptions"]


def test_endpoint_exemptions_contract():
    """엔드포인트 계약: GET /sparql/sr/{id}/exemptions == {sr_id, exemptions[], count}."""
    from app.api.v1.sparql import get_sr_exemptions
    with SessionLocal() as db:
        resp = asyncio.run(get_sr_exemptions("SR-MACHINE-018", db))
    assert resp["sr_id"] == "SR-MACHINE-018"
    assert resp["count"] == 2
    assert {"exempt_ns_id", "article_code", "condition"} <= set(resp["exemptions"][0].keys())


def _run():
    if not _data_available():
        print("SKIP — sr_inferred_relations 미적재 (make phase-g5-import ARGS=--apply 필요)")
        return 0
    tests = [
        test_get_exemptions_machine018,
        test_get_co_applicable_type,
        test_article_inferred_graph_carries_exemptedBy,
        test_enrich_pg_backed_source,
        test_endpoint_exemptions_contract,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILED'} ({len(tests)} tests)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
