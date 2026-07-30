# -*- coding: utf-8 -*-
"""targeted grounding 프로브 — 확정 위반 목록을 주고 '위치만' 표시하게 한다(판단 없음).

2단계 설계의 결정 실험: 파이프라인(cue-pool→RANK→검수)이 조문을 확정한 상황을 가정,
모델은 각 위반의 근거 위치만 b-box로 찍는다.
"""
import base64
import io
import json
import sys
from pathlib import Path

BACKEND = Path("/mnt/c/project/arch-bot/serving-team/08-app/backend")
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
from build_article_signatures import _ensure_key  # noqa: E402

from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-terra"
PHOTO = Path("/mnt/c/project/arch-bot/real-test-photo/label_photo/(주)경북환경_벽돌 성형기 주변 계단 상부 추락 위험.jpg")
S = Path("/mnt/c/Users/airat/AppData/Local/Temp/claude/C--project-arch-bot/ccdb5e3d-afc6-4c4e-97b0-d21a47ebde27/scratchpad")
OUT = S / f"bbox_tgt_{MODEL.replace('.', '_')}.jpg"
OUT_JSON = OUT.with_suffix(".json")

img = Image.open(PHOTO)
img = ImageOps.exif_transpose(img).convert("RGB")
send = img.copy()
send.thumbnail((1600, 1600))
buf = io.BytesIO()
send.save(buf, format="JPEG", quality=88)
b64 = base64.b64encode(buf.getvalue()).decode()

SCHEMA = {"name": "bbox", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"violations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {
            "article_code": {"type": "string"},
            "object": {"type": "string"},
            "label": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "integer"}},
            "confidence": {"type": "number"}},
        "required": ["article_code", "object", "label", "box_2d", "confidence"]}}},
    "required": ["violations"]}}

SYS = """너는 산업안전 감독관의 현장점검 비전 분석기다.
감독관이 이 사진에서 아래 위반을 이미 확정했다. 너의 임무는 **판단이 아니라 위치 표시**다.
각 위반의 근거가 되는 객체/영역을 사진에서 찾아 bounding box [x0,y0,x1,y1](0~1000 정규화, 왼쪽위 원점)로 정확히 표시하라.

[확정 위반 목록 — 각각 반드시 1개 이상 박스]
1. [제43조] 개구부 방호조치 미비 — 개구부란: 바닥·구조물 사이의 뚫린 깊은 공간(피트·구덩이·벽 옆 수직 낙하 공간·슬래브 단부). 난간·울타리·덮개가 없는 상태.
2. [제24조] 사다리식 통로 구조 미달 — 고정식 수직사다리(등받이울 포함)의 통로 구조·출입부.
3. [제4조] 폐기물·자재 적치 — 작업장에 폐기물이 무질서하게 쌓인 구역.

박스는 위반 근거가 가장 잘 보이는 영역으로 타이트하게. 같은 위반이 여러 곳이면 복수 박스 허용."""

_ensure_key()
from openai import OpenAI  # noqa: E402

client = OpenAI(timeout=240.0)
r = client.chat.completions.create(model=MODEL, max_completion_tokens=12000, messages=[
    {"role": "system", "content": SYS},
    {"role": "user", "content": [
        {"type": "text", "text": "확정 위반 3건의 근거 위치를 각각 bounding box로 표시하라."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
    response_format={"type": "json_schema", "json_schema": SCHEMA})
u = r.usage
rt = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", "?")
print(f"usage: input {u.prompt_tokens} · output {u.completion_tokens} (reasoning {rt})")
res = json.loads(r.choices[0].message.content)
OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

W, H = img.size
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 46)
except Exception:  # noqa: BLE001
    try:
        font = ImageFont.truetype("/mnt/c/Windows/Fonts/malgunbd.ttf", 46)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()

COLORS = ["#ff3b30", "#34c759", "#007aff", "#ff9500", "#af52de", "#00c7be", "#ffcc00"]
for i, v in enumerate(res["violations"]):
    x0, y0, x1, y1 = v["box_2d"]
    px = (x0 / 1000 * W, y0 / 1000 * H, x1 / 1000 * W, y1 / 1000 * H)
    c = COLORS[i % len(COLORS)]
    draw.rectangle(px, outline=c, width=10)
    tag = f'{v["article_code"]} {v["object"]}'
    ty = max(0, px[1] - 58)
    tb = draw.textbbox((px[0], ty), tag, font=font)
    draw.rectangle(tb, fill=c)
    draw.text((px[0], ty), tag, fill="white", font=font)
    print(f'{i+1}. [{v["confidence"]:.2f}] {v["article_code"]} {v["object"]} — {v["label"]}  box={v["box_2d"]}')

img.save(OUT, quality=88)
print(f"[{MODEL}] → {OUT.name}")
