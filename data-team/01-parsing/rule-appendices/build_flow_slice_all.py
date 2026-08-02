#!/usr/bin/env python3
"""기인물 그룹 113종 × 흐름 골격 6단계 조립 (LLM 호출 0).

**인덱스는 기인물 그룹이다.** 예전엔 별표 3(작업시작 전 점검)의 작업종류 19행을 인덱스로 썼는데,
별표 3은 원래 '작업 시작 전 점검' 칸 **하나의 재료**일 뿐이다. 재료 하나가 전체 목록을 결정하니
앵커가 내는 113종 중 19종만 흐름이 있었고, 정답 기준으로도 사진의 42%가 흐름 없이 비었다.
앵커(RESOLVE)가 `group_keys`를 내므로 인덱스도 그룹이어야 짝이 맞는다.

각 칸의 재료:
  PLAN     별표 4(이름 매칭) + 제38조
  ASSIGN   별표 2(좌표/이름) + 제39조
  PRECHECK 별표 3(좌표 매칭 — 19종만 해당) + 제35조
  EXEC     그룹 전용 조문 + 절 총칙(관1) + 기계 일반기준 상속
  POST     이탈·종료 성격 조문(같은 출처)
  PERIODIC 안전검사(법정) + 가이드 절차(권고)

⚠ '칸이 차는가'만 본다. 항목이 그 단계에 맞는지(라벨 정확도)는 사람 검수 대상
  (build_flow_viewer.py → flow_review_viewer.html).

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
#
#   ⚠ 이 목록은 '기계 등의 일반기준'(제86~99) 14개 조문의 **본문을 전부 읽어** 확정했다.
#     제87·88·90~97조는 "기계", "동력으로 작동되는 기계"라 진짜 일반이고,
#     스스로 대상을 한정하는 것은 제86·98·99조 셋뿐이다. 제41조는 절1 밖(편1 총칙)이다.
#   좌표는 **접두사**로 비교한다. (2,1,9)는 절9 전체, (2,1,9,6)은 관6 하나를 가리킨다.
#   allow = 여기에만 적용된다 / deny = 여기에는 적용되지 않는다.
SCOPE = {
    # ── 기계 등의 일반기준(절1) → 편2장1 전체로 상속되는 것 중 자기한정 조문 ──
    # 제41조 방호장치 — 양중기 / 항타기·항발기 / 양화장치
    "제41조": {"allow": {(2, 1, 9), (2, 1, 12), (2, 6, 2)}},
    # 제86조 탑승의 제한 — ①~⑥ 양중기(크레인·리프트·곤돌라·승강기), ⑦⑧ 차량계 하역운반기계·
    #   화물자동차, ⑨ 컨베이어, ⑩ 이삿짐운반용 리프트. **차량계 건설기계는 없다** —
    #   건설기계 탑승금지는 제202조가 따로 규율하므로 절12에서 빼도 구멍이 생기지 않는다.
    #   (⑪ 이륜자동차는 이 트리에 대응 그룹이 없다 — 편4 특수형태근로종사자 쪽이라 넣지 않는다)
    "제86조": {"allow": {(2, 1, 9), (2, 1, 10), (2, 1, 11)}},
    # 제98조 제한속도의 지정 — ① 차량계 하역운반기계·차량계 건설기계,
    #   ② 궤도작업차량(편2장8절2)·입환기(편2장8절3)
    "제98조": {"allow": {(2, 1, 10), (2, 1, 12), (2, 8, 2), (2, 8, 3)}},
    # 제99조 운전위치 이탈 시의 조치 — 차량계 하역운반기계등 / 차량계 건설기계
    "제99조": {"allow": {(2, 1, 10), (2, 1, 12)}},

    # ── 절 총칙(관1) → 형제 관으로 상속되는 것 중, 본문이 형제 하나를 콕 집어 빼는 조문 ──
    # 여기는 예전에 적용범위 검사가 아예 없었다. 절 총칙이라고 절 전체에 다 걸리지는 않는다.
    "제133조": {"deny": {(2, 1, 9, 6)}},    # "양중기(승강기는 제외한다)" — 승강기 관
    "제178조": {"deny": {(2, 1, 10, 4)}},   # ①지게차 ②구내운반차·화물자동차 — 고소작업대는 없다
}


def applies(code: str, coord: tuple) -> bool:
    """이 조문을 그 좌표의 그룹에 상속시켜도 되는가.

    ★ 조문 본문이 스스로 적용 대상을 한정하면 상속을 막아야 한다. 안 막으면
      프레스에 '차량계 운전위치 이탈 시 조치'가, 승강기에 '양중기(승강기 제외) 정격하중 표시'가 붙는다.
      둘 다 실제로 붙어 있었다.
    """
    sc = SCOPE.get(code)
    if not sc:
        return True
    def hit(pres):
        return any(tuple(coord[:len(x)]) == x for x in pres)
    if sc.get("deny") and hit(sc["deny"]):
        return False
    return hit(sc["allow"]) if sc.get("allow") else True

# 전 기인물 공통 주입 — 총칙 조문
COMMON = {"제38조": "PLAN", "제39조": "ASSIGN", "제35조": "PRECHECK"}

LEX = {
    "PLAN": r"사전조사|작업계획서|계획을 수립|설계도서",
    "ASSIGN": r"작업지휘자|지휘자|유도자|신호수|자격|특별교육|선임|배치",
    "PRECHECK": r"작업 ?시작 ?전|시작하기 전|사용 ?전|시동 ?전|작업 전 확인|미리 점검",
    "POST": r"이탈|종료|해체|반출|정리정돈|작업 후",
    "PERIODIC": r"정기|주기|월 1회|연 1회|자체검사",
}

# 별표 3 작업종류 번호 → 가이드 제목 키워드(사람이 큐레이션한 것). 좌표 조인으로 그룹에 옮겨 붙인다.
# ⚠ 나머지 그룹에는 가이드를 붙이지 않는다. 제목 키워드 자동 매칭은 오부착 위험이 커서
#   ('통칙' 같은 이름이 아무 가이드나 잡는다) 권고 계층을 오염시킨다.
GUIDE_KW = {
    "1": "프레스", "2": "로봇", "3": "공기압축기", "4": "크레인 안전작업", "5": "이동식 크레인",
    "6": "리프트", "7": "곤돌라", "8": "와이어로프", "9": "지게차의 안전작업", "10": "구내운반",
    "11": "고소작업대", "12": "화물자동차", "13": "컨베이어", "14": "건설기계",
    "14의2": "용접", "15": "방폭", "16": "중량물", "17": "양화장치", "18": "줄걸이",
}


def coord_of(section: str) -> tuple:
    """'편2 안전기준 > 장1 … > 절10 … > 관2 지게차' → (편, 장, 절, 관).

    ★ 항상 4튜플로 다룬다. 규칙에는 '절1'이라는 이름의 절이 20곳 있어
      (편2장1 기계 일반기준 / 편2장3 전기 / 편3 각 장 통칙 …) 편·장을 버리면 뭉개진다.
      이 유형의 버그가 네 번 재발했다.
    """
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)$", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        if lvl == "편":
            p = n
        elif lvl == "장":
            j = n
        elif lvl == "절":
            jeol = n
        else:
            gwan = n
    return (p, j, jeol, gwan)


def packed_coord(s: str) -> tuple:
    """'제2편제1장제10절제2관'(별표의 section_ref) → (편, 장, 절, 관)."""
    return coord_of(re.sub(r"제(\d+)(편|장|절|관)", r"\2\1 ", s or ""))


def strip_num(s: str) -> str:
    return re.sub(r"^(편|장|절|관)\d+\s*", "", (s or "").strip())


def namekey(s: str) -> str:
    """이름 매칭용 정규화 — 공백·중점·괄호 제거 후 꼬리 '등' 절단.

    '차량계 건설기계 등' 과 '차량계 건설기계를 사용하는 작업'을 붙이려면 꼬리 '등'을 떼야 한다.
    """
    return re.sub(r"등$", "", re.sub(r"[\s·ㆍ()（）]", "", s or ""))


# 그룹 이름의 꼬리 상투어 — 떼야 핵심 명사가 남는다('전기작업에 대한 위험 방지' → '전기작업')
GENERIC_TAIL = re.compile(r"(에\s*대한|에\s*의한|시의|시|등의)?\s*"
                          r"(위험\s*방지|위험\s*예방|건강장해의\s*예방|예방|조치기준)\s*$")


def name_variants(name: str) -> set[str]:
    """그룹 이름 → 매칭에 쓸 핵심어 집합.

    ★ 앞 4글자만 보면 '그 밖의'·'설비의' 같은 흔한 조각이 걸려 오부착한다
      (실제로 '그 밖의 유해인자에 의한 건강장해의 예방'에 '궤도와 그 밖의 관련설비의 보수·점검'이,
       비계의 '조립ㆍ해체 및 점검 등'에 타워크레인 작업계획서가 붙었다).
    ★ 반대로 이름 전체만 보면 '화학설비ㆍ압력용기 등'이 '화학설비와 그 부속설비 사용작업'을 놓친다.
    → 꼬리 상투어를 떼고 'ㆍ/및'로 쪼갠 조각까지 후보로 쓰되, 3글자 미만은 버린다.
    """
    s = GENERIC_TAIL.sub("", name or "").strip()
    s = re.sub(r"\s*등$", "", s).strip()
    parts = [p for p in re.split(r"[ㆍ·,]|\s+및\s+", s) if p.strip()]
    return {v for v in (namekey(x) for x in [s, *parts]) if len(v) >= 3}


def name_hit(name: str, subject: str) -> bool:
    """그룹 핵심어 ↔ 별표 행 제목의 양방향 포함 매칭.

    ⚠ 이름 매칭은 본질적으로 불확실하다. 좌표 매칭과 구별되도록 출처에 '(이름매칭)'을 표기해
      사람 검수에서 걸러낼 수 있게 한다. 규칙을 더 조이면 누락이, 풀면 오부착이 늘어난다.
    """
    b = namekey(subject)
    if len(b) < 3:
        return False
    return any(v in b or b in v for v in name_variants(name))


def phase_of(text: str) -> str:
    for ph in ("PLAN", "ASSIGN", "PRECHECK", "POST", "PERIODIC"):
        if re.search(LEX[ph], text or ""):
            return ph
    return "EXEC"


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


def load_inspection() -> tuple[dict, dict]:
    """기인물 그룹키 → 안전검사 기계 레코드 목록.

    ★ 이름 매칭은 join_inspection_coverage.py 가 하고 coverage-report.json 에 남긴다.
      여기서 매칭을 다시 구현하면 두 곳이 조용히 어긋난다. 데이터로만 받는다.
    """
    cov, si = SI_DIR / "coverage-report.json", SI_DIR / "safety-inspection.json"
    if not (cov.exists() and si.exists()):
        print("⚠ 안전검사 데이터 없음 — 정기 칸을 가이드 절차로만 채운다\n")
        return {}, {}
    c = json.loads(cov.read_text(encoding="utf-8"))
    s = json.loads(si.read_text(encoding="utf-8"))
    by_name = {m["name"]: m for m in s["machines"]}
    by_group: dict[str, list] = {}
    for m in c["machines"]:
        for g in m["gimulmul_groups"]:
            by_group.setdefault(g["key"], []).append(by_name[m["name"]])
    return by_group, by_name


def pg(sql: str) -> list[str]:
    r = subprocess.run(["docker", "exec", "kosha-pg", "sh", "-c",
                        f'psql -U $POSTGRES_USER -d $POSTGRES_DB -tAF"|" -c "{sql}"'],
                       capture_output=True, text=True, encoding="utf-8")
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def main() -> None:
    si_by_group, _ = load_inspection()
    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    a3 = json.loads((PARSED / "appendix-03.json").read_text(encoding="utf-8"))
    a4 = json.loads((PARSED / "appendix-04.json").read_text(encoding="utf-8"))
    a2 = json.loads((PARSED / "appendix-02.json").read_text(encoding="utf-8"))

    # ── 그룹 테이블 ────────────────────────────────────────────────────
    # ★ gimulmul_index 의 그룹키에는 편·장이 없다. 그래서 '절1 통칙' 하나에 편3의 12개 장 통칙이
    #   통째로 합쳐져 있다(같은 좌표 뭉갬 버그가 카탈로그 자체에 박혀 있다 — 3그룹·37조문, 전부 편3 보건).
    #   공유 카탈로그를 고치면 서빙(RESOLVE 카탈로그·alias·임베딩)까지 파급되므로 여기서 좌표별로 쪼갠다.
    split = 0
    for k in list(gim):
        g = gim[k]
        by_c = {}
        for a in g.get("articles", []):
            if a["code"] in sigs:
                by_c.setdefault(coord_of(sigs[a["code"]]["section"]), []).append(a)
        if len(by_c) <= 1:
            continue
        del gim[k]
        for c, arts in by_c.items():
            sec = sigs[arts[0]["code"]]["section"]
            toks = [t.strip() for t in sec.split(">")]
            gim[f"{k} @편{c[0]}장{c[1]}"] = {
                "pyeon": next((t for t in toks if t.startswith("편")), ""),
                "jang": next((t for t in toks if t.startswith("장")), ""),
                "jeol": next((t for t in toks if t.startswith("절")), ""),
                "gwan": next((t for t in toks if t.startswith("관")), ""),
                "gimulmul": g.get("gimulmul", ""), "articles": arts, "_split_from": k}
            split += 1
    if split:
        print(f"⚠ 좌표가 섞인 그룹을 {split}개로 분리했다(카탈로그의 그룹키에 편·장이 없어 생긴 병합)\n")

    G = {}
    for k, g in gim.items():
        c = coord_of(" ".join([g.get("pyeon", ""), g.get("jang", ""), g.get("jeol", ""), g.get("gwan", "")]))
        # 표시명은 가장 가까운 두 층만 쓴다. 장 이름을 앞에 붙이면
        # '기계ㆍ기구 및 그 밖의 설비에 의한 위험예방 > …'가 반복돼 목록에서 서로 구별되지 않는다.
        jang, jeol, gwan_ = (strip_num(g.get(x, "")) for x in ("jang", "jeol", "gwan"))
        label = f"{jeol} > {gwan_}" if gwan_ else (jeol or jang or strip_num(g.get("pyeon", "")) or k)
        path = " > ".join(strip_num(x) for x in
                          (g.get("pyeon", ""), g.get("jang", ""), g.get("jeol", ""), g.get("gwan", "")) if x)
        G[k] = {"key": k, "coord": c, "name": g.get("gimulmul") or strip_num(k),
                "label": label, "path": path, "src_key": g.get("_split_from", k),
                "codes": [a["code"] for a in g.get("articles", []) if a["code"] in sigs]}

    # 표시명이 겹치는 그룹(통칙·보호구 등·관리 등 …)은 장 이름을 앞에 붙여 구별한다.
    # 목록에서 '통칙'이 13개 나란히 뜨면 어느 것인지 고를 수 없다.
    dup_label = {lb for lb in (v["label"] for v in G.values())
                 if sum(1 for v in G.values() if v["label"] == lb) > 1}
    for v in G.values():
        if v["label"] in dup_label:
            jang = strip_num(gim[v["key"]].get("jang", ""))
            if jang:
                v["label"] = f"{jang} > {v['label']}"

    gwan1 = {v["coord"][:3]: k for k, v in G.items() if v["coord"][3] == 1}      # 절 총칙(관1)
    machine_base = next((k for k, v in G.items() if v["coord"] == (2, 1, 1, None)), None)  # 기계 등의 일반기준

    # 별표 3 좌표 → 행 (19종만 해당)
    a3_by_coord = {}
    for r in a3["rows"]:
        a3_by_coord.setdefault(packed_coord(r.get("section_ref", "")), []).append(r)

    report = []
    for k, gg in G.items():
        p, j, jeol, gwan = gg["coord"]
        here = (p, j, jeol)
        slots = {x: 0 for x, _ in SKELETON}
        items = {x: [] for x, _ in SKELETON}

        def add(ph, src, txt, ref=""):
            """항목 하나를 단계에 넣는다. **출처를 반드시 같이 남긴다** —
            사람이 '이 항목이 이 칸에 맞나'를 검수하려면 어디서 왔는지 봐야 한다."""
            slots[ph] += 1
            items[ph].append({"source": src, "text": txt, "ref": ref})

        # ── 조문: 전용 → 절 총칙(관1) → 기계 일반기준 상속 ────────────
        own = set(gg["codes"])
        for c in gg["codes"]:
            add(phase_of(sigs[c]["title"]), "조문(전용)", sigs[c]["title"], c)

        if gwan not in (None, 1) and here in gwan1:
            for c in G[gwan1[here]]["codes"]:
                if c not in own and applies(c, gg["coord"]):
                    add(phase_of(sigs[c]["title"]), "조문(절 총칙)", sigs[c]["title"], c)
                    own.add(c)

        # ★ '편2>장1>절1 기계 등의 일반기준'(제86~99)은 기계·설비류 전체의 상위 공통.
        #   제89조(운전 시작 전)·제93조(방호장치 해체 금지)·제99조(이탈 시 조치)가 여기 있다.
        if machine_base and k != machine_base and (p, j) == (2, 1):
            for c in G[machine_base]["codes"]:
                if c in own:
                    continue
                if not applies(c, gg["coord"]):
                    continue                      # 적용 대상 밖 — 상속시키지 않는다
                add(phase_of(sigs[c]["title"]), "조문(기계 일반기준 상속)", sigs[c]["title"], c)
                own.add(c)
        # 편2장1 밖이어도 적용 대상으로 명시된 좌표에는 넣는다(예: 항만 양화장치의 제41조)
        for c, sc in SCOPE.items():
            if sc.get("allow") and c not in own and c in sigs and applies(c, gg["coord"]):
                add(phase_of(sigs[c]["title"]), "조문(적용범위 지정)", sigs[c]["title"], c)
                own.add(c)

        for c, ph in COMMON.items():
            if c in sigs and c not in own:
                add(ph, "조문(총칙)", sigs[c]["title"], c)

        # ── PRECHECK: 별표 3 (좌표 정확 일치 — 19종만) ────────────────
        a3_rows = a3_by_coord.get(gg["coord"], [])
        for r in a3_rows:
            for it in r["items"]:
                add("PRECHECK", "별표 3", it, f"제35조제2항 · {r['subject'][:20]}")

        # ── PLAN: 별표 4 (이름 매칭) ──────────────────────────────────
        nm = gg["name"]
        for rr in a4["rows"]:
            if name_hit(nm, rr["subject"]):
                for it in rr["items"]:
                    add("PLAN", "별표 4(이름매칭)", it, f"제38조제1항 · {rr['subject'][:20]}")
                for it in (rr.get("values") or {}).get("사전조사 내용", []) or []:
                    add("PLAN", "별표 4(사전조사·이름매칭)", it, rr["subject"][:20])

        # ── ASSIGN: 별표 2 (좌표 우선, 없으면 이름) ───────────────────
        for rr in a2["rows"]:
            cc = packed_coord(rr.get("section_ref", ""))
            by_coord = cc == gg["coord"] or (cc[:3] == here and cc[3] is None and jeol is not None)
            if by_coord or name_hit(nm, rr["subject"]):
                src = "별표 2" if by_coord else "별표 2(이름매칭)"
                for it in rr["items"]:
                    add("ASSIGN", src, it, f"제35조제1항 · {rr['subject'][:20]}")

        # ── PERIODIC ① 안전검사(법정) ─────────────────────────────────
        machines = si_by_group.get(gg["src_key"], [])
        by_file = {m.get("inspection_criteria_file", ""): len(m.get("inspection_items") or []) for m in machines}
        insp = {"is_target": bool(machines), "machines": [m["name"] for m in machines],
                "criteria_items": sum(by_file.values()), "criteria_files": sorted(by_file),
                "criteria_articles": sorted({m.get("criteria_article", "") for m in machines})}
        for m in machines:
            for ln in cycle_lines(m):
                add("PERIODIC", "안전검사(법정)", ln, "시행규칙 제126조제1항")
        if insp["criteria_items"]:
            add("PERIODIC", "안전검사(법정)", f"안전검사 검사기준 {insp['criteria_items']}개 항목",
                f"고시 {'·'.join(insp['criteria_articles'])} → {', '.join(insp['criteria_files'])}")
        n_periodic_law = slots["PERIODIC"]

        # ── PERIODIC ② 가이드(권고) — 별표 3 좌표가 붙은 그룹만 ───────
        # ★ 한 그룹에 별표 3 행이 여럿 붙을 수 있다(양화장치·슬링은 둘 다 편2장6절2).
        #   첫 행만 보면 나머지 행의 가이드를 잃는다. 전부 시도하고 코드로 dedupe한다.
        gcodes = []
        for r in a3_rows:
            kw = GUIDE_KW.get(r["no"], "")
            if not kw:
                continue
            hit = pg(f"select guide_code from kosha_guides where title like '%{kw}%' order by guide_code limit 1")
            if hit and hit[0] not in gcodes:
                gcodes.append(hit[0])
        for gc in gcodes:
            for ln in pg(f"select process_order, replace(process_name,'|','/') from work_processes "
                         f"where source_guide='{gc}' order by process_order"):
                parts = ln.split("|")
                if len(parts) < 2:
                    continue
                add(phase_of(parts[1]), "가이드(권고)", parts[1], f"{gc} {parts[0]}단계")
        gcode = ", ".join(gcodes)

        # ★ 정기 칸의 근거 강도는 3단계다. 법정 안전검사와 가이드 권고는 무게가 다르므로
        #   화면에서 같은 칸에 섞어 보여주면 '해야 하는 것'과 '하면 좋은 것'이 구별되지 않는다.
        insp["periodic_law"] = n_periodic_law
        insp["periodic_guide"] = slots["PERIODIC"] - n_periodic_law
        insp["periodic_source"] = ("안전검사+가이드" if n_periodic_law and insp["periodic_guide"]
                                   else "안전검사" if n_periodic_law
                                   else "가이드만" if insp["periodic_guide"] else "없음")

        # src_key = 카탈로그(gimulmul_index)의 원래 그룹키. RESOLVE가 내는 group_key와 조인하려면
        # 분리 전 키가 있어야 한다(분리된 그룹은 no != src_key).
        report.append({"no": k, "src_key": gg["src_key"], "subject": gg["label"], "path": gg["path"], "name": nm,
                       "coord": list(gg["coord"]),
                       "guide": gcode, "apx3": [r["no"] for r in a3_rows],
                       "slots": slots, "filled": sum(1 for x, _ in SKELETON if slots[x]),
                       "items": items, "inspection": insp,
                       "detail": {x: [y["text"] for y in v[:3]] for x, v in items.items()}})

    # ── 리포트 ────────────────────────────────────────────────────────
    report.sort(key=lambda r: tuple(9999 if x is None else x for x in r["coord"]))
    n = len(report)
    print(f"=== 기인물 그룹 {n}종 × 흐름 골격 6단계 ===\n")
    dist = {}
    for r in report:
        dist[r["filled"]] = dist.get(r["filled"], 0) + 1
    for f in sorted(dist, reverse=True):
        print(f"  {f}/6 칸 채움  {dist[f]:>3}종")
    print(f"\n총 항목 {sum(sum(r['slots'].values()) for r in report)}개")

    # ★ '칸이 찼다'를 그대로 믿으면 안 된다. 계획·인적·작업전은 총칙 조문(제38·39·35조)을
    #   전 그룹에 1건씩 주입하므로 무조건 찬다. 그걸 뺀 **실질 채움**을 같이 낸다.
    def real(r, ph):
        return [y for y in r["items"][ph] if y["source"] != "조문(총칙)"]

    print("  (칸 채움 / 총칙 공통주입 제외한 실질)")
    for x, lab in SKELETON:
        empty = sum(1 for r in report if not r["slots"][x])
        sub = sum(1 for r in report if real(r, x))
        print(f"  {lab:6} 빈 그룹 {empty:>3}종 · 채움 {(n - empty) / n:>4.0%} / 실질 {sub / n:>4.0%}")
    rdist = {}
    for r in report:
        c = sum(1 for x, _ in SKELETON if real(r, x))
        rdist[c] = rdist.get(c, 0) + 1
    print("  실질 칸 수 분포: " + " · ".join(f"{f}칸 {rdist[f]}종" for f in sorted(rdist, reverse=True)))

    print(f"\n별표 3 붙은 그룹 {sum(1 for r in report if r['apx3'])}종 · "
          f"가이드 붙은 그룹 {sum(1 for r in report if r['guide'])}종 · "
          f"안전검사 대상 {sum(1 for r in report if r['inspection']['is_target'])}종")
    print("\n=== 정기 칸 근거 강도 ===")
    for src in ("안전검사+가이드", "안전검사", "가이드만", "없음"):
        g = [r for r in report if r["inspection"]["periodic_source"] == src]
        print(f"  {src:12} {len(g):>3}종")

    print("\n[칸이 가장 적게 찬 그룹]")
    for r in sorted(report, key=lambda x: x["filled"])[:8]:
        cells = " ".join(f"{lab}{r['slots'][x]}" for x, lab in SKELETON)
        print(f"  {r['filled']}/6  {r['subject'][:38]:40} {cells}")

    out = ART / "flow_slice_all.json"
    out.write_text(json.dumps({"_note": "기인물 그룹 113종 × 골격 6단계. 칸이 차는지만 본다(라벨 정확도는 사람 검수).",
                               "n_groups": n, "rows": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out.name}")


if __name__ == "__main__":
    main()
