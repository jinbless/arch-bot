#!/usr/bin/env python3
"""Part 3 prep — synthetic_observations_v*.jsonl의 KO enum 값 마이닝 + 자동 EN 후보 추출.

목적: synthetic data 정리(Part 3)의 입력 prep.
1. 모든 v*.jsonl의 expected_features axis별 KO 코드 + frequency 수집
2. f2_light_catalog_proposals.json의 ACCEPT/RELOCATE 결정에서 canonical_label_en 가져오기
3. risk_feature_catalog.json의 EN codes도 참조 (정확 일치 KO label인 경우)
4. 결과를 synthetic_ko_codes_for_review.json에 저장 (사람 검토용)

실제 변환은 다음 세션에서 transform_synthetic_to_en.py 작성 + 실행.
이 prep 자체는 LLM 호출 0 (순수 lookup).
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
SYNTH_DIR = ROOT / "data-team/05-enrichment/eval-data"
F2_PROPOSALS = ROOT / "data-team/05-enrichment/runtime-artifacts/f2_light_catalog_proposals.json"
CATALOG = ROOT / "serving-team/08-app/backend/app/data/risk_feature_catalog.json"
ALIASES = ROOT / "serving-team/08-app/backend/app/data/risk_feature_aliases.json"
OUT = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_ko_codes_for_review.json"

# synthetic uses plural axis keys, catalog/aliases use singular
AXIS_MAP = {
    "accident_types": "accident_type",
    "hazardous_agents": "hazardous_agent",
    "work_contexts": "work_context",
    "ppe_states": "ppe_state",        # not in catalog v3
    "environmental": "environmental",  # not in catalog v3
}


def mine_synthetic_ko() -> dict[str, Counter[str]]:
    by_axis: dict[str, Counter[str]] = defaultdict(Counter)
    for fp in sorted(SYNTH_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            exp = r.get("expected_features", {})
            for axis_synth, codes in exp.items():
                if isinstance(codes, list):
                    for c in codes:
                        if isinstance(c, str) and any(ord(ch) > 127 for ch in c):
                            by_axis[axis_synth][c] += 1
    return by_axis


def build_lookup_table():
    """Combine all available KO -> EN sources into one lookup."""
    # 1. catalog labels: KO label -> EN code
    label_to_code: dict[tuple[str, str], str] = {}  # (axis, ko_label) -> en_code
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    for axis, info in cat.get("axes", {}).items():
        for code, code_info in info.get("codes", {}).items():
            label_ko = code_info.get("label", "")
            if label_ko:
                label_to_code[(axis, label_ko)] = code
    # 2. aliases: KO alias -> EN code
    alias_to_code: dict[tuple[str, str], str] = {}
    al = json.loads(ALIASES.read_text(encoding="utf-8"))
    for axis, codes in al.get("tier1", {}).items():
        for code, aliases in codes.items():
            if not isinstance(aliases, list):
                continue
            for a in aliases:
                if isinstance(a, str):
                    alias_to_code[(axis, a.strip())] = code
    # 3. f2_light proposals: KO code -> en_canonical (ACCEPT or RELOCATE)
    f2_lookup: dict[tuple[str, str], dict] = {}  # (axis, ko_code) -> {en, decision, conf}
    if F2_PROPOSALS.exists():
        f2 = json.loads(F2_PROPOSALS.read_text(encoding="utf-8"))
        for dec in ("ACCEPT", "RELOCATE"):
            for item in f2.get("decisions", {}).get(dec, []):
                axis = item.get("axis")
                code = item.get("code")
                en = item.get("canonical_label_en", "")
                if axis and code and en:
                    f2_lookup[(axis, code)] = {
                        "en_candidate": en,
                        "decision": dec,
                        "confidence": item.get("confidence", 0),
                        "correct_axis": item.get("correct_axis", ""),
                    }
    return label_to_code, alias_to_code, f2_lookup


def main():
    ko_by_axis = mine_synthetic_ko()
    label_lookup, alias_lookup, f2_lookup = build_lookup_table()

    print(f"=== Synthetic KO codes mined ===")
    for axis, c in ko_by_axis.items():
        print(f"  {axis:18s} {len(c):4d} unique KO codes (top occurrence {max(c.values()) if c else 0})")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_axes": list(ko_by_axis.keys()),
        "sources_used": {
            "catalog_label_lookup": len(label_lookup),
            "alias_lookup": len(alias_lookup),
            "f2_light_proposals": len(f2_lookup),
        },
        "axes": {},
    }

    for axis_synth, counter in ko_by_axis.items():
        axis_cat = AXIS_MAP.get(axis_synth)
        items = []
        auto_mapped = 0
        need_llm = 0
        for ko_code, freq in counter.most_common():
            entry = {
                "ko_code": ko_code,
                "freq": freq,
                "auto_en": None,
                "auto_source": None,
                "f2_proposal": None,
            }
            # Try lookup chain: catalog label > alias > f2_proposal
            if axis_cat:
                if (axis_cat, ko_code) in label_lookup:
                    entry["auto_en"] = label_lookup[(axis_cat, ko_code)]
                    entry["auto_source"] = "catalog_label"
                    auto_mapped += 1
                elif (axis_cat, ko_code) in alias_lookup:
                    entry["auto_en"] = alias_lookup[(axis_cat, ko_code)]
                    entry["auto_source"] = "alias"
                    auto_mapped += 1
                elif (axis_cat, ko_code) in f2_lookup:
                    entry["f2_proposal"] = f2_lookup[(axis_cat, ko_code)]
                    entry["auto_en"] = f2_lookup[(axis_cat, ko_code)]["en_candidate"]
                    entry["auto_source"] = f"f2_light_{f2_lookup[(axis_cat, ko_code)]['decision']}"
                    auto_mapped += 1
                else:
                    need_llm += 1
            else:
                need_llm += 1
            items.append(entry)
        out["axes"][axis_synth] = {
            "total": len(items),
            "auto_mapped": auto_mapped,
            "need_llm_or_manual": need_llm,
            "items": items,
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT.relative_to(ROOT)}")
    print(f"\n=== Coverage summary ===")
    for axis_synth, data in out["axes"].items():
        total = data["total"]
        auto = data["auto_mapped"]
        pct = (100 * auto / total) if total else 0
        print(f"  {axis_synth:18s} auto: {auto:4d} / {total:4d}  ({pct:5.1f}%)  remaining: {data['need_llm_or_manual']}")


if __name__ == "__main__":
    main()
