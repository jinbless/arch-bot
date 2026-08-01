#!/usr/bin/env python3
"""별표 3의 작업종류 19종 전체에 대해 흐름 골격 6단계가 채워지는지 일괄 확인 (LLM 호출 0).

수직 슬라이스(build_flow_slice.py)를 지게차 1종으로 검증했으니, 나머지로 확대해
**어느 칸이 어디서 비는지** 분포를 본다. 빈 칸의 분포가 다음 데이터 작업을 정한다.

각 작업종류의 재료:
  PLAN     별표 4(작업명 매칭) + 제38조
  ASSIGN   별표 2(좌표/이름 매칭) + 제39조
  PRECHECK 별표 3(해당 행) + 제35조
  EXEC     해당 절/관 조문(전용 + 절 총칙)
  POST     종료·이탈 성격 조문
  PERIODIC 가이드 절차(제목 매칭으로 찾은 대표 가이드)

⚠ '칸이 차는가'만 본다. 항목이 그 단계에 맞는지(라벨 정확도)는 사람 검수 대상.
⚠ 가이드는 제목 키워드 매칭이라 대표성이 보장되지 않는다 — 미검증 연결로 표시한다.

사용: python data-team/01-parsing/rule-appendices/build_flow_slice_all.py
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARSED = Path(__file__).resolve().parent / "parsed"
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"

SKELETON = [("PLAN", "계획"), ("ASSIGN", "인적"), ("PRECHECK", "작업전"),
            ("EXEC", "작업중"), ("POST", "종료"), ("PERIODIC", "정기")]

LEX = {
    "PLAN": r"사전조사|작업계획서|계획을 수립|설계도서",
    "ASSIGN": r"작업지휘자|지휘자|유도자|신호수|자격|특별교육|선임|배치",
    "PRECHECK": r"작업 ?시작 ?전|시작하기 전|사용 ?전|시동 ?전|작업 전 확인|미리 점검",
    "POST": r"이탈|종료|해체|반출|정리정돈|작업 후",
    "PERIODIC": r"정기|주기|월 1회|연 1회|자체검사",
}

# 별표 3 작업종류 → 가이드 검색 키워드(제목 매칭용). 없으면 가이드 없이 채점.
GUIDE_KW = {
    "1": "프레스", "2": "로봇", "3": "공기압축기", "4": "크레인 안전작업", "5": "이동식 크레인",
    "6": "리프트", "7": "곤돌라", "8": "와이어로프", "9": "지게차의 안전작업", "10": "구내운반",
    "11": "고소작업대", "12": "화물자동차", "13": "컨베이어", "14": "건설기계",
    "14의2": "용접", "15": "방폭", "16": "중량물", "17": "양화장치", "18": "줄걸이",
}


def coord_of(section: str) -> tuple:
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        if lvl == "편":
            p = n
        elif lvl == "장":
            j = n
        elif lvl == "절":
            jeol = n
        elif lvl == "관":
            gwan = n
    return (p, j, jeol, gwan)


def phase_of(text: str) -> str:
    for ph in ("PLAN", "ASSIGN", "PRECHECK", "POST", "PERIODIC"):
        if re.search(LEX[ph], text or ""):
            return ph
    return "EXEC"


def pg(sql: str) -> list[str]:
    r = subprocess.run(["docker", "exec", "kosha-pg", "sh", "-c",
                        f'psql -U $POSTGRES_USER -d $POSTGRES_DB -tAF"|" -c "{sql}"'],
                       capture_output=True, text=True, encoding="utf-8")
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def main() -> None:
    sigs = [json.loads(l) for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    a3 = json.loads((PARSED / "appendix-03.json").read_text(encoding="utf-8"))
    a4 = json.loads((PARSED / "appendix-04.json").read_text(encoding="utf-8"))
    a2 = json.loads((PARSED / "appendix-02.json").read_text(encoding="utf-8"))

    art_coord = [(s, coord_of(s.get("section", ""))) for s in sigs]
    report = []

    for r in a3["rows"]:
        no, subj = r["no"], r["subject"]
        p, j, jeol, gwan = coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", r.get("section_ref", "")))
        slots = {k: 0 for k, _ in SKELETON}
        detail = {k: [] for k, _ in SKELETON}

        def add(ph, txt):
            slots[ph] += 1
            if len(detail[ph]) < 3:
                detail[ph].append(txt)

        # PRECHECK — 별표 3 본인 행
        for it in r["items"]:
            add("PRECHECK", it)
        add("PRECHECK", "제35조 관리감독자 점검")

        # EXEC/POST — 해당 절/관 조문 + 절 총칙.
        # ★ 편·장까지 일치시켜야 한다. 절 번호만 보면 다른 편의 같은 번호 절을 통째로 끌어와
        #   슬링(제2편제6장제2절)에 140건이 붙는다(join_coverage에서 이미 겪은 버그).
        arts = [s for s, c in art_coord
                if jeol is not None and c[0] == p and c[1] == j and c[2] == jeol
                and (gwan is None or c[3] in (gwan, None))]
        for s in arts:
            add(phase_of(s.get("title", "")), f"{s['article_code']} {s.get('title','')[:20]}")

        # PLAN — 별표 4 이름 매칭
        key = re.sub(r"(을|를|이|가)?\s*(사용하여|사용하는|가동할|취급하는).*", "", subj).strip()
        for rr in a4["rows"]:
            if key and (key[:4] in rr["subject"] or rr["subject"][:6] in subj):
                for it in rr["items"]:
                    add("PLAN", it)
                for it in (rr.get("values") or {}).get("사전조사 내용", []) or []:
                    add("PLAN", it)
        add("PLAN", "제38조 사전조사·작업계획서")

        # ASSIGN — 별표 2 좌표/이름
        for rr in a2["rows"]:
            cc = coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", rr.get("section_ref", "")))
            if (jeol is not None and cc[:3] == (p, j, jeol)) or (key and key[:4] and key[:4] in rr["subject"]):
                for it in rr["items"]:
                    add("ASSIGN", it)
        add("ASSIGN", "제39조 작업지휘자")

        # PERIODIC — 대표 가이드 절차
        kw = GUIDE_KW.get(no, "")
        gcode = ""
        if kw:
            g = pg(f"select guide_code from kosha_guides where title like '%{kw}%' order by guide_code limit 1")
            gcode = g[0] if g else ""
        if gcode:
            for ln in pg(f"select replace(process_name,'|','/') from work_processes "
                         f"where source_guide='{gcode}' order by process_order"):
                add(phase_of(ln), ln[:34])

        filled = sum(1 for k, _ in SKELETON if slots[k])
        report.append({"no": no, "subject": subj[:26], "coord": [jeol, gwan], "guide": gcode,
                       "slots": slots, "filled": filled, "detail": detail})

    print(f"=== 별표 3 작업종류 {len(report)}종 × 골격 6단계 채움 현황 ===")
    print(f"{'no':>5} {'작업종류':26} {'가이드':12} " + " ".join(f"{lab:>5}" for _, lab in SKELETON) + "  채움")
    for x in report:
        cells = " ".join(f"{x['slots'][k]:>5}" for k, _ in SKELETON)
        print(f"{x['no']:>5} {x['subject'][:24]:26} {x['guide'][:12]:12} {cells}  {x['filled']}/6")

    full = sum(1 for x in report if x["filled"] == 6)
    print(f"\n6/6 채움: {full}/{len(report)}종")
    for k, lab in SKELETON:
        empty = [x["no"] for x in report if not x["slots"][k]]
        print(f"  {lab:6} 빈 종류 {len(empty):2d}종 {('· ' + ', '.join(empty)) if empty else ''}")

    out = ART / "flow_slice_all.json"
    out.write_text(json.dumps({"_note": "별표 3 19종 × 골격 채움. 칸이 차는지만 본다(라벨 정확도 별도).",
                               "rows": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out.name}")


if __name__ == "__main__":
    main()
