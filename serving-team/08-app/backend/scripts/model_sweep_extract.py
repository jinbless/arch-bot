#!/usr/bin/env python3
"""OWA→CWA #4 — Stage1 '기인물-first' 추출 모델 스윕.

8장 실제 사진을 기인물-first 프롬프트로 여러 모델에 재추출. 기인물(사고 직접원인 설비/기계/
물질/구조물)을 우선 식별하고, 각 기인물의 관찰 위험상태 + 결여 안전조치(법정어휘) + 예상사고 +
즉시조치 체크리스트를 산출. 매칭/채점은 별도(model_sweep_score.py, 고정 gpt-5.4)라 Stage1
모델 효과만 분리된다.

산출 model_sweep_extractions.json: {photo: {model: {extraction|error}}}.

사용: .venv/bin/python scripts/model_sweep_extract.py
"""
from __future__ import annotations

import base64
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VISION = ART / "claude_vision_8photo_input.json"
PHOTODIR = REPO / "real-test-photo"
OUT = ART / "model_sweep_extractions.json"

MODELS = ["gpt-4.1", "gpt-5-mini", "gpt-5-nano", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4"]

SYS = (
    "너는 대한민국 산업안전보건 현장점검 비전 분석기다. 작업장 사진 1장을 받는다. "
    "사업주에게 (1)위험요소와 (2)즉시 조치 체크리스트를 주는 것이 목표다.\n"
    "원칙: '가장 먼저 사고를 일으킬 수 있는 기인물(起因物)'을 우선 찾아라. 기인물 = 사고의 직접 원인이 "
    "되는 기계·설비·물질·구조물·작업(예: 고소작업대, 지게차, 사출성형기, 프레스, 굴착기, 비계, 누출 유류). "
    "기인물 명칭은 산업안전보건규칙 어휘에 맞춰 정규화하라(포크레인→굴착기, 시저리프트→고소작업대 등).\n"
    "각 기인물마다: 관찰된 위험상태, 결여된 안전조치(법정·표준 어휘: 안전난간·방호장치·덮개·울·추락방호망·"
    "안전대·후방감지기·백레스트 등), 예상 사고형태(추락/끼임/충돌/낙하/화재/전도 등)를 적어라. "
    "사진에 실제로 보이는 근거로만. 사람이 안 보이면 설비 자체의 결여상태로 판단. 추측 금지. 한국어."
)

SCHEMA = {"name": "extraction", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "properties": {
        "scene_summary": {"type": "string"},
        "gimulmul": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "properties": {
                "name": {"type": "string"},
                "observed_state": {"type": "string"},
                "missing_measures": {"type": "array", "items": {"type": "string"}},
                "expected_accident": {"type": "string"}},
            "required": ["name", "observed_state", "missing_measures", "expected_accident"]}},
        "checklist": {"type": "array", "items": {"type": "string"}}},
    "required": ["scene_summary", "gimulmul", "checklist"]}}


def data_url(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def main():
    photos = json.load(open(VISION, encoding="utf-8"))["photos"]
    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    jobs = []
    for p in photos:
        f = PHOTODIR / p["photo"]
        if not f.exists():
            print(f"[skip] 파일없음 {p['photo']}"); continue
        url = data_url(f)
        for m in MODELS:
            jobs.append((p["photo"].split("(")[0], m, url))

    def run(job):
        short, model, url = job
        try:
            r = client.chat.completions.create(model=model, messages=[
                {"role": "system", "content": SYS},
                {"role": "user", "content": [
                    {"type": "text", "text": "이 사진을 기인물-first로 분석하라."},
                    {"type": "image_url", "image_url": {"url": url}}]}],
                response_format={"type": "json_schema", "json_schema": SCHEMA},
                max_completion_tokens=4000)
            data = json.loads(r.choices[0].message.content)
            return short, model, {"extraction": data}
        except Exception as e:  # noqa: BLE001
            return short, model, {"error": str(e)[:200]}

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(run, j) for j in jobs]
        for fu in as_completed(futs):
            short, model, res = fu.result()
            results.setdefault(short, {})[model] = res
            tag = "OK " if "extraction" in res else "ERR"
            n = len(res.get("extraction", {}).get("gimulmul", [])) if "extraction" in res else 0
            print(f"  {tag} {short:<12} {model:<14} 기인물 {n}", flush=True)

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    nok = sum(1 for s in results.values() for r in s.values() if "extraction" in r)
    print(f"\n추출 {nok}/{len(jobs)} 성공 → {OUT.name}")


if __name__ == "__main__":
    main()
