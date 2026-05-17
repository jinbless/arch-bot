#!/usr/bin/env python3
"""Phase E Step 1 — Competency Questions + class-layer assignment.

LLM 가속:
1. 62 class를 alethic (BFO Layer A) vs deontic (LKIF Layer B) 자동 분류
2. Competency Questions 50개 자동 생성 (alethic 25 + deontic 25)
3. 후보 ontology (BFO/LKIF-Core/RO/PROV-O/OccO/ENVO) 매핑 점수표
4. 산출:
   - competency_questions.json
   - class_layer_assignment.json
   - reuse_ontology_scorecard.json

ENV: OPENAI_API_KEY, LLM_RERANK_MODEL (default gpt-5.4-nano)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
TBOX_PATH = ONTOLOGY_DIR / "kosha-ontology.owl"
ANNOTATED_PATH = ONTOLOGY_DIR / "kosha-ontology.annotated.ttl"
SWRL_PATH = ONTOLOGY_DIR / "kosha-rules.swrl"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


def extract_classes() -> list[dict[str, str]]:
    """rdflib로 OWL TBox parse → class 목록 (iri, namespace, local, label_kor)."""
    from rdflib import Graph, RDF, OWL, RDFS, URIRef

    g = Graph()
    g.parse(str(TBOX_PATH), format="xml")
    classes: dict[str, dict[str, str]] = {}
    for s in g.subjects(RDF.type, OWL.Class):
        if not isinstance(s, URIRef):
            continue
        iri = str(s)
        if "#" in iri:
            ns, local = iri.rsplit("#", 1)
        elif "/" in iri:
            ns, local = iri.rsplit("/", 1)
        else:
            ns, local = "", iri
        if not local:
            continue
        label_kor = ""
        label_en = ""
        for lit in g.objects(s, RDFS.label):
            lang = getattr(lit, "language", None)
            if lang == "ko" and not label_kor:
                label_kor = str(lit)
            elif lang == "en" and not label_en:
                label_en = str(lit)
        classes[iri] = {
            "iri": iri,
            "namespace": ns,
            "local": local,
            "label_kor": label_kor or label_en,
        }
    return sorted(classes.values(), key=lambda c: c["iri"])


def load_swrl_summary() -> str:
    if not SWRL_PATH.exists():
        return ""
    text = SWRL_PATH.read_text(encoding="utf-8", errors="ignore")
    return text[:3000]


def load_synthetic_sample(n: int = 5) -> list[dict]:
    eval_dir = REPO_ROOT / "data-team" / "05-enrichment" / "eval-data"
    sample = []
    for f in sorted(eval_dir.glob("synthetic_observations_v*.jsonl"))[:2]:
        for line in f.read_text(encoding="utf-8").splitlines()[:n]:
            if line.strip():
                try:
                    sample.append(json.loads(line))
                except Exception:
                    continue
            if len(sample) >= n:
                break
        if len(sample) >= n:
            break
    return sample


# ─── Schemas for structured outputs ────────────────────────────────────────

LAYER_SCHEMA = {
    "name": "class_layer_batch",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "iri": {"type": "string"},
                        "layer": {"type": "string", "enum": ["A_alethic", "B_deontic", "AB_bridge"]},
                        "bfo_super": {
                            "type": "string",
                            "description": "Layer A 또는 AB일 때 BFO upper-level (예: Continuant, Occurrent, Quality, Role, Process). 그 외 빈 문자열",
                        },
                        "lkif_super": {
                            "type": "string",
                            "description": "Layer B 또는 AB일 때 LKIF-Core class (예: Norm, Obligation, Permission, Prohibition, Role, LegalDocument). 그 외 빈 문자열",
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["iri", "layer", "bfo_super", "lkif_super", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["assignments"],
        "additionalProperties": False,
    },
}

CQ_SCHEMA = {
    "name": "competency_questions",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "CQ-01 ~ CQ-50"},
                        "type": {"type": "string", "enum": ["alethic", "deontic", "bridge"]},
                        "category": {"type": "string", "description": "예: hazard_detection, norm_application, penalty_chain"},
                        "question_ko": {"type": "string"},
                        "expected_classes": {"type": "array", "items": {"type": "string"}},
                        "complexity": {"type": "string", "enum": ["basic", "intermediate", "advanced"]},
                    },
                    "required": ["id", "type", "category", "question_ko", "expected_classes", "complexity"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
}

REUSE_SCHEMA = {
    "name": "reuse_scorecard",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ontology": {"type": "string"},
                        "iri": {"type": "string"},
                        "scope": {"type": "string"},
                        "fit_score_0_10": {"type": "number"},
                        "covered_layers": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["A_alethic", "B_deontic", "bridge"]},
                        },
                        "recommended": {"type": "boolean"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["ontology", "iri", "scope", "fit_score_0_10", "covered_layers", "recommended", "rationale"],
                    "additionalProperties": False,
                },
            },
            "decision_summary": {"type": "string"},
        },
        "required": ["scores", "decision_summary"],
        "additionalProperties": False,
    },
}


# ─── LLM tasks ──────────────────────────────────────────────────────────────

LAYER_SYSTEM = """\
당신은 ontology engineer입니다. 우리 KOSHA 산업안전 ontology의 class를 2-layer 아키텍처로 자동 분류합니다.

Layer A (alethic, BFO 기반): 현실세계 객체/사건 — Photo, Equipment, Worker, Hazard, Process, RiskFeature 등
Layer B (deontic, LKIF-Core 기반): 법령 규범 — Article, NormStatement, Obligation, Modality, SubjectRole, Penalty 등
Layer AB (bridge): 두 layer를 연결 — observedIn, violatesObligation, appliesTo 같은 properties나 양면 class

각 class에 BFO super (Continuant/Occurrent/Quality/Role/Process)나 LKIF super (Norm/Obligation/LegalDocument/Role 등)를 매핑하세요.
"""

CQ_SYSTEM = """\
당신은 KOSHA 산업안전 ontology의 competency questions (CQs)을 생성합니다.

CQ는 ontology가 답해야 하는 자연어 질문 (한국어). SPARQL로 변환 가능해야 합니다.

3가지 type:
- alethic: 사실 추론 (예: "사진 X에서 어떤 hazard가 관찰되었는가?")
- deontic: 규범 추론 (예: "사업주가 추락방지 의무를 위반했을 때 어떤 벌칙이 적용되는가?")
- bridge: 두 layer 연결 (예: "사진 X의 작업 상황이 어떤 법령 의무를 위반하는가?")

basic (단순 lookup), intermediate (1-hop join), advanced (multi-hop + deontic chain) 균형있게.
"""

REUSE_SYSTEM = """\
KOSHA 산업안전 ontology를 위한 외부 표준 ontology 재사용 후보를 평가합니다.
각 후보의 적합도를 0-10 점수로 평가하고, 어느 layer (A/B/bridge)에 적용 가능한지 표시.
"""


async def assign_layers(client, model: str, classes: list[dict]) -> list[dict]:
    """62 class를 batch로 layer 분류."""
    batch_size = 20
    results: list[dict] = []
    for i in range(0, len(classes), batch_size):
        batch = classes[i : i + batch_size]
        user = "다음 class들을 2-layer로 분류:\n" + "\n".join(
            f"- {c['iri']} (label: {c.get('label_kor') or c['local']})" for c in batch
        )
        try:
            r = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "developer", "content": LAYER_SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_schema", "json_schema": LAYER_SCHEMA},
                max_completion_tokens=2048,
            )
            payload = json.loads(r.choices[0].message.content or "{}")
            results.extend(payload.get("assignments") or [])
            print(f"  layer batch {i + len(batch)}/{len(classes)}", flush=True)
        except Exception as exc:
            print(f"  layer batch {i} FAILED: {exc}", file=sys.stderr)
    return results


async def generate_cqs(
    client,
    model: str,
    classes: list[dict],
    swrl_summary: str,
    synthetic_sample: list[dict],
) -> list[dict]:
    class_list = "\n".join(
        f"- {c['iri']} ({c.get('label_kor') or c['local']})" for c in classes[:60]
    )
    syn_summary = json.dumps(
        [
            {
                "id": s.get("case_id"),
                "industry": s.get("industry_context"),
                "expected_risk": s.get("expected_primary_risk", "")[:80],
                "penalty_exposure": s.get("expected_pipeline_behavior", {}).get("penalty_exposure"),
            }
            for s in synthetic_sample[:5]
        ],
        ensure_ascii=False,
    )
    user = f"""\
[Ontology classes]
{class_list}

[SWRL Rules (seed patterns)]
{swrl_summary[:1500]}

[Synthetic case samples]
{syn_summary}

위 ontology가 답해야 할 CQ 50개 생성. alethic 20개, deontic 20개, bridge 10개. ID는 CQ-01~CQ-50.
"""
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": CQ_SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_schema", "json_schema": CQ_SCHEMA},
        max_completion_tokens=8192,
    )
    payload = json.loads(r.choices[0].message.content or "{}")
    return payload.get("questions") or []


async def score_reuse(client, model: str, classes: list[dict]) -> dict[str, Any]:
    class_summary = ", ".join(
        sorted({c["local"] for c in classes[:62]})
    )[:1500]
    candidates = [
        "BFO 2.0 (http://purl.obolibrary.org/obo/bfo.owl) — alethic upper-level (Continuant/Occurrent)",
        "LKIF-Core (http://www.estrellaproject.org/lkif-core/lkif-core.owl) — legal deontic (Obligation/Permission/Prohibition/Norm)",
        "RO Relation Ontology (http://purl.obolibrary.org/obo/ro.owl) — standardized relations",
        "PROV-O (http://www.w3.org/ns/prov) — provenance/lineage",
        "OccO Occupation Ontology (https://github.com/Occupation-Ontology/OccO) — O*Net-SOC occupations",
        "ENVO Environment Ontology (http://purl.obolibrary.org/obo/envo.owl) — workplace environment",
        "SSN/SOSA (http://www.w3.org/ns/sosa/) — sensor observation (photo as observation)",
    ]
    user = f"""\
KOSHA ontology class 요약: {class_summary}

각 후보 ontology를 평가:
{chr(10).join(f"- {c}" for c in candidates)}
"""
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": REUSE_SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_schema", "json_schema": REUSE_SCHEMA},
        max_completion_tokens=3072,
    )
    return json.loads(r.choices[0].message.content or "{}")


# ─── Main ──────────────────────────────────────────────────────────────────

async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    classes = extract_classes()
    if args.limit_classes:
        classes = classes[: args.limit_classes]
    print(f"Extracted {len(classes)} classes from {TBOX_PATH.name}")

    swrl_summary = load_swrl_summary()
    print(f"SWRL summary: {len(swrl_summary)} chars")

    synthetic_sample = load_synthetic_sample(n=5)
    print(f"Synthetic sample: {len(synthetic_sample)} cases")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    print("\n=== Task 1: Class → Layer assignment ===")
    layer_results = await assign_layers(client, args.model, classes)
    layer_counts = Counter(r.get("layer") for r in layer_results)
    print(f"  → {len(layer_results)} classes mapped, layer counts: {dict(layer_counts)}")
    layer_path = ARTIFACTS_DIR / "class_layer_assignment.json"
    layer_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "class_count": len(classes),
                "layer_counts": dict(layer_counts),
                "assignments": layer_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  saved: {layer_path}")

    print("\n=== Task 2: Competency Questions (50) ===")
    cqs = await generate_cqs(client, args.model, classes, swrl_summary, synthetic_sample)
    cq_type_counts = Counter(q.get("type") for q in cqs)
    print(f"  → {len(cqs)} CQs, type counts: {dict(cq_type_counts)}")
    cq_path = ARTIFACTS_DIR / "competency_questions.json"
    cq_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "type_counts": dict(cq_type_counts),
                "questions": cqs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  saved: {cq_path}")

    print("\n=== Task 3: Reuse Ontology Scorecard ===")
    reuse = await score_reuse(client, args.model, classes)
    print(f"  → {len(reuse.get('scores', []))} candidates scored")
    print(f"  decision: {reuse.get('decision_summary', '')[:200]}")
    reuse_path = ARTIFACTS_DIR / "reuse_ontology_scorecard.json"
    reuse_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                **reuse,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  saved: {reuse_path}")

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit-classes", type=int, default=None, help="처음 N개 class만 (디버그)")
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
