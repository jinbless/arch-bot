"""Photo-context suitability policy for standard procedure recommendations.

This is a serving-time guard for photo-based recommendations.  It does not
change SHE/SR/penalty reasoning and it is not legal evidence.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
GUIDE_PHOTO_MATCHABILITY_PATH = DATA_DIR / "guide_photo_matchability.v1.json"

PHOTO_ACTIONABLE = "photo_actionable"
PHOTO_CONDITIONAL_FOLLOWUP = "photo_conditional_followup"
PHOTO_UNMATCHABLE = "photo_unmatchable"

TOP_ALLOW = "allow_photo_top"
TOP_SUPPRESS = "suppress_photo_top"
FOLLOWUP_NONE = "none"
FOLLOWUP_EXPLICIT_CONTEXT_ONLY = "explicit_context_only"

UNMATCHABLE_ROLES = frozenset({
    "measurement_analysis",
    "test_protocol",
    "health_screening",
    "risk_method",
    "document_reference",
})

ROLE_CONTEXT_TERMS = {
    "management_program": (
        "작업계획서",
        "허가서",
        "프로그램",
        "관리계획",
        "절차서",
        "비상조치계획",
    ),
    "measurement_analysis": (
        "작업환경측정",
        "측정",
        "분석",
        "시료",
        "검량선",
        "시험",
        "독성시험",
    ),
    "test_protocol": (
        "측정",
        "분석",
        "시료",
        "검량선",
        "시험",
        "독성시험",
    ),
    "health_screening": (
        "건강진단",
        "검진",
        "의학적 관리",
        "폐활량검사",
    ),
    "risk_method": (
        "위험성평가",
        "리스크 평가",
        "문서",
        "서식",
        "보고서",
        "매뉴얼",
    ),
    "document_reference": (
        "위험성평가",
        "리스크 평가",
        "문서",
        "서식",
        "보고서",
        "매뉴얼",
    ),
}


def _blob(values: Iterable[str | None]) -> str:
    return " ".join(value for value in values if value).lower()


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


@lru_cache(maxsize=1)
def _load_artifact() -> dict[str, dict]:
    if not GUIDE_PHOTO_MATCHABILITY_PATH.exists():
        return {}
    try:
        data = json.loads(GUIDE_PHOTO_MATCHABILITY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    profiles = data.get("profiles")
    return profiles if isinstance(profiles, dict) else {}


def role_context_terms(role: str | None) -> list[str]:
    if not role:
        return []
    if role == "management_program":
        return list(ROLE_CONTEXT_TERMS["management_program"])
    if role in {"measurement_analysis", "test_protocol"}:
        return _unique([*ROLE_CONTEXT_TERMS["measurement_analysis"], *ROLE_CONTEXT_TERMS["test_protocol"]])
    if role == "health_screening":
        return list(ROLE_CONTEXT_TERMS["health_screening"])
    if role in {"risk_method", "document_reference"}:
        return _unique([*ROLE_CONTEXT_TERMS["risk_method"], *ROLE_CONTEXT_TERMS["document_reference"]])
    return []


def explicit_followup_context_hit(
    profile: dict | None,
    *,
    visual_cues: list[str] | None = None,
    context_text: str | None = None,
) -> bool:
    """Return true when a photo/text observation explicitly asks for a non-top role.

    Role terms are intentionally narrow.  Broad words such as "관리" are not
    enough to bring a management/program Guide into photo top recommendations.
    """
    role = str((profile or {}).get("procedure_role") or "field_control")
    terms = role_context_terms(role)
    if not terms:
        return False
    text = _blob([*(visual_cues or []), context_text])
    return any(term.lower() in text for term in terms)


def derive_photo_matchability(profile: dict | None) -> dict:
    """Conservative fallback classification used before the artifact exists."""
    role = str((profile or {}).get("procedure_role") or "field_control")
    if role == "management_program":
        return {
            "photo_matchability": PHOTO_CONDITIONAL_FOLLOWUP,
            "top_procedure_policy": TOP_SUPPRESS,
            "followup_policy": FOLLOWUP_EXPLICIT_CONTEXT_ONLY,
            "review_status": "derived",
        }
    if role in UNMATCHABLE_ROLES:
        return {
            "photo_matchability": PHOTO_UNMATCHABLE,
            "top_procedure_policy": TOP_SUPPRESS,
            "followup_policy": FOLLOWUP_EXPLICIT_CONTEXT_ONLY,
            "review_status": "derived",
        }
    return {
        "photo_matchability": PHOTO_ACTIONABLE,
        "top_procedure_policy": TOP_ALLOW,
        "followup_policy": FOLLOWUP_NONE,
        "review_status": "derived",
    }


def get_photo_matchability(guide_code: str | None, profile: dict | None = None) -> dict:
    artifact = _load_artifact()
    if guide_code and guide_code in artifact:
        return artifact[guide_code]
    if profile and profile.get("photo_matchability"):
        return {
            "photo_matchability": profile.get("photo_matchability"),
            "top_procedure_policy": profile.get("top_procedure_policy") or TOP_SUPPRESS,
            "followup_policy": profile.get("followup_policy") or FOLLOWUP_EXPLICIT_CONTEXT_ONLY,
            "review_status": profile.get("review_status") or "profile",
        }
    return derive_photo_matchability(profile)


def top_photo_allowed(guide_code: str | None, profile: dict | None = None) -> bool:
    policy = get_photo_matchability(guide_code, profile)
    return policy.get("photo_matchability") == PHOTO_ACTIONABLE and policy.get("top_procedure_policy") == TOP_ALLOW


def followup_photo_allowed(
    guide_code: str | None,
    profile: dict | None,
    *,
    visual_cues: list[str] | None = None,
    context_text: str | None = None,
) -> bool:
    policy = get_photo_matchability(guide_code, profile)
    if policy.get("photo_matchability") == PHOTO_ACTIONABLE:
        return False
    if policy.get("followup_policy") != FOLLOWUP_EXPLICIT_CONTEXT_ONLY:
        return False
    return explicit_followup_context_hit(profile, visual_cues=visual_cues, context_text=context_text)
