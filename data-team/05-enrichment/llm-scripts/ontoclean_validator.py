#!/usr/bin/env python3
"""Phase E Step 4 — OntoClean 자동 검증 (LLM).

각 class의 OntoClean meta-property 자동 라벨링:
- Rigidity (+R/-R/~R): 모든 instance가 항상 그 class인가?
- Identity (+I/-I): identity criteria 가지는가?
- Unity (+U/-U): wholeness 가지는가?
- Dependency (+D/-D): 다른 class에 존재 의존하는가?

OntoClean subsumption rule 위반 자동 탐지:
- A ⊑ B + A is +R + B is -R → 위반 (Person ⊑ Role 같은 흔한 오류)
- A ⊑ B + A is +I + B is -I → 위반
- 등등

산출:
- ontoclean_meta_labels.json
- ontoclean_report.md
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
TBOX_PATH = ONTOLOGY_DIR / "kosha-ontology-v2.owl"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LABELS_PATH = ARTIFACTS_DIR / "ontoclean_meta_labels.json"
REPORT_PATH = ARTIFACTS_DIR / "ontoclean_report.md"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "ontoclean_labels",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "labels": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "iri": {"type": "string"},
                        "rigidity": {"type": "string", "enum": ["+R", "-R", "~R"]},
                        "identity": {"type": "string", "enum": ["+I", "-I", "+O"]},
                        "unity": {"type": "string", "enum": ["+U", "-U", "~U"]},
                        "dependency": {"type": "string", "enum": ["+D", "-D"]},
                        "rationale": {"type": "string"},
                    },
                    "required": ["iri", "rigidity", "identity", "unity", "dependency", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["labels"],
        "additionalProperties": False,
    },
}

SYSTEM = """\
당신은 OntoClean (Guarino & Welty 2002) 전문가입니다. 각 OWL class에 4개 meta-property를 자동 라벨링합니다.

Meta-properties:
- Rigidity (+R/-R/~R): +R = 모든 instance가 항상 그 class (Person, Hazard). -R = 일부만 일시적 (Student, DutyHolder). ~R = anti-rigid (모든 instance가 결국 그 class가 아닐 수 있음)
- Identity (+I/-I/+O): +I = own identity criteria (Person, Photo). -I = inherit from super. +O = supply criteria to subclasses
- Unity (+U/-U/~U): +U = whole가 명확 (Person, Document). -U = collection (Group)
- Dependency (+D/-D): +D = 다른 class에 존재 의존 (Role depends on Person)

OntoClean rule: 같은 meta-property 안에서 subsumption은 더 specific해야. 예: +R class는 -R class subclass일 수 없음.
"""


def load_class_assignments() -> list[dict]:
    p = ARTIFACTS_DIR / "class_layer_assignment.json"
    if not p.exists():
        return []
    return (json.loads(p.read_text(encoding="utf-8")).get("assignments") or [])


async def label_batch(
    client,
    model: str,
    classes: list[dict],
    skip_iris: set[str] | None = None,
    batch_size: int = 6,
    max_tokens: int = 4096,
) -> list[dict]:
    skip_iris = skip_iris or set()
    targets = [c for c in classes if c.get("iri") not in skip_iris]
    print(f"  Labeling {len(targets)} new classes (skipping {len(classes) - len(targets)} already-labeled)")
    results = []
    for i in range(0, len(targets), batch_size):
        batch = targets[i : i + batch_size]
        user = "다음 class들의 OntoClean meta-property 라벨링:\n" + "\n".join(
            f"- {c['iri']} (layer={c.get('layer', '?')})" for c in batch
        )
        try:
            r = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "developer", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_schema", "json_schema": SCHEMA},
                max_completion_tokens=max_tokens,
            )
            payload = json.loads(r.choices[0].message.content or "{}")
            results.extend(payload.get("labels") or [])
            print(f"  ontoclean batch {i + len(batch)}/{len(targets)}", flush=True)
        except Exception as exc:
            print(f"  batch {i} FAILED: {exc}", file=sys.stderr)
    return results


def detect_violations(labels: list[dict], subclass_map: dict[str, list[str]]) -> list[dict]:
    """Subsumption violation 자동 탐지.

    Rule R1: anti-rigid (~R) ⊉ rigid (+R)
    Rule R2: +I cannot be subClassOf -I (identity 손실)
    """
    iri_to_label = {l["iri"]: l for l in labels}
    violations = []
    for sub_iri, supers in subclass_map.items():
        sub = iri_to_label.get(sub_iri)
        if not sub:
            continue
        for sup_iri in supers:
            sup = iri_to_label.get(sup_iri)
            if not sup:
                continue
            # Rigidity violation
            if sub["rigidity"] == "+R" and sup["rigidity"] == "~R":
                violations.append(
                    {
                        "type": "rigidity",
                        "sub": sub_iri,
                        "super": sup_iri,
                        "description": f"+R '{sub_iri}' subClassOf ~R '{sup_iri}' (rigid subclass of anti-rigid)",
                    }
                )
            # Identity violation
            if sub["identity"] == "+I" and sup["identity"] == "-I":
                violations.append(
                    {
                        "type": "identity",
                        "sub": sub_iri,
                        "super": sup_iri,
                        "description": f"+I '{sub_iri}' subClassOf -I '{sup_iri}' (identity supply mismatch)",
                    }
                )
    return violations


def build_subclass_map() -> dict[str, list[str]]:
    from rdflib import Graph, RDFS, URIRef

    g = Graph()
    g.parse(str(TBOX_PATH), format="xml")
    out: dict[str, list[str]] = {}
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            out.setdefault(str(s), []).append(str(o))
    return out


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    classes = load_class_assignments()
    if args.limit:
        classes = classes[: args.limit]
    print(f"Classes to label: {len(classes)}")

    existing_labels: list[dict] = []
    skip_iris: set[str] = set()
    if args.resume and LABELS_PATH.exists():
        prev = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        existing_labels = prev.get("labels") or []
        skip_iris = {l.get("iri") for l in existing_labels if l.get("iri")}
        print(f"Resume mode: {len(existing_labels)} already labeled, will skip")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    new_labels = await label_batch(client, args.model, classes, skip_iris=skip_iris)
    labels = existing_labels + new_labels
    print(f"\nLabeled (new {len(new_labels)} + existing {len(existing_labels)}) = {len(labels)} total")

    # Counts
    cnt_r = Counter(l.get("rigidity") for l in labels)
    cnt_i = Counter(l.get("identity") for l in labels)
    print(f"Rigidity: {dict(cnt_r)}")
    print(f"Identity: {dict(cnt_i)}")

    # Subsumption check
    subclass_map = build_subclass_map()
    violations = detect_violations(labels, subclass_map)
    print(f"\nSubsumption violations: {len(violations)}")
    for v in violations[:10]:
        print(f"  [{v['type']}] {v['description']}")

    # Save labels
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "class_count": len(labels),
                "rigidity_counts": dict(cnt_r),
                "identity_counts": dict(cnt_i),
                "violations_count": len(violations),
                "violations": violations,
                "labels": labels,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {LABELS_PATH.relative_to(REPO_ROOT)}")

    # Markdown report
    md = ["# OntoClean Report", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    md.append(f"## Summary")
    md.append(f"- Classes labeled: {len(labels)}")
    md.append(f"- Rigidity: {dict(cnt_r)}")
    md.append(f"- Identity: {dict(cnt_i)}")
    md.append(f"- **Subsumption violations: {len(violations)}**")
    md.append("")
    md.append("## Violations")
    for v in violations:
        md.append(f"- [{v['type']}] {v['description']}")
    md.append("")
    md.append("## Sample labels (first 20)")
    for l in labels[:20]:
        md.append(f"- `{l['iri'].rsplit('#', 1)[-1]}`: {l['rigidity']} {l['identity']} {l['unity']} {l['dependency']} — {l['rationale'][:100]}")
    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"Saved report: {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="기존 labeled iris skip + 누락만 처리")
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
