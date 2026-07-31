#!/usr/bin/env python3
"""RANK A/B v2 — 라벨 2차 검수 완료 후 정식 재실행 (사전등록: dev-note §다음 실험).

변경점(v1 실행 대비):
  - gold = **v2**(label_curation_gold_v2.csv, y 195 · top1 판정율 100%) 주지표, v1 병기(라벨/코드 이득 분리).
  - gold 코드 정규화(제45→제45조 오기 — v1 실행은 미정규화였음).
  - arm C(프롬프트 힌트) 제외(폐기). **arm D promote-1**은 A·B 랭킹에서 결정론 유도(추가 호출 0):
      D = union(B) 랭커의 top1이 baseline(A) 후보에 없던 신규 코드일 때만 그 top1 채택, 나머지는 A 랭킹.
  - 전체 랭킹 rep별 저장(G5) · 산출 rank_ab_results_v2.json/.md (v1 artifact 불변).
  - 계층 판정(사전등록): H1 비headroom Δ P@1(A→D) 비열등(마진 -0.02) 통과 시에만 → H2 headroom Δ P@1(A→D) 우월성(CI하한>0).
  - 층화 사전지정: headroom(후보구성만으로 결정) · gold∩CROSS16 유/무.

호출: 129장 × {A,B} × 4rep = 1,032 RANK (Vision·RESOLVE 캐시 재사용, 추가 비용 그 외 0).
사용: .venv/bin/python scripts/rank_ab_v2.py [--reps 4] [--limit N] [--workers 8]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

# 기존 하네스 재사용(RESOLVE/후보구성/프롬프트/지표 — 교란 없이 동일 조건 보장)
from rank_ab_gold import (  # noqa: E402
    IN_VISION, RESOLVE_CACHE, cross_set, scene_text, build_arm_candidates,
    do_rank, photo_metrics, mean, bootstrap_ci, mde, MKEYS,
)

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
LP = REPO / "real-test-photo" / "label_photo"
GOLD_V1 = LP / "label_curation_gold.csv"
GOLD_V2 = LP / "label_curation_gold_v2.csv"
OUT = ART / "rank_ab_results_v2.json"
OUT_MD = ART / "rank_ab_results_v2.md"

NI_HARM = -0.02      # H1: 비headroom Δ P@1(A→D) 비열등 마진(사전지정 — v1의 -0.05보다 엄격)
EXPECT = {"A": (0.837, 30.5), "B": (0.930, 46.1)}  # G3: v1-gold cand_any·avg_cand 재현(직전 실행 실측)


def norm_code(c):
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def load_gold(path):
    y = defaultdict(set)
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        if (r.get("match") or "").strip().lower() == "y":
            y[r["photo_file"]].add(norm_code(r["article_code"]))
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.reps % 2:
        sys.exit("--reps는 짝수(정순/역순 counterbalancing)")

    g1, g2 = load_gold(GOLD_V1), load_gold(GOLD_V2)
    vis = {r["photo"]: r["result"] for r in json.loads(IN_VISION.read_text(encoding="utf-8"))["photos"]}
    rcache = json.loads(RESOLVE_CACHE.read_text(encoding="utf-8"))
    photos = sorted([p for p in g2 if p in vis and p in rcache])
    if args.limit:
        photos = photos[:args.limit]
    print(f"사진 {len(photos)} · gold-y v1 {sum(len(g1[p]) for p in photos)} → v2 {sum(len(g2[p]) for p in photos)} · reps {args.reps}", flush=True)

    # 후보(결정적, v1 실행과 동일 코드 경로)
    cands = {}
    for pf in photos:
        for arm in ("A", "B"):
            cands[(pf, arm)] = build_arm_candidates(rcache[pf], vis[pf], arm)

    # 천장(G3: v1-gold 재현 게이트 + v2-gold 보고)
    ceiling = {}
    for arm in ("A", "B"):
        for tag, g in (("v1", g1), ("v2", g2)):
            anys = [1.0 if set(cands[(pf, arm)][0]) & g[pf] else 0.0 for pf in photos]
            recs = [len(set(cands[(pf, arm)][0]) & g[pf]) / len(g[pf]) if g[pf] else 0.0 for pf in photos]
            ceiling[f"{arm}_{tag}"] = {"cand_any": round(mean(anys), 3), "cand_recall": round(mean(recs), 3)}
        ceiling[f"{arm}_avg_cand"] = round(mean([len(cands[(pf, arm)][0]) for pf in photos]), 1)
    print("천장:", json.dumps(ceiling, ensure_ascii=False), flush=True)
    g3 = {"pass": True, "detail": []}
    if not args.limit:
        for arm, (exp_any, exp_n) in EXPECT.items():
            if abs(ceiling[f"{arm}_v1"]["cand_any"] - exp_any) > 0.01 or abs(ceiling[f"{arm}_avg_cand"] - exp_n) > 1.0:
                g3["pass"] = False
                g3["detail"].append(f"{arm}: {ceiling[f'{arm}_v1']['cand_any']}/{ceiling[f'{arm}_avg_cand']} (기대 {exp_any}/{exp_n})")
        if not g3["pass"] and not args.force:
            sys.exit(f"⛔ G3 실패 — 후보구성이 직전 실행과 갈라짐: {g3['detail']}")

    # 층화(사전지정·동결) — v2 gold 기준
    headroom = [pf for pf in photos
                if not (set(cands[(pf, "A")][0]) & g2[pf]) and (set(cands[(pf, "B")][0]) & g2[pf])]
    cs = set(cross_set)
    cross_out = [pf for pf in photos if g2[pf] and not (g2[pf] & cs)]
    print(f"층화: headroom {len(headroom)}장 · gold∩CROSS=∅ {len(cross_out)}장", flush=True)

    # RANK 실행 (A·B만, 홀수 rep 역순)
    jobs = [(pf, arm, rep) for arm in ("A", "B") for rep in range(args.reps) for pf in photos]
    print(f"RANK 호출 {len(jobs)}건 시작", flush=True)
    ranked_all, halluc_all, fails = {}, {}, []

    def _rank(job):
        pf, arm, rep = job
        codes, _k = cands[(pf, arm)]
        if rep % 2:
            codes = codes[::-1]
        return job, do_rank(scene_text(vis[pf]), codes, expert=False)

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_rank, j): j for j in jobs}
        for fu in as_completed(futs):
            job = futs[fu]
            try:
                _, (ranked, hall) = fu.result()
                ranked_all[job] = [norm_code(c) for c in ranked]
                halluc_all[job] = hall
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": job[0], "arm": job[1], "rep": job[2], "err": str(e)[:200]})
                print(f"  RANK ERR {job[1]}/rep{job[2]} {job[0][:26]}: {str(e)[:100]}", flush=True)
            done += 1
            if done % 50 == 0:
                print(f"  ... {done}/{len(jobs)}", flush=True)

    # arm D 유도(promote-1): B top1이 A 후보 밖 신규 코드일 때만 그 top1 채택 + 이하 A 랭킹
    for pf in photos:
        candA = set(norm_code(c) for c in cands[(pf, "A")][0])
        for rep in range(args.reps):
            ka, kb = (pf, "A", rep), (pf, "B", rep)
            if ka not in ranked_all or kb not in ranked_all:
                continue
            ra, rb = ranked_all[ka], ranked_all[kb]
            if rb and rb[0] not in candA:
                ranked_all[(pf, "D", rep)] = [rb[0]] + [c for c in ra if c != rb[0]]
            else:
                ranked_all[(pf, "D", rep)] = list(ra)

    ARMS = ["A", "B", "D"]

    def rep_avg(gold):
        per = defaultdict(dict)
        for arm in ARMS:
            for pf in photos:
                ms = [photo_metrics(ranked_all[(pf, arm, r)], gold[pf])
                      for r in range(args.reps) if (pf, arm, r) in ranked_all]
                if len(ms) == args.reps:
                    per[pf][arm] = {k: mean([m[k] for m in ms]) for k in ms[0]}
        return per

    per2, per1 = rep_avg(g2), rep_avg(g1)
    scored = [pf for pf in photos if all(a in per2[pf] for a in ARMS)]
    dropped = [pf for pf in photos if pf not in scored]
    agg2 = {a: {k: round(mean([per2[pf][a][k] for pf in scored]), 3) for k in MKEYS} for a in ARMS}
    agg1 = {a: {k: round(mean([per1[pf][a][k] for pf in scored]), 3) for k in MKEYS} for a in ARMS}

    # 상수 기저선(G4)
    def _const43(pf):
        c = [norm_code(x) for x in cands[(pf, "A")][0]]
        return (["제43조"] + [x for x in c if x != "제43조"]) if "제43조" in c else c
    const43 = {k: round(mean([photo_metrics(_const43(pf), g2[pf])[k] for pf in scored]), 3) for k in MKEYS}

    # 페어드 비교(v2) + 층화
    def comp(lo, hi, subset, key="p1"):
        pairs = [(per2[pf][lo][key], per2[pf][hi][key]) for pf in subset]
        d, l, h = bootstrap_ci(pairs)
        return {"n": len(subset), "delta": round(d, 4), "ci95": [round(l, 4), round(h, 4)], "mde": mde(pairs)}

    comps = {}
    for lo, hi in (("A", "B"), ("A", "D"), ("B", "D")):
        comps[f"{lo}->{hi}"] = {k: comp(lo, hi, scored, k) for k in ("p1", "hit3", "hit5", "mrr")}

    nonhead = [pf for pf in scored if pf not in set(headroom)]
    strata = {
        "H1_nonheadroom_AtoD_p1": comp("A", "D", nonhead),
        "H2_headroom_AtoD_p1": comp("A", "D", [pf for pf in scored if pf in set(headroom)]),
        "cross_out_AtoB_p1": comp("A", "B", [pf for pf in scored if pf in set(cross_out)]),
        "cross_in_AtoB_p1": comp("A", "B", [pf for pf in scored if pf not in set(cross_out) and g2[pf]]),
    }
    # 계층 판정(사전등록)
    h1 = strata["H1_nonheadroom_AtoD_p1"]
    h1_pass = h1["ci95"][0] > NI_HARM
    h2 = strata["H2_headroom_AtoD_p1"]
    h2_pass = h1_pass and h2["ci95"][0] > 0
    judgment = {"H1_noninferior(margin -0.02)": bool(h1_pass),
                "H2_superior(only if H1)": bool(h2_pass),
                "verdict": ("adopt_D" if h1_pass and h2_pass else
                            "D_safe_but_gain_unproven" if h1_pass else "D_rejected")}

    # order sensitivity(G2)
    def _dirmean(arm, par):
        return mean([photo_metrics(ranked_all[(pf, arm, r)], g2[pf])["p1"]
                     for pf in scored for r in range(par, args.reps, 2) if (pf, arm, r) in ranked_all])
    order_sens = {a: round(_dirmean(a, 0) - _dirmean(a, 1), 4) for a in ARMS}
    g2max = max(abs(v) for v in order_sens.values())

    gates = {
        "G1_no_failure": {"pass": not fails and not dropped, "n_fail": len(fails), "n_dropped": len(dropped)},
        "G2_order": {"pass": g2max <= 0.05, "max_abs": round(g2max, 4), "by_arm": order_sens},
        "G3_ceiling_v1_reproduced": g3,
        "G4_beats_const": {"pass": agg2["A"]["p1"] > const43["p1"], "A_p1": agg2["A"]["p1"], "const_p1": const43["p1"]},
        "G5_full_ranked_saved": {"pass": True},
    }

    result = {
        "n_photos": len(scored), "reps": args.reps, "arms": ARMS,
        "gold": {"v1_y": sum(len(g1[p]) for p in scored), "v2_y": sum(len(g2[p]) for p in scored)},
        "primary": "H1/H2 계층판정: 비headroom A→D 비열등(-0.02) → headroom A→D 우월성",
        "judgment": judgment, "gates": gates,
        "ceiling": ceiling, "headroom_photos": headroom, "n_cross_out": len(cross_out),
        "metrics_v2": agg2, "metrics_v1": agg1, "const43_v2": const43,
        "paired_v2": comps, "strata_v2": strata,
        "order_sensitivity": order_sens,
        "hallucinated_by_arm": {a: sum(v for (p, ar, r), v in halluc_all.items() if ar == a) for a in ("A", "B")},
        "rank_failures": fails, "dropped_photos": dropped,
        "per_photo": {pf: {"gold_v2": sorted(g2[pf]), "gold_v1": sorted(g1[pf]),
                           **{arm: {"metrics_v2": {k: round(v, 3) for k, v in per2[pf][arm].items()},
                                    "ranked": {str(r): ranked_all.get((pf, arm, r), []) for r in range(args.reps)}}
                              for arm in ARMS},
                           "candidates_A": cands[(pf, "A")][0], "candidates_B": cands[(pf, "B")][0],
                           "kind_B": cands[(pf, "B")][1]} for pf in scored},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"=== RANK A/B v2 (gold v2 · {len(scored)}장 · y {result['gold']['v2_y']} · reps {args.reps}) ===",
         f"실패 {len(fails)} · 제외 {len(dropped)} · 후보밖코드 {result['hallucinated_by_arm']}", "",
         f"{'arm':14}{'P@1':>8}{'Hit@3':>8}{'Hit@5':>8}{'R@5':>8}{'MRR':>8}   (v1-gold P@1)"]
    NAME = {"A": "A baseline", "B": "B union", "D": "D promote-1"}
    for a in ARMS:
        m = agg2[a]
        L.append(f"{NAME[a]:14}{m['p1']:>8.3f}{m['hit3']:>8.3f}{m['hit5']:>8.3f}{m['r5']:>8.3f}{m['mrr']:>8.3f}"
                 f"   ({agg1[a]['p1']:.3f})")
    L.append(f"{'const_제43조':14}{const43['p1']:>8.3f}{const43['hit3']:>8.3f}{const43['hit5']:>8.3f}"
             f"{const43['r5']:>8.3f}{const43['mrr']:>8.3f}")
    L.append("")
    for k, c in comps.items():
        L.append(f"[{k}] " + " · ".join(f"{m} Δ{c[m]['delta']:+.3f} CI[{c[m]['ci95'][0]:+.3f},{c[m]['ci95'][1]:+.3f}]"
                                        for m in ("p1", "hit3", "hit5")))
    L.append("")
    L.append(f"[계층판정] H1 비headroom A→D Δ{h1['delta']:+.4f} CI[{h1['ci95'][0]:+.4f},{h1['ci95'][1]:+.4f}] "
             f"(마진 {NI_HARM}) → {'PASS' if h1_pass else 'FAIL'}")
    L.append(f"          H2 headroom(n={h2['n']}) A→D Δ{h2['delta']:+.4f} CI[{h2['ci95'][0]:+.4f},{h2['ci95'][1]:+.4f}] "
             f"→ {'PASS' if h2_pass else 'FAIL'}")
    L.append(f"          verdict: {judgment['verdict']}")
    L.append("")
    L.append(f"[층화] CROSS밖(n={strata['cross_out_AtoB_p1']['n']}) A→B Δ{strata['cross_out_AtoB_p1']['delta']:+.3f} / "
             f"CROSS안(n={strata['cross_in_AtoB_p1']['n']}) Δ{strata['cross_in_AtoB_p1']['delta']:+.3f}")
    L.append("[유효성 게이트]")
    for gk, gv in gates.items():
        L.append(f"  {'PASS' if gv.get('pass') else 'FAIL'}  {gk}: "
                 + json.dumps({k: v for k, v in gv.items() if k != 'pass'}, ensure_ascii=False)[:160])
    txt = "\n".join(L)
    OUT_MD.write_text(txt, encoding="utf-8")
    print("\n" + txt)
    print(f"\n→ {OUT.name} · {OUT_MD.name}")


if __name__ == "__main__":
    main()
