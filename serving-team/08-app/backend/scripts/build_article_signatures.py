#!/usr/bin/env python3
"""OWA→CWA 1+2단계 — 산업안전보건규칙 조문(닫힌세계)을 '관찰 시그니처'로 변환.

배경: 사진 위험→조문 매핑 실패의 근본은 사진 *관찰언어* ↔ 조문 *법조문체* 간극.
해법: 각 조문을 (a) 사진에서 시각 탐지 가능한지 분류, (b) 가능하면 '사진에서 무엇이
보여야 그 위반인지'를 관찰 언어로 시그니처화. 핵심 산출 violation_scene(위반 사진 묘사)이
임베딩 타깃 → 사진 장면 서술과 같은 언어 공간에서 매칭(retrieve 천장 소멸).

닫힌세계는 유한(653조) → LLM batch 생성 + 사람 spot-check로 검수 닫힘.

모드: build → submit → (batch) → collect.
  build   PG에서 RULE 조문 전문 읽어 조당 1요청 JSONL 생성(키 불요).
  submit  업로드 + batch job 생성 → batch_id 기록(키 필요).
  collect 결과 다운로드·파싱 → article_signatures.jsonl(키 필요).

사용: .venv/bin/python scripts/build_article_signatures.py --mode build
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
BATCH_JSONL = ART / "article_sig_batch.jsonl"
META = ART / "article_sig_meta.json"
OUT = ART / "article_signatures.jsonl"
MODEL = os.environ.get("ARTICLE_SIG_MODEL", "gpt-5.4")

SYS = (
    "너는 대한민국 산업안전보건규칙 전문가이자 현장 안전점검관이다. "
    "산업안전보건규칙 조문 한 개(제목+전문)를 받는다. 목표는 이 조문을 '작업장 사진 한 장에서 "
    "위반을 시각적으로 탐지'할 수 있는 형태(관찰 시그니처)로 변환하는 것이다.\n"
    "다음을 판정·생성하라.\n"
    "1) observable: 사진 한 장(정지영상)에서 이 조문 위반을 탐지할 수 있는가?\n"
    "   - yes: 위반 상태가 직접 보임(예: 안전난간 없는 개구부, 방호장치 없는 회전체, 안전대 미착용).\n"
    "   - partial: 일부 시각 단서는 있으나 핵심은 절차·측정·점검주기 등(사진만으론 불확실).\n"
    "   - no: 순수 행정·교육·자격·기록·작업계획·신고 등 사진으로 볼 수 없음.\n"
    "2) context: 이 조문이 적용되는 작업/설비/장소 맥락을 '관찰 언어'로 1~2문장.\n"
    "3) equipment: 관련 설비·기계·작업·장소 키워드(짧은 명사, 정규화/매칭 신호용).\n"
    "4) visual_cues: 사진에서 '위반'으로 보이는 시각 징후(짧은 구). observable=no면 빈 배열.\n"
    "5) required_measures: 이 조문이 요구하는 안전조치(법정·표준 어휘. 예: 작업발판, 추락방호망, "
    "안전대 부착설비, 방호장치, 덮개, 울, 접지). 결여 시 위반 신호가 된다.\n"
    "6) violation_scene: '이 조문을 위반한 작업장 사진은 이렇게 보인다'를 1~2문장의 평서문으로. "
    "법조문체 금지, 사진 설명문처럼. observable=no면 빈 문자열.\n"
    "추측 금지. 조문 근거로만. 한국어."
)

SCHEMA = {
    "name": "article_signature",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "observable": {"type": "string", "enum": ["yes", "partial", "no"]},
            "observable_reason": {"type": "string"},
            "context": {"type": "string"},
            "equipment": {"type": "array", "items": {"type": "string"}},
            "visual_cues": {"type": "array", "items": {"type": "string"}},
            "required_measures": {"type": "array", "items": {"type": "string"}},
            "violation_scene": {"type": "string"},
        },
        "required": [
            "observable", "observable_reason", "context", "equipment",
            "visual_cues", "required_measures", "violation_scene",
        ],
    },
}


def _ensure_key() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        return
    for envf in (BACKEND / ".env", BACKEND.parent / ".env"):
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        os.environ["OPENAI_API_KEY"] = v
                        return


def _articles():
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "select article_code, title, coalesce(section,'') section, full_text "
            "from articles where law_type='RULE' and not deleted and length(full_text)>10 "
            "order by article_code"
        )).fetchall()
    finally:
        db.close()
    return [{"code": r[0], "title": r[1], "section": r[2], "full": r[3]} for r in rows]


def build():
    arts = _articles()
    n = 0
    with BATCH_JSONL.open("w", encoding="utf-8") as f:
        for a in arts:
            user = (
                f"[조문] {a['code']} {a['title']}\n"
                f"[분류(편/장/절/관)] {a['section']}\n"
                f"[전문]\n{a['full'][:2500]}\n\n"
                "위 조문을 관찰 시그니처로 변환하라."
            )
            req = {
                "custom_id": a["code"],
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYS},
                        {"role": "user", "content": user},
                    ],
                    "response_format": {"type": "json_schema", "json_schema": SCHEMA},
                },
            }
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
            n += 1
    print(f"조문 시그니처 요청 {n}건 → {BATCH_JSONL.name} (model={MODEL})")


def submit():
    _ensure_key()
    from openai import OpenAI
    client = OpenAI()
    up = client.files.create(file=BATCH_JSONL.open("rb"), purpose="batch")
    b = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions",
                              completion_window="24h", metadata={"task": "article_signatures"})
    META.write_text(json.dumps({"batch_id": b.id, "model": MODEL}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"submitted batch_id={b.id} status={b.status} → {META.name}")


def collect():
    _ensure_key()
    from openai import OpenAI
    client = OpenAI()
    bid = json.loads(META.read_text(encoding="utf-8"))["batch_id"]
    b = client.batches.retrieve(bid)
    print(f"batch {bid} status={b.status} ({b.request_counts})")
    if b.status != "completed":
        print("아직 완료 아님 — 나중에 다시 collect.")
        return
    # 조문 메타(section/title) 재첨부용
    meta = {a["code"]: a for a in _articles()}
    n = 0
    counts = {"yes": 0, "partial": 0, "no": 0}
    with OUT.open("w", encoding="utf-8") as f:
        for line in client.files.content(b.output_file_id).text.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            code = row.get("custom_id")
            try:
                data = json.loads(row["response"]["body"]["choices"][0]["message"]["content"])
            except Exception:  # noqa: BLE001
                continue
            m = meta.get(code, {})
            obs = data.get("observable", "no")
            counts[obs] = counts.get(obs, 0) + 1
            rec = {
                "article_code": code,
                "title": m.get("title", ""),
                "section": m.get("section", ""),
                "observable": obs,
                "observable_reason": data.get("observable_reason", ""),
                "context": data.get("context", ""),
                "equipment": data.get("equipment", []),
                "visual_cues": data.get("visual_cues", []),
                "required_measures": data.get("required_measures", []),
                "violation_scene": data.get("violation_scene", ""),
                "by_model": MODEL,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"signatures {n} → {OUT.name}  관찰성 분포: {counts}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["build", "submit", "collect"])
    args = ap.parse_args()
    {"build": build, "submit": submit, "collect": collect}[args.mode]()


if __name__ == "__main__":
    main()
