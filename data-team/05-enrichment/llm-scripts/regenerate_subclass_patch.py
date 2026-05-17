#!/usr/bin/env python3
"""Regenerate kosha-ontology-v3-subclass-patch.ttl from catalog v4's 'sub' field.

apply_phase3b.py 재실행 시 sub_codes 누락 버그 우회.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
OUT = ROOT / "ontology-team/06-reasoning/ontology/kosha-ontology-v3-subclass-patch.ttl"

PREFIX_MAP = {
    "accident_type": "hazard",
    "hazardous_agent": "agent",
    "work_context": "context",
}


def main():
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    lines = [
        "# Phase 3B subclass hierarchy patch — auto-generated from risk_feature_catalog.json",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix hazard: <https://cashtoss.info/ontology/risk/hazard#> .",
        "@prefix agent: <https://cashtoss.info/ontology/risk/agent#> .",
        "@prefix context: <https://cashtoss.info/ontology/risk/context#> .",
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
                lines.append(f"{prefix}:{sub} a owl:Class ; rdfs:subClassOf {prefix}:{code} .")
                count += 1
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {count} subClassOf statements -> {OUT.name}")


if __name__ == "__main__":
    main()
