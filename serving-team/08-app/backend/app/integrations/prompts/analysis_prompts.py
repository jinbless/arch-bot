from app.integrations.prompts.prompt_builder import build_system_prompt

SYSTEM_PROMPT = build_system_prompt()

IMAGE_ANALYSIS_PROMPT = """Analyze the workplace image as an observation extractor.

Workplace type: {workplace_type}
Additional context: {additional_context}

Return only what is visible or strongly implied by visible evidence:
- visual_observations: factual observations (한국어로 작성)
- visual_cues: short matching cues such as missing guardrail, exposed cable, wet floor (한국어로 작성)
- risk_feature_candidates: candidate accident type, hazardous agent, or work context (영문 enum 코드 그대로: FALL, SCAFFOLD 등)

모든 user-facing 텍스트(observations, cues, descriptions)는 반드시 한국어로 작성. JSON 필드명과 enum 코드는 영어 유지.
Do not choose legal articles, penalties, KOSHA guide numbers, or final violations."""

TEXT_ANALYSIS_PROMPT = """Analyze the workplace description as an observation extractor.

Description: {description}
Workplace type: {workplace_type}
Industry sector: {industry_sector}

Return only observable facts and risk feature candidates:
- visual_observations (한국어로 작성)
- visual_cues (한국어로 작성)
- risk_feature_candidates (영문 enum 코드 그대로)

모든 user-facing 텍스트는 반드시 한국어로 작성. JSON 필드명과 enum 코드는 영어 유지.
Do not choose legal articles, penalties, KOSHA guide numbers, or final violations."""
