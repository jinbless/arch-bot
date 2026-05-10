#!/usr/bin/env python3
"""P1-S2: Claude CLI 에이전트 기반 VLM PDF → 텍스트 JSON 파싱 오케스트레이터.

claude -p (print 모드)로 각 PDF를 독립 프로세스로 처리한다.
Claude Code의 Read 도구가 PDF를 시각적으로 읽으므로 이미지 변환 불필요.

대형 PDF(20p 초과)는 10페이지 청크로 물리 분할 후 청크별 독립 파싱 → 병합.

Usage:
    python3 step1_parse_pdf_vlm.py --guide C14 --model sonnet
    python3 step1_parse_pdf_vlm.py --domain D --model sonnet --max-guides 5
    python3 step1_parse_pdf_vlm.py --domain D --dry-run
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# -- 경로 설정 --
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.paths import (
    PROJECT_ROOT, SCHEMA_DIR, DATA_DIR, AGENTS_DIR,
    GUIDES_PDF, PARSED_DIR, PIPE_A_ROOT,
)

INVENTORY_PATH = DATA_DIR / "guide-inventory.json"
SCHEMA_PATH = SCHEMA_DIR / "guide-text-v2.schema.json"
AGENT_PROMPT_PATH = AGENTS_DIR / "step1-vlm-parse-prompt.md"
LOG_PATH = DATA_DIR / "vlm-parse-log.jsonl"
ERROR_PATH = DATA_DIR / "vlm-parse-errors.jsonl"

# -- 분할 모드 설정 --
SPLIT_THRESHOLD_PAGES = 20   # 이 페이지 수 초과 시 분할 모드
CHUNK_SIZE = 10              # 청크당 페이지 수
CHUNK_OVERLAP = 1            # 오버랩 페이지 수
CHUNK_MAX_RETRIES = 2        # 청크 JSON 파싱 실패 시 최대 재시도 횟수
SPLIT_CHUNKS_DIR = PARSED_DIR / ".split-chunks"

# -- Pipe-A schema_validator 동적 임포트 --
import importlib.util
_sv_path = PIPE_A_ROOT / "scripts" / "lib" / "schema_validator.py"
if _sv_path.exists():
    _spec = importlib.util.spec_from_file_location("schema_validator", _sv_path)
    _sv = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_sv)
    schema_validate = _sv.validate
else:
    # 폴백: jsonschema 직접 사용
    from jsonschema import validate as _jv, ValidationError
    def schema_validate(data, schema):
        try:
            _jv(data, schema)
            return []
        except ValidationError as e:
            return [str(e)]

DOMAIN_ORDER = ["D", "A", "B", "C", "E"]


# ═══════════════════════════════════════════════════════════════
# 유틸리티 함수
# ═══════════════════════════════════════════════════════════════

def load_inventory():
    """guide-inventory.json 로드."""
    raw = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "guides" in raw:
        return raw["guides"]
    return raw


def load_schema():
    """guide-text-v2.schema.json 로드."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_pdf_pages(pdf_path: Path) -> int:
    """PyMuPDF로 PDF 페이지 수 확인."""
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        pages = len(doc)
        doc.close()
        return pages
    except Exception:
        return 0


def filter_guides(inventory, domain=None, guide=None):
    """대상 가이드 필터링."""
    if guide:
        codes = [c.strip() for c in guide.split(",")]
        code_set = set(codes)
        return [g for g in inventory if g["shortCode"] in code_set]
    if domain:
        return [g for g in inventory if g["domain"] == domain]
    # 전체: 도메인 순서대로
    result = []
    for d in DOMAIN_ORDER:
        result.extend(g for g in inventory if g["domain"] == d)
    return result


def extract_json_from_output(raw: str) -> dict | None:
    """claude 출력에서 JSON 객체 추출.

    순서: 1) 전체를 JSON 파싱 시도
          2) 마크다운 펜스 제거 후 시도
          3) 첫 번째 { ... 마지막 } 추출 후 시도
    """
    text = raw.strip()
    if not text:
        return None

    # 1) 직접 파싱
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) 마크다운 펜스 제거
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3) 첫 { ~ 마지막 } 추출
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 4) JSON 문자열 내 이스케이프 안 된 큰따옴표 수정 시도
        #    "text": "...이하 "법"이라..." 같은 패턴을 처리
        try:
            fixed = _fix_unescaped_quotes(candidate)
            return json.loads(fixed)
        except (json.JSONDecodeError, Exception):
            pass

    return None


def _fix_unescaped_quotes(text: str) -> str:
    """JSON 문자열 값 내부의 이스케이프 안 된 큰따옴표를 수정.

    전략: JSON을 한 줄씩 처리하며, "key": "value" 패턴에서
    value 내부의 이스케이프 안 된 큰따옴표를 \\\"로 치환.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        # "text": "..." 패턴의 긴 문자열 값에서 발생
        # 키-값 패턴 매칭: "key": "value"
        m = re.match(r'^(\s*"(?:text|title|sectionTitle)"\s*:\s*)"(.*)"(\s*,?\s*)$', line, re.DOTALL)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            # value 내부의 이스케이프 안 된 큰따옴표를 수정
            # 이미 이스케이프된 것은 건드리지 않음
            fixed_value = re.sub(r'(?<!\\)"', '\\"', value)
            result.append(f'{prefix}"{fixed_value}"{suffix}')
        else:
            result.append(line)
    return "\n".join(result)


def post_process(data: dict, guide: dict, total_pages: int) -> dict:
    """메타데이터 강제 설정."""
    if "metadata" not in data:
        data["metadata"] = {}
    m = data["metadata"]
    m["guideCode"] = guide["guideCode"]
    m["shortCode"] = guide["shortCode"]
    m["title"] = guide["title"]
    m["totalPages"] = total_pages
    m["pdfPath"] = f"kosha-guides/{guide['pdfPath']}"
    m["parsedBy"] = "step2-text-extraction v2.0"

    # parsedAt: 없거나 잘못된 경우 현재 시각으로
    if not m.get("parsedAt"):
        m["parsedAt"] = datetime.now(timezone.utc).isoformat()

    # sections 기본 보장
    if "sections" not in data:
        data["sections"] = []

    # 재귀적으로 빈 배열 보장
    def ensure_arrays(section):
        section.setdefault("tables", [])
        section.setdefault("images", [])
        section.setdefault("text", "")
        for sub in section.get("subsections", []):
            ensure_arrays(sub)

    for sec in data.get("sections", []):
        ensure_arrays(sec)

    return data


def validate_output(data: dict, schema: dict) -> list:
    """스키마 검증, 에러 목록 반환."""
    try:
        from jsonschema import validate, ValidationError
        validate(data, schema)
        return []
    except ValidationError as e:
        return [e.message]
    except Exception as e:
        return [str(e)]


def append_log(entry: dict):
    """vlm-parse-log.jsonl에 한 줄 추가."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_error(entry: dict):
    """vlm-parse-errors.jsonl에 한 줄 추가."""
    ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ERROR_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# Claude CLI 호출
# ═══════════════════════════════════════════════════════════════

def run_claude_agent(user_prompt: str, model: str, timeout: int = 600) -> dict:
    """claude CLI를 subprocess로 실행, 결과 반환.

    Returns:
        {"ok": bool, "output": str, "duration_sec": float, "returncode": int}
    """
    system_prompt = AGENT_PROMPT_PATH.read_text(encoding="utf-8")

    cmd = [
        "claude", "-p",
        "--model", model,
        "--system-prompt", system_prompt,
        "--allowedTools", "Read",
        "--output-format", "text",
        "--permission-mode", "bypassPermissions",
        "--no-session-persistence",
        user_prompt,
    ]

    # Claude Code 중첩 세션 방지: 환경변수 제거
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_MAX_OUTPUT_TOKENS")}

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        duration = time.time() - t0
        return {
            "ok": result.returncode == 0,
            "output": result.stdout,
            "stderr": result.stderr,
            "duration_sec": round(duration, 1),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        duration = time.time() - t0
        return {
            "ok": False,
            "output": "",
            "stderr": f"TIMEOUT after {timeout}s",
            "duration_sec": round(duration, 1),
            "returncode": -1,
        }
    except Exception as e:
        duration = time.time() - t0
        return {
            "ok": False,
            "output": "",
            "stderr": str(e),
            "duration_sec": round(duration, 1),
            "returncode": -1,
        }


# ═══════════════════════════════════════════════════════════════
# 프롬프트 생성
# ═══════════════════════════════════════════════════════════════

def build_user_prompt(guide: dict, pdf_abs_path: str, total_pages: int) -> str:
    """단일 모드: claude CLI에 전달할 사용자 프롬프트 구성."""
    return (
        f"아래 KOSHA 가이드 PDF를 Read 도구로 읽고, "
        f"guide-text-v2 스키마에 맞는 JSON을 추출하라.\n\n"
        f"가이드 정보:\n"
        f"- guideCode: {guide['guideCode']}\n"
        f"- shortCode: {guide['shortCode']}\n"
        f"- title: {guide['title']}\n"
        f"- domain: {guide['domain']}\n"
        f"- totalPages: {total_pages}\n"
        f"- pdfPath: kosha-guides/{guide['pdfPath']}\n\n"
        f"PDF 파일 절대경로: {pdf_abs_path}\n\n"
        f"주의사항:\n"
        f"- Read 도구로 위 PDF 경로를 읽어라.\n"
        f"- 대용량 PDF는 pages 파라미터를 사용하여 분할 읽기하라 (예: pages=\"1-20\").\n"
        f"- JSON만 출력하라. 설명 텍스트, 마크다운 펜스 금지.\n"
        f"- parsedBy는 반드시 \"step2-text-extraction v2.0\"으로 설정.\n"
        f"- parsedAt은 현재 시각 ISO 8601 형식.\n"
    )


def build_chunk_prompt(
    guide: dict,
    chunk_abs_path: str,
    chunk_index: int,
    total_chunks: int,
    page_start: int,
    page_end: int,
    total_pages: int,
    prev_last_section: str | None = None,
) -> str:
    """청크 모드: 분할 PDF 청크용 프롬프트 구성."""
    is_first = chunk_index == 1
    is_continuation = chunk_index > 1

    continuation_note = ""
    if is_continuation:
        continuation_note = (
            f"- 이 청크의 첫 페이지(p{page_start})는 이전 청크와 겹치는 컨텍스트 페이지입니다. "
            f"이전 청크에서 이미 추출한 내용과 중복되지 않도록 주의하세요.\n"
        )
        if prev_last_section:
            continuation_note += (
                f"- 이전 청크의 마지막 섹션은 \"{prev_last_section}\"이었습니다. "
                f"해당 섹션이 이어진다면 동일한 sectionNumber로 시작하세요.\n"
            )

    toc_note = ""
    if is_first:
        toc_note = "- 이 청크에 목차가 있으면 tocSections를 작성하세요.\n"
    else:
        toc_note = "- tocSections는 빈 배열 []로 설정하세요 (첫 번째 청크에서만 추출).\n"

    return (
        f"아래 KOSHA 가이드 PDF 청크를 Read 도구로 읽고, "
        f"guide-text-v2 스키마에 맞는 JSON을 추출하라.\n\n"
        f"## 가이드 정보\n"
        f"- guideCode: {guide['guideCode']}\n"
        f"- shortCode: {guide['shortCode']}\n"
        f"- title: {guide['title']}\n"
        f"- domain: {guide['domain']}\n"
        f"- totalPages: {total_pages} (전체 가이드)\n"
        f"- pdfPath: kosha-guides/{guide['pdfPath']}\n\n"
        f"## 청크 정보\n"
        f"- 청크: {chunk_index}/{total_chunks}\n"
        f"- 이 청크 페이지 범위: 전체 가이드의 p{page_start}~p{page_end}\n"
        f"- 청크 PDF 절대경로: {chunk_abs_path}\n\n"
        f"## 주의사항\n"
        f"- Read 도구로 위 청크 PDF 경로를 읽어라.\n"
        f"{continuation_note}"
        f"{toc_note}"
        f"- 이 청크에 포함된 섹션만 추출하라.\n"
        f"- JSON만 출력하라. 설명 텍스트, 마크다운 펜스 금지.\n"
        f"- parsedBy는 반드시 \"step2-text-extraction v2.0\"으로 설정.\n"
        f"- parsedAt은 현재 시각 ISO 8601 형식.\n"
        f"- metadata.totalPages는 이 청크의 페이지 수가 아닌 전체 가이드 {total_pages}으로 설정.\n"
    )


# ═══════════════════════════════════════════════════════════════
# PDF 분할
# ═══════════════════════════════════════════════════════════════

@dataclass
class ChunkInfo:
    """PDF 청크 정보."""
    chunk_path: Path
    chunk_index: int       # 1-based
    total_chunks: int
    page_start: int        # 1-based (전체 PDF 기준)
    page_end: int          # 1-based (전체 PDF 기준)


def split_pdf_to_chunks(
    pdf_path: Path,
    short_code: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[ChunkInfo]:
    """PDF를 chunk_size 페이지 단위로 물리 분할.

    Args:
        pdf_path: 원본 PDF 경로
        short_code: 가이드 shortCode (임시 디렉토리명에 사용)
        chunk_size: 청크당 페이지 수
        overlap: 오버랩 페이지 수

    Returns:
        ChunkInfo 리스트
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    # 임시 디렉토리
    chunk_dir = SPLIT_CHUNKS_DIR / short_code
    chunk_dir.mkdir(parents=True, exist_ok=True)

    chunks = []
    page_idx = 0  # 0-based

    while page_idx < total_pages:
        chunk_start = page_idx  # 0-based
        chunk_end = min(page_idx + chunk_size, total_pages)  # exclusive, 0-based

        chunk_index = len(chunks) + 1
        chunk_path = chunk_dir / f"chunk-{chunk_index:03d}.pdf"

        # PDF가 이미 존재하면 재생성 생략
        if not chunk_path.exists():
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=chunk_start, to_page=chunk_end - 1)
            chunk_doc.save(str(chunk_path))
            chunk_doc.close()

        chunks.append(ChunkInfo(
            chunk_path=chunk_path,
            chunk_index=chunk_index,
            total_chunks=0,  # 나중에 설정
            page_start=chunk_start + 1,  # 1-based
            page_end=chunk_end,           # 1-based (inclusive)
        ))

        # 다음 청크 시작점: overlap만큼 뒤로
        page_idx = chunk_end - overlap
        # 남은 페이지가 overlap 이하면 마지막 청크에 포함시킴
        if total_pages - page_idx <= overlap:
            break

    doc.close()

    # total_chunks 설정
    total = len(chunks)
    for c in chunks:
        c.total_chunks = total

    return chunks


# ═══════════════════════════════════════════════════════════════
# 청크 결과 병합
# ═══════════════════════════════════════════════════════════════

def _merge_sections(all_sections: list[list[dict]]) -> list[dict]:
    """여러 청크의 sections 배열을 병합.

    동일 sectionNumber를 가진 인접 청크의 섹션은 text를 concat한다.
    """
    merged = []

    for chunk_sections in all_sections:
        for sec in chunk_sections:
            sec_num = sec.get("sectionNumber", "")

            # 마지막 병합된 섹션과 동일한 sectionNumber면 합침
            if merged and merged[-1].get("sectionNumber") == sec_num and sec_num:
                existing = merged[-1]
                # text 합침
                existing_text = existing.get("text", "")
                new_text = sec.get("text", "")
                if new_text and new_text not in existing_text:
                    existing["text"] = (existing_text + "\n" + new_text).strip()

                # tables 합침 (중복 제거: tableNumber 기준)
                existing_tables = existing.get("tables", [])
                existing_table_nums = {t.get("tableNumber") for t in existing_tables if t.get("tableNumber")}
                for t in sec.get("tables", []):
                    if t.get("tableNumber") and t["tableNumber"] in existing_table_nums:
                        continue
                    existing_tables.append(t)
                existing["tables"] = existing_tables

                # images 합침
                existing_images = existing.get("images", [])
                existing_image_nums = {im.get("imageNumber") for im in existing_images if im.get("imageNumber")}
                for im in sec.get("images", []):
                    if im.get("imageNumber") and im["imageNumber"] in existing_image_nums:
                        continue
                    existing_images.append(im)
                existing["images"] = existing_images

                # subsections 합침
                existing_subs = existing.get("subsections", [])
                existing_sub_nums = {s.get("sectionNumber") for s in existing_subs}
                for sub in sec.get("subsections", []):
                    sub_num = sub.get("sectionNumber", "")
                    if sub_num and sub_num in existing_sub_nums:
                        # 동일 subsection → text concat
                        for es in existing_subs:
                            if es.get("sectionNumber") == sub_num:
                                es_text = es.get("text", "")
                                sub_text = sub.get("text", "")
                                if sub_text and sub_text not in es_text:
                                    es["text"] = (es_text + "\n" + sub_text).strip()
                                break
                    else:
                        existing_subs.append(sub)
                existing["subsections"] = existing_subs
            else:
                merged.append(dict(sec))

    return merged


def merge_parsed_chunks(chunk_results: list[dict], guide: dict, total_pages: int) -> dict:
    """N개 청크 파싱 결과를 단일 guide-text-v2 JSON으로 병합."""
    # metadata: 첫 청크 기반
    merged = {
        "metadata": {
            "guideCode": guide["guideCode"],
            "shortCode": guide["shortCode"],
            "title": guide["title"],
            "totalPages": total_pages,
            "pdfPath": f"kosha-guides/{guide['pdfPath']}",
            "parsedBy": "step2-text-extraction v2.0",
            "parsedAt": datetime.now(timezone.utc).isoformat(),
            "tocSections": [],
        },
        "sections": [],
    }

    # tocSections: 모든 청크에서 수집, 중복 제거
    seen_toc = set()
    for chunk_data in chunk_results:
        for toc in chunk_data.get("metadata", {}).get("tocSections", []):
            toc_key = (toc.get("sectionNumber", ""), toc.get("title", ""))
            if toc_key not in seen_toc:
                seen_toc.add(toc_key)
                merged["metadata"]["tocSections"].append(toc)

    # sections 병합
    all_sections = [chunk_data.get("sections", []) for chunk_data in chunk_results]
    merged["sections"] = _merge_sections(all_sections)

    return merged


# ═══════════════════════════════════════════════════════════════
# 가이드 처리 (단일 / 청크)
# ═══════════════════════════════════════════════════════════════

def process_guide(guide: dict, model: str, schema: dict, force: bool) -> dict:
    """가이드 처리 분기: 페이지 수에 따라 단일/청크 모드 선택.

    Returns:
        {"shortCode", "status", "totalPages", "duration_sec", "errors"}
    """
    sc = guide["shortCode"]
    out_path = PARSED_DIR / f"guide-{sc}.json"

    # 스킵 체크
    if out_path.exists() and not force:
        return {"shortCode": sc, "status": "skip", "reason": "already parsed"}

    # PDF 존재 확인
    pdf_path = GUIDES_PDF / guide["pdfPath"]
    if not pdf_path.exists():
        err = f"PDF not found: {pdf_path}"
        append_error({"shortCode": sc, "error": err, "timestamp": datetime.now(timezone.utc).isoformat()})
        return {"shortCode": sc, "status": "error", "errors": [err]}

    total_pages = get_pdf_pages(pdf_path)
    if total_pages == 0:
        err = f"Cannot read PDF pages: {pdf_path}"
        append_error({"shortCode": sc, "error": err, "timestamp": datetime.now(timezone.utc).isoformat()})
        return {"shortCode": sc, "status": "error", "errors": [err]}

    # 분기: 대형 PDF는 청크 모드
    if total_pages > SPLIT_THRESHOLD_PAGES:
        return process_guide_chunked(guide, model, schema, pdf_path, total_pages)
    else:
        return process_guide_single(guide, model, schema, pdf_path, total_pages)


def process_guide_single(
    guide: dict, model: str, schema: dict, pdf_path: Path, total_pages: int
) -> dict:
    """단일 모드: 기존 로직 (20p 이하)."""
    sc = guide["shortCode"]
    out_path = PARSED_DIR / f"guide-{sc}.json"

    user_prompt = build_user_prompt(guide, str(pdf_path), total_pages)
    print(f"  [{sc}] Calling claude --model {model} ({total_pages}p)...", flush=True)

    agent_result = run_claude_agent(user_prompt, model, timeout=3600)

    if not agent_result["ok"]:
        err = f"claude exited with code {agent_result['returncode']}: {agent_result['stderr'][:500]}"
        append_error({
            "shortCode": sc, "model": model, "error": err,
            "duration_sec": agent_result["duration_sec"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "shortCode": sc, "status": "error",
            "duration_sec": agent_result["duration_sec"],
            "errors": [err],
        }

    # JSON 추출
    data = extract_json_from_output(agent_result["output"])
    if isinstance(data, list):
        dicts = [d for d in data if isinstance(d, dict)]
        data = dicts[0] if dicts else None
    if data is None:
        err = "Failed to extract JSON from claude output"
        append_error({
            "shortCode": sc, "model": model, "error": err,
            "output_preview": agent_result["output"][:2000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "shortCode": sc, "status": "error",
            "duration_sec": agent_result["duration_sec"],
            "errors": [err],
        }

    # 후처리
    data = post_process(data, guide, total_pages)

    # 스키마 검증
    errors = validate_output(data, schema)
    if errors:
        err_msg = f"Schema validation failed: {errors[0][:300]}"
        append_error({
            "shortCode": sc, "model": model, "error": err_msg,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "shortCode": sc, "status": "error",
            "duration_sec": agent_result["duration_sec"],
            "errors": errors,
        }

    # 저장
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 로그
    log_entry = {
        "shortCode": sc,
        "model": model,
        "status": "ok",
        "totalPages": total_pages,
        "duration_sec": agent_result["duration_sec"],
        "sections": len(data.get("sections", [])),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    append_log(log_entry)

    return {
        "shortCode": sc, "status": "ok",
        "totalPages": total_pages,
        "duration_sec": agent_result["duration_sec"],
        "sections": len(data.get("sections", [])),
    }


def process_guide_chunked(
    guide: dict, model: str, schema: dict, pdf_path: Path, total_pages: int
) -> dict:
    """청크 모드: 대형 PDF 분할 파싱 후 병합."""
    sc = guide["shortCode"]
    out_path = PARSED_DIR / f"guide-{sc}.json"
    chunk_dir = SPLIT_CHUNKS_DIR / sc

    print(f"  [{sc}] CHUNKED 모드 ({total_pages}p > {SPLIT_THRESHOLD_PAGES}p 임계값)", flush=True)

    # 1. PDF 물리 분할
    chunks = split_pdf_to_chunks(pdf_path, sc)
    print(f"  [{sc}] {len(chunks)}개 청크로 분할:", flush=True)
    for c in chunks:
        print(f"    chunk-{c.chunk_index:03d}: p{c.page_start}~p{c.page_end}", flush=True)

    # 2. 청크별 파싱
    chunk_results = []
    elapsed_total = 0.0
    prev_last_section = None

    for chunk in chunks:
        cache_path = chunk_dir / f"chunk-{chunk.chunk_index:03d}-result.json"

        # 캐시 확인
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                chunk_results.append(cached)
                # 이전 청크의 마지막 섹션 추적
                sections = cached.get("sections", [])
                if sections:
                    prev_last_section = sections[-1].get("sectionNumber")
                print(f"    chunk-{chunk.chunk_index:03d} 캐시 재사용 (skip)", flush=True)
                continue
            except (json.JSONDecodeError, OSError):
                pass  # 캐시 깨짐 → 재파싱

        # Claude 호출 (재시도 루프)
        prompt = build_chunk_prompt(
            guide=guide,
            chunk_abs_path=str(chunk.chunk_path),
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            total_pages=total_pages,
            prev_last_section=prev_last_section,
        )

        chunk_success = False
        for attempt in range(1, CHUNK_MAX_RETRIES + 1):
            attempt_label = f" (retry {attempt}/{CHUNK_MAX_RETRIES})" if attempt > 1 else ""
            print(f"    chunk-{chunk.chunk_index:03d} (p{chunk.page_start}~p{chunk.page_end}) 파싱 중...{attempt_label}",
                  end=" ", flush=True)

            agent_result = run_claude_agent(prompt, model, timeout=1200)
            elapsed_total += agent_result["duration_sec"]

            if not agent_result["ok"]:
                err = f"chunk-{chunk.chunk_index} claude error (attempt {attempt}): {agent_result['stderr'][:300]}"
                append_error({
                    "shortCode": sc, "model": model, "error": err,
                    "chunk": chunk.chunk_index, "attempt": attempt,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                print(f"ERROR", flush=True)
                if attempt < CHUNK_MAX_RETRIES:
                    print(f"    → 재시도 예정...", flush=True)
                    continue
                return {
                    "shortCode": sc, "status": "error",
                    "duration_sec": elapsed_total,
                    "errors": [err],
                }

            # JSON 추출
            data = extract_json_from_output(agent_result["output"])
            if isinstance(data, list):
                dicts = [d for d in data if isinstance(d, dict)]
                data = dicts[0] if dicts else None
            if data is None:
                err = f"chunk-{chunk.chunk_index} JSON parse failed (attempt {attempt})"
                # raw 응답 저장 (디버깅용)
                raw_path = chunk_dir / f"chunk-{chunk.chunk_index:03d}-raw.txt"
                raw_path.write_text(agent_result["output"][:50000], encoding="utf-8")
                append_error({
                    "shortCode": sc, "model": model, "error": err,
                    "chunk": chunk.chunk_index, "attempt": attempt,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                print(f"FAIL (raw → {raw_path.name})", flush=True)
                if attempt < CHUNK_MAX_RETRIES:
                    print(f"    → 재시도 예정...", flush=True)
                    continue
                return {
                    "shortCode": sc, "status": "error",
                    "duration_sec": elapsed_total,
                    "errors": [err],
                }

            # 성공
            chunk_success = True
            break

        # 캐시 저장
        cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        chunk_results.append(data)

        # 이전 청크의 마지막 섹션 추적
        sections = data.get("sections", [])
        if sections:
            prev_last_section = sections[-1].get("sectionNumber")

        n_sections = len(sections)
        print(f"({agent_result['duration_sec']}s, {n_sections} sections)", flush=True)

    # 3. 병합
    merged = merge_parsed_chunks(chunk_results, guide, total_pages)

    # 4. 후처리 + 스키마 검증
    merged = post_process(merged, guide, total_pages)
    errors = validate_output(merged, schema)

    if errors:
        # 스키마 에러가 있어도 저장 (soft fail — 수동 수정 가능)
        print(f"  [{sc}] WARN: 스키마 에러 {len(errors)}건 (저장은 진행)", flush=True)
        append_error({
            "shortCode": sc, "model": model,
            "error": f"Schema validation after merge: {errors[0][:300]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # 5. 최종 저장
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 6. 성공 시 임시 chunk PDF 정리 (결과 JSON 캐시는 유지)
    if not errors:
        for c in chunks:
            if c.chunk_path.exists():
                c.chunk_path.unlink()

    # 로그
    log_entry = {
        "shortCode": sc,
        "model": model,
        "status": "ok",
        "mode": "chunked",
        "totalPages": total_pages,
        "chunks": len(chunks),
        "duration_sec": elapsed_total,
        "sections": len(merged.get("sections", [])),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    append_log(log_entry)

    status = "ok" if not errors else "warn"
    return {
        "shortCode": sc, "status": status,
        "totalPages": total_pages,
        "duration_sec": elapsed_total,
        "sections": len(merged.get("sections", [])),
        "chunks": len(chunks),
        "schemaErrors": len(errors),
    }


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="VLM 기반 KOSHA 가이드 PDF 파서 (claude CLI 에이전트)"
    )
    parser.add_argument("--domain", choices=["A", "B", "C", "D", "E"],
                        help="도메인 전체 처리")
    parser.add_argument("--guide", type=str,
                        help="특정 가이드 shortCode 처리 (예: C14)")
    parser.add_argument("--model", choices=["sonnet", "opus"], default="sonnet",
                        help="Claude 모델 (기본: sonnet)")
    parser.add_argument("--dry-run", action="store_true",
                        help="처리 대상만 출력, API 호출 없음")
    parser.add_argument("--force", action="store_true",
                        help="기존 파싱 결과 덮어쓰기")
    parser.add_argument("--max-guides", type=int,
                        help="처리할 최대 가이드 수")

    args = parser.parse_args()

    if not args.domain and not args.guide:
        parser.error("--domain 또는 --guide 중 하나를 지정하세요")

    # 의존성 확인
    if not AGENT_PROMPT_PATH.exists():
        print(f"ERROR: Agent prompt not found: {AGENT_PROMPT_PATH}", file=sys.stderr)
        sys.exit(1)
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)

    # 데이터 로드
    inventory = load_inventory()
    schema = load_schema()
    guides = filter_guides(inventory, args.domain, args.guide)

    if args.max_guides:
        guides = guides[:args.max_guides]

    if not guides:
        print("처리할 가이드가 없습니다.")
        return

    print(f"=== VLM PDF Parser ===")
    print(f"Model: {args.model}")
    print(f"대상: {len(guides)}개 가이드")
    print(f"분할 임계값: {SPLIT_THRESHOLD_PAGES}p (초과 시 {CHUNK_SIZE}p 청크)")
    print()

    if args.dry_run:
        for g in guides:
            pdf_path = GUIDES_PDF / g["pdfPath"]
            exists = "OK" if pdf_path.exists() else "MISSING"
            parsed = "PARSED" if (PARSED_DIR / f"guide-{g['shortCode']}.json").exists() else "NEW"
            pages = get_pdf_pages(pdf_path) if pdf_path.exists() else 0
            mode = "CHUNK" if pages > SPLIT_THRESHOLD_PAGES else "SINGLE"
            print(f"  [{g['shortCode']:8s}] {pages:3d}p  {exists:7s}  {parsed:6s}  {mode:6s}  {g['title'][:45]}")
        return

    # 처리 루프
    ok_count = 0
    err_count = 0
    skip_count = 0
    warn_count = 0

    for i, g in enumerate(guides, 1):
        print(f"[{i}/{len(guides)}] {g['shortCode']} — {g['title'][:40]}")
        result = process_guide(g, args.model, schema, args.force)

        if result["status"] == "ok":
            ok_count += 1
            chunks_info = f", {result['chunks']} chunks" if result.get("chunks") else ""
            print(f"  OK ({result['duration_sec']}s, {result['sections']} sections{chunks_info})")
        elif result["status"] == "warn":
            warn_count += 1
            print(f"  WARN ({result['duration_sec']}s, {result['sections']} sections, {result['schemaErrors']} schema errors)")
        elif result["status"] == "skip":
            skip_count += 1
            print(f"  SKIP ({result.get('reason', '')})")
        else:
            err_count += 1
            print(f"  ERROR: {result.get('errors', ['unknown'])[0][:100]}")
        print()

    # 요약
    print(f"=== 완료 ===")
    print(f"  OK: {ok_count}  WARN: {warn_count}  SKIP: {skip_count}  ERROR: {err_count}")
    print(f"  로그: {LOG_PATH}")
    if err_count > 0:
        print(f"  에러: {ERROR_PATH}")


if __name__ == "__main__":
    main()
