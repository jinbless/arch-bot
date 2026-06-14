#!/usr/bin/env python3
"""Track A ② — 추론 diff TTL 산출 (R-1 exemptedBy / R-2 coApplicable / K-R2 chapter-coApplicable).

리즈너(SWRL/Pellet/SHACL) 산출과 동치인 SPARQL CONSTRUCT를 kosha-instances.ttl ABox에
적용해 **추론으로만 얻어지는** 트리플(inferred-only diff)을 별도 TTL로 emit한다. 이 산출물이
PG 물질화(sr_inferred_relations)의 입력이며, "추론이 서빙의 하중을 받는다" 수직 슬라이스의
출발점이다.

두 모드:
  strict  : R-1 exemptedBy(107) + R-2 coApplicable(0, 같은 Article 1:1) → kosha-inferred-relations.ttl
  chapter : K-R2 coApplicable(16,429, 같은 Chapter 일반화) → kosha-coapplicable-chapter.ttl
            (kosha-rules-k-general-shacl.ttl의 SHACL K-R2 동치 — Article→Chapter 완화)

산출 TTL은 run-level PROV-O Activity 헤더를 담는다(prov/run/ 접두사; 트리플 단위 wasGeneratedBy는
PG sr_inferred_relations.run_id에서 행 단위로 보존). content 해시는 PROV를 제외하므로 재-emit
타임스탬프 변동이 drift로 오인되지 않는다.

사용:
  python emit_inferred_relations.py --write                    # strict (R-1/R-2)
  python emit_inferred_relations.py --mode chapter --write     # K-R2 same-Chapter coApplicable
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
PROV_RUN = "https://cashtoss.info/ontology/prov/run/"  # 모든 emit Activity는 이 접두사 (해시 제외)

DEFAULT_SOURCE = ONT_DIR / "kosha-instances.ttl"

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

# K-R2: 같은 Chapter(belongsToChapter) 공유 SR → coApplicable (kosha-rules-k-general-shacl.ttl 동치).
# appliesToArticle는 ABox에 asserted(626, SR↔Article 1:1) → SHACL 규칙 그대로 사용.
KR2_CONSTRUCT = """
PREFIX sr: <https://cashtoss.info/ontology/sr#>
PREFIX law: <https://cashtoss.info/ontology/law#>
PREFIX core: <https://cashtoss.info/ontology#>
CONSTRUCT { ?sr1 core:coApplicable ?sr2 . } WHERE {
  ?sr1 sr:appliesToArticle ?a1 . ?a1 law:belongsToChapter ?ch .
  ?sr2 sr:appliesToArticle ?a2 . ?a2 law:belongsToChapter ?ch .
  FILTER(STR(?sr1) < STR(?sr2))
}
"""

# 생산 경로의 권위 규칙 정의 파일(추론 근거 PROV 기록용).
MODES = {
    "strict": {
        "out": ONT_DIR / "kosha-inferred-relations.ttl",
        "activity": PROV_RUN + "inferred-relations-emit",
        "label": "R-1/R-2 inferred-relations emit",
        "constructs": [("exemptedBy", R1_CONSTRUCT), ("coApplicable", R2_CONSTRUCT)],
        "rule_files": ("kosha-rules-r1-r3-swrl.ttl", "kosha-rules-r2-r4-swrl.ttl"),
    },
    "chapter": {
        "out": ONT_DIR / "kosha-coapplicable-chapter.ttl",
        "activity": PROV_RUN + "chapter-coapplicable-emit",
        "label": "K-R2 chapter-coApplicable emit",
        "constructs": [("coApplicable", KR2_CONSTRUCT)],
        "rule_files": ("kosha-rules-k-general-shacl.ttl",),
    },
}


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


def build(source: Path, constructs: list[tuple[str, str]]) -> tuple[Graph, dict]:
    print(f"Loading {source.name} ({source.stat().st_size / 1024 / 1024:.1f} MB)...", flush=True)
    g = Graph()
    g.parse(str(source), format="turtle")
    print(f"  base triples: {len(g)}", flush=True)

    inferred = Graph()
    inferred.bind("core", CORE)
    inferred.bind("law", LAW)
    inferred.bind("sr", SR)
    inferred.bind("prov", PROV)

    counts: dict[str, int] = {}
    for name, query in constructs:
        rows = list(g.query(query))
        for t in rows:
            inferred.add(t)
        counts[name] = len(rows)
        print(f"  {name}: {len(rows)}", flush=True)
    return inferred, counts


def add_prov_header(g: Graph, source: Path, counts: dict, started_at: str,
                    activity_uri: str, label: str, rule_files: tuple[str, ...]) -> None:
    """run-level PROV-O Activity. 트리플 단위 출처는 PG run_id가 보존."""
    act = URIRef(activity_uri)
    g.add((act, RDF.type, PROV.Activity))
    g.add((act, RDFS.label, Literal(label, lang="en")))
    g.add((act, PROV.startedAtTime, Literal(started_at, datatype=XSD.dateTime)))
    g.add((act, PROV.used, URIRef(f"file:{source.name}")))
    g.add((act, CORE.sourceSha256, Literal(_sha256(source))))
    g.add((act, CORE.ontologyCommit, Literal(_git_sha())))
    for name, n in counts.items():
        g.add((act, CORE[f"{name}Count"], Literal(n, datatype=XSD.integer)))
    for rf in rule_files:
        g.add((act, PROV.wasAssociatedWith, URIRef(f"file:{rf}")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=list(MODES), default="strict")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out", type=Path, default=None, help="기본: 모드별 표준 경로")
    ap.add_argument("--write", action="store_true", help="TTL 산출 (없으면 카운트만)")
    ap.add_argument("--started-at", default=None,
                    help="PROV startedAtTime ISO8601 (기본: 현재 UTC)")
    args = ap.parse_args()

    cfg = MODES[args.mode]
    out = args.out or cfg["out"]

    if not args.source.exists():
        print(f"ERROR: source not found: {args.source}", file=sys.stderr)
        return 1

    started_at = args.started_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    inferred, counts = build(args.source, cfg["constructs"])

    if not args.write:
        print(f"\n[DRY] mode={args.mode} {counts} (산출하려면 --write)")
        return 0

    add_prov_header(inferred, args.source, counts, started_at,
                    cfg["activity"], cfg["label"], cfg["rule_files"])
    out.parent.mkdir(parents=True, exist_ok=True)
    inferred.serialize(str(out), format="turtle")
    print(f"\n→ {out.name}: {len(inferred)} triples ({counts} + PROV header)")
    print(f"  source sha256: {_sha256(args.source)[:16]}...  git: {_git_sha()[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
