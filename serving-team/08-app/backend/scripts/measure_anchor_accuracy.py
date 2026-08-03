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
    # ★ 카탈로그가 바뀌면 RESOLVE를 다시 돌려야 한다. 옛 캐시는 **그때의 카탈로그**로 만든 것이라
    #   새로 들어온 그룹을 고를 방법이 아예 없었다(비계 6종이 그랬다).
    #   v2가 있으면 그걸 쓴다 — 원본은 RANK A/B 실측의 구성 요소라 지우지 않는다.
    cp = ART / "rank_ab_resolve_cache_v2.json"
    if not cp.exists():
        cp = ART / "rank_ab_resolve_cache.json"
    print(f"[RESOLVE 캐시] {cp.name}")
    rcache = json.loads(cp.read_text(encoding="utf-8"))
    # 새 형식이면 {_catalog_sha, _catalog_keys, photos}. 옛 형식은 사진 dict 그대로.
    cat_keys = rcache.get("_catalog_keys") if isinstance(rcache, dict) else None
    if cat_keys is not None:
        rcache = rcache.get("photos") or {}

    # 그룹키 → 좌표 **(편,장,절,관) 4튜플**. 그룹 소속 조문의 section에서 역산한다.
    # ★ 예전에는 [2:]로 (절,관)만 썼다. 그룹키 자체엔 편·장이 없지만 조문 section에는 있다.
    #   규칙에는 '절1'이라는 이름의 절이 20곳 있다(편2장1 기계 일반기준 / 편2장3 전기 / 편3 각 장 통칙 …).
    #   앞 두 칸을 버리면 서로 다른 절이 같은 좌표가 되어 오매칭이 난다.
    gkey_coord, gkey_coord_legacy = {}, {}
    for k, g in gim.items():
        cs = {coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
        gkey_coord[k] = cs
        gkey_coord_legacy[k] = {c[2:] for c in cs}     # 구 방식 — 부풀림 폭 비교용

    # ★ 채점 가능한 좌표 = **RESOLVE 카탈로그에 있는 그룹의 좌표**.
    #   예전에는 `편1이면 제외`로 하드코딩했는데, 그러면 카탈로그가 바뀌어도 측정이 못 따라온다.
    #   실제로 비계(편1 장7) 6종을 카탈로그에 올린 뒤에도 측정은 비계를 정답으로 인정하지 않았고,
    #   **정답이 비계뿐인 사진 15장이 통째로 채점에서 빠져 있었다.**
    #   카탈로그에서 역산하면 앞으로 카탈로그를 바꿀 때마다 측정이 저절로 따라온다.
    cross = set(json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["cross_cutting"])
    # ★ 우산 그룹(총칙·통칙)도 카탈로그에서 빠졌으므로 채점 대상에서 뺀다.
    #   여기서 빼는 게 옳은 이유: gold는 **조문**을 인용하고 우리는 그 조문의 좌표로 정답 앵커를
    #   역산한다. 그런데 제86~99조처럼 모든 기계에 상속되는 조문은 좌표가 '절1 기계 등의 일반기준'이라
    #   **어느 기인물인지 식별하지 못한다**. 그런 좌표를 정답으로 삼으면 "컨베이어 사진의 정답은
    #   기계 일반기준"이라는 틀린 문제를 내는 셈이다.
    #   대신 그 사진들은 정답 집합이 비어 채점에서 빠진다 — 그 수를 반드시 보고한다.
    umb_src = set(json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))
                  .get("umbrella_src_keys") or [])
    OBS_OK = ("yes", "partial")
    if cat_keys is not None:
        # ★★ 채점 범위를 **캐시에 적힌 카탈로그**에서 뽑는다. 규칙을 여기서 다시 계산하면
        #     "LLM이 본 보기"와 "채점이 인정하는 정답"이 소리 없이 갈린다 — 비계 15장이 그랬다.
        scorable = set()
        for k in cat_keys:
            scorable |= gkey_coord.get(k, set())
        print(f"[채점 좌표] {len(scorable)}개 — 캐시에 적힌 카탈로그 {len(cat_keys)}종에서 역산")
    else:
        scorable = set()
        for k, g in gim.items():
            nobs = sum(1 for a in g.get("articles", []) if a.get("observable") in OBS_OK)
            if nobs >= 1 and k not in cross and k not in umb_src:
                scorable |= gkey_coord[k]
        print(f"[채점 좌표] {len(scorable)}개 (우산 {len(umb_src)}종 제외) "
              f"⚠ 캐시에 카탈로그 기록이 없다 — 지금 규칙으로 재계산했다. 캐시가 낡았을 수 있다")

    jy = defaultdict(set)
    with GOLD.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("match") or "").strip().lower() == "y":
                jy[r["photo_file"]].add(norm(r["article_code"]))

    rows, skipped = [], []
    for pf, ys in sorted(jy.items()):
        if pf not in rcache:
            continue
        # 정답 좌표 — **카탈로그에 있는 그룹의 좌표만** 채점한다.
        # 카탈로그 밖(작업장·통로·보호구·추락 같은 횡단, 정의뿐인 통칙)은 앵커가 될 수 없으므로
        # 정답으로 삼으면 절대 못 맞히는 문제를 내는 셈이 된다.
        truth = set()
        for c in ys:
            if c not in sigs:
                continue
            t = coord(sigs[c]["section"])
            if t[2] is None or t not in scorable:
                continue
            truth.add(t)
        if not truth:
            skipped.append(pf)
            continue
        pred, pred_legacy = set(), set()
        # LLM이 카탈로그 줄 전체(`… ::기인물=… (N조)`)를 복사하는 일이 있다. 서빙과 같은 규칙으로 정리한다.
        for gk in (g.split(" ::")[0].strip() for g in rcache[pf].get("group_keys", [])):
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
