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
    """coApplicable: list 계약 유지(서빙 shape 불변)."""
    with SessionLocal() as db:
        co = svc.get_co_applicable(db, "SR-MACHINE-018")
    assert isinstance(co, list)


def _has_coapplicable() -> bool:
    from sqlalchemy import text
    with SessionLocal() as db:
        n = db.execute(text("SELECT count(*) FROM sr_inferred_relations WHERE rel_type='coApplicable'")).scalar()
        return bool(n and n > 0)


def test_kr2_coapplicable_target_attrs():
    """K-R2 적재 시: 양방향 행의 attrs가 각자 TARGET SR을 기술(검토 수정 #4 실데이터 검증).

    같은 Chapter SR 쌍 (A,B)에서 get_co_applicable(A)의 B 항목 title은 B의 제목,
    get_co_applicable(B)의 A 항목 title은 A의 제목이어야 한다(역방향 오기재 없음).
    K-R2 미적재(coApplicable 0) 환경에선 SKIP.
    """
    if not _has_coapplicable():
        return  # K-R2 미적재 — skip
    with SessionLocal() as db:
        a_co = {x["sr_id"]: x for x in svc.get_co_applicable(db, "SR-CARGO-001")}
        b_co = {x["sr_id"]: x for x in svc.get_co_applicable(db, "SR-CARGO-002")}
    assert "SR-CARGO-002" in a_co, "SR-CARGO-001은 같은 Chapter SR-CARGO-002와 coApplicable이어야"
    assert "SR-CARGO-001" in b_co, "대칭(양방향) 보장"
    # 역방향 attrs 정확성: 각 항목 title은 그 항목(target)의 제목.
    assert a_co["SR-CARGO-002"]["article_code"] == "제388조", a_co["SR-CARGO-002"]
    assert b_co["SR-CARGO-001"]["article_code"] == "제387조", b_co["SR-CARGO-001"]
    assert a_co["SR-CARGO-002"]["title"] != b_co["SR-CARGO-001"]["title"], "역방향이 같은 제목이면 오기재"


def _has_dependson() -> bool:
    from sqlalchemy import text
    with SessionLocal() as db:
        n = db.execute(text("SELECT count(*) FROM sr_inferred_relations WHERE rel_type='dependsOn'")).scalar()
        return bool(n and n > 0)


def test_kr4_dependson_and_endpoint():
    """K-R4 적재 시: get_depends_on이 같은 Hazard SR 반환 + 전용 엔드포인트 계약.

    K-R4 미적재(dependsOn 0) 환경에선 SKIP. inferred-graph에는 dependsOn이 없어야(노이즈 제외).
    """
    if not _has_dependson():
        return  # K-R4 미적재 — skip
    from app.api.v1.sparql import get_sr_depends_on
    with SessionLocal() as db:
        dep = svc.get_depends_on(db, "SR-CARGO-001")
        assert len(dep) > 0, "SR-CARGO-001은 같은 Hazard SR과 dependsOn이어야"
        assert {"sr_id", "title", "article_code"} <= set(dep[0].keys())
        resp = asyncio.run(get_sr_depends_on("SR-CARGO-001", db))
        assert resp["count"] == len(dep) and resp["sr_id"] == "SR-CARGO-001"
        # inferred-graph는 dependsOn 제외(전용 엔드포인트로만 소비)
        g = svc.get_article_inferred_graph(db, "제103조")
        assert "dependsOn" not in {e["edge_type"] for e in g["edges"]}


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
        test_kr2_coapplicable_target_attrs,
        test_kr4_dependson_and_endpoint,
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
