#!/usr/bin/env python3
"""Phase E Step 3b — SWRL rules R-9~R-30 자동 생성 (LLM).

기존 R-1~R-8 패턴을 seed로 LLM이 새 rule 22개 생성.
2-layer (alethic + deontic) 추론 chain 강조.

산출: ontology-team/06-reasoning/ontology/kosha-rules-v2.swrl
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
SWRL_PATH = ONTOLOGY_DIR / "kosha-rules.swrl"
OUT_PATH = ONTOLOGY_DIR / "kosha-rules-v2.swrl"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "swrl_rules",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "R-09 ~ R-30"},
                        "name_ko": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["alethic_inference", "deontic_inference", "bridge_inference", "violation_chain", "penalty_chain"],
                        },
                        "head": {"type": "string", "description": "SWRL head (conclusion). 예: 'core:hasViolation(?obs, ?norm)'"},
                        "body": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "SWRL body atoms. 예: ['Photo(?p)', 'observedIn(?obs, ?p)', 'NormStatement(?norm)']",
                        },
                        "comment_ko": {"type": "string"},
                    },
                    "required": ["id", "name_ko", "category", "head", "body", "comment_ko"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["rules"],
        "additionalProperties": False,
    },
}


SYSTEM = """\
당신은 OWL/SWRL ontology engineer입니다. KOSHA 산업안전 ontology의 SWRL rule을 작성합니다.

2-layer 아키텍처:
- Layer A (alethic, BFO): Photo, VisualObservation, RiskFeature, Equipment, Worker, Hazard
- Layer B (deontic, LKIF-Core): law:Article, law:NormStatement, sr:SafetyRequirement, pen:PenaltyRule, core:Modality
- Bridge: violatesObligation, observedIn, appliesTo

규칙은 다음 chain을 추론:
1. 사진 관찰 (Layer A) → 위험 특징 (Layer A)
2. 위험 특징 → 적용 가능한 SR (Bridge)
3. SR 위반 → 위반된 NormStatement (Layer B)
4. NormStatement → PenaltyRule (Layer B)

namespace prefix: core:, law:, sr:, pen:, guide:, risk:, haz:, agent:, ctx:, she:, app:
"""

USER_TEMPLATE = """\
[기존 SWRL R-1~R-8 패턴]
{existing}

[Class layer 분포 (Step 1 결과)]
{layer_summary}

[CQ 샘플 (Step 1)]
{cq_summary}

위 컨텍스트를 바탕으로 R-09~R-30 (총 22개) 신규 SWRL rule 생성.
카테고리 균형:
- alethic_inference: 5개 (Layer A 내부 추론)
- bridge_inference: 5개 (Layer A → B 연결)
- deontic_inference: 5개 (Layer B 내부 추론)
- violation_chain: 4개 (위반 추적)
- penalty_chain: 3개 (제재 추론)
"""


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    existing = SWRL_PATH.read_text(encoding="utf-8")[:3000] if SWRL_PATH.exists() else ""

    layer_path = ARTIFACTS_DIR / "class_layer_assignment.json"
    layer_summary = ""
    if layer_path.exists():
        p = json.loads(layer_path.read_text(encoding="utf-8"))
        layer_summary = json.dumps(p.get("layer_counts", {}), ensure_ascii=False)
        sample_classes = [(a["iri"].rsplit("#", 1)[-1], a["layer"]) for a in (p.get("assignments") or [])[:30]]
        layer_summary += "\n samples: " + str(sample_classes)

    cq_path = ARTIFACTS_DIR / "competency_questions.json"
    cq_summary = ""
    if cq_path.exists():
        cqs = json.loads(cq_path.read_text(encoding="utf-8")).get("questions") or []
        cq_summary = "\n".join(f"- [{q['type']}] {q['question_ko']}" for q in cqs[:15])

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    user = USER_TEMPLATE.format(existing=existing[:2000], layer_summary=layer_summary[:1500], cq_summary=cq_summary[:2000])
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
    rules = payload.get("rules") or []
    print(f"Generated {len(rules)} SWRL rules")

    # Build SWRL .swrl text (existing + new)
    lines: list[str] = []
    if existing:
        lines.append(existing.rstrip())
        lines.append("\n\n# --- v2 신규 rule (Phase E Step 3b 자동 생성) ---\n")
    from collections import Counter

    cat_counts = Counter(r.get("category") for r in rules)
    for r_entry in rules:
        body_str = " AND ".join(r_entry["body"])
        block = f"""\
# {r_entry['id']}: {r_entry['name_ko']} ({r_entry['category']})
# {r_entry['comment_ko']}
{r_entry['head']} ← {body_str}
"""
        lines.append(block)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"Category counts: {dict(cat_counts)}")

    audit_path = ARTIFACTS_DIR / "swrl_rules_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "category_counts": dict(cat_counts),
                "rules": rules,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved audit: {audit_path.relative_to(REPO_ROOT)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
