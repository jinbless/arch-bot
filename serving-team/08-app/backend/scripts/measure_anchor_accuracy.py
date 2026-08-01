#!/usr/bin/env python3
"""앵커(기인물) 인식 정확도 — 새 흐름도 구조의 단일 실패점을 측정한다. LLM 호출 0.

왜 재는가: 스냅샷→시간축 구조는 기인물 하나에 흐름 6단계가 전부 걸린다.
지게차를 굴착기로 보면 계획·점검·작업·종료가 통째로 틀린다(현행은 조문마다 따로 틀림).

측정 방법 — **라벨 추가 없이**:
  감독관 gold의 정답 조문(y) → 각 조문의 절/관 좌표 → '정답 기인물 그룹' 역산
  RESOLVE가 낸 group_keys → '예측 기인물 그룹'
  두 집합을 대조한다.

⚠ 한계(반드시 함께 읽을 것)
  - gold는 감독건 인용이라 사진의 **모든** 기인물을 담지 않는다 → recall은 과소평가된다.
    신뢰할 수 있는 건 precision 쪽과 '완전 오인식률'이다.
  - 총칙(편1)·횡단 조문은 기인물 그룹으로 역산되지 않으므로 정답 집합에서 제외한다.
    정답 집합이 비는 사진은 측정 대상에서 빠진다(그 사실도 보고한다).

사용: python scripts/measure_anchor_accuracy.py
"""
from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
GOLD = REPO / "real-test-photo" / "label_photo" / "label_curation_gold_v2.csv"
OUT = ART / "anchor_accuracy.json"


def norm(c: str) -> str:
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def coord(section: str) -> tuple:
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        if lvl == "편":
            p = n
        elif lvl == "장":
            j = n
        elif lvl == "절":
            jeol = n
        elif lvl == "관":
            gwan = n
    return (p, j, jeol, gwan)


def boot(vals, n=4000, seed=17):
    if not vals:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    pt = sum(vals) / len(vals)
    bs = sorted(sum(vals[rnd.randrange(len(vals))] for _ in range(len(vals))) / len(vals) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def main() -> None:
    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    rcache = json.loads((ART / "rank_ab_resolve_cache.json").read_text(encoding="utf-8"))

    # 그룹키 → 좌표 **(편,장,절,관) 4튜플**. 그룹 소속 조문의 section에서 역산한다.
    # ★ 예전에는 [2:]로 (절,관)만 썼다. 그룹키 자체엔 편·장이 없지만 조문 section에는 있다.
    #   규칙에는 '절1'이라는 이름의 절이 20곳 있다(편2장1 기계 일반기준 / 편2장3 전기 / 편3 각 장 통칙 …).
    #   앞 두 칸을 버리면 서로 다른 절이 같은 좌표가 되어 오매칭이 난다.
    gkey_coord, gkey_coord_legacy = {}, {}
    for k, g in gim.items():
        cs = {coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
        gkey_coord[k] = cs
        gkey_coord_legacy[k] = {c[2:] for c in cs}     # 구 방식 — 부풀림 폭 비교용

    jy = defaultdict(set)
    with GOLD.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("match") or "").strip().lower() == "y":
                jy[r["photo_file"]].add(norm(r["article_code"]))

    rows, skipped = [], []
    for pf, ys in sorted(jy.items()):
        if pf not in rcache:
            continue
        # 정답 좌표 — 총칙(편1) 제외. 기인물 축이 아니므로 앵커 채점에 못 쓴다
        truth = set()
        for c in ys:
            if c not in sigs:
                continue
            p, j, jeol, gwan = coord(sigs[c]["section"])
            if p == 1 or jeol is None:
                continue
            truth.add((p, j, jeol, gwan))
        if not truth:
            skipped.append(pf)
            continue
        pred, pred_legacy = set(), set()
        for gk in rcache[pf].get("group_keys", []):
            pred |= gkey_coord.get(gk, set())
            pred_legacy |= gkey_coord_legacy.get(gk, set())
        # 관 단위가 달라도 같은 절이면 '절 일치'로 따로 센다(상위 흐름은 공유되므로 실무상 유효).
        # 단 '같은 절'도 편·장까지 같아야 같은 절이다.
        hit_exact = bool(truth & pred)
        hit_jeol = bool({t[:3] for t in truth} & {p_[:3] for p_ in pred})
        hit_legacy = bool({t[2:] for t in truth} & pred_legacy)

        def _k(t):
            return tuple(9999 if x is None else x for x in t)
        rows.append({"photo": pf, "truth": [list(t) for t in sorted(truth, key=_k)],
                     "pred": [list(t) for t in sorted(pred, key=_k)],
                     "gimulmul": rcache[pf].get("gimulmul", []), "exact": hit_exact, "jeol": hit_jeol,
                     "legacy_exact": hit_legacy, "n_pred": len(pred)})

    n = len(rows)
    ex = boot([1.0 if r["exact"] else 0.0 for r in rows])
    jl = boot([1.0 if r["jeol"] else 0.0 for r in rows])
    lg = boot([1.0 if r["legacy_exact"] else 0.0 for r in rows])
    miss = [r for r in rows if not r["jeol"]]
    empty_pred = sum(1 for r in rows if not r["pred"])

    top_miss = Counter()
    for r in miss:
        for g in r["gimulmul"][:2]:
            top_miss[g.split("(")[0].strip()[:20]] += 1

    out = {"_note": "앵커(기인물) 인식 정확도. gold 조문에서 (편,장,절,관) 역산 → RESOLVE group_keys와 대조. 라벨 추가 없음.",
           "_coord": "좌표는 (편,장,절,관) 4튜플 전체로 비교한다. legacy_*는 편·장을 버리던 구 방식(부풀림 폭 비교용).",
           "n_scored": n, "n_skipped_no_truth": len(skipped),
           "exact_match": {"point": round(ex[0], 3), "ci95": [round(ex[1], 3), round(ex[2], 3)]},
           "jeol_match": {"point": round(jl[0], 3), "ci95": [round(jl[1], 3), round(jl[2], 3)]},
           "legacy_exact_match": {"point": round(lg[0], 3), "ci95": [round(lg[1], 3), round(lg[2], 3)],
                                  "_note": "편·장을 버리고 (절,관)만 비교하던 구 방식. 이 값과 exact_match의 차이가 부풀림 폭이다."},
           "empty_prediction": empty_pred,
           "complete_miss": len(miss),
           "top_gimulmul_on_miss": top_miss.most_common(10),
           "per_photo": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"=== 앵커(기인물) 인식 정확도 — 채점 {n}장 (정답 좌표 없어 제외 {len(skipped)}장) ===")
    print(f"  관 단위 정확 일치  {ex[0]:.3f}  CI[{ex[1]:.3f},{ex[2]:.3f}]")
    print(f"  절 단위 일치       {jl[0]:.3f}  CI[{jl[1]:.3f},{jl[2]:.3f}]   ← 상위 흐름 공유 기준")
    print(f"  (구 방식 편·장 무시 {lg[0]:.3f}  ← 부풀림 {lg[0] - ex[0]:+.3f})")
    print(f"  완전 오인식(절도 불일치) {len(miss)}장 ({len(miss)/max(n,1):.1%}) · 예측 자체가 빈 사진 {empty_pred}장")
    print("\n[오인식 사진에서 RESOLVE가 지목한 기인물 상위]")
    for g, k in top_miss.most_common(8):
        print(f"   {g:24} {k}장")
    print(f"\n→ {OUT.name}")


if __name__ == "__main__":
    main()
