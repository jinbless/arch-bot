#!/usr/bin/env python3
"""Phase E Step 3c — SHACL shapes 5~30번째 자동 생성 (LLM).

기존 4 shape + 2-layer architecture를 seed로 신규 26 shape 생성.

산출: ontology-team/06-reasoning/ontology/serving-validation-shapes-v2.ttl
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
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
EXISTING_PATH = ONTOLOGY_DIR / "serving-validation-shapes.ttl"
OUT_PATH = ONTOLOGY_DIR / "serving-validation-shapes-v2.ttl"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "shacl_shapes",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "shapes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "ShapeName (예: HazardObservationShape)"},
                        "target_class": {"type": "string", "description": "예: core:VisualObservation"},
                        "category": {
                            "type": "string",
                            "enum": ["alethic_validation", "deontic_validation", "bridge_validation", "cardinality", "domain_constraint"],
                        },
                        "constraints_ttl": {
                            "type": "string",
                            "description": "SHACL property constraint block in Turtle (sh:property [...]). 여러 줄 가능.",
                        },
                        "comment_ko": {"type": "string"},
                    },
                    "required": ["name", "target_class", "category", "constraints_ttl", "comment_ko"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["shapes"],
        "additionalProperties": False,
    },
}


SYSTEM = """\
당신은 SHACL ontology engineer입니다. KOSHA 산업안전 ontology의 instance validation을 위한 SHACL shapes 생성.

2-layer 아키텍처:
- Layer A (alethic): Photo, VisualObservation, RiskFeature, Equipment, Worker, Hazard
- Layer B (deontic): law:Article, law:NormStatement, sr:SafetyRequirement, pen:PenaltyRule

각 shape는 다음 카테고리:
- alethic_validation: 사진/관찰 instance 검증
- deontic_validation: 법령 instance 검증 (Modality 필수 등)
- bridge_validation: 두 layer 연결 properties 검증
- cardinality: 1..N 제약
- domain_constraint: rdfs:domain/range 위반 탐지

prefix:
  sh: <http://www.w3.org/ns/shacl#>
  core: <https://cashtoss.info/ontology#>
  law: <https://cashtoss.info/ontology/law#>
  sr: <https://cashtoss.info/ontology/sr#>
  pen: <https://cashtoss.info/ontology/penalty#>
"""

USER_TEMPLATE = """\
[기존 4개 SHACL shapes]
{existing}

[Class layer 분포]
{layer_summary}

[CQ 샘플]
{cq_summary}

위 컨텍스트로 26개 신규 SHACL shapes 생성.
카테고리 균형:
- alethic_validation: 7개
- deontic_validation: 7개
- bridge_validation: 6개
- cardinality: 3개
- domain_constraint: 3개
"""


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    existing = EXISTING_PATH.read_text(encoding="utf-8") if EXISTING_PATH.exists() else ""

    layer_path = ARTIFACTS_DIR / "class_layer_assignment.json"
    layer_summary = ""
    if layer_path.exists():
        p = json.loads(layer_path.read_text(encoding="utf-8"))
        layer_summary = json.dumps(p.get("layer_counts", {}), ensure_ascii=False)

    cq_path = ARTIFACTS_DIR / "competency_questions.json"
    cq_summary = ""
    if cq_path.exists():
        cqs = json.loads(cq_path.read_text(encoding="utf-8")).get("questions") or []
        cq_summary = "\n".join(f"- [{q['type']}] {q['question_ko']}" for q in cqs[:12])

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    user = USER_TEMPLATE.format(existing=existing[:2000], layer_summary=layer_summary, cq_summary=cq_summary[:1500])
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
    shapes = payload.get("shapes") or []
    print(f"Generated {len(shapes)} SHACL shapes")

    lines: list[str] = []
    if existing:
        lines.append(existing.rstrip())
        lines.append("\n# --- v2 신규 shapes (Phase E Step 3c 자동 생성) ---\n")
    for s in shapes:
        block = f"""\
# {s['name']} ({s['category']}) — {s['comment_ko']}
core:{s['name']}
    a sh:NodeShape ;
    sh:targetClass {s['target_class']} ;
{s['constraints_ttl']}
    .
"""
        lines.append(block)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {OUT_PATH.relative_to(REPO_ROOT)}")

    from collections import Counter

    cat_counts = Counter(s.get("category") for s in shapes)
    audit_path = ARTIFACTS_DIR / "shacl_shapes_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "category_counts": dict(cat_counts),
                "shapes": shapes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved audit: {audit_path.relative_to(REPO_ROOT)}")
    print(f"Category counts: {dict(cat_counts)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
