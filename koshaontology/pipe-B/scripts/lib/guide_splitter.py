"""Guide splitter — top-level 섹션 단위로만 분할 (절대 섹션 내부 분할 금지).

대형 가이드(>30K chars)를 Claude CLI 타임아웃 회피 위해 여러 part로 분할.
- 섹션 3 (용어의 정의)은 parts[1..]에 컨텍스트로 prepend
- DT는 Part 1에서만 추출
- 단일 섹션이 max 초과해도 분할 금지 (단독 part로 격리)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuidePart:
    """가이드 분할 part."""
    part_index: int                          # 1-based
    total_parts: int
    sections: list[dict]                     # 원본 parsed_doc["sections"] 부분집합 (top-level only)
    char_count: int                          # 실제 LLM에 들어갈 텍스트 길이 (section 3 포함)
    must_include_section_3: bool             # part_index >= 2이면 True (section3가 sections에 없을 때)
    section_numbers: list[str]               # 디버깅용 ex: ["4", "5", "6"]
    extract_dt: bool                         # part_index == 1이면 True


def _section_char_count(section: dict | None) -> int:
    """top-level 섹션 1개의 총 char count (subsections + tables 재귀)."""
    if section is None or not isinstance(section, dict):
        return 0
    n = len(section.get("text") or "")
    for t in section.get("tables", []) or []:
        if isinstance(t, dict):
            n += len((t.get("caption") or "")) + len((t.get("content") or ""))
    for sub in section.get("subsections", []) or []:
        n += _section_char_count(sub)
    # 헤더 prefix 오버헤드 (섹션 N + 제목 + 줄바꿈)
    n += 80
    return n


def _find_section_3(sections: list[dict]) -> dict | None:
    """'용어의 정의' 섹션 식별 (sectionTitle에 '용어' 포함)."""
    for s in sections:
        if not isinstance(s, dict):
            continue
        title = s.get("sectionTitle") or ""
        if "용어" in title:
            return s
    return None


def split_guide_by_sections(
    parsed_guide_doc: dict,
    max_chars: int = 25000,
    section3_as_context: bool = True,
) -> list[GuidePart]:
    """
    Top-level 섹션 단위로만 분할. 섹션 내부는 절대 자르지 않는다.

    Args:
        parsed_guide_doc: 파싱된 가이드 JSON dict
        max_chars: part당 목표 최대 char count
        section3_as_context: 섹션 3을 parts[1..]에 컨텍스트로 prepend할지

    Returns:
        list of GuidePart (최소 1개, 최대 N개)
    """
    sections = parsed_guide_doc.get("sections", [])
    if not sections:
        return []

    section3 = _find_section_3(sections)
    section3_size = _section_char_count(section3) if section3 else 0

    # 1. greedy section grouping (top-level only)
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_size = 0

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        size = _section_char_count(sec)

        # 단일 섹션이 max 초과 → 분할 금지, 단독 part로 격리
        if size > max_chars:
            if current:
                groups.append(current)
                current = []
                current_size = 0
            groups.append([sec])
            continue

        # parts[1..]는 섹션 3 컨텍스트도 포함하므로 budget 차감
        budget = max_chars
        is_first_group = len(groups) == 0
        if (not is_first_group) and section3_as_context and section3 and sec is not section3:
            budget = max(1000, max_chars - section3_size)

        if current_size + size > budget and current:
            groups.append(current)
            current = [sec]
            current_size = size
        else:
            current.append(sec)
            current_size += size

    if current:
        groups.append(current)

    # 2. GuidePart 변환
    total = len(groups)
    result = []
    for i, part_sections in enumerate(groups, start=1):
        char_count = sum(_section_char_count(s) for s in part_sections)
        # parts[1..]에서 섹션 3이 part_sections에 없으면 컨텍스트로 prepend
        must_inc = (
            i >= 2
            and section3_as_context
            and section3 is not None
            and section3 not in part_sections
        )
        if must_inc:
            char_count += section3_size

        result.append(GuidePart(
            part_index=i,
            total_parts=total,
            sections=part_sections,
            char_count=char_count,
            must_include_section_3=must_inc,
            section_numbers=[s.get("sectionNumber", "?") for s in part_sections],
            extract_dt=(i == 1),
        ))
    return result


def render_part_text(part: GuidePart, section3: dict | None) -> str:
    """GuidePart를 LLM 입력용 단일 문자열로 직렬화.
    must_include_section_3=True면 맨 앞에 [참조-읽기전용] 마커와 함께 section 3 prepend."""
    chunks = []
    if part.must_include_section_3 and section3 is not None:
        chunks.append(
            "[--- 참조용 (읽기 전용, 이 섹션에서는 어떤 엔티티도 추출하지 말 것) ---]\n"
            + _render_section(section3)
            + "\n[--- 참조용 끝 ---]\n"
        )
    for s in part.sections:
        chunks.append(_render_section(s))
    return "\n\n".join(chunks)


def _render_section(section: dict, depth: int = 0) -> str:
    """섹션을 텍스트로 직렬화 (step4_extract_entities.load_guide_text와 동일 포맷)."""
    if not isinstance(section, dict):
        return ""
    parts = []
    prefix = f"[섹션 {section.get('sectionNumber', '?')}] {section.get('sectionTitle', '')}\n"
    body = section.get("text", "") or ""
    parts.append(prefix + body)

    # 테이블 포함
    for t in section.get("tables", []) or []:
        if not isinstance(t, dict):
            continue
        tnum = t.get("tableNumber", "") or ""
        tcap = t.get("caption", "") or ""
        tcontent = t.get("content", "") or ""
        parts.append(f"[표 {tnum}] {tcap}\n{tcontent}")

    # 재귀: subsections
    for sub in section.get("subsections", []) or []:
        parts.append(_render_section(sub, depth + 1))

    return "\n\n".join(p for p in parts if p)
