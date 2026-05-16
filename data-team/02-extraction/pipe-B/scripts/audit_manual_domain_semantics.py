#!/usr/bin/env python3
"""Heuristic semantic audit for manual Guide domain-guard candidates.

The audit is intentionally conservative: it does not change candidate JSON,
does not call external APIs, and does not import to DB. It flags likely semantic
risks that need review before candidate-table import or OHS runtime use.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
ARCH_ROOT = PIPE_B_ROOT.parents[1]
DATA_DIR = PIPE_B_ROOT / "data"
SR_DIR = ARCH_ROOT / "koshaontology" / "pipe-A" / "data" / "safety-requirements"

METHOD = "codex_manual_semantic_audit"

WATCH_GUIDES = {
    "A-G-18-2026",
    "G-116-2014",
    "B-5-2011",
    "B-M-11-2025",
    "B-M-32-2026",
    "A-G-10-2025",
    "B-E-21-2026",
    "D-57-2016",
    "C-C-16-2026",
    "B-E-3-2025",
    "B-E-19-2025",
    "H-110-2013",
    "H-221-2023",
}

GENERIC_FEATURES = {
    "GENERAL_WORKPLACE",
    "CHEMICAL",
    "CHEMICAL_EXPOSURE",
    "CHEMICAL_WORK",
    "FIRE",
    "EXPLOSION",
    "ELECTRICAL_WORK",
    "ELECTRICITY",
    "MACHINE",
    "ERGONOMIC",
    "BIOLOGICAL",
    "VENTILATION_POOR",
}

DOCUMENT_CUES = {
    "measurement_analysis": [
        "작업환경측정",
        "측정·분석",
        "측정ㆍ분석",
        "분석 기술",
        "시료채취",
        "검량선",
        "정량한계",
        "탈착효율",
        "기기분석",
        "생물학적 노출지표",
    ],
    "toxicity_test_protocol": [
        "독성시험",
        "시험 프로토콜",
        "시험법",
        "조직병리",
        "발암성시험",
        "유전독성",
        "피부과민성",
        "급성흡입",
        "급성경구",
        "AOP",
    ],
    "health_screening_or_diagnosis": [
        "건강진단",
        "폐활량검사",
        "순음청력검사",
        "운동부하검사",
        "업무적합성평가",
        "업무관련성",
        "검사 이상",
        "사후관리",
    ],
    "document_admin": [
        "물질안전보건자료",
        "SDS",
        "GHS",
        "유해성·위험성 분류",
        "유해성ㆍ위험성 분류",
        "신뢰성평가",
        "작성 지침",
    ],
    "risk_method": [
        "위험성평가",
        "평가 기법",
        "시나리오",
        "정량적 위험성",
        "업무관련성평가",
        "분석기법",
        "평가절차",
    ],
}

OPERATIONAL_CUES = [
    "작업",
    "운전",
    "정비",
    "설치",
    "해체",
    "하역",
    "굴착",
    "용접",
    "절단",
    "청소",
    "운반",
    "조리",
    "도장",
    "수리",
    "취급",
    "점검",
]

PURE_METHOD_CUES = [
    "리스크 평가",
    "위험성평가",
    "평가기법",
    "평가 기법",
    "정량적 위험성",
    "우선순위 결정",
    "방호계층분석",
    "LOPA",
    "HAZOP",
    "THERP",
    "SHERPA",
    "HEART",
    "OAT",
    "평가표",
    "분석기법",
    "시나리오 분석",
]

FIELD_CONTROL_CATEGORIES = {
    "CARGO",
    "CONSTRUCTION_EQUIP",
    "CRANE",
    "ELECTRIC",
    "EXCAVATION",
    "FALL",
    "FIRE_EXPLOSION",
    "MACHINE",
    "PRESSURE",
    "RIGGING",
    "SCAFFOLD",
    "SHORING",
    "STEELWORK",
    "VEHICLE",
    "CONFINED",
}

WEAK_DOC_SR_CATEGORIES = {"CHEMICAL", "PPE", "VENTILATION", "WORKPLACE", "MGMT"}

SR_CATEGORY_KEYWORDS = {
    "CARGO": ["하역", "화물", "항만", "선박", "컨테이너", "로프"],
    "CONFINED": ["밀폐", "질식", "산소", "유해가스", "탱크", "맨홀"],
    "CONSTRUCTION_EQUIP": ["굴착기", "항타", "건설기계", "양중", "타워크레인"],
    "CRANE": ["크레인", "양중", "줄걸이", "인양", "와이어로프"],
    "ELECTRIC": ["전기", "감전", "접지", "누전", "정전기", "방폭", "전선", "분전반"],
    "EXCAVATION": ["굴착", "흙막이", "터파기", "지반", "토사"],
    "FALL": ["추락", "넘어짐", "비계", "사다리", "개구부", "난간", "작업발판"],
    "FIRE_EXPLOSION": ["화재", "폭발", "화기", "인화", "가연", "위험물", "소화", "방폭"],
    "MACHINE": ["기계", "프레스", "컨베이어", "선반", "톱", "절단", "방호", "롤러"],
    "PRESSURE": ["압력", "보일러", "압력용기", "안전밸브", "배관", "파열판"],
    "PPE": ["보호구", "보호복", "호흡보호구", "안전모", "보안경", "장갑"],
    "CHEMICAL": ["화학", "유해물질", "노출", "시료", "분석", "MSDS", "SDS", "용제", "산", "가스"],
    "VEHICLE": ["차량", "지게차", "트럭", "경운기", "운전", "후진"],
    "VENTILATION": ["환기", "국소배기", "후드", "배기", "덕트"],
    "WORKPLACE": ["작업장", "통로", "바닥", "조명", "출입", "안전표지"],
}


@dataclass
class Flag:
    guide_code: str
    title: str
    batch_id: str
    severity: str
    issue: str
    message: str
    evidence: dict[str, Any]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_sr_registry() -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for path in sorted(SR_DIR.glob("sr-batch-*.json")):
        data = read_json(path)
        for group in data.get("srGroups", []) or []:
            sr_id = group.get("preAssignedId")
            if not sr_id:
                continue
            registry[sr_id] = {
                "category": group.get("category") or sr_id.split("-")[1],
                "title": group.get("title") or "",
                "section": group.get("section") or "",
            }
    return registry


def compact_text(*items: Any) -> str:
    chunks: list[str] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, list):
            chunks.extend(str(v) for v in item)
        else:
            chunks.append(str(item))
    return " ".join(chunks)


def classify_document_profile(guide: dict[str, Any]) -> list[str]:
    profile = guide.get("domain_profile") or {}
    primary_text = compact_text(
        guide.get("title"),
        profile.get("domain_family"),
        profile.get("required_context_terms"),
    )
    secondary_text = str(profile.get("evidence") or "")
    found: list[str] = []
    for label, cues in DOCUMENT_CUES.items():
        primary_hit = any(cue in primary_text for cue in cues)
        secondary_hits = sum(1 for cue in cues if cue in secondary_text)
        if not primary_hit and secondary_hits < 2:
            continue
        if label == "risk_method" and has_any(primary_text, OPERATIONAL_CUES) and not has_any(primary_text, PURE_METHOD_CUES):
            continue
        found.append(label)
    return found


def is_document_only_profile(guide: dict[str, Any], doc_types: list[str]) -> bool:
    profile = guide.get("domain_profile") or {}
    primary_text = compact_text(
        guide.get("title"),
        profile.get("domain_family"),
        profile.get("required_context_terms"),
    )
    operational_primary = has_any(primary_text, OPERATIONAL_CUES)
    lab_or_measurement_only = has_any(
        primary_text,
        [
            "작업환경측정",
            "측정·분석",
            "측정ㆍ분석",
            "분석기술지침",
            "생물학적 노출지표",
            "독성시험",
            "시험 프로토콜",
            "시험법",
        ],
    )
    health_only = has_any(
        primary_text,
        [
            "건강진단",
            "폐활량검사",
            "순음청력검사",
            "운동부하검사",
            "업무적합성평가",
            "업무관련성평가",
        ],
    )

    if "toxicity_test_protocol" in doc_types:
        return True
    if "measurement_analysis" in doc_types:
        return lab_or_measurement_only or not operational_primary
    if "health_screening_or_diagnosis" in doc_types:
        return health_only and not operational_primary
    if "document_admin" in doc_types:
        return not operational_primary
    if "risk_method" not in doc_types:
        return False
    return has_any(primary_text, PURE_METHOD_CUES)


def sr_category(sr_id: str, registry: dict[str, dict[str, str]]) -> str:
    if sr_id in registry:
        return registry[sr_id]["category"]
    parts = sr_id.split("-")
    return parts[1] if len(parts) > 2 else "UNKNOWN"


def list_sr_categories(guide: dict[str, Any], registry: dict[str, dict[str, str]]) -> list[str]:
    return [sr_category(c.get("sr_id", ""), registry) for c in guide.get("sr_link_candidates", [])]


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle and needle in text for needle in needles)


def token_overlap(left: str, right: str) -> set[str]:
    tokens = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", left))
    other = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", right))
    return {tok for tok in tokens & other if tok not in {"작업", "안전", "관리", "기술", "지침", "위험"}}


def audit_guide(
    guide: dict[str, Any],
    batch_id: str,
    registry: dict[str, dict[str, str]],
    sr_domain_families: dict[str, set[str]],
) -> list[Flag]:
    flags: list[Flag] = []
    code = guide.get("guide_code") or ""
    title = guide.get("title") or ""
    profile = guide.get("domain_profile") or {}
    family = profile.get("domain_family") or ""
    profile_level = profile.get("profile_level")
    required_terms = profile.get("required_context_terms") or []
    negative_terms = profile.get("negative_context_terms") or []
    industry_alignment = profile.get("industry_alignment") or []
    feature_codes = [c.get("feature_code") for c in guide.get("feature_candidates", []) if c.get("feature_code")]
    sr_candidates = guide.get("sr_link_candidates", []) or []
    sr_categories = list_sr_categories(guide, registry)
    doc_types = classify_document_profile(guide)
    profile_text = compact_text(title, family, profile.get("evidence"), required_terms, industry_alignment)

    def add(severity: str, issue: str, message: str, evidence: dict[str, Any]) -> None:
        flags.append(Flag(code, title, batch_id, severity, issue, message, evidence))

    if profile_level == "exclusive" and not required_terms:
        add("high", "exclusive_without_required_context", "exclusive profile인데 필수 문맥 term이 비어 있음", {})

    if profile_level == "exclusive" and not negative_terms:
        add("medium", "exclusive_without_negative_context", "exclusive Guide인데 제외 문맥 term이 비어 있어 과추천 방어가 약함", {})

    if profile_level == "exclusive" and not industry_alignment:
        add("medium", "exclusive_without_industry_alignment", "exclusive Guide인데 업종/작업장 alignment가 비어 있음", {})

    if required_terms and not has_any(compact_text(title, profile.get("evidence"), family), list(required_terms)):
        add(
            "medium",
            "required_terms_not_grounded",
            "required_context_terms가 title/evidence/domain_family에 거의 근거를 남기지 않음",
            {"required_context_terms": required_terms[:8], "profile_evidence": profile.get("evidence")},
        )

    if profile_level == "exclusive" and feature_codes and set(feature_codes).issubset(GENERIC_FEATURES):
        add(
            "medium",
            "generic_feature_only_for_exclusive",
            "exclusive Guide인데 feature가 넓은 일반 feature만 있어 사진 매칭에서 의미 경계가 약함",
            {"feature_codes": feature_codes, "domain_family": family},
        )

    if doc_types and sr_candidates:
        field_sr = [
            c.get("sr_id")
            for c in sr_candidates
            if sr_category(c.get("sr_id", ""), registry) in FIELD_CONTROL_CATEGORIES
            and (c.get("review_status") == "candidate" or float(c.get("confidence") or 0) >= 0.72)
        ]
        if field_sr:
            document_only = is_document_only_profile(guide, doc_types)
            add(
                "high" if document_only else "medium",
                "document_profile_has_field_control_sr" if document_only else "method_or_planning_profile_has_field_control_sr",
                "문서/분석/검진 성격 Guide에 현장 시정조치형 SR이 강하게 붙어 있음"
                if document_only
                else "평가/계획 성격 Guide에 현장 시정조치형 SR이 붙어 있어 절차 추천 사용범위 확인 필요",
                {"document_types": doc_types, "sr_ids": field_sr[:10]},
            )

        weak_doc_sr = [
            c.get("sr_id")
            for c in sr_candidates
            if sr_category(c.get("sr_id", ""), registry) in WEAK_DOC_SR_CATEGORIES
        ]
        if len(weak_doc_sr) >= 3:
            add(
                "medium",
                "document_profile_has_many_generic_control_sr",
                "문서/분석 Guide에 화학/PPE/작업장 일반 SR이 여러 개 붙어 있어 절차 추천 과노출 위험",
                {"document_types": doc_types, "sr_ids": weak_doc_sr[:10]},
            )

    if not sr_candidates:
        looks_operational = profile_level != "general" and has_any(profile_text, OPERATIONAL_CUES)
        looks_document = bool(doc_types)
        if looks_operational and not looks_document:
            add(
                "medium",
                "operational_guide_without_sr_candidate",
                "작업/운전/정비 Guide로 보이는데 SR 후보가 없음",
                {"domain_family": family, "required_context_terms": required_terms[:8]},
            )

    if len(sr_candidates) >= 8:
        add(
            "medium",
            "too_many_sr_candidates",
            "한 Guide에 SR 후보가 8개 이상 붙어 ranking/import 전에 우선순위 조정 필요",
            {"sr_count": len(sr_candidates), "sr_categories": dict(Counter(sr_categories))},
        )

    for candidate in sr_candidates:
        sr_id = candidate.get("sr_id") or ""
        category = sr_category(sr_id, registry)
        confidence = float(candidate.get("confidence") or 0)
        if confidence < 0.72:
            continue
        keywords = SR_CATEGORY_KEYWORDS.get(category)
        if not keywords:
            continue
        guide_context = compact_text(profile_text, candidate.get("evidence"), feature_codes)
        if not has_any(guide_context, keywords):
            add(
                "medium",
                "sr_category_context_mismatch",
                "SR category를 지지하는 Guide 문맥/feature/evidence 단어가 약함",
                {
                    "sr_id": sr_id,
                    "sr_category": category,
                    "sr_title": registry.get(sr_id, {}).get("title"),
                    "confidence": confidence,
                    "expected_keywords": keywords[:8],
                    "candidate_evidence": candidate.get("evidence"),
                },
            )

    for candidate in sr_candidates:
        sr_id = candidate.get("sr_id") or ""
        confidence = float(candidate.get("confidence") or 0)
        if confidence < 0.76:
            continue
        sr_info = registry.get(sr_id, {})
        overlap = token_overlap(compact_text(required_terms, title, family), compact_text(candidate.get("evidence"), sr_info.get("title")))
        if not overlap and profile_level == "exclusive":
            add(
                "low",
                "high_conf_sr_lacks_profile_token_overlap",
                "높은 confidence SR 후보가 Guide 고유 문맥 term과 직접 겹치지 않음",
                {
                    "sr_id": sr_id,
                    "sr_title": sr_info.get("title"),
                    "confidence": confidence,
                    "candidate_evidence": candidate.get("evidence"),
                },
            )

    visual_types = [c.get("cue_type") for c in guide.get("visual_trigger_candidates", [])]
    document_visual = [t for t in visual_types if t and "document" in t]
    physical_terms = has_any(profile_text, OPERATIONAL_CUES)
    if profile_level == "exclusive" and physical_terms and visual_types and len(document_visual) == len(visual_types):
        add(
            "low",
            "physical_guide_has_document_only_visual_triggers",
            "물리 작업 Guide처럼 보이지만 visual trigger가 문서 단서뿐임",
            {"visual_trigger_types": visual_types},
        )

    for candidate in sr_candidates:
        sr_id = candidate.get("sr_id") or ""
        sr_domain_families[sr_id].add(family)

    return flags


def main() -> int:
    registry = load_sr_registry()
    batch_paths = sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json"))
    all_flags: list[Flag] = []
    sr_domain_families: dict[str, set[str]] = defaultdict(set)
    guide_rows: list[dict[str, Any]] = []
    sr_counter: Counter[str] = Counter()
    profile_counter: Counter[str] = Counter()
    batch_counter: Counter[str] = Counter()
    no_sr_count = 0

    for path in batch_paths:
        data = read_json(path)
        batch_id = (data.get("scope") or {}).get("batch_id") or path.stem.rsplit("-", 1)[-1]
        for guide in data.get("guides", []) or []:
            guide_flags = audit_guide(guide, batch_id, registry, sr_domain_families)
            all_flags.extend(guide_flags)
            guide_code = guide.get("guide_code")
            profile = guide.get("domain_profile") or {}
            profile_counter[profile.get("profile_level") or "unknown"] += 1
            batch_counter[batch_id] += len(guide_flags)
            for c in guide.get("sr_link_candidates", []) or []:
                sr_counter[c.get("sr_id") or "UNKNOWN"] += 1
            if not guide.get("sr_link_candidates"):
                no_sr_count += 1
            guide_rows.append(
                {
                    "guide_code": guide_code,
                    "title": guide.get("title"),
                    "batch_id": batch_id,
                    "profile_level": profile.get("profile_level"),
                    "domain_family": profile.get("domain_family"),
                    "doc_types": classify_document_profile(guide),
                    "feature_codes": [c.get("feature_code") for c in guide.get("feature_candidates", [])],
                    "sr_ids": [c.get("sr_id") for c in guide.get("sr_link_candidates", [])],
                    "flag_count": len(guide_flags),
                    "flag_issues": [f.issue for f in guide_flags],
                }
            )

    severity_counts = Counter(f.severity for f in all_flags)
    issue_counts = Counter(f.issue for f in all_flags)
    flagged_guides = {f.guide_code for f in all_flags}
    high_guides = {f.guide_code for f in all_flags if f.severity == "high"}

    overused_sr = []
    for sr_id, count in sr_counter.most_common(40):
        families = sorted(sr_domain_families.get(sr_id, set()))
        overused_sr.append(
            {
                "sr_id": sr_id,
                "count": count,
                "category": registry.get(sr_id, {}).get("category"),
                "title": registry.get(sr_id, {}).get("title"),
                "distinct_domain_families": len(families),
                "sample_domain_families": families[:12],
            }
        )

    watch_rows = [row for row in guide_rows if row["guide_code"] in WATCH_GUIDES]
    high_examples = [asdict(f) for f in all_flags if f.severity == "high"][:80]
    medium_examples = [asdict(f) for f in all_flags if f.severity == "medium"][:120]

    report = {
        "generated_at": "2026-05-09",
        "method": METHOD,
        "external_api_used": False,
        "db_imported": False,
        "source": "pipe-B/data/manual-enrichment-domain-guard-batch-001..035.json",
        "scope": {
            "batch_files": len(batch_paths),
            "guides": len(guide_rows),
            "no_sr_guides": no_sr_count,
        },
        "summary": {
            "flagged_guides": len(flagged_guides),
            "high_risk_guides": len(high_guides),
            "total_flags": len(all_flags),
            "severity_counts": dict(severity_counts),
            "issue_counts": dict(issue_counts.most_common()),
            "profile_level_distribution": dict(profile_counter),
        },
        "interpretation": [
            "Flags are review queues, not automatic corrections.",
            "High risk usually means a document/analysis/medical profile is linked to operational field-control SRs strongly enough to pollute procedure ranking.",
            "Medium risk usually means generic SR/feature over-breadth or missing semantic grounding.",
            "Candidate data remains candidate-only; asserted mapping updates are still zero.",
        ],
        "top_overused_sr_candidates": overused_sr,
        "batch_flag_counts": dict(sorted(batch_counter.items())),
        "watch_guides": watch_rows,
        "high_risk_examples": high_examples,
        "medium_risk_examples": medium_examples,
        "all_flags": [asdict(f) for f in all_flags],
    }

    json_path = DATA_DIR / "manual-enrichment-domain-guard-semantic-audit.json"
    write_json(json_path, report)

    issue_lines = "\n".join(f"| {issue} | {count} |" for issue, count in issue_counts.most_common())
    severity_lines = "\n".join(f"| {sev} | {count} |" for sev, count in sorted(severity_counts.items()))
    overused_lines = "\n".join(
        f"| {row['sr_id']} | {row['count']} | {row['distinct_domain_families']} | {row['title']} |"
        for row in overused_sr[:20]
    )
    watch_lines = "\n".join(
        f"| {row['guide_code']} | {row['profile_level']} | {row['domain_family']} | {row['flag_count']} | {', '.join(row['flag_issues'][:5])} |"
        for row in watch_rows
    )
    high_lines = "\n".join(
        f"| {f['guide_code']} | {f['issue']} | {f['message']} |"
        for f in high_examples[:30]
    )

    md_path = DATA_DIR / "manual-enrichment-domain-guard-semantic-audit.md"
    md_path.write_text(
        f"""# Manual Domain Guard Semantic Audit

Generated: 2026-05-09

This audit checks the semantic fit of the 35 candidate-only manual enrichment batches. It does not call external APIs, does not import to PostgreSQL, and does not promote asserted mappings.

## Summary

| Item | Count |
|---|---:|
| Batch files | {len(batch_paths)} |
| Guides | {len(guide_rows)} |
| Guides with any flag | {len(flagged_guides)} |
| High-risk guides | {len(high_guides)} |
| Total flags | {len(all_flags)} |
| Guides with no SR candidate | {no_sr_count} |

## Severity Counts

| Severity | Count |
|---|---:|
{severity_lines}

## Issue Counts

| Issue | Count |
|---|---:|
{issue_lines}

## Top Overused SR Candidates

High counts are not automatically wrong, but broad SRs used across many unrelated domain families are likely to need ranking dampening or review-only treatment.

| SR | Count | Distinct domain families | Title |
|---|---:|---:|---|
{overused_lines}

## Watch Guides

| Guide | Profile | Domain family | Flags | Issues |
|---|---|---|---:|---|
{watch_lines}

## High-Risk Examples

| Guide | Issue | Message |
|---|---|---|
{high_lines}

## Interpretation

- These are review queues, not automatic fixes.
- The strongest risk is document/analysis/medical Guides receiving operational field-control SRs.
- The second risk is broad chemical/PPE/workplace SRs appearing across too many unrelated domain families.
- Candidate JSON remains candidate-only; asserted mapping update count remains zero.
""",
        encoding="utf-8",
    )

    print(json_path.relative_to(PIPE_B_ROOT))
    print(md_path.relative_to(PIPE_B_ROOT))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
