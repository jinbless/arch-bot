#!/usr/bin/env python3
"""Step S — 채점: 시스템 매핑(dump focused/broad 조) vs 독립 gold → precision/recall/F1.

`dump_synthetic_sr_articles.py`(시스템 예측)와 `build_gold_articles.py`(독립 gold)를 case_id로 조인,
시스템의 focused·broad 조 집합을 gold(applies=yes) 대비 채점한다. gold 기준이므로:
- focused/broad **precision** = 시스템이 매핑한 조 중 gold에 든 비율(↔ 과태깅).
- focused/broad **recall**    = gold 조 중 시스템이 잡은 비율(↔ 누락).
- broad recall이 천장(시스템이 닿는 최대), focused는 정밀하나 누락 가능.

산출: 전체 micro P/R/F1(focused·broad) + case_type/work_context 슬라이스 + 가장 많이 누락/과태깅된 조.
사용: python scripts/score_sr_article_mapping.py [--dump ...] [--gold ...] [--include-maybe]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ARTIFACTS = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DEFAULT_DUMP = ARTIFACTS / "synthetic_sr_article_dump.jsonl"
DEFAULT_GOLD = ARTIFACTS / "gold_articles.jsonl"
REPORT_JSON = ARTIFACTS / "score_sr_article_mapping.json"
REPORT_MD = ARTIFACTS / "score_sr_article_mapping.md"


def load_jsonl(p: Path) -> dict[str, dict]:
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("error") or not d.get("case_id"):
            continue
        out[d["case_id"]] = d
    return out


def art_set(items) -> set:
    return {x.get("article_code") for x in (items or []) if x.get("article_code")}


def _prf(tp: int, fp: int, fn: int):
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * p * r / (p + r)) if (p and r) else (0.0 if (tp + fp + fn) else None)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(p, 4) if p is not None else None,
        "recall": round(r, 4) if r is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", default=str(DEFAULT_DUMP))
    ap.add_argument("--gold", default=str(DEFAULT_GOLD))
    ap.add_argument("--include-maybe", action="store_true", help="gold에 maybe도 포함(느슨)")
    args = ap.parse_args()

    dump = load_jsonl(Path(args.dump))
    gold = load_jsonl(Path(args.gold))
    common = sorted(set(dump) & set(gold))
    if not common:
        print(f"교집합 case 0 — dump({len(dump)}) ∩ gold({len(gold)}). dump가 gold 샘플 케이스를 아직 안 담았을 수 있음.")
        return 1

    # micro accumulators
    F = {"tp": 0, "fp": 0, "fn": 0}
    B = {"tp": 0, "fp": 0, "fn": 0}
    by_slice = defaultdict(lambda: {"F": {"tp": 0, "fp": 0, "fn": 0}, "B": {"tp": 0, "fp": 0, "fn": 0}, "n": 0})
    missed_by_broad = Counter()      # gold인데 broad도 못 잡음(진짜 커버리지 갭)
    focused_overtag = Counter()      # focused인데 gold 아님
    broad_overtag = Counter()        # broad인데 gold 아님
    focused_miss = Counter()         # gold인데 focused 놓침
    gold_in_broad = 0
    gold_sizes = []
    per_case = []

    for cid in common:
        g = set(gold[cid].get("gold_codes") or [])
        if args.include_maybe:
            g |= set(gold[cid].get("maybe_codes") or [])
        foc = art_set(dump[cid].get("focused"))
        bro = art_set(dump[cid].get("broad"))
        gold_sizes.append(len(g))
        if g and g <= bro:
            gold_in_broad += 1

        ftp, ffp, ffn = len(foc & g), len(foc - g), len(g - foc)
        btp, bfp, bfn = len(bro & g), len(bro - g), len(g - bro)
        F["tp"] += ftp; F["fp"] += ffp; F["fn"] += ffn
        B["tp"] += btp; B["fp"] += bfp; B["fn"] += bfn

        for key in (dump[cid].get("case_type") or "?", "wc:" + (dump[cid].get("work_context") or "?")):
            s = by_slice[key]
            s["n"] += 1
            s["F"]["tp"] += ftp; s["F"]["fp"] += ffp; s["F"]["fn"] += ffn
            s["B"]["tp"] += btp; s["B"]["fp"] += bfp; s["B"]["fn"] += bfn

        for c in (g - bro):
            missed_by_broad[c] += 1
        for c in (g - foc):
            focused_miss[c] += 1
        for c in (foc - g):
            focused_overtag[c] += 1
        for c in (bro - g):
            broad_overtag[c] += 1

        per_case.append({
            "case_id": cid, "case_type": dump[cid].get("case_type"),
            "gold_n": len(g), "focused": _prf(ftp, ffp, ffn), "broad": _prf(btp, bfp, bfn),
        })

    n = len(common)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "n_scored": n, "avg_gold_per_case": round(sum(gold_sizes) / n, 2) if n else 0,
        "gold_subset_of_broad_rate": round(gold_in_broad / n, 4) if n else None,
        "focused_micro": _prf(**F),
        "broad_micro": _prf(**B),
        "slices": {k: {"n": v["n"], "focused": _prf(**v["F"]), "broad": _prf(**v["B"])}
                   for k, v in sorted(by_slice.items())},
        "top_missed_by_broad": missed_by_broad.most_common(15),
        "top_focused_miss": focused_miss.most_common(15),
        "top_focused_overtag": focused_overtag.most_common(15),
        "top_broad_overtag": broad_overtag.most_common(15),
    }
    REPORT_JSON.write_text(json.dumps({"summary": summary, "per_case": per_case}, ensure_ascii=False, indent=2), encoding="utf-8")

    fm, bm = summary["focused_micro"], summary["broad_micro"]
    md = [
        "# 시스템 매핑 vs 독립 gold 채점 (조 단위)",
        f"- {summary['generated_at']} · 채점 {n} 케이스 · gold 평균 {summary['avg_gold_per_case']}조/케이스",
        f"- gold ⊆ broad 비율(시스템 recall 천장): **{summary['gold_subset_of_broad_rate']}**",
        "",
        "| 매핑 | precision | recall | F1 | tp/fp/fn |",
        "|---|---|---|---|---|",
        f"| **focused** | {fm['precision']} | {fm['recall']} | {fm['f1']} | {fm['tp']}/{fm['fp']}/{fm['fn']} |",
        f"| **broad** | {bm['precision']} | {bm['recall']} | {bm['f1']} | {bm['tp']}/{bm['fp']}/{bm['fn']} |",
        "",
        "## 가장 많이 누락된 gold 조 (broad조차 놓침 = 커버리지 갭)",
    ]
    md += [f"- {c}: {k}건" for c, k in summary["top_missed_by_broad"]] or ["- (없음 — broad가 gold 전부 포함)"]
    md += ["", "## focused가 놓친 gold 조 (broad엔 있을 수 있음)"]
    md += [f"- {c}: {k}건" for c, k in summary["top_focused_miss"]]
    md += ["", "## broad 과태깅 top (gold 아닌데 매핑)"]
    md += [f"- {c}: {k}건" for c, k in summary["top_broad_overtag"]]
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"채점 {n}건 → {REPORT_MD}")
    print(f"  focused  P={fm['precision']} R={fm['recall']} F1={fm['f1']}")
    print(f"  broad    P={bm['precision']} R={bm['recall']} F1={bm['f1']}")
    print(f"  gold⊆broad={summary['gold_subset_of_broad_rate']} · 평균 gold {summary['avg_gold_per_case']}조")
    return 0


if __name__ == "__main__":
    sys.exit(main())
