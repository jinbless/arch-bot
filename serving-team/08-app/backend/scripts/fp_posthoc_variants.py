#!/usr/bin/env python3
"""FP 측정 **사후 탐색** — 어떤 노출 규칙이면 오탐이 내려가는가 (LLM 호출 0).

⚠ 사전등록 판정은 이미 났다(top1 FP율 0.948 → '프로덕션 노출 부적합'). 이 스크립트는 그 판정을
   바꾸지 않는다. 다음 설계를 고르기 위한 **탐색적 사후 분석**이며, 여기서 좋아 보이는 규칙은
   반드시 새 표본에서 사전등록 후 재측정해야 한다(같은 80장으로 규칙을 고르면 그 80장에 과적합된다).

변형: 전체 / CROSS16 제외 / 상위 빈출 포괄조 제외 / top-k 제한.
각 변형에서 '위반없음' 사진의 주장률과 '위반있음' 사진의 주장률을 **나란히** 본다 —
오탐만 낮추고 정탐도 같이 죽으면 아무 의미가 없다(판별력 Δ가 핵심).

사용: python scripts/fp_posthoc_variants.py
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
RUN = ART / "fp_run_nolabel.json"
JUDGED = REPO / "real-test-photo" / "label_photo" / "fp_binary_filled.csv"
OUT = ART / "fp_posthoc_variants.json"

# 서빙 코드(cue_article_service.CROSS)와 동일 — 매 사진 무조건 주입되는 횡단 일반의무
CROSS = ["제3조", "제5조", "제13조", "제14조", "제20조", "제22조", "제23조", "제32조",
         "제42조", "제43조", "제44조", "제45조", "제46조", "제88조", "제92조", "제93조"]


def boot(vals: list[float], n: int = 4000, seed: int = 17) -> tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    pt = sum(vals) / len(vals)
    bs = sorted(sum(vals[rnd.randrange(len(vals))] for _ in range(len(vals))) / len(vals) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def main() -> None:
    run = json.loads(RUN.read_text(encoding="utf-8"))
    per = {r["photo"]: r for r in run["per_photo"]}
    verdict = {}
    with JUDGED.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("verdict") or "").strip().lower()
            if v in ("y", "n", "m"):
                verdict[r["photo_file"]] = v
    neg = [p for p in per if verdict.get(p) == "n"]
    pos = [p for p in per if verdict.get(p) == "y"]

    # '위반없음' 사진에서 실제로 무엇이 튀어나왔나 — 조문별 등장 사진 수
    appear = Counter()
    top1_of = Counter()
    for p in neg:
        seen = set()
        for rep in per[p]["reps"]:
            for c in rep["ranked"][:3]:
                seen.add(c)
            if rep["ranked"]:
                top1_of[rep["ranked"][0]] += 1
        for c in seen:
            appear[c] += 1

    def claim_rate(ps: list[str], drop: set, topk: int | None = None) -> list[float]:
        """사진별 '무언가 주장함' 비율(rep 평균). drop 조문 제거 후, topk 제한 시 상위 k만 노출."""
        out = []
        for p in ps:
            hits = 0
            for rep in per[p]["reps"]:
                kept = [c for c in rep["ranked"] if c not in drop]
                if topk is not None:
                    kept = kept[:topk]
                hits += 1 if kept else 0
            out.append(hits / len(per[p]["reps"]))
        return out

    # 사후 탐색 변형
    ubiquitous = {c for c, k in appear.items() if k >= 0.5 * len(neg)}   # 음성 절반 이상에 등장
    variants = [
        ("전체(사전등록 주지표)", set(), None),
        ("CROSS16 제외", set(CROSS), None),
        (f"음성 50%+ 등장 조문 제외({len(ubiquitous)}종)", ubiquitous, None),
        ("CROSS16 제외 + top1만", set(CROSS), 1),
    ]

    rows = []
    for name, drop, topk in variants:
        n_pt, n_lo, n_hi = boot(claim_rate(neg, drop, topk))
        p_pt, _, _ = boot(claim_rate(pos, drop, topk))
        rows.append({"variant": name, "n_drop": len(drop), "topk": topk,
                     "neg_claim": round(n_pt, 3), "neg_ci95": [round(n_lo, 3), round(n_hi, 3)],
                     "pos_claim": round(p_pt, 3), "discrimination": round(p_pt - n_pt, 3)})

    out = {"_note": "사후 탐색 — 사전등록 판정(부적합)을 바꾸지 않는다. 새 표본에서 사전등록 후 재측정 필요.",
           "n_neg": len(neg), "n_pos": len(pos),
           "ubiquitous_on_negatives": [[c, appear[c], round(appear[c] / len(neg), 2)] for c in
                                       sorted(ubiquitous, key=lambda c: -appear[c])],
           "top1_distribution_on_negatives": top1_of.most_common(10),
           "variants": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"=== FP 사후 탐색 (위반없음 {len(neg)}장 · 위반있음 {len(pos)}장) ===\n")
    print("[음성 사진 절반 이상에 등장한 조문] — 사진과 무관하게 붙는 것들")
    for c in sorted(ubiquitous, key=lambda c: -appear[c]):
        print(f"  {c:>8} {appear[c]:>3}/{len(neg)}장 ({appear[c] / len(neg):.0%})")
    print("\n[음성 사진 top1 분포]")
    for c, k in top1_of.most_common(8):
        print(f"  {c:>8} {k:>3}회")
    print(f"\n{'변형':32}{'음성 주장률':>12}{'CI95':>18}{'양성 주장률':>12}{'판별력Δ':>10}")
    for r in rows:
        print(f"{r['variant']:32}{r['neg_claim']:>12.3f}  [{r['neg_ci95'][0]:.3f},{r['neg_ci95'][1]:.3f}]"
              f"{r['pos_claim']:>12.3f}{r['discrimination']:>10.3f}")
    print(f"\n→ {OUT.name}")


if __name__ == "__main__":
    main()
