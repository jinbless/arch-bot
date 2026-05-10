"""KOSHA 가이드코드 파싱 유틸리티.

PDF 파일명에서 guideCode, shortCode, title, domain을 추출한다.

파일명 패턴:
  - 표준(공백 구분): "A-G-4-2025 이동식 사다리의 사용에 관한 기술지원규정.pdf"
  - 구형(공백 구분): "C-103-2014 굴착공사 계측관리 기술지침.pdf"
  - 특수(숫자 시작): "3-65-2023 화학물질의 유해위험성 분류.pdf"
  - 밑줄 구분:     "E-182-2021_정전기에 의한 화재폭발...pdf"
  - 코드 내 공백:   "D-27- 2021 수소 저장설비...pdf"
  - 코드 내 공백:   "C - 73 - 2012.pdf"  (제목 없음)
  - 숫자ID 접두사:  "347896_P-79-2011.pdf"

shortCode 규칙: 가이드코드에서 하이픈과 연도(마지막 4자리)를 제거.
  A-G-4-2025  → AG4
  D-C-13-2026 → DC13
  C-103-2014  → C103
"""

import re
from pathlib import Path

# shortCode 유효성: 영문 대문자(또는 숫자) + 숫자/문자 조합, 2자 이상
_SHORT_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9]+$")

# 연도 패턴 (마지막 세그먼트)
_YEAR_RE = re.compile(r"-(\d{4})$")

# 숫자ID 접두사 패턴: "347896_P-79-2011.pdf"
_NUMERIC_PREFIX_RE = re.compile(r"^\d+_(.+)$")

# 가이드코드 패턴 (공백/밑줄 허용): 영숫자-세그먼트-...-연도4자리
# "E-182-2021", "D-27- 2021" (공백 포함), "C - 73 - 2012" (공백 포함)
_GUIDE_CODE_LOOSE_RE = re.compile(
    r"^([A-Z0-9][\s]*[-][\s]*[\w][\s]*(?:[-][\s]*[\w]+[\s]*)*[-][\s]*\d{4})"
)


def _normalize_guide_code(raw_code: str) -> str:
    """가이드코드 내 불필요한 공백 제거.

    "D-27- 2021" → "D-27-2021"
    "C - 73 - 2012" → "C-73-2012"
    """
    # 하이픈 주변 공백 제거
    code = re.sub(r"\s*-\s*", "-", raw_code.strip())
    return code


def parse_guide_filename(filename: str, domain: str) -> dict | None:
    """PDF 파일명에서 가이드 메타데이터를 추출.

    Args:
        filename: PDF 파일명 (예: "A-G-4-2025 이동식 사다리...pdf")
        domain: 소속 도메인 디렉토리명 (A/B/C/D/E)

    Returns:
        dict with guideCode, shortCode, title, domain, year
        또는 파싱 실패 시 None
    """
    name = filename
    if name.lower().endswith(".pdf"):
        name = name[:-4]

    # 패턴 1: 숫자ID 접두사 제거 ("347896_P-79-2011" → "P-79-2011")
    m = _NUMERIC_PREFIX_RE.match(name)
    if m:
        name = m.group(1)

    # 밑줄을 구분자로 사용한 경우: 첫 번째 밑줄 기준으로 코드와 제목 분리 시도
    # "E-182-2021_정전기에..." → code="E-182-2021", title="정전기에..."
    # 단, 밑줄만 있고 공백이 없는 경우에만 밑줄 분리 적용
    guide_code = None
    title = None

    # 전략: 가이드코드를 먼저 추출 → 나머지가 제목
    # 공백이 코드 내에 있을 수 있으므로, 정규식으로 코드 부분을 매칭

    # 먼저 공백 없는 표준 패턴 시도: "CODE TITLE" 또는 "CODE_TITLE"
    # 코드 부분에 공백이 없는 경우 (대부분)
    for delimiter in [" ", "_"]:
        if delimiter in name:
            idx = name.index(delimiter)
            candidate_code = name[:idx].strip()
            candidate_title = name[idx+1:].strip()

            # 밑줄이 제목 내에도 있을 수 있음 → 밑줄을 공백으로 변환
            if delimiter == "_" and candidate_title:
                candidate_title = candidate_title.replace("_", " ").strip()

            normalized = _normalize_guide_code(candidate_code)
            if _YEAR_RE.search(normalized):
                guide_code = normalized
                title = candidate_title
                break

    # 코드 내 공백 패턴: "D-27- 2021 수소..." 또는 "C - 73 - 2012"
    if guide_code is None:
        # 모든 공백을 제거하고 가이드코드 패턴 검색
        collapsed = name.replace(" ", "")
        # 가이드코드 패턴: 영숫자-세그먼트-연도
        m = re.match(r"^([A-Z0-9](?:[A-Z0-9]*-)*\d{4})(.*)", collapsed, re.IGNORECASE)
        if m:
            guide_code = m.group(1).upper()
            # 원본에서 제목 부분 추출: 연도 이후의 텍스트
            year_str = guide_code[-4:]
            year_pos = name.rfind(year_str)
            if year_pos >= 0:
                after_year = name[year_pos + 4:].strip()
                # 구분자 제거
                if after_year.startswith(("_", " ")):
                    after_year = after_year[1:].strip()
                title = after_year if after_year else None
            else:
                rest = m.group(2)
                title = rest.strip() if rest.strip() else None

    if guide_code is None:
        return None

    # 연도 추출
    year_match = _YEAR_RE.search(guide_code)
    if not year_match:
        return None
    year = int(year_match.group(1))

    # shortCode 생성
    short_code = guide_code_to_short_code(guide_code)
    if not short_code:
        return None

    # 제목이 없으면 가이드코드를 제목으로 사용 (예: "347896_P-79-2011.pdf")
    if not title:
        title = guide_code

    return {
        "guideCode": guide_code,
        "shortCode": short_code,
        "title": title,
        "domain": domain,
        "year": year,
    }


def guide_code_to_short_code(guide_code: str) -> str | None:
    """가이드코드 → shortCode 변환.

    하이픈과 마지막 연도(4자리)를 제거하고 대문자로 통일.

    Args:
        guide_code: 가이드코드 (예: "A-G-4-2025", "C-103-2014")

    Returns:
        shortCode (예: "AG4", "C103") 또는 실패 시 None
    """
    # 연도 제거
    code = _YEAR_RE.sub("", guide_code)
    # 하이픈 제거
    code = code.replace("-", "")
    # 공백 제거 후 대문자화
    code = code.strip().upper()

    if not code or len(code) < 2:
        return None
    return code


def validate_guide_code(code: str) -> bool:
    """가이드코드 형식 검증.

    패턴: 하이픈으로 구분된 세그먼트, 마지막은 4자리 연도.
    """
    return bool(_YEAR_RE.search(code)) and len(code) >= 6


def validate_short_code(code: str) -> bool:
    """shortCode 형식 검증."""
    return bool(_SHORT_CODE_RE.match(code))
