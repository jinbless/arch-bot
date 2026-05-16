#!/usr/bin/env python3
"""Build conservative Stage2 NO_TOP SituationFrame support artifacts.

This script repairs a narrow class of NO_TOP cases where the synthetic Stage 1
substitute already names a specific work context, but Stage 2 collapses it into
a broad parent or drops it as a non-catalog feature.  The generated rows are
Guide ranking support only: they do not approve SHE patterns, do not affect
finding status or penalty exposure, and do not assert legal SR mappings.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "data-team/05-enrichment/eval-data"
    / "reports"
    / "stage2_5_no_top_root_cause_no_top_support_signal3.json"
)
DEFAULT_PROFILES = BACKEND_DIR / "app" / "data" / "guide_domain_profiles.json"
DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v2.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v3.jsonl"
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v3.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v4.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_no_top_support_candidates_v1"

ROOT_CAUSES = {
    "stage2_taxonomy_or_normalization_gap",
    "situation_frame_child_context_gap",
}
PHOTO_ACTIONABLE = "photo_actionable"
FIELD_CONTROL = "field_control"


@dataclass(frozen=True)
class ContextSeed:
    child_context: str
    parents: tuple[str, ...]
    aliases: tuple[str, ...]
    guide_codes: tuple[str, ...]
    source_sr_ids: tuple[str, ...]
    accident_type: str = "OTHER"
    hazardous_agent: str = "OTHER"
    confidence: float = 0.6
    rationale: str = ""
    trigger_terms: tuple[str, ...] = ()


CONTEXT_SEEDS: tuple[ContextSeed, ...] = (
    ContextSeed(
        child_context="HIGH_RISE_WINDOW",
        parents=("ROPE_ACCESS", "SCAFFOLD"),
        aliases=("고층 창문", "외부 유리창", "건물 외벽 청소", "곤돌라", "창틀", "앵커 포인트"),
        guide_codes=("G-67-2011",),
        source_sr_ids=("SR-FALL-003", "SR-WORKPLACE-008", "SR-SCAFFOLD-010", "SR-LIFTING-013"),
        accident_type="FALL",
        confidence=0.66,
        rationale="High-rise exterior window cleaning is photo-observable and directly matches exterior building cleaning controls.",
        trigger_terms=("안전대 없이 상체를 창밖", "곤돌라 와이어", "앵커 볼트 파손", "외부 유리창 청소"),
    ),
    ContextSeed(
        child_context="EXTERIOR_ROPE",
        parents=("ROPE_ACCESS", "SCAFFOLD"),
        aliases=("로프 접근", "외벽 청소", "로프 매듭", "로프 피복", "모서리 보호대"),
        guide_codes=("G-67-2011",),
        source_sr_ids=("SR-FALL-001", "SR-FALL-003", "SR-WORKPLACE-008"),
        accident_type="FALL",
        confidence=0.66,
        rationale="Rope-access exterior cleaning has a specific KOSHA Guide boundary and should not remain parent-only.",
        trigger_terms=("로프 접근", "로프 매듭", "로프 피복", "모서리 보호대", "통신 단절"),
    ),
    ContextSeed(
        child_context="CONFINED_SPACE_CLEANING",
        parents=("CONFINED_SPACE", "CHEMICAL_WORK"),
        aliases=("배기 덕트", "덕트 내부", "좁은 덕트", "밀폐공간"),
        guide_codes=("E-G-18-2026",),
        source_sr_ids=("SR-CONFINED-002", "SR-CONFINED-005", "SR-CONFINED-019"),
        accident_type="OTHER",
        hazardous_agent="CHEMICAL",
        confidence=0.64,
        rationale="Duct entry cleaning is a confined-space support signal, but remains Guide-only until SHE/SR evidence is reviewed.",
        trigger_terms=("배기 덕트 내부 청소", "좁은 덕트 내부", "환기 없이 몸이 끼여", "세제 증기"),
    ),
    ContextSeed(
        child_context="AIRLESS_SPRAYER",
        parents=("CHEMICAL_WORK", "PAINTING_WOODWORK"),
        aliases=("에어리스 스프레이어", "고압 도료", "도료 피부 침투"),
        guide_codes=("E-74-2011", "B-E-17-2026", "P-6-2011"),
        source_sr_ids=("SR-FIRE_EXPLOSION-007", "SR-FIRE_EXPLOSION-003"),
        accident_type="OTHER",
        hazardous_agent="CHEMICAL",
        confidence=0.62,
        rationale="Airless sprayer cases need spray-equipment/painting Guide support without asserting a new injection-injury SHE.",
        trigger_terms=("에어리스 스프레이어", "노즐 막힘", "압력 미해제", "잔압 도료", "핀홀", "피부 주사 침투"),
    ),
    ContextSeed(
        child_context="SPRAY_PAINTING",
        parents=("CHEMICAL_WORK", "PAINTING_WOODWORK"),
        aliases=("고압 스프레이 도장", "고압 도료", "도료 피부 침투"),
        guide_codes=("E-74-2011", "B-E-17-2026", "P-6-2011"),
        source_sr_ids=("SR-FIRE_EXPLOSION-007",),
        accident_type="OTHER",
        hazardous_agent="CHEMICAL",
        confidence=0.62,
        rationale="Spray painting is a photo-observable field-control context when the row explicitly shows spraying equipment.",
        trigger_terms=("압력이 과도하게 설정", "피부에 주사기 효과", "고압 도료", "피부 주사 침투"),
    ),
    ContextSeed(
        child_context="RESTROOM_CHEMICAL",
        parents=("CHEMICAL_WORK", "GENERAL_WORKPLACE"),
        aliases=("화장실 세정제", "변기 세정제", "강산성 변기 세정제"),
        guide_codes=("H-25-2011",),
        source_sr_ids=("SR-HAZMAT-010", "SR-HAZMAT-013"),
        accident_type="BURN",
        hazardous_agent="CHEMICAL",
        confidence=0.61,
        rationale="Restroom cleaning chemical exposure is better routed to building-cleaner field controls than generic chemical Guides.",
        trigger_terms=("강산성 변기 세정제", "세정제를 붓다가 튀어서 눈", "세정제 오염 손"),
    ),
    ContextSeed(
        child_context="CHEMICAL_MIXING_CLEANER",
        parents=("CHEMICAL_WORK", "GENERAL_WORKPLACE"),
        aliases=("세제 보충 라벨 불일치", "청소용 세제 라벨 불일치"),
        guide_codes=("H-25-2011",),
        source_sr_ids=("SR-HAZMAT-010",),
        accident_type="OTHER",
        hazardous_agent="CHEMICAL",
        confidence=0.58,
        rationale="Cleaner chemical relabeling is used as Guide support only, not as a legal SR assertion.",
        trigger_terms=("세제 보충", "원래 표시와 다른 세제", "라벨이 불일치", "빈 용기에 다른 세제"),
    ),
    ContextSeed(
        child_context="FLOUR_HANDLING",
        parents=("CHEMICAL_WORK", "MACHINE"),
        aliases=("밀가루", "곡분", "곡물분진", "분진 폭발"),
        guide_codes=("M-16-2012", "P-144-2014", "D-12-2012"),
        source_sr_ids=("SR-DUST-008", "SR-DUST-009", "SR-DUST-005"),
        accident_type="EXPLOSION",
        hazardous_agent="DUST",
        confidence=0.6,
        rationale="Flour handling is a visible grain/flour dust context; health-only Guides remain excluded from top photo procedures.",
        trigger_terms=("밀가루 창고", "25kg 포대", "대량의 밀가루 분진", "분진 폭발"),
    ),
    ContextSeed(
        child_context="COLD_ROOM_ACCESS",
        parents=("COLD_STORAGE", "CONFINED_SPACE"),
        aliases=("냉장실", "냉동실", "내부 비상 해제", "냉장실 갇힘"),
        guide_codes=("H-103-2012", "D-6-2012"),
        source_sr_ids=("SR-CONFINED-014", "SR-HEAT-013"),
        accident_type="OTHER",
        hazardous_agent="HEAT_COLD",
        confidence=0.58,
        rationale="Cold-room access is Guide support only because current Guide coverage is refrigeration-centered rather than retail cold storage.",
        trigger_terms=("냉장실", "방한복 없이", "내부에서 탈출할 수 없는", "바깥에서 잠겨", "저체온증"),
    ),
    ContextSeed(
        child_context="RECYCLING_SORT",
        parents=("MATERIAL_HANDLING", "MACHINE"),
        aliases=("재활용 캔 압착기", "캔 압착기", "비산 캔"),
        guide_codes=("G-131-2020", "G-6-2011"),
        source_sr_ids=("SR-WORKPLACE-004", "SR-WELFARE-001"),
        accident_type="COLLISION",
        hazardous_agent="OTHER",
        confidence=0.59,
        rationale="Waste sorting/compaction is photo-actionable for municipal/industrial waste field controls.",
        trigger_terms=("재활용 캔 압착기", "캔이 튀어", "얼굴 보호구 미착용", "비산 캔"),
    ),
    ContextSeed(
        child_context="LANDFILL_OPERATION",
        parents=("MATERIAL_HANDLING", "CONSTRUCTION_EQUIP"),
        aliases=("매립지", "폐기물 더미 사면", "매립지 중장비"),
        guide_codes=("G-6-2011", "G-131-2020"),
        source_sr_ids=("SR-WORKPLACE-004",),
        accident_type="COLLAPSE",
        hazardous_agent="OTHER",
        confidence=0.58,
        rationale="Landfill operation is a waste-site Guide support context, not a new approved SHE.",
        trigger_terms=("매립지", "폐기물 더미 사면", "중장비가 작업", "사면 붕괴"),
    ),
    ContextSeed(
        child_context="HIGH_PRESSURE_WASH",
        parents=("ELECTRICAL_WORK", "GENERAL_WORKPLACE"),
        aliases=("고압 세척기", "고압세척기", "고압 세척기 침수"),
        guide_codes=("E-2-2012", "E-100-2021"),
        source_sr_ids=("SR-ELECTRIC-004",),
        accident_type="ELECTRIC_SHOCK",
        hazardous_agent="ELECTRICITY",
        confidence=0.62,
        rationale="High-pressure electric washer in standing water has a specific electrical hazard Guide boundary.",
        trigger_terms=("고인 물 위에 놓인", "전기 모터 고압 세척기가 고인 물", "전기 세척기 침수 감전"),
    ),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _unique(values: list[Any] | tuple[Any, ...]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _compact_terms(rows: list[dict[str, Any]], seed: ContextSeed) -> list[str]:
    terms: list[str] = list(seed.trigger_terms)
    for row in rows:
        terms.extend([
            row.get("photo_description"),
            row.get("expected_primary_risk"),
            row.get("expected_corrective_direction"),
        ])
    return _unique(terms)[:24]


def _load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    data = _read_json(path)
    return data.get("profiles") or data


def _validated_guides(seed: ContextSeed, profiles: dict[str, dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    accepted: list[str] = []
    review: list[dict[str, Any]] = []
    for guide_code in seed.guide_codes:
        profile = profiles.get(guide_code)
        if not profile:
            review.append({"guide_code": guide_code, "decision": "reject", "reason": "missing_profile"})
            continue
        if profile.get("photo_matchability") != PHOTO_ACTIONABLE:
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": f"not_photo_actionable:{profile.get('photo_matchability')}",
            })
            continue
        if profile.get("procedure_role") != FIELD_CONTROL:
            review.append({
                "guide_code": guide_code,
                "decision": "reject",
                "reason": f"not_field_control:{profile.get('procedure_role')}",
            })
            continue
        accepted.append(guide_code)
        review.append({"guide_code": guide_code, "decision": "accept", "reason": "curated_stage2_child_context"})
    return accepted[:6], review


def _source_rows(rows: list[dict[str, Any]], seed: ContextSeed) -> list[dict[str, Any]]:
    accepted = []
    direct_contexts = {seed.child_context}
    if seed.child_context == "CHEMICAL_MIXING_CLEANER":
        direct_contexts.add("CHEMICAL_MIXING")
    for row in rows:
        if row.get("primary_root_cause") not in ROOT_CAUSES:
            continue
        if row.get("case_type") != "positive":
            continue
        if not row.get("expected_primary_risk"):
            continue
        if row.get("work_context") in direct_contexts:
            accepted.append(row)
    return accepted


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = _read_json(args.no_top_report)
    rows = report.get("rows") or []
    profiles = _load_profiles(args.profiles)
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)

    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []
    added_support_rows: list[dict[str, Any]] = []

    for seed in CONTEXT_SEEDS:
        source_rows = _source_rows(rows, seed)
        child_aliases = _unique([
            seed.child_context,
            seed.child_context.replace("_", " "),
            seed.child_context.lower(),
            seed.child_context.lower().replace("_", " "),
            *seed.aliases,
        ])
        child_contexts[seed.child_context] = {
            "parents": list(seed.parents),
            "aliases": child_aliases,
            "candidate_count": len(source_rows),
            "allowed_runtime_use": "guide_support_only",
        }
        aliases[seed.child_context] = child_aliases
        for parent in seed.parents:
            info = parent_contexts.setdefault(parent, {})
            info["allowed_runtime_use"] = "search_expansion_only"
            info["candidate_count"] = int(info.get("candidate_count") or 0) + len(source_rows)

        guide_codes, guide_review = _validated_guides(seed, profiles)
        case_ids = _unique([row.get("case_id") for row in source_rows])
        decision = "candidate" if source_rows and guide_codes else "taxonomy_only"
        if source_rows and guide_codes:
            support_id = f"STAGE2-NO-TOP-{seed.child_context}"
            support_row = {
                "support_id": support_id,
                "source_candidate_id": f"STAGE2-{seed.child_context}",
                "allowed_runtime_use": "guide_support_only",
                "child_context": seed.child_context,
                "parent_contexts": list(seed.parents),
                "accident_type": seed.accident_type,
                "hazardous_agent": seed.hazardous_agent,
                "trigger_terms": _compact_terms(source_rows, seed),
                "require_trigger_match": True,
                "guide_codes": guide_codes,
                "source_sr_ids": list(seed.source_sr_ids),
                "candidate_labels": ["stage2_taxonomy_gap", "guide_support_only", "no_top_repair_preview"],
                "confidence": seed.confidence,
                "evidence": seed.rationale,
                "review_status": "candidate",
                "policy": "stage2_support_only_no_status_penalty_no_asserted_sr",
                "source_no_top_cases": case_ids,
                "guide_review": [item for item in guide_review if item.get("decision") == "accept"],
            }
            support_by_id[support_id] = support_row
            added_support_rows.append(support_row)

        audit_rows.append({
            "child_context": seed.child_context,
            "decision": decision,
            "case_count": len(source_rows),
            "case_ids": case_ids,
            "domain_buckets": dict(Counter(row.get("domain_bucket") for row in source_rows)),
            "root_causes": dict(Counter(row.get("primary_root_cause") for row in source_rows)),
            "accepted_guide_codes": guide_codes,
            "guide_review": guide_review,
            "aliases": child_aliases,
            "source_sr_ids": list(seed.source_sr_ids),
        })

    merged_support_rows = sorted(
        support_by_id.values(),
        key=lambda row: (str(row.get("child_context") or ""), str(row.get("support_id") or "")),
    )
    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v3"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_no_top_support": {
            "runtime_use": "guide_support_only",
            "status_penalty_update": 0,
            "asserted_mapping_update": 0,
            "parent_only_match": "blocked",
            "source_baseline": str(args.no_top_report),
        },
    }
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_jsonl(args.support_output, merged_support_rows)

    child_counts = Counter(row.get("child_context") for row in added_support_rows)
    guide_counts = Counter(
        guide_code
        for row in added_support_rows
        for guide_code in (row.get("guide_codes") or [])
    )
    summary = {
        "generated_at": generated_at,
        "policy": {
            "input_scope": sorted(ROOT_CAUSES),
            "runtime_use": "guide_support_only",
            "status_penalty_update": 0,
            "asserted_mapping_update": 0,
            "parent_only_match": "blocked",
            "base_taxonomy": str(args.base_taxonomy),
            "base_support": str(args.base_support),
        },
        "input_no_top_rows": len(rows),
        "curated_contexts": len(CONTEXT_SEEDS),
        "taxonomy_child_context_count": len(child_contexts),
        "base_support_rows": len(support_rows),
        "added_support_rows": len(added_support_rows),
        "merged_support_rows": len(merged_support_rows),
        "covered_no_top_case_count": len({case for row in added_support_rows for case in row.get("source_no_top_cases") or []}),
        "added_child_context_counts": dict(child_counts.most_common()),
        "added_guide_code_counts": dict(guide_counts.most_common()),
        "outputs": {
            "taxonomy": str(args.taxonomy_output),
            "support_candidates": str(args.support_output),
        },
        "audit_rows": audit_rows,
    }
    return summary


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Stage2 NO_TOP Support Candidates v1",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Input NO_TOP rows: `{summary['input_no_top_rows']}`",
        f"- Curated contexts: `{summary['curated_contexts']}`",
        f"- Added support rows: `{summary['added_support_rows']}`",
        f"- Merged support rows: `{summary['merged_support_rows']}`",
        f"- Covered NO_TOP cases: `{summary['covered_no_top_case_count']}`",
        "- Status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Added Contexts",
        "",
    ]
    for row in summary["audit_rows"]:
        lines.append(
            f"- `{row['child_context']}` {row['decision']} "
            f"cases={row['case_count']} guides={','.join(row['accepted_guide_codes']) or '-'}"
        )
    lines.extend(["", "## Added Guide Counts", ""])
    for guide_code, count in summary["added_guide_code_counts"].items():
        lines.append(f"- `{guide_code}`: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    fieldnames = [
        "child_context",
        "decision",
        "case_count",
        "case_ids",
        "accepted_guide_codes",
        "domain_buckets",
        "root_causes",
        "source_sr_ids",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary["audit_rows"]:
            writer.writerow({
                "child_context": row.get("child_context"),
                "decision": row.get("decision"),
                "case_count": row.get("case_count"),
                "case_ids": ";".join(row.get("case_ids") or []),
                "accepted_guide_codes": ";".join(row.get("accepted_guide_codes") or []),
                "domain_buckets": json.dumps(row.get("domain_buckets") or {}, ensure_ascii=False, sort_keys=True),
                "root_causes": json.dumps(row.get("root_causes") or {}, ensure_ascii=False, sort_keys=True),
                "source_sr_ids": ";".join(row.get("source_sr_ids") or []),
            })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build(args)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, summary)
    write_csv(csv_path, summary)
    print("=== Stage2 NO_TOP Support Candidate Build ===")
    print(f"curated_contexts: {summary['curated_contexts']}")
    print(f"added_support_rows: {summary['added_support_rows']}")
    print(f"covered_no_top_case_count: {summary['covered_no_top_case_count']}")
    print(f"merged_support_rows: {summary['merged_support_rows']}")
    print(f"taxonomy_child_context_count: {summary['taxonomy_child_context_count']}")
    print(f"wrote: {args.taxonomy_output}")
    print(f"wrote: {args.support_output}")
    print(f"wrote: {json_path}")
    print(f"wrote: {md_path}")
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    sys.exit(main())
