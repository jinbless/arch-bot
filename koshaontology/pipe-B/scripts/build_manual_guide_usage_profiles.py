#!/usr/bin/env python3
"""Build materialized Guide usage profiles from manual domain-guard batches.

The output is ontology-side serving metadata.  It is not legal evidence and it
must not promote any SR mapping to asserted status.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
ARCH_ROOT = PIPE_B_ROOT.parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
KOSHA_ROOT = ARCH_ROOT / "koshaontology"
OUTPUT_JSON = DATA_DIR / "manual-guide-usage-profiles.json"
OUTPUT_MD = DATA_DIR / "manual-guide-usage-profiles.md"

DOCUMENT_ROLE_CUES = {
    "measurement_analysis": ["측정", "분석", "시료채취", "검량선", "탈착효율", "작업환경측정", "생물학적 노출지표"],
    "test_protocol": ["독성시험", "시험법", "조직병리", "발암성시험", "유전독성", "AOP", "급성흡입", "급성경구"],
    "health_screening": ["건강진단", "폐활량검사", "청력검사", "업무적합성", "업무관련성", "검사 이상"],
    "risk_method": ["위험성평가", "평가기법", "HAZOP", "LOPA", "THERP", "SHERPA", "HEART", "시나리오"],
    "document_reference": ["MSDS", "SDS", "GHS", "작성지침", "신뢰성평가", "매뉴얼 작성"],
    "management_program": ["관리 프로그램", "보건관리", "예방관리", "관리지침", "계획서", "절차서"],
}

FIELD_CONTROL_HINTS = ["설치", "작업", "운전", "정비", "하역", "적재", "취급", "사용", "청소", "조리", "보수"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def batch_paths() -> list[Path]:
    return sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json"))


def load_ci_output(guide: dict[str, Any]) -> dict[str, Any]:
    source = guide.get("source_file") or ""
    candidates = []
    if source:
        candidates.extend([KOSHA_ROOT / source, ARCH_ROOT / source])
    short_code = guide.get("short_code")
    if short_code:
        candidates.append(DATA_DIR / "ci-output" / f"ci-{short_code}.json")
    for path in candidates:
        if path.exists():
            try:
                return read_json(path)
            except json.JSONDecodeError:
                return {}
    return {}


def classify_role(guide: dict[str, Any]) -> str:
    profile = guide.get("domain_profile") or {}
    explicit_role = profile.get("procedure_role") or profile.get("procedure_role_hint") or guide.get("procedure_role")
    if explicit_role:
        return str(explicit_role)
    text = " ".join([
        guide.get("title") or "",
        profile.get("domain_family") or "",
        profile.get("evidence") or "",
        " ".join(profile.get("required_context_terms") or []),
    ])
    for role, cues in DOCUMENT_ROLE_CUES.items():
        if any(cue.lower() in text.lower() for cue in cues):
            return role
    if any(cue in text for cue in FIELD_CONTROL_HINTS):
        return "field_control"
    return "field_control"


def unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        value = str(value).strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def compact_terms(values: list[str], limit: int = 12) -> list[str]:
    cleaned = []
    for value in values:
        if not value:
            continue
        text = re.sub(r"\s+", " ", str(value)).strip()
        if len(text) > 80:
            text = text[:77].rstrip() + "..."
        cleaned.append(text)
    return unique(cleaned)[:limit]


def term_hit_score(text: str, terms: list[str]) -> int:
    lower = text.lower()
    score = 0
    for term in terms:
        lowered = str(term).lower().strip()
        if lowered and lowered in lower:
            score += 1
    return score


def primary_work_processes(guide: dict[str, Any], ci_data: dict[str, Any]) -> list[dict[str, Any]]:
    profile = guide.get("domain_profile") or {}
    visual_terms = [c.get("trigger_text") for c in guide.get("visual_trigger_candidates", []) or [] if c.get("trigger_text")]
    terms = compact_terms([
        *(profile.get("required_context_terms") or []),
        *(profile.get("industry_alignment") or []),
        *visual_terms,
        *[c.get("feature_code") for c in guide.get("feature_candidates", []) or [] if c.get("feature_code")],
    ], limit=40)
    ranked = []
    for wp in ci_data.get("workProcesses", []) or []:
        text = " ".join(str(wp.get(field) or "") for field in ["processName", "safetyMeasures", "sourceSection"])
        score = term_hit_score(text, terms)
        if score:
            ranked.append((score, int(wp.get("processOrder") or wp.get("process_order") or 999), wp))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2].get("identifier") or ""))
    return [item[2] for item in ranked[:8]]


def build_usage_profile(guide: dict[str, Any]) -> dict[str, Any]:
    profile = guide.get("domain_profile") or {}
    boundary = guide.get("recommendation_boundary") or {}
    ci_data = load_ci_output(guide)
    visual_candidates = guide.get("visual_trigger_candidates", []) or []
    role = classify_role(guide)
    primary_wps = primary_work_processes(guide, ci_data)

    intended_workplaces = compact_terms([
        *(profile.get("industry_alignment") or []),
        *(profile.get("required_context_terms") or []),
        *[c.get("trigger_text") for c in visual_candidates if c.get("cue_type") in {"workplace_context", "environment"}],
    ])
    intended_tasks = compact_terms([
        *[wp.get("processName") for wp in primary_wps if wp.get("processName")],
        *[c.get("trigger_text") for c in visual_candidates if c.get("cue_type") in {"work_activity", "activity"}],
        *(boundary.get("include_when") or []),
    ])
    observable_required_cues = compact_terms([
        *[c.get("trigger_text") for c in visual_candidates if c.get("trigger_text")],
        *(profile.get("required_context_terms") or []),
    ], limit=16)
    negative_boundaries = compact_terms([
        *(profile.get("negative_context_terms") or []),
        *(boundary.get("exclude_when") or []),
    ], limit=16)

    usage_summary = f"{guide.get('title')} 사용경계: {profile.get('domain_family') or 'general'} / {profile.get('profile_level') or 'general'}"
    if role != "field_control":
        usage_summary += f" / {role}"

    return {
        "guide_code": guide.get("guide_code"),
        "title": guide.get("title"),
        "profile_level": profile.get("profile_level") or "general",
        "domain_family": profile.get("domain_family"),
        "usage_summary": usage_summary,
        "intended_workplaces": intended_workplaces,
        "intended_tasks": intended_tasks,
        "observable_required_cues": observable_required_cues,
        "negative_boundaries": negative_boundaries,
        "procedure_role": role,
        "primary_work_process_ids": [wp.get("identifier") for wp in primary_wps if wp.get("identifier")],
        "primary_work_process_titles": [wp.get("processName") for wp in primary_wps if wp.get("processName")],
        "evidence": profile.get("evidence") or guide.get("notes") or guide.get("title"),
        "review_status": guide.get("review_status") or "candidate",
        "source_fields": unique([*(profile.get("source_fields") or []), "manual_domain_profile", "ci-output.workProcesses"]),
        "method": "codex_manual_usage_profile_v1",
    }


def main() -> None:
    profiles: dict[str, dict[str, Any]] = {}
    role_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    for batch_path in batch_paths():
        batch = read_json(batch_path)
        for guide in batch.get("guides", []) or []:
            guide_code = guide.get("guide_code")
            if not guide_code:
                continue
            usage = build_usage_profile(guide)
            profiles[guide_code] = usage
            role_counts[usage["procedure_role"]] += 1
            level_counts[usage["profile_level"]] += 1

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "codex_manual_usage_profile_v1",
        "source": "manual-enrichment-domain-guard-batch-001..035.json",
        "legal_asserted_use": False,
        "guide_count": len(profiles),
        "procedure_role_counts": dict(sorted(role_counts.items())),
        "profile_level_counts": dict(sorted(level_counts.items())),
        "profiles": dict(sorted(profiles.items())),
    }
    write_json(OUTPUT_JSON, output)

    lines = [
        "# Manual Guide Usage Profiles",
        "",
        f"- generated_at: `{output['generated_at']}`",
        f"- guide_count: `{output['guide_count']}`",
        "",
        "## Procedure Roles",
        "",
        "| role | count |",
        "| --- | ---: |",
    ]
    for role, count in sorted(role_counts.items()):
        lines.append(f"| `{role}` | {count} |")
    lines.extend(["", "## Notes", "", "- These profiles are recommendation boundary metadata, not asserted legal evidence.", "- OHS must consume them through exported serving artifacts, not by reading koshaontology paths at runtime.", ""])
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
