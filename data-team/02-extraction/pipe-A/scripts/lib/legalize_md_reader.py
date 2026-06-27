"""legalize-kr .md 파서 — 편/장/절/관/조 계층에서 조문 추출 (의N 보존).

legalize-kr 업스트림이 JSON → Markdown으로 전환되어, 기존 legalize_reader.py
(JSON 전용)를 대체한다. 출력 구조는 legalize_reader.extract_articles()와 동일:
  {조문코드: {title, fullText, deleted, section, annotations, paragraphCount}}

- 조문코드는 `제N조` / `제N조의M` 모두 보존 (구 파이프라인의 의N 누락 버그 수정).
- section 포맷: '편N 이름 > 장N 이름 > 절N 이름 > 관N 이름' (gimulmul/signatures 호환).
- 중복 조문코드는 DuplicateArticleError로 즉시 실패 (silent overwrite 결함 차단).
- '부칙' 도달 시 본문 파싱 종료 (부칙 조문은 본문과 코드 충돌하므로 제외).
"""
import re
from pathlib import Path

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
SEC_RE = re.compile(r"^#{1,6}\s+제(\d+)(편|장|절|관)\b\s*(.*)$")
ART_RE = re.compile(r"^#{1,6}\s+(제\d+조(?:의\d+)?)\b(?:\s*\(([^)]*)\))?\s*(.*)$")
BUCHIK_RE = re.compile(r"^#{1,6}\s*부칙")
ORDER = ["편", "장", "절", "관"]


class DuplicateArticleError(Exception):
    """동일 법령 본문에서 조문코드가 중복될 때 (silent overwrite 방지)."""


def _clean(line: str) -> str:
    line = line.replace("**", "")
    line = re.sub(r"(\d)\\\.", r"\1.", line)  # markdown escaped "1\." -> "1."
    return line.strip()


def parse_law_md(text: str, law_id: str) -> dict:
    """법령 .md 텍스트 → {조문코드: article dict}."""
    result: dict[str, dict] = {}
    path = {"편": None, "장": None, "절": None, "관": None}
    state = {"cur": None, "body": [], "gae": [], "sin": None}

    def flush():
        cur = state["cur"]
        if cur is None:
            return
        raw = "\n".join(state["body"]).strip()
        deleted = raw.startswith("삭제")
        if deleted:
            full, pcount = "", 0
        else:
            full = raw
            pcount = sum(1 for ln in state["body"] if ln[:1] in CIRCLED)
            if pcount == 0 and full:
                pcount = 1
        result[cur]["fullText"] = full
        result[cur]["deleted"] = deleted
        result[cur]["paragraphCount"] = pcount
        result[cur]["annotations"] = {"개정": state["gae"], "신설": state["sin"]}
        state["cur"], state["body"], state["gae"], state["sin"] = None, [], [], None

    for line in text.splitlines():
        if BUCHIK_RE.match(line):          # 부칙 도달 → 본문 종료
            flush()
            break

        sec = SEC_RE.match(line)
        if sec:
            flush()
            num, typ, name = sec.group(1), sec.group(2), sec.group(3).strip()
            name = re.sub(r"\s*<[^>]*>\s*$", "", name).strip()
            path[typ] = f"{typ}{num} {name}".strip()
            for t in ORDER[ORDER.index(typ) + 1:]:
                path[t] = None
            continue

        art = ART_RE.match(line)
        if art:
            flush()
            code = art.group(1)
            title = (art.group(2) or "").strip()
            rest = art.group(3) or ""
            if code in result:
                raise DuplicateArticleError(f"[{law_id}] 중복 조문코드: {code}")
            section = " > ".join(path[t] for t in ORDER if path[t])
            result[code] = {"title": title, "section": section or None}
            state["cur"] = code
            for g in re.findall(r"<개정\s*([^>]+)>", rest):
                state["gae"].append(g.strip())
            continue

        if state["cur"] is not None:
            cl = _clean(line)
            if not cl:
                continue
            m_sin = re.search(r"\[본조신설\s*([^\]]+)\]", cl)
            if m_sin:
                state["sin"] = m_sin.group(1).strip()
            state["gae"].extend(g.strip() for g in re.findall(r"<개정\s*([^>]+)>", cl))
            cl2 = re.sub(r"<[^>]*>", "", cl)
            cl2 = re.sub(r"\[(본조신설|전문개정|제목개정)[^\]]*\]", "", cl2).strip()
            if cl2:
                state["body"].append(cl2)

    flush()
    return result


def parse_law_file(path: str | Path, law_id: str) -> dict:
    """법령 .md 파일 경로 → {조문코드: article dict}."""
    return parse_law_md(Path(path).read_text(encoding="utf-8"), law_id)


# 하위 호환: 기존 step0가 기대하는 시그니처(파싱된 데이터, law_id)와 다르므로
# 신규 step0_extract_articles_md.py에서 parse_law_file을 직접 사용한다.
