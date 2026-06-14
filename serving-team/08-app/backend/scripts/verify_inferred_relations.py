#!/usr/bin/env python3
"""Track A ② 게이트 — sr_inferred_relations PG가 현재 리즈너 emit과 동기인지 검증.

검사(불일치 시 exit 1):
  1) 최신 completed materialization_run(rule_set='reasoning-slice R-1/R-2')의
     source_ttl_sha256 == 현재 kosha-inferred-relations.ttl sha256
     → 재-emit 후 재-import 누락(drift) 차단.
  2) PG sr_inferred_relations(rule_id R-1/R-2) 행 수 == 그 run.triple_count
     → 적재 일관성.
  3) exemptedBy 행 수 > 0, 모든 행 run_id NOT NULL, FK orphan 0
     → 추론이 실제로 서빙 PG에 하중을 싣는지.

make phase-g5-verify (consistency-gate와 무관, PG만 필요).
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
INFERRED_TTL = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology" / "kosha-inferred-relations.ttl"
RULE_SET = "reasoning-slice R-1/R-2"
# import_sr_inferred_relations_to_pg.py와 동일해야 함 — PROV Activity는 drift 해시에서 제외.
PROV_ACTIVITY = "https://cashtoss.info/ontology/prov/run/inferred-relations-emit"


def _relations_sha256(path: Path) -> str:
    """추론 관계 트리플만의 content hash (PROV Activity 제외).

    import open_run과 동일 정의 — prov:startedAtTime(emit마다 변동)을 빼서 재-emit이
    거짓 drift FAIL을 내지 않게 한다. 관계 변화만 sha 변경.
    """
    from rdflib import Graph, URIRef

    g = Graph()
    g.parse(str(path), format="turtle")
    act = URIRef(PROV_ACTIVITY)
    triples = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in g if s != act)
    return hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL 미설정", file=sys.stderr)
        return 2
    if not INFERRED_TTL.exists():
        print(f"ERROR: {INFERRED_TTL.name} 없음 — `make reasoning-emit` 먼저", file=sys.stderr)
        return 2

    ttl_sha = _relations_sha256(INFERRED_TTL)
    e = create_engine(url)
    fails: list[str] = []
    with e.connect() as c:
        run = c.execute(text(
            "SELECT run_id, source_ttl_sha256, triple_count FROM materialization_runs "
            "WHERE rule_set = :rs AND status = 'completed' ORDER BY run_id DESC LIMIT 1"
        ), {"rs": RULE_SET}).first()
        if run is None:
            print(f"FAIL: completed run 없음 (rule_set={RULE_SET}) — `make phase-g5-import ARGS=--apply` 필요")
            return 1
        run_id, run_sha, run_tc = run

        n_total = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations WHERE rule_id IN ('R-1','R-2')"
        )).scalar() or 0
        n_exempt = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations WHERE rel_type='exemptedBy'"
        )).scalar() or 0
        n_co = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations WHERE rel_type='coApplicable'"
        )).scalar() or 0
        n_distinct_sr = c.execute(text(
            "SELECT count(distinct sr_id) FROM sr_inferred_relations"
        )).scalar() or 0
        n_null_run = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations WHERE run_id IS NULL"
        )).scalar() or 0
        n_orphan = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations s "
            "LEFT JOIN safety_requirements r ON s.sr_id = r.identifier WHERE r.identifier IS NULL"
        )).scalar() or 0

    print(f"run #{run_id}: triple_count={run_tc} sha={run_sha[:12]}")
    print(f"PG: total={n_total} exemptedBy={n_exempt} coApplicable={n_co} distinct_sr={n_distinct_sr}")
    print(f"TTL sha={ttl_sha[:12]} | run_id NULL={n_null_run} | FK orphan={n_orphan}")

    if run_sha != ttl_sha:
        fails.append(f"sha256 불일치 (PG run {run_sha[:12]} != TTL {ttl_sha[:12]}) — 재-emit 후 phase-g5-import 누락?")
    if n_total != run_tc:
        fails.append(f"행 수({n_total}) != run.triple_count({run_tc})")
    if n_exempt == 0:
        fails.append("exemptedBy 0건 — 추론이 PG에 적재되지 않음")
    if n_null_run > 0:
        fails.append(f"run_id NULL {n_null_run}건 — PROV 누락")
    if n_orphan > 0:
        fails.append(f"FK orphan {n_orphan}건 — sr_id가 safety_requirements에 없음")

    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nPASS — sr_inferred_relations가 현재 리즈너 emit과 동기")
    return 0


if __name__ == "__main__":
    sys.exit(main())
