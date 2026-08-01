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
SI_DIR = ROOT / "data-team" / "01-parsing" / "safety-inspection" / "parsed"

SKELETON = [("PLAN", "계획"), ("ASSIGN", "인적"), ("PRECHECK", "작업전"),
            ("EXEC", "작업중"), ("POST", "종료"), ("PERIODIC", "정기")]

# ★ 조문 본문이 **스스로 적용 대상을 한정**하는 조문. 상위 계층(총칙·일반기준)에 있다고
#   무조건 상속시키면 프레스에 '차량계 운전위치 이탈 시 조치'가 붙는다(실제로 붙었다).
#   허용 좌표 (편,장,절)에 해당할 때만 주입한다.
SCOPED = {
    # 제41조①: 양중기 / 항타기·항발기 / 양화장치 를 운전하는 경우로 한정
    "제41조": {(2, 1, 9), (2, 1, 12), (2, 6, 2)},
    # 제99조①: 차량계 하역운반기계등, 차량계 건설기계 로 한정
    "제99조": {(2, 1, 10), (2, 1, 12)},
}

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


def load_inspection() -> tuple[dict, dict]:
    """별표 3 행번호 → 안전검사 대상 기계명, 기계명 → 기계 레코드.

    ★ 이름 매칭은 join_inspection_coverage.py 가 하고 coverage-report.json 에 남긴다.
      여기서 매칭을 다시 구현하면 두 곳이 조용히 어긋난다. 데이터로만 받는다.
    """
    cov, si = SI_DIR / "coverage-report.json", SI_DIR / "safety-inspection.json"
    if not (cov.exists() and si.exists()):
        print("⚠ 안전검사 데이터 없음 — 정기 칸을 가이드 절차로만 채운다\n")
        return {}, {}
    c = json.loads(cov.read_text(encoding="utf-8"))
    s = json.loads(si.read_text(encoding="utf-8"))
    return ({r["no"]: r["machines"] for r in c["periodic_slot"]["rows"]},
            {m["name"]: m for m in s["machines"]})


def cycle_lines(m: dict) -> list[str]:
    """주기 규정 → 읽을 수 있는 문장. 원문 문구를 이어 붙이기만 한다(해석 추가 금지)."""
    out, c = [], m.get("cycle") or {}
    base = " ".join(x for x in (c.get("first"), c.get("then")) if x)
    if base:
        out.append(f"{m['name']}: {base}")
    if c.get("special"):
        out.append(f"{m['name']}: {c['special']}")
    for v in m.get("cycle_variants") or []:
        vb = " ".join(x for x in (v.get("first"), v.get("then")) if x)
        if vb:
            out.append(f"{v['subtype']}: {vb}")
    return out


def pg(sql: str) -> list[str]:
    r = subprocess.run(["docker", "exec", "kosha-pg", "sh", "-c",
                        f'psql -U $POSTGRES_USER -d $POSTGRES_DB -tAF"|" -c "{sql}"'],
                       capture_output=True, text=True, encoding="utf-8")
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def main() -> None:
    si_by_row, si_by_name = load_inspection()
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
        items = {k: [] for k, _ in SKELETON}

        def add(ph, src, txt, ref=""):
            """항목 하나를 단계에 넣는다. **출처를 반드시 같이 남긴다** —
            사람이 '이 항목이 이 칸에 맞나'를 검수하려면 어디서 왔는지 봐야 한다."""
            slots[ph] += 1
            items[ph].append({"source": src, "text": txt, "ref": ref})

        # PRECHECK — 별표 3 본인 행
        for it in r["items"]:
            add("PRECHECK", "별표 3", it, f"제35조제2항 · {subj[:20]}")
        add("PRECHECK", "조문(총칙)", "제35조 관리감독자의 유해ㆍ위험 방지 업무 등", "제35조")

        # EXEC/POST — 해당 절/관 조문 + 절 총칙.
        # ★ 편·장까지 일치시켜야 한다. 절 번호만 보면 다른 편의 같은 번호 절을 통째로 끌어와
        #   슬링(제2편제6장제2절)에 140건이 붙는다(join_coverage에서 이미 겪은 버그).
        arts = [s for s, c in art_coord
                if jeol is not None and c[0] == p and c[1] == j and c[2] == jeol
                and (gwan is None or c[3] in (gwan, None))]
        for s in arts:
            add(phase_of(s.get("title", "")), "조문(해당 절·관)", s.get("title", ""), s["article_code"])

        # ★ 상속 계층 — '편2>장1>절1 기계 등의 일반기준'(제86~99)은 기계·설비류 전체의 상위 공통.
        #   제89조(운전 시작 전)·제93조(방호장치 해체 금지)·제99조(이탈 시 조치)가 여기 있어서,
        #   상속시키지 않으면 종료 칸이 가이드 절차에만 의존하게 된다(19종 중 10종이 비었던 원인).
        own_codes = {s["article_code"] for s in arts}
        here = (p, j, jeol)
        if (p, j) == (2, 1):
            for s, c in art_coord:
                code = s["article_code"]
                if "절1 기계 등의 일반기준" not in s.get("section", "") or code in own_codes:
                    continue
                if code in SCOPED and here not in SCOPED[code]:
                    continue                      # 적용 대상 밖 — 상속시키지 않는다
                add(phase_of(s.get("title", "")), "조문(기계 일반기준 상속)", s.get("title", ""), code)
        if here in SCOPED["제41조"]:
            add("POST", "조문(총칙)", "운전위치의 이탈금지", "제41조")

        # PLAN — 별표 4 이름 매칭
        key = re.sub(r"(을|를|이|가)?\s*(사용하여|사용하는|가동할|취급하는).*", "", subj).strip()
        for rr in a4["rows"]:
            if key and (key[:4] in rr["subject"] or rr["subject"][:6] in subj):
                for it in rr["items"]:
                    add("PLAN", "별표 4", it, f"제38조제1항 · {rr['subject'][:20]}")
                for it in (rr.get("values") or {}).get("사전조사 내용", []) or []:
                    add("PLAN", "별표 4(사전조사)", it, rr["subject"][:20])
        add("PLAN", "조문(총칙)", "사전조사 및 작업계획서의 작성 등", "제38조")

        # ASSIGN — 별표 2 좌표/이름
        for rr in a2["rows"]:
            cc = coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", rr.get("section_ref", "")))
            if (jeol is not None and cc[:3] == (p, j, jeol)) or (key and key[:4] and key[:4] in rr["subject"]):
                for it in rr["items"]:
                    add("ASSIGN", "별표 2", it, f"제35조제1항 · {rr['subject'][:20]}")
        add("ASSIGN", "조문(총칙)", "작업지휘자의 지정", "제39조")

        # PERIODIC ① — 안전검사(법 제93조). ★ 정기는 **조건부 칸**이다.
        #   안전검사 대상은 시행령 제78조의 15종뿐이고 지게차·차량계 건설기계 등은 대상이 아니다.
        #   그건 데이터 결손이 아니라 법이 그런 것이므로, 빈칸으로 두지 말고 '대상 아님'을 명시한다.
        machines = [si_by_name[x] for x in si_by_row.get(no, []) if x in si_by_name]
        # ★ 검사기준은 **별표 파일 기준으로 센다.** 프레스와 전단기는 시행령상 별개 호지만
        #   검사기준은 별표 1 하나를 공유한다 — 기계 수로 세면 208개가 416개가 된다.
        by_file = {m.get("inspection_criteria_file", ""): len(m.get("inspection_items") or [])
                   for m in machines}
        insp = {"is_target": bool(machines), "machines": [m["name"] for m in machines],
                "cycle": [ln for m in machines for ln in cycle_lines(m)],
                "criteria_items": sum(by_file.values()),
                "criteria_files": sorted(by_file),
                "criteria_articles": sorted({m.get("criteria_article", "") for m in machines})}
        for ln in insp["cycle"]:
            add("PERIODIC", "안전검사(법정)", ln, "시행규칙 제126조제1항")
        if insp["criteria_items"]:
            add("PERIODIC", "안전검사(법정)",
                f"안전검사 검사기준 {insp['criteria_items']}개 항목",
                f"고시 {'·'.join(insp['criteria_articles'])} → {', '.join(insp['criteria_files'])}")

        n_periodic_law = slots["PERIODIC"]      # 여기까지가 법정(안전검사) 분

        # PERIODIC ② — 대표 가이드 절차
        kw = GUIDE_KW.get(no, "")
        gcode = ""
        if kw:
            g = pg(f"select guide_code from kosha_guides where title like '%{kw}%' order by guide_code limit 1")
            gcode = g[0] if g else ""
        if gcode:
            for ln in pg(f"select process_order, replace(process_name,'|','/') from work_processes "
                         f"where source_guide='{gcode}' order by process_order"):
                parts = ln.split("|")
                if len(parts) < 2:
                    continue
                add(phase_of(parts[1]), "가이드(권고)", parts[1], f"{gcode} {parts[0]}단계")

        # ★ 정기 칸의 근거 강도는 3단계다. 법정 안전검사(주기·검사기준)와 가이드 권고 절차는
        #   무게가 다르므로 화면에서 같은 칸에 섞어 보여주면 안 된다.
        insp["periodic_law"] = n_periodic_law
        insp["periodic_guide"] = slots["PERIODIC"] - n_periodic_law
        insp["periodic_source"] = ("안전검사+가이드" if n_periodic_law and insp["periodic_guide"]
                                   else "안전검사" if n_periodic_law
                                   else "가이드만" if insp["periodic_guide"] else "없음")

        filled = sum(1 for k, _ in SKELETON if slots[k])
        report.append({"no": no, "subject": subj, "coord": [p, j, jeol, gwan], "guide": gcode,
                       "slots": slots, "filled": filled, "items": items, "inspection": insp,
                       "detail": {k: [x["text"] for x in v[:3]] for k, v in items.items()}})

    print(f"=== 별표 3 작업종류 {len(report)}종 × 골격 채움 현황 ===")
    print(f"{'no':>5} {'작업종류':26} {'가이드':12} " + " ".join(f"{lab:>5}" for _, lab in SKELETON)
          + "  채움  정기근거     안전검사 대상")
    for x in report:
        cells = " ".join(f"{x['slots'][k]:>5}" for k, _ in SKELETON)
        i = x["inspection"]
        print(f"{x['no']:>5} {x['subject'][:24]:26} {x['guide'][:12]:12} {cells}  {x['filled']}/6  "
              f"{i['periodic_source']:12} {'·'.join(i['machines']) if i['machines'] else '-'}")

    full = sum(1 for x in report if x["filled"] == len(SKELETON))
    print(f"\n6/6 채움: {full}/{len(report)}종")
    for k, lab in SKELETON:
        empty = [x["no"] for x in report if not x["slots"][k]]
        print(f"  {lab:6} 빈 종류 {len(empty):2d}종 {('· ' + ', '.join(empty)) if empty else ''}")

    # ★ 정기 칸은 근거 강도가 갈린다. 법정 주기와 가이드 권고를 같은 칸에 섞으면
    #   사업주가 '해도 되는 것'과 '안 하면 위법인 것'을 구별하지 못한다.
    print("\n=== 정기 칸 근거 강도 ===")
    for src in ("안전검사+가이드", "안전검사", "가이드만", "없음"):
        g = [x for x in report if x["inspection"]["periodic_source"] == src]
        if g:
            print(f"  {src:12} {len(g):2d}종 · {', '.join(x['subject'][:12] for x in g)}")
    print("  ('없음'은 데이터 결손이 아니라 안전검사 대상이 아니고 가이드에도 정기 절차가 없는 것)")

    out = ART / "flow_slice_all.json"
    out.write_text(json.dumps({"_note": "별표 3 19종 × 골격 채움. 칸이 차는지만 본다(라벨 정확도 별도).",
                               "rows": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out.name}")


if __name__ == "__main__":
    main()
