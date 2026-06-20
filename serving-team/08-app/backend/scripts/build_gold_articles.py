#!/usr/bin/env python3
"""Step G — 독립 정답지(gold) 빌더: GPT 인식 장면 → 산업안전보건규칙 "조"를 전체 규칙서에서 직접 선택.

시스템(focused/broad)과 **독립적으로** gpt-5.4가 정답 조를 고른다. 비용 절감 위해 2-stage:
  S1 (recall, 제목)  : 장면 + RULE 656조 제목 목록 → 위반 성립 가능 조 shortlist(~12).
  S2 (precision, 전문): 장면 + S1 shortlist의 조문 전문 → 각 조 applies(yes/maybe/no)+reason.
gold[case] = applies==yes 조 집합(+maybe 소프트). 출력 gold_articles.jsonl.

입력은 synthetic_observations_v*.jsonl의 photo_description + visual_cues(=GPT가 인식한 장면).
expected_primary_risk(큐레이터 정답라벨)는 **주지 않음** — 순수 "보이는 장면 → 조" 판정.

모드: sync(샘플 즉시, 2-stage 루프). batch 2-round는 후속.
사용: OPENAI_API_KEY/.env 자동 → python scripts/build_gold_articles.py --mode sync --sample 200
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgArticle  # noqa: E402
from judge_sr_article_mapping import _ensure_openai_key, JUDGE_MODEL  # noqa: E402

EVAL_DIR = REPO / "data-team" / "05-enrichment" / "eval-data"
ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_OUT = ARTIFACTS / "gold_articles.jsonl"

S1_SYS = (
    "너는 대한민국 산업안전보건 전문가다. 작업장 사진을 GPT가 인식한 '장면 서술'을 보고, "
    "아래 '산업안전보건규칙' 조 목록(제목)에서 그 장면에 관찰된 위험을 예방·조치하지 않았을 때 "
    "위반이 성립할 수 있는 조를 모두 고르라. 보수적으로(직접 관련만) 최대 12개, 코드만(예: 제42조)."
)
S2_SYS = (
    "너는 대한민국 산업안전보건 전문가다. 장면 서술과 후보 조(전문 포함)를 보고, 각 후보 조가 그 "
    "장면의 관찰된 위험에 실제로 해당하는 위반인지 조문 근거로 판정하라. applies: yes(직접 해당)/"
    "maybe(정황 추가 필요)/no(장면과 무관). reason은 한 줄(한국어)."
)
S1_SCHEMA = {
    "name": "article_shortlist", "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {"candidate_codes": {"type": "array", "items": {"type": "string"}}},
        "required": ["candidate_codes"],
    },
}
S2_SCHEMA = {
    "name": "article_gold_verdicts", "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "article_code": {"type": "string"},
                        "applies": {"type": "string", "enum": ["yes", "maybe", "no"]},
                        "reason": {"type": "string"},
                    },
                    "required": ["article_code", "applies", "reason"],
                },
            }
        },
        "required": ["verdicts"],
    },
}


def load_cases(limit=None, positive_only=False, sample=None, seed=13) -> list[dict]:
    cases = []
    for p in sorted(EVAL_DIR.glob("synthetic_observations_v*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if positive_only:
        cases = [c for c in cases if c.get("case_type") == "positive"]
    if sample and sample < len(cases):
        by_wc = defaultdict(list)
        rnd = random.Random(seed)
        for c in cases:
            by_wc[c.get("work_context") or "?"].append(c)
        for v in by_wc.values():
            rnd.shuffle(v)
        picked, buckets, i = [], list(by_wc.values()), 0
        while len(picked) < sample and any(buckets):
            b = buckets[i % len(buckets)]
            if b:
                picked.append(b.pop())
            i += 1
            if i > sample * 50:
                break
        cases = picked
    if limit:
        cases = cases[:limit]
    return cases


def load_articles(db) -> tuple[str, dict]:
    rows = db.query(PgArticle.article_code, PgArticle.title, PgArticle.full_text).filter(
        PgArticle.law_type == "RULE", PgArticle.deleted == False  # noqa: E712
    ).all()
    rows = sorted(rows, key=lambda r: (len(r[0]), r[0]))  # 제N조 대략 번호순
    titles_block = "\n".join(f"{c} {t or ''}" for c, t, _ in rows)
    fulltext = {c: (ft or "") for c, t, ft in rows}
    return titles_block, fulltext


def scene_text(case: dict) -> str:
    parts = [case.get("photo_description", "")]
    vc = case.get("visual_cues") or []
    if vc:
        parts.append("시각 단서: " + " / ".join(vc))
    return "\n".join(p for p in parts if p)


def s1_body(scene: str, titles_block: str) -> dict:
    return {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": S1_SYS},
            {"role": "user", "content": f"[장면]\n{scene}\n\n[산업안전보건규칙 조 목록]\n{titles_block}"},
        ],
        "response_format": {"type": "json_schema", "json_schema": S1_SCHEMA},
    }


def s2_body(scene: str, codes: list[str], fulltext: dict) -> dict:
    blocks = [f"{c} 전문:\n{(fulltext.get(c) or '')[:600]}" for c in codes]
    return {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": S2_SYS},
            {"role": "user", "content": f"[장면]\n{scene}\n\n[후보 조]\n" + "\n\n".join(blocks)},
        ],
        "response_format": {"type": "json_schema", "json_schema": S2_SCHEMA},
    }


def run_sync(args, db) -> int:
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    titles_block, fulltext = load_articles(db)
    cases = load_cases(limit=args.limit, positive_only=args.positive_only, sample=args.sample)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.resume and out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["case_id"])
            except Exception:  # noqa: BLE001
                pass
    print(f"gold builder: {len(cases)} 케이스 (model={JUDGE_MODEL}, 조 {len(fulltext)}) → {out}")
    n = 0
    with out.open("a" if args.resume else "w", encoding="utf-8") as f:
        for i, case in enumerate(cases):
            cid = case.get("case_id")
            if cid in done:
                continue
            if i % 20 == 0:
                print(f"  [{i}/{len(cases)}] {cid}", flush=True)
            scene = scene_text(case)
            try:
                r1 = client.chat.completions.create(**s1_body(scene, titles_block))
                cands = json.loads(r1.choices[0].message.content).get("candidate_codes") or []
                cands = [c for c in cands if c in fulltext][:15]
                verds = []
                if cands:
                    r2 = client.chat.completions.create(**s2_body(scene, cands, fulltext))
                    verds = json.loads(r2.choices[0].message.content).get("verdicts") or []
                rec = {
                    "case_id": cid, "case_type": case.get("case_type"),
                    "work_context": case.get("work_context"), "industry_context": case.get("industry_context"),
                    "candidate_codes": cands,
                    "gold_codes": [v["article_code"] for v in verds if v.get("applies") == "yes"],
                    "maybe_codes": [v["article_code"] for v in verds if v.get("applies") == "maybe"],
                    "verdicts": verds,
                }
            except Exception as exc:  # noqa: BLE001
                rec = {"case_id": cid, "error": repr(exc)[:200]}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
    print(f"DONE — {n} gold 레코드 → {out}")
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["sync"], default="sync", help="sync(2-stage 루프). batch는 후속.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--positive-only", action="store_true")
    ap.add_argument("--sample", type=int, default=None, help="work_context 층화 샘플 N")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--resume", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        return run_sync(args, db)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
