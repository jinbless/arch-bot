#!/usr/bin/env python3
"""공통 LLM client — OpenAI + Anthropic 통일 structured-output 래퍼 + mock.

하이브리드 enrichment용. enum-constrained tool/function로 환각 차단(catalog allowlist를
schema에 baking), env 키로 provider 자동 선택, 키 없으면 mock(plumbing 검증).

provider/model:
  anthropic: cheap=claude-haiku-4-5  strong=claude-sonnet-4-6   (ANTHROPIC_API_KEY)
  openai   : cheap=gpt-4.1-mini       strong=gpt-4.1             (OPENAI_API_KEY)
  mock     : 키 없음/강제 — mock_fn(또는 schema 기본값) 반환

structured(system, user, tool) → dict (tool.input_schema에 맞는 구조화 출력).
  tool = {"name","description","input_schema"(JSON Schema)} — Anthropic tool / OpenAI function 공용.

사용:
  c = LLMClient()                 # 키 자동, 없으면 mock
  c = LLMClient(provider="anthropic", tier="strong")
  c = LLMClient(mock=True)        # 강제 mock
  out = c.structured(SYS, USER, TOOL, mock_fn=lambda s,u: {...})
"""
from __future__ import annotations

import json
import os
from typing import Callable, Optional

MODELS = {
    "anthropic": {"cheap": "claude-haiku-4-5", "strong": "claude-sonnet-4-6"},
    "openai": {"cheap": "gpt-4.1-mini", "strong": "gpt-4.1"},
}
_KEY = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def available_providers() -> list[str]:
    return [p for p, k in _KEY.items() if os.environ.get(k)]


class LLMClient:
    def __init__(self, provider: Optional[str] = None, tier: str = "cheap",
                 model: Optional[str] = None, mock: bool = False):
        self.tier = tier
        avail = available_providers()
        if mock or not avail:
            self.provider, self.model, self.mock = "mock", model or "mock", True
            return
        self.provider = provider if (provider in avail) else avail[0]
        self.model = model or MODELS[self.provider][tier]
        self.mock = False
        self._client = None

    def _lazy(self):
        if self._client is not None:
            return self._client
        if self.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=os.environ[_KEY["anthropic"]])
        elif self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=os.environ[_KEY["openai"]])
        return self._client

    def structured(self, system: str, user: str, tool: dict, *,
                   mock_fn: Optional[Callable[[str, str], dict]] = None,
                   max_tokens: int = 600, temperature: float = 0.0) -> dict:
        """tool.input_schema에 맞는 구조화 dict 반환. 실패/mock 시 mock_fn 또는 {}."""
        if self.mock:
            return (mock_fn(system, user) if mock_fn else {}) | {"_mock": True}
        try:
            if self.provider == "anthropic":
                msg = self._lazy().messages.create(
                    model=self.model, max_tokens=max_tokens, temperature=temperature,
                    system=system, messages=[{"role": "user", "content": user}],
                    tools=[{"name": tool["name"], "description": tool["description"],
                            "input_schema": tool["input_schema"]}],
                    tool_choice={"type": "tool", "name": tool["name"]},
                )
                for block in msg.content:
                    if getattr(block, "type", None) == "tool_use":
                        return dict(block.input)
                return {"_error": "no tool_use"}
            else:  # openai
                resp = self._lazy().chat.completions.create(
                    model=self.model, temperature=temperature, max_tokens=max_tokens,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    tools=[{"type": "function", "function": {
                        "name": tool["name"], "description": tool["description"],
                        "parameters": tool["input_schema"]}}],
                    tool_choice={"type": "function", "function": {"name": tool["name"]}},
                )
                tc = resp.choices[0].message.tool_calls
                if tc:
                    return json.loads(tc[0].function.arguments)
                return {"_error": "no tool_call"}
        except Exception as exc:  # noqa: BLE001
            return {"_error": str(exc)}


if __name__ == "__main__":
    c = LLMClient()
    print(f"provider={c.provider} model={c.model} mock={c.mock} avail={available_providers()}")
