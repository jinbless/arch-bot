#!/usr/bin/env python3
"""Build an import preview for manual domain-guard enrichment batches.

This script does not write to the database.  It flattens the 1,038 manual
Guide enrichment records into the three candidate-table shapes, validates the
serving gates that OHS should use, and records the import strategy needed to
preserve manual confidence demotions.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
ARCH_ROOT = PIPE_B_ROOT.parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
SR_DIR = ARCH_ROOT / "koshaontology" / "pipe-A" / "data" / "safety-requirements"
FEATURE_CATALOG = ARCH_ROOT / "OHS" / "backend" / "app" / "data" / "risk_feature_catalog.json"
CI_OUTPUT_DIR = DATA_DIR / "ci-output"

METHOD = "codex_manual_pilot"
SERVING_CONFIDENCE = 0.65
SERVING_STATUSES = {"candidate", "asserted"}
EXCLUDED_STATUSES = {"needs_review", "rejected"}

PREVIEW_JSON = DATA_DIR / "manual-enrichment-domain-guard-import-preview.json"
PREVIEW_MD = DATA_DIR / "manual-enrichment-domain-guard-import-preview.md"
REVIEW_QUEUE_JSON = DATA_DIR / "manual-enrichment-domain-guard-review-queues.json"
REVIEW_QUEUE_MD = DATA_DIR / "manual-enrichment-domain-guard-review-queues.md"
SEMANTIC_AUDIT_JSON = DATA_DIR / "manual-enrichment-domain-guard-semantic-audit.json"


OPERATIONAL_NO_SR_TRIAGE = {
    "B-5-2011": {
        "classification": "domain_guard_only",
        "reason": "조선업 점검 기술지침으로 업종 경계는 강하지만 현재 후보 evidence만으로 신규 SR 보강을 확정하기 어렵다.",
    },
    "A-G-10-2025": {
        "classification": "SR 보강",
        "reason": "급식실 시설은 미끄럼, 화상, 가스, 조리설비 같은 현장 조치로 연결될 여지가 크다.",
    },
    "O-1-2011": {
        "classification": "document_only",
        "reason": "용접재료 선정 지침 성격이 강해 사진 기반 표준절차 후보로 쓰기보다 문서 참조로 보존한다.",
    },
    "A-G-5-2025": {
        "classification": "SR 보강",
        "reason": "조리도구 사용은 베임, 화상, 끼임 등 즉시 조치형 SR 보강 후보로 볼 수 있다.",
    },
    "A-G-7-2025": {
        "classification": "taxonomy_gap",
        "reason": "아파트 경비 보조업무는 야간 단독근무, 순찰, 폐기물, 조경 등 현재 taxonomy가 덜 세분화된 영역이다.",
    },
    "X-45-2014": {
        "classification": "SR 보강",
        "reason": "도로/철도 작업 고시인성 의복은 차량 충돌 및 PPE의 구체 작업 경계가 필요하다.",
    },
    "X-69-2016": {
        "classification": "document_only",
        "reason": "THERP 기반 human error 정량평가 방법론으로 현장 조치 추천 근거가 아니다.",
    },
    "X-70-2016": {
        "classification": "document_only",
        "reason": "OAT 기반 방법론 문서라 사진 상황의 조치 추천보다 분석 문서 참조에 가깝다.",
    },
    "X-72-2017": {
        "classification": "document_only",
        "reason": "SHERPA 기반 방법론 문서라 현장 표준절차로 직접 노출하면 과추천 위험이 크다.",
    },
    "X-73-2017": {
        "classification": "document_only",
        "reason": "Human error HAZOP 방법론 문서로 candidate-only/domain guard 용도에 머문다.",
    },
    "X-74-2017": {
        "classification": "document_only",
        "reason": "HEART 기반 방법론 문서라 broad SR로 표준절차를 만들면 안 된다.",
    },
    "H-163-2021": {
        "classification": "taxonomy_gap",
        "reason": "감정노동 평가 영역은 psychosocial risk taxonomy/SR 축이 별도로 필요하다.",
    },
    "H-203-2018": {
        "classification": "taxonomy_gap",
        "reason": "고객응대 건강장해 예방은 현재 물리적 사고 중심 taxonomy와 분리해 다뤄야 한다.",
    },
    "H-204-2018": {
        "classification": "taxonomy_gap",
        "reason": "직장 내 괴롭힘은 psychosocial/management SR 축 확장이 필요하다.",
    },
    "H-37-2021": {
        "classification": "taxonomy_gap",
        "reason": "우울증/자살 예방은 건강관리·정신건강 taxonomy가 필요해 일반 작업 사진 추천에 직접 쓰기 어렵다.",
    },
    "H-75-2015": {
        "classification": "document_only",
        "reason": "작업환경 평가 방법론 성격이 강해 사진 기반 표준절차 primary 후보보다 평가 문서 참조로 제한한다.",
    },
    "H-91-2021": {
        "classification": "taxonomy_gap",
        "reason": "피로도 평가는 건강관리/인적요인 taxonomy 확장 후 별도로 연결해야 한다.",
    },
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def batch_paths() -> list[Path]:
    return sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json"))


def load_batches() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, read_json(path)) for path in batch_paths()]


def iter_guides(batches: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    guides: list[dict[str, Any]] = []
    for path, batch in batches:
        for guide in batch.get("guides", []) or []:
            guide["_batch_file"] = path.name
            guide["_batch_id"] = (batch.get("scope") or {}).get("batch_id") or path.stem
            guides.append(guide)
    return guides


def load_sr_registry() -> set[str]:
    sr_ids: set[str] = set()
    for path in sorted(SR_DIR.glob("sr-batch-*.json")):
        data = read_json(path)
        for group in data.get("srGroups", []) or []:
            sr_id = group.get("preAssignedId")
            if sr_id:
                sr_ids.add(sr_id)
    return sr_ids


def load_feature_codes() -> set[str]:
    data = read_json(FEATURE_CATALOG)
    codes: set[str] = set()
    for axis in (data.get("axes") or {}).values():
        for code, spec in (axis.get("codes") or {}).items():
            codes.add(code)
            codes.update(spec.get("sub") or [])
    return codes


def load_entity_registry() -> dict[str, set[str]]:
    registry: dict[str, set[str]] = defaultdict(set)
    for path in sorted(CI_OUTPUT_DIR.glob("ci-*.json")):
        try:
            data = read_json(path)
        except json.JSONDecodeError:
            continue
        guide_code = (data.get("metadata") or {}).get("guideCode")
        if not guide_code:
            continue
        registry["GUIDE"].add(guide_code)
        for entity_type, key in (
            ("CI", "checklistItems"),
            ("WP", "workProcesses"),
            ("ES", "equipmentSpecs"),
            ("DR", "documentRequirements"),
            ("DT", "domainTerms"),
        ):
            for item in data.get(key, []) or []:
                identifier = item.get("identifier")
                if identifier:
                    registry[entity_type].add(identifier)
    return registry


def candidate_status(candidate: dict[str, Any], guide: dict[str, Any]) -> str:
    return str(candidate.get("review_status") or guide.get("review_status") or "candidate")


def candidate_method(candidate: dict[str, Any], guide: dict[str, Any]) -> str:
    return str(candidate.get("method") or guide.get("method") or METHOD)


def is_serving_eligible(candidate: dict[str, Any], guide: dict[str, Any]) -> bool:
    confidence = float(candidate.get("confidence") or 0.0)
    return confidence >= SERVING_CONFIDENCE and candidate_status(candidate, guide) in SERVING_STATUSES


def flatten_rows(guides: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    rows = {
        "guide_entity_feature_candidates": [],
        "guide_sr_link_candidates": [],
        "guide_visual_trigger_candidates": [],
    }
    for guide in guides:
        guide_code = guide.get("guide_code")
        for candidate in guide.get("feature_candidates", []) or []:
            rows["guide_entity_feature_candidates"].append({
                "batch_file": guide["_batch_file"],
                "batch_id": guide["_batch_id"],
                "entity_type": candidate.get("entity_type"),
                "entity_id": candidate.get("entity_id"),
                "guide_code": candidate.get("guide_code") or guide_code,
                "axis": candidate.get("axis"),
                "feature_code": candidate.get("feature_code"),
                "confidence": candidate.get("confidence"),
                "evidence": candidate.get("evidence"),
                "source_fields": candidate.get("source_fields") or [],
                "method": candidate_method(candidate, guide),
                "review_status": candidate_status(candidate, guide),
                "non_llm_evidence_count": candidate.get("non_llm_evidence_count", 0),
                "serving_eligible": is_serving_eligible(candidate, guide),
            })
        for candidate in guide.get("sr_link_candidates", []) or []:
            rows["guide_sr_link_candidates"].append({
                "batch_file": guide["_batch_file"],
                "batch_id": guide["_batch_id"],
                "entity_type": candidate.get("entity_type"),
                "entity_id": candidate.get("entity_id"),
                "guide_code": candidate.get("guide_code") or guide_code,
                "sr_id": candidate.get("sr_id"),
                "confidence": candidate.get("confidence"),
                "evidence": candidate.get("evidence"),
                "source_fields": candidate.get("source_fields") or [],
                "method": candidate_method(candidate, guide),
                "review_status": candidate_status(candidate, guide),
                "non_llm_evidence_count": candidate.get("non_llm_evidence_count", 0),
                "asserted": bool(candidate.get("asserted") or False),
                "serving_eligible": is_serving_eligible(candidate, guide),
            })
        for candidate in guide.get("visual_trigger_candidates", []) or []:
            rows["guide_visual_trigger_candidates"].append({
                "batch_file": guide["_batch_file"],
                "batch_id": guide["_batch_id"],
                "entity_type": candidate.get("entity_type"),
                "entity_id": candidate.get("entity_id"),
                "guide_code": candidate.get("guide_code") or guide_code,
                "trigger_text": candidate.get("trigger_text"),
                "cue_type": candidate.get("cue_type"),
                "confidence": candidate.get("confidence"),
                "evidence": candidate.get("evidence"),
                "source_fields": candidate.get("source_fields") or [],
                "method": candidate_method(candidate, guide),
                "review_status": candidate_status(candidate, guide),
                "serving_eligible": is_serving_eligible(candidate, guide),
            })
    return rows


def unique_key(table: str, row: dict[str, Any]) -> tuple[Any, ...]:
    if table == "guide_entity_feature_candidates":
        return (row["entity_type"], row["entity_id"], row["axis"], row["feature_code"], row["method"])
    if table == "guide_sr_link_candidates":
        return (row["entity_type"], row["entity_id"], row["sr_id"], row["method"])
    return (row["entity_type"], row["entity_id"], row["trigger_text"], row["method"])


def validate_rows(
    rows: dict[str, list[dict[str, Any]]],
    sr_registry: set[str],
    feature_codes: set[str],
    entity_registry: dict[str, set[str]],
) -> dict[str, Any]:
    issues: dict[str, Any] = {
        "missing_required_fields": [],
        "invalid_review_status": [],
        "invalid_sr_id": [],
        "non_catalog_feature_code": [],
        "entity_fk_violations": [],
        "duplicate_unique_keys": {},
    }

    for table, table_rows in rows.items():
        counter = Counter(unique_key(table, row) for row in table_rows)
        duplicates = [key for key, count in counter.items() if count > 1]
        if duplicates:
            issues["duplicate_unique_keys"][table] = [
                {"key": list(key), "count": counter[key]} for key in duplicates[:50]
            ]

        for row in table_rows:
            required = ["entity_type", "entity_id", "guide_code", "confidence", "evidence", "method", "review_status"]
            if table == "guide_entity_feature_candidates":
                required.extend(["axis", "feature_code"])
            elif table == "guide_sr_link_candidates":
                required.append("sr_id")
            else:
                required.extend(["trigger_text", "cue_type"])
            missing = [field for field in required if row.get(field) in (None, "", [])]
            if missing:
                issues["missing_required_fields"].append({
                    "table": table,
                    "guide_code": row.get("guide_code"),
                    "entity_id": row.get("entity_id"),
                    "missing": missing,
                })
            if row.get("review_status") not in SERVING_STATUSES | EXCLUDED_STATUSES:
                issues["invalid_review_status"].append({
                    "table": table,
                    "guide_code": row.get("guide_code"),
                    "review_status": row.get("review_status"),
                })
            entity_type = row.get("entity_type")
            entity_id = row.get("entity_id")
            if entity_type in entity_registry and entity_id not in entity_registry[entity_type]:
                issues["entity_fk_violations"].append({
                    "table": table,
                    "guide_code": row.get("guide_code"),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                })
            if table == "guide_sr_link_candidates" and row.get("sr_id") not in sr_registry:
                issues["invalid_sr_id"].append({
                    "guide_code": row.get("guide_code"),
                    "sr_id": row.get("sr_id"),
                    "entity_id": entity_id,
                })
            if table == "guide_entity_feature_candidates" and row.get("feature_code") not in feature_codes:
                issues["non_catalog_feature_code"].append({
                    "guide_code": row.get("guide_code"),
                    "feature_code": row.get("feature_code"),
                    "entity_id": entity_id,
                })
    return issues


def summarize_rows(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for table, table_rows in rows.items():
        status_counts = Counter(row.get("review_status") for row in table_rows)
        serving_count = sum(1 for row in table_rows if row.get("serving_eligible"))
        confidence_excluded = sum(
            1
            for row in table_rows
            if row.get("review_status") in SERVING_STATUSES
            and float(row.get("confidence") or 0.0) < SERVING_CONFIDENCE
        )
        status_excluded = sum(1 for row in table_rows if row.get("review_status") in EXCLUDED_STATUSES)
        summary[table] = {
            "rows": len(table_rows),
            "serving_eligible": serving_count,
            "excluded_by_review_status": status_excluded,
            "excluded_by_confidence": confidence_excluded,
            "review_status_counts": dict(sorted(status_counts.items())),
        }
    return summary


def build_review_queues(guides: list[dict[str, Any]], rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    audit = read_json(SEMANTIC_AUDIT_JSON) if SEMANTIC_AUDIT_JSON.exists() else {}
    flags = audit.get("all_flags") or audit.get("flags", []) or []
    no_sr_flags = [flag for flag in flags if flag.get("issue") == "operational_guide_without_sr_candidate"]
    broad_feature_flags = [flag for flag in flags if flag.get("issue") == "generic_feature_only_for_exclusive"]

    guide_by_code = {guide.get("guide_code"): guide for guide in guides}
    operational_no_sr = []
    for flag in sorted(no_sr_flags, key=lambda item: item.get("guide_code") or ""):
        guide_code = flag.get("guide_code")
        triage = OPERATIONAL_NO_SR_TRIAGE.get(guide_code, {
            "classification": "pending_manual_triage",
            "reason": "semantic audit flagged an operational-looking Guide without SR candidates.",
        })
        guide = guide_by_code.get(guide_code, {})
        operational_no_sr.append({
            "guide_code": guide_code,
            "title": flag.get("title") or guide.get("title"),
            "batch_id": flag.get("batch_id"),
            "classification": triage["classification"],
            "reason": triage["reason"],
            "next_action": {
                "SR 보강": "SR 후보 evidence를 추가 검토한 뒤 candidate table에만 보강한다.",
                "domain_guard_only": "표준절차 생성 신호보다 domain boundary 신호로만 사용한다.",
                "taxonomy_gap": "별도 taxonomy/SR 확장 큐로 이동한다.",
                "document_only": "사진 기반 추천에서 primary procedure가 되지 않도록 broad SR을 차단한다.",
                "pending_manual_triage": "수동 판정을 완료한다.",
            }[triage["classification"]],
        })

    broad_by_code = defaultdict(list)
    for flag in broad_feature_flags:
        broad_by_code[flag.get("guide_code")].append(flag)
    exclusive_broad_feature_only = [
        {
            "guide_code": guide_code,
            "title": flags_for_guide[0].get("title"),
            "flag_count": len(flags_for_guide),
            "recommendation": "Do not add new generic features; use domain_profile/visual_trigger as guide-specific signal.",
        }
        for guide_code, flags_for_guide in sorted(broad_by_code.items())
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "codex_manual_import_preview",
        "source_audit": SEMANTIC_AUDIT_JSON.name if SEMANTIC_AUDIT_JSON.exists() else None,
        "operational_no_sr_guides": {
            "count": len(operational_no_sr),
            "items": operational_no_sr,
            "classification_counts": dict(Counter(item["classification"] for item in operational_no_sr)),
        },
        "exclusive_broad_feature_only_guides": {
            "count": len(exclusive_broad_feature_only),
            "items": exclusive_broad_feature_only,
        },
        "serving_gate_reminder": {
            "review_status_in": sorted(SERVING_STATUSES),
            "min_confidence": SERVING_CONFIDENCE,
            "excluded_statuses": sorted(EXCLUDED_STATUSES),
        },
    }


def write_preview_markdown(preview: dict[str, Any]) -> None:
    totals = preview["totals"]
    row_summary = preview["candidate_row_summary"]
    issues = preview["validation"]
    lines = [
        "# Manual Domain Guard Import Preview",
        "",
        f"- generated_at: `{preview['generated_at']}`",
        f"- source_batches: `{totals['batch_files']}`",
        f"- unique_guides: `{totals['unique_guides']}`",
        f"- asserted_mapping_updates: `{totals['asserted_mapping_updates']}`",
        f"- import_mode: `{preview['import_strategy']['mode']}`",
        "",
        "## Candidate Rows",
        "",
        "| table | rows | serving_eligible | excluded_by_status | excluded_by_confidence |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for table, item in row_summary.items():
        lines.append(
            f"| `{table}` | {item['rows']} | {item['serving_eligible']} | "
            f"{item['excluded_by_review_status']} | {item['excluded_by_confidence']} |"
        )
    lines.extend([
        "",
        "## Validation",
        "",
        f"- missing_required_fields: `{len(issues['missing_required_fields'])}`",
        f"- invalid_review_status: `{len(issues['invalid_review_status'])}`",
        f"- invalid_sr_id: `{len(issues['invalid_sr_id'])}`",
        f"- non_catalog_feature_code: `{len(issues['non_catalog_feature_code'])}`",
        f"- entity_fk_violations: `{len(issues['entity_fk_violations'])}`",
        f"- duplicate_unique_key_tables: `{len(issues['duplicate_unique_keys'])}`",
        "",
    ])
    if issues["duplicate_unique_keys"]:
        lines.extend([
            "### Mergeable Duplicate Unique Keys",
            "",
            "These source rows must be pre-aggregated before real DB import.",
            "",
        ])
        for table, duplicates in issues["duplicate_unique_keys"].items():
            lines.append(f"- `{table}`")
            for duplicate in duplicates[:10]:
                lines.append(f"  - `{duplicate['key']}` count {duplicate['count']}")
        lines.append("")
    lines.extend([
        "## Import Strategy",
        "",
        "- Do not write asserted mapping tables from this preview.",
        "- Import candidate tables with `replace-per-method`: delete/replace rows for `method=codex_manual_pilot` before inserting corrected rows.",
        "- Do not use `GREATEST(confidence)` for this import path because manual demotions to `needs_review`/lower confidence must be preserved.",
        "- OHS serving must require both `confidence >= 0.65` and `review_status in ('candidate', 'asserted')`.",
        "",
    ])
    PREVIEW_MD.write_text("\n".join(lines), encoding="utf-8")


def write_review_queue_markdown(queue: dict[str, Any]) -> None:
    lines = [
        "# Manual Domain Guard Review Queues",
        "",
        f"- generated_at: `{queue['generated_at']}`",
        f"- operational_no_sr_guides: `{queue['operational_no_sr_guides']['count']}`",
        f"- exclusive_broad_feature_only_guides: `{queue['exclusive_broad_feature_only_guides']['count']}`",
        "",
        "## Operational No-SR Manual Triage",
        "",
        "| guide | classification | next_action |",
        "| --- | --- | --- |",
    ]
    for item in queue["operational_no_sr_guides"]["items"]:
        lines.append(f"| `{item['guide_code']}` | {item['classification']} | {item['next_action']} |")
    lines.extend([
        "",
        "## Broad Feature-Only Exclusive Guides",
        "",
        "These remain a guard/visual-trigger queue. Do not expand the feature catalog with generic codes only to make them score.",
        "",
    ])
    for item in queue["exclusive_broad_feature_only_guides"]["items"][:40]:
        lines.append(f"- `{item['guide_code']}` {item['title']} ({item['flag_count']} flags)")
    if queue["exclusive_broad_feature_only_guides"]["count"] > 40:
        lines.append("- ... see JSON for the full queue.")
    REVIEW_QUEUE_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    batches = load_batches()
    guides = iter_guides(batches)
    rows = flatten_rows(guides)
    sr_registry = load_sr_registry()
    feature_codes = load_feature_codes()
    entity_registry = load_entity_registry()
    validation = validate_rows(rows, sr_registry, feature_codes, entity_registry)

    asserted_updates = sum(
        int((batch.get("asserted_mapping_updates") or 0))
        for _, batch in batches
    )
    duplicate_guide_codes = [
        guide_code
        for guide_code, count in Counter(guide.get("guide_code") for guide in guides).items()
        if guide_code and count > 1
    ]

    preview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "codex_manual_import_preview",
        "source_method": METHOD,
        "serving_policy": {
            "min_confidence": SERVING_CONFIDENCE,
            "review_status_in": sorted(SERVING_STATUSES),
            "excluded_statuses": sorted(EXCLUDED_STATUSES),
        },
        "totals": {
            "batch_files": len(batches),
            "guides": len(guides),
            "unique_guides": len({guide.get("guide_code") for guide in guides if guide.get("guide_code")}),
            "duplicate_guide_codes": duplicate_guide_codes,
            "asserted_mapping_updates": asserted_updates,
        },
        "candidate_row_summary": summarize_rows(rows),
        "validation": validation,
        "import_strategy": {
            "mode": "preview_only",
            "candidate_tables_only": True,
            "asserted_mapping_updates": 0,
            "replace_per_method_required": True,
            "replace_method": METHOD,
            "why_replace_per_method": "Corrected manual batches may demote confidence/review_status; GREATEST(confidence) upserts would keep stale high confidence.",
            "recommended_steps": [
                "BEGIN",
                "DELETE FROM guide_entity_feature_candidates WHERE method = 'codex_manual_pilot'",
                "DELETE FROM guide_sr_link_candidates WHERE method = 'codex_manual_pilot'",
                "DELETE FROM guide_visual_trigger_candidates WHERE method = 'codex_manual_pilot'",
                "INSERT flattened candidate rows",
                "COMMIT",
            ],
        },
    }
    write_json(PREVIEW_JSON, preview)
    write_preview_markdown(preview)

    queue = build_review_queues(guides, rows)
    write_json(REVIEW_QUEUE_JSON, queue)
    write_review_queue_markdown(queue)

    print(f"Wrote {PREVIEW_JSON}")
    print(f"Wrote {PREVIEW_MD}")
    print(f"Wrote {REVIEW_QUEUE_JSON}")
    print(f"Wrote {REVIEW_QUEUE_MD}")


if __name__ == "__main__":
    main()
