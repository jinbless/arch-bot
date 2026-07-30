#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1·2차 라벨 병합 — label_curation_gold.csv(원본 불변) + label_round2_filled.csv → gold v2.

입력:
  real-test-photo/label_photo/label_curation_gold.csv     (1차 원본 — 절대 수정하지 않음)
  real-test-photo/label_photo/label_round2_filled.csv     (뷰어 내보내기: source=round2 신규 / r1 수정)
출력:
  real-test-photo/label_photo/label_curation_gold_v2.csv  (병합본 + provenance: source·orig_match·revised)

병합 규칙:
  - r1 행에 match(수정값)가 있고 orig_match와 다르면 → 그 판정으로 교체(revised=y, orig_match 보존)
  - round2 행에 match가 있으면 → 신규 판정으로 추가(source=round2)
  - 나머지 1차 행은 그대로 승계(EXCLUDED 포함)
⚠ 재채점 시 원본 gold(v1)와 v2 지표를 나란히 보고할 것 — 라벨 변화 이득과 코드 변화 이득을 섞지 않는다.

사용: python3 scripts/merge_label_rounds.py [--filled 경로]
"""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
LP = REPO / "real-test-photo/label_photo"
GOLD = LP / "label_curation_gold.csv"
DEFAULT_FILLED = LP / "label_round2_filled.csv"
OUT = LP / "label_curation_gold_v2.csv"


def norm_code(c):
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filled", default=str(DEFAULT_FILLED))
    args = ap.parse_args()
    filled_p = Path(args.filled)
    if not filled_p.exists():
        raise SystemExit(f"내보내기 CSV 없음: {filled_p} — 뷰어에서 'CSV 내보내기' 후 이 위치에 두거나 --filled 지정")

    # 2차 결과 로드
    revisions, additions = {}, []   # revisions[(pf,code)] = (orig, new)
    with filled_p.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            pf, code = r["photo_file"], norm_code(r["article_code"])
            m = (r.get("match") or "").strip().lower()
            src = (r.get("source") or "").strip()
            if src == "r1":
                orig = (r.get("orig_match") or "").strip().lower()
                if m and m != orig:
                    revisions[(pf, code)] = (orig, m)
            elif src == "round2" and m:
                additions.append({**r, "article_code": code, "match": m})

    # 1차 원본 승계 + 수정 적용
    out_rows, applied = [], set()
    with GOLD.open(encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        base_fields = rd.fieldnames
        for r in rd:
            pf, code = r["photo_file"], norm_code(r["article_code"])
            row = {k: r.get(k, "") for k in base_fields}
            row["article_code"] = code
            row["orig_match"], row["revised"] = "", ""
            key = (pf, code)
            if key in revisions:
                orig, new = revisions[key]
                row["orig_match"], row["match"], row["revised"] = orig, new, "y"
                applied.add(key)
            out_rows.append(row)

    orphan = [k for k in revisions if k not in applied]  # 1차에 없는 키의 수정(정규화 불일치 등)
    for a in additions:
        out_rows.append({"row": "", "pjts_id": a.get("pjts_id", ""), "photo_file": a["photo_file"],
                         "ognl": a.get("ognl", ""), "article_code": a["article_code"],
                         "article_title": a.get("article_title", ""), "observable": a.get("observable", ""),
                         "source": "round2", "match": a["match"], "orig_match": "", "revised": ""})

    fields = list(dict.fromkeys((base_fields or []) + ["orig_match", "revised"]))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, row in enumerate(out_rows, 1):
            row["row"] = i
            w.writerow({k: row.get(k, "") for k in fields})

    # 요약
    rev_kinds = Counter(f"{o or '빈칸'}→{n}" for o, n in revisions.values())
    add_kinds = Counter(a["match"] for a in additions)
    y2 = sum(1 for r in out_rows if (r.get("match") or "").strip().lower() == "y")
    print(f"병합 완료 → {OUT.name} (총 {len(out_rows)}행 · v1 {len(out_rows)-len(additions)} + 신규 {len(additions)})")
    print(f"1차 수정 {len(applied)}건: {dict(rev_kinds)}")
    if orphan:
        print(f"⚠ 미적용 수정 {len(orphan)}건(1차에 해당 행 없음): {orphan[:5]}")
    print(f"신규 판정 {len(additions)}건: {dict(add_kinds)}")
    print(f"v2 match=y 총 {y2}건")
    print("⚠ 재채점 시 v1/v2 지표를 나란히 보고할 것(라벨 변화 vs 코드 변화 분리).")


if __name__ == "__main__":
    main()
