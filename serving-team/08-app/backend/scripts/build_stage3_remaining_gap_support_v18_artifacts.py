#!/usr/bin/env python3
"""Build narrow v18 Guide-support artifacts for remaining NO_TOP cases.

v18 starts from the accepted v17b artifacts and only adds or tightens
trigger-backed Guide support rows.  These rows are support-only: they must not
change finding status, penalty exposure, approved SHE patterns, asserted SR
mappings, or legal SR evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_stage2_3_support_v8_artifacts import (
    BACKEND_DIR,
    PROJECT_ROOT,
    SupportSeed,
    _merge,
    _read_json,
    _read_jsonl,
    _source_rows,
    _unique,
    _write_jsonl,
)


DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v17b.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v17b.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT
    / "data-team/05-enrichment/eval-data"
    / "reports"
    / "stage2_5_no_top_root_cause_stage3_remaining_gap_support_v17b_narrow9b.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v18.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v18.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage3_remaining_gap_support_v18_artifacts_narrow10"


SUPPORT_ROW_TRIGGER_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "STAGE3-REMAINING-GAP-SUPPORT-V17B-BINDING_MACHINE_LOTO_GAP": (
        "기계 미정지",
        "용지 걸림 제거",
        "침 박음 장치 근처",
        "작업자가 용지 걸림 제거",
    ),
}


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="INDUSTRIAL_WASHER_VIBRATION_CRUSH",
        parents=("MACHINE", "WASHING_MACHINE", "LAUNDRY_WORK"),
        aliases=("산업용 세탁기 진동", "세탁기 진동", "기계가 이동", "벽으로 밀어붙", "좁은 통로"),
        profile_alignment_aliases=("회전기계", "진동감시", "진동", "방호설비", "기계 이동", "세탁기"),
        guide_codes=("B-M-37-2026",),
        source_sr_ids=("SR-MACHINE-001", "SR-MACHINE-002", "SR-MACHINE-004"),
        trigger_terms=("산업용 세탁기 진동", "기계가 이동", "벽으로 밀어붙", "좁은 통로"),
        source_case_ids=("SYN-V5-0012",),
        confidence=0.64,
        rationale="Industrial washer vibration/movement causing crush risk is narrow rotating-machine/vibration Guide support.",
    ),
    SupportSeed(
        child_context="GARMENT_SHARP_OBJECT_PUNCTURE",
        parents=("SHARP_OBJECT", "GARMENT_SORTING", "PPE"),
        aliases=("날카로운 브로치", "브로치 제거", "장갑 없이 손으로 제거", "찔리는", "날카로운 부착물"),
        profile_alignment_aliases=("개인보호구", "보호장갑", "찔림", "날카로운 물체", "보호구 착용"),
        guide_codes=("A-G-12-2026",),
        source_sr_ids=("SR-PPE-002", "SR-CARGO-001"),
        trigger_terms=("날카로운 브로치", "장갑 없이 손으로 제거", "찔리는"),
        source_case_ids=("SYN-V5-0026",),
        confidence=0.62,
        rationale="Sharp brooch removal without gloves is retained as narrow PPE support, not a broad cargo/handling Guide.",
    ),
    SupportSeed(
        child_context="EV_BATTERY_HIGH_VOLTAGE_PPE_GAP",
        parents=("EV_BATTERY", "ELECTRICAL_WORK"),
        aliases=("고전압 배터리", "400V", "전기 단자", "일반 면 장갑", "배터리 교체"),
        profile_alignment_aliases=("충전전로", "고전압", "절연 보호구", "전기 단자", "활선", "정전전로"),
        guide_codes=("B-E-11-2026", "E-115-2011", "B-E-10-2026"),
        source_sr_ids=("SR-ELECTRIC-007", "SR-ELECTRIC-010", "SR-ELECTRIC-014"),
        trigger_terms=("고전압 배터리", "400V", "일반 면 장갑", "전기 단자"),
        source_case_ids=("SYN-V7-0316",),
        confidence=0.64,
        rationale="High-voltage EV battery terminal contact with cotton gloves is narrow electrical/PPE support only.",
    ),
    SupportSeed(
        child_context="COLD_ROOM_EMERGENCY_RELEASE_FAILURE",
        parents=("COLD_ROOM_ACCESS", "COLD_STORAGE"),
        aliases=("비상 탈출 레버", "탈출 레버 고장", "냉장 창고", "혼자 창고", "문이 닫히는"),
        profile_alignment_aliases=("냉장실", "냉동실", "비상 탈출", "내부 탈출", "비상 연락", "저온작업"),
        guide_codes=("H-103-2012", "D-6-2012"),
        source_sr_ids=("SR-CONFINED-003", "SR-CONFINED-004", "SR-WORKPLACE-018"),
        trigger_terms=("비상 탈출 레버", "고장 난 상태", "혼자 창고", "문이 닫히는"),
        source_case_ids=("SYN-V8-0207",),
        confidence=0.64,
        rationale="Cold-storage emergency-release failure is a narrow cold-room access/entrapment support signal.",
    ),
)


def build(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    taxonomy = _read_json(args.base_taxonomy)
    support_rows = _read_jsonl(args.base_support)
    no_top_rows = (_read_json(args.no_top_report).get("rows") or [])

    child_contexts = taxonomy.setdefault("child_contexts", {})
    parent_contexts = taxonomy.setdefault("parent_contexts", {})
    aliases = taxonomy.setdefault("aliases", {})
    support_by_id = {row.get("support_id"): row for row in support_rows if row.get("support_id")}
    audit_rows: list[dict[str, Any]] = []

    for support_id, terms in SUPPORT_ROW_TRIGGER_EXTENSIONS.items():
        row = support_by_id.get(support_id)
        if not row:
            continue
        row["trigger_terms"] = _merge(row.get("trigger_terms") or [], terms)
        row["candidate_labels"] = _merge(row.get("candidate_labels") or [], ("v18_trigger_tightening",))
        audit_rows.append({
            "child_context": row.get("child_context"),
            "case_count": 0,
            "source_case_ids": row.get("source_no_top_cases") or [],
            "guide_codes": row.get("guide_codes") or [],
            "source_sr_ids": row.get("source_sr_ids") or [],
            "trigger_terms": list(terms),
            "rationale": "Existing support row trigger terms tightened to match the actual remaining NO_TOP wording.",
        })

    for seed in SUPPORT_SEEDS:
        source_rows = _source_rows(no_top_rows, seed.source_case_ids)
        child_aliases = _unique([
            seed.child_context,
            seed.child_context.replace("_", " "),
            seed.child_context.lower(),
            seed.child_context.lower().replace("_", " "),
            *seed.aliases,
        ])
        info = child_contexts.setdefault(seed.child_context, {})
        info["parents"] = _merge(info.get("parents") or [], seed.parents)
        info["aliases"] = _merge(info.get("aliases") or [], child_aliases)
        info["profile_alignment_aliases"] = _merge(
            info.get("profile_alignment_aliases") or [],
            seed.profile_alignment_aliases,
        )
        info["candidate_count"] = int(info.get("candidate_count") or 0) + len(source_rows)
        info["allowed_runtime_use"] = "guide_support_only"
        aliases[seed.child_context] = _merge(aliases.get(seed.child_context) or [], child_aliases)
        for parent in seed.parents:
            parent_info = parent_contexts.setdefault(parent, {})
            parent_info["allowed_runtime_use"] = "search_expansion_only"
            parent_info["candidate_count"] = int(parent_info.get("candidate_count") or 0) + len(source_rows)

        support_id = f"STAGE3-REMAINING-GAP-SUPPORT-V18-{seed.child_context}"
        source_case_ids = _unique([row.get("case_id") for row in source_rows] or list(seed.source_case_ids))
        support_by_id[support_id] = {
            "support_id": support_id,
            "source_candidate_id": support_id,
            "allowed_runtime_use": "guide_support_only",
            "child_context": seed.child_context,
            "parent_contexts": list(seed.parents),
            "accident_type": "OTHER",
            "hazardous_agent": "OTHER",
            "trigger_terms": list(seed.trigger_terms),
            "require_trigger_match": True,
            "allow_trigger_only_support": True,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "candidate_labels": ["stage3_remaining_gap", "guide_support_only", "v18_narrow_support"],
            "confidence": seed.confidence,
            "evidence": seed.rationale,
            "review_status": "candidate",
            "policy": "support_only_no_status_penalty_no_asserted_sr",
            "source_no_top_cases": source_case_ids,
        }
        audit_rows.append({
            "child_context": seed.child_context,
            "case_count": len(source_rows),
            "source_case_ids": source_case_ids,
            "guide_codes": list(seed.guide_codes),
            "source_sr_ids": list(seed.source_sr_ids),
            "trigger_terms": list(seed.trigger_terms),
            "rationale": seed.rationale,
        })

    taxonomy["generated_at"] = generated_at
    taxonomy["version"] = "v18"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage3_remaining_gap_support_v18": "guide_support_only_no_status_penalty_no_asserted_mapping",
    }

    support_rows_out = sorted(support_by_id.values(), key=lambda row: str(row.get("support_id") or ""))
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, support_rows_out)

    summary = {
        "generated_at": generated_at,
        "version": "v18",
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "no_top_report": str(args.no_top_report),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "support_rows_total": len(support_rows_out),
        "added_support_rows": len(SUPPORT_SEEDS),
        "tightened_support_rows": len(SUPPORT_ROW_TRIGGER_EXTENSIONS),
        "asserted_mapping_updates": 0,
        "status_penalty_changes": 0,
        "audit_rows": audit_rows,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps({"summary": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "child_context",
                "case_count",
                "source_case_ids",
                "guide_codes",
                "source_sr_ids",
                "trigger_terms",
                "rationale",
            ],
        )
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({
                **row,
                "source_case_ids": json.dumps(row.get("source_case_ids") or [], ensure_ascii=False),
                "guide_codes": json.dumps(row.get("guide_codes") or [], ensure_ascii=False),
                "source_sr_ids": json.dumps(row.get("source_sr_ids") or [], ensure_ascii=False),
                "trigger_terms": json.dumps(row.get("trigger_terms") or [], ensure_ascii=False),
            })
    md_lines = [
        "# Stage3 Remaining Gap Support v18 Artifacts",
        "",
        f"generated_at: {generated_at}",
        f"base_taxonomy: `{args.base_taxonomy}`",
        f"base_support: `{args.base_support}`",
        f"taxonomy_output: `{args.taxonomy_output}`",
        f"support_output: `{args.support_output}`",
        f"support_rows_total: {len(support_rows_out)}",
        f"added_support_rows: {len(SUPPORT_SEEDS)}",
        f"tightened_support_rows: {len(SUPPORT_ROW_TRIGGER_EXTENSIONS)}",
        "asserted_mapping_updates: 0",
        "status_penalty_changes: 0",
        "",
        "## Added/Tightened Rows",
        "",
    ]
    for row in audit_rows:
        md_lines.append(
            f"- `{row['child_context']}` cases={row['case_count']} "
            f"guides={', '.join(row.get('guide_codes') or [])} "
            f"source_cases={', '.join(row.get('source_case_ids') or [])}"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    return parser.parse_args()


def main() -> None:
    summary = build(parse_args())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
