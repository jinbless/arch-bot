#!/usr/bin/env python3
"""Gold 확정(A) — Claude×gpt 두 독립 gold의 합의/충돌 분리 + 3차 tiebreak 준비/병합.

두 gold(claude_gold_v2.jsonl, gpt_gold.jsonl)의 공통 case_id에 대해:
- agreed-core = gold_codes 교집합 → 확정 gold(두 주석자 독립 합의).
- disputed   = gold_codes 대칭차 → 3차 모델(+사람)이 조문 전문 대조로 판정할 대상.

모드(--mode):
  split   합의/충돌 분리 → gold_auto.jsonl(확정 core) + tiebreak_cases.jsonl(충돌 케이스+조문).
  merge   tiebreak 판정(gpt/claude) 병합 → final_gold.jsonl + human_residual.jsonl.

split만으로 PG 불요(로컬 jsonl/tsv만). tiebreak 실행은 별도(gpt batch / Claude workflow).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"

CLAUDE = ART / "claude_gold_v2.jsonl"
GPT = ART / "gpt_gold.jsonl"
CASES = ART / "gold_cases_all.jsonl"
CATALOG = ART / "articles_by_chapter.tsv"

GOLD_AUTO = ART / "gold_auto.jsonl"
TIEBREAK = ART / "tiebreak_cases.jsonl"
FINAL_GOLD = ART / "final_gold.jsonl"
HUMAN_RESIDUAL = ART / "human_residual.jsonl"


def _load_jsonl(p: Path) -> dict:
    out = {}
    if not p.exists():
        return out
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            d = json.loads(ln)
            out[d["case_id"]] = d
    return out


def _load_article_text() -> dict:
    """code -> (title, full)."""
    by = {}
    if not CATALOG.exists():
        return by
    for ln in CATALOG.read_text(encoding="utf-8").splitlines():
        p = ln.split("\t")
        if len(p) >= 4:
            by[p[1]] = (p[2], p[3])
    return by


def split(args):
    claude = _load_jsonl(CLAUDE)
    gpt = _load_jsonl(GPT)
    cases = _load_jsonl(CASES)
    atext = _load_article_text()
    shared = sorted(set(claude) & set(gpt))

    n_consensus = n_both_empty = n_exact = n_dispute = 0
    n_disputed_codes = 0
    with GOLD_AUTO.open("w", encoding="utf-8") as fa, TIEBREAK.open("w", encoding="utf-8") as ft:
        for cid in shared:
            c = set(claude[cid].get("gold_codes") or [])
            g = set(gpt[cid].get("gold_codes") or [])
            core = sorted(c & g)
            disputed = sorted(c ^ g)
            fa.write(json.dumps({
                "case_id": cid, "core": core, "consensus": not disputed,
            }, ensure_ascii=False) + "\n")
            if not disputed:
                n_consensus += 1
                if not core:
                    n_both_empty += 1
                else:
                    n_exact += 1
                continue
            n_dispute += 1
            n_disputed_codes += len(disputed)
            scene = (cases.get(cid) or {}).get("scene", "")
            dlist = []
            for code in disputed:
                by = []
                if code in c:
                    by.append("claude")
                if code in g:
                    by.append("gpt")
                t, full = atext.get(code, ("", ""))
                dlist.append({"code": code, "by": by, "title": t, "full": full[:400]})
            ft.write(json.dumps({
                "case_id": cid, "scene": scene, "core": core, "disputed": dlist,
            }, ensure_ascii=False) + "\n")

    print(f"shared={len(shared)}  consensus={n_consensus} (exact={n_exact}, both_empty={n_both_empty})  "
          f"dispute_cases={n_dispute}  disputed_codes={n_disputed_codes}")
    print(f"→ {GOLD_AUTO.name} (확정 core), {TIEBREAK.name} (충돌 {n_dispute}건 tiebreak 입력)")


def merge(args):
    """gold_auto + tiebreak 판정(verdicts jsonl: {case_id, code, applies:yes/no/maybe, by_model}) 병합.

    규칙: final = core ∪ {disputed code: tiebreaker가 yes & (사람 검토 불요 임계)}.
    충돌/저신뢰 → human_residual.
    """
    auto = _load_jsonl(GOLD_AUTO)
    # verdicts: case_id -> {code -> [verdict,...]}
    verdicts: dict = {}
    for vp in args.verdicts:
        for ln in Path(vp).read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            d = json.loads(ln)
            verdicts.setdefault(d["case_id"], {}).setdefault(d["code"], []).append(d)
    tb = _load_jsonl(TIEBREAK)
    n_final = n_resid = 0
    with FINAL_GOLD.open("w", encoding="utf-8") as ff, HUMAN_RESIDUAL.open("w", encoding="utf-8") as fr:
        for cid, a in auto.items():
            gold = set(a.get("core") or [])
            resid = []
            for d in (tb.get(cid, {}) or {}).get("disputed", []):
                code = d["code"]
                vs = verdicts.get(cid, {}).get(code, [])
                yes = sum(1 for v in vs if v.get("applies") == "yes")
                no = sum(1 for v in vs if v.get("applies") == "no")
                if vs and yes == len(vs):
                    gold.add(code)
                elif vs and no == len(vs):
                    pass  # 만장일치 no → drop
                else:
                    resid.append({**d, "verdicts": vs})
            ff.write(json.dumps({"case_id": cid, "gold_codes": sorted(gold)}, ensure_ascii=False) + "\n")
            n_final += 1
            if resid:
                fr.write(json.dumps({"case_id": cid, "scene": (tb.get(cid) or {}).get("scene", ""),
                                     "core": sorted(gold), "residual": resid}, ensure_ascii=False) + "\n")
                n_resid += 1
    print(f"final_gold={n_final} → {FINAL_GOLD.name}  human_residual={n_resid} → {HUMAN_RESIDUAL.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=["split", "merge"])
    ap.add_argument("--verdicts", nargs="*", default=[], help="merge: tiebreak verdict jsonl(들)")
    args = ap.parse_args()
    if args.mode == "split":
        split(args)
    else:
        merge(args)


if __name__ == "__main__":
    main()
