#!/usr/bin/env python3
"""Phase 4-B Stage 2 — KOSHA-22 62개 NamedIndividual TBox 패치 생성 (SSOT 파생).

shared/reference SSOT의 3축 정본(accident 23/agent 10/work_context 29)을 CamelCase IRI로
NamedIndividual 정의. 멱등(기존과 동일 triple은 RDF dedup). accident 한글 라벨은 KOSHA-22 reference.
출력: kosha-ontology-v4-kosha22-vocab-patch.ttl
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shared" / "reference"))
sys.path.insert(0, str(ROOT / "serving-team" / "08-app" / "backend"))
import canonical_vocab as cv
from app.integrations.code_iri_mapper import _camel, _AXIS_PREFIX

OUT = Path(__file__).resolve().parents[1] / "kosha-ontology-v4-kosha22-vocab-patch.ttl"
KREF = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "kosha_reference_parsed.json"

AXIS_CLASS = {
    "accident_type": "haz:AccidentType",
    "hazardous_agent": "agent:HazardousAgent",
    "work_context": "ctx:WorkContext",
}
# TTL @prefix 라벨 (URI는 code_iri_mapper와 동일; 라벨만 haz/ctx로).
TTL_PREFIX = {"accident_type": "haz", "hazardous_agent": "agent", "work_context": "ctx"}


def de_camel(frag: str) -> str:
    out = []
    for i, ch in enumerate(frag):
        if ch.isupper() and i > 0:
            out.append(" ")
        out.append(ch)
    return "".join(out)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main() -> int:
    # accident 한글 라벨 (en_suggested → ko)
    ko_label: dict[str, str] = {}
    try:
        kref = json.loads(KREF.read_text(encoding="utf-8"))
        for a in (kref.get("accident_types_22") or []):
            en, ko = a.get("en_suggested"), a.get("ko")
            if en and ko:
                ko_label[en] = ko
    except Exception as e:  # noqa: BLE001
        print(f"[warn] KOSHA ref 라벨 로드 실패: {e}", file=sys.stderr)

    lines = [
        "# Phase 4-B Stage 2 — KOSHA-22 정본 어휘 NamedIndividual (SSOT 파생, gen_kosha22_vocab_patch.py)",
        "# accident 23 + hazardous_agent 10 + work_context 29 = 62. CamelCase IRI = code_iri_mapper._camel.",
        "@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "",
    ]
    n = 0
    for axis in ("accident_type", "hazardous_agent", "work_context"):
        cls = AXIS_CLASS[axis]
        prefix = TTL_PREFIX[axis]
        lines.append(f"# === {axis} ({len(cv.canonical_set(axis))}) ===")
        for code in sorted(cv.canonical_set(axis)):
            frag = _camel(code)
            en = de_camel(frag)
            label = f'rdfs:label "{esc(en)}"@en'
            if axis == "accident_type" and code in ko_label:
                label += f',\n        "{esc(ko_label[code])}"@ko'
            lines.append(f"{prefix}:{frag} a owl:NamedIndividual,\n        {cls} ;\n    {label} .")
            lines.append("")
            n += 1
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"생성: {OUT.name} — {n}개 개체 (accident 23 + agent 10 + wc 29)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
