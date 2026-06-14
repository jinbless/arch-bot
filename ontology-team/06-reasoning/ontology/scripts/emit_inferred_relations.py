#!/usr/bin/env python3
"""Track A ② — 추론 diff TTL 산출 (R-1 exemptedBy / R-2 coApplicable).

리즈너(SWRL/Pellet) 산출과 동치인 SPARQL CONSTRUCT를 kosha-instances.ttl ABox에
적용해 **추론으로만 얻어지는** 트리플(inferred-only diff)을 별도 TTL로 emit한다.
이 산출물이 PG 물질화(sr_inferred_relations)의 입력이며, "추론이 서빙의 하중을
받는다"는 수직 슬라이스의 출발점이다.

규칙(생산 경로 SWRL과 동치, 오프라인 rdflib 재현):
  R-1 exemptedBy : ?oblig core:exemptedBy ?exempt
                   (Obligation NS  ←  Exemption NS via law:modifies)  — 현재 107건
  R-2 coApplicable: ?sr1 core:coApplicable ?sr2
                   (같은 source Article 기반 SR 쌍)                    — 현재 0건
                   (SR↔Article 1:1 → cross-pair 0. 의미있는 co-application은
                    K-R2 same-Chapter SHACL(별도 프로파일)에 존재.)

산출 TTL은 run-level PROV-O Activity 헤더를 담는다(트리플 단위 wasGeneratedBy는
PG sr_inferred_relations.run_id(→ materialization_runs)에서 행 단위로 보존).

사용:
  python emit_inferred_relations.py                 # dry (카운트만)
  python emit_inferred_relations.py --write          # kosha-inferred-relations.ttl 산출
  python emit_inferred_relations.py --write --no-coapplicable
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

SCRIPT_DIR = Path(__file__).resolve().parent
ONT_DIR = SCRIPT_DIR.parent  # ontology-team/06-reasoning/ontology

CORE = Namespace("https://cashtoss.info/ontology#")
LAW = Namespace("https://cashtoss.info/ontology/law#")
SR = Namespace("https://cashtoss.info/ontology/sr#")
PROV = Namespace("http://www.w3.org/ns/prov#")

DEFAULT_SOURCE = ONT_DIR / "kosha-instances.ttl"
DEFAULT_OUT = ONT_DIR / "kosha-inferred-relations.ttl"

# 생산 경로의 권위 규칙 정의 파일(추론 근거 PROV 기록용).
RULE_FILES = (
    "kosha-rules-r1-r3-swrl.ttl",   # R-1 exemptedBy (+ R-3)
    "kosha-rules-r2-r4-swrl.ttl",   # R-2 coApplicable (+ R-4)
)

R1_CONSTRUCT = """
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
CONSTRUCT { ?ns1 core:exemptedBy ?ns2 . } WHERE {
  ?ns1 a law:NormStatement ; law:hasModality core:Obligation .
  ?ns2 a law:NormStatement ; law:hasModality core:Exemption .
  ?ns2 law:modifies ?ns1 .
}
"""

# R-2 오프라인 동치: rdflib은 OWL propertyChain 미추론 → NS chain(derivedFromNS →
# hasSourceArticle) 직접 사용. STR(?sr1) < STR(?sr2)로 무순서 유일쌍(symmetric 중복 방지).
R2_CONSTRUCT = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
CONSTRUCT { ?sr1 core:coApplicable ?sr2 . } WHERE {
  ?sr1 a sr:SafetyRequirement ; sr:derivedFromNS ?ns1 .
  ?sr2 a sr:SafetyRequirement ; sr:derivedFromNS ?ns2 .
  ?ns1 law:hasSourceArticle ?art .
  ?ns2 law:hasSourceArticle ?art .
  FILTER(?sr1 != ?sr2 && STR(?sr1) < STR(?sr2))
}
"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ONT_DIR),
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def build(source: Path, include_coapplicable: bool) -> tuple[Graph, dict]:
    print(f"Loading {source.name} ({source.stat().st_size / 1024 / 1024:.1f} MB)...", flush=True)
    g = Graph()
    g.parse(str(source), format="turtle")
    print(f"  base triples: {len(g)}", flush=True)

    inferred = Graph()
    inferred.bind("core", CORE)
    inferred.bind("law", LAW)
    inferred.bind("sr", SR)
    inferred.bind("prov", PROV)

    r1 = list(g.query(R1_CONSTRUCT))
    for t in r1:
        inferred.add(t)
    print(f"  R-1 exemptedBy: {len(r1)}", flush=True)

    r2_n = 0
    if include_coapplicable:
        r2 = list(g.query(R2_CONSTRUCT))
        for t in r2:
            inferred.add(t)
        r2_n = len(r2)
        print(f"  R-2 coApplicable: {r2_n}", flush=True)
    else:
        print("  R-2 coApplicable: skipped (--no-coapplicable)", flush=True)

    counts = {"exemptedBy": len(r1), "coApplicable": r2_n}
    return inferred, counts


def add_prov_header(g: Graph, source: Path, counts: dict, started_at: str) -> None:
    """run-level PROV-O Activity. 트리플 단위 출처는 PG run_id가 보존."""
    act = URIRef("https://cashtoss.info/ontology/prov/run/inferred-relations-emit")
    g.add((act, RDF.type, PROV.Activity))
    g.add((act, RDFS.label, Literal("R-1/R-2 inferred-relations emit", lang="en")))
    g.add((act, PROV.startedAtTime, Literal(started_at, datatype=XSD.dateTime)))
    g.add((act, PROV.used, URIRef(f"file:{source.name}")))
    g.add((act, CORE.sourceSha256, Literal(_sha256(source))))
    g.add((act, CORE.ontologyCommit, Literal(_git_sha())))
    g.add((act, CORE.exemptedByCount, Literal(counts["exemptedBy"], datatype=XSD.integer)))
    g.add((act, CORE.coApplicableCount, Literal(counts["coApplicable"], datatype=XSD.integer)))
    for rf in RULE_FILES:
        g.add((act, PROV.wasAssociatedWith, URIRef(f"file:{rf}")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true", help="TTL 산출 (없으면 카운트만)")
    ap.add_argument("--no-coapplicable", dest="coapplicable", action="store_false",
                    help="R-2 coApplicable 산출 생략")
    ap.add_argument("--started-at", default=None,
                    help="PROV startedAtTime ISO8601 (기본: 현재 UTC)")
    args = ap.parse_args()

    if not args.source.exists():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    started_at = args.started_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    inferred, counts = build(args.source, args.coapplicable)

    if not args.write:
        print(f"\n[DRY] exemptedBy={counts['exemptedBy']} coApplicable={counts['coApplicable']} "
              f"(산출하려면 --write)")
        return 0

    add_prov_header(inferred, args.source, counts, started_at)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    inferred.serialize(str(args.out), format="turtle")
    print(f"\n→ {args.out.name}: {len(inferred)} triples "
          f"(exemptedBy {counts['exemptedBy']} + coApplicable {counts['coApplicable']} + PROV header)")
    print(f"  source sha256: {_sha256(args.source)[:16]}...  git: {_git_sha()[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
