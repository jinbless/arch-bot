#!/usr/bin/env python3
"""Phase 4-B Stage 3-5a — 온톨로지 어휘 KOSHA-22 CamelCase 단일화 (결정적 fragment 치환).

모든 *.ttl(disjoint+SWRL+restriction+SHACL+ABox)에서 구 어휘(CamelCase 8-type + UPPER haz:Hazard
레거시 + mis-axis 오염) → KOSHA-22 CamelCase로 단어경계 치환. git이 백업(되돌리기: git checkout).

근거(code_iri_mapper.LEGACY_FRAGMENT_TO_CODE + canonical_vocab):
- 구 8-type: Crush→CaughtIn, Cut→CutLaceration, FallingObject→StruckBy, Slip→SlipTrip, Ergonomic→ErgonomicStrain
- UPPER 레거시(haz:Hazard): CAUGHT_IN→CaughtIn, STRUCK_BY→StruckBy, ... (KOSHA-22 CamelCase)
- mis-axis(haz:에 잘못 들어온 work_context/agent): CONFINED_SPACE→OxygenDeficiency, SCAFFOLDING→Fall,
  HEAT_COLD→TempExtremeContact, NOISE_VIBRATION→OtherAccident (가장 근접 accident, in-axis 유지)

사용: python migrate_vocab_to_kosha22.py [--apply]   (기본: dry-run, --apply로 실제 기록)
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

ONTO_DIR = Path(__file__).resolve().parents[1]

# haz: fragment 치환 (구 → KOSHA-22 CamelCase). 값이 같은 경우(Fall→Fall 등)는 생략.
HAZ_SUB = {
    # 구 CamelCase AccidentType
    "Crush": "CaughtIn", "Cut": "CutLaceration", "FallingObject": "StruckBy",
    "Slip": "SlipTrip", "Ergonomic": "ErgonomicStrain",
    "ColdExposure": "TempExtremeContact", "Burn": "TempExtremeContact",
    "FoodContamination": "OtherAccident",
    # UPPER 레거시(haz:Hazard) → KOSHA-22
    "CAUGHT_IN": "CaughtIn", "STRUCK_BY": "StruckBy", "FALLING_OBJECT": "StruckBy",
    "ENTANGLEMENT": "CaughtIn", "CRUSH": "CaughtIn", "CUT": "CutLaceration",
    "COLLAPSE": "Collapse", "COLLISION": "Collision", "FALL": "Fall",
    "FALL_ON_GROUND": "Fall", "ELECTRIC_SHOCK": "ElectricShock",
    "CHEMICAL_EXPOSURE": "ChemicalExposure", "ERGONOMIC": "ErgonomicStrain",
    "FIRE_EXPLOSION": "FireInjury", "FIRE_AND_EXPLOSION": "FireInjury",
    # mis-axis(haz:에 잘못 들어온 것) → 가장 근접 accident
    "CONFINED_SPACE": "OxygenDeficiency", "SCAFFOLDING": "Fall",
    "HEAT_COLD": "TempExtremeContact", "NOISE_VIBRATION": "OtherAccident",
}
# agent: fragment 치환 (SSOT 외 변종)
AGENT_SUB = {"Corrosion": "Chemical", "ArcFlash": "Electricity"}
# ctx: fragment 치환 — 구 CamelCase는 이미 SSOT와 정합(Scaffold=SCAFFOLD 등). 없음.
CTX_SUB: dict[str, str] = {}

PREFIX_SUBS = {"haz": HAZ_SUB, "agent": AGENT_SUB, "ctx": CTX_SUB}


def build_patterns():
    """(compiled_regex, replacement) 리스트. 단어경계: prefix:Frag 뒤에 [A-Za-z0-9_] 없을 때만."""
    pats = []
    for prefix, sub in PREFIX_SUBS.items():
        # 긴 fragment 먼저(부분일치 방지): FALL_ON_GROUND를 FALL보다 먼저
        for old in sorted(sub, key=len, reverse=True):
            new = sub[old]
            # prefix:OLD 뒤에 word char가 없어야(FALL이 FALLING_OBJECT 안 건드림)
            pat = re.compile(rf"(?<![A-Za-z0-9_])({prefix}:){re.escape(old)}(?![A-Za-z0-9_])")
            pats.append((pat, rf"\g<1>{new}", f"{prefix}:{old}→{prefix}:{new}"))
    return pats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 파일 기록(기본 dry-run)")
    args = ap.parse_args()
    pats = build_patterns()

    # 제외: original(롤백 백업), disjoint(Stage 3에서 신규 작성)
    EXCLUDE = {"kosha-instances.original.ttl", "kosha-accident22-disjoint.ttl"}
    files = sorted(fp for fp in ONTO_DIR.glob("*.ttl") if fp.name not in EXCLUDE)
    total_changes = 0
    per_rule: dict[str, int] = {}
    changed_files = 0
    for fp in files:
        text = fp.read_text(encoding="utf-8")
        new_text = text
        file_changes = 0
        for pat, repl, label in pats:
            new_text, n = pat.subn(repl, new_text)
            if n:
                per_rule[label] = per_rule.get(label, 0) + n
                file_changes += n
        if file_changes:
            changed_files += 1
            total_changes += file_changes
            print(f"  {fp.name:48s} {file_changes:6d} 치환")
            if args.apply:
                fp.write_text(new_text, encoding="utf-8")

    print(f"\n{'=== APPLIED ===' if args.apply else '=== DRY-RUN (미적용) ==='}")
    print(f"파일 {changed_files}/{len(files)} 변경, 총 {total_changes} 치환")
    print("\n규칙별 치환 수:")
    for label, n in sorted(per_rule.items(), key=lambda x: -x[1]):
        print(f"  {label:40s} {n:6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
