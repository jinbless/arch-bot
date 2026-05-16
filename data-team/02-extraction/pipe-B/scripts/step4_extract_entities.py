#!/usr/bin/env python3
"""P2-Step 4: CI/DT/WP/ES/DR 엔티티 추출 실행.

Claude CLI를 사용하여 가이드 텍스트에서 5종 엔티티를 추출한다.

Usage:
    # 파일럿 가이드 전체 실행
    python3 scripts/step4_extract_entities.py --guides-file data/pilot-guides.json

    # 단일 배치 실행
    python3 scripts/step4_extract_entities.py --batch data/ci-batches/pipeb-pilot-A-001-input.json

    # 단일 가이드 실행
    python3 scripts/step4_extract_entities.py --guide AG10

    # 이미 추출된 가이드 건너뛰기 (기본 동작)
    python3 scripts/step4_extract_entities.py --guides-file data/pilot-guides.json --skip-existing
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── 경로 설정 ──
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, BATCHES_DIR, PARSED_DIR, SCHEMA_DIR, REPO_ROOT
from lib.guide_splitter import split_guide_by_sections, render_part_text, GuidePart, _find_section_3
from lib.ci_merger import merge_ci_parts

CI_OUTPUT_DIR = DATA_DIR / "ci-output"
SPLIT_TEMP_DIR = CI_OUTPUT_DIR / ".split-parts"
AGENT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "agents" / "step4-entity-extraction.md"
CI_SCHEMA_PATH = SCHEMA_DIR / "ci-file.schema.json"

MODEL = "opus"  # claude CLI model

# 분할 모드 임계값
SPLIT_THRESHOLD_CHARS = 15000   # 이상이면 split 모드 진입
SPLIT_TARGET_CHARS = 6000       # part당 목표 max (T16 등 대형 가이드 대응)


def load_guide_doc(short_code: str) -> dict | None:
    """파싱된 가이드 JSON dict를 로드 (split 분기 결정용)."""
    parsed_path = PARSED_DIR / f"guide-{short_code}.json"
    if not parsed_path.exists():
        return None
    try:
        return json.loads(parsed_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_guide_text(short_code: str) -> str:
    """파싱된 가이드 텍스트를 로드하여 단일 텍스트로 합침."""
    parsed_path = PARSED_DIR / f"guide-{short_code}.json"
    if not parsed_path.exists():
        return ""

    try:
        doc = json.loads(parsed_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ""
    texts = []

    def extract_text(section, depth=0):
        prefix = f"[섹션 {section.get('sectionNumber', '?')}] {section.get('sectionTitle', '')}\n"
        body = section.get("text", "")
        texts.append(prefix + body)

        # 테이블 포함
        for t in section.get("tables", []):
            tnum = t.get("tableNumber", "")
            tcap = t.get("caption", "")
            tcontent = t.get("content", "")
            texts.append(f"[표 {tnum}] {tcap}\n{tcontent}")

        # 재귀: subsections
        for sub in section.get("subsections", []):
            extract_text(sub, depth + 1)

    for s in doc.get("sections", []):
        extract_text(s)

    return "\n\n".join(texts)


def build_extraction_prompt(
    guide_entry: dict,
    guide_text: str,
    batch_id: str | None = None,
    part_info: dict | None = None,
) -> str:
    """엔티티 추출용 프롬프트 생성. part_info가 있으면 분할 모드 컨텍스트 추가."""
    sc = guide_entry["shortCode"]
    gc = guide_entry["guideCode"]
    domain = guide_entry.get("domain", "?")
    title = guide_entry.get("title", "")
    cited = guide_entry.get("citedArticles", [])
    candidates = guide_entry.get("candidateSR", [])
    id_range = guide_entry.get("preAssignedIdRange", {})

    # 에이전트 프롬프트 로드
    agent_prompt = AGENT_PROMPT_PATH.read_text(encoding="utf-8")

    # candidateSR 목록 포맷
    sr_list = "\n".join(
        f"  - {sr['id']}: {sr['title']}" for sr in candidates
    )

    # 분할 모드 컨텍스트 절
    part_section = ""
    id_ranges_text = f"""### preAssignedIdRange
- CI: {id_range.get('start', f'CI-{sc}-001')} ~ {id_range.get('end', f'CI-{sc}-200')}
- DT: DT-{sc}-001 ~ DT-{sc}-100
- WP: WP-{sc}-01 ~ WP-{sc}-50
- ES: ES-{sc}-001 ~ ES-{sc}-100
- DR: DR-{sc}-001 ~ DR-{sc}-050"""

    if part_info:
        secs = ", ".join(part_info["section_numbers"])
        ir = part_info["id_ranges"]
        dt_line = (f"- DT: {ir['DT']['start']} ~ {ir['DT']['end']}"
                   if ir.get("DT") else "- DT: **추출 금지** (Part 1에서 처리됨, 빈 배열 [] 반환)")
        part_section = f"""## 분할 추출 컨텍스트 (Split Mode)

이 가이드는 크기가 커서 {part_info['total_parts']}개 부분으로 나누어 처리됩니다.

- **현재 Part**: {part_info['part_index']} / {part_info['total_parts']}
- **이 Part의 포함 섹션**: {secs}
- **DT 추출**: {'허용 (이 Part에서 추출)' if part_info['extract_dt'] else '금지 (Part 1에서 처리됨)'}
- **참조용 섹션 3 (용어의 정의) 첨부**: {'예 (DT 추출 금지)' if part_info['must_include_section_3'] else '아니오'}

### 분할 추출 절대 규칙
1. 위 "포함 섹션" 목록의 섹션에서만 엔티티를 추출한다.
2. 참조용으로 첨부된 섹션 3에서는 어떤 엔티티도 추출하지 말 것 (DT 포함).
3. DT는 Part 1에서만 추출. Part 2+ 는 `domainTerms: []` 빈 배열 반환.
4. processOrder는 이 Part 내에서 1부터 시작 (병합 시 글로벌 재정렬됨).
5. sourceSection은 반드시 "포함 섹션" 중 하나여야 함.
6. ID 범위를 벗어나면 검증에서 탈락된다.

"""
        id_ranges_text = f"""### preAssignedIdRange (Part {part_info['part_index']}/{part_info['total_parts']} 한정)
- CI: {ir['CI']['start']} ~ {ir['CI']['end']}
{dt_line}
- WP: {ir['WP']['start']} ~ {ir['WP']['end']}
- ES: {ir['ES']['start']} ~ {ir['ES']['end']}
- DR: {ir['DR']['start']} ~ {ir['DR']['end']}"""

    prompt = f"""당신은 KOSHA 산업안전 가이드에서 5종 엔티티(CI/DT/WP/ES/DR)를 추출하는 전문가입니다.

## 에이전트 지침

{agent_prompt}

{part_section}## 입력 정보

- **가이드코드**: {gc}
- **shortCode**: {sc}
- **도메인**: {domain}
- **제목**: {title}
- **인용 조문**: {json.dumps(cited, ensure_ascii=False)}
- **배치 ID**: {batch_id or "pilot-manual"}

{id_ranges_text}

### candidateSR (basedOn에서 선택 가능한 SR 목록)
{sr_list}

### 가이드 원문 텍스트

{guide_text}

## 출력 지시

위 가이드 텍스트에서 5종 엔티티를 추출하여 아래 JSON 형식으로 출력하세요.

### 절대 준수 출력 규칙
1. 반드시 ```json ... ``` 코드블록 안에 **완전하고 유효한 JSON 객체**를 출력하세요.
2. JSON은 반드시 최상위 `{{` 로 시작하고 `}}` 로 끝나야 합니다.
3. **절대 금지**: 이전 Part의 이어쓰기 형태로 배열 원소부터 시작하는 출력. 매 Part마다 독립적인 완전한 JSON 객체를 출력하세요.
4. 다른 설명 텍스트는 JSON 코드블록 **밖에** 작성하세요.
5. 코드블록 안에는 JSON 외의 텍스트(예: "Continuing from ...", 요약 등)를 포함하지 마세요.
6. **절대 금지**: Python 스크립트 생성, Write 도구 사용, 파일 저장 시도 등 우회 방법. 출력이 크더라도 반드시 JSON 텍스트를 직접 출력하세요.

출력 JSON 구조:
{{
  "metadata": {{
    "guideCode": "{gc}",
    "shortCode": "{sc}",
    "domain": "{domain}",
    "extractedAt": "(ISO 8601 현재시각)",
    "extractedBy": "claude-sonnet-pilot",
    "batchId": "{batch_id or 'pilot-manual'}"
  }},
  "checklistItems": [...],
  "domainTerms": [...],
  "workProcesses": [...],
  "equipmentSpecs": [...],
  "documentRequirements": [...]
}}
"""
    return prompt


def extract_json_from_response(response: str) -> dict | None:
    """Claude 응답에서 JSON 코드블록을 추출.

    복구 전략:
    1. ```json ... ``` 코드블록에서 완전한 JSON 추출
    2. 코드블록 없이 순수 JSON인 경우
    3. 코드블록 내 JSON이 checklistItems 래퍼 없이 배열 원소부터 시작하는 경우 래핑 복구
    """
    REQUIRED_KEYS = {"checklistItems", "domainTerms", "workProcesses",
                     "equipmentSpecs", "documentRequirements"}

    def _is_valid_ci_output(data: dict) -> bool:
        """최소한 checklistItems 키가 있는 dict인지 확인."""
        return isinstance(data, dict) and "checklistItems" in data

    # ── 1) ```json ... ``` 코드블록 추출 ──
    pattern = r"```json\s*\n?(.*?)\n?\s*```"
    matches = re.findall(pattern, response, re.DOTALL)

    if matches:
        # 가장 큰 JSON 블록 선택
        for match in sorted(matches, key=len, reverse=True):
            try:
                data = json.loads(match)
                if _is_valid_ci_output(data):
                    return data
            except json.JSONDecodeError:
                continue

        # ── 3) 래핑 복구: checklistItems 배열 원소부터 시작하는 경우 ──
        for match in sorted(matches, key=len, reverse=True):
            block = match.strip()
            # 시도: {"checklistItems": [ + block 으로 래핑
            wrapped = '{"checklistItems": [\n' + block
            try:
                data = json.loads(wrapped)
                if _is_valid_ci_output(data):
                    print("[RECOVERY] checklistItems 래퍼 복구 성공", end=" ", flush=True)
                    return data
            except json.JSONDecodeError:
                pass

    # ── 2) 코드블록 없이 순수 JSON인 경우 ──
    try:
        data = json.loads(response)
        if _is_valid_ci_output(data):
            return data
    except json.JSONDecodeError:
        pass

    return None


def validate_ci_output(data: dict) -> list[str]:
    """ci-file.schema.json으로 검증. 에러 목록 반환."""
    try:
        from jsonschema import validate, ValidationError, Draft202012Validator
    except ImportError:
        # jsonschema 없으면 기본 검증만
        errors = []
        if "checklistItems" not in data:
            errors.append("checklistItems 누락")
        if "domainTerms" not in data:
            errors.append("domainTerms 누락")
        return errors

    schema = json.loads(CI_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in validator.iter_errors(data):
        path = ".".join(str(p) for p in err.absolute_path)
        errors.append(f"[{path}] {err.message}")
    return errors


class RateLimitError(Exception):
    """API rate limit / token limit 초과 시 배치 즉시 중단용."""
    pass


# rate limit / token limit 감지 패턴
_RATE_LIMIT_PATTERNS = [
    "rate limit", "rate_limit", "too many requests", "429",
    "token limit", "token_limit", "quota", "exceeded",
    "overloaded", "capacity", "billing", "credit",
]


def _is_rate_limit_error(error_msg: str) -> bool:
    """에러 메시지에 rate limit / token limit 관련 키워드가 있는지 확인."""
    lower = error_msg.lower()
    return any(pat in lower for pat in _RATE_LIMIT_PATTERNS)


def run_claude_extraction(prompt: str, text_chars: int = 0, max_retries: int = 0) -> str:
    """Claude CLI를 호출하여 추출 수행. 적응형 타임아웃 + 리트라이.

    Rate limit/token limit 에러 감지 시 RateLimitError를 발생시켜
    배치 전체를 즉시 중단한다 (토큰 낭비 방지).
    """
    import tempfile

    # 적응형 타임아웃: 문자수 비례 (600s~3600s)
    timeout = max(1800, min(3600, text_chars // 50)) if text_chars > 0 else 1800

    # 프롬프트를 임시 파일에 저장 (CLI 인자 길이 제한 회피)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        # 중첩 세션 감지 환경변수만 제거 (CLAUDE_CONFIG_DIR은 로그인 정보에 필요하므로 유지)
        env = os.environ.copy()
        for key in ["CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_MAX_OUTPUT_TOKENS"]:
            env.pop(key, None)

        _RL_WAITS = [7200, 3600, 3600, 3600]  # rate limit 대기: 2h, 1h, 1h, 1h
        _MAX_ATTEMPTS = max(max_retries + 1, len(_RL_WAITS) + 1)  # rate limit 재시도까지 포함
        last_error = None
        rl_count = 0  # rate limit 재시도 횟수
        timeout_count = 0  # timeout 재시도 횟수
        for attempt in range(_MAX_ATTEMPTS):
            try:
                # stdin 파이프로 프롬프트 전달
                with open(prompt_file, "r", encoding="utf-8") as pf:
                    result = subprocess.run(
                        ["claude", "-p", "--model", MODEL, "--output-format", "text"],
                        stdin=pf,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        env=env,
                        cwd=str(Path(__file__).resolve().parent.parent.parent),  # koshaontology/
                    )

                if result.returncode != 0:
                    err_msg = result.stderr.strip()
                    # rate limit 감지 → 리트라이 없이 즉시 중단
                    if _is_rate_limit_error(err_msg):
                        raise RateLimitError(f"API limit detected, aborting batch: {err_msg[:500]}")
                    raise RuntimeError(f"Claude CLI error (rc={result.returncode}): {err_msg[:1000]}")

                return result.stdout

            except RateLimitError as e:
                last_error = e
                if rl_count < len(_RL_WAITS):
                    wait = _RL_WAITS[rl_count]
                    wait_min = wait // 60
                    print(f"\n  ⏳ Rate limit 감지. {wait_min}분 대기 후 재시도 ({rl_count+1}/{len(_RL_WAITS)})...", flush=True)
                    rl_count += 1
                    time.sleep(wait)
                    continue
                raise last_error

            except (subprocess.TimeoutExpired, RuntimeError) as e:
                last_error = e
                if timeout_count < max_retries:
                    timeout_count += 1
                    wait = timeout_count * 30  # 30s, 60s 대기
                    print(f"RETRY({timeout_count}/{max_retries}, {wait}s)...", end=" ", flush=True)
                    time.sleep(wait)
                    continue
                raise last_error
    finally:
        try:
            os.unlink(prompt_file)
        except OSError:
            pass


def _apply_post_processing(data: dict, candidate_srs: set | None = None) -> None:
    """추출 결과 후처리 (relatedSR 정규화, requirementType 보정, MANDATORY 다운그레이드).

    candidate_srs가 주어지면 basedOn/relatedSR에서 candidateSR 밖의 SR을 자동 제거.
    """
    # 5개 배열 키 보장
    for key in ["checklistItems", "domainTerms", "workProcesses", "equipmentSpecs", "documentRequirements"]:
        if key not in data:
            data[key] = []

    # relatedSR / basedOn 후처리: 단일 문자열/콤마 구분 → 배열로 변환
    for items_key in ["checklistItems", "domainTerms", "workProcesses", "equipmentSpecs", "documentRequirements"]:
        sr_field = "basedOn" if items_key == "checklistItems" else "relatedSR"
        for item in data.get(items_key, []):
            val = item.get(sr_field)
            if isinstance(val, str):
                if "," in val:
                    item[sr_field] = [s.strip() for s in val.split(",") if s.strip()]
                else:
                    item[sr_field] = [val] if val else None

    # candidateSR 밖의 SR 자동 제거 (검증 사전 통과)
    if candidate_srs:
        for items_key in ["checklistItems", "domainTerms", "workProcesses", "equipmentSpecs", "documentRequirements"]:
            sr_field = "basedOn" if items_key == "checklistItems" else "relatedSR"
            for item in data.get(items_key, []):
                val = item.get(sr_field)
                if isinstance(val, list):
                    filtered = [s for s in val if s in candidate_srs]
                    item[sr_field] = filtered if filtered else None

    # requirementType 후처리: 유효하지 않은 값 → null 또는 매핑
    VALID_REQ_TYPES = {
        "PHYSICAL_PROTECTION", "PPE_REQUIREMENT", "PROCEDURAL",
        "TRAINING", "EQUIPMENT_STANDARD", "ENVIRONMENTAL",
        "MANAGEMENT_SYSTEM", "EMERGENCY_RESPONSE",
    }
    REQ_TYPE_MAP = {
        "INSPECTION_REQUIREMENT": "PROCEDURAL",
        "INSPECTION": "PROCEDURAL",
        "SAFETY_INSPECTION": "PROCEDURAL",
        "DOCUMENTATION": "MANAGEMENT_SYSTEM",
        "DOCUMENTATION_REQUIREMENT": "MANAGEMENT_SYSTEM",
        "MAINTENANCE": "EQUIPMENT_STANDARD",
        "HAZARD_PREVENTION": "PHYSICAL_PROTECTION",
        "WORK_PROCEDURE": "PROCEDURAL",
    }
    for ci in data.get("checklistItems", []):
        rt = ci.get("requirementType")
        if rt and rt not in VALID_REQ_TYPES:
            ci["requirementType"] = REQ_TYPE_MAP.get(rt)

    # requirementType null → 키워드 자동 분류 보충
    _RT_KEYWORDS = {
        "PPE_REQUIREMENT": ["안전모", "보호구", "안전대", "안전화", "보안경", "방진마스크", "귀마개"],
        "PROCEDURAL": ["점검", "확인", "검사", "조사", "측정", "감시"],
        "TRAINING": ["교육", "훈련", "자격", "면허", "숙지"],
        "ENVIRONMENTAL": ["환기", "조명", "온도", "습도", "소음", "분진"],
        "MANAGEMENT_SYSTEM": ["작업계획서", "안전관리", "관리감독", "위험성평가"],
        "EMERGENCY_RESPONSE": ["비상", "응급", "대피", "경보", "소화"],
        "EQUIPMENT_STANDARD": ["규격", "KS", "내하중", "사용하중"],
        "PHYSICAL_PROTECTION": ["방호", "난간", "덮개", "방호울", "방지망"],
    }
    for ci in data.get("checklistItems", []):
        if ci.get("requirementType") is None:
            ci_text = ci.get("text", "")
            for rt_type, keywords in _RT_KEYWORDS.items():
                if any(kw in ci_text for kw in keywords):
                    ci["requirementType"] = rt_type
                    break

    # DR documentType 보정: 유효하지 않은 값 → WORK_PLAN 또는 제거
    VALID_DOC_TYPES = {"WORK_PLAN", "RISK_ASSESSMENT", "SAFETY_CHECKLIST", "MSDS", "INCIDENT_REPORT", "TRAINING_RECORD"}
    DOC_TYPE_MAP = {
        "EMERGENCY_RESPONSE": "WORK_PLAN",
        "EMERGENCY": "WORK_PLAN",
        "INSPECTION": "SAFETY_CHECKLIST",
        "REPORT": "INCIDENT_REPORT",
        "TRAINING": "TRAINING_RECORD",
    }
    for dr in data.get("documentRequirements", []):
        dt = dr.get("documentType")
        if dt and dt not in VALID_DOC_TYPES:
            dr["documentType"] = DOC_TYPE_MAP.get(dt, "WORK_PLAN")

    # MANDATORY CI with null basedOn → RECOMMENDED 다운그레이드
    for ci in data.get("checklistItems", []):
        if ci.get("bindingForce") == "MANDATORY" and not ci.get("basedOn"):
            ci["bindingForce"] = "RECOMMENDED"
            ctx = ci.get("guideContext") or ""
            if "(법령 근거 미확인)" not in ctx:
                ci["guideContext"] = (ctx + " (법령 근거 미확인)").strip()


def partition_id_ranges(short_code: str, parts: list) -> list[dict]:
    """preAssignedIdRange를 part char_count 비율로 비례 분할.
    DT는 Part 1에만 전체 범위 부여 (다른 part는 None).
    CI/WP/ES/DR은 비례 분할, 마지막 part가 잔여 흡수, 각 part 최소 5개 보장.
    """
    base_ranges = {"CI": (1, 200), "DT": (1, 100), "WP": (1, 50), "ES": (1, 100), "DR": (1, 50)}
    total_chars = sum(p.char_count for p in parts) or 1
    cursors = {k: base_ranges[k][0] for k in base_ranges}
    result = []

    for idx, part in enumerate(parts):
        ranges = {}
        for et, (lo, hi) in base_ranges.items():
            total = hi - lo + 1

            if et == "DT":
                if part.extract_dt:
                    ranges[et] = {"start": _fmt_id(et, short_code, lo),
                                  "end": _fmt_id(et, short_code, hi)}
                else:
                    ranges[et] = None
                continue

            if idx == len(parts) - 1:
                start_seq = cursors[et]
                end_seq = hi
            else:
                share = max(5, int(round(total * part.char_count / total_chars)))
                start_seq = cursors[et]
                end_seq = min(hi, start_seq + share - 1)
                cursors[et] = end_seq + 1

            ranges[et] = {"start": _fmt_id(et, short_code, start_seq),
                          "end": _fmt_id(et, short_code, end_seq)}
        result.append(ranges)
    return result


def _fmt_id(entity_type: str, sc: str, seq: int) -> str:
    width = 2 if entity_type == "WP" else 3
    return f"{entity_type}-{sc}-{seq:0{width}d}"


def process_guide(guide_entry: dict, batch_id: str | None = None, dry_run: bool = False) -> dict:
    """가이드 처리 분기: char count > SPLIT_THRESHOLD_CHARS면 split 모드."""
    sc = guide_entry["shortCode"]
    doc = load_guide_doc(sc)
    if doc is None:
        print(f"  [{sc}] 텍스트 로드... SKIP (파싱 파일 없음/깨짐)")
        return {"shortCode": sc, "status": "SKIP", "reason": "no parsed file"}

    # char count 측정 (전체 평탄화)
    full_text = load_guide_text(sc)
    text_chars = len(full_text)

    if text_chars > SPLIT_THRESHOLD_CHARS:
        return _process_guide_split(guide_entry, doc, batch_id, dry_run)
    else:
        return _process_guide_single(guide_entry, full_text, batch_id, dry_run)


def _process_guide_split(guide_entry: dict, doc: dict, batch_id: str | None, dry_run: bool) -> dict:
    """대형 가이드 분할 추출."""
    sc = guide_entry["shortCode"]
    gc = guide_entry["guideCode"]

    print(f"  [{sc}] SPLIT 모드 진입 ({len(doc.get('sections', []))}개 섹션)")

    parts = split_guide_by_sections(doc, max_chars=SPLIT_TARGET_CHARS)
    print(f"  [{sc}] {len(parts)}개 part로 분할:")
    for p in parts:
        flag = " (DT)" if p.extract_dt else ""
        ctx = " +Sec3" if p.must_include_section_3 else ""
        print(f"    Part {p.part_index}/{p.total_parts}: 섹션 {p.section_numbers} ({p.char_count} chars{ctx}){flag}")

    id_partitions = partition_id_ranges(sc, parts)
    section3 = _find_section_3(doc.get("sections", []))

    SPLIT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    part_outputs = []
    elapsed_total = 0.0

    for part, id_ranges in zip(parts, id_partitions):
        part_path = SPLIT_TEMP_DIR / f"ci-{sc}-part{part.part_index}.json"

        # 캐시 재사용: 이미 임시 파일이 있으면 LLM 호출 생략
        if part_path.exists():
            try:
                data = json.loads(part_path.read_text(encoding="utf-8"))
                part_outputs.append(data)
                print(f"    Part {part.part_index}/{part.total_parts} 캐시 재사용 (skip)")
                continue
            except (json.JSONDecodeError, OSError):
                pass  # 캐시 깨짐 → 재추출

        part_text = render_part_text(part, section3)
        part_info = {
            "part_index": part.part_index,
            "total_parts": part.total_parts,
            "section_numbers": part.section_numbers,
            "extract_dt": part.extract_dt,
            "must_include_section_3": part.must_include_section_3,
            "id_ranges": id_ranges,
        }
        prompt = build_extraction_prompt(guide_entry, part_text, batch_id, part_info=part_info)

        if dry_run:
            print(f"    Part {part.part_index} DRY-RUN ({len(prompt)} chars)")
            continue

        print(f"    Part {part.part_index}/{part.total_parts} 추출 중...", end=" ", flush=True)
        start = time.time()
        try:
            response = run_claude_extraction(prompt, text_chars=part.char_count)
        except RateLimitError:
            raise  # 배치 즉시 중단 — 상위에서 처리
        except Exception as e:
            print(f"ERROR: {e}")
            return {"shortCode": sc, "status": "ERROR", "error": f"part{part.part_index}: {e}"}
        elapsed = time.time() - start
        elapsed_total += elapsed

        data = extract_json_from_response(response)
        if not data:
            err_path = SPLIT_TEMP_DIR / f"ci-{sc}-part{part.part_index}-raw.txt"
            err_path.write_text(response, encoding="utf-8")
            print(f"FAIL (raw → {err_path.name})")
            return {"shortCode": sc, "status": "JSON_PARSE_FAIL", "failedPart": part.part_index}

        # part 결과 임시 저장
        part_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        part_outputs.append(data)
        print(f"({elapsed:.1f}s) OK")

    if dry_run:
        return {"shortCode": sc, "status": "DRY_RUN", "parts": len(parts)}

    # 병합
    domain = guide_entry.get("domain")
    if not domain or domain == "?":
        raise ValueError(f"domain 정보 없음: {sc}")

    merged, merge_errors = merge_ci_parts(
        part_outputs, sc, gc, domain, batch_id, f"claude-{MODEL}-split",
    )

    # candidateSR 추출
    candidate_srs = {sr["id"] for sr in guide_entry.get("candidateSR", [])}

    # 후처리 적용 (split: candidate_srs 필터링 포함)
    _apply_post_processing(merged, candidate_srs=candidate_srs)

    # 스키마 검증
    schema_errors = validate_ci_output(merged)

    output_path = CI_OUTPUT_DIR / f"ci-{sc}.json"
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    # split-meta sidecar
    sidecar = {
        "shortCode": sc,
        "splitMode": True,
        "totalParts": len(parts),
        "parts": [{
            "partIndex": p.part_index,
            "sectionNumbers": p.section_numbers,
            "charCount": p.char_count,
            "mustIncludeSection3": p.must_include_section_3,
            "extractDt": p.extract_dt,
            "idRanges": id_ranges,
        } for p, id_ranges in zip(parts, id_partitions)],
        "mergeErrors": merge_errors,
        "schemaErrors": len(schema_errors),
        "elapsedTotal": elapsed_total,
    }
    (CI_OUTPUT_DIR / f"ci-{sc}.split-meta.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 임시 part 파일 정리 (성공 시)
    if not merge_errors and not schema_errors:
        for f in SPLIT_TEMP_DIR.glob(f"ci-{sc}-part*.json"):
            f.unlink()

    counts = {
        "CI": len(merged.get("checklistItems", [])),
        "DT": len(merged.get("domainTerms", [])),
        "WP": len(merged.get("workProcesses", [])),
        "ES": len(merged.get("equipmentSpecs", [])),
        "DR": len(merged.get("documentRequirements", [])),
    }
    status = "PASS" if not (schema_errors or merge_errors) else f"WARN({len(schema_errors)+len(merge_errors)})"
    print(f"  [{sc}] MERGED ({elapsed_total:.1f}s)  CI={counts['CI']} DT={counts['DT']} WP={counts['WP']} ES={counts['ES']} DR={counts['DR']}  {status}")

    return {
        "shortCode": sc,
        "status": "PASS" if not (schema_errors or merge_errors) else "SCHEMA_WARN",
        "elapsed": elapsed_total,
        "splitParts": len(parts),
        "counts": counts,
        "schemaErrors": len(schema_errors),
        "mergeErrors": len(merge_errors),
        "errors": (schema_errors[:3] + merge_errors[:3]),
    }


def _process_guide_single(guide_entry: dict, full_text: str, batch_id: str | None, dry_run: bool) -> dict:
    """단일 가이드 추출 처리 (기존 로직)."""
    sc = guide_entry["shortCode"]
    gc = guide_entry["guideCode"]

    print(f"  [{sc}] 텍스트 로드...", end=" ", flush=True)
    guide_text = full_text

    # 텍스트가 너무 길면 잘라내기 (토큰 제한 고려)
    text_chars = len(guide_text)
    truncated = False
    original_chars = text_chars
    if text_chars > 120000:
        guide_text = guide_text[:120000] + "\n\n[... 텍스트 잘림 ...]"
        truncated = True
        print(f"({text_chars}→120K chars)", end=" ", flush=True)
    else:
        print(f"({text_chars} chars)", end=" ", flush=True)

    prompt = build_extraction_prompt(guide_entry, guide_text, batch_id)

    if dry_run:
        print(f"DRY-RUN (prompt {len(prompt)} chars)")
        return {"shortCode": sc, "status": "DRY_RUN", "promptChars": len(prompt)}

    print("추출 중...", end=" ", flush=True)
    start = time.time()

    try:
        response = run_claude_extraction(prompt, text_chars=text_chars)
    except RateLimitError:
        raise  # 배치 즉시 중단 — 상위에서 처리
    except Exception as e:
        print(f"ERROR: {e}")
        return {"shortCode": sc, "status": "ERROR", "error": str(e)}

    elapsed = time.time() - start
    print(f"({elapsed:.1f}s)", end=" ", flush=True)

    # JSON 추출
    data = extract_json_from_response(response)
    if not data:
        # 응답 저장 (디버깅용)
        err_path = CI_OUTPUT_DIR / f"ci-{sc}-raw-response.txt"
        err_path.write_text(response, encoding="utf-8")
        print(f"FAIL (JSON 추출 실패, raw → {err_path.name})")
        return {"shortCode": sc, "status": "JSON_PARSE_FAIL", "elapsed": elapsed}

    # metadata 보정 (LLM이 잘못 채울 수 있음)
    if "metadata" not in data:
        data["metadata"] = {}
    data["metadata"]["guideCode"] = gc
    data["metadata"]["shortCode"] = sc
    # domain은 배치 metadata에서 가져오거나 가이드 정보에서
    domain = guide_entry.get("domain")
    if not domain or domain == "?":
        raise ValueError(f"domain 정보 없음: {sc} — 배치 파일에 domain이 설정되어야 합니다")
    data["metadata"]["domain"] = domain
    data["metadata"]["extractedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["metadata"]["extractedBy"] = f"claude-{MODEL}-pilot"
    data["metadata"]["batchId"] = batch_id

    # candidateSR 추출
    candidate_srs = {sr["id"] for sr in guide_entry.get("candidateSR", [])}

    # 후처리 (5개 키 보장 + relatedSR/basedOn + requirementType + MANDATORY 다운그레이드)
    _apply_post_processing(data, candidate_srs=candidate_srs)

    # 잘림 메타데이터 추가
    if truncated:
        data["metadata"]["truncated"] = True
        data["metadata"]["truncatedAt"] = 120000
        data["metadata"]["originalChars"] = original_chars

    # 스키마 검증
    errors = validate_ci_output(data)

    # 저장
    output_path = CI_OUTPUT_DIR / f"ci-{sc}.json"
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    ci_count = len(data.get("checklistItems", []))
    dt_count = len(data.get("domainTerms", []))
    wp_count = len(data.get("workProcesses", []))
    es_count = len(data.get("equipmentSpecs", []))
    dr_count = len(data.get("documentRequirements", []))

    status = "PASS" if not errors else f"WARN({len(errors)})"
    print(f"{status}  CI={ci_count} DT={dt_count} WP={wp_count} ES={es_count} DR={dr_count}")

    return {
        "shortCode": sc,
        "status": "PASS" if not errors else "SCHEMA_WARN",
        "elapsed": elapsed,
        "counts": {"CI": ci_count, "DT": dt_count, "WP": wp_count, "ES": es_count, "DR": dr_count},
        "schemaErrors": len(errors),
        "errors": errors[:5] if errors else [],
    }


def main():
    parser = argparse.ArgumentParser(description="CI/DT/WP/ES/DR 엔티티 추출")
    parser.add_argument("--guides-file", type=str, help="가이드 목록 JSON (pilot-guides.json)")
    parser.add_argument("--batch", type=str, help="배치 입력 JSON 경로")
    parser.add_argument("--guide", type=str, help="단일 가이드 shortCode")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="이미 추출된 가이드 건너뛰기 (기본: True)")
    parser.add_argument("--force", action="store_true", help="이미 추출된 가이드도 재실행")
    parser.add_argument("--skip-guides", type=str, default="", help="콤마 구분 shortCode 목록 (timeout outlier 임시 제외)")
    parser.add_argument("--dry-run", action="store_true", help="프롬프트 구성만 확인, API 호출 안 함")
    parser.add_argument("--model", type=str, default="opus", help="Claude 모델 (기본: opus)")
    args = parser.parse_args()

    global MODEL
    MODEL = args.model

    CI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[START] 엔티티 추출 (model={MODEL})")

    # 가이드 목록 수집
    guide_entries = []  # list of {shortCode, guideCode, domain, candidateSR, ...}

    if args.guide:
        # 단일 가이드: 배치 파일에서 해당 가이드 찾기
        for bp in sorted(BATCHES_DIR.glob("pipeb-*-input.json")):
            batch = json.loads(bp.read_text(encoding="utf-8"))
            batch_domain = batch["metadata"].get("domain", "?")
            for g in batch["guides"]:
                if g["shortCode"] == args.guide:
                    g.setdefault("domain", batch_domain)
                    guide_entries.append((g, batch["metadata"]["batchId"]))
                    break
        if not guide_entries:
            # 배치 없이 단일 가이드 처리 (기본 candidateSR 없음)
            print(f"  WARNING: {args.guide}에 해당하는 배치를 찾을 수 없음")
            sys.exit(1)

    elif args.batch:
        batch_path = Path(args.batch)
        if not batch_path.is_absolute():
            batch_path = DATA_DIR.parent / args.batch
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        bid = batch["metadata"]["batchId"]
        batch_domain = batch["metadata"].get("domain", "?")
        for g in batch["guides"]:
            g.setdefault("domain", batch_domain)
            guide_entries.append((g, bid))

    elif args.guides_file:
        # 파일럿 가이드 목록 → 배치 파일에서 해당 가이드 찾기
        gf_path = Path(args.guides_file)
        if not gf_path.is_absolute():
            gf_path = DATA_DIR.parent / args.guides_file
        pilot = json.loads(gf_path.read_text(encoding="utf-8"))
        pilot_scs = {g["shortCode"] for g in pilot["guides"]}

        # 배치 파일에서 pilot 가이드 추출
        for bp in sorted(BATCHES_DIR.glob("pipeb-*-input.json")):
            batch = json.loads(bp.read_text(encoding="utf-8"))
            bid = batch["metadata"]["batchId"]
            batch_domain = batch["metadata"].get("domain", "?")
            for g in batch["guides"]:
                if g["shortCode"] in pilot_scs:
                    g.setdefault("domain", batch_domain)
                    guide_entries.append((g, bid))
                    pilot_scs.discard(g["shortCode"])

        if pilot_scs:
            print(f"  WARNING: 배치에서 찾지 못한 가이드: {pilot_scs}")
    else:
        parser.print_help()
        sys.exit(1)

    # --skip-guides로 명시 제외
    if args.skip_guides:
        skip_set = {s.strip() for s in args.skip_guides.split(",") if s.strip()}
        before = len(guide_entries)
        guide_entries = [(g, b) for g, b in guide_entries if g["shortCode"] not in skip_set]
        skipped = before - len(guide_entries)
        if skipped:
            print(f"  --skip-guides: {skipped}개 명시 제외 ({sorted(skip_set)})")

    print(f"  대상: {len(guide_entries)}개 가이드")

    # 기존 추출 결과 확인
    if not args.force:
        filtered = []
        for g, bid in guide_entries:
            output_path = CI_OUTPUT_DIR / f"ci-{g['shortCode']}.json"
            if output_path.exists():
                print(f"  [{g['shortCode']}] 이미 추출됨 → 건너뜀")
            else:
                filtered.append((g, bid))
        guide_entries = filtered

    if not guide_entries:
        print("\n[DONE] 추출할 가이드 없음 (모두 완료)")
        return

    print(f"  실행: {len(guide_entries)}개\n")

    results = []
    for g, bid in guide_entries:
        try:
            result = process_guide(g, batch_id=bid, dry_run=args.dry_run)
        except RateLimitError as e:
            print(f"\n[ABORT] API limit 감지 — 배치 즉시 중단: {e}")
            results.append({"shortCode": g["shortCode"], "status": "RATE_LIMIT", "error": str(e)})
            break
        results.append(result)

    # 결과 요약
    print(f"\n[DONE] 추출 완료")
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "SCHEMA_WARN")
    failed = sum(1 for r in results if r["status"] in ("ERROR", "JSON_PARSE_FAIL"))
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    print(f"  PASS: {passed}  WARN: {warned}  FAIL: {failed}  SKIP: {skipped}")

    if any(r.get("counts") for r in results):
        total_ci = sum(r.get("counts", {}).get("CI", 0) for r in results)
        total_dt = sum(r.get("counts", {}).get("DT", 0) for r in results)
        total_wp = sum(r.get("counts", {}).get("WP", 0) for r in results)
        total_es = sum(r.get("counts", {}).get("ES", 0) for r in results)
        total_dr = sum(r.get("counts", {}).get("DR", 0) for r in results)
        print(f"  총 엔티티: CI={total_ci} DT={total_dt} WP={total_wp} ES={total_es} DR={total_dr}")

    # 결과 저장
    report_path = DATA_DIR / "pilot-extraction-report.json"
    report_path.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": MODEL,
        "totalGuides": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  보고서: {report_path}")


if __name__ == "__main__":
    main()
