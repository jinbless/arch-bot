#!/usr/bin/env python3
"""[DEPRECATED — P3] facet 계층은 scripts/gen_facet_taxonomy.py(vocab rollup SSOT)로 대체됨.

이 스크립트가 만드는 kosha-ontology-v3-subclass-patch.ttl은 archive(manifest)로 이동했고
어떤 소비자도 로드하지 않는다. catalog `sub`는 불완전(canonical 미도달 다수·work_context 계층 부재,
진단: scripts/diff_facet_sources.py)이라 은퇴. 재생성 금지 — 실행 시 archive 파일만 덮어쓴다.

(원래 목적) Regenerate kosha-ontology-v3-subclass-patch.ttl from catalog v4's 'sub' field.

apply_phase3b.py 재실행 시 sub_codes 누락 버그 우회.

IRI casing 규칙 (axis별 — 온톨로지 개체명 convention; to_iri_name() 참고):
  - accident_type → 코드 그대로 UPPER (KOSHA-22 공식 코드, 예: haz:FALL / haz:SLIP)
  - hazardous_agent / work_context → 우리 taxonomy → PascalCase (예: agent:Chemical, agent:HeatCold)
  catalog 'sub'/'code'는 전부 UPPER_SNAKE이므로 emit 시 변환한다.
  (이 변환을 빠뜨리면 agent:DUST 가 나와 live 개체 agent:Dust 와 단절된다 — 2026-05-30 회귀 방지.)
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
OUT = ROOT / "ontology-team/06-reasoning/ontology/kosha-ontology-v3-subclass-patch.ttl"

PREFIX_MAP = {
    "accident_type": "haz",
    "hazardous_agent": "agent",
    "work_context": "ctx",
}


def to_iri_name(axis: str, code: str) -> str:
    """catalog 코드(UPPER_SNAKE) → 온톨로지 IRI 개체명. axis별 convention."""
    if axis == "accident_type":
        return code  # KOSHA-22 공식 코드는 UPPER 유지 (haz:FALL)
    return "".join(w.capitalize() for w in code.split("_"))  # taxonomy = PascalCase (agent:Chemical)


def main():
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    lines = [
        "# Phase 3B subclass hierarchy patch — auto-generated from risk_feature_catalog.json",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix ctx: <https://cashtoss.info/ontology/risk/context#> .",
        "",
    ]
    count = 0
    for axis, info in cat.get("axes", {}).items():
        prefix = PREFIX_MAP.get(axis)
        if not prefix:
            continue
        for code, code_info in (info.get("codes") or {}).items():
            subs = code_info.get("sub") or []
            if not subs:
                continue
            for sub in subs:
                lines.append(
                    f"{prefix}:{to_iri_name(axis, sub)} a owl:Class ; "
                    f"rdfs:subClassOf {prefix}:{to_iri_name(axis, code)} .")
                count += 1
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {count} subClassOf statements -> {OUT.name}")


if __name__ == "__main__":
    import sys as _s
    _s.exit("[DEPRECATED P3] scripts/gen_facet_taxonomy.py로 대체됨. 이 스크립트는 archive 파일을 "
            "덮어쓰므로 실행 금지. (강제 실행 필요 시 main() 직접 호출)")
