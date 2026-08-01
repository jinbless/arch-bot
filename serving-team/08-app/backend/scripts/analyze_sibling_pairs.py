#!/usr/bin/env python3
"""형제 조문 '쌍별' 변별 분해 — probe_discrimination_v2.json 사후 분석(LLM 호출 0).

probe는 집계 JPA만 낸다. 어느 형제쌍에서 실제로 뒤집히는지, 어떤 조문이 오답인데 위로
올라오는지는 쌍 단위로 봐야 보인다(감독관 SSOT §5.1의 제13조 분기 원칙과 직접 연결).

⚠ per_photo에 저장된 순서는 **rep0(정순 제시)뿐**이라 이 분해는 4-rep 평균이 아닌 rep0 기술통계다.
   집계 지표(JPA·CI)는 probe 산출물을 쓰고, 여기서는 방향만 읽는다.

사용: python scripts/analyze_sibling_pairs.py [--arm P0] [--min-pairs 3]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "probe_discrimination_v2.json"

# 2차 검수가 전수로 물은 형제 10종(추락·통로 계열)
SIB = {"제13조", "제23조", "제24조", "제30조", "제42조", "제43조", "제44조", "제45조", "제56조", "제68조"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="P0")
    ap.add_argument("--min-pairs", type=int, default=3, help="표에 실을 최소 쌍 수")
    args = ap.parse_args()

    d = json.loads(SRC.read_text(encoding="utf-8"))
    pair: dict = defaultdict(lambda: [0, 0])
    as_y: dict = defaultdict(lambda: [0, 0])
    as_n_fail: dict = defaultdict(int)
    tot = fail = 0
    top1_wrong: dict = defaultdict(int)
    n_photo: dict = defaultdict(int)

    for _pf, v in d["per_photo"].items():
        order = (v.get(args.arm) or {}).get("order_rep0") or []
        pos = {c: i for i, c in enumerate(order)}
        ys, ns = set(v["y"]) & SIB, set(v["n"]) & SIB
        for y in ys:
            for n in ns:
                if y not in pos or n not in pos:
                    continue
                win = 1 if pos[y] < pos[n] else 0
                pair[(y, n)][0] += win
                pair[(y, n)][1] += 1
                as_y[y][0] += win
                as_y[y][1] += 1
                tot += 1
                if not win:
                    fail += 1
                    as_n_fail[n] += 1
        for c in set(v["n"]) & SIB:      # 오답인데 후보 1위를 차지한 사진
            n_photo[c] += 1
            if order and order[0] == c:
                top1_wrong[c] += 1

    print(f"=== 형제쌍 변별 분해 (arm {args.arm} · rep0 기술통계 · gold {d.get('gold')}) ===")
    print(f"형제 판정쌍 {tot} · 순서 실패 {fail} ({fail / tot:.1%})\n")

    print("[실패를 만든 오답(n) 조문] — 정답 위로 잘못 올라온 빈도")
    for c, k in sorted(as_n_fail.items(), key=lambda kv: -kv[1]):
        t1 = f" · 1위 오염 {top1_wrong[c]}/{n_photo[c]}장" if n_photo.get(c) else ""
        print(f"  {c:>8} {k:>4}건 ({k / fail:.0%} of 실패){t1}")

    print("\n[정답(y) 조문별] — 그 조가 정답일 때 형제 오답 위로 올린 비율")
    for c, (w, t) in sorted(as_y.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1)):
        if t >= args.min_pairs:
            print(f"  {c:>8} {w:>4}/{t:<4} {w / t:.2f}")

    print(f"\n[약한 쌍] 비율 < 0.60 · {args.min_pairs}쌍 이상")
    for (y, n), (w, t) in sorted(pair.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1)):
        if t >= args.min_pairs and w / t < 0.60:
            print(f"  정답 {y:>8} vs 오답 {n:>8}  {w:>3}/{t:<3} {w / t:.2f}")


if __name__ == "__main__":
    main()
