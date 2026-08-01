#!/usr/bin/env python3
"""FP Round 2 축 2 — A+C가 **진짜 위반을 얼마나 죽이는지** (감독관 gold, 사람 판정 불요).

오탐만 줄이고 정탐도 같이 죽이면 의미가 없다. 라벨이 이미 있는 gold v2에서 정책별
P@1 · Hit@3 · **완전침묵률**(gold 사진인데 위반 목록이 빈 비율)을 잰다.

정책 3종: 현행(yes+maybe) / A만(yes) / A+C(yes + SSOT §6.2 포괄조문을 위반목록에서 분리).
하네스 구성은 rank_ab v2의 B arm과 동일(RANK_SYS_BLIND · build_arm_candidates "B" · 조번호 정렬)이라
그 P@1(0.521)과 직접 비교 가능하다. Vision·RESOLVE 캐시 재사용 → RANK만 신규 호출.

사용: python scripts/fp_recall_gold.py [--reps 2] [--workers 6]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
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

from measure_cuepool_gold import resolve  # noqa: E402
from rank_ab_gold import (  # noqa: E402
    RANK_SCHEMA, RANK_SYS_BLIND, RESOLVE_CACHE, build_arm_candidates, chat, rank_prompt, scene_text,
)

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
GOLD = REPO / "real-test-photo" / "label_photo" / "label_curation_gold_v2.csv"
VISION = ART / "intake_vision_gold.json"
RAW = ART / "fp_recall_gold_raw.json"
OUT = ART / "fp_recall_gold.json"

GENERIC = {"제3조", "제4조", "제22조"}      # SSOT 00-master §6.2


def norm(c: str) -> str:
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def boot(vals: list[float], n: int = 4000, seed: int = 17) -> tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    pt = sum(vals) / len(vals)
    bs = sorted(sum(vals[rnd.randrange(len(vals))] for _ in range(len(vals))) / len(vals) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    jy = defaultdict(set)
    with GOLD.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("match") or "").strip().lower() == "y":
                jy[r["photo_file"]].add(norm(r["article_code"]))
    vis = {r["photo"]: r["result"] for r in json.loads(VISION.read_text(encoding="utf-8"))["photos"]}
    rcache = json.loads(RESOLVE_CACHE.read_text(encoding="utf-8")) if RESOLVE_CACHE.exists() else {}
    photos = sorted(p for p in jy if p in vis)
    print(f"gold 위반확정 {len(photos)}장 · RESOLVE 캐시 {sum(1 for p in photos if p in rcache)}장 "
          f"· reps {args.reps}", flush=True)

    if RAW.exists():
        rows = json.loads(RAW.read_text(encoding="utf-8"))["per_photo"]
        print(f"기존 RANK 결과 재사용: {RAW.name}")
    else:
        def one(pf: str) -> dict:
            res = vis[pf]
            st = scene_text(res)
            rv = rcache.get(pf) or resolve(st)
            codes, kind = build_arm_candidates(rv, res, "B")
            reps = []
            for rep in range(args.reps):
                cs = codes[::-1] if rep % 2 else codes
                rk = chat(RANK_SYS_BLIND, rank_prompt(st, cs), RANK_SCHEMA)
                valid = set(cs)
                reps.append([{"code": norm(x["article_code"]), "applies": x["applies"]}
                             for x in rk["ranked"] if x["article_code"] in valid])
            return {"photo": pf, "kind": kind, "reps": reps}

        rows, fails, done = [], [], 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, p): p for p in photos}
            for fu in as_completed(futs):
                try:
                    rows.append(fu.result())
                except Exception as e:  # noqa: BLE001
                    fails.append(futs[fu])
                    print(f"  ERR {futs[fu][:34]}: {str(e)[:100]}", flush=True)
                done += 1
                if done % 25 == 0:
                    print(f"  ... {done}/{len(photos)}", flush=True)
        RAW.write_text(json.dumps({"n_fail": len(fails), "per_photo": rows}, ensure_ascii=False, indent=1),
                       encoding="utf-8")

    per = {r["photo"]: r for r in rows}

    def exposed(pf: str, rep_i: int, policy: str) -> list[str]:
        rep = per[pf]["reps"][rep_i]
        if policy == "current":
            return [x["code"] for x in rep if x["applies"] in ("yes", "maybe")]
        yes = [x["code"] for x in rep if x["applies"] == "yes"]
        return yes if policy == "A" else [c for c in yes if c not in GENERIC]

    results = {}
    for policy, label in (("current", "현행(yes+maybe)"), ("A", "A만(yes)"), ("AC", "A+C(yes+포괄분리)")):
        p1, h3, silent = [], [], []
        for pf in per:
            g = jy[pf]
            k = len(per[pf]["reps"])
            p1.append(sum(1 for i in range(k) if exposed(pf, i, policy)[:1] and exposed(pf, i, policy)[0] in g) / k)
            h3.append(sum(1 for i in range(k) if set(exposed(pf, i, policy)[:3]) & g) / k)
            silent.append(sum(1 for i in range(k) if not exposed(pf, i, policy)) / k)
        results[policy] = {"label": label,
                           "p1": [round(x, 4) for x in boot(p1)],
                           "hit3": [round(x, 4) for x in boot(h3)],
                           "silent": [round(x, 4) for x in boot(silent)]}

    out = {"_note": "축 2 — A+C가 진짜 위반을 죽이는 정도. gold y 라벨 기준, 사람 판정 불요.",
           "n_photos": len(per), "reps": args.reps, "generic": sorted(GENERIC), "policies": results}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== 축 2 누락 측정 (gold 위반확정 {len(per)}장 · reps {args.reps}) ===")
    print(f"{'정책':22}{'P@1':>8}{'CI95':>18}{'Hit@3':>8}{'완전침묵률':>12}")
    for p in ("current", "A", "AC"):
        r = results[p]
        print(f"{r['label']:22}{r['p1'][0]:>8.3f}  [{r['p1'][1]:.3f},{r['p1'][2]:.3f}]"
              f"{r['hit3'][0]:>8.3f}{r['silent'][0]:>12.3f}")
    print("\n[사전 선언] 완전침묵률 0.30 초과면 A+C 채택하지 않는다.")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
