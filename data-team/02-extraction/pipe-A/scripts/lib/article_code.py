"""조문코드 정규화 유틸리티.

모든 조문코드를 `제N조` 또는 `제N조의M` 형식으로 정규화한다.
"""

import re

_SUFFIX_MAP = {
    "2": "B", "3": "C", "4": "D", "5": "E",
    "6": "F", "7": "G", "8": "H", "9": "I", "10": "J",
}


def normalize_article_code(번호: str) -> str:
    """legalize-kr의 조문 번호를 정규화된 조문코드로 변환.

    Args:
        번호: legalize-kr JSON의 조 번호 문자열 (예: "24", "332의2")

    Returns:
        정규화된 조문코드 (예: "제24조", "제332조의2")
    """
    번호 = 번호.strip()
    if "의" in 번호:
        base, suffix = 번호.split("의", 1)
        return f"제{base}조의{suffix}"
    return f"제{번호}조"


def article_code_to_ns_prefix(article_code: str, law_id: str) -> str:
    """조문코드를 NS 식별자 접두사로 변환.

    Args:
        article_code: 정규화된 조문코드 (예: "제24조", "제332조의2")
        law_id: 법령 ID (RULE, OSHA, SADA)

    Returns:
        NS 접두사 (예: "NS-RULE24", "NS-RULE332B")
    """
    m = re.match(r"^제(\d+)조(?:의(\d+))?$", article_code)
    if not m:
        raise ValueError(f"잘못된 조문코드 형식: {article_code}")
    num = m.group(1)
    suffix = m.group(2)
    if suffix:
        letter = _SUFFIX_MAP.get(suffix, chr(ord("A") + int(suffix) - 1))
        return f"NS-{law_id}{num}{letter}"
    return f"NS-{law_id}{num}"


def validate_article_code(code: str) -> bool:
    """조문코드 형식 검증."""
    return bool(re.match(r"^제\d+조(의\d+)?$", code))
