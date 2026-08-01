#!/usr/bin/env python3
"""FP 게이트 후보 A/B — "무엇을 게이트로 쓰면 오탐이 내려가는가" 탐색 (사후·탐색적).

배경(fp_results): top1 FP율 0.948, 판별력 Δ0.052. 조문 단위 제거(CROSS16 등)로는 0.799가 바닥이었다.
그러나 그 사후 탐색에는 **두 개의 큰 공백**이 있었다:
  ① `do_rank()`가 applies(yes/maybe)를 버리고 코드만 반환 → **'yes만 노출' 정책이 미측정**
  ② 조문 단위로만 뺐고 **기인물(후보 출처) 단위**로는 빼보지 않았다
본 스크립트는 RESOLVE/RANK를 재실행하되 **applies 라벨과 출처(kind)를 보존**해 두 공백을 메우고,
추가로 '결여 신호 게이트'(존재가 아니라 결여를 요구)를 시뮬레이션한다.

⚠ 전부 **같은 80장 위에서의 사후 탐색**이다. 여기서 좋아 보이는 정책은 남은 568장에서
   사전등록 후 재측정해야 한다(같은 표본으로 정책을 고르면 그 표본에 과적합).

사용: python scripts/fp_gate_variants.py [--workers 6]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from measure_cuepool_gold import resolve  # noqa: E402
from rank_ab_gold import (  # noqa: E402
    RANK_SCHEMA, RANK_SYS_BLIND, build_arm_candidates, chat, rank_prompt, scene_text,
)

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
VCACHE = ART / "intake_vision_nolabel.json"
JUDGED = REPO / "real-test-photo" / "label_photo" / "fp_binary_filled.csv"
RAW = ART / "fp_gate_raw.json"          # applies·kind 보존 재실행 결과(재사용)
OUT = ART / "fp_gate_variants.json"

CROSS = {"제3조", "제5조", "제13조", "제14조", "제20조", "제22조", "제23조", "제32조",
         "제42조", "제43조", "제44조", "제45조", "제46조", "제88조", "제92조", "제93조"}

# 결여(deficiency) 신호 — '물체가 있다'가 아니라 '있어야 할 것이 없다/불량하다'
DEFICIENCY = re.compile(
    r"없|미설치|미착용|미비|미고정|미부착|불량|파손|손상|훼손|열려|개방|이탈|누락|"
    r"방치|적치|쌓여|무질서|어지럽|젖어|미끄러|누유|누수|돌출|노출|끊어|헐거|"
    r"임의|해체|제거|초과|불안정|기울|넘어질|추락할")


def norm(c: str) -> str:
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def cue_text(res: dict) -> str:
    parts = [o.get("text", "") for o in res.get("visual_observations") or []]
    parts += [o.get("text", "") for o in res.get("visual_cues") or []]
    for h in res.get("hazards") or []:
        parts += [h.get("name", ""), h.get("description", ""), h.get("location", "")]
    return " | ".join(parts)


def boot(vals: list[float], n: int = 4000, seed: int = 17) -> tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    pt = sum(vals) / len(vals)
    bs = sorted(sum(vals[rnd.randrange(len(vals))] for _ in range(len(vals))) / len(vals) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def collect(workers: int) -> dict:
    """applies·kind·기인물을 보존해 재실행(있으면 재사용)."""
    if RAW.exists():
        print(f"기존 재실행 결과 재사용: {RAW.name}")
        return json.loads(RAW.read_text(encoding="utf-8"))

    vis = {r["photo"]: r["result"] for r in json.loads(VCACHE.read_text(encoding="utf-8"))["photos"]}
    photos = sorted(vis)
    print(f"RESOLVE+RANK 재실행 {len(photos)}장 (Vision은 캐시 재사용)", flush=True)

    def one(pf: str) -> dict:
        res = vis[pf]
        st = scene_text(res)
        rv = resolve(st)
        codes, kind = build_arm_candidates(rv, res, "B")
        reps = []
        for rep in range(2):
            cs = codes[::-1] if rep % 2 else codes
            rk = chat(RANK_SYS_BLIND, rank_prompt(st, cs), RANK_SCHEMA)
            valid = set(cs)
            reps.append([{"code": norm(x["article_code"]), "applies": x["applies"]}
                         for x in rk["ranked"] if x["article_code"] in valid])
        return {"photo": pf, "gimulmul": rv.get("gimulmul", []), "group_keys": rv.get("group_keys", []),
                "kind": kind, "n_candidates": len(codes), "reps": reps,
                "deficiency_hits": sorted(set(DEFICIENCY.findall(cue_text(res))))}

    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, p): p for p in photos}
        for fu in as_completed(futs):
            try:
                rows.append(fu.result())
            except Exception as e:  # noqa: BLE001
                print(f"  ERR {futs[fu][:36]}: {str(e)[:100]}", flush=True)
            done += 1
            if done % 20 == 0:
                print(f"  ... {done}/{len(photos)}", flush=True)
    data = {"_note": "applies·kind·기인물 보존 재실행(FP 게이트 탐색용)", "per_photo": rows}
    RAW.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    data = collect(args.workers)
    per = {r["photo"]: r for r in data["per_photo"]}
    verdict = {}
    with JUDGED.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("verdict") or "").strip().lower()
            if v in ("y", "n", "m"):
                verdict[r["photo_file"]] = v
    neg = [p for p in per if verdict.get(p) == "n"]
    pos = [p for p in per if verdict.get(p) == "y"]

    def rate(ps: list[str], keep) -> list[float]:
        """정책 keep(item, row)->bool 적용 후 '무언가 노출했는가' 비율(rep 평균)."""
        out = []
        for p in ps:
            row = per[p]
            hits = sum(1 for rep in row["reps"] if any(keep(it, row) for it in rep))
            out.append(hits / max(len(row["reps"]), 1))
        return out

    def deficient(row) -> bool:
        return bool(row["deficiency_hits"])

    POLICIES = [
        ("현행(yes+maybe 전부)", lambda it, r: True),
        ("yes만 노출", lambda it, r: it["applies"] == "yes"),
        ("CROSS16 제외", lambda it, r: it["code"] not in CROSS),
        ("yes만 + CROSS16 제외", lambda it, r: it["applies"] == "yes" and it["code"] not in CROSS),
        ("횡단 출처 제외(kind)", lambda it, r: r["kind"].get(it["code"]) != "횡단"),
        ("단서/흐름 출처만(cue 직결)", lambda it, r: r["kind"].get(it["code"]) in ("단서", "흐름")),
        ("결여신호 없으면 전량 억제", lambda it, r: deficient(r)),
        ("결여신호 게이트 + yes만", lambda it, r: deficient(r) and it["applies"] == "yes"),
        ("결여신호 + yes + CROSS제외", lambda it, r: deficient(r) and it["applies"] == "yes" and it["code"] not in CROSS),
    ]

    rows = []
    for name, keep in POLICIES:
        n_pt, n_lo, n_hi = boot(rate(neg, keep))
        p_pt, _, _ = boot(rate(pos, keep))
        rows.append({"policy": name, "neg_claim": round(n_pt, 3), "neg_ci95": [round(n_lo, 3), round(n_hi, 3)],
                     "pos_claim": round(p_pt, 3), "discrimination": round(p_pt - n_pt, 3)})

    # 진단: 음성에서 어떤 기인물/출처/applies가 나오나
    gim = Counter()
    kindc = Counter()
    appl = Counter()
    for p in neg:
        r = per[p]
        for g in r["gimulmul"]:
            gim[g.split("(")[0].strip()] += 1
        for rep in r["reps"]:
            for it in rep:
                appl[it["applies"]] += 1
                kindc[r["kind"].get(it["code"], "?")] += 1
    defic_neg = sum(1 for p in neg if deficient(per[p]))
    defic_pos = sum(1 for p in pos if deficient(per[p]))

    out = {"_note": "사후 탐색 — 같은 80장. 유망 정책은 남은 568장에서 사전등록 후 재측정 필요.",
           "n_neg": len(neg), "n_pos": len(pos),
           "deficiency_signal": {"neg_with_signal": defic_neg, "neg_total": len(neg),
                                 "pos_with_signal": defic_pos, "pos_total": len(pos)},
           "applies_distribution_on_neg": dict(appl), "kind_distribution_on_neg": dict(kindc),
           "top_gimulmul_on_neg": gim.most_common(15), "policies": rows}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== FP 게이트 탐색 (위반없음 {len(neg)} · 위반있음 {len(pos)}) ===")
    print(f"\n[결여 신호 보유] 음성 {defic_neg}/{len(neg)}장 · 양성 {defic_pos}/{len(pos)}장")
    print(f"[음성 노출의 applies 분포] {dict(appl)}")
    print(f"[음성 노출의 출처 분포] {dict(kindc)}")
    print("\n[음성 사진에서 식별된 기인물 상위]")
    for g, k in gim.most_common(12):
        print(f"  {g[:28]:30} {k:>3}/{len(neg)}장")
    print(f"\n{'정책':34}{'음성':>9}{'CI95':>18}{'양성':>9}{'판별력Δ':>10}")
    for r in rows:
        print(f"{r['policy']:34}{r['neg_claim']:>9.3f}  [{r['neg_ci95'][0]:.3f},{r['neg_ci95'][1]:.3f}]"
              f"{r['pos_claim']:>9.3f}{r['discrimination']:>10.3f}")
    print(f"\n→ {OUT.name} · {RAW.name}")


if __name__ == "__main__":
    main()
