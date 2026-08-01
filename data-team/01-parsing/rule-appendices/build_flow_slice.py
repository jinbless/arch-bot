#!/usr/bin/env python3
"""기인물 1종에 대한 '작업 전체 흐름' 수직 슬라이스 조립 (LLM 호출 0).

목적: 골격 6단계가 실제 데이터로 **다 채워지는지** 확인한다. 안 차는 칸이 곧 진짜 갭이다.

재료(전부 기존 데이터):
  PLAN     별표 4(사전조사·작업계획서) + 제38조
  ASSIGN   별표 2(관리감독자 직무) + 제39조
  PRECHECK 별표 3(작업시작 전 점검) + 제35조
  EXEC     해당 절/관 조문 + KOSHA 가이드 work_processes
  POST     종료·이탈 성격 조문/절차
  PERIODIC 정기점검 성격 절차

⚠ 이 스크립트는 '칸이 차는가'만 본다. 각 항목이 그 단계에 맞는지(라벨 정확도)는 별도 사람 검수 대상.

사용: python data-team/01-parsing/rule-appendices/build_flow_slice.py --gimulmul 지게차
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARSED = Path(__file__).resolve().parent / "parsed"
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"

SKELETON = [("PLAN", "계획·사전조사"), ("ASSIGN", "인적 배치·자격"), ("PRECHECK", "작업 시작 전 점검"),
            ("EXEC", "작업 중"), ("POST", "종료·이탈"), ("PERIODIC", "정기점검")]

# 조문/절차를 단계로 가르는 어휘 — 결정론 1차 신호(나머지는 EXEC 기본값)
LEX = {
    "PLAN": r"사전조사|작업계획서|계획을 수립|설계도서",
    "ASSIGN": r"작업지휘자|지휘자|유도자|신호수|자격|특별교육|선임|배치",
    "PRECHECK": r"작업 ?시작 ?전|시작하기 전|사용 ?전|시동 ?전|작업 전 확인|미리 점검",
    "POST": r"이탈|종료|해체|반출|정리정돈|작업 후",
    "PERIODIC": r"정기|주기|월 1회|연 1회|자체검사",
}


def coord_of(section: str) -> tuple:
    """'편2 안전기준 > 절10 … > 관2 지게차' 와 '편2 장1 절10 관2' 를 모두 받는다.
    (구분자를 '>'로만 쪼개면 별표 좌표를 정규화한 공백 구분 문자열이 통째로 한 토큰이 돼
     맨 앞 '편2'만 잡히고 절·관이 소실된다 — 지게차 슬라이스에서 별표 3이 통째로 누락됐던 버그)"""
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        p, j, jeol, gwan = (n, j, jeol, gwan) if lvl == "편" else \
                           (p, n, jeol, gwan) if lvl == "장" else \
                           (p, j, n, gwan) if lvl == "절" else (p, j, jeol, n)
    return (p, j, jeol, gwan)


def phase_of(text: str) -> str:
    for ph in ("PLAN", "ASSIGN", "PRECHECK", "POST", "PERIODIC"):
        if re.search(LEX[ph], text or ""):
            return ph
    return "EXEC"


def pg(sql: str) -> list[str]:
    cmd = ["docker", "exec", "kosha-pg", "sh", "-c",
           f'psql -U $POSTGRES_USER -d $POSTGRES_DB -tAF"|" -c "{sql}"']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gimulmul", default="지게차")
    ap.add_argument("--guide", default="B-M-11", help="해당 기인물 대표 가이드 코드 prefix")
    args = ap.parse_args()
    name = args.gimulmul

    sigs = [json.loads(l) for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by_code = {s["article_code"]: s for s in sigs}
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]

    # 1) 기인물 그룹 → 좌표(관) + 상위(절 총칙)
    gkey = next((k for k in gim if name in str(gim[k].get("gimulmul", "")) or name in k), None)
    if not gkey:
        raise SystemExit(f"기인물 그룹을 못 찾음: {name}")
    codes = [a["code"] for a in gim[gkey]["articles"]]
    coords = {coord_of(by_code[c]["section"]) for c in codes if c in by_code}
    p, j, jeol, gwan = sorted(coords)[0]
    own = [c for c in codes if c in by_code]
    sibling = [s["article_code"] for s in sigs
               if coord_of(s["section"])[:3] == (p, j, jeol) and s["article_code"] not in own]

    slots: dict[str, list] = {k: [] for k, _ in SKELETON}

    def add(ph: str, src: str, text: str, ref: str = "") -> None:
        slots[ph].append({"source": src, "text": text, "ref": ref})

    # 2) 별표 3 — 좌표 조인
    a3 = json.loads((PARSED / "appendix-03.json").read_text(encoding="utf-8"))
    for r in a3["rows"]:
        c = coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", r.get("section_ref", "")))
        if c[:4] == (p, j, jeol, gwan) or (c[:3] == (p, j, jeol) and c[3] is None):
            for it in r["items"]:
                add("PRECHECK", "별표 3", it, f"제35조제2항 · {r['subject'][:20]}")

    # 3) 별표 4 / 별표 2 — 이름 조인(좌표 없음)
    a4 = json.loads((PARSED / "appendix-04.json").read_text(encoding="utf-8"))
    grp_kw = re.split(r"[>]", gkey)[0].replace("절", "").strip()
    grp_kw = re.sub(r"^\d+\s*", "", grp_kw)
    for r in a4["rows"]:
        if any(w and w in r["subject"] for w in [name, grp_kw]):
            for it in r["items"]:
                add("PLAN", "별표 4", it, f"제38조제1항 · {r['subject'][:22]}")
            for it in (r.get("values") or {}).get("사전조사 내용", []) or []:
                add("PLAN", "별표 4(사전조사)", it, r["subject"][:22])
    a2 = json.loads((PARSED / "appendix-02.json").read_text(encoding="utf-8"))
    for r in a2["rows"]:
        cc = coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", r.get("section_ref", "")))
        if cc[:3] == (p, j, jeol) or any(w and w in r["subject"] for w in [name, grp_kw]):
            for it in r["items"]:
                add("ASSIGN", "별표 2", it, f"제35조제1항 · {r['subject'][:20]}")

    # 4) 조문 — 자기 관 + 상위 절 총칙, 어휘로 단계 배정
    for c in sorted(own + sibling, key=lambda x: int(re.match(r"제(\d+)", x).group(1))):
        s = by_code[c]
        # 단계 판정은 **조문 제목만** 본다. violation_scene은 사진 묘사라 단계 신호가 아니다 —
        # 제171조(전도 등의 방지)가 장면 문구 "유도자가 보이지 않는다" 때문에 ASSIGN으로 오분류됐었다.
        add(phase_of(s.get("title", "")),
            "조문(전용)" if c in own else "조문(절 총칙)", s.get("title", ""), c)
    for c in ("제38조", "제39조", "제35조", "제41조"):
        if c in by_code:
            add({"제38조": "PLAN", "제39조": "ASSIGN", "제35조": "PRECHECK",
                 "제41조": "POST"}[c],
                "조문(총칙)", by_code[c].get("title", ""), c)

    # ★ 상속 계층 추가 — '편2>장1>절1 기계 등의 일반기준'(제86~99) 14조는 기계·설비류 기인물 전체의
    #   상위 공통이다. 여기에 제89조(운전 시작 전 조치)·제93조(방호장치 해체 금지)·제99조(이탈 시 조치)가
    #   있어서, 이 층을 상속시키지 않으면 종료·이탈 칸이 조문 없이 가이드 절차에만 의존하게 된다.
    #   적용 대상은 편2·장1 소속 기인물(기계·기구 및 그 밖의 설비)로 한정한다.
    if (p, j) == (2, 1):
        for s in sigs:
            if "절1 기계 등의 일반기준" in s.get("section", "") and s["article_code"] not in own + sibling:
                add(phase_of(s.get("title", "")), "조문(기계 일반기준)", s.get("title", ""), s["article_code"])

    # 5) 가이드 절차
    rows = pg(f"select process_order, replace(process_name,'|','/'), coalesce(left(safety_measures,60),'') "
              f"from work_processes where source_guide like '{args.guide}%' order by process_order")
    for ln in rows:
        parts = ln.split("|")
        if len(parts) < 2:
            continue
        o, nm = parts[0], parts[1]
        add(phase_of(nm), "가이드 절차", nm, f"{args.guide} {o}단계")

    # 6) 리포트
    print(f"=== 수직 슬라이스: {name} ({gkey}) ===")
    print(f"좌표 편{p}·장{j}·절{jeol}·관{gwan} | 전용 조문 {len(own)} · 절 총칙 조문 {len(sibling)}\n")
    filled = 0
    for key, label in SKELETON:
        n = len(slots[key])
        filled += 1 if n else 0
        srcs = sorted({x["source"] for x in slots[key]})
        print(f"[{label}] {n}건  ({', '.join(srcs) if srcs else '비어 있음'})")
        for x in slots[key][:6]:
            print(f"    · {x['text'][:52]:54} ← {x['source']} {x['ref'][:24]}")
        if n > 6:
            print(f"    … 외 {n-6}건")
        print()
    print(f"→ 골격 {filled}/{len(SKELETON)} 칸 채움")
    out = ART / f"flow_slice_{name}.json"
    out.write_text(json.dumps({"gimulmul": name, "group": gkey, "coord": [p, j, jeol, gwan],
                               "slots": slots}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {out.name}")


if __name__ == "__main__":
    main()
