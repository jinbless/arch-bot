#!/usr/bin/env python3
"""Build narrow Stage2/3 NO_TOP support artifacts on top of v7.

The added rows are Guide-ranking support only. They do not broaden
RiskFeature normalization, SHE status, penalty exposure, asserted SR mappings,
or legal evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_BASE_TAXONOMY = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v7.json"
DEFAULT_BASE_SUPPORT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v7.jsonl"
DEFAULT_NO_TOP_REPORT = (
    PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "stage2_5_no_top_root_cause_stage2_service_support_v7_narrow1.json"
)
DEFAULT_TAXONOMY_OUTPUT = BACKEND_DIR / "app" / "data" / "situation_context_taxonomy.v8.json"
DEFAULT_SUPPORT_OUTPUT = BACKEND_DIR / "app" / "data" / "guide_support_candidates.v8.jsonl"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_REPORT_PREFIX = "stage2_3_support_v8_artifacts"


@dataclass(frozen=True)
class SupportSeed:
    child_context: str
    parents: tuple[str, ...]
    aliases: tuple[str, ...]
    profile_alignment_aliases: tuple[str, ...]
    guide_codes: tuple[str, ...]
    source_sr_ids: tuple[str, ...]
    trigger_terms: tuple[str, ...]
    source_case_ids: tuple[str, ...]
    confidence: float
    rationale: str


SUPPORT_SEEDS: tuple[SupportSeed, ...] = (
    SupportSeed(
        child_context="XRAY_RADIATION_CONTROL",
        parents=("RADIATION", "GENERAL_WORKPLACE"),
        aliases=(
            "RADIATION_XRAY",
            "X선",
            "X레이",
            "엑스레이",
            "방사선",
            "산란 방사선",
            "차폐 벽",
            "차폐 구역",
            "개인선량계",
        ),
        profile_alignment_aliases=("방사선", "X레이", "X선", "차폐", "개인선량계", "방사성 물질"),
        guide_codes=("G-24-2011", "E-164-2017"),
        source_sr_ids=("SR-RADIATION-001", "SR-RADIATION-002", "SR-RADIATION-013"),
        trigger_terms=("X선", "X레이", "엑스레이", "방사선 촬영", "산란 방사선", "차폐 구역", "차폐 벽", "개인선량계", "임신 직원"),
        source_case_ids=("SYN-V6-0256", "SYN-V6-0257", "SYN-V6-0258"),
        confidence=0.66,
        rationale="Dental/medical X-ray scenes have explicit radiation, shielding, or dosimeter cues; use as Guide support only.",
    ),
    SupportSeed(
        child_context="BLASTING_OPERATION",
        parents=("OTHER", "EXCAVATION"),
        aliases=("발파 작업", "발파", "기폭", "폭약", "뇌관", "화약 저장소", "발파 신호", "발파 경보"),
        profile_alignment_aliases=("발파공사", "화약류", "폭약", "뇌관", "전기뇌관", "장약", "발파모선"),
        guide_codes=("D-C-6-2025", "D-C-11-2026"),
        source_sr_ids=(
            "SR-HAZMAT-024",
            "SR-HAZMAT-001",
            "SR-HAZMAT-002",
            "SR-EXCAVATION-010",
            "SR-EXCAVATION-011",
            "SR-EXCAVATION-018",
        ),
        trigger_terms=("발파", "기폭", "폭약", "뇌관", "화약 저장소", "경보", "대피", "불발", "장약"),
        source_case_ids=("SYN-V8-0037", "SYN-V8-0038"),
        confidence=0.67,
        rationale="Blasting/explosives scenes are narrow, photo-observable, and map better to D-C-6 than generic excavation.",
    ),
    SupportSeed(
        child_context="HOT_WORK_PERMIT",
        parents=("WELDING", "FIRE_EXPLOSION"),
        aliases=("화기 작업", "화기작업", "작업 허가서", "화기 작업 허가", "허가 구역", "잔화", "화재감시자", "감시자"),
        profile_alignment_aliases=("용접", "용단", "화기작업", "화기작업 허가", "화재감시자", "잔화", "작업허가"),
        guide_codes=("A-G-14-2026", "G-116-2014", "M-67-2012"),
        source_sr_ids=("SR-FIRE_EXPLOSION-006", "SR-FIRE_EXPLOSION-007", "SR-FIRE_EXPLOSION-008", "SR-HEAT-012"),
        trigger_terms=(
            "허가 구역 외부",
            "작업 구역 외부",
            "실제 작업 위치 불일치",
            "허가 구역과 실제 작업 위치 불일치",
            "감시자가 배치되지",
            "감시자 부재",
            "감시 의무",
            "잔화 가능성",
            "작업자 전원 이석",
        ),
        source_case_ids=("SYN-V7-0278", "SYN-V7-0297", "SYN-V7-0298"),
        confidence=0.66,
        rationale="Hot-work permit and fire-watch deviations are support-only Guide signals for welding/fire prevention procedures.",
    ),
    SupportSeed(
        child_context="SHIPYARD_WELDING",
        parents=("WELDING", "CONFINED_SPACE", "FIRE_EXPLOSION"),
        aliases=("선박 내부 용접", "조선 용접", "void space", "협소 구역 용접", "수동 용접봉", "용접 흄", "밀폐 용접"),
        profile_alignment_aliases=("용접", "용접 흄", "수동 금속 아크 용접", "국소배기", "밀폐공간", "선박", "조선"),
        guide_codes=("M-67-2012", "A-G-14-2026", "G-116-2014"),
        source_sr_ids=("SR-FIRE_EXPLOSION-006", "SR-FIRE_EXPLOSION-007", "SR-FIRE_EXPLOSION-008", "SR-CHEMICAL-002"),
        trigger_terms=("선박 내부", "협소 구역", "void space", "수동 용접봉", "환기 없이", "환기 미흡", "밀폐 환경", "자급식 공기호흡기 미착용"),
        source_case_ids=("SYN-V7-0278",),
        confidence=0.66,
        rationale="Ship internal welding-fume scenes are narrow support-only signals for manual welding and shipbuilding hot-work controls.",
    ),
    SupportSeed(
        child_context="SOLDERING_ASSEMBLY",
        parents=("ELECTRICAL_WORK", "CHEMICAL_WORK"),
        aliases=("납땜", "납 흄", "플럭스", "PCB 납땜", "국소배기", "납땜 인두"),
        profile_alignment_aliases=("납땜", "납 흄", "플럭스", "국소배기", "후드", "덕트", "환기"),
        guide_codes=("E-G-21-2026",),
        source_sr_ids=("SR-CHEMICAL-002", "SR-CHEMICAL-006", "SR-CHEMICAL-008"),
        trigger_terms=("납땜", "납 흄", "플럭스", "국소 배기 없이", "국소배기 없이", "작업자 호흡 영역", "방진마스크"),
        source_case_ids=("SYN-V7-0101",),
        confidence=0.65,
        rationale="Soldering fume scenes should support ventilation procedures when local exhaust/fume cues are explicit.",
    ),
    SupportSeed(
        child_context="SOLVENT_WASTE_FIRE",
        parents=("CHEMICAL_WORK", "FIRE_EXPLOSION"),
        aliases=("용제 세척", "용제 함침 걸레", "함침 걸레", "자연 발화", "인쇄공정 용제", "개방형 쓰레기통"),
        profile_alignment_aliases=("유기용제", "인화성", "화재", "폭발", "착화원", "소화기", "방유제"),
        guide_codes=("D-28-2012", "D-3-2012"),
        source_sr_ids=("SR-FIRE_EXPLOSION-006", "SR-FIRE_EXPLOSION-007", "SR-FIRE_EXPLOSION-008", "SR-CHEMICAL-002"),
        trigger_terms=("용제 세척 완료 후", "용제 함침 걸레", "용제 묻은 걸레", "용제 걸레", "개방형 쓰레기통", "자연 발화"),
        source_case_ids=("SYN-V8-0292",),
        confidence=0.65,
        rationale="Solvent-soaked rag/fire scenes are support-only signals for small-workplace fire/explosion controls.",
    ),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _unique(values: list[Any] | tuple[Any, ...]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _merge(existing: list[Any] | None, additions: tuple[Any, ...] | list[Any]) -> list[str]:
    return _unique([*(existing or []), *additions])


def _source_rows(no_top_rows: list[dict[str, Any]], case_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    wanted = set(case_ids)
    return [row for row in no_top_rows if row.get("case_id") in wanted]


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

        support_id = f"STAGE2-3-SUPPORT-{seed.child_context}"
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
            "candidate_labels": ["no_top_repair", "guide_support_only", "v8_narrow_support"],
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
    taxonomy["version"] = "v8"
    taxonomy["policy"] = {
        **(taxonomy.get("policy") or {}),
        "stage2_3_support_v8": "guide_support_only_no_status_penalty_no_asserted_mapping",
    }

    merged_rows = sorted(
        support_by_id.values(),
        key=lambda row: (str(row.get("child_context") or ""), str(row.get("support_id") or "")),
    )
    args.taxonomy_output.parent.mkdir(parents=True, exist_ok=True)
    args.taxonomy_output.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_jsonl(args.support_output, merged_rows)

    summary = {
        "generated_at": generated_at,
        "base_taxonomy": str(args.base_taxonomy),
        "base_support": str(args.base_support),
        "taxonomy_output": str(args.taxonomy_output),
        "support_output": str(args.support_output),
        "added_child_context_count": len(SUPPORT_SEEDS),
        "support_candidate_count": len(merged_rows),
        "audit_rows": audit_rows,
        "status_penalty_she_approval_asserted_mapping_update": 0,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / f"{args.report_prefix}.json"
    md_path = args.report_dir / f"{args.report_prefix}.md"
    csv_path = args.report_dir / f"{args.report_prefix}.csv"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_lines = [
        "# Stage2/3 Support v8 Artifact Report",
        "",
        f"- generated_at: `{generated_at}`",
        f"- added_child_context_count: `{len(SUPPORT_SEEDS)}`",
        f"- support_candidate_count: `{len(merged_rows)}`",
        "- status/penalty/SHE approval/asserted mapping update: `0`",
        "",
        "## Added Contexts",
        "",
    ]
    for row in audit_rows:
        md_lines.extend([
            f"### {row['child_context']}",
            "",
            f"- cases: `{row['case_count']}`",
            f"- source_case_ids: `{', '.join(row['source_case_ids'])}`",
            f"- guide_codes: `{', '.join(row['guide_codes'])}`",
            f"- source_sr_ids: `{', '.join(row['source_sr_ids'])}`",
            f"- rationale: {row['rationale']}",
            "",
        ])
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
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
                "source_case_ids": "|".join(row["source_case_ids"]),
                "guide_codes": "|".join(row["guide_codes"]),
                "source_sr_ids": "|".join(row["source_sr_ids"]),
                "trigger_terms": "|".join(row["trigger_terms"]),
            })
    summary["outputs"] = {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-taxonomy", type=Path, default=DEFAULT_BASE_TAXONOMY)
    parser.add_argument("--base-support", type=Path, default=DEFAULT_BASE_SUPPORT)
    parser.add_argument("--no-top-report", type=Path, default=DEFAULT_NO_TOP_REPORT)
    parser.add_argument("--taxonomy-output", type=Path, default=DEFAULT_TAXONOMY_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    args = parser.parse_args()
    summary = build(args)
    print(json.dumps({
        "added_child_context_count": summary["added_child_context_count"],
        "support_candidate_count": summary["support_candidate_count"],
        "outputs": summary["outputs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
