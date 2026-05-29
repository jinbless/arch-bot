#!/usr/bin/env python3
"""코드 어휘 정합성 전수조사 — catalog ↔ hazard_seed ↔ aliases ↔ PG ↔ ontology.

3축(accident_type/hazardous_agent/work_context) 코드가 surface별로 같은 어휘를
쓰는지 감사. "hazard 매핑이 SR에 없는 코드를 써서 결과가 빈다"류 갭을 전부 찾는다.

사용: PYTHONIOENCODING=utf-8 python scripts/audit_code_consistency.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "serving-team/08-app/backend/app/data"
ONT = REPO / "ontology-team/06-reasoning/ontology"
ART = REPO / "data-team/05-enrichment/runtime-artifacts"
PG = "dbname=kosha user=kosha password=1229 host=localhost"

AXES = ["accident_type", "hazardous_agent", "work_context"]
NS = {"haz": "accident_type", "agent": "hazardous_agent", "ctx": "work_context"}
ONT_CLASSES = {  # 코드가 아닌 TBox 클래스/속성 토큰 — 제외
    "Hazard", "AccidentType", "HazardousAgent", "WorkContext", "RiskFeature",
    "NaturalLanguageHazardCategory", "Agent", "Context",
}


def _codes_from_node(node) -> set[str]:
    if isinstance(node, dict):
        return set(node.keys())
    if isinstance(node, list):
        return set((c.get("code") if isinstance(c, dict) else c) for c in node)
    return set()


def load_catalog() -> dict[str, set[str]]:
    cat = json.load(open(DATA / "risk_feature_catalog.json", encoding="utf-8"))
    axes = cat.get("axes", cat)
    return {a: _codes_from_node(axes.get(a, {}).get("codes")) for a in AXES}


def load_seed() -> dict[str, set[str]]:
    out = {a: set() for a in AXES}
    p = ART / "hazard_name_seed.json"
    if p.exists():
        for m in json.load(open(p, encoding="utf-8")).get("mappings", []):
            if m.get("axis") in out and m.get("code"):
                out[m["axis"]].add(m["code"])
    return out


def load_aliases() -> dict[str, set[str]]:
    out = {a: set() for a in AXES}
    for fn in ("risk_feature_aliases.json", "risk_feature_aliases_candidates.json"):
        p = DATA / fn
        if not p.exists():
            continue
        al = json.load(open(p, encoding="utf-8"))

        def _add(axis, code):
            if axis not in out or not code:
                return
            if isinstance(code, str):
                out[axis].add(code)
            elif isinstance(code, list):
                out[axis].update(c for c in code if isinstance(c, str))

        for a in AXES:
            for _alias, code in (al.get("tier1", {}).get(a, {}) or {}).items():
                _add(a, code)
        for e in al.get("tier2", []) or []:
            if isinstance(e, dict):
                _add(e.get("axis"), e.get("code"))
    return out


def pg_codes() -> dict[str, dict[str, set[str]]]:
    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    col = {"accident_type": "accident_types", "hazardous_agent": "hazardous_agents", "work_context": "work_contexts"}
    res: dict[str, dict[str, set[str]]] = {}
    for table in ("safety_requirements", "checklist_items"):
        res[table] = {}
        for a, c in col.items():
            cur.execute(
                f"SELECT DISTINCT jsonb_array_elements_text({c}) FROM {table} WHERE {c} IS NOT NULL"
            )
            res[table][a] = set(r[0] for r in cur.fetchall())
    res["guide_feat_GUIDE"] = {}
    for a in AXES:
        cur.execute(
            "SELECT DISTINCT feature_code FROM guide_entity_feature_candidates "
            "WHERE entity_type='GUIDE' AND axis=%s",
            (a,),
        )
        res["guide_feat_GUIDE"][a] = set(r[0] for r in cur.fetchall())
    conn.close()
    return res


def ontology_codes() -> dict[str, set[str]]:
    out = {a: set() for a in AXES}
    pat = re.compile(r"\b(haz|agent|ctx):([A-Za-z][A-Za-z0-9_]*)")
    for fn in ("kosha-instances.ttl", "kosha-instances-hazard-direct.ttl",
               "kosha-instances-guide-hazard.ttl"):
        p = ONT / fn
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                for m in pat.finditer(line):
                    ns, code = m.group(1), m.group(2)
                    if code in ONT_CLASSES:
                        continue
                    out[NS[ns]].add(code)
    return out


def _is_snake(c: str) -> bool:
    return c == c.upper()


def show(title: str, s: set[str], limit: int = 40) -> None:
    items = sorted(s)
    extra = "" if len(items) <= limit else f" … (+{len(items)-limit})"
    print(f"  {title} [{len(items)}]: {', '.join(items[:limit])}{extra}")


def main() -> None:
    cat = load_catalog()
    seed = load_seed()
    alias = load_aliases()
    pg = pg_codes()
    ont = ontology_codes()
    sr, ci, gf = pg["safety_requirements"], pg["checklist_items"], pg["guide_feat_GUIDE"]

    print("=== 코드 수 요약 (axis: catalog / SR / CI / GUIDEfeat / ontology) ===")
    for a in AXES:
        print(f"  {a:16} cat={len(cat[a]):4} SR={len(sr[a]):4} CI={len(ci[a]):4} "
              f"GUIDE={len(gf[a]):4} ont={len(ont[a]):4} seed={len(seed[a])} alias={len(alias[a])}")

    for a in AXES:
        print(f"\n========== AXIS: {a} ==========")
        print("[1] hazard_seed 코드 중 SR 커버리지 0 (→ 분석 시 Guide/CI 빈값):")
        show("seed - SR", seed[a] - sr[a])
        print("[2] catalog 코드 중 SR에 없음 (조회 불가능한 코드):")
        show("catalog - SR", cat[a] - sr[a])
        print("[3] SR 코드 중 catalog에 없음 (rogue/미등록):")
        show("SR - catalog", sr[a] - cat[a])
        print("[4] CI vs SR 어휘 불일치:")
        show("CI - SR", ci[a] - sr[a])
        show("SR - CI", sr[a] - ci[a])
        print("[5] GUIDE feature 코드 중 SR에 없음 (hazard-direct 빈 결과):")
        show("GUIDEfeat - SR", gf[a] - sr[a])
        print("[6] 온톨로지 코드 vs catalog:")
        camel = {c for c in ont[a] if not _is_snake(c)}
        show("ontology CamelCase(비-UPPER_SNAKE)", camel)
        show("ontology - catalog (catalog에 없는 온톨로지 코드)", ont[a] - cat[a])
        show("catalog - ontology (온톨로지에 없는 catalog 코드)", cat[a] - ont[a])
        print("[7] 온톨로지 코드 vs PG SR:")
        show("ontology - SR", ont[a] - sr[a])
        show("SR - ontology", sr[a] - ont[a])

    print("\n=== alias 타깃 코드 중 catalog에 없음 (깨진 alias) ===")
    for a in AXES:
        show(a, alias[a] - cat[a])


if __name__ == "__main__":
    main()
