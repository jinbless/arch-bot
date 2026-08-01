#!/usr/bin/env python3
"""정식 FP 측정 — 표본 추출 + 파이프라인 실행 (사전등록: docs/dev-notes/fp-measurement-2026-08-01.md).

모집단 `real-test-photo/no_label_photo/`(648장, label_photo와 교집합 0)에서 **업체당 최대 1장** ·
seed 고정 무작위 N장을 뽑아 B(union) 구성으로 Vision→RESOLVE→RANK(2rep 정/역순)를 돌린다.

⚠ 사람 판정(블라인드 뷰어)이 끝나기 전에는 이 스크립트의 출력으로 FP율을 계산하지 않는다 —
   여기서는 "파이프라인이 무엇을 주장했는가"만 저장하고, 채점은 fp_score.py가 한다.
⚠ Vision 캐시는 gold와 **분리**(intake_vision_nolabel.json) — gold 실험 입력을 오염시키지 않는다.

사용:
  python scripts/fp_sample_and_run.py --sample-only     # 표본만 고정(뷰어 생성용)
  python scripts/fp_sample_and_run.py --workers 6       # 표본 고정 + 파이프라인 실행
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from measure_cuepool_gold import vision, resolve  # noqa: E402
from rank_ab_gold import build_arm_candidates, do_rank, scene_text  # noqa: E402

POOL = REPO / "real-test-photo" / "no_label_photo"
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SAMPLE = ART / "fp_sample.json"                    # 사전등록 표본(고정 — 재추출 금지)
VCACHE = ART / "intake_vision_nolabel.json"        # gold 캐시와 분리
OUT = ART / "fp_run_nolabel.json"
SEED = 20260801
N_DEFAULT = 80


def norm(c: str) -> str:
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def company(fn: str) -> str:
    """파일명 prefix = 업체(감독건 대리). '(주)경문기술단-송파...' / '주식회사씨에이치테크_...'"""
    return re.split(r"[-_]", fn, maxsplit=1)[0].strip()


def draw_sample(n: int) -> list[str]:
    """업체당 최대 1장 · seed 고정. 이미 고정된 표본이 있으면 그대로 재사용(재추출 금지)."""
    if SAMPLE.exists():
        s = json.loads(SAMPLE.read_text(encoding="utf-8"))
        print(f"기존 표본 재사용: {len(s['photos'])}장 (seed {s['seed']}, {s['drawn_at_pool_size']}장 풀)")
        return s["photos"]
    files = sorted(p.name for p in POOL.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    by_co: dict[str, list[str]] = defaultdict(list)
    for f in files:
        by_co[company(f)].append(f)
    rnd = random.Random(SEED)
    one_each = sorted(rnd.choice(v) for v in by_co.values())   # 업체당 1장
    rnd.shuffle(one_each)
    picked = sorted(one_each[:n])
    SAMPLE.write_text(json.dumps({
        "_note": "정식 FP 측정 사전등록 표본 — 재추출 금지(docs/dev-notes/fp-measurement-2026-08-01.md)",
        "seed": SEED, "n": len(picked), "drawn_at_pool_size": len(files),
        "n_companies": len(by_co), "rule": "업체(파일명 prefix)당 최대 1장",
        "photos": picked}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"표본 고정: {len(picked)}장 / 풀 {len(files)}장 · 업체 {len(by_co)}개 → {SAMPLE.name}")
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=N_DEFAULT)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sample-only", action="store_true")
    args = ap.parse_args()

    photos = draw_sample(args.n)
    if args.sample_only:
        return

    vcache = {}
    if VCACHE.exists():
        vcache = {r["photo"]: r for r in json.loads(VCACHE.read_text(encoding="utf-8"))["photos"]}
    print(f"파이프라인 실행 {len(photos)}장 (Vision 캐시 보유 {sum(1 for p in photos if p in vcache)}장)", flush=True)

    def run_one(pf: str) -> dict:
        res = vcache[pf]["result"] if pf in vcache else vision(POOL / pf)
        rv = resolve(scene_text(res))
        codes, kind = build_arm_candidates(rv, res, "B")
        reps = []
        for rep in range(2):
            cs = codes[::-1] if rep % 2 else codes
            ranked, halluc = do_rank(scene_text(res), cs, expert=False)
            reps.append({"ranked": [norm(c) for c in ranked], "halluc": halluc})
        return {"photo": pf, "result": res, "n_candidates": len(codes),
                "reps": reps,
                "top1_reps": [r["ranked"][0] if r["ranked"] else None for r in reps],
                "n_ranked_avg": sum(len(r["ranked"]) for r in reps) / 2,
                "abstain_rate": sum(1 for r in reps if not r["ranked"]) / 2,
                "halluc_total": sum(r["halluc"] for r in reps)}

    rows, fails, done = [], [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, pf): pf for pf in photos}
        for fu in as_completed(futs):
            pf = futs[fu]
            try:
                rows.append(fu.result())
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": pf, "err": str(e)[:200]})
                print(f"  ERR {pf[:40]}: {str(e)[:120]}", flush=True)
            done += 1
            if done % 10 == 0:
                print(f"  ... {done}/{len(photos)}", flush=True)

    for r in rows:  # Vision 캐시 갱신(분리 파일)
        vcache[r["photo"]] = {"photo": r["photo"], "industry": r["result"].get("industry", ""), "result": r["result"]}
    VCACHE.write_text(json.dumps({"_note": "no_label_photo FP 표본 Vision(gold 캐시와 분리)",
                                  "photos": list(vcache.values())}, ensure_ascii=False, indent=1), encoding="utf-8")

    asserted = Counter()
    for r in rows:
        for rep in r["reps"]:
            for c in rep["ranked"][:3]:
                asserted[c] += 1
    out = {"_note": "사람 판정 전 — 여기 수치로 FP율을 계산하지 말 것(채점은 fp_score.py)",
           "n_photos": len(rows), "n_fail": len(fails), "failures": fails,
           "abstain_rate_mean": round(sum(r["abstain_rate"] for r in rows) / max(len(rows), 1), 3),
           "avg_candidates": round(sum(r["n_candidates"] for r in rows) / max(len(rows), 1), 1),
           "avg_ranked": round(sum(r["n_ranked_avg"] for r in rows) / max(len(rows), 1), 1),
           "halluc_total": sum(r["halluc_total"] for r in rows),
           "top_asserted": asserted.most_common(15),
           "per_photo": [{k: v for k, v in r.items() if k != "result"} for r in rows]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n실패 {len(fails)} · abstain 평균 {out['abstain_rate_mean']} · 후보 평균 {out['avg_candidates']} · "
          f"노출 평균 {out['avg_ranked']} · 환각 {out['halluc_total']}건")
    print(f"→ {OUT.name} · {VCACHE.name}")


if __name__ == "__main__":
    main()
