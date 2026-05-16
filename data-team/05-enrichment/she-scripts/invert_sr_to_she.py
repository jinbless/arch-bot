"""Phase 2.1 — SR Inversion to SHE (LLM-based).

목적: 626 v1 SR을 LLM으로 8 dimension SHE로 분해 → she-draft-v1.jsonl 생성.
1 SR당 SHE 1~3개 (≤3 hard cap, dedupe by exact 8-feature tuple).

Day 1 dry-run: 10 SR만 처리 → cost calibration + prompt 검증.
Day 2 production: 626 SR 전체 (예상 비용 ~$15 with gpt-4o).

Usage:
  Dry-run (10 SR):
    PYTHONUTF8=1 python koshaontology/scripts/she/invert_sr_to_she.py --dry-run
  Production (626 SR):
    PYTHONUTF8=1 python koshaontology/scripts/she/invert_sr_to_she.py --all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "koshaontology" / "scripts" / "she"))

from llm_provider import call_llm

SR_REGISTRY = ROOT / "koshaontology" / "pipe-C" / "data" / "sr-registry.json"
OUTPUT_DIR = ROOT / "koshaontology" / "data" / "she"

# 8 dim RiskFeature enum (risk 중심 v2 T-Box 와 일치)
WORK_ACTIVITY_CODES = [
    "MAINTENANCE", "INSPECTION", "INSTALLATION", "DISMANTLE", "TRANSPORT",
    "REPAIR", "COMMISSIONING", "ANALYSIS_TESTING", "ROUTINE_OPERATION",
    "EMERGENCY_RESPONSE", "OTHER",
]
WORK_CONTEXT_CODES = [
    "SCAFFOLD", "CONFINED_SPACE", "EXCAVATION", "MACHINE", "VEHICLE",
    "CRANE", "CONVEYOR", "ROBOT", "CONSTRUCTION_EQUIP", "RAIL",
    "PRESSURE_VESSEL", "STEELWORK", "MATERIAL_HANDLING", "OTHER",
]
HAZARDOUS_AGENT_CODES = [
    "CHEMICAL", "DUST", "TOXIC", "CORROSION", "RADIATION", "FIRE",
    "ELECTRICITY", "ARC_FLASH", "NOISE", "HEAT_COLD", "BIOLOGICAL", "OTHER",
]
ACCIDENT_TYPE_CODES = [
    "FALL", "SLIP", "COLLISION", "FALLING_OBJECT", "CRUSH", "CUT",
    "COLLAPSE", "ERGONOMIC", "OTHER",
]
AGENT_STATE_CODES = [
    "ACTIVE_SOLO", "ACTIVE_PAIR", "ACTIVE_CREW", "STANDING_OBSERVATION", "OTHER",
]
PPE_STATE_CODES = [
    "HELMET_WORN", "HELMET_MISSING", "HARNESS_TIED", "HARNESS_UNTIED",
    "GLOVE_WORN", "MASK_WORN", "GOGGLES_WORN", "OTHER",
]
ENVIRONMENTAL_CODES = [
    "WET_SURFACE", "OIL_CONTAMINATION", "HIGH_ELEVATION", "LOW_LIGHT",
    "CLUTTERED", "WINDY_WEATHER", "EXTREME_TEMPERATURE", "OTHER",
]
TEMPORAL_STAGE_CODES = [
    "BEFORE_WORK", "DURING_WORK", "AFTER_WORK", "EMERGENCY_STAGE", "OTHER",
]


SYSTEM_PROMPT = """당신은 한국 산업안전 도메인 전문가이자 온톨로지 엔지니어입니다.
주어진 SafetyRequirement (SR) 텍스트를 보고, 이 SR이 위반될 수 있는 구체적 작업 상황(SituationalHazardPattern, SHE)을 8 dimension feature로 분해해주세요.

엄격한 규칙:
1. 1 SR당 SHE 1~3개 (≤3 hard cap). SR이 여러 상황을 다루면 분해, 단일 상황이면 1개만.
2. 각 SHE는 8 dimension feature 모두 보유 (값이 명확하지 않으면 "OTHER" 또는 가장 가까운 enum 코드).
3. **broadness 금지**: 한 SHE가 4개 이상 dim에 OTHER를 가지면 안됨. 가능한 specific.
4. **Dedupe**: 동일한 8-feature tuple은 1개만 (자동 합치기 후보).
5. 각 SHE에 한국어 name (50자 이내) + name_pattern: 비계_설치중_안전대미체결_추락 형식.
6. 각 SHE에는 사진에서 관찰 가능해야 하는 visual_triggers 1~5개를 포함. SR 문장 그대로가 아니라 "난간 없음", "덮개 없음", "작업자 접근 가능"처럼 시각 단서로 작성.

8 dimensions (각 enum + OTHER):
  - work_activity:    [MAINTENANCE, INSPECTION, INSTALLATION, DISMANTLE, TRANSPORT, REPAIR, COMMISSIONING, ANALYSIS_TESTING, ROUTINE_OPERATION, EMERGENCY_RESPONSE, OTHER]
  - work_context:     [SCAFFOLD, CONFINED_SPACE, EXCAVATION, MACHINE, VEHICLE, CRANE, CONVEYOR, ROBOT, CONSTRUCTION_EQUIP, RAIL, PRESSURE_VESSEL, STEELWORK, MATERIAL_HANDLING, OTHER]
  - hazardous_agent:  [CHEMICAL, DUST, TOXIC, CORROSION, RADIATION, FIRE, ELECTRICITY, ARC_FLASH, NOISE, HEAT_COLD, BIOLOGICAL, OTHER]
  - accident_type:    [FALL, SLIP, COLLISION, FALLING_OBJECT, CRUSH, CUT, COLLAPSE, ERGONOMIC, OTHER]
  - agent_state:      [ACTIVE_SOLO, ACTIVE_PAIR, ACTIVE_CREW, STANDING_OBSERVATION, OTHER]
  - ppe_state:        [HELMET_WORN, HELMET_MISSING, HARNESS_TIED, HARNESS_UNTIED, GLOVE_WORN, MASK_WORN, GOGGLES_WORN, OTHER]
  - environmental:    [WET_SURFACE, OIL_CONTAMINATION, HIGH_ELEVATION, LOW_LIGHT, CLUTTERED, WINDY_WEATHER, EXTREME_TEMPERATURE, OTHER]
  - temporal_stage:   [BEFORE_WORK, DURING_WORK, AFTER_WORK, EMERGENCY_STAGE, OTHER]

출력 형식 (JSON 객체만, 다른 텍스트 X):
{
  "she_list": [
    {
      "name": "비계 설치 중 안전대 미체결 추락 위험",
      "name_pattern": "scaffold_install_harness_untied_fall",
      "features": {
        "work_activity": "INSTALLATION",
        "work_context": "SCAFFOLD",
        "hazardous_agent": "OTHER",
        "accident_type": "FALL",
        "agent_state": "ACTIVE_SOLO",
        "ppe_state": "HARNESS_UNTIED",
        "environmental": "HIGH_ELEVATION",
        "temporal_stage": "DURING_WORK"
      },
      "visual_triggers": [
        "비계 또는 고소 작업발판이 보임",
        "안전대 체결 상태가 보이지 않거나 미체결로 보임",
        "작업자가 추락 가능 위치에서 작업 중임"
      ],
      "rationale": "SR text에서 비계+설치+안전대 미체결 시 추락이 핵심 시나리오"
    }
  ]
}"""


def build_user_prompt(sr: dict) -> str:
    """SR registry entry → LLM user prompt."""
    sr_id = sr["identifier"]
    title = sr.get("title", "")
    text = sr.get("text", "")[:800]  # 너무 길면 truncate
    addresses_hazard = sr.get("addressesHazard") or []
    sub_role = sr.get("subjectRole") or ""
    requirement_type = sr.get("requirementType", "")
    return f"""다음 SR을 8 dimension SHE로 분해해주세요.

SR ID: {sr_id}
제목: {title}
요구사항 유형: {requirement_type}
대상 위험: {", ".join(addresses_hazard) if addresses_hazard else "(없음)"}
의무 주체: {sub_role or "(미명시)"}

본문:
{text}

JSON 객체만 출력 (she_list 배열). 1~3개 SHE."""


def feature_tuple_hash(features: dict) -> str:
    """8 dim feature tuple → stable 10-char hash (사용자 비판 #8: SHE ID = SHE-{wc}-{hash10})."""
    keys = sorted([
        "work_activity", "work_context", "hazardous_agent", "accident_type",
        "agent_state", "ppe_state", "environmental", "temporal_stage",
    ])
    s = "|".join(f"{k}:{features.get(k, 'OTHER')}" for k in keys)
    return hashlib.md5(s.encode()).hexdigest()[:10]


def build_she_id(features: dict, sr_id: str) -> str:
    """SHE ID = SHE-{primary_work_context}-{feature_tuple_hash10}."""
    wc = features.get("work_context", "OTHER").replace("_", "")
    h = feature_tuple_hash(features)
    return f"SHE-{wc}-{h}"


def compute_broadness(features: dict) -> float:
    """specificity ratio = (1 - OTHER_count/8). ≥0.5 권장."""
    other_count = sum(1 for v in features.values() if v == "OTHER")
    return 1.0 - (other_count / 8.0)


def invert_one_sr(sr: dict, provider: str, model: str) -> tuple[list[dict], dict]:
    """1 SR → SHE list + usage stats."""
    user_prompt = build_user_prompt(sr)
    r = call_llm(
        provider=provider,
        model=model,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=2000,
        temperature=0.3,
        json_mode=True,
    )
    try:
        parsed = json.loads(r["text"])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from LLM: {e}\nRaw: {r['text'][:300]}")
    she_list = parsed.get("she_list", [])

    # Hard cap 1 SR → ≤3 SHE
    she_list = she_list[:3]

    # Dedup by feature tuple
    seen_hashes: set[str] = set()
    unique_shes: list[dict] = []
    for she in she_list:
        features = she.get("features", {})
        h = feature_tuple_hash(features)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        # SHE ID + metadata
        she_id = build_she_id(features, sr["identifier"])
        broadness = compute_broadness(features)

        unique_shes.append({
            "she_id": she_id,
            "name": she.get("name", ""),
            "name_pattern": she.get("name_pattern", ""),
            "features": features,
            "visual_triggers": she.get("visual_triggers") or [she.get("name", "")],
            "rationale": she.get("rationale", ""),
            "source_sr_ids": [sr["identifier"]],
            "source_model": f"{provider}/{model}",
            "source_prompt_hash": hashlib.md5(SYSTEM_PROMPT.encode()).hexdigest(),
            "broadness_score": round(broadness, 3),
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        })
    return unique_shes, r["usage"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--dry-run", action="store_true",
                        help="10 SR만 처리 (cost calibration)")
    parser.add_argument("--all", action="store_true",
                        help="626 SR 전체 처리")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", default="phase2-she-inversion-2026-04-27")
    args = parser.parse_args()

    if args.dry_run:
        n_target = 10
        out_file = OUTPUT_DIR / "she-dryrun-v1.jsonl"
    elif args.all:
        n_target = None
        out_file = OUTPUT_DIR / "she-draft-v1.jsonl"
    else:
        n_target = args.limit or 10
        out_file = OUTPUT_DIR / f"she-partial-{n_target}.jsonl"

    print(f"[INFO] sr-registry: {SR_REGISTRY}")
    print(f"[INFO] output: {out_file}")
    print(f"[INFO] provider/model: {args.provider}/{args.model}")
    print(f"[INFO] target SR count: {n_target}")

    registry = json.loads(SR_REGISTRY.read_text(encoding="utf-8"))
    srs = registry.get("registry", [])
    print(f"[INFO] sr-registry SRs: {len(srs)}")

    # Deterministic order
    srs_sorted = sorted(srs, key=lambda s: hashlib.md5((s["identifier"] + args.seed).encode()).hexdigest())
    if n_target:
        srs_sorted = srs_sorted[:n_target]

    out_file.parent.mkdir(parents=True, exist_ok=True)
    total_in_tok = 0
    total_out_tok = 0
    she_count = 0
    sr_count = 0
    errors = []

    with out_file.open("w", encoding="utf-8") as f:
        for i, sr in enumerate(srs_sorted, start=1):
            try:
                shes, usage = invert_one_sr(sr, args.provider, args.model)
                for she in shes:
                    f.write(json.dumps(she, ensure_ascii=False) + "\n")
                    she_count += 1
                total_in_tok += usage["in"]
                total_out_tok += usage["out"]
                sr_count += 1
                if shes:
                    avg_broad = sum(s["broadness_score"] for s in shes) / len(shes)
                    print(f"  [{i:3d}/{len(srs_sorted)}] {sr['identifier']:30s} → {len(shes)} SHE (broad={avg_broad:.2f}, tok in/out={usage['in']}/{usage['out']})")
                else:
                    print(f"  [{i:3d}/{len(srs_sorted)}] {sr['identifier']:30s} → 0 SHE (skip)")
            except Exception as e:
                errors.append((sr["identifier"], str(e)[:200]))
                print(f"  [{i:3d}/{len(srs_sorted)}] {sr['identifier']:30s} → ERROR: {str(e)[:100]}")

    # 비용 추정 (gpt-4o 기준: $0.0025/1K input + $0.010/1K output)
    cost_in = total_in_tok / 1000 * 0.0025
    cost_out = total_out_tok / 1000 * 0.010
    cost_total = cost_in + cost_out

    print(f"\n[OK] {out_file} 생성")
    print(f"     SRs processed: {sr_count}/{len(srs_sorted)}")
    print(f"     SHE generated: {she_count}")
    print(f"     Avg SHE/SR: {she_count / max(sr_count, 1):.2f}")
    print(f"     Tokens in/out: {total_in_tok:,} / {total_out_tok:,}")
    print(f"     Cost (gpt-4o): ${cost_total:.4f} (in ${cost_in:.4f} + out ${cost_out:.4f})")

    if errors:
        print(f"\n[WARN] {len(errors)} errors:")
        for sr_id, err in errors[:5]:
            print(f"  {sr_id}: {err}")

    # Extrapolate cost for full 626 SR
    if n_target and n_target < 626:
        ratio = 626 / n_target
        proj_cost = cost_total * ratio
        print(f"\n[EST] Full 626 SR projected cost: ~${proj_cost:.2f} ({ratio:.1f}x scaling)")


if __name__ == "__main__":
    main()
