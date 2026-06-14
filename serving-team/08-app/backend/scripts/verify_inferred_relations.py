#!/usr/bin/env python3
"""Track A ② 게이트 — sr_inferred_relations PG가 현재 리즈너 emit과 동기인지 검증.

rule_set별로 (strict R-1/R-2, chapter K-R2) 최신 completed run을 기준으로 검사
(불일치 시 exit 1):
  1) run.source_ttl_sha256 == 현재 TTL의 관계 content-hash(PROV 제외)
     → 재-emit 후 재-import 누락(drift) 차단.
  2) PG에서 run_id = 그 run인 행 수 == run.triple_count → 적재 일관성.
  3) 행 수 > 0, FK orphan 0 → 추론이 실제로 서빙 PG에 하중을 싣는지.

사용:
  python verify_inferred_relations.py                                  # strict (R-1/R-2)
  python verify_inferred_relations.py --rule-set "reasoning-slice K-R2 chapter-coApplicable" \\
      --ttl ontology-team/06-reasoning/ontology/kosha-coapplicable-chapter.ttl
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
ONT = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
DEFAULT_TTL = ONT / "kosha-inferred-relations.ttl"
DEFAULT_RULE_SET = "reasoning-slice R-1/R-2"
# import_sr_inferred_relations_to_pg.py와 동일해야 함 — PROV run Activity는 drift 해시에서 제외.
PROV_RUN_PREFIX = "https://cashtoss.info/ontology/prov/run/"


def _relations_sha256(path: Path) -> str:
    """추론 관계 트리플만의 content hash (PROV run Activity 제외). import open_run과 동일 정의."""
    from rdflib import Graph

    g = Graph()
    g.parse(str(path), format="turtle")
    triples = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in g
                     if not str(s).startswith(PROV_RUN_PREFIX))
    return hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule-set", default=DEFAULT_RULE_SET)
    ap.add_argument("--ttl", type=Path, default=DEFAULT_TTL)
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL 미설정", file=sys.stderr)
        return 2
    if not args.ttl.exists():
        print(f"ERROR: {args.ttl} 없음 — emit 먼저", file=sys.stderr)
        return 2

    ttl_sha = _relations_sha256(args.ttl)
    e = create_engine(url)
    fails: list[str] = []
    with e.connect() as c:
        run = c.execute(text(
            "SELECT run_id, source_ttl_sha256, triple_count FROM materialization_runs "
            "WHERE rule_set = :rs AND status = 'completed' ORDER BY run_id DESC LIMIT 1"
        ), {"rs": args.rule_set}).first()
        if run is None:
            print(f"FAIL: completed run 없음 (rule_set={args.rule_set}) — import --apply 필요")
            return 1
        run_id, run_sha, run_tc = run

        n_rows = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations WHERE run_id = :rid"
        ), {"rid": run_id}).scalar() or 0
        n_orphan = c.execute(text(
            "SELECT count(*) FROM sr_inferred_relations s "
            "LEFT JOIN safety_requirements r ON s.sr_id = r.identifier "
            "WHERE s.run_id = :rid AND r.identifier IS NULL"
        ), {"rid": run_id}).scalar() or 0

    print(f"rule_set: {args.rule_set}")
    print(f"run #{run_id}: triple_count={run_tc} sha={run_sha[:12]}")
    print(f"PG rows(run_id={run_id})={n_rows} | TTL sha={ttl_sha[:12]} | FK orphan={n_orphan}")

    if run_sha != ttl_sha:
        fails.append(f"sha256 불일치 (PG run {run_sha[:12]} != TTL {ttl_sha[:12]}) — 재-emit 후 import 누락?")
    if n_rows != run_tc:
        fails.append(f"행 수({n_rows}) != run.triple_count({run_tc})")
    if n_rows == 0:
        fails.append("0행 — 추론이 PG에 적재되지 않음")
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
