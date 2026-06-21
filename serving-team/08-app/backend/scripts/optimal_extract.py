#!/usr/bin/env python3
"""OWA→CWA A — rich+기인물 하이브리드 추출 (포맷 처방).

#4 발견: 추출 *포맷*이 변수(rich scene > 터스 기인물-only). 처방 = 둘 다 유지.
이 추출은 풍부한 장면관찰(visual_observations/cues)과 기인물 구조(name/observed_state/
missing_measures/expected_accident)를 함께 산출. missing_measures(결여조치, 법정어휘)는
Stage2 변별의 핵심 키(조문 required_measures와 대조).

GPT(OpenAI) / Claude(Anthropic) 모델 모두 지원. 산출 optimal_extractions.json.

사용: .venv/bin/python scripts/optimal_extract.py
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

from build_article_signatures import _ensure_key  # noqa: E402
from claude_sweep_extract import _ensure_anthropic_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VISION = ART / "claude_vision_8photo_input.json"
PHOTODIR = REPO / "real-test-photo"
OUT = ART / "optimal_extractions.json"

# 강한 추출기 2종(모델은 병목 아니나 rich 추출 품질 위해 강모델). gpt=OpenAI, claude=Anthropic
MODELS = ["gpt-5.4", "claude-sonnet-4-6"]

SYS = (
    "너는 대한민국 산업안전보건 현장점검 비전 분석기다. 작업장 사진 1장을 받는다. "
    "사업주에게 위험요소 + 즉시조치 체크리스트를 주는 것이 목표다.\n"
    "두 가지를 모두 풍부하게 산출하라:\n"
    "(1) 풍부한 장면 묘사: visual_observations(보이는 사실), visual_cues(위험 시각단서). 구체적으로.\n"
    "(2) 기인물 구조: '가장 먼저 사고를 일으킬 기인물(起因物)'을 우선 식별. 기인물 = 사고 직접원인 "
    "기계·설비·물질·구조물·작업(고소작업대·지게차·사출성형기·프레스·굴착기·비계·누출유류 등). "
    "명칭은 산업안전보건규칙 어휘로 정규화(포크레인→굴착기, 시저리프트→고소작업대). "
    "프레스와 사출성형기는 구조가 유사하니 프레임/금형/슬라이드/노즐로 구분하라.\n"
    "각 기인물: observed_state(관찰 위험상태), missing_measures(결여된 안전조치 — 법정·표준 어휘로: "
    "안전난간·방호장치·덮개·울·추락방호망·안전대 부착설비·후방감지기·백레스트·헤드가드·접지 등), "
    "expected_accident(예상 사고: 추락/끼임/충돌/낙하/화재/전도 등).\n"
    "사진에 실제 보이는 근거로만. 사람이 없으면 설비 자체의 결여상태로 판단. 추측 금지. 한국어."
)

PROPS = {
    "scene_summary": {"type": "string"},
    "visual_observations": {"type": "array", "items": {"type": "string"}},
    "visual_cues": {"type": "array", "items": {"type": "string"}},
    "gimulmul": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "name": {"type": "string"},
            "observed_state": {"type": "string"},
            "missing_measures": {"type": "array", "items": {"type": "string"}},
            "expected_accident": {"type": "string"}},
        "required": ["name", "observed_state", "missing_measures", "expected_accident"]}},
    "checklist": {"type": "array", "items": {"type": "string"}},
}
REQUIRED = ["scene_summary", "visual_observations", "visual_cues", "gimulmul", "checklist"]
JSON_SCHEMA = {"type": "object", "additionalProperties": False, "properties": PROPS, "required": REQUIRED}


def data_url(path: Path):
    ext = path.suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode()}", f"image/{mime}", base64.b64encode(path.read_bytes()).decode()


def main():
    photos = json.load(open(VISION, encoding="utf-8"))["photos"]
    _ensure_key(); _ensure_anthropic_key()
    from openai import OpenAI
    from anthropic import Anthropic
    oai = OpenAI(); ant = Anthropic()
    tool = {"name": "extraction", "description": "rich+기인물 추출", "input_schema": JSON_SCHEMA}

    jobs = []
    for p in photos:
        f = PHOTODIR / p["photo"]
        if f.exists():
            for m in MODELS:
                jobs.append((p["photo"].split("(")[0], m, f))

    def run(job):
        short, model, f = job
        url, media, b64 = data_url(f)
        try:
            if model.startswith("claude"):
                r = ant.messages.create(model=model, max_tokens=4000, system=SYS,
                    tools=[tool], tool_choice={"type": "tool", "name": "extraction"},
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "이 사진을 rich+기인물로 분석하라."},
                        {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}}]}])
                data = next((b.input for b in r.content if b.type == "tool_use"), None)
            else:
                kw = {"reasoning_effort": "low"} if "nano" in model else {}
                r = oai.chat.completions.create(model=model, max_completion_tokens=6000, messages=[
                    {"role": "system", "content": SYS},
                    {"role": "user", "content": [
                        {"type": "text", "text": "이 사진을 rich+기인물로 분석하라."},
                        {"type": "image_url", "image_url": {"url": url}}]}],
                    response_format={"type": "json_schema", "json_schema": {"name": "extraction", "strict": True, "schema": JSON_SCHEMA}}, **kw)
                c = r.choices[0].message.content
                data = json.loads(c) if c else None
            if data is None:
                return short, model, {"error": "empty"}
            return short, model, {"extraction": data}
        except Exception as e:  # noqa: BLE001
            return short, model, {"error": str(e)[:200]}

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(run, j) for j in jobs]):
            short, model, res = fu.result()
            results.setdefault(short, {})[model] = res
            n = len(res.get("extraction", {}).get("gimulmul", [])) if "extraction" in res else 0
            print(f"  {'OK ' if 'extraction' in res else 'ERR'} {short:<12} {model:<20} 기인물 {n} {res.get('error','')}", flush=True)

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    nok = sum(1 for s in results.values() for r in s.values() if "extraction" in r)
    print(f"\nrich+기인물 추출 {nok}/{len(jobs)} → {OUT.name}")


if __name__ == "__main__":
    main()
