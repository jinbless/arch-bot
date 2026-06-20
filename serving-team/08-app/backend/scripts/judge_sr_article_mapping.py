#!/usr/bin/env python3
"""Step 2 — LLM-judge: GPT 인식 장면 → SR → 산업안전보건규칙 "조" 매핑 타당성 검증.

`dump_synthetic_sr_articles.py`(Step 0)의 dump(케이스별 photo_description + focused/broad SR + 조)를
입력으로, 강한 GPT 모델(`gpt-5.4`)이 각 후보 SR/조가 그 장면에서 **성립하는 위반인지**를 판정한다.
focused vs broad를 분리 집계해 정밀도/과태깅을 정량화한다. 서빙/온톨로지 무변경(검증 전용).

모드(--mode):
  mock    OpenAI 미호출 — focused→correct/broad-only→wrong 휴리스틱으로 스키마·집계 검증(키 불요).
  sync    동기 호출(소량, 프롬프트 튜닝). 키 필요.
  build   Batch API 요청 JSONL 생성(케이스당 1요청). 키 불요.
  submit  build 산출 JSONL 업로드 + batch job 생성 → batch_id 기록. 키 필요.
  collect batch 결과 다운로드·파싱·집계 리포트. 키 필요.

판정은 SR을 set(focused/broad) 모르게 **blind**로 받아 편향을 줄이고, 집계 시 dump의 멤버십으로 분리한다.

사용 예:
  python scripts/judge_sr_article_mapping.py --mode mock --limit 5
  python scripts/judge_sr_article_mapping.py --mode build --positive-only --sample 200 --out-jsonl batch.jsonl
  OPENAI_API_KEY=... python scripts/judge_sr_article_mapping.py --mode submit --out-jsonl batch.jsonl
  OPENAI_API_KEY=... python scripts/judge_sr_article_mapping.py --mode collect
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from app.db.models import PgSafetyRequirement  # noqa: E402
from _mapping_review_common import _sr_articles  # noqa: E402

ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_DUMP = ARTIFACTS / "synthetic_sr_article_dump.jsonl"
DEFAULT_BATCH_JSONL = ARTIFACTS / "judge_sr_article_batch.jsonl"
BATCH_META = ARTIFACTS / "judge_sr_article_batch_meta.json"
REPORT_JSON = ARTIFACTS / "judge_sr_article_mapping.json"
REPORT_MD = ARTIFACTS / "judge_sr_article_mapping.md"
JUDGE_MODEL = os.environ.get("LLM_JUDGE_MODEL", "gpt-5.4")
LOW_CONF = 0.6  # edge 큐 임계


def _ensure_openai_key() -> None:
    """OPENAI_API_KEY가 env에 없으면 .env에서 로드(submit/collect 전용). 값은 출력하지 않음."""
    if os.environ.get("OPENAI_API_KEY"):
        return
    for envf in (BACKEND / ".env", BACKEND.parent / ".env"):
        if not envf.exists():
            continue
        for line in envf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["OPENAI_API_KEY"] = val
                    return

SYS_PROMPT = (
    "너는 대한민국 산업안전보건 전문가다. 입력으로 (1) GPT가 사진을 인식한 '장면 서술'과 "
    "(2) 시스템이 그 장면에 매핑한 '산업안전보건규칙 조항(SR→조)' 후보 목록을 받는다. "
    "각 후보 SR에 대해, 장면에서 관찰된 위험을 예방·조치하지 않았을 때 해당 조(제N조) 위반이 "
    "성립하는지 조문(full_text)과 장면 단서를 근거로 판정하라.\n"
    "label 기준: correct=장면 위험에 직접 해당하는 명백한 위반 / plausible=관련은 있으나 직접 위반 "
    "단정엔 추가 정황 필요 / wrong=장면과 무관하거나 과도하게 끌어온 조(과태깅).\n"
    "각 판정에 confidence(0~1)와 한 줄 reason(한국어). 더 적절한 조가 있으면 suggested_articles에 "
    "'제N조' 형식으로(없으면 빈 배열). 입력에 준 모든 SR을 빠짐없이 판정하라."
)

JUDGE_SCHEMA = {
    "name": "sr_article_verdicts",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "sr_id": {"type": "string"},
                        "label": {"type": "string", "enum": ["correct", "plausible", "wrong"]},
                        "confidence": {"type": "number"},
                        "reason": {"type": "string"},
                        "suggested_articles": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["sr_id", "label", "confidence", "reason", "suggested_articles"],
                },
            }
        },
        "required": ["verdicts"],
    },
}


# ── 입력 로딩 / 후보 강화 ──────────────────────────────────────────────────

def load_dump(path: Path, limit=None, positive_only=False, sample=None, seed=13) -> list[dict]:
    recs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("error"):
            continue
        if positive_only and d.get("case_type") != "positive":
            continue
        recs.append(d)
    if sample and sample < len(recs):
        # work_context 기준 층화 샘플(균등 라운드로빈).
        by_wc: dict[str, list] = defaultdict(list)
        rnd = random.Random(seed)
        for r in recs:
            by_wc[r.get("work_context") or "?"].append(r)
        for v in by_wc.values():
            rnd.shuffle(v)
        picked, buckets = [], list(by_wc.values())
        i = 0
        while len(picked) < sample and any(buckets):
            b = buckets[i % len(buckets)]
            if b:
                picked.append(b.pop())
            i += 1
            if i > sample * 50:
                break
        recs = picked
    if limit:
        recs = recs[:limit]
    return recs


def candidate_sets(rec: dict) -> tuple[list[str], set, set]:
    foc = [c["sr_id"] for c in rec.get("focused") or []]
    bro = [c["sr_id"] for c in rec.get("broad") or []]
    union, seen = [], set()
    for s in foc + bro:
        if s not in seen:
            seen.add(s)
            union.append(s)
    return union, set(foc), set(bro)


def enrich(db, sr_ids: list[str]) -> dict[str, dict]:
    if not sr_ids:
        return {}
    arts = _sr_articles(db, sr_ids)
    titles = {}
    for r in db.query(
        PgSafetyRequirement.identifier, PgSafetyRequirement.title, PgSafetyRequirement.text
    ).filter(PgSafetyRequirement.identifier.in_(list(set(sr_ids)))).all():
        titles[r[0]] = (r[1] or "", r[2] or "")
    out = {}
    for s in sr_ids:
        a = arts.get(s) or {}
        t = titles.get(s, ("", ""))
        out[s] = {
            "sr_id": s,
            "sr_title": t[0],
            "sr_text": t[1][:200],
            "article_code": a.get("article_code", ""),
            "article_title": a.get("title", ""),
            "article_full_text": (a.get("full_text") or "")[:400],
        }
    return out


def build_user_prompt(rec: dict, cands: list[dict]) -> str:
    lines = [f"[장면 서술] {rec.get('photo_description', '')}"]
    vc = rec.get("visual_cues") or []
    if vc:
        lines.append("[시각 단서] " + " / ".join(vc))
    if rec.get("expected_primary_risk"):
        lines.append(f"[정답 핵심위험(참고)] {rec['expected_primary_risk']}")
    lines.append("\n[판정 대상 — 시스템이 매핑한 산업안전보건규칙 조 후보]")
    for i, c in enumerate(cands, 1):
        lines.append(
            f"{i}. SR={c['sr_id']} | {c['article_code']} {c['article_title']} | SR제목: {c['sr_title']}"
        )
        if c["article_full_text"]:
            lines.append(f"   조문: {c['article_full_text']}")
    lines.append("\n위 모든 SR을 빠짐없이 verdicts 배열로 판정하라.")
    return "\n".join(lines)


def build_body(rec: dict, cands: list[dict]) -> dict:
    return {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": build_user_prompt(rec, cands)},
        ],
        "response_format": {"type": "json_schema", "json_schema": JUDGE_SCHEMA},
    }


# ── 판정 실행 모드 ────────────────────────────────────────────────────────

def mock_verdicts(cands: list[dict], focused: set) -> list[dict]:
    """키 없이 집계 파이프 검증: focused→correct(0.8), broad-only→wrong(0.55)."""
    out = []
    for c in cands:
        in_f = c["sr_id"] in focused
        out.append({
            "sr_id": c["sr_id"],
            "label": "correct" if in_f else "wrong",
            "confidence": 0.8 if in_f else 0.55,
            "reason": "[mock] focused 후보" if in_f else "[mock] broad-only 과태깅 추정",
            "suggested_articles": [],
        })
    return out


def parse_verdicts(content: str) -> list[dict]:
    data = json.loads(content)
    return data.get("verdicts") or []


def sync_judge(client, rec: dict, cands: list[dict]) -> list[dict]:
    body = build_body(rec, cands)
    resp = client.chat.completions.create(**body)
    return parse_verdicts(resp.choices[0].message.content)


# ── 집계 ─────────────────────────────────────────────────────────────────

def aggregate(judged: list[dict]) -> dict:
    """judged: [{case_id, case_type, work_context, focused:set, broad:set, verdicts:{sr_id:verdict}, cand_meta:{sr_id:{article_code}}}]."""
    foc = Counter()        # label -> n (focused 소속 SR)
    bro_only = Counter()   # label -> n (broad-only SR)
    both = Counter()
    wrong_articles = Counter()
    plausible_articles = Counter()
    edges = []
    per_case = []
    for j in judged:
        v = j["verdicts"]
        focused, broad = j["focused"], j["broad"]
        c_foc = Counter(); c_bro_only = Counter()
        for sid, vd in v.items():
            label = vd.get("label", "wrong")
            in_f, in_b = sid in focused, sid in broad
            art = (j["cand_meta"].get(sid) or {}).get("article_code", "")
            if in_f and in_b:
                both[label] += 1
            if in_f:
                foc[label] += 1; c_foc[label] += 1
            if in_b and not in_f:
                bro_only[label] += 1; c_bro_only[label] += 1
            if label == "wrong":
                wrong_articles[art] += 1
            elif label == "plausible":
                plausible_articles[art] += 1
            if label != "correct" or float(vd.get("confidence", 1.0)) < LOW_CONF:
                edges.append({
                    "case_id": j["case_id"], "sr_id": sid, "article_code": art,
                    "set": "focused" if in_f else "broad", "label": label,
                    "confidence": vd.get("confidence"), "reason": vd.get("reason", ""),
                    "suggested_articles": vd.get("suggested_articles") or [],
                })
        per_case.append({
            "case_id": j["case_id"], "case_type": j["case_type"], "work_context": j.get("work_context"),
            "focused_correct": c_foc["correct"], "focused_total": sum(c_foc.values()),
            "broad_only_wrong": c_bro_only["wrong"], "broad_only_total": sum(c_bro_only.values()),
        })

    def prec(c):
        d = c["correct"] + c["wrong"] + c["plausible"]
        return round(c["correct"] / d, 4) if d else None

    foc_total = sum(foc.values())
    bro_only_total = sum(bro_only.values())
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": JUDGE_MODEL,
        "n_cases": len(judged),
        "focused": {
            "labels": dict(foc), "total": foc_total,
            "precision": prec(foc),
            "correct_rate": round(foc["correct"] / foc_total, 4) if foc_total else None,
        },
        "broad_only": {
            "labels": dict(bro_only), "total": bro_only_total,
            "overtag_rate": round(bro_only["wrong"] / bro_only_total, 4) if bro_only_total else None,
            "precision": prec(bro_only),
        },
        "both": dict(both),
        "top_wrong_articles": wrong_articles.most_common(15),
        "top_plausible_articles": plausible_articles.most_common(10),
        "n_edges": len(edges),
        "edges": edges,
        "per_case": per_case,
    }


def write_report(agg: dict, edges_out: Path):
    REPORT_JSON.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    f = agg["focused"]; b = agg["broad_only"]
    md = [
        f"# SR→조 매핑 LLM-judge 리포트 ({agg['model']})",
        f"- 생성: {agg['generated_at']} · 케이스 {agg['n_cases']}",
        "",
        "## focused (situation_matches.applies_sr_ids — 정밀 후보)",
        f"- 총 {f['total']} · **precision {f['precision']}** · labels {f['labels']}",
        "",
        "## broad-only (findings.sr_ids 中 focused 제외 — 과태깅 의심)",
        f"- 총 {b['total']} · **과태깅율(wrong) {b['overtag_rate']}** · labels {b['labels']}",
        "",
        "## 가장 많이 wrong 판정된 조 (top 15)",
    ]
    md += [f"- {code or '(no article)'}: {n}" for code, n in agg["top_wrong_articles"]]
    md += ["", f"## edge 큐: {agg['n_edges']}건 (wrong/plausible/low-conf) → {edges_out.name}"]
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")
    # edge 큐 별도 jsonl(사람 확정 입력).
    edges_out.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in agg["edges"]) + ("\n" if agg["edges"] else ""),
        encoding="utf-8",
    )
    print(f"리포트 → {REPORT_MD}\n  focused precision={f['precision']} · broad-only overtag={b['overtag_rate']} · edges={agg['n_edges']}")


# ── 모드 디스패치 ─────────────────────────────────────────────────────────

def _judged_from(db, recs, verdict_fn) -> list[dict]:
    judged = []
    for rec in recs:
        union, focused, broad = candidate_sets(rec)
        if not union:
            continue
        meta = enrich(db, union)
        cands = [meta[s] for s in union]
        verdicts = {v["sr_id"]: v for v in verdict_fn(rec, cands, focused)}
        judged.append({
            "case_id": rec["case_id"], "case_type": rec.get("case_type"),
            "work_context": rec.get("work_context"),
            "focused": focused, "broad": broad, "cand_meta": meta, "verdicts": verdicts,
        })
    return judged


def run_local(args, db, recs, use_api: bool):
    if use_api:
        from openai import OpenAI
        client = OpenAI()
        fn = lambda rec, cands, foc: sync_judge(client, rec, cands)  # noqa: E731
    else:
        fn = lambda rec, cands, foc: mock_verdicts(cands, foc)  # noqa: E731
    judged = _judged_from(db, recs, fn)
    agg = aggregate(judged)
    write_report(agg, Path(args.edges_out))


def run_build(args, db, recs):
    out = Path(args.out_jsonl)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for rec in recs:
            union, _, _ = candidate_sets(rec)
            if not union:
                continue
            meta = enrich(db, union)
            cands = [meta[s] for s in union]
            req = {
                "custom_id": rec["case_id"],
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": build_body(rec, cands),
            }
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
            n += 1
    print(f"batch 요청 {n}건 → {out} (모델 {JUDGE_MODEL}). 다음: --mode submit --out-jsonl {out}")


def run_submit(args):
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    out = Path(args.out_jsonl)
    up = client.files.create(file=out.open("rb"), purpose="batch")
    batch = client.batches.create(
        input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h",
        metadata={"task": "sr_article_judge"},
    )
    BATCH_META.write_text(json.dumps({
        "batch_id": batch.id, "input_file_id": up.id, "jsonl": str(out),
        "submitted_at": datetime.now().isoformat(timespec="seconds"), "model": JUDGE_MODEL,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"submitted batch_id={batch.id} status={batch.status} → meta {BATCH_META}\n  완료 후: --mode collect")


def run_collect(args, db):
    _ensure_openai_key()
    from openai import OpenAI
    client = OpenAI()
    batch_id = args.batch_id or json.loads(BATCH_META.read_text(encoding="utf-8"))["batch_id"]
    batch = client.batches.retrieve(batch_id)
    print(f"batch {batch_id} status={batch.status} ({batch.request_counts})")
    if batch.status != "completed":
        print("아직 완료 아님. 나중에 다시 --mode collect.")
        return
    content = client.files.content(batch.output_file_id).text
    # custom_id → verdicts
    by_case = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cid = row.get("custom_id")
        try:
            msg = row["response"]["body"]["choices"][0]["message"]["content"]
            by_case[cid] = parse_verdicts(msg)
        except Exception:  # noqa: BLE001
            by_case[cid] = []
    # dump 재로딩(멤버십/메타) + verdicts 결합
    recs = {r["case_id"]: r for r in load_dump(Path(args.input))}
    judged = []
    for cid, verdicts in by_case.items():
        rec = recs.get(cid)
        if not rec:
            continue
        union, focused, broad = candidate_sets(rec)
        meta = enrich(db, union)
        judged.append({
            "case_id": cid, "case_type": rec.get("case_type"), "work_context": rec.get("work_context"),
            "focused": focused, "broad": broad, "cand_meta": meta,
            "verdicts": {v["sr_id"]: v for v in verdicts},
        })
    agg = aggregate(judged)
    write_report(agg, Path(args.edges_out))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["mock", "sync", "build", "submit", "collect"], default="mock")
    ap.add_argument("--input", default=str(DEFAULT_DUMP), help="Step 0 dump jsonl")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--positive-only", action="store_true")
    ap.add_argument("--sample", type=int, default=None, help="work_context 층화 샘플 N건")
    ap.add_argument("--out-jsonl", default=str(DEFAULT_BATCH_JSONL), help="build/submit batch 요청 파일")
    ap.add_argument("--edges-out", default=str(ARTIFACTS / "judge_sr_article_edges.jsonl"))
    ap.add_argument("--batch-id", default=None, help="collect 시 batch_id 직접 지정(없으면 meta에서)")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "submit":
        run_submit(args)
        return 0
    db = SessionLocal()
    try:
        if args.mode in ("mock", "sync", "build"):
            recs = load_dump(Path(args.input), limit=args.limit,
                             positive_only=args.positive_only, sample=args.sample)
            print(f"로딩 {len(recs)} 케이스 (mode={args.mode}, model={JUDGE_MODEL})")
            if args.mode == "build":
                run_build(args, db, recs)
            else:
                run_local(args, db, recs, use_api=(args.mode == "sync"))
        elif args.mode == "collect":
            run_collect(args, db)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
