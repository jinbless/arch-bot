#!/usr/bin/env python3
"""Gold tiebreak(A) — 충돌 770건의 disputed 조를 gpt-5.4가 조문 전문 대조로 판정(Batch API).

입력: tiebreak_cases.jsonl(adjudicate_gold --mode split 산출). 케이스당 1요청(disputed 조 전부 판정).
출력: tiebreak_verdicts.jsonl ({case_id, code, applies, reason, by_model}) → adjudicate_gold --mode merge 입력.

모드: build → submit → (24h) → collect. PG 불요(로컬 jsonl만). 키는 .env 자동 로드.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
TIEBREAK = ART / "tiebreak_cases.jsonl"
BATCH_JSONL = ART / "tiebreak_gpt_batch.jsonl"
META = ART / "tiebreak_gpt_meta.json"
VERDICTS = ART / "tiebreak_verdicts.jsonl"
MODEL = os.environ.get("LLM_JUDGE_MODEL", "gpt-5.4")

SYS = ("너는 대한민국 산업안전보건 전문가다. 작업장 '장면 서술'과 '후보 조(전문)'를 받는다. "
       "각 후보 조가 그 장면에서 관찰된 위험의 위반으로 성립하는지 조문 근거로 판정하라. "
       "applies: yes(직접 명백한 위반)/maybe(정황 필요)/no(장면과 무관). reason 한 줄(한국어). 모든 후보 조를 빠짐없이.")

SCHEMA = {"name": "verdicts", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]},
            "reason": {"type": "string"}}, "required": ["article_code", "applies", "reason"]}}},
    "required": ["verdicts"]}}


def _ensure_key():
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


def _cases():
    return [json.loads(l) for l in TIEBREAK.read_text(encoding="utf-8").splitlines() if l.strip()]


def build():
    n = 0
    with BATCH_JSONL.open("w", encoding="utf-8") as f:
        for c in _cases():
            disputed = c.get("disputed") or []
            if not disputed:
                continue
            lines = [f"[장면]\n{c.get('scene','')}", "", "[후보 조 (전문)]"]
            for d in disputed:
                lines.append(f"- {d['code']} {d.get('title','')}\n  {(d.get('full') or '')[:400]}")
            user = "\n".join(lines) + "\n\n위 후보 조를 모두 판정하라."
            req = {"custom_id": c["case_id"], "method": "POST", "url": "/v1/chat/completions", "body": {
                "model": MODEL, "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
                "response_format": {"type": "json_schema", "json_schema": SCHEMA}}}
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
            n += 1
    print(f"tiebreak 요청 {n}건 → {BATCH_JSONL.name} (model={MODEL})")


def submit():
    _ensure_key()
    from openai import OpenAI
    client = OpenAI()
    up = client.files.create(file=BATCH_JSONL.open("rb"), purpose="batch")
    b = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions",
                              completion_window="24h", metadata={"task": "gold_tiebreak"})
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
    n = 0
    with VERDICTS.open("w", encoding="utf-8") as f:
        for line in client.files.content(b.output_file_id).text.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            cid = row.get("custom_id")
            try:
                data = json.loads(row["response"]["body"]["choices"][0]["message"]["content"])
            except Exception:  # noqa: BLE001
                continue
            for v in data.get("verdicts") or []:
                f.write(json.dumps({"case_id": cid, "code": v["article_code"],
                                    "applies": v.get("applies"), "reason": v.get("reason", ""),
                                    "by_model": MODEL}, ensure_ascii=False) + "\n")
                n += 1
    print(f"verdicts {n} → {VERDICTS.name}  (다음: adjudicate_gold.py --mode merge --verdicts {VERDICTS})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["build", "submit", "collect"])
    args = ap.parse_args()
    {"build": build, "submit": submit, "collect": collect}[args.mode]()


if __name__ == "__main__":
    main()
