#!/usr/bin/env python3
"""production ABox enrichment — 8 photo eval 결과 → ontology ABox instance.

Phase B/C-J 발견: production ABox에 alethic/bridge chain runtime instance 0 → R-10~R-30 fire 0.
본 ETL은 실제 사진 분석 결과 (hazard_direct_8photo_eval.json)를 ontology ABox로 변환:
- 각 photo → app:VisualObservation
- hazards[].mapped_codes (예: accident_type.FALL) → risk:RiskFeature + haz:hasHazard haz:{CODE}
  (CODE는 기존 ABox의 haz:Hazard instance — addressesHazard target과 일치)
- VisualObservation risk:hasRiskFeature RiskFeature (R-10 결과 직접 생성)
- RiskFeature risk:correspondsToHazard + haz:hasHazard haz:{CODE} (R-11 결과)

이로써 SHACL R-14 (VO→Hazard), R-15 (기존 SR addressesHazard 공유 → bridge:appliesTo) fire.

사용:
  PYTHONIOENCODING=utf-8 python export_8photo_to_abox.py
산출:
  ontology-team/06-reasoning/ontology/kosha-instances-production-8photo.ttl
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "ontology-team" / "06-reasoning" / "ontology").is_dir():
            return p
    raise RuntimeError("repo root not found")


REPO = _find_root()
EVAL = REPO / "data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json"
OUT = REPO / "ontology-team/06-reasoning/ontology/kosha-instances-production-8photo.ttl"


def slug(s: str) -> str:
    """photo 파일명 → ASCII slug (IRI fragment)."""
    base = re.sub(r"[^a-zA-Z0-9]", "_", s)[:30].strip("_")
    return base or "photo"


HEADER = """# production ABox enrichment — 8 photo eval 결과 → ontology ABox instance.
#
# export_8photo_to_abox.py 산출. 실제 사진 분석 (hazard_direct_8photo_eval.json) →
# VisualObservation/RiskFeature chain. R-14/R-15 (bridge) SHACL fire 입증용.
#
# 검증 전용 — production fuseki sources 등록은 운영 정책에 따라 (현재 demo/sample).

@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix risk: <https://cashtoss.info/ontology/risk#> .
@prefix haz: <https://cashtoss.info/ontology/risk/hazard#> .
@prefix app: <https://cashtoss.info/ontology/app#> .
@prefix prod: <https://cashtoss.info/ontology/production#> .

"""


def main():
    d = json.loads(EVAL.read_text(encoding="utf-8"))
    results = d.get("results", [])
    lines = [HEADER]
    vo_count = 0
    rf_count = 0
    hazard_links = 0
    seen_rf = set()

    for i, r in enumerate(results, 1):
        photo_slug = slug(r.get("photo", f"photo{i}"))
        vo_id = f"prod:VO_{i:02d}_{photo_slug}"
        lines.append(f"### Photo {i}: {r.get('photo','')[:50]}")
        lines.append(f"{vo_id} a app:VisualObservation ;")
        lines.append(f'    rdfs:label "photo {i}: {photo_slug}"@ko .')
        lines.append("")
        vo_count += 1

        # 각 hazard의 mapped_codes → RiskFeature + Hazard
        for j, h in enumerate(r.get("hazards", []), 1):
            codes = h.get("mapped_codes", []) or []
            for code_str in codes:
                # "accident_type.FALL" → axis=accident_type, code=FALL
                if "." in code_str:
                    axis, code = code_str.split(".", 1)
                else:
                    axis, code = "accident_type", code_str
                rf_id = f"prod:RF_{code}"
                if rf_id not in seen_rf:
                    seen_rf.add(rf_id)
                    lines.append(f"{rf_id} a risk:RiskFeature ;")
                    lines.append(f'    rdfs:label "{code} ({axis})"@en ;')
                    # R-11 body + 결과 (correspondsToHazard + hasHazard) — code가 기존 haz:Hazard와 일치
                    lines.append(f"    risk:correspondsToHazard haz:{code} ;")
                    lines.append(f"    haz:hasHazard haz:{code} .")
                    lines.append("")
                    rf_count += 1
                # VisualObservation → hasRiskFeature (R-10 결과)
                lines.append(f"{vo_id} risk:hasRiskFeature {rf_id} .")
                hazard_links += 1
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  VisualObservation: {vo_count}")
    print(f"  RiskFeature (unique mapped_code): {rf_count}")
    print(f"  hasRiskFeature links: {hazard_links}")
    print(f"  mapped codes: {sorted(c.replace('prod:RF_','') for c in seen_rf)}")


if __name__ == "__main__":
    main()
