"""Phase 1 Track 2 — LLM Provider 단순 wrapper (사용자 비판 #10).

목적: SR inversion (Phase 2) + 향후 reranker/description synthesis 등에서
일관된 호출 인터페이스 제공. 정식 abstract class까지는 over-engineering이므로
함수 호출만 통일.

Supports:
  - OpenAI (gpt-4o, gpt-4-turbo, etc.)
  - Anthropic (claude-sonnet-*, claude-opus-*) — anthropic SDK 설치 시
  - mock (tests/eval 재현)

Usage:
  from llm_provider import call_llm
  result = call_llm(
      provider="openai",
      model="gpt-4o",
      system="You are an expert.",
      user="Convert SR to SHE.",
      max_tokens=2000,
      temperature=0.3,
      json_mode=True,
  )
  print(result["text"])  # 응답 텍스트
  print(result["usage"]) # token 사용량
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load_env_keys() -> None:
    """OPENAI_API_KEY, ANTHROPIC_API_KEY 환경변수 로드 (없으면 OHS/.env 또는 OHS/backend/.env에서)."""
    if not os.environ.get("OPENAI_API_KEY"):
        for env_file in [ROOT / "OHS" / ".env", ROOT / "OHS" / "backend" / ".env"]:
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
                if os.environ.get("OPENAI_API_KEY"):
                    break


def call_llm(
    provider: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> dict[str, Any]:
    """Unified LLM call.

    Returns:
      {
        "text": str,           # 응답 텍스트
        "usage": {"in": int, "out": int, "total": int},
        "provider": str,
        "model": str,
      }
    """
    _load_env_keys()

    if provider == "openai":
        return _call_openai(model, system, user, max_tokens, temperature, json_mode)
    elif provider == "anthropic":
        return _call_anthropic(model, system, user, max_tokens, temperature, json_mode)
    elif provider == "mock":
        return _call_mock(model, system, user)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _call_openai(
    model: str, system: str, user: str,
    max_tokens: int, temperature: float, json_mode: bool,
) -> dict[str, Any]:
    from openai import OpenAI
    client = OpenAI()
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    r = client.chat.completions.create(**kwargs)
    return {
        "text": r.choices[0].message.content or "",
        "usage": {
            "in": r.usage.prompt_tokens,
            "out": r.usage.completion_tokens,
            "total": r.usage.total_tokens,
        },
        "provider": "openai",
        "model": model,
    }


def _call_anthropic(
    model: str, system: str, user: str,
    max_tokens: int, temperature: float, json_mode: bool,
) -> dict[str, Any]:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic SDK not installed. Add to requirements-eval.txt: anthropic>=0.40.0"
        )
    client = anthropic.Anthropic()
    if json_mode:
        # Anthropic은 OpenAI같은 strict json_mode 없음 — system에 강제 지시 추가
        system = system + "\n\nIMPORTANT: 응답은 반드시 valid JSON 객체 1개만 반환. 다른 텍스트 금지."
    r = client.messages.create(
        model=model,
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return {
        "text": r.content[0].text,
        "usage": {
            "in": r.usage.input_tokens,
            "out": r.usage.output_tokens,
            "total": r.usage.input_tokens + r.usage.output_tokens,
        },
        "provider": "anthropic",
        "model": model,
    }


def _call_mock(model: str, system: str, user: str) -> dict[str, Any]:
    """Test/eval 재현용 — 결정론적 응답."""
    import hashlib
    h = hashlib.md5((system + user).encode()).hexdigest()[:10]
    return {
        "text": json.dumps({"mock": True, "hash": h}, ensure_ascii=False),
        "usage": {"in": 0, "out": 0, "total": 0},
        "provider": "mock",
        "model": model,
    }


# CLI: dry-run cost calibration
if __name__ == "__main__":
    print("=" * 60)
    print("LLM Provider Wrapper — dry-run")
    print("=" * 60)
    test_system = "You are a Korean industrial safety expert."
    test_user = "다음 SR을 SHE로 변환해주세요: '사업주는 비계 위 작업 시 안전대를 체결해야 한다.'"

    # OpenAI
    print("\n[OpenAI gpt-4o]")
    try:
        r = call_llm(
            provider="openai",
            model="gpt-4o",
            system=test_system,
            user=test_user,
            max_tokens=200,
            temperature=0.3,
        )
        print(f"  text ({len(r['text'])} chars): {r['text'][:120]}...")
        print(f"  usage: in={r['usage']['in']}, out={r['usage']['out']}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Mock
    print("\n[Mock]")
    r = call_llm(provider="mock", model="any", system=test_system, user=test_user)
    print(f"  text: {r['text']}")

    # Anthropic (skipped if SDK missing)
    print("\n[Anthropic]")
    try:
        r = call_llm(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            system=test_system,
            user=test_user,
            max_tokens=200,
        )
        print(f"  text ({len(r['text'])} chars): {r['text'][:120]}...")
    except Exception as e:
        print(f"  SKIP: {e}")
