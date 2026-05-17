#!/usr/bin/env python3
"""Phase E Step 5b — SPARQL CQ 재생성 (instance pattern 기반).

기존 LLM 생성 SPARQL은 actual instance property와 mismatch (0% coverage).
이번엔 kosha-instances.ttl에서 실제 property pattern을 추출하여 LLM에게 제공.

흐름:
1. instance graph parse → 자주 사용된 (class, predicate, object_type) triple 추출
2. CQ + actual pattern을 LLM에 제공
3. 재생성된 SPARQL을 rdflib에서 in-memory 실행 → coverage 측정

산출:
- sparql_cq_v2.json (재생성 결과)
- sparql_cq_coverage.json 업데이트
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
INSTANCES_TTL = ONTOLOGY_DIR / "kosha-instances.ttl"
V2_OWL = ONTOLOGY_DIR / "kosha-ontology-v2.owl"
CQ_PATH = ARTIFACTS_DIR / "competency_questions.json"
SPARQL_V1_PATH = ARTIFACTS_DIR / "sparql_cq_coverage.json"
SPARQL_V2_PATH = ARTIFACTS_DIR / "sparql_cq_v2.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "sparql_queries",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cq_id": {"type": "string"},
                        "sparql": {"type": "string"},
                        "uses_classes": {"type": "array", "items": {"type": "string"}},
                        "complexity": {"type": "string", "enum": ["basic", "intermediate", "advanced"]},
                    },
                    "required": ["cq_id", "sparql", "uses_classes", "complexity"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["queries"],
        "additionalProperties": False,
    },
}


def extract_instance_patterns(g) -> dict:
    """instance graph에서 (class, predicate) 사용 패턴 추출."""
    from rdflib import RDF, RDFS, URIRef

    pred_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    class_predicates: dict[str, Counter[str]] = {}

    for s, p, o in g:
        ps = str(p)
        if ps == str(RDF.type) and isinstance(o, URIRef):
            class_counts[str(o)] += 1
        else:
            pred_counts[ps] += 1

    # For each class, find common predicates (separate pass)
    type_map: dict = {}
    for s, _, o in g.triples((None, RDF.type, None)):
        if isinstance(o, URIRef):
            type_map.setdefault(str(s), set()).add(str(o))

    for s, p, _ in g:
        ps = str(p)
        if ps == str(RDF.type):
            continue
        for cls in type_map.get(str(s), set()):
            class_predicates.setdefault(cls, Counter())[ps] += 1

    return {
        "top_classes": class_counts.most_common(40),
        "top_predicates": pred_counts.most_common(50),
        "class_predicates": {k: v.most_common(10) for k, v in list(class_predicates.items())[:30]},
    }


SYSTEM = """\
당신은 SPARQL 전문가입니다. KOSHA 산업안전 ontology의 competency question을 SPARQL SELECT query로 변환.

KOSHA ontology namespace prefix:
  PREFIX core: <https://cashtoss.info/ontology#>
  PREFIX law: <https://cashtoss.info/ontology/law#>
  PREFIX sr: <https://cashtoss.info/ontology/sr#>
  PREFIX pen: <https://cashtoss.info/ontology/penalty#>
  PREFIX guide: <https://cashtoss.info/ontology/guide#>
  PREFIX risk: <https://cashtoss.info/ontology/risk#>
  PREFIX haz: <https://cashtoss.info/ontology/risk/hazard#>
  PREFIX ctx: <https://cashtoss.info/ontology/risk/context#>
  PREFIX agent: <https://cashtoss.info/ontology/risk/agent#>
  PREFIX she: <https://cashtoss.info/ontology/risk/situation#>
  PREFIX app: <https://cashtoss.info/ontology/app#>
  PREFIX industry: <https://cashtoss.info/ontology/industry#>
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  PREFIX owl: <http://www.w3.org/2002/07/owl#>

중요: 사용자가 제공하는 actual instance pattern을 참조해서 SPARQL을 작성하세요. instance에 없는 가상 property를 사용하지 마세요.

각 SPARQL은:
- prefix declarations 포함
- SELECT + WHERE 구조
- 실제 instance graph에서 결과 반환되어야 함 (LIMIT 100)
"""

USER_TEMPLATE = """\
[CQ 변환 대상 (10개)]
{cqs}

[Actual instance graph patterns (자주 사용된 property)]
Top classes (with instance count):
{top_classes}

Top predicates (with usage count):
{top_predicates}

Class → 자주 사용된 properties:
{class_predicates}

위 actual pattern을 활용하여 각 CQ의 SPARQL을 작성. 실제 instance graph에서 답 반환되도록.
"""


def render_patterns(patterns: dict) -> tuple[str, str, str]:
    top_classes = "\n".join(f"  {cls.rsplit('#', 1)[-1]}: {cnt}" for cls, cnt in patterns["top_classes"][:25])
    top_predicates = "\n".join(f"  {pred.rsplit('#', 1)[-1] or pred[-40:]}: {cnt}" for pred, cnt in patterns["top_predicates"][:30])
    class_preds = []
    for cls, preds in list(patterns["class_predicates"].items())[:15]:
        local = cls.rsplit("#", 1)[-1]
        prop_list = ", ".join(p.rsplit("#", 1)[-1] for p, _ in preds[:6])
        class_preds.append(f"  {local}: {prop_list}")
    return top_classes, top_predicates, "\n".join(class_preds)


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    print("=== Load instance graph ===")
    from rdflib import Graph

    g = Graph()
    g.parse(str(V2_OWL), format="xml")
    print(f"  v2 owl: {len(g)} triples")
    g.parse(str(INSTANCES_TTL), format="turtle")
    print(f"  + instances: {len(g)} triples")

    print("\n=== Extract instance patterns ===")
    patterns = extract_instance_patterns(g)
    print(f"  top classes: {len(patterns['top_classes'])}")
    print(f"  top predicates: {len(patterns['top_predicates'])}")
    top_classes, top_predicates, class_preds = render_patterns(patterns)
    print(f"\n  Top 5 classes:")
    for cls, cnt in patterns["top_classes"][:5]:
        print(f"    {cls.rsplit('#', 1)[-1]}: {cnt}")

    print("\n=== Load CQs ===")
    cqs = json.loads(CQ_PATH.read_text(encoding="utf-8")).get("questions") or []
    if args.limit:
        cqs = cqs[: args.limit]
    print(f"  {len(cqs)} CQs")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    queries: list[dict] = []
    batch = 10
    for i in range(0, len(cqs), batch):
        slice_ = cqs[i : i + batch]
        cqs_text = "\n".join(
            f"- {q['id']} [{q['type']}]: {q['question_ko']} (expected_classes: {q.get('expected_classes', [])})"
            for q in slice_
        )
        user = USER_TEMPLATE.format(
            cqs=cqs_text,
            top_classes=top_classes,
            top_predicates=top_predicates,
            class_predicates=class_preds,
        )
        try:
            r = await client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "developer", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_schema", "json_schema": SCHEMA},
                max_completion_tokens=8192,
            )
            payload = json.loads(r.choices[0].message.content or "{}")
            queries.extend(payload.get("queries") or [])
            print(f"  sparql batch {i + len(slice_)}/{len(cqs)}", flush=True)
        except Exception as exc:
            print(f"  batch {i} FAILED: {exc}", file=sys.stderr)
    print(f"\nGenerated {len(queries)} SPARQL queries")

    print("\n=== Run queries against in-memory graph ===")
    answered = 0
    errored = 0
    details = []
    for q in queries:
        sparql = q.get("sparql", "")
        try:
            res = g.query(sparql)
            rows = list(res)
            n = len(rows)
            if n > 0:
                answered += 1
            details.append({"cq_id": q.get("cq_id"), "rows": n, "status": "ok"})
        except Exception as exc:
            errored += 1
            details.append({"cq_id": q.get("cq_id"), "status": "error", "error": str(exc)[:200]})
    coverage = answered / len(queries) if queries else 0
    print(f"  answered={answered}/{len(queries)} = {coverage:.1%}, errored={errored}")

    # Save
    SPARQL_V2_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPARQL_V2_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "instance_patterns": patterns,
                "cq_total": len(cqs),
                "sparql_generated": len(queries),
                "answered": answered,
                "errored": errored,
                "coverage": round(coverage, 4),
                "details": details,
                "queries": queries,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {SPARQL_V2_PATH.relative_to(REPO_ROOT)}")

    # Update v1 coverage to reflect v2 result
    if SPARQL_V1_PATH.exists():
        v1 = json.loads(SPARQL_V1_PATH.read_text(encoding="utf-8"))
        v1["v2_coverage"] = round(coverage, 4)
        v1["v2_answered"] = answered
        v1["v2_errored"] = errored
        SPARQL_V1_PATH.write_text(json.dumps(v1, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Updated: {SPARQL_V1_PATH.relative_to(REPO_ROOT)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
