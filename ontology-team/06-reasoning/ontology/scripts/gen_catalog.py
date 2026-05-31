#!/usr/bin/env python3
"""온톨로지 카탈로그 생성 — 전체 class/property를 1개 Markdown으로 통독 + 자동 이상징후 점검.

'전체 그림을 한 눈에' 보고 '어디가 잘못됐는지' 짚기 위한 도구. top-level .ttl/.owl(대용량
kosha-instances.ttl 제외)을 머지해:
  1) 모듈(prefix) 개요  2) 클래스 계층 트리(label·하위수·피참조수)  3) 속성(domain/range)
  4) ⚠️ 자동 이상징후(floating/label누락/dead후보/중복label/domain·range누락/punning)
산출: ../CATALOG.md (AUTO-GENERATED, 수동편집 금지 — 본 스크립트를 고친다).
"""
from __future__ import annotations
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal
from rdflib.namespace import split_uri

ONT = Path(__file__).resolve().parents[1]
OUT = ONT / "CATALOG.md"
BIG_ABOX = "kosha-instances.ttl"

PREFIXES = {
    "risk": "https://cashtoss.info/ontology/risk#",
    "haz": "https://cashtoss.info/ontology/risk/hazard#",
    "agent": "https://cashtoss.info/ontology/risk/agent#",
    "ctx": "https://cashtoss.info/ontology/risk/context#",
    "she": "https://cashtoss.info/ontology/risk/situation#",
    "sr": "https://cashtoss.info/ontology/sr#",
    "pen": "https://cashtoss.info/ontology/penalty#",
    "law": "https://cashtoss.info/ontology/law#",
    "guide": "https://cashtoss.info/ontology/guide#",
    "core": "https://cashtoss.info/ontology#",
    "app": "https://cashtoss.info/ontology/app#",
    "industry": "https://cashtoss.info/ontology/industry#",
    "bridge": "https://cashtoss.info/ontology/bridge#",
    "actor": "https://cashtoss.info/ontology/actor#",
}
PROJ_NS = tuple(PREFIXES.values())
_REV = sorted({**PREFIXES, "owl": str(OWL), "rdfs": str(RDFS), "rdf": str(RDF),
               "obo": "http://purl.obolibrary.org/obo/",
               "lkif": "http://www.estrellaproject.org/lkif-core/lkif-core#",
               "sosa": "http://www.w3.org/ns/sosa/"}.items(), key=lambda kv: -len(kv[1]))


def short(u) -> str:
    s = str(u)
    for pfx, ns in _REV:
        if s.startswith(ns):
            return f"{pfx}:{s[len(ns):]}"
    return s


def is_proj(u) -> bool:
    return isinstance(u, URIRef) and str(u).startswith(PROJ_NS)


def ko_label(g, u) -> str:
    for o in g.objects(u, RDFS.label):
        if isinstance(o, Literal) and o.language == "ko":
            return str(o)
    for o in g.objects(u, RDFS.label):
        return str(o)
    return ""


def load():
    files = sorted([p for p in ONT.glob("*.ttl")] + [p for p in ONT.glob("*.owl")])
    g = Graph()
    n_files = 0
    for p in files:
        if p.name == BIG_ABOX:
            continue
        try:
            g.parse(str(p), format=("xml" if p.suffix == ".owl" else "turtle"))
            n_files += 1
        except Exception as e:  # noqa: BLE001
            print(f"  skip {p.name}: {e}", file=sys.stderr)
    return g, n_files


def main() -> int:
    g, n_files = load()
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if is_proj(c)}
    obj_props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if is_proj(p)}
    dat_props = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if is_proj(p)}
    inds = {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if is_proj(s)}

    # 피참조 빈도(목적어 위치) 1-pass
    ref = Counter()
    for _, _, o in g:
        if isinstance(o, URIRef):
            ref[o] += 1

    # 계층: 프로젝트 내 super/children
    proj_super = {c: [s for s in g.objects(c, RDFS.subClassOf) if is_proj(s) and s != c] for c in classes}
    children = defaultdict(list)
    for c, sups in proj_super.items():
        for s in sups:
            children[s].append(c)
    roots = sorted([c for c in classes if not proj_super[c]], key=lambda u: short(u))

    L = []
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    L.append("# KOSHA 온톨로지 카탈로그")
    L.append("")
    L.append(f"> AUTO-GENERATED (scripts/gen_catalog.py) — 수동편집 금지. Generated: {ts}")
    L.append(f"> 소스: serving TBox+facet+moderate ABox ({n_files} files, {len(g):,} triples; 대용량 instances 제외)")
    L.append(f"> class {len(classes)} · objectProperty {len(obj_props)} · dataProperty {len(dat_props)} · individual {len(inds)}")
    L.append("")

    # ── 1. 모듈 개요 ──
    L.append("## 1. 모듈 개요 (prefix)")
    L.append("")
    L.append("| prefix | class | objProp | dataProp | individual | namespace |")
    L.append("|---|--:|--:|--:|--:|---|")
    for pfx, ns in PREFIXES.items():
        cc = sum(1 for c in classes if str(c).startswith(ns))
        op = sum(1 for p in obj_props if str(p).startswith(ns))
        dp = sum(1 for p in dat_props if str(p).startswith(ns))
        ic = sum(1 for i in inds if str(i).startswith(ns))
        if cc or op or dp or ic:
            L.append(f"| `{pfx}:` | {cc} | {op} | {dp} | {ic} | `{ns}` |")
    L.append("")

    # ── 2. 클래스 계층 ──
    L.append("## 2. 클래스 계층 (전체 트리)")
    L.append("")
    L.append("표기: `prefix:Class` \"label\" [⊒하위수, ←피참조수]. 상위 BFO/LKIF는 괄호로.")
    L.append("")

    def render(node, depth, seen):
        if node in seen:
            L.append("  " * depth + f"- {short(node)} ↻(순환생략)")
            return
        seen = seen | {node}
        kids = sorted(children.get(node, []), key=lambda u: short(u))
        # 상위 주석: 프로젝트 외 named 상위(BFO/LKIF)만. 익명 제약(blank node)은 +제약N으로 요약(노이즈 제거).
        upper = [short(s) for s in g.objects(node, RDFS.subClassOf)
                 if isinstance(s, URIRef) and not is_proj(s)]
        n_restr = sum(1 for s in g.objects(node, RDFS.subClassOf) if not isinstance(s, URIRef))
        if n_restr:
            upper.append(f"+제약{n_restr}")
        up = f" ⊑({', '.join(upper)})" if upper else ""
        lab = ko_label(g, node)
        labs = f' "{lab}"' if lab else ""
        r = ref.get(node, 0)
        meta = f" [⊒{len(kids)}" + (f", ←{r}" if r else "") + "]" if (kids or r) else ""
        L.append("  " * depth + f"- `{short(node)}`{labs}{meta}{up}")
        # 큰 하위는 상위 일부만 펼치고 나머지 요약
        show = kids if len(kids) <= 40 else kids[:40]
        for k in show:
            render(k, depth + 1, seen)
        if len(kids) > 40:
            L.append("  " * (depth + 1) + f"- … (+{len(kids) - 40} more 하위, inspect_node.py --list 로 확인)")

    for r in roots:
        render(r, 0, set())
    L.append("")

    # ── 3. 속성 ──
    def prop_table(props, title):
        L.append(f"### {title} ({len(props)})")
        L.append("")
        L.append("| property | label | domain | range |")
        L.append("|---|---|---|---|")
        for p in sorted(props, key=lambda u: short(u)):
            dom = ", ".join(short(o) for o in g.objects(p, RDFS.domain)) or "—"
            rng = ", ".join(short(o) for o in g.objects(p, RDFS.range)) or "—"
            lab = ko_label(g, p)
            L.append(f"| `{short(p)}` | {lab} | {dom} | {rng} |")
        L.append("")

    L.append("## 3. 속성 (predicate)")
    L.append("")
    prop_table(obj_props, "Object Properties")
    prop_table(dat_props, "Data Properties")

    # ── 4. 이상 징후 ──
    L.append("## 4. ⚠️ 자동 이상징후 점검")
    L.append("")
    L.append("> ⚠️ ref/dead는 **대용량 kosha-instances.ttl(코퍼스) 제외** 집계 — guide/core/app 등 "
             "코퍼스에 instance가 있는 클래스의 dead/ref는 신뢰 불가(코퍼스에서 live일 수 있음). "
             "facet(haz/agent/ctx) fine 코드는 canonical-ci 포함이라 정확. 제거 전 반드시 코퍼스 포함 재확인.")
    L.append("")
    # floating: facet 클래스가 risk:RiskFeature까지 subClassOf로 도달하는가
    def reaches_riskfeature(c):
        RF = URIRef(PREFIXES["risk"] + "RiskFeature")
        stack, seen = [c], set()
        while stack:
            x = stack.pop()
            if x == RF:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(s for s in g.objects(x, RDFS.subClassOf) if isinstance(s, URIRef))
        return False

    # (a) facet 축 클래스인데 risk:RiskFeature 미도달
    facet_ns = (PREFIXES["haz"], PREFIXES["agent"], PREFIXES["ctx"])
    floating = sorted([c for c in classes if str(c).startswith(facet_ns) and not reaches_riskfeature(c)], key=short)
    L.append(f"**(a) facet 클래스인데 risk:RiskFeature 미도달(floating): {len(floating)}**")
    L.append("")
    if floating:
        L.append("  " + ", ".join(f"`{short(c)}`" for c in floating[:40]) + (" …" if len(floating) > 40 else ""))
    else:
        L.append("  ✅ 없음 (모든 facet 클래스가 risk:RiskFeature까지 연결).")
    L.append("")
    # (b) label 없는 클래스
    nolabel = sorted([c for c in classes if not ko_label(g, c)], key=short)
    L.append(f"**(b) rdfs:label 없는 클래스: {len(nolabel)}**")
    L.append("")
    if nolabel:
        L.append("  " + ", ".join(f"`{short(c)}`" for c in nolabel[:40]) + (" …" if len(nolabel) > 40 else ""))
    L.append("")
    # (c) dead 후보: 하위 0 + 피참조 0 + 개체 아님
    dead = sorted([c for c in classes
                   if not children.get(c) and ref.get(c, 0) == 0 and c not in inds], key=short)
    L.append(f"**(c) dead 후보(하위0·피참조0·개체아님): {len(dead)}**")
    L.append("")
    if dead:
        L.append("  " + ", ".join(f"`{short(c)}`" for c in dead[:40]) + (" …" if len(dead) > 40 else ""))
    L.append("")
    # (d) 중복 label (동일 ko label, 다른 IRI)
    by_label = defaultdict(list)
    for c in classes | inds:
        lab = ko_label(g, c)
        if lab:
            by_label[lab].append(c)
    dups = {lab: us for lab, us in by_label.items() if len(us) > 1}
    L.append(f"**(d) 중복 label(같은 한글 라벨, 다른 IRI): {len(dups)}쌍**")
    L.append("")
    for lab in sorted(dups)[:30]:
        L.append(f"  - \"{lab}\": " + ", ".join(f"`{short(u)}`" for u in dups[lab]))
    L.append("")
    # (e) domain/range 없는 property
    nodr = sorted([p for p in (obj_props | dat_props)
                   if not list(g.objects(p, RDFS.domain)) or not list(g.objects(p, RDFS.range))], key=short)
    L.append(f"**(e) domain 또는 range 누락 property: {len(nodr)}**")
    L.append("")
    if nodr:
        L.append("  " + ", ".join(f"`{short(p)}`" for p in nodr[:40]) + (" …" if len(nodr) > 40 else ""))
    L.append("")
    # (f) punned (class+individual 동시)
    punned = sorted([c for c in classes if c in inds], key=short)
    L.append(f"**(f) punned IRI(class+individual 동시, 정상이지만 참고): {len(punned)}**")
    L.append("")
    L.append(f"  {len(punned)}개 — facet canonical punning 설계(haz:Fall 등). 표본: " +
             ", ".join(f"`{short(c)}`" for c in punned[:12]) + (" …" if len(punned) > 12 else ""))
    L.append("")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[OK] {OUT.relative_to(ONT.parents[2])}  ({len(L)} lines)")
    print(f"  class {len(classes)} / obj {len(obj_props)} / dat {len(dat_props)} / ind {len(inds)}")
    print(f"  이상징후: floating={len(floating)} nolabel={len(nolabel)} dead={len(dead)} "
          f"dupLabel={len(dups)} no-dom/rng={len(nodr)} punned={len(punned)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
