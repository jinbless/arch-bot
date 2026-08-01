#!/usr/bin/env python3
"""정식 FP 측정 — 채점 (사전등록: docs/dev-notes/fp-measurement-2026-08-01.md).

입력: 사람 판정 CSV(뷰어 내보내기 `fp_binary_filled.csv`: photo_file, verdict[y|n|m], memo)
     + 파이프라인 출력 `fp_run_nolabel.json`

주지표(사전선언): **top1 FP율** = '위반 없음(n)' 확정 사진에서 top1이 나온 비율(2rep 평균).
 - 이 파이프라인의 top1은 정의상 applies∈{yes,maybe}만 남은 목록의 1위다(랭커가 no로 판정한 건 애초에 빠진다).
 - 부지표: top3 FP율 · 사진당 노출 수 · abstain율 · 주장 조문 분포 · '위반 있음' 사진과의 대비.
'모호(m)'는 주지표에서 제외하고 따로 보고한다.

사용: python scripts/fp_score.py [--judged real-test-photo/no_label_photo/fp_binary_filled.csv]
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
RUN = ART / "fp_run_nolabel.json"
OUT = ART / "fp_results.json"
OUT_MD = ART / "fp_results.md"
DEFAULT_JUDGED = REPO / "real-test-photo" / "no_label_photo" / "fp_binary_filled.csv"


def boot_ci(vals: list[float], n: int = 4000, seed: int = 17) -> tuple[float, float, float]:
    """사진 단위 부트스트랩 — 비율의 95% CI."""
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

    run = json.loads(RUN.read_text(encoding="utf-8"))
    per = {r["photo"]: r for r in run["per_photo"]}

    verdict, memo = {}, {}
    with args.judged.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("verdict") or "").strip().lower()
            if v in ("y", "n", "m"):
                verdict[r["photo_file"]] = v
                if (r.get("memo") or "").strip():
                    memo[r["photo_file"]] = r["memo"].strip()

    judged = [p for p in per if p in verdict]
    neg = [p for p in judged if verdict[p] == "n"]      # 위반 없음 확정 → 주지표 분모
    pos = [p for p in judged if verdict[p] == "y"]
    amb = [p for p in judged if verdict[p] == "m"]
    if not neg:
        raise SystemExit("'위반 없음(n)' 판정이 0장 — 채점 불가")

    def top1_rate(ps: list[str]) -> list[float]:
        """사진별 top1 주장 비율(2rep 평균) — 목록이 비면 0(기권)."""
        return [sum(1 for t in per[p]["top1_reps"] if t) / len(per[p]["top1_reps"]) for p in ps]

    def any_claim_rate(ps: list[str], k: int) -> list[float]:
        return [sum(1 for rep in per[p]["reps"] if rep["ranked"][:k]) / len(per[p]["reps"]) for p in ps]

    fp1 = boot_ci(top1_rate(neg))
    fp3 = boot_ci(any_claim_rate(neg, 3))
    exposure = boot_ci([per[p]["n_ranked_avg"] for p in neg])
    abst = boot_ci([per[p]["abstain_rate"] for p in neg])
    pos1 = boot_ci(top1_rate(pos)) if pos else (0.0, 0.0, 0.0)

    asserted = Counter()
    for p in neg:
        for rep in per[p]["reps"]:
            for c in rep["ranked"][:3]:
                asserted[c] += 1

    verdict_band = ("현 구성 프로덕션 노출 부적합(기권 경로 선행 필요)" if fp1[0] >= 0.50
                    else "표기·임계 보완 후 재측정" if fp1[0] >= 0.20
                    else "현 표기 정책 하 조건부 노출 가능")

    out = {
        "n_judged": len(judged), "n_neg": len(neg), "n_pos": len(pos), "n_ambiguous": len(amb),
        "primary_top1_fp": {"point": round(fp1[0], 3), "ci95": [round(fp1[1], 3), round(fp1[2], 3)]},
        "top3_fp": {"point": round(fp3[0], 3), "ci95": [round(fp3[1], 3), round(fp3[2], 3)]},
        "exposure_mean": {"point": round(exposure[0], 2), "ci95": [round(exposure[1], 2), round(exposure[2], 2)]},
        "abstain_mean": {"point": round(abst[0], 3), "ci95": [round(abst[1], 3), round(abst[2], 3)]},
        "positive_top1_claim": {"point": round(pos1[0], 3), "n": len(pos)},
        "pre_registered_band": verdict_band,
        "top_asserted_on_negatives": asserted.most_common(15),
        "ambiguous_photos": [{"photo": p, "memo": memo.get(p, "")} for p in amb],
        "per_photo": [{"photo": p, "verdict": verdict[p], "top1_reps": per[p]["top1_reps"],
                       "n_ranked_avg": per[p]["n_ranked_avg"], "abstain": per[p]["abstain_rate"],
                       "ranked_rep0": per[p]["reps"][0]["ranked"][:5], "memo": memo.get(p, "")}
                      for p in judged],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"=== 정식 FP 측정 (사전등록 80장 표본 · 판정 {len(judged)}장) ===",
         f"위반없음 {len(neg)} · 위반있음 {len(pos)} · 모호 {len(amb)}", "",
         f"[주지표] top1 FP율 {fp1[0]:.3f} CI[{fp1[1]:.3f},{fp1[2]:.3f}]  → {verdict_band}",
         f"[부지표] top3 주장률 {fp3[0]:.3f} · 사진당 노출 {exposure[0]:.1f}건 · abstain {abst[0]:.3f}",
         f"[대비] '위반 있음' 사진의 top1 주장률 {pos1[0]:.3f} (n={len(pos)})", "",
         "[위반없음 사진에서 많이 주장된 조문]"]
    L += [f"  {c} {k}회" for c, k in asserted.most_common(10)]
    L += ["", "[한계] 라벨 없음≠위반 없음이라 사람 판정이 분모. 판정자는 감독관이 아니며 [B]절차 위반은 원리적으로 미검출.",
          "       오탐만 측정한다 — 누락(FN)은 이 측정의 대상이 아니다."]
    txt = "\n".join(L)
    OUT_MD.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\n→ {OUT.name} · {OUT_MD.name}")


if __name__ == "__main__":
    main()
