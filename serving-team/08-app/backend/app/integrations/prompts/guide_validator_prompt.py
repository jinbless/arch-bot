"""Phase B.2 — LLM rerank prompt for domain-relevance verification.

이 prompt는 사진 관찰사실(visual_observations + visual_cues)과 candidate
KOSHA Guide 메타데이터(title, domain_family, work_processes)를 받아
"사진의 작업/현장 도메인이 이 Guide의 의도된 도메인과 일치하는가?" 만 판정한다.

법령/처벌 판단은 하지 않는다. 단지 "도메인 매칭" yes/no + 한국어 사유.

모델: gpt-5.4-mini (structured output)
응답 schema: {verdict: "accept"|"reject", reason: str (한국어), confidence: float}
"""
from __future__ import annotations


SYSTEM_PROMPT = """\
당신은 KOSHA 산업안전 Guide의 도메인 매칭 검증자입니다.
사진의 관찰사실과 후보 Guide의 도메인이 일치하는지만 판정합니다.

판정 원칙:
- 도메인이 명백히 다른 경우 reject (예: 식당 사진 vs 사장교 guide, 지게차 사진 vs 가공목재 적재 guide)
- 일부 키워드만 일치하고 산업/작업 맥락이 완전히 다른 경우 reject
- 동일 작업의 다른 측면을 다루는 경우 accept (예: 추락방호 guide vs 비계 사진)
- 일반적 위험 카테고리 guide (예: 일반 안전관리)는 대부분 accept

다음은 판정하지 마세요:
- 법령 적합성, 처벌 여부, 사고 결과
- Guide의 절대적 품질
- 사진의 위험 수준
"""

USER_PROMPT_TEMPLATE = """\
[사진 관찰사실]
{visual_observations}

[사진 시각 단서]
{visual_cues}

[추정 산업/현장]
{industry_context}

[후보 Guide]
- Guide code: {guide_code}
- 제목: {guide_title}
- 도메인 family: {domain_family}
- 핵심 용어: {required_context_terms}
- 주요 작업 절차: {work_processes}

위 사진의 도메인이 이 Guide의 의도된 도메인과 매칭되는가?
"""

RESPONSE_SCHEMA = {
    "name": "guide_relevance_verdict",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["accept", "reject"],
                "description": "사진과 Guide의 도메인 매칭 여부",
            },
            "reason": {
                "type": "string",
                "description": "한국어로 1-2문장 사유. reject 시 도메인 불일치 명시.",
            },
            "confidence": {
                "type": "number",
                "description": "0.0~1.0. reject 시 확신도가 높을수록 1에 가깝게.",
            },
        },
        "required": ["verdict", "reason", "confidence"],
        "additionalProperties": False,
    },
}


def build_user_prompt(
    *,
    visual_observations: list[str],
    visual_cues: list[str],
    industry_context: str,
    guide_code: str,
    guide_title: str,
    domain_family: str,
    required_context_terms: list[str],
    work_processes: list[str],
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        visual_observations="\n".join(f"- {o}" for o in (visual_observations or [])[:10])
        or "(없음)",
        visual_cues="\n".join(f"- {c}" for c in (visual_cues or [])[:15]) or "(없음)",
        industry_context=industry_context or "(미확정)",
        guide_code=guide_code,
        guide_title=guide_title or "(제목 없음)",
        domain_family=domain_family or "(미정)",
        required_context_terms=", ".join((required_context_terms or [])[:20]) or "(없음)",
        work_processes="\n".join(f"- {w}" for w in (work_processes or [])[:8]) or "(없음)",
    )
