import json
import os
from functools import lru_cache
from pathlib import Path


_INTRO = """You are a workplace-safety observation extractor.

Your job is not to make legal conclusions. The ontology and deterministic rule
engine will map observations to SHE patterns, safety requirements, guides, and
penalty paths later."""


_FEATURE_GUIDE_HEADER = """Output policy:

- Write only facts that are visible in the image or explicitly described.
- Split short visual cues for pattern matching.
- Do not choose law articles, penalties, KOSHA guide numbers, or final violation status.
- If something is uncertain, say it is uncertain instead of inventing detail.
- All user-facing text values (visual_observations, visual_cues, risk descriptions, recommendations, reasoning text, etc.) MUST be written in Korean (한국어). JSON field names and enum codes stay in English (e.g. accident_type, FALL, SCAFFOLD).
- Even if the user input is short or mixed-language, respond in Korean."""


_CATALOG_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "risk_feature_catalog.json"
)


@lru_cache(maxsize=1)
def _load_catalog_enums() -> dict[str, list[str]]:
    """Return {axis: sorted[codes]} from current risk_feature_catalog.json."""
    if not _CATALOG_PATH.is_file():
        return {}
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for axis_name, axis_def in data.get("axes", {}).items():
        if not isinstance(axis_def, dict):
            continue
        codes = sorted((axis_def.get("codes") or {}).keys())
        if codes:
            out[axis_name] = codes
    return out


def _build_axis_enum_text() -> str:
    """Build axis enum guidance for risk_feature_candidates.

    Phase F.2+closed-vocab — Layer 0 Vision LLM에 catalog v3.3 enum 목록 명시.
    LLM이 'MACHINERY', 'cooking' 같은 catalog 미존재 영어 변형 생성 차단.
    """
    enums = _load_catalog_enums()
    if not enums:
        return ""
    lines = ["- risk_feature_candidates: catalog 5 axis. **반드시 아래 enum 코드만 사용.** catalog 미존재 코드 생성 금지."]
    for axis in ("accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"):
        codes = enums.get(axis, [])
        if not codes:
            continue
        # Print all codes — 한 axis당 ~50-200 codes
        codes_text = ", ".join(codes)
        lines.append(f"  - {axis} ({len(codes)} codes): {codes_text}")
    lines.append("  - 위 코드 외의 자유 영어 생성(예: MACHINERY, cooking, KITCHEN)은 절대 금지.")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def build_system_prompt() -> str:
    parts = [_INTRO, _FEATURE_GUIDE_HEADER]
    enum_block = _build_axis_enum_text()
    if enum_block:
        parts.append(enum_block)
    return "\n\n".join(parts)
