#!/usr/bin/env python3
"""Pilot v2: PG에서 v2 SR + 관련 NS/Article을 읽어 self-contained TTL 생성 후
R-2 (coApplicable) SPARQL CONSTRUCT 추론을 적용해 영구화.

출력:
  data/pilot/kosha-instances-v2-pilot.ttl  (v2 SR + 관련 NS/Article + R-2 결과)

이 TTL은 Fuseki에 별도 dataset(/kosha-v2)으로 등록할 수 있도록 self-contained.
v1 데이터(626 SR)는 무손상.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from rdflib import Graph, Literal, Namespace, RDF, XSD

PIPE_A_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPE_A_ROOT / "data"
PILOT_DIR = DATA_DIR / "pilot"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"

KOSHA = Namespace("https://cashtoss.info/ontology#")
LAW = Namespace("https://cashtoss.info/ontology/law#")
SR = Namespace("https://cashtoss.info/ontology/sr#")
GUIDE = Namespace("https://cashtoss.info/ontology/guide#")
HAZ = Namespace("https://cashtoss.info/ontology/hazard#")
PEN = Namespace("https://cashtoss.info/ontology/penalty#")

REQTYPE_MAP = {
    "PHYSICAL_PROTECTION": SR.PhysicalProtection,
    "PPE_REQUIREMENT":     SR.PPERequirement,
    "PROCEDURAL":          SR.Procedural,
    "TRAINING":            SR.Training,
    "EQUIPMENT_STANDARD":  SR.EquipmentStandard,
    "ENVIRONMENTAL":       SR.Environmental,
    "MANAGEMENT_SYSTEM":   SR.ManagementSystem,
    "EMERGENCY_RESPONSE":  SR.EmergencyResponse,
}
BINDING_MAP = {"MANDATORY": KOSHA.Mandatory, "RECOMMENDED": KOSHA.Recommended}


def safe_uri(s: str) -> str:
    return s.replace(" ", "_").replace("·", "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g = Graph()
    g.bind("kosha", KOSHA)
    g.bind("law", LAW)
    g.bind("sr", SR)
    g.bind("guide", GUIDE)
    g.bind("hazard", HAZ)
    g.bind("pen", PEN)

    with psycopg2.connect(PG_CONNINFO) as conn, conn.cursor() as cur:
        # ── 1. v2 SR 본체 ──
        cur.execute("""
            SELECT identifier, title, text, requirement_type, binding_force, addresses_hazard
            FROM safety_requirements_v2
        """)
        sr_count = 0
        for ident, title, text, req_type, binding, hazards in cur.fetchall():
            uri = SR[safe_uri(ident)]
            g.add((uri, RDF.type, SR.SafetyRequirement))
            g.add((uri, KOSHA.identifier, Literal(ident, datatype=XSD.string)))
            if title:
                g.add((uri, KOSHA.title, Literal(title, datatype=XSD.string)))
            if text:
                g.add((uri, KOSHA.text, Literal(text, datatype=XSD.string)))
            if req_type and req_type in REQTYPE_MAP:
                g.add((uri, SR.hasRequirementType, REQTYPE_MAP[req_type]))
            if binding and binding in BINDING_MAP:
                g.add((uri, SR.hasBindingForce, BINDING_MAP[binding]))
            if hazards:
                hlist = hazards if isinstance(hazards, list) else []
                for h in hlist:
                    g.add((uri, SR.addressesHazard, HAZ[h]))
            sr_count += 1

        # ── 2. v2 SR-NS mapping (derivedFromNS) ──
        cur.execute("SELECT sr_id, ns_id FROM sr_ns_mapping_v2")
        ns_map_count = 0
        related_ns: set[str] = set()
        for sr_id, ns_id in cur.fetchall():
            g.add((SR[safe_uri(sr_id)], SR.derivedFromNS, LAW[safe_uri(ns_id)]))
            related_ns.add(ns_id)
            ns_map_count += 1

        # ── 3. v2 SR-Article mapping ──
        cur.execute("SELECT sr_id, law_type, article_code FROM sr_article_mapping_v2")
        art_map_count = 0
        related_articles: set[tuple[str, str]] = set()
        for sr_id, law_type, art_code in cur.fetchall():
            g.add((SR[safe_uri(sr_id)],
                   SR.directlyAppliesToArticle,
                   LAW[safe_uri(f"{law_type}_{art_code}")]))
            related_articles.add((law_type, art_code))
            art_map_count += 1

        # ── 4. 관련 NS의 메타 + hasSourceArticle (PA-4 chain의 두 번째 절) ──
        if related_ns:
            placeholder = ", ".join(["%s"] * len(related_ns))
            cur.execute(
                f"""SELECT identifier, article_code, paragraph_ref, has_modality, text
                    FROM norm_statements WHERE identifier IN ({placeholder})""",
                tuple(related_ns),
            )
            ns_count = 0
            for ns_id, ac, pref, modality, ns_text in cur.fetchall():
                ns_uri = LAW[safe_uri(ns_id)]
                g.add((ns_uri, RDF.type, LAW.NormStatement))
                g.add((ns_uri, KOSHA.identifier, Literal(ns_id, datatype=XSD.string)))
                if pref:
                    g.add((ns_uri, LAW.paragraphRef, Literal(pref, datatype=XSD.string)))
                if modality:
                    g.add((ns_uri, LAW.hasModality, KOSHA[modality.capitalize()]))
                if ns_text:
                    g.add((ns_uri, KOSHA.text, Literal(ns_text, datatype=XSD.string)))
                # NS → Article (이게 있어야 propertyChain SR→NS→Article 추론 가능)
                g.add((ns_uri, LAW.hasSourceArticle, LAW[safe_uri(f"RULE_{ac}")]))
                ns_count += 1

        # ── 5. 관련 Article 메타 ──
        if related_articles:
            ph = ", ".join(["(%s, %s)"] * len(related_articles))
            params: list = []
            for lt, ac in related_articles:
                params.extend([lt, ac])
            cur.execute(
                f"""SELECT law_type, article_code, title FROM articles
                    WHERE (law_type, article_code) IN ({ph})""",
                tuple(params),
            )
            art_count = 0
            for lt, ac, title in cur.fetchall():
                art_uri = LAW[safe_uri(f"{lt}_{ac}")]
                g.add((art_uri, RDF.type, LAW.Article))
                g.add((art_uri, LAW.articleCode, Literal(ac, datatype=XSD.string)))
                g.add((art_uri, LAW.lawType, Literal(lt, datatype=XSD.string)))
                if title:
                    g.add((art_uri, KOSHA.title, Literal(title, datatype=XSD.string)))
                art_count += 1

    base_count = len(g)
    print(f"[1/3] v2 base 트리플 적재 완료")
    print(f"        SR_v2: {sr_count}, sr_ns_mapping_v2: {ns_map_count}, "
          f"sr_article_mapping_v2: {art_map_count}")
    print(f"        관련 NS: {ns_count}, 관련 Article: {art_count}")
    print(f"        총 base 트리플: {base_count}")

    # ── R-2 SPARQL CONSTRUCT (NS chain 사용) ──
    print(f"\n[2/3] R-2 (coApplicable) CONSTRUCT 실행...")
    r2 = """
    PREFIX sr: <https://cashtoss.info/ontology/sr#>
    PREFIX law: <https://cashtoss.info/ontology/law#>
    PREFIX kosha: <https://cashtoss.info/ontology#>
    CONSTRUCT { ?sr1 kosha:coApplicable ?sr2 . }
    WHERE {
      ?sr1 a sr:SafetyRequirement ; sr:derivedFromNS ?ns1 .
      ?sr2 a sr:SafetyRequirement ; sr:derivedFromNS ?ns2 .
      ?ns1 law:hasSourceArticle ?art .
      ?ns2 law:hasSourceArticle ?art .
      FILTER(?sr1 != ?sr2 && STR(?sr1) < STR(?sr2))
    }
    """
    coapp_pairs = list(g.query(r2))
    print(f"        coApplicable 추론된 쌍: {len(coapp_pairs)}")

    # 영구화: 추론 결과를 그래프에 추가
    for triple in coapp_pairs:
        g.add(triple)
    after_count = len(g)
    print(f"        영구화 후 총 트리플: {after_count} (+{after_count - base_count})")

    # 샘플 출력
    print(f"\n[샘플 5쌍]")
    for s, _p, o in coapp_pairs[:5]:
        s_short = str(s).split("#")[-1]
        o_short = str(o).split("#")[-1]
        print(f"  {s_short} ↔ {o_short}")

    # 분포 (article별)
    print(f"\n[Article별 coApplicable 후보 분포]")
    by_art = {}
    for triple in coapp_pairs:
        s = str(triple[0])
        o = str(triple[2])
        # 둘 다 같은 article에서 나왔으니 NS 검색해서 article 알아내기 (간이)
        # 더 간단: SR ID에서 카테고리 추출
        s_cat = s.split("PILOT_")[1].rsplit("-", 1)[0] if "PILOT_" in s else "?"
        by_art.setdefault(s_cat, 0)
        by_art[s_cat] += 1
    for cat in sorted(by_art, key=lambda c: -by_art[c]):
        print(f"  {cat}: {by_art[cat]}쌍")

    # ── 3. TTL 저장 ──
    print(f"\n[3/3] TTL 저장...")
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PILOT_DIR / "kosha-instances-v2-pilot.ttl"
    g.serialize(out_path, format="turtle")
    print(f"        [OK] {out_path}")
    print(f"        [OK] 총 트리플: {after_count} (base {base_count} + R-2 {len(coapp_pairs)})")
    print(f"        [OK] 자기-완결적 — Fuseki에 별도 dataset(/kosha-v2)으로 등록 가능")


if __name__ == "__main__":
    main()
