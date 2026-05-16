"""Phase 1 — SHE JSONL Validator (사용자 비판 #5).

OWL DL은 closed-world 가정 안 함 → "8 dim 필수" 검증을 OWL에서 강제 불가능.
Python validator로 다음 검사:
  1. 8 dim 모두 존재 (각 feature dim에 ≥1 값)
  2. 허용 코드만 사용 (enum 검증)
  3. feature tuple 정확일치 dedup
  4. source SR 최소 1개 (orphan SHE 0건)
  5. broadness score ≥ 0.5 (specific dim 4+/8)
  6. SHE name 중복 검사

승인 흐름:
  validator + broadness 통과 → status='approved_auto'
  validator 실패 또는 broadness <0.5 → 'rejected'
  → she-rejected-v1.jsonl로 이동 (통계 분석용)

Usage:
  PYTHONUTF8=1 python koshaontology/scripts/she/validate_she_jsonl.py \
      --input koshaontology/data/she/she-draft-v1.jsonl \
      --output-approved koshaontology/data/she/she-approved-v1.jsonl \
      --output-rejected koshaontology/data/she/she-rejected-v1.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[3]

# 8 dim 허용 enum (kosha-ontology.owl SHE T-Box과 일치)
ALLOWED_CODES = {
    "work_activity": {
        "MAINTENANCE", "INSPECTION", "INSTALLATION", "DISMANTLE", "TRANSPORT",
        "REPAIR", "COMMISSIONING", "ANALYSIS_TESTING", "ROUTINE_OPERATION",
        "EMERGENCY_RESPONSE", "OTHER",
    },
    "work_context": {
        "SCAFFOLD", "CONFINED_SPACE", "EXCAVATION", "MACHINE", "VEHICLE",
        "CRANE", "CONVEYOR", "ROBOT", "CONSTRUCTION_EQUIP", "RAIL",
        "PRESSURE_VESSEL", "STEELWORK", "MATERIAL_HANDLING", "OTHER",
    },
    "hazardous_agent": {
        "CHEMICAL", "DUST", "TOXIC", "CORROSION", "RADIATION", "FIRE",
        "ELECTRICITY", "ARC_FLASH", "NOISE", "HEAT_COLD", "BIOLOGICAL", "OTHER",
    },
    "accident_type": {
        "FALL", "SLIP", "COLLISION", "FALLING_OBJECT", "CRUSH", "CUT",
        "COLLAPSE", "ERGONOMIC", "OTHER",
    },
    "agent_state": {
        "ACTIVE_SOLO", "ACTIVE_PAIR", "ACTIVE_CREW", "STANDING_OBSERVATION", "OTHER",
    },
    "ppe_state": {
        # LLM이 자체적으로 추가한 변형도 허용 (SHE T-Box에 없는 코드는 OTHER로 normalize)
        "HELMET_WORN", "HELMET_MISSING", "HARNESS_TIED", "HARNESS_UNTIED",
        "GLOVE_WORN", "MASK_WORN", "GOGGLES_WORN", "OTHER",
    },
    "environmental": {
        "WET_SURFACE", "OIL_CONTAMINATION", "HIGH_ELEVATION", "LOW_LIGHT",
        "CLUTTERED", "WINDY_WEATHER", "EXTREME_TEMPERATURE", "OTHER",
    },
    "temporal_stage": {
        "BEFORE_WORK", "DURING_WORK", "AFTER_WORK", "EMERGENCY_STAGE", "OTHER",
    },
}

REQUIRED_DIMS = list(ALLOWED_CODES.keys())  # 8개

# Broadness gate (specificity ≥ 0.5 = 8 dim 중 ≥4개가 specific value)
BROADNESS_THRESHOLD = 0.5


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    @property
    def passed(self) -> bool:
        return not self.errors


def normalize_feature_value(dim: str, value: str) -> str:
    """LLM이 enum 외 변형을 만들면 OTHER로 normalize.

    예: ppe_state="MASK_MISSING" (enum 외) → "OTHER"
    """
    if value in ALLOWED_CODES.get(dim, set()):
        return value
    # alias mapping (자주 발생하는 변형)
    aliases = {
        "ppe_state": {
            "MASK_MISSING": "OTHER",      # MASK_WORN의 negation은 enum 없음
            "HELMET_OFF": "HELMET_MISSING",
            "HARNESS_NOT_TIED": "HARNESS_UNTIED",
        },
    }
    return aliases.get(dim, {}).get(value, "OTHER")


def validate_she(she: dict[str, Any]) -> tuple[ValidationResult, dict]:
    """Validate one SHE row.

    Returns:
      (result, normalized_she)
    """
    res = ValidationResult()
    she = dict(she)  # shallow copy

    # 1. 필수 필드
    if not she.get("she_id"):
        res.error("missing she_id")
    if not she.get("name"):
        res.error("missing name")
    features = she.get("features")
    if not features or not isinstance(features, dict):
        res.error("missing or invalid features")
        return res, she

    # 2. 8 dim 모두 존재
    for dim in REQUIRED_DIMS:
        if dim not in features:
            res.error(f"missing dim: {dim}")

    # 3. enum 검증 + normalization
    for dim in REQUIRED_DIMS:
        v = features.get(dim, "OTHER")
        normalized = normalize_feature_value(dim, v)
        if normalized != v:
            res.warn(f"dim {dim}: '{v}' normalized to '{normalized}'")
            features[dim] = normalized
        elif v not in ALLOWED_CODES[dim]:
            # 예외적으로 enum 외 + alias 미매칭 → OTHER
            res.warn(f"dim {dim}: unknown value '{v}' → OTHER")
            features[dim] = "OTHER"
    she["features"] = features

    # 4. broadness score (≥0.5 — 8 dim 중 4개 이상 specific)
    other_count = sum(1 for v in features.values() if v == "OTHER")
    broadness = 1.0 - (other_count / 8.0)
    she["broadness_score"] = round(broadness, 3)
    if broadness < BROADNESS_THRESHOLD:
        res.error(f"broadness {broadness:.2f} < threshold {BROADNESS_THRESHOLD} (OTHER count: {other_count}/8)")

    # 5. source SR 최소 1개 (orphan 방지)
    src_srs = she.get("source_sr_ids") or []
    if not src_srs:
        res.error("missing source_sr_ids (orphan SHE)")

    # 6. VisualTrigger seed. Legacy rows without visual_triggers use name as a reviewable fallback.
    visual_triggers = she.get("visual_triggers") or []
    if isinstance(visual_triggers, str):
        visual_triggers = [visual_triggers]
    visual_triggers = [v for v in visual_triggers if str(v).strip()]
    if not visual_triggers and she.get("name"):
        visual_triggers = [she["name"]]
        res.warn("missing visual_triggers; fallback to SHE name")
    if not visual_triggers:
        res.error("missing visual_triggers")
    she["visual_triggers"] = visual_triggers

    # 7. SHE ID format (SHE-{wc}-{hash10})
    she_id = she.get("she_id", "")
    if not she_id.startswith("SHE-") or len(she_id.split("-")) != 3:
        res.warn(f"she_id format atypical: {she_id}")

    return res, she


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-approved", type=Path, required=True)
    parser.add_argument("--output-rejected", type=Path, required=True)
    parser.add_argument("--deduplicate", action="store_true",
                        help="feature tuple exact match dedup")
    args = parser.parse_args()

    print(f"[INFO] input:    {args.input}")
    print(f"[INFO] approved: {args.output_approved}")
    print(f"[INFO] rejected: {args.output_rejected}")

    raw_shes = []
    with args.input.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw_shes.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [PARSE-ERR] line {i}: {e}")

    print(f"[INFO] loaded {len(raw_shes)} SHE drafts")

    # Validate + normalize
    approved: list[dict] = []
    rejected: list[dict] = []
    seen_hashes: set[str] = set()
    name_dup: dict[str, int] = defaultdict(int)
    dim_coverage: Counter = Counter()
    err_reasons: Counter = Counter()

    for she in raw_shes:
        res, normalized = validate_she(she)
        # Dedupe by exact she_id (feature_tuple_hash 이미 적용됨)
        sid = normalized.get("she_id", "")
        if args.deduplicate and sid in seen_hashes:
            res.warn("duplicate she_id (skipped)")
            err_reasons["duplicate"] += 1
            continue
        seen_hashes.add(sid)

        # Coverage (specific dim 카운트)
        features = normalized.get("features", {})
        for dim, v in features.items():
            if v != "OTHER":
                dim_coverage[dim] += 1

        # Name 중복 카운트
        name_dup[normalized.get("name", "")] += 1

        if res.passed:
            normalized["status"] = "approved_auto"
            normalized["validation_warnings"] = res.warnings or None
            approved.append(normalized)
        else:
            normalized["status"] = "rejected"
            normalized["validation_errors"] = res.errors
            normalized["validation_warnings"] = res.warnings or None
            rejected.append(normalized)
            for e in res.errors:
                if "broadness" in e:
                    err_reasons["broadness_low"] += 1
                elif "missing" in e:
                    err_reasons["missing_field"] += 1
                else:
                    err_reasons["other"] += 1

    # Save
    args.output_approved.parent.mkdir(parents=True, exist_ok=True)
    with args.output_approved.open("w", encoding="utf-8") as f:
        for s in approved:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    with args.output_rejected.open("w", encoding="utf-8") as f:
        for s in rejected:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # 통계
    print(f"\n[OK] {len(approved)} approved + {len(rejected)} rejected (= {len(raw_shes)})")
    print(f"     Pass rate: {100*len(approved)/max(len(raw_shes), 1):.1f}%")

    print(f"\n[Coverage by dim] (specific value 보유 SHE 수):")
    for dim in REQUIRED_DIMS:
        n = dim_coverage.get(dim, 0)
        pct = 100 * n / max(len(approved), 1)
        marker = "✓" if pct >= 80 else "✗"
        print(f"  {marker} {dim:20s} {n:5d} ({pct:5.1f}%) {'✓ ≥80%' if pct >= 80 else '✗ <80%'}")

    print(f"\n[Rejection reasons]:")
    for reason, n in err_reasons.most_common():
        print(f"  {reason:20s} {n:5d}")

    # Name 중복 (high dup count = LLM이 같은 패턴 반복)
    name_dups = [(n, c) for n, c in name_dup.items() if c >= 3]
    if name_dups:
        print(f"\n[Name dup (≥3)] (top 10):")
        for n, c in sorted(name_dups, key=lambda x: -x[1])[:10]:
            print(f"  {c:3d}x  {n[:80]}")

    # work_context 분포
    wc_dist = Counter(s.get("features", {}).get("work_context", "OTHER") for s in approved)
    print(f"\n[Approved work_context 분포]:")
    for wc, n in wc_dist.most_common():
        print(f"  {wc:25s} {n:5d}")

    # Pilot 3 wc 검증
    pilot_count = sum(wc_dist.get(wc, 0) for wc in ["SCAFFOLD", "EXCAVATION", "MACHINE"])
    print(f"\n[Pilot 3 wc] (SCAFFOLD+EXCAVATION+MACHINE) approved: {pilot_count}")


if __name__ == "__main__":
    main()
