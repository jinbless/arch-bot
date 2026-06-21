#!/usr/bin/env python3
"""OWA→CWA #4 확장 — Claude 모델로 Stage1 '기인물-first' 추출(GPT sweep과 동일 프롬프트·스키마).

기존 Claude rich 추출이 GPT 기인물-first를 능가한 발견 → Claude 모델(Haiku/Sonnet/Opus)을
동일 기인물-first 포맷으로 재추출해 공정 비교. 결과를 model_sweep_extractions.json에 병합 →
model_sweep_score.py가 자동 채점(매칭단 고정 gpt-5.4).

구조화 출력은 Anthropic tool-forcing(input_schema=동일 스키마). 키는 .env ANTHROPIC_API_KEY.

사용: .venv/bin/python scripts/claude_sweep_extract.py
"""
from __future__ import annotations

import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from model_sweep_extract import SYS, SCHEMA, VISION, PHOTODIR, OUT  # noqa: E402

CLAUDE_MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"]


def _ensure_anthropic_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for envf in (BACKEND / ".env", BACKEND.parent / ".env"):
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        os.environ["ANTHROPIC_API_KEY"] = v
                        return


def main():
    photos = json.load(open(VISION, encoding="utf-8"))["photos"]
    _ensure_anthropic_key()
    from anthropic import Anthropic
    client = Anthropic()

    tool = {"name": "extraction", "description": "기인물-first 위험 추출 결과", "input_schema": SCHEMA["schema"]}

    jobs = []
    for p in photos:
        f = PHOTODIR / p["photo"]
        if not f.exists():
            continue
        ext = f.suffix.lstrip(".").lower()
        media = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        b64 = base64.b64encode(f.read_bytes()).decode()
        for m in CLAUDE_MODELS:
            jobs.append((p["photo"].split("(")[0], m, media, b64))

    def run(job):
        short, model, media, b64 = job
        try:
            r = client.messages.create(model=model, max_tokens=4000, system=SYS,
                tools=[tool], tool_choice={"type": "tool", "name": "extraction"},
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "이 사진을 기인물-first로 분석하라."},
                    {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}}]}])
            data = None
            for blk in r.content:
                if blk.type == "tool_use":
                    data = blk.input
                    break
            if data is None:
                return short, model, {"error": "no tool_use"}
            return short, model, {"extraction": data}
        except Exception as e:  # noqa: BLE001
            return short, model, {"error": str(e)[:200]}

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(run, j) for j in jobs]):
            short, model, res = fu.result()
            results.setdefault(short, {})[model] = res
            n = len(res.get("extraction", {}).get("gimulmul", [])) if "extraction" in res else 0
            print(f"  {'OK ' if 'extraction' in res else 'ERR'} {short:<12} {model:<26} 기인물 {n} {res.get('error','')}", flush=True)

    d = json.loads(OUT.read_text(encoding="utf-8"))
    for short, bym in results.items():
        d.setdefault(short, {}).update(bym)
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    nok = sum(1 for s in results.values() for r in s.values() if "extraction" in r)
    print(f"\nClaude 추출 {nok}/{len(jobs)} 성공, 병합 → {OUT.name}")


if __name__ == "__main__":
    main()
