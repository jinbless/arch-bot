#!/usr/bin/env python3
"""데이터 적재 커버리지 검출 — "스키마는 있는데 데이터(인스턴스)가 없는" 요소를 상시 탐지.

동기(2026-05-31): F5/SHE 케이스 — she:SituationalHazardPattern 클래스 + she:hasPPEState 등
property는 TBox에 정의됐으나 ABox 인스턴스/사용이 0이었다(데이터팀 TTL에만 있고 온톨로지 미적재).
이런 "데이터 미적재 갭"을 사람이 top-down으로 우연히 찾는 대신 **자동·반복 검출**한다.

catalog(gen_catalog)는 대용량 ABox를 제외하므로 인스턴스/사용 카운트가 부정확 → 본 도구는
**manifest 비-archive 전체 union(956K+ ABox 포함)**을 로드해 정확히 집계한다(수 분 소요).

검출(triage 후보 — 하드 게이트 아님, 사람이 판정):
  (A) 빈 클래스: project 클래스인데 자기+하위 subtree에 인스턴스 0
       제외: punned(class+individual 동시, facet canonical 설계) · app:(요청시 생성 runtime 모델)
  (B) dormant property: project property인데 predicate 사용 0
       주석: rule-head(추론/물질화 시점 생성) 후보는 별도 표시

각 항목은 "데이터 미적재(SHE형)" / "추상·런타임(정상)" / "dead 스키마(폐지 후보)" 중 하나 —
판정은 사람 몫. PG↔온톨로지 대사(별도)와 함께 쓰면 완전.

사용: python scripts/check_data_coverage.py
순수 조회 — 파일 미수정. 종료코드 0(항상; 진단용).
"""
from __future__ import annotations
import sys
from collections import defaultdict, Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef

ONT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ONT / "assembly"))
import manifest_source as MS  # noqa: E402

PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#", "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#", "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#", "sr": "https://cashtoss.info/ontology/sr#",
    "pen": "https://cashtoss.info/ontology/penalty#", "law": "https://cashtoss.info/ontology/law#",
    "guide": "https://cashtoss.info/ontology/guide#", "core": "https://cashtoss.info/ontology#",
    "app": "https://cashtoss.info/ontology/app#", "industry": "https://cashtoss.info/ontology/industry#",
    "bridge": "https://cashtoss.info/ontology/bridge#", "actor": "https://cashtoss.info/ontology/actor#",
}
PROJ = tuple(PREFIXES.values())
_REV = sorted(PREFIXES.items(), key=lambda kv: -len(kv[1]))
# rule-head/추론·물질화 시점 생성 property (static 0이 정상) — 주석용
RULE_HEAD = {"core:exemptedBy", "core:coApplicable", "core:dependsOn", "core:hasViolation",
             "bridge:violatesObligation", "bridge:appliesTo", "bridge:observedIn",
             "haz:hasHazard", "pen:hasPenaltyRule"}


def short(u) -> str:
    s = str(u)
    for p, ns in _REV:
        if s.startswith(ns):
            return f"{p}:{s[len(ns):]}"
    return s


def is_proj(u) -> bool:
    return isinstance(u, URIRef) and str(u).startswith(PROJ)


def load_union() -> Graph:
    g = Graph(); seen = set()
    for e in MS.ENTRIES:
        if e["role"] == "archive" or e["file"] in seen:
            continue
        seen.add(e["file"]); p = ONT / e["file"]
        if not p.exists():
            continue
        try:
            g.parse(str(p), format=("xml" if e["format"] == "xml" else "turtle"))
        except Exception as ex:  # noqa: BLE001
            print(f"  [skip] {e['file']}: {ex}", file=sys.stderr)
    return g


def main() -> int:
    print("로딩 중 (전체 ABox 포함, 수 분)...", file=sys.stderr)
    g = load_union()
    print(f"로드 {len(g):,} triples\n", file=sys.stderr)

    classes = {c for c in g.subjects(RDF.type, OWL.Class) if is_proj(c)}
    individuals = {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if is_proj(s)}
    obj_props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if is_proj(p)}
    dat_props = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if is_proj(p)}

    # 직접 인스턴스 수 (rdf:type C)
    direct_inst = Counter()
    for _, o in g.subject_objects(RDF.type):
        if o in classes:
            direct_inst[o] += 1
    # 하위 클래스 맵 (subtree 합산용)
    children = defaultdict(list)
    for c in classes:
        for sup in g.objects(c, RDFS.subClassOf):
            if sup in classes:
                children[sup].append(c)

    def subtree_inst(c, seen=None):
        seen = seen or set()
        if c in seen:
            return 0
        seen.add(c)
        return direct_inst.get(c, 0) + sum(subtree_inst(k, seen) for k in children.get(c, []))

    # (A) 빈 클래스: subtree 인스턴스 0, punned 제외
    empty = []
    for c in classes:
        if c in individuals:      # punned (facet canonical 설계) 제외
            continue
        if subtree_inst(c) == 0:
            empty.append(c)
    # app: 는 runtime 모델이라 0이 정상 → 분리
    empty_app = sorted([c for c in empty if str(c).startswith(PREFIXES["app"])], key=short)
    empty_other = sorted([c for c in empty if not str(c).startswith(PREFIXES["app"])], key=short)

    # (B) dormant property: predicate 사용 0
    pred_use = Counter()
    for _, p, _ in g:
        if p in obj_props or p in dat_props:
            pred_use[p] += 1
    dormant_obj = sorted([p for p in obj_props if pred_use.get(p, 0) == 0], key=short)
    dormant_dat = sorted([p for p in dat_props if pred_use.get(p, 0) == 0], key=short)

    print("=" * 78)
    print("데이터 적재 커버리지 — '스키마 있으나 데이터 0' 검출 (triage 후보)")
    print("=" * 78)

    print(f"\n## (A) 빈 클래스 (subtree 인스턴스 0, punned 제외): "
          f"{len(empty_other)} + app:{len(empty_app)}")
    byns = defaultdict(list)
    for c in empty_other:
        byns[short(c).split(":")[0]].append(short(c))
    for ns in sorted(byns):
        lst = byns[ns]
        print(f"  [{ns}] {len(lst)}: " + ", ".join(lst[:25]) + (" …" if len(lst) > 25 else ""))
    if empty_app:
        print(f"  [app] {len(empty_app)} (요청시 생성 runtime 모델 — 0 정상): "
              + ", ".join(empty_app[:12]) + (" …" if len(empty_app) > 12 else ""))

    # dormant 분류: app(runtime) / rule-head / 그외(triage 우선)
    def bucket(props):
        app_, rh, other = [], [], []
        for p in props:
            if str(p).startswith(PREFIXES["app"]):
                app_.append(p)
            elif short(p) in RULE_HEAD:
                rh.append(p)
            else:
                other.append(p)
        return app_, rh, other
    o_app, o_rh, o_other = bucket(dormant_obj)
    d_app, d_rh, d_other = bucket(dormant_dat)
    print(f"\n## (B) dormant property (predicate 사용 0): obj {len(dormant_obj)} / data {len(dormant_dat)}")
    print(f"  ▸ 우선 triage(app/rule-head 제외) — obj {len(o_other)} / data {len(d_other)}:")
    if o_other:
        print("      object: " + ", ".join(short(p) for p in o_other))
    if d_other:
        print("      data  : " + ", ".join(short(p) for p in d_other))
    print(f"  ▸ app:(요청시 생성 runtime — 0 정상): obj {len(o_app)} / data {len(d_app)}")
    print(f"  ▸ rule-head/물질화(추론·on-demand — 0 정상): {', '.join(short(p) for p in o_rh + d_rh)}")

    # 헤드라인: facet fine(haz/agent/ctx) 제외한 구조적 빈 클래스 = 우선 triage
    facet_fine = [c for c in empty_other if str(c).startswith((PREFIXES["haz"], PREFIXES["agent"], PREFIXES["ctx"]))]
    structural = [c for c in empty_other if c not in set(facet_fine)]
    print("\n" + "=" * 78)
    print(f"🎯 우선 triage 후보 (known 카테고리 제외):")
    print(f"   · 구조적 빈 클래스(facet fine·app 제외): {len(structural)} — "
          + ", ".join(short(c) for c in structural[:20]) + (" …" if len(structural) > 20 else ""))
    print(f"   · dormant property(app·rule-head 제외): obj {len(o_other)} / data {len(d_other)}")
    print(f"   · [참고] facet fine 코드(haz/agent/ctx, prune 정책 항목): {len(facet_fine)}")
    print("\n── 판정 가이드 ──")
    print("  · 우선 triage 항목이 데이터팀 PG/jsonl/TTL엔 있나? → 있으면 미적재 갭(SHE형, 통합 대상)")
    print("  · PG 물질화(Incompatibility/GuideUsageProfile/penalty 등)·app runtime·rule-head = static 0 정상")
    print("  · 어디에도 데이터 없고 용도 불명 → dead 스키마(폐지 후보). PG↔온톨로지 대사와 병용 권장.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
