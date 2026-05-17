#!/usr/bin/env python3
"""Phase E Step 4b — OntoClean violations 자동 수정 (LLM).

각 violation에 대해 LLM이 수정 전략 선택:
- LABEL_CORRECTION: meta-property label만 수정 (가장 안전, 구조 불변)
- RESTRUCTURE: TBox 변경 (super class 변경 또는 새 class 삽입)
- ACCEPT: justified — 위반이 의도된 경우 (예: legal artifact)

label 수정은 즉시 적용, restructure는 axiom patch 생성.
적용 후 재검증.

산출:
- ontoclean_meta_labels.json (업데이트)
- ontoclean_fix_audit.json (LLM 결정 + diff)
- (선택) kosha-ontology-v3-restructure-patch.ttl (TBox patch)
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
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
LABELS_PATH = ARTIFACTS_DIR / "ontoclean_meta_labels.json"
FIX_AUDIT_PATH = ARTIFACTS_DIR / "ontoclean_fix_audit.json"
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
RESTRUCTURE_PATCH = ONTOLOGY_DIR / "kosha-ontology-v3-restructure-patch.ttl"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "ontoclean_fix",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "violation_id": {"type": "string"},
            "fix_type": {
                "type": "string",
                "enum": ["LABEL_CORRECTION", "RESTRUCTURE", "ACCEPT"],
            },
            "target_class": {"type": "string", "description": "수정 대상 class IRI"},
            "field_to_update": {
                "type": "string",
                "enum": ["rigidity", "identity", "unity", "dependency", "subClassOf", "none"],
            },
            "new_value": {"type": "string", "description": "수정 후 새 값 (+R, -R, ~R, +I, -I, 새 super IRI 등)"},
            "old_value": {"type": "string"},
            "rationale": {"type": "string", "description": "한국어 1-2문장"},
            "restructure_axiom": {
                "type": "string",
                "description": "RESTRUCTURE인 경우 TTL axiom (예: 'class X rdfs:subClassOf Y .'). 그 외 빈 문자열",
            },
        },
        "required": ["violation_id", "fix_type", "target_class", "field_to_update", "new_value", "old_value", "rationale", "restructure_axiom"],
        "additionalProperties": False,
    },
}

SYSTEM = """\
당신은 OntoClean (Guarino & Welty 2002) 전문가입니다.
ontology의 OntoClean subsumption violation을 수정합니다.

각 violation에 대해 가장 적절한 수정 전략을 선택:

1. **LABEL_CORRECTION** (가장 선호): meta-property label이 잘못된 경우
   - 예: parent class가 실제로는 +I인데 -I로 labeled됨 → parent의 identity를 +I로 수정
   - 우리 도메인 (KOSHA 산업안전)에서 흔한 케이스:
     - umbrella class (예: RiskFeature, SanctionType)이 추상적이지만 실제로는 identity criteria가 있음
     - parent label을 +I/+R로 승격이 적합한 경우 많음

2. **RESTRUCTURE** (구조 변경): label 수정으로 해결 안 되는 진짜 design 결함
   - subclass를 다른 super 아래로 이동
   - 중간 abstract class 삽입
   - axiom으로 TTL patch 표현 (rdfs:subClassOf change)

3. **ACCEPT** (드물게): 위반이 도메인에 의도된 경우, justification

원칙:
- 우리 시스템은 법령 규범 기반이므로 deontic class는 LKIF-Core 의미 유지
- alethic class는 BFO 의미 유지
- 가능하면 LABEL_CORRECTION으로 (TBox 안정성)
"""


def load_labels() -> dict:
    if not LABELS_PATH.exists():
        raise FileNotFoundError(f"{LABELS_PATH} 없음. ontoclean_validator.py 먼저.")
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


async def fix_violation(client, model: str, violation: dict, labels_by_iri: dict, idx: int) -> dict:
    sub_iri = violation["sub"]
    sup_iri = violation["super"]
    sub_label = labels_by_iri.get(sub_iri, {})
    sup_label = labels_by_iri.get(sup_iri, {})
    user = f"""\
[Violation #{idx}]
Type: {violation['type']}
Subclass: {sub_iri}
  current labels: R={sub_label.get('rigidity')}, I={sub_label.get('identity')}, U={sub_label.get('unity')}, D={sub_label.get('dependency')}
  rationale: {sub_label.get('rationale', '')[:200]}

Superclass: {sup_iri}
  current labels: R={sup_label.get('rigidity')}, I={sup_label.get('identity')}, U={sup_label.get('unity')}, D={sup_label.get('dependency')}
  rationale: {sup_label.get('rationale', '')[:200]}

Description: {violation['description']}

위 violation에 대해 가장 적절한 수정 전략을 선택하고 적용 내용 명시.
"""
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
        max_completion_tokens=1024,
    )
    return json.loads(r.choices[0].message.content or "{}")


def apply_label_correction(labels_by_iri: dict, fix: dict) -> bool:
    """LABEL_CORRECTION을 labels dict에 적용."""
    if fix["fix_type"] != "LABEL_CORRECTION":
        return False
    target = fix["target_class"]
    field = fix["field_to_update"]
    new_value = fix["new_value"]
    if target not in labels_by_iri or field not in ("rigidity", "identity", "unity", "dependency"):
        return False
    labels_by_iri[target][field] = new_value
    return True


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    payload = load_labels()
    labels = payload.get("labels") or []
    violations = payload.get("violations") or []
    labels_by_iri = {l["iri"]: dict(l) for l in labels}
    print(f"Loaded {len(labels)} labels, {len(violations)} violations")
    if not violations:
        print("No violations to fix.")
        return 0

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(args.concurrency)

    async def _one(i, v):
        async with semaphore:
            return await fix_violation(client, args.model, v, labels_by_iri, i)

    fixes = await asyncio.gather(*[_one(i + 1, v) for i, v in enumerate(violations)])
    print(f"Generated {len(fixes)} fix proposals")

    # Apply LABEL_CORRECTION first
    applied_label = 0
    restructure_axioms = []
    accepted = 0
    fix_counts = Counter(f.get("fix_type") for f in fixes)
    print(f"Fix types: {dict(fix_counts)}")

    for fix in fixes:
        if fix.get("fix_type") == "LABEL_CORRECTION":
            if apply_label_correction(labels_by_iri, fix):
                applied_label += 1
        elif fix.get("fix_type") == "RESTRUCTURE":
            ax = fix.get("restructure_axiom", "").strip()
            if ax:
                restructure_axioms.append({"axiom": ax, "for": fix["violation_id"], "target": fix["target_class"]})
        elif fix.get("fix_type") == "ACCEPT":
            accepted += 1

    print(f"Applied: LABEL_CORRECTION={applied_label}, RESTRUCTURE patches={len(restructure_axioms)}, ACCEPT={accepted}")

    # Re-check violations
    updated_labels = list(labels_by_iri.values())
    sys.path.insert(0, str(Path(__file__).parent))
    from ontoclean_validator import detect_violations, build_subclass_map  # type: ignore

    subclass_map = build_subclass_map()
    new_violations = detect_violations(updated_labels, subclass_map)
    print(f"\nAfter fix: {len(new_violations)} violations remaining (was {len(violations)})")

    # Re-counts
    cnt_r = Counter(l.get("rigidity") for l in updated_labels)
    cnt_i = Counter(l.get("identity") for l in updated_labels)
    print(f"Rigidity: {dict(cnt_r)}")
    print(f"Identity: {dict(cnt_i)}")

    # Save updated labels
    LABELS_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "class_count": len(updated_labels),
                "rigidity_counts": dict(cnt_r),
                "identity_counts": dict(cnt_i),
                "violations_count": len(new_violations),
                "violations": new_violations,
                "labels": updated_labels,
                "fixes_applied": {
                    "label_correction": applied_label,
                    "restructure": len(restructure_axioms),
                    "accept": accepted,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved updated labels: {LABELS_PATH.relative_to(REPO_ROOT)}")

    FIX_AUDIT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "violations_before": len(violations),
                "violations_after": len(new_violations),
                "fix_counts": dict(fix_counts),
                "fixes": fixes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved fix audit: {FIX_AUDIT_PATH.relative_to(REPO_ROOT)}")

    if restructure_axioms:
        patch_lines = [
            "# kosha-ontology-v3 restructure patch (Phase E Step 4b)",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix core: <https://cashtoss.info/ontology#> .",
            "",
        ]
        for r in restructure_axioms:
            patch_lines.append(f"# fix for {r['for']} target={r['target']}")
            patch_lines.append(r["axiom"])
            patch_lines.append("")
        RESTRUCTURE_PATCH.write_text("\n".join(patch_lines), encoding="utf-8")
        print(f"Saved restructure patch: {RESTRUCTURE_PATCH.relative_to(REPO_ROOT)}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--concurrency", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
