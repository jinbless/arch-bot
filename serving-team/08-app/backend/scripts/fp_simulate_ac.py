#!/usr/bin/env python3
"""A+C 적용 후 화면이 실제로 어떻게 바뀌는지 시뮬레이션 (LLM 호출 0).

A안 = `applies == "yes"`만 노출 / C안 = SSOT §6.2 포괄조문(제3·4·22조)을 '공통 점검'으로 분리.
입력은 이미 확보된 `fp_gate_raw.json`(applies·kind 보존) + 사람 이진 판정 CSV.

⚠ 같은 80장 위의 시뮬레이션이다 — 정책을 이 표본으로 고른 뒤 같은 표본에서 재는 것이므로
   낙관 편향이 있다. 채택 후에는 손대지 않은 568장에서 사전등록 재측정이 필요하다.
⚠ 실제 서빙은 후보 집합 자체가 이 실행과 동일해야 같은 결과가 나온다(모델·프롬프트 동일 전제).

사용: python scripts/fp_simulate_ac.py
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
RAW = ART / "fp_gate_raw.json"
JUDGED = REPO / "real-test-photo" / "label_photo" / "fp_binary_filled.csv"
OUT = ART / "fp_simulate_ac.json"

GENERIC = {"제3조", "제4조", "제22조"}      # SSOT 00-master §6.2 전역 강등


def main() -> None:
    per = {r["photo"]: r for r in json.loads(RAW.read_text(encoding="utf-8"))["per_photo"]}
    verdict = {}
    with JUDGED.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("verdict") or "").strip().lower()
            if v in ("y", "n", "m"):
                verdict[r["photo_file"]] = v
    neg = [p for p in per if verdict.get(p) == "n"]
    pos = [p for p in per if verdict.get(p) == "y"]

    def split(pf: str, rep_i: int, conditional: bool = False) -> tuple[list[str], list[str], list[str]]:
        """(현행 노출, 위반목록, 공통점검)

        conditional=False: 포괄조문을 항상 공통으로 내린다(단순 C).
        conditional=True : SSOT §6.2 원문대로 **특정조문이 있을 때만** 내린다
                           ("단독 명확한 정리불량/전도일 때만 상위") — 포괄조문뿐이면 그대로 위반목록에 둔다.
        """
        rep = per[pf]["reps"][rep_i]
        cur = [x["code"] for x in rep if x["applies"] in ("yes", "maybe")]
        yes = [x["code"] for x in rep if x["applies"] == "yes"]
        specific = [c for c in yes if c not in GENERIC]
        generic = [c for c in yes if c in GENERIC]
        if conditional and not specific:
            return cur, generic, []          # 포괄조문 단독 → 강등하지 않음
        return cur, specific, generic

    def stats(ps: list[str], conditional: bool) -> dict:
        cur_any = viol_any = both_empty = viol_n = 0.0
        for p in ps:
            k = len(per[p]["reps"])
            cur_any += sum(1 for i in range(k) if split(p, i, conditional)[0]) / k
            viol_any += sum(1 for i in range(k) if split(p, i, conditional)[1]) / k
            both_empty += sum(1 for i in range(k)
                              if not split(p, i, conditional)[1] and not split(p, i, conditional)[2]) / k
            viol_n += sum(len(split(p, i, conditional)[1]) for i in range(k)) / k
        n = max(len(ps), 1)
        return {"n_photos": len(ps),
                "현행_주장률": round(cur_any / n, 3), "위반목록_주장률": round(viol_any / n, 3),
                "완전침묵률": round(both_empty / n, 3), "위반목록_평균건수": round(viol_n / n, 2)}

    variants = {
        "A만(yes 노출, 분리 없음)": None,
        "A+C 단순(포괄조문 항상 분리)": False,
        "A+C 조건부(SSOT §6.2 — 특정조문 있을 때만 분리)": True,
    }
    table = {}
    for name, cond in variants.items():
        if cond is None:
            # 분리 없음 = 포괄조문도 위반목록에 남김
            def s(ps):
                out = 0.0
                for p in ps:
                    k = len(per[p]["reps"])
                    out += sum(1 for i in range(k)
                               if [x for x in per[p]["reps"][i] if x["applies"] == "yes"]) / k
                return round(out / max(len(ps), 1), 3)
            table[name] = {"정상_위반목록_주장률": s(neg), "위반_위반목록_주장률": s(pos)}
        else:
            a, b = stats(neg, cond), stats(pos, cond)
            table[name] = {"정상_위반목록_주장률": a["위반목록_주장률"],
                           "위반_위반목록_주장률": b["위반목록_주장률"],
                           "정상_완전침묵률": a["완전침묵률"], "위반_완전침묵률": b["완전침묵률"]}

    s_neg, s_pos = stats(neg, False), stats(pos, False)
    moved = Counter()
    for p in neg + pos:
        for i in range(len(per[p]["reps"])):
            for c in split(p, i)[2]:
                moved[c] += 1

    out = {"_note": "A+C 시뮬(같은 80장 — 낙관 편향 있음). 채택 후 568장에서 사전등록 재측정 필요.",
           "generic_set": sorted(GENERIC), "variants": table,
           "negatives_simple_C": s_neg, "positives_simple_C": s_pos,
           "moved_to_common_simple_C": moved.most_common()}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=== A/C 변형 비교 (같은 80장 · '위반목록'에 뭐라도 뜨는 비율) ===")
    print(f"{'변형':46}{'정상 67장':>10}{'위반 7장':>10}")
    print(f"{'현행(yes+maybe, 분리 없음)':46}{0.948:>10}{1.0:>10}")
    for name, v in table.items():
        print(f"{name:46}{v['정상_위반목록_주장률']:>10}{v['위반_위반목록_주장률']:>10}")
    print(f"\n공통 점검으로 이동한 조문(단순 C): {dict(moved)}")
    print(f"\n→ {OUT.name}")


if __name__ == "__main__":
    main()
