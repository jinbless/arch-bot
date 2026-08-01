#!/usr/bin/env python3
"""FP Round 2 축 1 채점 — A+C를 켠 채로 손대지 않은 표본에서 잰 오탐 (사전등록 준수).

주지표(사전선언): **위반 목록 top1 FP율** = '위반 없음' 확정 사진에서 위반 목록(공통 점검 제외)에
무언가 뜬 비율(2rep 평균). 공통 점검은 설계상 '이 사진의 위반'이 아니므로 분모에서 뺀다.
현행/A만/A+C를 나란히 보고한다(정책 효과를 새 표본에서 재확인).

밴드(사전선언): >=0.50 부적합 / 0.20~0.50 보완 후 재측정 / <0.20 조건부 노출 가능.

사용: python scripts/fp_round2_score.py [--judged <csv>]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
RAW = ART / "fp_round2_raw.json"
OUT = ART / "fp_round2_results.json"
OUT_MD = ART / "fp_round2_results.md"
DEFAULT_JUDGED = REPO / "real-test-photo" / "no_label_photo" / "fp_binary_filled_r2.csv"

GENERIC = {"제3조", "제4조", "제22조"}      # SSOT 00-master §6.2


def boot(vals: list[float], n: int = 4000, seed: int = 17) -> tuple[float, float, float]:
    if not vals:
        return (0.0, 0.0, 0.0)
    rnd = random.Random(seed)
    pt = sum(vals) / len(vals)
    bs = sorted(sum(vals[rnd.randrange(len(vals))] for _ in range(len(vals))) / len(vals) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judged", type=Path, default=DEFAULT_JUDGED)
    args = ap.parse_args()

    per = {r["photo"]: r for r in json.loads(RAW.read_text(encoding="utf-8"))["per_photo"]}
    verdict, memo = {}, {}
    with args.judged.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("verdict") or "").strip().lower()
            if v in ("y", "n", "m"):
                verdict[r["photo_file"]] = v
                if (r.get("memo") or "").strip():
                    memo[r["photo_file"]] = r["memo"].strip()

    judged = [p for p in per if p in verdict]
    neg = [p for p in judged if verdict[p] == "n"]
    pos = [p for p in judged if verdict[p] == "y"]
    amb = [p for p in judged if verdict[p] == "m"]
    unknown = [p for p in verdict if p not in per]
    if not neg:
        raise SystemExit("'위반 없음(n)' 판정이 0장 — 채점 불가")

    def lists(pf: str, rep_i: int, policy: str) -> tuple[list[str], list[str]]:
        """(위반 목록, 공통 점검)"""
        rep = per[pf]["reps"][rep_i]["ranked"]
        if policy == "current":
            return [x["code"] for x in rep if x["applies"] in ("yes", "maybe")], []
        yes = [x["code"] for x in rep if x["applies"] == "yes"]
        if policy == "A":
            return yes, []
        return [c for c in yes if c not in GENERIC], [c for c in yes if c in GENERIC]

    def rate(ps: list[str], policy: str, what: str) -> list[float]:
        out = []
        for p in ps:
            k = len(per[p]["reps"])
            hit = 0
            for i in range(k):
                v, c = lists(p, i, policy)
                hit += 1 if (v if what == "viol" else (not v and not c) if what == "silent" else c) else 0
            out.append(hit / k)
        return out

    pol = {}
    for policy, label in (("current", "현행(yes+maybe)"), ("A", "A만(yes)"), ("AC", "A+C(채택안)")):
        n_pt, n_lo, n_hi = boot(rate(neg, policy, "viol"))
        p_pt, _, _ = boot(rate(pos, policy, "viol"))
        sil = boot(rate(neg, policy, "silent"))
        pol[policy] = {"label": label,
                       "neg_violation_claim": [round(n_pt, 3), round(n_lo, 3), round(n_hi, 3)],
                       "pos_violation_claim": round(p_pt, 3),
                       "neg_full_silence": round(sil[0], 3),
                       "discrimination": round(p_pt - n_pt, 3)}

    fp1 = pol["AC"]["neg_violation_claim"][0]
    band = ("현 구성 프로덕션 노출 부적합" if fp1 >= 0.50
            else "표기·임계 보완 후 재측정" if fp1 >= 0.20 else "현 표기 정책 하 조건부 노출 가능")

    asserted = Counter()
    for p in neg:
        for i in range(len(per[p]["reps"])):
            for c in lists(p, i, "AC")[0]:
                asserted[c] += 1

    out = {"round": 2, "n_judged": len(judged), "n_neg": len(neg), "n_pos": len(pos), "n_ambiguous": len(amb),
           "n_unmatched_rows": len(unknown),
           "primary_AC_violation_fp": pol["AC"]["neg_violation_claim"],
           "pre_registered_band": band, "policies": pol,
           "top_asserted_on_negatives_AC": asserted.most_common(12),
           "ambiguous": [{"photo": p, "memo": memo.get(p, "")} for p in amb],
           "per_photo": [{"photo": p, "verdict": verdict[p],
                          "AC_violation_rep0": lists(p, 0, "AC")[0],
                          "AC_common_rep0": lists(p, 0, "AC")[1],
                          "current_rep0": lists(p, 0, "current")[0][:6],
                          "memo": memo.get(p, "")} for p in judged]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"=== FP Round 2 (새 표본 80장 · 판정 {len(judged)}장 — 위반없음 {len(neg)} · 있음 {len(pos)} · 모호 {len(amb)}) ===",
         "", f"{'정책':22}{'정상 위반목록':>12}{'CI95':>18}{'위반 위반목록':>12}{'정상 완전침묵':>12}"]
    for k in ("current", "A", "AC"):
        v = pol[k]
        L.append(f"{v['label']:22}{v['neg_violation_claim'][0]:>12.3f}"
                 f"  [{v['neg_violation_claim'][1]:.3f},{v['neg_violation_claim'][2]:.3f}]"
                 f"{v['pos_violation_claim']:>12.3f}{v['neg_full_silence']:>12.3f}")
    L += ["", f"[주지표] A+C 위반목록 top1 FP율 {fp1:.3f} → {band}", "",
          "[정상 사진에서 위반 목록에 남은 조문]"]
    L += [f"  {c} {k}회" for c, k in asserted.most_common(10)]
    L += ["", "[한계] 라벨 없음≠위반 없음 — 사람 판정이 분모. 판정자는 감독관이 아니며 [B]절차 위반은 미검출.",
          "       누락(FN)은 축 2(fp_recall_gold)에서 별도 측정."]
    txt = "\n".join(L)
    OUT_MD.write_text(txt, encoding="utf-8")
    print(txt)
    if unknown:
        print(f"\n⚠ 표본에 없는 판정 행 {len(unknown)}건 무시됨(라운드 CSV 혼동 여부 확인)")
    print(f"\n→ {OUT.name} · {OUT_MD.name}")


if __name__ == "__main__":
    main()
