import json
import os
from pathlib import Path
from typing import Optional

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.integrations.prompts.analysis_prompts import (
    IMAGE_ANALYSIS_PROMPT,
    SYSTEM_PROMPT,
    TEXT_ANALYSIS_PROMPT,
)
from app.integrations.prompts.guide_validator_prompt import (
    RESPONSE_SCHEMA as VALIDATOR_RESPONSE_SCHEMA,
    SYSTEM_PROMPT as VALIDATOR_SYSTEM_PROMPT,
    build_user_prompt as build_validator_user_prompt,
)


RERANK_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


def _load_catalog_codes() -> list[str]:
    """Tier 3.A — risk_feature_catalog 전체 코드를 단일 enum으로 수집.

    schema enum constraint용. 532개 코드 (accident_type 161 + hazardous_agent 99
    + work_context 204 + ppe_state 50 + environmental 18). axis-text 페어링은
    LLM 신뢰 (axis enum + text enum으로 search space 좁힘).

    Catalog 갱신 시 자동 반영 (모듈 import 시 1회 로드).
    재시작 없이 catalog 변경 적용하려면 backend restart 필요 (캐시 module-level).
    """
    catalog_path = (
        Path(__file__).resolve().parents[1] / "data" / "risk_feature_catalog.json"
    )
    if not catalog_path.exists():
        return []
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    codes: set[str] = set()
    axes = data.get("axes", {})
    for axis_name, axis_info in axes.items():
        if isinstance(axis_info, dict):
            axis_codes = axis_info.get("codes", {}) or {}
            if isinstance(axis_codes, dict):
                codes.update(axis_codes.keys())
            elif isinstance(axis_codes, list):
                codes.update(axis_codes)
        elif isinstance(axis_info, list):
            codes.update(axis_info)
    return sorted(codes)


# Module-level cache (computed once at import; backend restart for updates)
_ALL_CATALOG_CODES = _load_catalog_codes()


ONTOLOGY_OBSERVATION_SCHEMA = {
    "name": "ontology_observation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "visual_observations": {
                "type": "array",
                "description": "Facts directly visible in the photo or described in text.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "confidence": {"type": "number"},
                        "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                    },
                    "required": ["text", "confidence", "severity"],
                    "additionalProperties": False,
                },
            },
            "visual_cues": {
                "type": "array",
                "description": "Short visual cues used for SHE pattern matching.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "cue_type": {
                            "type": "string",
                            "enum": ["object", "state", "absence", "environment", "activity", "other"],
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": ["text", "cue_type", "confidence"],
                    "additionalProperties": False,
                },
            },
            "risk_feature_candidates": {
                "type": "array",
                "description": "Candidate terms for risk:RiskFeature normalization. "
                "text는 catalog enum (532 codes) 강제. axis-text 페어링은 LLM 신뢰.",
                "items": {
                    "type": "object",
                    "properties": {
                        "axis": {
                            "type": "string",
                            "enum": ["accident_type", "hazardous_agent", "work_context", "ppe_state", "environmental"],
                        },
                        # Tier 3.A — text는 catalog code enum 강제 (Hybrid Day 3
                        # partial 효과 → 본격 schema-level enum). free-create 차단:
                        # MACHINERY / ELEVATED_WORK / STEEL_STRUCTURE 등 cooking 방지.
                        "text": (
                            {"type": "string", "enum": _ALL_CATALOG_CODES}
                            if _ALL_CATALOG_CODES
                            else {"type": "string"}
                        ),
                        "evidence": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["axis", "text", "evidence", "confidence"],
                    "additionalProperties": False,
                },
            },
            "overall_assessment": {"type": "string"},
            "immediate_actions": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "visual_observations",
            "visual_cues",
            "risk_feature_candidates",
            "overall_assessment",
            "immediate_actions",
        ],
        "additionalProperties": False,
    },
}


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=httpx.AsyncClient(trust_env=False),
        )
        self.model = "gpt-4.1"

    async def analyze_image(
        self,
        image_base64: str,
        workplace_type: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> dict:
        user_prompt = IMAGE_ANALYSIS_PROMPT.format(
            workplace_type=workplace_type or "unknown",
            additional_context=additional_context or "none",
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
            response_format={"type": "json_schema", "json_schema": ONTOLOGY_OBSERVATION_SCHEMA},
            max_tokens=4096,
        )
        return json.loads(response.choices[0].message.content or "{}")

    async def analyze_text(
        self,
        description: str,
        workplace_type: Optional[str] = None,
        industry_sector: Optional[str] = None,
    ) -> dict:
        user_prompt = TEXT_ANALYSIS_PROMPT.format(
            description=description,
            workplace_type=workplace_type or "unknown",
            industry_sector=industry_sector or "unknown",
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_schema", "json_schema": ONTOLOGY_OBSERVATION_SCHEMA},
            max_tokens=4096,
        )
        return json.loads(response.choices[0].message.content or "{}")

    async def validate_guide_relevance(
        self,
        *,
        visual_observations: list[str],
        visual_cues: list[str],
        industry_context: str,
        guide_code: str,
        guide_title: str,
        domain_family: str,
        required_context_terms: list[str],
        work_processes: list[str],
    ) -> dict:
        """Phase B.2 — 후보 Guide 도메인 적합성 LLM 검증.

        반환: {verdict: "accept|reject", reason: str, confidence: float}
        모델: env LLM_RERANK_MODEL (default gpt-5.4-mini).
        호출자(guide_recommendation_service)가 캐싱/배치 책임.
        """
        user_prompt = build_validator_user_prompt(
            visual_observations=visual_observations,
            visual_cues=visual_cues,
            industry_context=industry_context,
            guide_code=guide_code,
            guide_title=guide_title,
            domain_family=domain_family,
            required_context_terms=required_context_terms,
            work_processes=work_processes,
        )
        response = await self.client.chat.completions.create(
            model=RERANK_MODEL,
            messages=[
                {"role": "developer", "content": VALIDATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_schema", "json_schema": VALIDATOR_RESPONSE_SCHEMA},
            max_completion_tokens=512,
        )
        return json.loads(response.choices[0].message.content or "{}")


openai_client = OpenAIClient()
