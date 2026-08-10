#!/usr/bin/env python3
"""비계 공통 상속(A안) 항목 16건의 Sol 검수 프로브.

무엇을 묻나: 상속된 각 항목에 대해 ①이 그룹(사용 중 사진 전제) 흐름에 포함이 적절한가
②배치 칸이 적절한가 ③한정 문구가 조문 문언과 일치하는가. **조문 원문을 그대로** 준다
(요약·의역 금지 원칙). 재료는 flow_slice_all.json의 '비계 공통 상속' 항목에서 직접 뽑는다 —
프로브 입력과 실제 데이터가 어긋나면 검수가 무의미하다.

사용: OPENAI_API_KEY 필요. python3 probe_bike_inherit_sol.py [model]
출력: bike_inherit_sol_verdicts.json (이 폴더)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
TEXTS = REPO / "data-team" / "02-extraction" / "pipe-A" / "data" / "article-texts.json"
OUT = HERE / "bike_inherit_sol_verdicts.json"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-sol"

SLOT_KO = {"PLAN": "계획·사전조사", "ASSIGN": "인적 배치·자격", "PRECHECK": "작업 시작 전 점검",
           "EXEC": "작업 중", "POST": "종료·이탈", "PERIODIC": "정기점검"}

SYS = (
    "너는 산업안전보건 법령 검토자다. 산업안전보건기준에 관한 규칙의 비계 공통 조문을 구체 비계"
    " 유형의 '작업 흐름'(사업주가 그 비계를 사용하는 작업에서 지켜야 할 의무의 시간축 배치)에"
    " 상속시킨 결과를 검수한다. 전제: 화면은 '그 비계를 사용 중인 현장 사진'에서 출발하므로,"
    " 조립·해체 전용 절차는 이 흐름에 넣지 않는 것이 편집 방침이다. 각 항목에 대해 원문 문언을"
    " 근거로 판정하라. 추측 금지 — 원문에 없는 내용을 지어내지 말라.")

SCHEMA = {"name": "verdicts", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"idx": {"type": "integer"},
                       "판정": {"type": "string", "enum": ["적합", "부적합", "조건부"]},
                       "사유": {"type": "string"}},
        "required": ["idx", "판정", "사유"]}}},
    "required": ["verdicts"]}}


def main() -> None:
    fl = json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))
    rule = json.loads(TEXTS.read_text(encoding="utf-8"))["laws"]["RULE"]

    probes = []
    for r in fl["rows"]:
        if "비계" not in (r.get("path") or ""):
            continue
        for slot, its in r["items"].items():
            for it in its:
                if "비계 공통 상속" not in (it.get("source") or ""):
                    continue
                probes.append({"group": r["src_key"], "slot": slot, "ref": it["ref"],
                               "source": it["source"], "evidence": it.get("evidence", "")})
    if not probes:
        raise SystemExit("상속 항목이 없다 — build_flow_slice_all을 먼저 실행했는가?")

    lines = []
    for i, p in enumerate(probes):
        e = rule[p["ref"]]
        limit = p["source"].split("·", 1)[1].strip().rstrip(")") if "·" in p["source"] else "(없음)"
        lines.append(
            f"[{i}] 대상 그룹: {p['group']} / 배치 칸: {SLOT_KO[p['slot']]} / "
            f"한정 문구: {limit}\n"
            f"    {p['ref']} {e['title']} — 원문: {e['fullText'][:400]}")

    user = ("다음은 비계 공통 조문을 구체 비계 그룹 흐름에 상속시킨 항목들이다. 각 항목에 대해\n"
            "①이 그룹의 '사용 중' 흐름에 포함되는 것이 적절한가 ②배치 칸이 적절한가\n"
            "③한정 문구(있는 경우)가 원문 문언과 일치하는가를 종합해 적합/부적합/조건부로 판정하고\n"
            "사유를 한 줄로 적어라. 부적합·조건부는 반드시 원문 문언을 인용해 근거를 대라.\n\n"
            + "\n".join(lines))

    client = OpenAI()
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": SCHEMA})
    verdicts = json.loads(r.choices[0].message.content)["verdicts"]

    out = {"_model": MODEL, "n_probes": len(probes),
           "items": [{**probes[v["idx"]], "판정": v["판정"], "사유": v["사유"]}
                     for v in verdicts if 0 <= v["idx"] < len(probes)]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    print(f"판정 분포: {Counter(v['판정'] for v in verdicts).most_common()}")
    for it in out["items"]:
        if it["판정"] != "적합":
            print(f"  [{it['판정']}] {it['group']} · {it['slot']} · {it['ref']}: {it['사유'][:120]}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
