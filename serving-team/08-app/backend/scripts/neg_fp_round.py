#!/usr/bin/env python3
"""오탐(FP) 라운드 — 음성 사진(y 없음·n 판정만)에서 파이프라인이 무엇을 주장하는지.

⚠ 표본 정정: 이전 문서의 "음성 102장"은 과대 집계 — 231장 중 129 양성 · 93 EXCLUDED(재사용 불가) ·
   **진짜 음성 9장**뿐. 본 라운드는 통계가 아니라 스모크 수준(사전 선언). 정식 FP 측정은
   위반 없는 정상 현장 사진의 신규 수집이 필요하다.

측정: B(union) 구성으로 Vision→RESOLVE→RANK(2rep 정/역순) 실행 후
  - abstain율(랭커가 applies yes/maybe를 하나도 안 냄)
  - top1/top3가 큐레이터 n 판정 코드를 침(=확정 오탐)
  - 주장 조문 분포
Vision·RESOLVE는 기존 캐시 파일에 파일명 키로 append(재사용 가능).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

import csv  # noqa: E402

from measure_cuepool_gold import vision, resolve, PHOTO_DIR, OUT_VISION  # noqa: E402
from rank_ab_gold import RESOLVE_CACHE, build_arm_candidates, do_rank, scene_text  # noqa: E402

REPO = HERE.parents[4]
LP = REPO / "real-test-photo" / "label_photo"
OUT = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "neg_fp_results.json"


def norm(c):
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def main():
    # 음성 집합: v2 gold에서 y 없음·EXCLUDED 아님·n 보유·파일 실재
    y, n, excl = defaultdict(set), defaultdict(set), set()
    for r in csv.DictReader(open(LP / "label_curation_gold_v2.csv", encoding="utf-8-sig")):
        m = (r.get("match") or "").strip().lower()
        pf, code = r["photo_file"], norm(r["article_code"])
        if m == "y":
            y[pf].add(code)
        elif m == "n":
            n[pf].add(code)
        elif m == "excluded":
            excl.add(pf)
    neg = [p for p in sorted(set(n)) if not y.get(p) and p not in excl and (PHOTO_DIR / p).exists()]
    print(f"음성 사진 {len(neg)}장 (n 판정 평균 {sum(len(n[p]) for p in neg)/max(len(neg),1):.1f})", flush=True)

    vcache = {r["photo"]: r for r in json.loads(OUT_VISION.read_text(encoding="utf-8"))["photos"]}
    rcache = json.loads(RESOLVE_CACHE.read_text(encoding="utf-8"))

    rows = []
    asserted = Counter()
    for pf in neg:
        if pf in vcache:
            res = vcache[pf]["result"]
        else:
            res = vision(PHOTO_DIR / pf)
            vcache[pf] = {"photo": pf, "industry": res.get("industry", ""), "result": res}
        if pf in rcache:
            rv = rcache[pf]
        else:
            rv = resolve(scene_text(res))
            rcache[pf] = rv
        codes, _k = build_arm_candidates(rv, res, "B")
        ranked_reps = []
        for rep in range(2):
            cs = codes[::-1] if rep % 2 else codes
            ranked, _h = do_rank(scene_text(res), cs, expert=False)
            ranked_reps.append([norm(c) for c in ranked])
        top1s = [r[0] if r else None for r in ranked_reps]
        top3 = set()
        for r in ranked_reps:
            top3 |= set(r[:3])
        fp1 = sum(1 for t in top1s if t and t in n[pf]) / 2
        abstain = sum(1 for r in ranked_reps if not r) / 2
        for r in ranked_reps:
            for c in r[:3]:
                asserted[c] += 1
        rows.append({"photo": pf, "judged_n": sorted(n[pf]), "top1_reps": top1s,
                     "n_ranked_avg": sum(len(r) for r in ranked_reps) / 2,
                     "abstain_rate": abstain, "top1_hits_judged_n": fp1,
                     "top3_hits_judged_n": sorted(top3 & n[pf]),
                     "ranked_rep0": ranked_reps[0][:5]})
        print(f"  {pf[:36]:38} abstain {abstain:.1f} · top1 {top1s} · n적중 {sorted(top3 & n[pf])}", flush=True)

    # 캐시 저장(append)
    OUT_VISION.write_text(json.dumps({"_note": "intake rich vision — gold+negative(한글 파일명 키)",
                                      "photos": list(vcache.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
    RESOLVE_CACHE.write_text(json.dumps(rcache, ensure_ascii=False, indent=1), encoding="utf-8")

    summary = {
        "n_photos": len(neg),
        "caveat": "음성 표본 9장(이전 문서의 102장은 과대 집계 — 93장은 EXCLUDED). 스모크 수준, 통계 아님.",
        "abstain_rate_mean": round(sum(r["abstain_rate"] for r in rows) / max(len(rows), 1), 3),
        "top1_confirmed_fp_mean": round(sum(r["top1_hits_judged_n"] for r in rows) / max(len(rows), 1), 3),
        "photos_top3_hits_judged_n": sum(1 for r in rows if r["top3_hits_judged_n"]),
        "avg_ranked": round(sum(r["n_ranked_avg"] for r in rows) / max(len(rows), 1), 1),
        "top_asserted": asserted.most_common(10),
    }
    OUT.write_text(json.dumps({"summary": summary, "per_photo": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n요약:", json.dumps(summary, ensure_ascii=False))
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
