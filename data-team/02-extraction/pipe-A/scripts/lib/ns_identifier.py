"""NS 식별자 알고리즘 생성.

LLM이 아닌 스크립트가 식별자를 결정론적으로 생성한다.
"""

from .article_code import article_code_to_ns_prefix


def generate_ns_id(law_id: str, article_code: str, seq: int) -> str:
    """NS 식별자를 알고리즘으로 생성.

    Args:
        law_id: 법령 ID (RULE, OSHA, SADA)
        article_code: 정규화된 조문코드 (예: "제24조")
        seq: 해당 조문 내 순번 (0부터)

    Returns:
        NS 식별자 (예: "NS-RULE24-0", "NS-RULE332B-1")
    """
    prefix = article_code_to_ns_prefix(article_code, law_id)
    return f"{prefix}-{seq}"
