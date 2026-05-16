"""legalize-kr JSON 트리 순회 유틸리티.

legalize-kr의 계층 구조(편→장→절→관→조)를 재귀 순회하여
조문 데이터를 추출한다.
"""

import json
from pathlib import Path
from typing import Any

from .article_code import normalize_article_code


def load_law_json(path: str | Path) -> dict:
    """법령 JSON 파일 로드."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_full_text(항_list: list[dict]) -> str:
    """항/호/목 리스트로부터 전문 텍스트를 재구성."""
    lines = []
    for 항 in 항_list:
        번호 = 항["번호"]
        내용 = 항.get("내용", "")
        if 번호 == "0":
            lines.append(내용)
        else:
            lines.append(f"② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨ ⑩".split()[int(번호) - 1] if int(번호) <= 10 else f"({번호})")
            lines[-1] = f"{lines[-1]} {내용}" if 내용 else lines[-1]
            # Simpler: just use numbered prefix
            lines[-1] = f"({번호}) {내용}"

        for 호 in 항.get("호", []):
            호내용 = 호.get("내용", "")
            lines.append(f"  {호['번호']}. {호내용}")
            for 목 in 호.get("목", []):
                목내용 = 목.get("내용", "")
                lines.append(f"    {목['번호']}. {목내용}")

    return "\n".join(lines)


def _circled_number(n: int) -> str:
    """숫자를 원문자로 변환 (항 표기용)."""
    if 1 <= n <= 20:
        return chr(0x2460 + n - 1)  # ① ~ ⑳
    return f"({n})"


def _build_full_text_v2(항_list: list[dict]) -> str:
    """항/호/목 리스트로부터 전문 텍스트를 재구성 (개선판)."""
    lines = []
    for 항 in 항_list:
        번호 = 항["번호"]
        내용 = 항.get("내용", "")
        if 번호 == "0":
            prefix = ""
        else:
            prefix = f"{_circled_number(int(번호))} "
        lines.append(f"{prefix}{내용}")

        for 호 in 항.get("호", []):
            호내용 = 호.get("내용", "")
            lines.append(f"  {호['번호']}. {호내용}")
            for 목 in 호.get("목", []):
                목내용 = 목.get("내용", "")
                lines.append(f"    {목['번호']}. {목내용}")

    return "\n".join(lines)


def extract_articles(law_json: dict, law_id: str) -> dict[str, dict]:
    """법령 JSON에서 모든 조문을 추출.

    Args:
        law_json: legalize-kr JSON 데이터
        law_id: 법령 식별자 (RULE, OSHA, SADA)

    Returns:
        {조문코드: {title, fullText, deleted, section, annotations, paragraphCount}} 딕셔너리
    """
    result = {}

    def walk(nodes: list[dict], section_path: list[str]):
        for node in nodes:
            node_type = node.get("type", "")

            if node_type == "조":
                article_code = normalize_article_code(node["번호"])
                항_list = node.get("항", [])

                # 항 개수 계산 (번호 "0"은 단일 항, 빈 리스트는 삭제 조문)
                if len(항_list) == 0:
                    paragraph_count = 0
                elif len(항_list) == 1 and 항_list[0]["번호"] == "0":
                    paragraph_count = 1
                else:
                    paragraph_count = len(항_list)

                result[article_code] = {
                    "title": node.get("제목") or "",
                    "fullText": _build_full_text_v2(항_list),
                    "deleted": node.get("삭제", False),
                    "section": " > ".join(section_path) if section_path else None,
                    "annotations": node.get("annotations", {"개정": [], "신설": None}),
                    "paragraphCount": paragraph_count,
                }

            if node_type in ("편", "장", "절", "관"):
                label = f"{node_type}{node['번호']} {node.get('제목', '')}"
                walk(node.get("children", []), section_path + [label.strip()])
            elif node_type == "조":
                pass  # 조는 leaf, children 무시
            else:
                walk(node.get("children", []), section_path)

    walk(law_json.get("본문", []), [])
    return result
