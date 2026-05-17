#!/usr/bin/env python3
"""Phase E Step 4d — SHACL shapes syntax 자동 fix (LLM iteration).

서비스 검증 shapes (serving-validation-shapes-v2.ttl)의 LLM 생성 결함을
rdflib parse + pyshacl validate 반복 검증으로 자동 수정.

흐름:
1. rdflib로 parse 시도
2. error message 캡처
3. LLM에게 error + ttl 컨텍스트 보여주고 fix 요청
4. 새 ttl로 re-parse
5. 통과 또는 max iterations (default 5)

산출:
- serving-validation-shapes-v3.ttl (fix 통과 시)
- shacl_fix_audit.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = _find_repo_root()
ONTOLOGY_DIR = REPO_ROOT / "ontology-team" / "06-reasoning" / "ontology"
ARTIFACTS_DIR = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
SHAPES_V2 = ONTOLOGY_DIR / "serving-validation-shapes-v2.ttl"
SHAPES_V3 = ONTOLOGY_DIR / "serving-validation-shapes-v3.ttl"
AUDIT_PATH = ARTIFACTS_DIR / "shacl_fix_audit.json"
DEFAULT_MODEL = os.environ.get("LLM_RERANK_MODEL", "gpt-5.4-nano")


SCHEMA = {
    "name": "shacl_fix",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "fixed_ttl": {"type": "string", "description": "Complete corrected Turtle content"},
            "fix_summary": {"type": "string", "description": "한국어 1-2문장 수정 요약"},
        },
        "required": ["fixed_ttl", "fix_summary"],
        "additionalProperties": False,
    },
}

SYSTEM = """\
당신은 SHACL/Turtle 문법 전문가입니다. rdflib parse error가 발생한 Turtle 파일을 자동 수정합니다.

원칙:
1. 모든 `@prefix` 선언 유지/추가
2. `sh:property [ ... ]` blank node nesting을 정확하게 (괄호, 세미콜론, 마침표 위치)
3. 각 NodeShape는 `.`로 종료
4. URI 안에 한글 있으면 percent-encode 또는 prefix 사용
5. 모든 triple은 `subject predicate object .` 형식 필수

원본 의미 유지, 문법만 수정.
"""

USER_TEMPLATE = """\
[parse error]
{error}

[현재 Turtle 파일]
{ttl}

위 error를 fix한 완전한 corrected Turtle을 반환하세요. 모든 prefix 선언 + shape 구조 유지.
"""


def try_parse(content: str) -> tuple[bool, str]:
    """rdflib parse 시도. (success, error_msg)"""
    from rdflib import Graph

    try:
        g = Graph()
        g.parse(data=content, format="turtle")
        return True, f"OK: {len(g)} triples"
    except Exception as exc:
        return False, str(exc)


async def fix_iteration(client, model: str, content: str, error: str) -> dict:
    user = USER_TEMPLATE.format(error=error[:600], ttl=content[:12000])
    r = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "developer", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_schema", "json_schema": SCHEMA},
        max_completion_tokens=16384,
    )
    return json.loads(r.choices[0].message.content or "{}")


async def main_async(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY required", file=sys.stderr)
        return 2

    if not SHAPES_V2.exists():
        print(f"ERROR: {SHAPES_V2} 없음", file=sys.stderr)
        return 2

    content = SHAPES_V2.read_text(encoding="utf-8")
    print(f"Initial: {len(content)} chars, {len(content.splitlines())} lines")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    audit_iterations = []

    for i in range(args.max_iterations):
        ok, msg = try_parse(content)
        print(f"\n[Iter {i+1}] {msg[:200]}")
        if ok:
            print(f"  ✅ Parse PASS at iteration {i+1}")
            audit_iterations.append({"iter": i + 1, "status": "ok", "msg": msg})
            break
        audit_iterations.append({"iter": i + 1, "status": "error", "error": msg[:500]})
        print(f"  → LLM fix attempt...")
        fix = await fix_iteration(client, args.model, content, msg)
        new_content = fix.get("fixed_ttl", "")
        if not new_content or len(new_content) < 200:
            print(f"  ⚠️ LLM returned empty/short fix")
            audit_iterations[-1]["llm_response"] = "empty"
            continue
        content = new_content
        print(f"  → got fix ({len(new_content)} chars), summary: {fix.get('fix_summary', '')[:120]}")
    else:
        print(f"\n⚠️ Max iterations ({args.max_iterations}) reached without PASS")

    final_ok, final_msg = try_parse(content)
    if final_ok:
        SHAPES_V3.write_text(content, encoding="utf-8")
        print(f"\n✅ Saved: {SHAPES_V3.relative_to(REPO_ROOT)}")
    else:
        print(f"\n❌ Final still fails: {final_msg[:200]}")

    AUDIT_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": args.model,
                "max_iterations": args.max_iterations,
                "final_status": "ok" if final_ok else "fail",
                "final_msg": final_msg[:500],
                "iterations": audit_iterations,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    return 0 if final_ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-iterations", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    sys.exit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
