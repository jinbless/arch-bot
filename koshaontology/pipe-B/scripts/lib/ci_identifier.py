"""5종 엔티티 식별자 생성 유틸리티.

LLM이 아닌 스크립트가 식별자를 결정론적으로 생성한다.

식별자 형식:
  CI: CI-{shortCode}-{NNN}   예: CI-DC13-001
  DT: DT-{shortCode}-{NNN}   예: DT-AG4-001
  WP: WP-{shortCode}-{NN}    예: WP-AG4-01
  ES: ES-{shortCode}-{NNN}   예: ES-AG4-001
  DR: DR-{shortCode}-{NNN}   예: DR-DC13-001
"""

import re

_ID_PATTERNS = {
    "CI": re.compile(r"^CI-[A-Z0-9]+-[0-9]+$"),
    "DT": re.compile(r"^DT-[A-Z0-9]+-[0-9]+$"),
    "WP": re.compile(r"^WP-[A-Z0-9]+-[0-9]+$"),
    "ES": re.compile(r"^ES-[A-Z0-9]+-[0-9]+$"),
    "DR": re.compile(r"^DR-[A-Z0-9]+-[0-9]+$"),
}


def generate_ci_id(short_code: str, seq: int) -> str:
    """CI 식별자 생성 (3자리 순번)."""
    return f"CI-{short_code}-{seq:03d}"


def generate_dt_id(short_code: str, seq: int) -> str:
    """DT 식별자 생성 (3자리 순번)."""
    return f"DT-{short_code}-{seq:03d}"


def generate_wp_id(short_code: str, seq: int) -> str:
    """WP 식별자 생성 (2자리 순번)."""
    return f"WP-{short_code}-{seq:02d}"


def generate_es_id(short_code: str, seq: int) -> str:
    """ES 식별자 생성 (3자리 순번)."""
    return f"ES-{short_code}-{seq:03d}"


def generate_dr_id(short_code: str, seq: int) -> str:
    """DR 식별자 생성 (3자리 순번)."""
    return f"DR-{short_code}-{seq:03d}"


def validate_entity_id(id_str: str, entity_type: str) -> bool:
    """엔티티 식별자 형식 검증.

    Args:
        id_str: 검증할 식별자 (예: "CI-DC13-001")
        entity_type: 엔티티 유형 (CI, DT, WP, ES, DR)

    Returns:
        True if valid
    """
    pattern = _ID_PATTERNS.get(entity_type)
    if not pattern:
        raise ValueError(f"알 수 없는 엔티티 유형: {entity_type}")
    return bool(pattern.match(id_str))
