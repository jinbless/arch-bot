#!/usr/bin/env python3
"""gpt-5.4 장(章) 기반 독립 gold — Claude와 동일 기준, Batch API 2-round.

S1: scene + 32 장 목록 → 관련 장 multi-label.   S2: scene + 그 장들의 조문 전문 → applies(yes/maybe/no).
gold = applies==yes. Claude gold와 consensus/disagreement 비교용 2nd annotator.

모드(--mode):
  s1-build   S1 요청 JSONL 생성(케이스당 1).
  s1-submit  S1 batch 제출 → batch_id 기록.
  s1-collect S1 결과 → gpt_gold_s1.jsonl (case_id→chapters).
  s2-build   S1 결과로 S2 요청 JSONL 생성(scene + 선택 장 조문).
  s2-submit  S2 batch 제출.
  s2-collect S2 결과 → gpt_gold.jsonl.
사용: OPENAI_API_KEY/.env 자동. python scripts/build_gpt_chapter_gold.py --mode s1-build [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from judge_sr_article_mapping import _ensure_openai_key, JUDGE_MODEL  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
CHAPTERS_F = ART / "chapters.tsv"
CAT_F = ART / "articles_by_chapter.tsv"
DEFAULT_CASES = ART / "gold_cases_positive.jsonl"
S1_JSONL = ART / "gpt_gold_s1_batch.jsonl"
S1_OUT = ART / "gpt_gold_s1.jsonl"
S2_JSONL = ART / "gpt_gold_s2_batch.jsonl"
GPT_GOLD = ART / "gpt_gold.jsonl"
META = ART / "gpt_gold_batch_meta.json"

S1_SYS = ("너는 대한민국 산업안전보건 전문가다. 작업장 사진 '장면 서술'을 보고, 아래 산업안전보건규칙 "
          "'장(章)' 목록에서 그 장면의 관찰 위험에 관련된 장을 1~5개 고르라(multi-label, 보통 여러 장에 걸침; "
          "보호구·작업장·통로 등 횡단 장도 근거 있으면 포함). 장 문자열 그대로 반환.")
S2_SYS = ("너는 대한민국 산업안전보건 전문가다. 장면 서술과 후보 조(전문)를 보고, 각 조가 그 장면의 관찰 위험에 "
          "실제로 해당하는 위반인지 조문 근거로 판정하라. applies: yes(직접 명백)/maybe(정황 필요)/no(무관). reason 한 줄.")

S1_SCHEMA = {"name": "chapters", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "properties": {"chapters": {"type": "array", "items": {"type": "string"}}},
    "required": ["chapters"]}}
S2_SCHEMA = {"name": "verdicts", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "properties": {
            "article_code": {"type": "string"}, "applies": {"type": "string", "enum": ["yes", "maybe", "no"]},
            "reason": {"type": "string"}}, "required": ["article_code", "applies", "reason"]}}},
    "required": ["verdicts"]}}


def load_chapters_block() -> str:
    lines = []
    for ln in CHAPTERS_F.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            lines.append(ln.split("\t")[0])
    return "\n".join(lines)


def load_articles_by_chapter() -> dict:
    by = defaultdict(list)
    for ln in CAT_F.read_text(encoding="utf-8").splitlines():
        p = ln.split("\t")
        if len(p) >= 4:
            by[p[0]].append((p[1], p[2], p[3]))
    return by


def load_cases(path: Path, limit=None) -> list[dict]:
    cs = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            cs.append(json.loads(ln))
    return cs[:limit] if limit else cs


def _req(cid, sys_p, user_p, schema):
    return {"custom_id": cid, "method": "POST", "url": "/v1/chat/completions", "body": {
        "model": JUDGE_MODEL, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
        "response_format": {"type": "json_schema", "json_schema": schema}}}


def s1_build(args):
    cases = load_cases(Path(args.cases), args.limit)
    chapters = load_chapters_block()
    with S1_JSONL.open("w", encoding="utf-8") as f:
        for c in cases:
            user = f"[장면]\n{c['scene']}\n\n[산업안전보건규칙 장 목록]\n{chapters}"
            f.write(json.dumps(_req(c["case_id"], S1_SYS, user, S1_SCHEMA), ensure_ascii=False) + "\n")
    print(f"S1 요청 {len(cases)} → {S1_JSONL}")


def s2_build(args):
    s1 = {json.loads(l)["case_id"]: json.loads(l)["chapters"] for l in S1_OUT.read_text(encoding="utf-8").splitlines() if l.strip()}
    by = load_articles_by_chapter()
    cases = {c["case_id"]: c for c in load_cases(Path(args.cases), args.limit)}
    n = 0
    with S2_JSONL.open("w", encoding="utf-8") as f:
        for cid, chs in s1.items():
            if cid not in cases:
                continue
            arts = []
            for ch in chs:
                for code, title, full in by.get(ch, []):
                    arts.append(f"{code} {title}\n  {full[:400]}")
            if not arts:
                continue
            user = f"[장면]\n{cases[cid]['scene']}\n\n[후보 조 전문]\n" + "\n".join(arts[:120])
            f.write(json.dumps(_req(cid, S2_SYS, user, S2_SCHEMA), ensure_ascii=False) + "\n")
            n += 1
    print(f"S2 요청 {n} → {S2_JSONL}")


def _submit(jsonl: Path, tag: str):
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    up = client.files.create(file=jsonl.open("rb"), purpose="batch")
    b = client.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h", metadata={"task": tag})
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta[tag] = {"batch_id": b.id, "jsonl": str(jsonl)}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"submitted {tag} batch_id={b.id} status={b.status}")


def _collect(tag: str):
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    bid = json.loads(META.read_text(encoding="utf-8"))[tag]["batch_id"]
    b = client.batches.retrieve(bid)
    print(f"{tag} batch {bid} status={b.status} ({b.request_counts})")
    if b.status != "completed":
        print("아직 완료 아님 — 나중에 다시 collect."); return None
    out = {}
    for line in client.files.content(b.output_file_id).text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            out[row["custom_id"]] = json.loads(row["response"]["body"]["choices"][0]["message"]["content"])
        except Exception:  # noqa: BLE001
            out[row["custom_id"]] = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True,
                    choices=["s1-build", "s1-submit", "s1-collect", "s2-build", "s2-submit", "s2-collect"])
    ap.add_argument("--cases", default=str(DEFAULT_CASES))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.mode == "s1-build":
        s1_build(args)
    elif args.mode == "s1-submit":
        _submit(S1_JSONL, "s1")
    elif args.mode == "s1-collect":
        res = _collect("s1")
        if res is not None:
            with S1_OUT.open("w", encoding="utf-8") as f:
                for cid, d in res.items():
                    chs = (d or {}).get("chapters") or []
                    f.write(json.dumps({"case_id": cid, "chapters": chs}, ensure_ascii=False) + "\n")
            print(f"S1 → {S1_OUT} ({len(res)})")
    elif args.mode == "s2-build":
        s2_build(args)
    elif args.mode == "s2-submit":
        _submit(S2_JSONL, "s2")
    elif args.mode == "s2-collect":
        res = _collect("s2")
        if res is not None:
            with GPT_GOLD.open("w", encoding="utf-8") as f:
                for cid, d in res.items():
                    vs = (d or {}).get("verdicts") or []
                    f.write(json.dumps({
                        "case_id": cid,
                        "gold_codes": [v["article_code"] for v in vs if v.get("applies") == "yes"],
                        "maybe_codes": [v["article_code"] for v in vs if v.get("applies") == "maybe"],
                    }, ensure_ascii=False) + "\n")
            print(f"gpt gold → {GPT_GOLD} ({len(res)})")


if __name__ == "__main__":
    main()
