"""PG-backed 추론 관계 조회 — sr_inferred_relations (Fuseki 대체).

Track A ②: 리즈너(R-1 exemptedBy / R-2 coApplicable) 산출의 PG 물질화를 서빙이 직접
소비. 기존 sparql.py가 Fuseki(sparql_client)로 받던 q2/q4/q7을 PG SELECT로 대체 —
Fuseki 장애/재분류와 무관하게 ms 응답(F8 "추론이 서빙의 하중을 받는다").

출처 테이블: sr_inferred_relations (import_sr_inferred_relations_to_pg.py 적재).
고위험(R-3 동치)은 penalty_rule_index.severity_score >= N 으로 SQL 재현.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_co_applicable(db: Session, sr_id: str) -> list[dict]:
    """R-2 coApplicable — 같은 조문 기반 관련 SR. (현재 0건; 양방향 물질화)"""
    rows = db.execute(text(
        "SELECT target_id, attrs->>'title' AS title, attrs->>'article_code' AS article_code "
        "FROM sr_inferred_relations "
        "WHERE sr_id = :sr AND rel_type = 'coApplicable' ORDER BY target_id"
    ), {"sr": sr_id}).mappings().all()
    return [
        {"sr_id": r["target_id"], "title": r["title"] or "", "article_code": r["article_code"] or ""}
        for r in rows
    ]


def get_exemptions(db: Session, sr_id: str) -> list[dict]:
    """R-1 exemptedBy — SR이 파생된 의무 NS를 면제하는 NS 목록."""
    rows = db.execute(text(
        "SELECT target_id, attrs->>'article_code' AS article_code, attrs->>'condition' AS condition "
        "FROM sr_inferred_relations "
        "WHERE sr_id = :sr AND rel_type = 'exemptedBy' ORDER BY target_id"
    ), {"sr": sr_id}).mappings().all()
    return [
        {"exempt_ns_id": r["target_id"], "article_code": r["article_code"], "condition": r["condition"]}
        for r in rows
    ]


def get_high_severity(db: Session, sr_ids: list[str], min_severity: int = 5) -> list[dict]:
    """R-3 HighSeverityPenalty 동치 — penalty_rule_index.severity_score >= N 을 SQL로 재현.

    (리즈너 class-membership ?x a pen:HighSeverityPenalty 는 severityScore>=5 와 동치이므로
     PG에서 reasoner 없이 같은 결과. sr_ids 교집합만 반환.)
    """
    if not sr_ids:
        return []
    rows = db.execute(text(
        "SELECT DISTINCT sr_id, severity_score, penalty_description FROM penalty_rule_index "
        "WHERE sr_id = ANY(:ids) AND severity_score >= :ms ORDER BY severity_score DESC"
    ), {"ids": list(sr_ids), "ms": min_severity}).mappings().all()
    return [
        {"sr_id": r["sr_id"], "severity": r["severity_score"], "penalty": r["penalty_description"] or ""}
        for r in rows
    ]


def get_article_inferred_graph(db: Session, article_code: str, limit: int = 100) -> dict:
    """조문별 추론 그래프 (vis.js nodes/edges) — q7_article_inferred_graph PG 동치.

    SR(조문) → NS(derivedFromNS) + 면제(exemptedBy) + 동시적용(coApplicable) 엣지.
    Fuseki q7과 달리 SR-중심(exemptedBy: sr→exemptNs)으로 재구성 — 동일 edge_type/그룹이라
    프론트 OntologyGraph 렌더 동일.
    """
    nodes: dict[str, dict] = {}
    edge_set: set[tuple[str, str, str]] = set()

    art_key = f"art_{article_code}"
    nodes[art_key] = {"id": art_key, "label": article_code, "group": "article"}

    sr_ids = db.execute(text(
        "SELECT sr_id FROM sr_article_mapping WHERE article_code = :a LIMIT :lim"
    ), {"a": article_code, "lim": limit}).scalars().all()
    sr_ids = list(sr_ids)

    if sr_ids:
        for sid in sr_ids:
            nodes[f"sr_{sid}"] = {"id": f"sr_{sid}", "label": sid, "group": "sr"}

        # derivedFromNS edges + norm nodes
        ns_rows = db.execute(text(
            "SELECT sr_id, ns_id FROM sr_ns_mapping WHERE sr_id = ANY(:ids)"
        ), {"ids": sr_ids}).all()
        for sid, ns in ns_rows:
            nodes[f"ns_{ns}"] = {"id": f"ns_{ns}", "label": ns, "group": "norm"}
            edge_set.add((f"sr_{sid}", f"ns_{ns}", "derivedFromNS"))

        # 추론 엣지: exemptedBy(면제 NS) + coApplicable(상대 SR)
        ir = db.execute(text(
            "SELECT sr_id, rel_type, target_id FROM sr_inferred_relations WHERE sr_id = ANY(:ids)"
        ), {"ids": sr_ids}).all()
        for sid, rel, target in ir:
            if rel == "exemptedBy":
                nodes[f"exempt_{target}"] = {"id": f"exempt_{target}", "label": target, "group": "exemption"}
                edge_set.add((f"sr_{sid}", f"exempt_{target}", "exemptedBy"))
            elif rel == "coApplicable":
                nodes.setdefault(f"sr_{target}", {"id": f"sr_{target}", "label": target, "group": "inferred_sr"})
                edge_set.add((f"sr_{sid}", f"sr_{target}", "coApplicable"))

    edges = [{"from": f, "to": t, "edge_type": et} for f, t, et in edge_set]
    return {"article_code": article_code, "nodes": list(nodes.values()), "edges": edges}


def enrich_sr_results(
    db: Session,
    sr_results: list[dict],
    min_severity: int = 5,
    per_sr_limit: int = 3,
) -> dict:
    """PG SR 결과를 추론 관계로 보강 (구 enrich_sr_with_sparql의 Fuseki 비의존 대체).

    co_applicable(R-2) + exemptions(R-1) + high_severity(R-3 동치) 를 sr_inferred_relations /
    penalty_rule_index 에서 조회해 번들. Fuseki 미사용.
    """
    sr_ids = [sr["identifier"] for sr in sr_results if sr.get("identifier")]
    enrichment = {
        "source": "pg_inferred",
        "co_applicable_srs": [],
        "exemptions": [],
        "high_severity_srs": [],
    }
    sr_id_set = set(sr_ids)
    for sr_id in sr_ids[:per_sr_limit]:
        for co in get_co_applicable(db, sr_id):
            if co["sr_id"] not in sr_id_set:
                enrichment["co_applicable_srs"].append({**co, "discovered_via": sr_id})
        for ex in get_exemptions(db, sr_id):
            enrichment["exemptions"].append({**ex, "applies_to_sr": sr_id})
    enrichment["high_severity_srs"] = get_high_severity(db, sr_ids, min_severity=min_severity)
    return enrichment
