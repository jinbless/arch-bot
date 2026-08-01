#!/usr/bin/env python3
"""FP Round 2 축 1 — 손대지 않은 새 표본에서 A+C 정책 재측정 (사전등록: fp-measurement-2026-08-01.md).

Round 1의 80장과 **그 업체 전체**를 제외한 나머지에서 업체당 1장·seed 20260802·80장을 뽑아
Vision→RESOLVE→RANK(2rep 정/역순)를 돌린다. applies를 **보존해서** 저장하므로 채점 시 정책
(현행 / A / A+C)을 골라 적용할 수 있다.

⚠ 사람 판정 전에는 이 출력으로 FP율을 계산하지 않는다(채점은 fp_round2_score.py).

사용: python scripts/fp_round2_run.py [--sample-only] [--workers 6]
"""
from __future__ import annotations

import argparse
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

from measure_cuepool_gold import resolve, vision  # noqa: E402
from rank_ab_gold import (  # noqa: E402
    RANK_SCHEMA, RANK_SYS_BLIND, build_arm_candidates, chat, rank_prompt, scene_text,
)

POOL = REPO / "real-test-photo" / "no_label_photo"
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SAMPLE1 = ART / "fp_sample.json"
SAMPLE2 = ART / "fp_sample_r2.json"
VCACHE = ART / "intake_vision_nolabel.json"
OUT = ART / "fp_round2_raw.json"
SEED = 20260802
N_DEFAULT = 80


def norm(c: str) -> str:
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def company(fn: str) -> str:
    return re.split(r"[-_]", fn, maxsplit=1)[0].strip()


def draw(n: int) -> list[str]:
    if SAMPLE2.exists():
        s = json.loads(SAMPLE2.read_text(encoding="utf-8"))
        print(f"기존 R2 표본 재사용: {len(s['photos'])}장 (seed {s['seed']})")
        return s["photos"]
    r1 = set(json.loads(SAMPLE1.read_text(encoding="utf-8"))["photos"])
    r1_co = {company(p) for p in r1}          # 클러스터 독립 — 업체 단위로 제외
    files = sorted(p.name for p in POOL.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    by_co: dict[str, list[str]] = defaultdict(list)
    for f in files:
        if f in r1 or company(f) in r1_co:
            continue
        by_co[company(f)].append(f)
    rnd = random.Random(SEED)
    one_each = sorted(rnd.choice(v) for v in by_co.values())
    rnd.shuffle(one_each)
    picked = sorted(one_each[:n])
    assert not (set(picked) & r1), "Round 1 표본과 겹침"
    assert not ({company(p) for p in picked} & r1_co), "Round 1 업체와 겹침"
    SAMPLE2.write_text(json.dumps({
        "_note": "FP Round 2 사전등록 표본 — 재추출 금지. Round 1 사진·업체 전부 제외.",
        "seed": SEED, "n": len(picked), "excluded_r1_photos": len(r1), "excluded_r1_companies": len(r1_co),
        "pool_after_exclusion": sum(len(v) for v in by_co.values()), "n_companies": len(by_co),
        "photos": picked}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"R2 표본 고정: {len(picked)}장 · 잔여 풀 {sum(len(v) for v in by_co.values())}장 "
          f"· 업체 {len(by_co)}개 (R1 업체 {len(r1_co)}개 제외) → {SAMPLE2.name}")
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=N_DEFAULT)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sample-only", action="store_true")
    args = ap.parse_args()

    photos = draw(args.n)
    if args.sample_only:
        return

    vcache = {}
    if VCACHE.exists():
        vcache = {r["photo"]: r for r in json.loads(VCACHE.read_text(encoding="utf-8"))["photos"]}
    print(f"실행 {len(photos)}장 (Vision 캐시 보유 {sum(1 for p in photos if p in vcache)}장)", flush=True)

    def one(pf: str) -> dict:
        res = vcache[pf]["result"] if pf in vcache else vision(POOL / pf)
        st = scene_text(res)
        rv = resolve(st)
        codes, kind = build_arm_candidates(rv, res, "B")
        reps = []
        for rep in range(2):
            cs = codes[::-1] if rep % 2 else codes
            rk = chat(RANK_SYS_BLIND, rank_prompt(st, cs), RANK_SCHEMA)
            valid = set(cs)
            halluc = sum(1 for x in rk["ranked"] if x["article_code"] not in valid)
            reps.append({"ranked": [{"code": norm(x["article_code"]), "applies": x["applies"]}
                                    for x in rk["ranked"] if x["article_code"] in valid],
                         "halluc": halluc})
        return {"photo": pf, "result": res, "gimulmul": rv.get("gimulmul", []),
                "kind": kind, "n_candidates": len(codes), "reps": reps}

    rows, fails, done = [], [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, p): p for p in photos}
        for fu in as_completed(futs):
            try:
                rows.append(fu.result())
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": futs[fu], "err": str(e)[:200]})
                print(f"  ERR {futs[fu][:36]}: {str(e)[:110]}", flush=True)
            done += 1
            if done % 20 == 0:
                print(f"  ... {done}/{len(photos)}", flush=True)

    for r in rows:
        vcache[r["photo"]] = {"photo": r["photo"], "industry": r["result"].get("industry", ""), "result": r["result"]}
    VCACHE.write_text(json.dumps({"_note": "no_label_photo FP 표본 Vision(gold 캐시와 분리)",
                                  "photos": list(vcache.values())}, ensure_ascii=False, indent=1), encoding="utf-8")

    out = {"_note": "사람 판정 전 — 채점은 fp_round2_score.py", "n_photos": len(rows),
           "n_fail": len(fails), "failures": fails,
           "halluc_total": sum(rep["halluc"] for r in rows for rep in r["reps"]),
           "per_photo": [{k: v for k, v in r.items() if k != "result"} for r in rows]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n실패 {len(fails)} · 환각 {out['halluc_total']}건 → {OUT.name}")


if __name__ == "__main__":
    main()
