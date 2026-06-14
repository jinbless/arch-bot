#!/usr/bin/env python3
"""Track A ② — 리즈너 산출(R-1 exemptedBy / R-2 coApplicable) → PG 물질화.

입력: ontology-team/06-reasoning/ontology/kosha-inferred-relations.ttl
        (emit_inferred_relations.py 산출 — inferred-only 추론 트리플)
      + kosha-instances.ttl (SR↔NS↔Article 확장에 필요한 ABox)
대상: sr_inferred_relations (SR-단위 비정규화) + materialization_runs (PROV-O 출처)

서빙 계약(q4_exemption_chain / q2_co_applicable_srs)과 동일 의미를 SPARQL SELECT로
재현해 SR-단위 행을 만든다 — 이 테이블이 Fuseki를 대체하는 서빙 소스가 된다.
  exemptedBy: 의무 NS가 면제 NS에 면제됨 → (sr, exemptNsId, article, condition)  현재 107행
  coApplicable: 같은 조문 SR 쌍(symmetric 양방향)                                현재 0행

run 1건마다 materialization_runs 행 생성(git rev + TTL sha256). 적재 행은 run_id로
행 단위 wasGeneratedBy 보존. --apply 없으면 dry-run(run 미생성).

사용:
  python import_sr_inferred_relations_to_pg.py            # dry-run
  python import_sr_inferred_relations_to_pg.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BACKEND_DIR = REPO_ROOT / "serving-team" / "08-app" / "backend"
ONT_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.models import PgMaterializationRun, PgSrInferredRelation  # noqa: E402

DEFAULT_INFERRED_TTL = ONT_DIR / "kosha-inferred-relations.ttl"
DEFAULT_INSTANCES_TTL = ONT_DIR / "kosha-instances.ttl"
RULE_SET = "reasoning-slice R-1/R-2"
IMPORTED_RULE_IDS = ("R-1", "R-2")
# emit_inferred_relations.add_prov_header의 run-level PROV Activity subject — drift 해시에서 제외.
PROV_ACTIVITY = "https://cashtoss.info/ontology/prov/run/inferred-relations-emit"

# 서빙 q4_exemption_chain 동치 — exemptedBy(R-1)를 SR 단위로 확장.
Q_EXEMPTED = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT ?srId ?exemptNsId ?exemptArt ?condition WHERE {
  ?sr a sr:SafetyRequirement ; core:identifier ?srId ; sr:derivedFromNS ?obligNs .
  ?obligNs law:hasModality core:Obligation ; core:exemptedBy ?exemptNs .
  ?exemptNs core:identifier ?exemptNsId .
  OPTIONAL { ?exemptNs law:hasSourceArticle ?ea . ?ea law:articleCode ?exemptArt . }
  OPTIONAL { ?exemptNs law:conditionText ?condition . }
}
"""

# 서빙 q2_co_applicable_srs 동치(영구화된 core:coApplicable 직접) — R-2를 SR 단위로.
# 양쪽 SR 메타(?co* + ?s*)를 모두 가져온다 — symmetric 역방향 행이 각자 target SR의
# title/article을 담도록(역방향에 ?co 메타 재사용하면 오기재).
Q_COAPPLICABLE = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
SELECT ?srId ?coSrId ?coTitle ?coArt ?srTitle ?srArt WHERE {
  ?s core:coApplicable ?co .
  ?s core:identifier ?srId .
  ?co core:identifier ?coSrId .
  OPTIONAL { ?co core:title ?coTitle . }
  OPTIONAL { ?co sr:derivedFromNS ?coNs . ?coNs law:hasSourceArticle ?ca . ?ca law:articleCode ?coArt . }
  OPTIONAL { ?s core:title ?srTitle . }
  OPTIONAL { ?s sr:derivedFromNS ?sNs . ?sNs law:hasSourceArticle ?sa . ?sa law:articleCode ?srArt . }
}
"""


def _relations_sha256(path: Path) -> str:
    """추론 관계 트리플만의 content hash (PROV Activity 제외) — drift 게이트용.

    raw 파일 해시는 prov:startedAtTime(emit마다 변동) 때문에 재-emit 시 거짓 drift를
    유발한다. 의미있는 관계(exemptedBy/coApplicable)만 정렬 N-Triples로 직렬화해 해시 →
    timestamp 무관, 관계 변화만 감지. verify_inferred_relations.py와 동일 정의여야 한다.
    """
    from rdflib import Graph, URIRef

    g = Graph()
    g.parse(str(path), format="turtle")
    act = URIRef(PROV_ACTIVITY)
    triples = sorted(f"{s.n3()} {p.n3()} {o.n3()}" for s, p, o in g if s != act)
    return hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()


def _git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _s(v) -> str | None:
    return str(v) if v is not None else None


def build_rows(inferred_ttl: Path, instances_ttl: Path) -> list[dict]:
    """instances + inferred TTL을 합쳐 서빙 계약 SELECT로 SR-단위 행 생성."""
    from rdflib import Graph

    print(f"Parsing {instances_ttl.name} ({instances_ttl.stat().st_size / 1024 / 1024:.1f} MB)...", flush=True)
    g = Graph()
    g.parse(str(instances_ttl), format="turtle")
    print(f"  instances triples: {len(g)}", flush=True)
    g.parse(str(inferred_ttl), format="turtle")
    print(f"  + inferred triples loaded: {inferred_ttl.name}", flush=True)

    rows: list[dict] = []

    # R-1 exemptedBy → SR 단위 (sr, exemptNsId)
    n_ex = 0
    for r in g.query(Q_EXEMPTED):
        sr_id = _s(r.srId)
        target = _s(r.exemptNsId)
        if not sr_id or not target:
            continue
        attrs = {}
        if r.exemptArt is not None:
            attrs["article_code"] = _s(r.exemptArt)
        if r.condition is not None:
            attrs["condition"] = _s(r.condition)
        rows.append({
            "sr_id": sr_id, "rel_type": "exemptedBy", "target_id": target,
            "target_kind": "norm_statement", "rule_id": "R-1",
            "attrs": attrs or None,
        })
        n_ex += 1
    print(f"  R-1 exemptedBy SR-rows: {n_ex}", flush=True)

    # R-2 coApplicable → 양방향(symmetric) SR 쌍. 각 행 attrs는 그 행의 TARGET SR을 기술
    # (역방향에 ?co 메타를 재사용하면 상대 SR 오기재 — emit이 단방향만 산출하므로 주의).
    n_co = 0
    co_seen: set[tuple[str, str]] = set()
    for r in g.query(Q_COAPPLICABLE):
        a = _s(r.srId)
        b = _s(r.coSrId)
        if not a or not b or a == b:
            continue
        b_attrs = {}  # target = b (a→b 행)
        if r.coTitle is not None:
            b_attrs["title"] = _s(r.coTitle)
        if r.coArt is not None:
            b_attrs["article_code"] = _s(r.coArt)
        a_attrs = {}  # target = a (b→a 행)
        if r.srTitle is not None:
            a_attrs["title"] = _s(r.srTitle)
        if r.srArt is not None:
            a_attrs["article_code"] = _s(r.srArt)
        for (s, t, at) in ((a, b, b_attrs), (b, a, a_attrs)):  # at은 target(t)을 기술
            if (s, t) in co_seen:
                continue
            co_seen.add((s, t))
            rows.append({
                "sr_id": s, "rel_type": "coApplicable", "target_id": t,
                "target_kind": "safety_requirement", "rule_id": "R-2",
                "attrs": at or None,
            })
            n_co += 1
    print(f"  R-2 coApplicable SR-rows (both directions): {n_co}", flush=True)

    return rows


def open_run(inferred_ttl: Path) -> int:
    rel_path = str(inferred_ttl.relative_to(REPO_ROOT)) if inferred_ttl.is_relative_to(REPO_ROOT) else str(inferred_ttl)
    with SessionLocal() as s:
        run = PgMaterializationRun(
            rule_set=RULE_SET,
            ontology_commit=_git_sha(),
            source_ttl=rel_path,
            source_ttl_sha256=_relations_sha256(inferred_ttl),
            status="running",
        )
        s.add(run)
        s.commit()
        s.refresh(run)
        return run.run_id


def finalize_run(run_id: int, status: str, triple_count: int | None) -> None:
    """실패 경로 전용 — 완료는 upsert_and_reconcile가 data txn 내부에서 원자적으로 표시."""
    with SessionLocal() as s:
        run = s.get(PgMaterializationRun, run_id)
        if run is None:
            return
        run.status = status
        run.triple_count = triple_count
        run.finished_at = func.now()
        s.commit()


def _last_completed_triple_count() -> int | None:
    with SessionLocal() as s:
        row = s.execute(text(
            "SELECT triple_count FROM materialization_runs "
            "WHERE rule_set = :rs AND status = 'completed' ORDER BY run_id DESC LIMIT 1"
        ), {"rs": RULE_SET}).first()
        return row[0] if row and row[0] is not None else None


def upsert_and_reconcile(rows: list[dict], run_id: int) -> dict:
    """UPSERT + reconcile + run 완료표시 — 모두 단일 txn(원자).

    - advisory lock으로 동시 import 직렬화 → reconcile가 동시 run의 행을 stale로 오인·삭제하는
      레이스 차단(직렬화된 last-writer = 마지막 full 재물질화, 멱등).
    - run 완료(status/triple_count/finished_at)를 데이터와 같은 txn에서 갱신 → '데이터는
      커밋됐는데 run은 running' 불일치 제거(중간 실패 시 둘 다 롤백, except가 'failed' 기록).
    """
    table = PgSrInferredRelation.__table__
    for r in rows:
        r["run_id"] = run_id

    new_keys = {(r["sr_id"], r["rel_type"], r["target_id"], r["rule_id"]) for r in rows}
    stats = {"upserted": 0, "deleted_stale": 0}

    with engine.begin() as conn:
        # 동시 import 직렬화 — reconcile 레이스 차단.
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('sr_inferred_relations'))"))

        BATCH = 500
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            stmt = pg_insert(table).values(chunk)
            update_cols = {
                c.name: getattr(stmt.excluded, c.name)
                for c in table.columns
                if c.name not in {"id", "created_at"}
            }
            update_cols["updated_at"] = func.now()
            stmt = stmt.on_conflict_do_update(
                index_elements=["sr_id", "rel_type", "target_id", "rule_id"],
                set_=update_cols,
            )
            conn.execute(stmt)
            stats["upserted"] += len(chunk)

        # reconcile: 이번 run 범위(R-1/R-2)의 기존 행 중 새 집합에 없는 것 삭제.
        existing = conn.execute(text(
            "SELECT sr_id, rel_type, target_id, rule_id FROM sr_inferred_relations "
            "WHERE rule_id = ANY(:rids)"
        ), {"rids": list(IMPORTED_RULE_IDS)}).fetchall()
        stale = [e for e in existing if (e[0], e[1], e[2], e[3]) not in new_keys]
        for e in stale:
            conn.execute(text(
                "DELETE FROM sr_inferred_relations WHERE sr_id=:s AND rel_type=:r "
                "AND target_id=:t AND rule_id=:u"
            ), {"s": e[0], "r": e[1], "t": e[2], "u": e[3]})
        stats["deleted_stale"] = len(stale)

        # run 완료 — 데이터와 동일 txn(원자). 실패 시 이 UPDATE도 함께 롤백.
        conn.execute(text(
            "UPDATE materialization_runs SET status='completed', triple_count=:tc, "
            "finished_at=NOW() WHERE run_id=:rid"
        ), {"tc": len(rows), "rid": run_id})

    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inferred-ttl", type=Path, default=DEFAULT_INFERRED_TTL)
    ap.add_argument("--instances-ttl", type=Path, default=DEFAULT_INSTANCES_TTL)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-empty", action="store_true",
                    help="산출 0행/급감(직전 50%% 미만)이어도 적재 강행 — reconcile wipe 안전바닥 해제")
    args = ap.parse_args()

    for p in (args.inferred_ttl, args.instances_ttl):
        if not p.exists():
            print(f"ERROR: not found: {p}", file=sys.stderr)
            if p == args.inferred_ttl:
                print("  → 먼저 `make reasoning-emit` (emit_inferred_relations.py --write) 실행", file=sys.stderr)
            return 1

    start = time.time()
    rows = build_rows(args.inferred_ttl, args.instances_ttl)
    print(f"\nBuilt {len(rows)} SR-relation rows in {time.time() - start:.1f}s")

    from collections import Counter
    by_rel = Counter(r["rel_type"] for r in rows)
    distinct_sr = len({r["sr_id"] for r in rows})
    print(f"  by rel_type: {dict(by_rel)} | distinct SR subjects: {distinct_sr}")
    for r in rows[:3]:
        print(f"  sample: {r['sr_id']} --{r['rel_type']}--> {r['target_id']} attrs={r['attrs']}")

    with SessionLocal() as s:
        n_before = s.query(func.count(PgSrInferredRelation.id)).scalar() or 0
    print(f"\nPG sr_inferred_relations before: {n_before}")

    if not args.apply:
        print(f"\n[DRY-RUN] {len(rows)} rows would be UPSERTed (run 미생성). 적재: --apply")
        return 0

    # 안전 바닥: 빈/급감 산출이 reconcile로 정상 행을 wipe하는 사고 차단(예: emit 깨짐/리네임).
    n_prev = _last_completed_triple_count()
    if not args.allow_empty:
        if not rows:
            print("REFUSE: 산출 0행 — reconcile가 기존 전량을 삭제하게 됨. 의도면 --allow-empty.",
                  file=sys.stderr)
            return 1
        if n_prev and len(rows) < n_prev * 0.5:
            print(f"REFUSE: 산출 {len(rows)}행 < 직전 완료 run {n_prev}행의 50%. "
                  f"비정상 급감. 의도면 --allow-empty.", file=sys.stderr)
            return 1

    run_id = open_run(args.inferred_ttl)
    print(f"\n--- materialization_run #{run_id} 시작 ({RULE_SET}) ---")
    try:
        stats = upsert_and_reconcile(rows, run_id)
    except Exception as e:
        finalize_run(run_id, "failed", None)
        print(f"FAILED run #{run_id}: {type(e).__name__}: {e}", file=sys.stderr)
        raise

    with SessionLocal() as s:
        n_after = s.query(func.count(PgSrInferredRelation.id)).scalar() or 0
    print(f"UPSERT {stats['upserted']} / delete stale {stats['deleted_stale']}")
    print(f"PG sr_inferred_relations after: {n_after} (run #{run_id} completed, triple_count={len(rows)})")
    print(f"\nStatus: PASS ({time.time() - start:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
