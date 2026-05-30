#!/usr/bin/env python3
"""Phase 0 — Canonical-CI 레이어 산출 (Three-Worlds 재설계).

근본: per-guide CI instance(54,631)는 추출 부산물. 같은 control이 여러 Guide에 중복
(guide_frequency max 130). CI를 "고유 control 세계"로 정규화하고 Guide는 그 control을
bundle하는 상위 계층으로 본다. boilerplate = canonical CI의 guide-degree(구조 신호).

비파괴(additive): 기존 checklist_items instance 보존 + canonical_ci_id FK로 연결.
동일성 1차 = 정규화-텍스트(NFKC + 공백 정리). 식별자 결정적(해시). 의미적 병합은 후속 gated.
구조 산출이라 PG staging에서 계산 → export_owl.py가 ABox로 author (휴리스틱 아님).

사용:
  PYTHONIOENCODING=utf-8 python derive_canonical_ci.py                  # dry-run 분석
  PYTHONIOENCODING=utf-8 python derive_canonical_ci.py --apply          # staging 테이블 생성+적재
  ... --boilerplate-threshold 10
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from collections import defaultdict

import psycopg2

PG = "dbname=kosha user=kosha password=1229 host=localhost"
AXES = ("accident_types_canonical", "hazardous_agents_canonical", "work_contexts_canonical")


def norm_text(t: str) -> str:
    """정규화-텍스트(보수적): NFKC + 공백 정리 + strip. 동일 텍스트=동일 control."""
    if not t:
        return ""
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def canonical_id(nt: str) -> str:
    """정규화-텍스트 → 결정적 canonical id (재실행 안정)."""
    return "CCI-" + hashlib.sha1(nt.encode("utf-8")).hexdigest()[:12]


def _union(values) -> list[str]:
    out: set[str] = set()
    for v in values:
        if isinstance(v, list):
            out.update(c for c in v if isinstance(c, str))
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="staging 테이블 생성+적재")
    ap.add_argument("--boilerplate-threshold", type=int, default=10,
                    help="guide-degree 이 값 이상이면 is_boilerplate=true")
    args = ap.parse_args()

    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    cur.execute(
        "SELECT identifier, text, source_guide, "
        "accident_types_canonical, hazardous_agents_canonical, work_contexts_canonical "
        "FROM checklist_items"
    )
    rows = cur.fetchall()
    print(f"checklist_items instance: {len(rows)}")

    # 정규화-텍스트로 군집
    groups: dict[str, dict] = defaultdict(
        lambda: {"members": [], "guides": set(), "rep": "",
                 "acc": [], "agt": [], "ctx": []}
    )
    for ident, text, sg, acc, agt, ctx in rows:
        nt = norm_text(text)
        if not nt:
            continue
        cid = canonical_id(nt)
        g = groups[cid]
        g["members"].append(ident)
        if sg:
            g["guides"].add(sg)
        if not g["rep"]:
            g["rep"] = text
        g["acc"].append(acc)
        g["agt"].append(agt)
        g["ctx"].append(ctx)

    # 집계
    canon = {}
    for cid, g in groups.items():
        degree = len(g["guides"])
        canon[cid] = {
            "rep": g["rep"],
            "member_count": len(g["members"]),
            "members": g["members"],
            "guides": sorted(g["guides"]),
            "degree": degree,
            "is_boilerplate": degree >= args.boilerplate_threshold,
            "acc": _union(g["acc"]),
            "agt": _union(g["agt"]),
            "ctx": _union(g["ctx"]),
        }
    conn_close_needed = True

    # === 리포트 ===
    n_canon = len(canon)
    n_inst = len(rows)
    degrees = sorted((c["degree"] for c in canon.values()), reverse=True)
    boiler = [c for c in canon.values() if c["is_boilerplate"]]
    with_acc = sum(1 for c in canon.values() if c["acc"])
    with_any = sum(1 for c in canon.values() if c["acc"] or c["agt"] or c["ctx"])
    multi = sum(1 for c in canon.values() if c["degree"] > 1)

    print(f"\n=== Canonical-CI 군집 (정규화-텍스트, threshold={args.boilerplate_threshold}) ===")
    print(f"  instance {n_inst} → canonical {n_canon}  (축소율 {1 - n_canon/n_inst:.1%})")
    print(f"  degree>1 (여러 Guide 공유): {multi} ({multi/n_canon:.1%})")
    print(f"  boilerplate(degree>={args.boilerplate_threshold}): {len(boiler)}")
    print(f"  facet 보유: accident {with_acc} ({with_acc/n_canon:.1%}), any-facet {with_any} ({with_any/n_canon:.1%})")
    # degree 분포
    import bisect
    buckets = [1, 2, 3, 5, 10, 20, 50, 100]
    hist = defaultdict(int)
    for d in degrees:
        i = bisect.bisect_right(buckets, d) - 1
        hist[buckets[i] if i >= 0 else 1] += 1
    print("  degree 분포:")
    for b in buckets:
        if hist[b]:
            print(f"    >= {b:>3}: {hist[b]}")
    print("  최다 공유 canonical(boilerplate 후보) 상위 8:")
    for c in sorted(canon.values(), key=lambda x: -x["degree"])[:8]:
        print(f"    degree={c['degree']:>3} members={c['member_count']:>3}  {c['rep'][:54]}")

    if not args.apply:
        print("\n--apply 로 staging 테이블 생성+적재")
        conn.close()
        return 0

    # === --apply: staging 테이블 ===
    print("\n[apply] DDL (additive, IF NOT EXISTS)...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS canonical_checklist_items (
            canonical_ci_id varchar(20) PRIMARY KEY,
            rep_text text NOT NULL,
            member_count integer NOT NULL,
            guide_degree integer NOT NULL,
            is_boilerplate boolean NOT NULL DEFAULT false,
            accident_types_canonical jsonb,
            hazardous_agents_canonical jsonb,
            work_contexts_canonical jsonb,
            addresses_hazard_canonical jsonb
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS guide_control_bundle (
            guide_code varchar(20) NOT NULL,
            canonical_ci_id varchar(20) NOT NULL,
            member_count integer NOT NULL DEFAULT 1,
            PRIMARY KEY (guide_code, canonical_ci_id)
        )
    """)
    cur.execute("ALTER TABLE checklist_items ADD COLUMN IF NOT EXISTS canonical_ci_id varchar(20)")
    cur.execute("TRUNCATE canonical_checklist_items")
    cur.execute("TRUNCATE guide_control_bundle")

    import json
    for cid, c in canon.items():
        cur.execute(
            "INSERT INTO canonical_checklist_items "
            "(canonical_ci_id, rep_text, member_count, guide_degree, is_boilerplate, "
            " accident_types_canonical, hazardous_agents_canonical, work_contexts_canonical) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (cid, c["rep"], c["member_count"], c["degree"], c["is_boilerplate"],
             json.dumps(c["acc"]), json.dumps(c["agt"]), json.dumps(c["ctx"])),
        )
    # guide_control_bundle + instance→canonical: (guide, canonical) member counts
    bundle_counts: dict[tuple, int] = defaultdict(int)
    cur.execute("SELECT identifier, source_guide, text FROM checklist_items")
    inst_canon = {}
    for ident, sg, text in cur.fetchall():
        nt = norm_text(text)
        if not nt:
            continue
        cid = canonical_id(nt)
        inst_canon[ident] = cid
        if sg:
            bundle_counts[(sg, cid)] += 1
    for (sg, cid), n in bundle_counts.items():
        cur.execute(
            "INSERT INTO guide_control_bundle (guide_code, canonical_ci_id, member_count) "
            "VALUES (%s,%s,%s) ON CONFLICT (guide_code, canonical_ci_id) DO UPDATE SET member_count=EXCLUDED.member_count",
            (sg, cid, n),
        )
    # checklist_items.canonical_ci_id backfill
    for ident, cid in inst_canon.items():
        cur.execute("UPDATE checklist_items SET canonical_ci_id=%s WHERE identifier=%s", (cid, ident))
    conn.commit()
    print(f"  canonical_checklist_items: {n_canon}")
    print(f"  guide_control_bundle: {len(bundle_counts)}")
    print(f"  checklist_items.canonical_ci_id backfill: {len(inst_canon)}")
    conn.close()
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
