#!/usr/bin/env python3
"""Phase E Step 5 — CQ → SPARQL 자동 변환 + Fuseki 답 검증 (LLM).

competency_questions.json의 50개 CQ를 SPARQL query로 자동 변환.
Fuseki endpoint에 실행하여 답 가능 여부 (coverage) 측정.

산출:
- sparql_cq_coverage.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
CQ_PATH = ARTIFACTS_DIR / "competency_questions.json"
OUT_PATH = ARTIFACTS_DIR / "sparql_cq_coverage.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")
FUSEKI_ENDPOINT = os.environ.get("FUSEKI_ENDPOINT", "http://localhost:3030/kosha/sparql")


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
                        "sparql": {"type": "string", "description": "Complete SPARQL SELECT query"},
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

SYSTEM = """\
당신은 SPARQL 전문가입니다. KOSHA 산업안전 ontology의 competency question을 SPARQL SELECT query로 변환합니다.

사용 가능한 namespace prefix:
  PREFIX core: <https://cashtoss.info/ontology#>
  PREFIX law: <https://cashtoss.info/ontology/law#>
  PREFIX sr: <https://cashtoss.info/ontology/sr#>
  PREFIX pen: <https://cashtoss.info/ontology/penalty#>
  PREFIX guide: <https://cashtoss.info/ontology/guide#>
  PREFIX risk: <https://cashtoss.info/ontology/risk#>
  PREFIX haz: <https://cashtoss.info/ontology/risk/hazard#>
  PREFIX ctx: <https://cashtoss.info/ontology/risk/context#>
  PREFIX app: <https://cashtoss.info/ontology/app#>
  PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  PREFIX owl: <http://www.w3.org/2002/07/owl#>

각 SPARQL은 prefix declarations + SELECT + WHERE 구조. 답 가능하면 결과 행 1+ 반환되도록 작성.
"""


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    if not CQ_PATH.exists():
        print(f"ERROR: {CQ_PATH} 없음. Step 1 먼저.", file=sys.stderr)
        return 2

    cqs = json.loads(CQ_PATH.read_text(encoding="utf-8")).get("questions") or []
    if args.limit:
        cqs = cqs[: args.limit]
    print(f"CQs to convert: {len(cqs)}")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)

    # Batch 10 at a time
    queries: list[dict] = []
    batch = 10
    for i in range(0, len(cqs), batch):
        slice_ = cqs[i : i + batch]
        user = "다음 CQ들을 SPARQL로 변환:\n" + "\n".join(
            f"- {q['id']} [{q['type']}]: {q['question_ko']} (uses: {q.get('expected_classes', [])})"
            for q in slice_
        )
        try:
            r = await client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "developer", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_schema", "json_schema": SCHEMA},
                max_completion_tokens=4096,
            )
            payload = json.loads(r.choices[0].message.content or "{}")
            queries.extend(payload.get("queries") or [])
            print(f"  sparql batch {i + len(slice_)}/{len(cqs)}", flush=True)
        except Exception as exc:
            print(f"  batch {i} FAILED: {exc}", file=sys.stderr)
    print(f"Generated {len(queries)} SPARQL queries")

    # Try Fuseki (if reachable) — count coverage
    answered = 0
    errored = 0
    coverage_details = []
    try:
        import urllib.request
        import urllib.parse

        for q in queries:
            try:
                url = f"{FUSEKI_ENDPOINT}?{urllib.parse.urlencode({'query': q['sparql']})}"
                req = urllib.request.Request(
                    url,
                    headers={"Accept": "application/sparql-results+json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    n_rows = len(data.get("results", {}).get("bindings", []))
                    coverage_details.append({"cq_id": q["cq_id"], "rows": n_rows, "status": "ok"})
                    if n_rows > 0:
                        answered += 1
            except Exception as exc:
                coverage_details.append({"cq_id": q["cq_id"], "status": "error", "error": str(exc)[:200]})
                errored += 1
    except Exception as exc:
        print(f"Fuseki probe failed: {exc}", file=sys.stderr)

    coverage = answered / len(queries) if queries else 0
    print(f"\nFuseki coverage: {answered}/{len(queries)} = {coverage:.1%} (errored: {errored})")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "endpoint": FUSEKI_ENDPOINT,
                "cq_total": len(cqs),
                "sparql_generated": len(queries),
                "answered": answered,
                "errored": errored,
                "coverage": round(coverage, 4),
                "coverage_details": coverage_details,
                "queries": queries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {OUT_PATH.relative_to(REPO_ROOT)}")
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
