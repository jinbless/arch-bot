"""Compare backend catalog axes vs synthetic_observations distinct codes.

Output: missing codes that backend cannot normalize.
"""
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CATALOG = REPO / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
ALIASES = REPO / "serving-team/08-app/backend/app/data/risk_feature_aliases.json"
EVAL_DIR = REPO / "data-team/05-enrichment/eval-data"


def axis_codes(axis: str) -> set[str]:
    tax = json.loads(CATALOG.read_text(encoding="utf-8"))
    codes = set()
    for code, info in tax["axes"][axis]["codes"].items():
        codes.add(code)
        for sub in info.get("sub", []):
            codes.add(sub)
    return codes


def alias_codes(axis: str) -> set[str]:
    payload = json.loads(ALIASES.read_text(encoding="utf-8"))
    return set((payload.get("tier1") or {}).get(axis, {}).keys())


def synthetic_codes() -> dict[str, Counter[str]]:
    out: dict[str, Counter[str]] = {
        "accident_types": Counter(),
        "hazardous_agents": Counter(),
        "work_contexts": Counter(),
    }
    for f in sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ef = row.get("expected_features") or {}
            for field in ("accident_types", "hazardous_agents", "work_contexts"):
                for v in (ef.get(field) or []):
                    if v:
                        out[field][str(v).strip()] += 1
    return out


syn = synthetic_codes()
axis_map = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
}

for field, axis in axis_map.items():
    catalog = axis_codes(axis)
    aliases = alias_codes(axis)
    syn_codes = syn[field]
    missing = []
    for code, cnt in syn_codes.most_common():
        if code in catalog:
            continue
        if code in aliases:
            continue
        missing.append((code, cnt))
    print(f"\n=== {axis} ===")
    print(f"  catalog codes: {len(catalog)}")
    print(f"  alias keys: {len(aliases)}")
    print(f"  synthetic distinct: {len(syn_codes)}")
    print(f"  missing: {len(missing)}  (covered: {len(syn_codes) - len(missing)})")
    if missing:
        total_missing_occurrences = sum(c for _, c in missing)
        print(f"  occurrences of missing: {total_missing_occurrences}")
        print(f"  top 20 missing (code, freq):")
        for code, cnt in missing[:20]:
            print(f"    {cnt:4d}  {code}")
