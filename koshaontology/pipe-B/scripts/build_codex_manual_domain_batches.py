#!/usr/bin/env python3
"""Build local Codex manual enrichment batch drafts.

This helper does not call external APIs and does not write to PostgreSQL.
It creates candidate-only JSON/MD files that can be globally audited before
any import into the candidate tables.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
CI_OUTPUT_DIR = DATA_DIR / "ci-output"
INVENTORY = DATA_DIR / "guide-inventory.json"
METHOD = "codex_manual_pilot"
BATCH_SIZE = 30


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm(text: Any) -> str:
    if text is None:
        return ""
    if isinstance(text, dict):
        return " ".join(f"{k} {v}" for k, v in text.items())
    if isinstance(text, list):
        return " ".join(norm(v) for v in text)
    return str(text)


def truncate(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def ci_path(short_code: str) -> Path:
    return CI_OUTPUT_DIR / f"ci-{short_code}.json"


def source_blocks(guide: dict[str, Any], title: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = [("title", title)]
    for item in guide.get("workProcesses") or []:
        if item.get("processName"):
            blocks.append(("workProcesses.processName", norm(item.get("processName"))))
        if item.get("safetyMeasures"):
            blocks.append(("workProcesses.safetyMeasures", norm(item.get("safetyMeasures"))))
    for item in guide.get("domainTerms") or []:
        if item.get("term"):
            blocks.append(("domainTerms.term", norm(item.get("term"))))
        if item.get("definition"):
            blocks.append(("domainTerms.definition", norm(item.get("definition"))))
    for item in guide.get("equipmentSpecs") or []:
        if item.get("equipmentName"):
            blocks.append(("equipmentSpecs.equipmentName", norm(item.get("equipmentName"))))
        if item.get("specifications"):
            blocks.append(("equipmentSpecs.specifications", norm(item.get("specifications"))))
    for item in guide.get("checklistItems") or []:
        if item.get("text"):
            blocks.append(("checklistItems.text", norm(item.get("text"))))
    return blocks


def profile_source_blocks(guide: dict[str, Any], title: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = [("title", title)]
    for item in guide.get("domainTerms") or []:
        if item.get("term"):
            blocks.append(("domainTerms.term", norm(item.get("term"))))
        if item.get("definition"):
            blocks.append(("domainTerms.definition", norm(item.get("definition"))))
    for item in guide.get("equipmentSpecs") or []:
        if item.get("equipmentName"):
            blocks.append(("equipmentSpecs.equipmentName", norm(item.get("equipmentName"))))
    return blocks


def find_evidence(blocks: list[tuple[str, str]], keywords: list[str], fallback: str) -> tuple[str, list[str]]:
    for source, text in blocks:
        for keyword in keywords:
            if keyword and keyword.lower() in text.lower():
                return truncate(text), [source]
    return truncate(fallback), ["title"]


PROFILE_RULES: list[dict[str, Any]] = [
    {
        "family": "chemical_measurement_analysis",
        "level": "exclusive",
        "terms": ["작업환경측정", "시료채취", "검량선", "XRD"],
    },
    {"family": "silica_dust_work", "level": "exclusive", "terms": ["결정형 유리규산", "유리규산", "실리카", "석영"]},
    {
        "family": "chemical_handling",
        "level": "exclusive",
        "terms": [
            "화학물질",
            "유해화학물질",
            "독성물질",
            "MSDS",
            "물질안전보건자료",
            "인화성 액체",
            "염소",
            "시안",
            "과산화수소",
            "염산",
            "황산",
            "질산",
            "불산",
            "알칼리",
            "유기용제",
            "용제",
        ],
    },
    {"family": "hot_work_fire", "level": "domain_specific", "terms": ["용접", "용단", "화기작업", "불티", "방화포"]},
    {"family": "fire_explosion_prevention", "level": "domain_specific", "terms": ["화재", "폭발", "인화성", "가연성", "방폭"]},
    {"family": "electrical_work", "level": "domain_specific", "terms": ["전기", "감전", "접지", "피뢰", "조명", "방폭전기", "변전"]},
    {"family": "fall_access_work", "level": "domain_specific", "terms": ["추락", "떨어짐", "사다리", "계단", "경사로", "비계", "고소"]},
    {"family": "crane_lifting_rigging", "level": "domain_specific", "terms": ["크레인", "인양", "양중", "슬링", "줄걸이", "권상"]},
    {"family": "vehicle_transport", "level": "domain_specific", "terms": ["차량", "지게차", "오토바이", "운반차량", "트럭", "트레일러"]},
    {"family": "warehouse_material_handling", "level": "domain_specific", "terms": ["창고", "물류", "적재", "하역", "중량물", "운반"]},
    {"family": "food_service", "level": "exclusive", "terms": ["급식", "조리", "주방", "배식", "식자재"]},
    {"family": "agriculture_farm_work", "level": "domain_specific", "terms": ["농장", "농업", "경운", "트랙터", "수목", "벌목"]},
    {"family": "machine_safety", "level": "domain_specific", "terms": ["기계", "선반", "프레스", "컨베이어", "로봇", "가드"]},
    {"family": "biological_healthcare", "level": "exclusive", "terms": ["병원체", "혈액", "감염", "의료", "실험실"]},
    {"family": "administrative_management", "level": "general", "terms": ["관리체계", "리스크 평가", "위험성평가", "기록", "분류", "교육훈련", "벤치마킹"]},
]


FEATURE_RULES: list[dict[str, Any]] = [
    {"axis": "work_context", "code": "WELDING", "terms": ["용접", "용단", "화기작업"], "confidence": 0.84},
    {"axis": "hazardous_agent", "code": "FIRE", "terms": ["화재", "불티", "가연성", "인화성"], "confidence": 0.82},
    {"axis": "accident_type", "code": "EXPLOSION", "terms": ["폭발", "폭발위험", "분진폭발"], "confidence": 0.82},
    {"axis": "hazardous_agent", "code": "CHEMICAL", "terms": ["화학", "유해물질", "독성", "염소", "시안", "과산화수소", "요오드", "바나듐", "실리카", "분진"], "confidence": 0.82},
    {"axis": "accident_type", "code": "CHEMICAL_EXPOSURE", "terms": ["노출", "시료채취", "분진", "유해물질", "중독"], "confidence": 0.76},
    {"axis": "hazardous_agent", "code": "BIOLOGICAL", "terms": ["병원체", "혈액", "감염", "바이러스", "세균"], "confidence": 0.84},
    {"axis": "hazardous_agent", "code": "ELECTRICITY", "terms": ["전기", "접지", "피뢰", "방폭전기", "변전", "조명"], "confidence": 0.80},
    {"axis": "accident_type", "code": "ELECTRIC_SHOCK", "terms": ["감전", "누전", "충전부"], "confidence": 0.80},
    {"axis": "work_context", "code": "ELECTRICAL_WORK", "terms": ["전기", "접지", "조명", "방폭전기", "변전"], "confidence": 0.78},
    {"axis": "accident_type", "code": "FALL", "terms": ["추락", "떨어짐", "사다리", "계단", "고소", "비계"], "confidence": 0.84},
    {"axis": "work_context", "code": "LADDER", "terms": ["사다리", "발판사다리", "고정식 사다리"], "confidence": 0.82},
    {"axis": "work_context", "code": "SCAFFOLD", "terms": ["비계", "작업발판", "강관비계", "시스템비계"], "confidence": 0.84},
    {"axis": "accident_type", "code": "COLLAPSE", "terms": ["붕괴", "도괴", "무너짐", "지반", "흙막이"], "confidence": 0.78},
    {"axis": "work_context", "code": "EXCAVATION", "terms": ["굴착", "터파기", "매설물"], "confidence": 0.84},
    {"axis": "work_context", "code": "CRANE", "terms": ["크레인", "인양", "양중", "항타기", "타워크레인"], "confidence": 0.84},
    {"axis": "work_context", "code": "HEAVY_LIFTING", "terms": ["중량물", "들기", "인력운반", "권상"], "confidence": 0.80},
    {"axis": "accident_type", "code": "FALLING_OBJECT", "terms": ["낙하", "물체에 맞음", "하중", "줄걸이"], "confidence": 0.78},
    {"axis": "work_context", "code": "FORKLIFT_OPERATION", "terms": ["지게차"], "confidence": 0.84},
    {"axis": "work_context", "code": "VEHICLE", "terms": ["차량", "트럭", "트레일러", "오토바이", "경운기"], "confidence": 0.78},
    {"axis": "accident_type", "code": "COLLISION", "terms": ["충돌", "후진", "차량", "운행"], "confidence": 0.74},
    {"axis": "work_context", "code": "DELIVERY_RIDER", "terms": ["배달", "오토바이"], "confidence": 0.84},
    {"axis": "work_context", "code": "FARM_MACHINERY", "terms": ["경운기", "농업용 기계", "농장", "트랙터"], "confidence": 0.80},
    {"axis": "work_context", "code": "KITCHEN_COOKING", "terms": ["조리", "급식", "주방", "가스레인지"], "confidence": 0.82},
    {"axis": "work_context", "code": "FOOD_PREP", "terms": ["식자재", "전처리", "배식"], "confidence": 0.78},
    {"axis": "work_context", "code": "WET_FLOOR_WORK", "terms": ["세척", "물기", "청소", "미끄럼"], "confidence": 0.74},
    {"axis": "work_context", "code": "STORAGE_SHELF", "terms": ["창고", "선반", "적재대", "보관"], "confidence": 0.78},
    {"axis": "work_context", "code": "PACKAGE_SORTING", "terms": ["분류", "선별", "물류"], "confidence": 0.72},
    {"axis": "work_context", "code": "MATERIAL_HANDLING", "terms": ["운반", "하역", "적재", "화물"], "confidence": 0.78},
    {"axis": "work_context", "code": "CONVEYOR", "terms": ["컨베이어"], "confidence": 0.84},
    {"axis": "accident_type", "code": "CRUSH", "terms": ["끼임", "협착", "컨베이어", "프레스"], "confidence": 0.78},
    {"axis": "work_context", "code": "MACHINE", "terms": ["기계", "선반", "프레스", "가드"], "confidence": 0.76},
    {"axis": "work_context", "code": "VENTILATION_POOR", "terms": ["환기", "국소배기", "공기질"], "confidence": 0.76},
    {"axis": "hazardous_agent", "code": "NOISE", "terms": ["소음", "귀마개", "귀덮개"], "confidence": 0.72},
    {"axis": "work_context", "code": "NOISE_EXPOSURE", "terms": ["소음", "진동"], "confidence": 0.72},
    {"axis": "work_context", "code": "GENERAL_WORKPLACE", "terms": ["작업장", "사업장", "안전보건", "위험성평가"], "confidence": 0.66},
]


def select_profile(title: str, blocks: list[tuple[str, str]], short_code: str) -> dict[str, Any]:
    blob = " ".join(text for _, text in blocks)
    for rule in PROFILE_RULES:
        if any(term.lower() in blob.lower() for term in rule["terms"]):
            evidence, fields = find_evidence(blocks, rule["terms"], title)
            return {
                "profile_level": rule["level"],
                "domain_family": rule["family"],
                "mismatch_policy": {
                    "exclusive": "exclude_without_required_context",
                    "domain_specific": "penalize_without_required_context",
                    "general": "allow_with_low_boost",
                }[rule["level"]],
                "required_context_terms": rule["terms"][:8],
                "evidence": evidence,
                "source_fields": fields,
                "confidence": 0.84 if rule["level"] == "exclusive" else 0.78 if rule["level"] == "domain_specific" else 0.70,
            }
    evidence, fields = find_evidence(blocks, [title.split()[0] if title.split() else short_code], title)
    return {
        "profile_level": "general",
        "domain_family": f"general_{short_code.lower()}",
        "mismatch_policy": "allow_with_low_boost",
        "required_context_terms": [title],
        "evidence": evidence,
        "source_fields": fields,
        "confidence": 0.64,
    }


def select_features(
    guide_code: str,
    title: str,
    blocks: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    blob = " ".join(text for _, text in blocks)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for rule in FEATURE_RULES:
        if not any(term.lower() in blob.lower() for term in rule["terms"]):
            continue
        key = (rule["axis"], rule["code"])
        if key in seen:
            continue
        evidence, fields = find_evidence(blocks, rule["terms"], title)
        review_status = "candidate" if rule["confidence"] >= 0.70 else "needs_review"
        candidates.append({
            "entity_type": "GUIDE",
            "entity_id": guide_code,
            "guide_code": guide_code,
            "axis": rule["axis"],
            "feature_code": rule["code"],
            "confidence": rule["confidence"],
            "evidence": evidence,
            "source_fields": fields,
            "method": METHOD,
            "review_status": review_status,
            "non_llm_evidence_count": 0,
        })
        seen.add(key)
        if len(candidates) == 2:
            return candidates

    fallback_rules = [
        {"axis": "work_context", "code": "GENERAL_WORKPLACE", "confidence": 0.60},
        {"axis": "accident_type", "code": "ERGONOMIC", "confidence": 0.55},
    ]
    for rule in fallback_rules:
        key = (rule["axis"], rule["code"])
        if key in seen:
            continue
        candidates.append({
            "entity_type": "GUIDE",
            "entity_id": guide_code,
            "guide_code": guide_code,
            "axis": rule["axis"],
            "feature_code": rule["code"],
            "confidence": rule["confidence"],
            "evidence": truncate(title),
            "source_fields": ["title"],
            "method": METHOD,
            "review_status": "needs_review",
            "non_llm_evidence_count": 0,
        })
        seen.add(key)
        if len(candidates) == 2:
            return candidates
    return candidates


def collect_sr_candidates(guide: dict[str, Any], guide_code: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in guide.get("workProcesses") or []:
        for sr_id in item.get("relatedSR") or []:
            if sr_id in seen:
                continue
            evidence = truncate(norm(item.get("processName") or item.get("safetyMeasures") or sr_id))
            candidates.append({
                "entity_type": "GUIDE",
                "entity_id": guide_code,
                "guide_code": guide_code,
                "sr_id": sr_id,
                "confidence": 0.78,
                "evidence": evidence,
                "source_fields": ["workProcesses.relatedSR", "workProcesses.processName"],
                "method": METHOD,
                "review_status": "candidate",
                "non_llm_evidence_count": 0,
                "asserted": False,
            })
            seen.add(sr_id)
            if len(candidates) == 2:
                return candidates
    for item in guide.get("checklistItems") or []:
        for sr_id in item.get("basedOn") or []:
            if sr_id in seen:
                continue
            candidates.append({
                "entity_type": "GUIDE",
                "entity_id": guide_code,
                "guide_code": guide_code,
                "sr_id": sr_id,
                "confidence": 0.74,
                "evidence": truncate(norm(item.get("text") or sr_id)),
                "source_fields": ["checklistItems.basedOn", "checklistItems.text"],
                "method": METHOD,
                "review_status": "candidate",
                "non_llm_evidence_count": 0,
                "asserted": False,
            })
            seen.add(sr_id)
            if len(candidates) == 2:
                return candidates
    return candidates


def trigger_text_from(value: str, fallback: str) -> str:
    text = re.sub(r"\([^)]*\)", "", value)
    text = re.sub(r"[·/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    if not text:
        text = fallback
    return truncate(text, 70)


def collect_triggers(guide: dict[str, Any], guide_code: str, title: str) -> list[dict[str, Any]]:
    raw_values: list[tuple[str, str, str]] = [("title", "workplace_or_activity", title)]
    for item in guide.get("domainTerms") or []:
        if item.get("term"):
            raw_values.append(("domainTerms.term", "domain_term", norm(item.get("term"))))
    for item in guide.get("workProcesses") or []:
        if item.get("processName"):
            raw_values.append(("workProcesses.processName", "work_activity", norm(item.get("processName"))))
    triggers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source, cue_type, value in raw_values:
        trigger = trigger_text_from(value, title)
        if trigger in seen:
            continue
        triggers.append({
            "entity_type": "GUIDE",
            "entity_id": guide_code,
            "guide_code": guide_code,
            "trigger_text": trigger,
            "cue_type": cue_type,
            "confidence": 0.76 if source == "title" else 0.72,
            "evidence": truncate(value),
            "source_fields": [source],
            "method": METHOD,
            "review_status": "candidate",
        })
        seen.add(trigger)
        if len(triggers) == 2:
            return triggers
    while len(triggers) < 2:
        triggers.append({
            "entity_type": "GUIDE",
            "entity_id": guide_code,
            "guide_code": guide_code,
            "trigger_text": truncate(title, 70),
            "cue_type": "document_or_context",
            "confidence": 0.55,
            "evidence": truncate(title),
            "source_fields": ["title"],
            "method": METHOD,
            "review_status": "needs_review",
        })
    return triggers


def build_guide(entry: dict[str, Any]) -> dict[str, Any]:
    guide_code = entry["guideCode"]
    short_code = entry["shortCode"]
    title = entry.get("title") or guide_code
    path = ci_path(short_code)
    guide = read_json(path) if path.exists() else {"workProcesses": [], "domainTerms": [], "checklistItems": []}
    blocks = source_blocks(guide, title)
    profile_blocks = profile_source_blocks(guide, title)
    return {
        "guide_code": guide_code,
        "short_code": short_code,
        "title": title,
        "source_file": f"pipe-B/data/ci-output/ci-{short_code}.json",
        "domain_profile": select_profile(title, profile_blocks, short_code),
        "feature_candidates": select_features(guide_code, title, blocks),
        "sr_link_candidates": collect_sr_candidates(guide, guide_code),
        "visual_trigger_candidates": collect_triggers(guide, guide_code, title),
    }


def batch_number(path: Path) -> int | None:
    match = re.search(r"batch-(\d+)\.json$", path.name)
    if not match:
        return None
    return int(match.group(1))


def existing_processed_codes(before_batch: int | None = None) -> set[str]:
    codes: set[str] = set()
    for path in sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json")):
        number = batch_number(path)
        if before_batch is not None and number is not None and number >= before_batch:
            continue
        data = read_json(path)
        for guide in data.get("guides") or []:
            code = guide.get("guide_code")
            if code:
                codes.add(code)
    return codes


def write_md(path: Path, data: dict[str, Any]) -> None:
    guides = data["guides"]
    no_sr = [g["guide_code"] for g in guides if not g.get("sr_link_candidates")]
    profiles = "\n".join(
        f"| {g['guide_code']} | {g['domain_profile']['profile_level']} | {g['domain_profile']['domain_family']} |"
        for g in guides
    )
    body = f"""# Manual Enrichment Domain Guard {data['scope']['batch_id'].replace('_', ' ').title()}

Generated: {data['generated_at']}

This batch is a Codex manual candidate draft generated locally from extracted Guide JSON. It did not call an external API, did not update PostgreSQL, and did not update asserted mapping tables.

## Output

```text
JSON: {path.with_suffix('.json').relative_to(PIPE_B_ROOT)}
method: {METHOD}
review_status: candidate / needs_review
asserted_mapping_updates: 0
selection_policy: {data['scope']['selection_policy']}
```

## Counts

| Item | Count |
|---|---:|
| Guides reviewed | {len(guides)} |
| Guide domain profiles | {len(guides)} |
| Feature candidates | {sum(len(g['feature_candidates']) for g in guides)} |
| SR link candidates | {sum(len(g['sr_link_candidates']) for g in guides)} |
| Visual trigger candidates | {sum(len(g['visual_trigger_candidates']) for g in guides)} |
| Guides with no SR candidate | {len(no_sr)} |

Guides with no SR candidate:

```text
{chr(10).join(no_sr) if no_sr else '(none)'}
```

## Domain Profiles

| Guide | Level | Domain family |
|---|---|---|
{profiles}

## Import Guidance

Do not import this batch alone. Accumulate all batches, run a global audit, normalize duplicate domain families, then import all candidate rows together with `method='codex_manual_pilot'`.
"""
    path.write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-batch", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Overwrite batches from --start-batch onward while preserving earlier batch selections.",
    )
    args = parser.parse_args()

    inventory = read_json(INVENTORY)["guides"]
    processed = existing_processed_codes(args.start_batch if args.replace_existing else None)
    pending = [entry for entry in inventory if entry.get("guideCode") not in processed]
    if not pending:
        print("No pending guides.")
        return 0

    chunks = [pending[i:i + args.batch_size] for i in range(0, len(pending), args.batch_size)]
    if not args.all:
        chunks = chunks[:1]

    for offset, chunk in enumerate(chunks):
        batch_no = args.start_batch + offset
        batch_id = f"domain_guard_manual_batch_{batch_no:03d}"
        data = {
            "schema_version": "codex_manual_pilot.v1",
            "generated_at": "2026-05-09",
            "method": METHOD,
            "asserted_mapping_updates": 0,
            "review_status": "candidate",
            "scope": {
                "batch_id": batch_id,
                "guide_count": len(chunk),
                "source": "pipe-B/data/ci-output plus pipe-B/data/guide-inventory.json",
                "selection_policy": "inventory order excluding prior manual batches",
                "purpose": "Guide domain/profile guard enrichment without external API calls",
            },
            "policies": {
                "external_api_used": False,
                "candidate_table_ready": True,
                "auto_asserted_promotion": False,
                "max_confidence_for_manual_sr_link": 0.86,
                "notes": [
                    "Generated locally from extracted Guide JSON.",
                    "Candidate rows require global audit before import.",
                    "Rows must not be promoted to asserted mapping tables from this report.",
                ],
            },
            "guides": [build_guide(entry) for entry in chunk],
        }
        json_path = DATA_DIR / f"manual-enrichment-domain-guard-batch-{batch_no:03d}.json"
        md_path = json_path.with_suffix(".md")
        write_json(json_path, data)
        write_md(md_path, data)
        print(f"wrote {json_path.relative_to(PIPE_B_ROOT)} ({len(chunk)} guides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
