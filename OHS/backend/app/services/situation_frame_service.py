"""SituationFrame helpers for guide recommendation support.

The frame sits between flat RiskFeature codes and Guide/SHE routing.  It keeps
specific child contexts such as BAND_SAW separate from broad parent contexts
such as MACHINE.  In this first iteration the frame is allowed to support Guide
ranking only; it must not drive finding status, penalty exposure, or asserted
SR evidence.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SITUATION_CONTEXT_TAXONOMY_PATH = Path(
    os.getenv("OHS_SITUATION_CONTEXT_TAXONOMY_PATH", str(DATA_DIR / "situation_context_taxonomy.v20.json"))
)
GUIDE_SUPPORT_CANDIDATES_PATH = Path(
    os.getenv("OHS_GUIDE_SUPPORT_CANDIDATES_PATH", str(DATA_DIR / "guide_support_candidates.v20.jsonl"))
)

TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")

UNSAFE_TERMS = (
    "미설치", "미착용", "미체결", "미차단", "노출", "파손", "손상",
    "누출", "가동 중", "회전 중", "접근", "끼임", "절단", "화상",
    "감전", "붕괴", "추락", "충돌", "폭발", "환기", "방독마스크 없이",
    "보호구 없이", "장갑 없이", "마스크 없이", "잠금 장치", "잠금장치",
    "미적용", "미정지", "정지하지", "미흡", "부정착용", "턱 아래",
    "턱 착용", "고분진",
)
SAFE_TERMS = (
    "전원 차단", "전원 차단 후", "잠금표지", "잠금 표지", "LOTO", "보호구 착용",
    "장갑을 착용", "마스크를 착용", "난간을 완비", "정상", "확인한 뒤",
)
UNCERTAINTY_TERMS = (
    "여부", "불명", "불분명", "확인 불가", "확인불가", "가능성",
    "시도", "하려고", "아직", "일 수", "사진만으로", "처럼 보",
)
SAFE_TRIGGER_ONLY_BLOCK_TERMS = (
    "올바른 장면",
    "체크리스트로 완료",
    "이상 없음을 기록",
    "점검을 완료",
    "정상 작동",
    "압력 게이지 0",
    "잔압 완전 방출",
    "방열 장갑 착용",
    "안면 보호대 착용",
    "절차 준수",
    "정상 안전 절차",
    "현 절차 유지",
    "착용 후",
)
NEGATED_SAFE_CONTEXT_TERMS = (
    "미적용", "미실시", "미착용", "미차단", "미정지", "미흡",
    "없이", "없", "않", "걸려 있지", "누락", "불량", "부재", "대비",
)
LOCKOUT_MISSING_TERMS = (
    "없", "미실시", "미적용", "미차단", "걸려 있지", "잠금 장치는 걸려 있지", "누락",
)
ENERGIZED_TERMS = ("가동 중", "운전 중", "회전 중", "전원이 켜", "활선", "충전부", "미정지")
DEENERGIZED_TERMS = ("전원 차단", "전원 off", "전원 OFF", "코드를 빼", "분리")
LOCKED_OUT_TERMS = ("잠금표지", "잠금 표지", "LOTO", "lockout", "tagout", "잠근 뒤", "전원 잠금")
LOCKOUT_CONTROL_TERMS = LOCKED_OUT_TERMS + ("잠금 장치 적용", "잠금장치 적용")

TASK_KEYWORDS = {
    "cleaning": ("청소", "세척", "닦", "제거"),
    "maintenance": ("점검", "정비", "유지보수", "수리", "교체"),
    "operation": ("가동", "운전", "작업 중", "사용 중"),
    "cutting": ("절단", "블레이드", "톱", "칼날"),
    "painting": ("도장", "스프레이", "페인트"),
    "material_handling": ("운반", "적재", "하역", "이동"),
    "hot_work": ("용접", "불꽃", "아크"),
    "chemical_handling": ("화학", "용제", "시약", "MSDS", "약품"),
}


@dataclass
class SituationFrame:
    equipment_contexts: list[str] = field(default_factory=list)
    parent_contexts: list[str] = field(default_factory=list)
    task_contexts: list[str] = field(default_factory=list)
    accident_types: list[str] = field(default_factory=list)
    hazardous_agents: list[str] = field(default_factory=list)
    energy_state: str = "unknown"
    control_state: list[str] = field(default_factory=list)
    ppe_state: list[str] = field(default_factory=list)
    environmental_state: list[str] = field(default_factory=list)
    observable_cues: list[str] = field(default_factory=list)
    safe_cues: list[str] = field(default_factory=list)
    uncertainty_cues: list[str] = field(default_factory=list)
    match_policy: str = "guide_support_only"
    industry_contexts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _blob(values: list[str] | None) -> str:
    return " ".join(str(value) for value in values or [] if value).lower()


def _contains_any(text: str, terms: list[str] | tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return _unique([term for term in terms if term and term.lower() in lower])


def _contains_contextual_terms(
    text: str,
    terms: list[str] | tuple[str, ...],
    *,
    block_terms: list[str] | tuple[str, ...] = (),
    window: int = 12,
) -> list[str]:
    lower = text.lower()
    hits: list[str] = []
    block_lowers = [term.lower() for term in block_terms if term]
    for term in terms:
        lowered = term.lower()
        if not lowered:
            continue
        start = lower.find(lowered)
        while start >= 0:
            span = lower[max(0, start - window): min(len(lower), start + len(lowered) + window)]
            if not any(block in span for block in block_lowers):
                hits.append(term)
                break
            start = lower.find(lowered, start + len(lowered))
    return _unique(hits)


def _has_safe_trigger_only_context(text: str) -> bool:
    return bool(
        _contains_contextual_terms(
            text,
            SAFE_TRIGGER_ONLY_BLOCK_TERMS,
            block_terms=NEGATED_SAFE_CONTEXT_TERMS,
        )
    )


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall((text or "").lower()))


@lru_cache(maxsize=1)
def load_situation_context_taxonomy(path: str | None = None) -> dict[str, Any]:
    taxonomy_path = Path(path) if path else SITUATION_CONTEXT_TAXONOMY_PATH
    if not taxonomy_path.exists():
        return {"child_contexts": {}, "parent_contexts": {}, "aliases": {}}
    return json.loads(taxonomy_path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_guide_support_candidates(path: str | None = None) -> list[dict[str, Any]]:
    candidate_path = Path(path) if path else GUIDE_SUPPORT_CANDIDATES_PATH
    if not candidate_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in candidate_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_situation_frame(
    *,
    canonical: dict[str, Any],
    normalized: dict[str, Any] | None = None,
    visual_cues: list[str] | None = None,
    context_text: str | None = None,
    industry_contexts: list[str] | None = None,
    taxonomy: dict[str, Any] | None = None,
) -> SituationFrame:
    taxonomy = taxonomy or load_situation_context_taxonomy()
    text = _blob([context_text or "", *(visual_cues or [])])
    work_contexts = _unique(list(canonical.get("work_contexts") or []))
    accident_types = _unique(list(canonical.get("accident_types") or []))
    hazardous_agents = _unique(list(canonical.get("hazardous_agents") or []))

    equipment_contexts: list[str] = []
    parent_contexts: list[str] = list(work_contexts)
    aliases = taxonomy.get("aliases") or {}
    child_contexts = taxonomy.get("child_contexts") or {}
    for child_code, info in child_contexts.items():
        terms = _unique([
            child_code,
            str(child_code).replace("_", " "),
            *(aliases.get(child_code) or []),
            *((info or {}).get("aliases") or []),
        ])
        if child_code in work_contexts or _contains_any(text, terms):
            equipment_contexts.append(child_code)
            parent_contexts.extend((info or {}).get("parents") or [])

    task_contexts = [
        task
        for task, terms in TASK_KEYWORDS.items()
        if _contains_any(text, terms)
    ]
    observable_cues = _contains_any(text, UNSAFE_TERMS)
    safe_cues = _contains_contextual_terms(
        text,
        SAFE_TERMS,
        block_terms=NEGATED_SAFE_CONTEXT_TERMS,
    )
    uncertainty_cues = _contains_any(text, UNCERTAINTY_TERMS)
    lockout_hits = _contains_any(text, LOCKED_OUT_TERMS)
    non_negated_lockout_hits = _contains_contextual_terms(
        text,
        LOCKED_OUT_TERMS,
        block_terms=NEGATED_SAFE_CONTEXT_TERMS,
    )
    non_negated_deenergized_hits = _contains_contextual_terms(
        text,
        DEENERGIZED_TERMS,
        block_terms=NEGATED_SAFE_CONTEXT_TERMS,
    )
    if non_negated_lockout_hits:
        energy_state = "locked_out"
    elif non_negated_deenergized_hits:
        energy_state = "deenergized"
    elif _contains_any(text, ENERGIZED_TERMS):
        energy_state = "energized"
    else:
        energy_state = "unknown"

    control_state: list[str] = []
    if _contains_any(text, ("방호", "가드", "덮개", "커버")):
        if _contains_any(text, ("없", "제거", "열려", "미설치", "노출")):
            control_state.append("guard_missing")
        else:
            control_state.append("guard_present")
    if lockout_hits or _contains_any(text, LOCKOUT_CONTROL_TERMS):
        if _contains_any(text, LOCKOUT_MISSING_TERMS) or not non_negated_lockout_hits:
            control_state.append("lockout_missing")
        else:
            control_state.append("lockout_present")
    if _contains_any(text, ("환기", "덕트", "배기")):
        if _contains_any(text, ("없", "무환기", "미흡", "불량")):
            control_state.append("ventilation_missing")
        else:
            control_state.append("ventilation_present")

    if safe_cues and not observable_cues and not accident_types:
        match_policy = "status_safe"
    elif uncertainty_cues:
        match_policy = "confirmation_required"
    else:
        match_policy = "guide_support_only"

    return SituationFrame(
        equipment_contexts=_unique(equipment_contexts),
        parent_contexts=_unique(parent_contexts),
        task_contexts=_unique(task_contexts),
        accident_types=accident_types,
        hazardous_agents=hazardous_agents,
        energy_state=energy_state,
        control_state=_unique(control_state),
        ppe_state=_unique(list((normalized or {}).get("ppe_states") or [])),
        environmental_state=_unique(list((normalized or {}).get("environmental") or [])),
        observable_cues=observable_cues,
        safe_cues=safe_cues,
        uncertainty_cues=uncertainty_cues,
        match_policy=match_policy,
        industry_contexts=_unique(industry_contexts or []),
    )


def _term_hits(text: str, terms: list[str], limit: int = 4) -> list[str]:
    hits: list[str] = []
    lower = text.lower()
    for term in terms:
        if term and str(term).lower() in lower and term not in hits:
            hits.append(str(term))
        if len(hits) >= limit:
            break
    return hits


def match_guide_support_candidates(
    situation_frame: SituationFrame | dict[str, Any] | None,
    *,
    visual_cues: list[str] | None = None,
    context_text: str | None = None,
    candidates: list[dict[str, Any]] | None = None,
    taxonomy: dict[str, Any] | None = None,
    limit: int = 30,
    require_observable_cue: bool = True,
) -> list[dict[str, Any]]:
    if not situation_frame:
        return []
    frame = situation_frame if isinstance(situation_frame, dict) else situation_frame.to_dict()
    if frame.get("match_policy") == "status_safe":
        return []
    missing_observable_cue = require_observable_cue and not frame.get("observable_cues")

    taxonomy = taxonomy or load_situation_context_taxonomy()
    aliases = taxonomy.get("aliases") or {}
    text = _blob([context_text or "", *(visual_cues or [])])
    frame_children = set(frame.get("equipment_contexts") or [])
    frame_parents = set(frame.get("parent_contexts") or [])
    frame_accidents = set(frame.get("accident_types") or [])
    frame_agents = set(frame.get("hazardous_agents") or [])
    rows = candidates if candidates is not None else load_guide_support_candidates()
    scored: list[tuple[float, dict[str, Any]]] = []

    for row in rows:
        if row.get("allowed_runtime_use") != "guide_support_only":
            continue
        if row.get("review_status") not in {"candidate", "asserted"}:
            continue
        child = row.get("child_context")
        parents = set(row.get("parent_contexts") or [])
        accident = row.get("accident_type")
        agent = row.get("hazardous_agent")
        if accident and accident != "OTHER" and frame_accidents and accident not in frame_accidents:
            continue
        if agent and agent != "OTHER" and frame_agents and agent not in frame_agents:
            continue

        child_terms = _unique([child, str(child or "").replace("_", " "), *(aliases.get(child) or [])])
        exact_child_hit = bool(child and child in frame_children)
        child_text_hit = bool(_term_hits(text, child_terms, limit=1))
        parent_hit = bool(parents & frame_parents)
        trigger_hits = _term_hits(text, row.get("trigger_terms") or [], limit=4)
        if row.get("require_trigger_match") and not trigger_hits:
            continue
        if missing_observable_cue and not row.get("allow_trigger_only_support"):
            continue
        if missing_observable_cue and not trigger_hits:
            continue
        if row.get("allow_trigger_only_support") and _has_safe_trigger_only_context(text):
            continue
        if not (exact_child_hit or child_text_hit):
            # Parent-only and trigger-only matches are explicitly support-blocked.
            continue
        if not (parent_hit or exact_child_hit or child_text_hit):
            continue

        score = 0.34
        if exact_child_hit:
            score += 0.20
        if child_text_hit:
            score += 0.16
        if trigger_hits:
            score += min(0.24, len(trigger_hits) * 0.08)
        if frame.get("match_policy") == "confirmation_required":
            score *= 0.65
        row_copy = dict(row)
        row_copy["support_score"] = round(min(0.85, score), 4)
        row_copy["support_reasons"] = _unique([
            "child_context_match" if exact_child_hit else "",
            "child_text_match" if child_text_hit else "",
            "trigger_match" if trigger_hits else "",
            f"match_policy:{frame.get('match_policy')}",
        ])
        row_copy["match_policy"] = frame.get("match_policy")
        row_copy["trigger_hits"] = trigger_hits
        scored.append((row_copy["support_score"], row_copy))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:limit]]
