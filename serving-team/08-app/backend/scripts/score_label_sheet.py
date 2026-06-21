#!/usr/bin/env python3
"""OWA→CWA 4단계 — 사람이 채운 라벨시트로 시그니처-매칭 vs 배포 semantic 채점(첫 실제 측정).

label_sheet.csv의 LABEL 열을 사람이 y(정답)/n(오답)/m(애매)로 채운 뒤 실행.
y인 조문 = 실제 gold. 같은 시트의 SIG{n}/DEPL{n} 랭크로 양쪽을 동일 gold에 채점.

지표(8장 macro):
  P@1   1순위 후보가 gold인 사진 비율
  Hit@k top-k 안에 gold 하나라도 있는 사진 비율
  R@k   사진별 (top-k ∩ gold)/|gold| 평균

라벨 없는 candidate(사람이 표시 안 함)는 n으로 간주(보수적). 사람이 추가한 gold행
(sources 빈칸, LABEL=y)은 양쪽 모두 '미회수'로 잡혀 recall 상한을 정직하게 낮춘다.

사용: .venv/bin/python scripts/score_label_sheet.py
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
CSV = ART / "label_sheet.csv"


def rank_of(sources: str, tag: str):
    m = re.search(tag + r"(\d+)", sources or "")
    return int(m.group(1)) if m else None


def main():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8-sig")))
    by_photo = defaultdict(list)
    for r in rows:
        by_photo[r["photo"]].append(r)

    n_y = sum(1 for r in rows if (r.get("LABEL") or "").strip().lower().startswith("y"))
    if n_y == 0:
        print("LABEL 열에 y가 하나도 없음 — 사람이 먼저 채워야 채점 가능.")
        return

    KS = [1, 3, 5, 10]
    agg = {src: {"p1": [], **{f"hit{k}": [] for k in KS}, **{f"r{k}": [] for k in KS}}
           for src in ("SIG", "DEPL")}
    per_photo = []

    for photo, rs in by_photo.items():
        gold = {r["article_code"] for r in rs if (r.get("LABEL") or "").strip().lower().startswith("y")}
        if not gold:
            per_photo.append((photo, 0, {}, {}))
            continue
        line = {}
        for src in ("SIG", "DEPL"):
            ranked = sorted(
                [(rank_of(r["sources"], src), r["article_code"]) for r in rs if rank_of(r["sources"], src)],
                key=lambda x: x[0])
            top = [c for _, c in ranked]
            p1 = 1.0 if top and top[0] in gold else 0.0
            agg[src]["p1"].append(p1)
            stat = {"p1": p1}
            for k in KS:
                hit = 1.0 if set(top[:k]) & gold else 0.0
                r_at = len(set(top[:k]) & gold) / len(gold)
                agg[src][f"hit{k}"].append(hit)
                agg[src][f"r{k}"].append(r_at)
                stat[f"hit{k}"] = hit
                stat[f"r{k}"] = r_at
            line[src] = stat
        per_photo.append((photo, len(gold), line.get("SIG", {}), line.get("DEPL", {})))

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    print(f"=== 실제 사진 채점 (gold y={n_y}, 사진 {len(by_photo)}) ===\n")
    hdr = f"{'metric':<8}{'SIG(시그니처)':>16}{'DEPL(배포)':>14}"
    print(hdr); print("-" * len(hdr))
    print(f"{'P@1':<8}{mean(agg['SIG']['p1']):>16.1%}{mean(agg['DEPL']['p1']):>14.1%}")
    for k in KS:
        print(f"{'Hit@'+str(k):<8}{mean(agg['SIG'][f'hit{k}']):>16.1%}{mean(agg['DEPL'][f'hit{k}']):>14.1%}")
    for k in KS:
        print(f"{'R@'+str(k):<8}{mean(agg['SIG'][f'r{k}']):>16.1%}{mean(agg['DEPL'][f'r{k}']):>14.1%}")

    print("\n--- 사진별 (gold | SIG P@1/Hit@5 | DEPL P@1/Hit@5) ---")
    for photo, ng, s, d in per_photo:
        if not ng:
            print(f"  {photo}: gold 없음(미라벨)")
            continue
        print(f"  {photo}: gold {ng} | SIG {s.get('p1',0):.0f}/{s.get('hit5',0):.0f} "
              f"| DEPL {d.get('p1',0):.0f}/{d.get('hit5',0):.0f}")


if __name__ == "__main__":
    main()
