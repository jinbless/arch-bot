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
import sys
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
    # 제41조 운전위치의 이탈금지 — ①항 각 호가 대상을 스스로 열거한다:
    #   1.양중기 2.항타기·항발기(하중 건 상태) 3.양화장치(적재 상태)
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
    """제목/문장 한 줄로 시점을 추정 — **가이드 절차명 전용 fallback**이다.

    ⚠ 조문에는 쓰지 마라. 조문은 원문(fullText)을 읽은 `article_phases.json`을 쓴다.
      제목만 보면 669개 중 642개가 EXEC로 뭉개진다(제89조는 제목이 '운전 시작 전 조치'인데
      이 정규식의 '시작하기 전'에 안 걸린다). 가이드 절차명은 원문이라 부를 것이 없어 여기 남는다.
    """
    for ph in ("PLAN", "ASSIGN", "PRECHECK", "POST", "PERIODIC"):
        if re.search(LEX[ph], text or ""):
            return ph
    return "EXEC"


def load_law3(G: dict) -> dict[str, list[dict]]:
    """법·시행령·시행규칙 조문 43건 → 그룹키별 항목 목록.

    흐름의 재료는 원래 산업안전보건기준규칙뿐이었다. 법·시행령·시행규칙 554조를 훑어
    기인물 단위로 매달 수 있는 의무를 찾았고(`law3_flow_gap_candidates.json`),
    적용 대상은 `law3_targets.py`의 표가 정한다.

    ★ 대상을 코드가 알아서 정하게 두지 않는다. 조문마다 표에 적고 근거를 남긴다.
      과부착 버그가 이 프로젝트에서 7번 났다.
    """
    cand_p = ART / "law3_flow_gap_candidates.json"
    if not cand_p.exists():
        return {}
    try:
        from law3_targets import TARGETS, load_list, resolve_machines, nkey  # noqa: PLC0415
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from law3_targets import TARGETS, load_list, resolve_machines, nkey  # noqa: PLC0415

    glist = [{"key": k, "name": v["name"], "coord": v["coord"]} for k, v in G.items()]
    machine_base = {k for k, v in G.items() if (v["coord"][0], v["coord"][1]) == (2, 1)}
    by_group: dict[str, list[dict]] = {}
    unmatched, no_target = [], []

    for c in json.loads(cand_p.read_text(encoding="utf-8"))["candidates"]:
        t = TARGETS.get((c["law"], c["code"], c["phase"]))
        if t is None:
            no_target.append(f"{c['law']} {c['code']}/{c['phase']}")
            continue
        kind = t["kind"]
        if kind == "none":
            continue
        if kind == "machines":
            names = load_list(t["list"]) if t.get("list") else t["names"]
            keys, miss = resolve_machines(names, glist)
            unmatched += [f"{c['code']}: {m}" for m in miss]
        elif kind == "coord":
            keys = {g["key"] for g in glist
                    if any(tuple(g["coord"][:len(p)]) == p for p in t["prefixes"])}
        elif kind == "all_machine":
            keys = set(machine_base)
        else:                                   # byeolpyo5 — 특별교육은 아래에서 따로 붙인다
            continue
        law_short = {"산업안전보건법": "법", "산업안전보건법 시행령": "시행령",
                     "산업안전보건법 시행규칙": "시행규칙"}[c["law"]]
        for k in keys:
            by_group.setdefault(k, []).append({
                "phase": c["phase"], "text": c["title_원문"], "evidence": c["quote"],
                "ref": f"{law_short} {c['code']}", "note": t.get("note", "")})

    if unmatched:
        print(f"⚠ 법령이 대상으로 정했으나 기인물 그룹이 없는 기계 {len(set(unmatched))}건 — "
              f"{', '.join(sorted(set(unmatched))[:6])} …")
    if no_target:
        print(f"⚠ 적용 대상 표에 없는 후보 {len(no_target)}건 — {', '.join(no_target[:5])}")
    print(f"법·시행령·시행규칙 조문을 {len(by_group)}개 그룹에 "
          f"{sum(len(v) for v in by_group.values())}건 붙였다\n")
    return by_group


def load_article_phases() -> tuple[dict[str, list[dict]], set[str]]:
    """조문 코드 → [{phase, quote}] — 원문 판독 결과. 그리고 **의무가 아닌 조문** 집합.

    한 조문이 여러 칸에 들어갈 수 있다(제35조는 인적 배치와 작업 전 점검 둘 다).
    quote는 그 칸에 넣은 **원문 근거**다. 화면에도 검수 뷰어에도 이걸 같이 보여준다 —
    같은 조문 제목이 두 칸에 뜨면 근거 없이는 중복으로 보인다.

    ★ no_duty = 목적·정의·적용 제외 조문. 사업주가 '할 일'이 아니므로 흐름에서 뺀다.
      빼기 전에는 제1조 '목적'과 제2조 '정의'가 **'작업 중' 칸에 항목으로 떠 있었다.**
    """
    p = ART / "article_phases.json"
    if not p.exists():
        print("⚠ article_phases.json 없음 — 조문 시점을 제목 정규식으로 추정한다(96%가 EXEC로 뭉개진다)\n")
        return {}, set()
    d = json.loads(p.read_text(encoding="utf-8"))["articles"]
    # ★ quote가 아니라 evidence를 쓴다. 1차의 EXEC quote는 근거가 아니라 자리표시라서
    #   그대로 띄우면 한 문장이 두 칸에 중복으로 뜬다(제388조 등 19종에서 실제로 그랬다).
    aph = {c: [{"phase": x["phase"], "quote": x.get("evidence", x.get("quote", ""))} for x in a["phases"]]
           for c, a in d.items()}
    return aph, {c for c, a in d.items() if a.get("no_duty")}


def cycle_lines(m: dict, group: str, groups: set[str]) -> list[str]:
    """주기 규정 → 읽을 수 있는 문장. 원문 문구를 이어 붙이기만 한다(해석 추가 금지).

    ★ 하위 종류마다 주기가 다르고, 법령이 **명시적으로 제외**한다.
      시행규칙 제126조제1항제1호는 "크레인(**이동식 크레인은 제외한다**), 리프트(이삿짐운반용
      리프트는 제외한다) 및 곤돌라: 설치 3년 이내 … 건설현장 6개월마다"이고,
      이동식 크레인은 제2호에서 "신규등록 이후 3년 이내"로 따로 규율한다.
      이걸 안 걸러서 **이동식 크레인 그룹에 '설치 3년 · 건설현장 6개월'이 붙어 있었다** —
      적용범위 무시 버그의 7번째 발현이다. 이번엔 조문이 아니라 주기에서 났다.
    """
    out, c = [], m.get("cycle") or {}
    if group not in (c.get("excludes") or []):
        base = " ".join(x for x in (c.get("first"), c.get("then")) if x)
        if base:
            out.append(f"{m['name']}: {base}")
        if c.get("special"):
            out.append(f"{m['name']}: {c['special']}")
    for v in m.get("cycle_variants") or []:
        sub = v.get("subtype", "")
        # 그 하위 종류에 해당하는 **기인물 그룹이 따로 있으면** 거기서만 보여준다.
        # 없으면(이삿짐운반용 리프트) 상위 그룹에 남긴다 — 안 그러면 정보가 사라진다.
        if sub in groups and sub != group:
            continue
        vb = " ".join(x for x in (v.get("first"), v.get("then")) if x)
        if vb:
            out.append(f"{sub}: {vb}")
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
    APH, NO_DUTY = load_article_phases()
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

    # 안전검사 주기의 하위 종류('이동식 크레인')에 대응하는 그룹이 있는지 볼 때 쓴다.
    group_names = {v["name"] for v in G.values()}
    LAW3 = load_law3(G)
    gwan1 = {v["coord"][:3]: k for k, v in G.items() if v["coord"][3] == 1}      # 절 총칙(관1)
    machine_base = next((k for k, v in G.items() if v["coord"] == (2, 1, 1, None)), None)  # 기계 등의 일반기준

    # 별표 3 좌표 → 행 (19종만 해당)
    a3_by_coord = {}
    for r in a3["rows"]:
        a3_by_coord.setdefault(packed_coord(r.get("section_ref", "")), []).append(r)

    report = []
    skipped: set[str] = set()      # 흐름에서 뺀 의무 아닌 조문(목적·정의·적용 제외)
    for k, gg in G.items():
        p, j, jeol, gwan = gg["coord"]
        here = (p, j, jeol)
        slots = {x: 0 for x, _ in SKELETON}
        items = {x: [] for x, _ in SKELETON}

        def add(ph, src, txt, ref="", ev=""):
            """항목 하나를 단계에 넣는다. **출처를 반드시 같이 남긴다** —
            사람이 '이 항목이 이 칸에 맞나'를 검수하려면 어디서 왔는지 봐야 한다.
            ev = 그 칸에 넣은 근거로 삼은 **원문 문구**(조문만 해당)."""
            slots[ph] += 1
            items[ph].append({"source": src, "text": txt, "ref": ref, "evidence": ev})

        def add_article(src, c):
            """조문 하나를 원문 판독 결과에 따라 **여러 칸에** 넣는다.

            제35조는 관리감독자 직무(인적 배치)이면서 작업 시작 전 점검이기도 하다.
            한 칸에만 넣으면 둘 중 하나가 흐름에서 사라진다.

            ★ 목적·정의·적용 제외 조문은 넣지 않는다. '할 일'이 아니다."""
            if c in NO_DUTY:
                skipped.add(c)
                return
            for x in APH.get(c) or [{"phase": phase_of(sigs[c]["title"]), "quote": ""}]:
                add(x["phase"], src, sigs[c]["title"], c, x["quote"])

        # ── 조문: 전용 → 절 총칙(관1) → 기계 일반기준 상속 ────────────
        own = set(gg["codes"])
        for c in gg["codes"]:
            add_article("조문(전용)", c)

        if gwan not in (None, 1) and here in gwan1:
            for c in G[gwan1[here]]["codes"]:
                if c not in own and applies(c, gg["coord"]):
                    add_article("조문(절 총칙)", c)
                    own.add(c)

        # ★ '편2>장1>절1 기계 등의 일반기준'(제86~99)은 기계·설비류 전체의 상위 공통.
        #   제89조(운전 시작 전)·제93조(방호장치 해체 금지)·제99조(이탈 시 조치)가 여기 있다.
        if machine_base and k != machine_base and (p, j) == (2, 1):
            for c in G[machine_base]["codes"]:
                if c in own:
                    continue
                if not applies(c, gg["coord"]):
                    continue                      # 적용 대상 밖 — 상속시키지 않는다
                add_article("조문(기계 일반기준 상속)", c)
                own.add(c)
        # 편2장1 밖이어도 적용 대상으로 명시된 좌표에는 넣는다(예: 항만 양화장치의 제41조)
        for c, sc in SCOPE.items():
            if sc.get("allow") and c not in own and c in sigs and applies(c, gg["coord"]):
                add_article("조문(적용범위 지정)", c)
                own.add(c)

        # 총칙 3조문은 **칸을 고정**한다. 제38조=작업계획서, 제39조=작업지휘자, 제35조=관리감독자 점검.
        # 원문 판독으로는 제35조가 두 칸에 걸치지만, 전 그룹에 주입되는 항목이라
        # 칸마다 늘어나면 '겉보기 채움'만 부풀고 실질은 그대로다.
        for c, ph in COMMON.items():
            if c in sigs and c not in own:
                ev = next((x["quote"] for x in APH.get(c, []) if x["phase"] == ph), "")
                add(ph, "조문(총칙)", sigs[c]["title"], c, ev)

        # ── 법·시행령·시행규칙 조문 ────────────────────────────────────
        # 규칙 조문과 출처를 구분한다. 사람이 검수할 때 '이건 법이고 이건 규칙'이 보여야 한다.
        for x in LAW3.get(k, []):
            add(x["phase"], f"법령({x['ref'].split()[0]})", x["text"], x["ref"], x["evidence"])

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
        # ★ 이 시점의 PERIODIC은 **조문에서 온 정기 의무**다(원문 판독으로 19개 조문이 여기 들어온다).
        #   예전엔 조문이 정기 칸에 오는 일이 없어(제목 정규식이 하나도 못 잡았다) 이 구분이 필요 없었고,
        #   그래서 아래 n_periodic_law가 조문분까지 안전검사로 집계해 12종을 29종으로 부풀렸다.
        n_periodic_article = slots["PERIODIC"]
        machines = si_by_group.get(gg["src_key"], [])
        by_file = {m.get("inspection_criteria_file", ""): len(m.get("inspection_items") or []) for m in machines}
        scopes = {m["name"]: m["scope"] for m in machines if m.get("scope")}
        insp = {"is_target": bool(machines), "machines": [m["name"] for m in machines],
                "scopes": scopes,
                "criteria_items": sum(by_file.values()), "criteria_files": sorted(by_file),
                "criteria_articles": sorted({m.get("criteria_article", "") for m in machines})}
        for m in machines:
            # ★ 적용 범위를 **주기보다 먼저** 보여준다. 6종에 괄호 단서가 있는데
            #   (정격하중 2톤 미만 크레인, 이동식 국소배기장치, 밀폐형 롤러기 …) 화면에는
            #   '안전검사 대상 · 2년마다'만 떠서, 대상이 아닌 설비까지 대상으로 읽혔다.
            if m.get("scope"):
                add("PERIODIC", "안전검사(법정)", f"대상 범위 — {m['name']}: {m['scope']}",
                    m.get("source_ref", "시행령 제78조제1항"))
            for ln in cycle_lines(m, gg["name"], group_names):
                add("PERIODIC", "안전검사(법정)", ln, "시행규칙 제126조제1항")
        if machines:
            # 면제를 안 적으면 이미 다른 법령 검사를 받은 사업주도 받아야 하는 것으로 읽는다.
            add("PERIODIC", "안전검사(법정)",
                "다른 법령에 따른 검사·점검을 이미 받은 경우 안전검사가 면제될 수 있습니다 "
                "(건설기계관리법·고압가스법·전기안전관리법 등 11가지)", "시행규칙 제125조")
        if insp["criteria_items"]:
            add("PERIODIC", "안전검사(법정)", f"안전검사 검사기준 {insp['criteria_items']}개 항목",
                f"고시 {'·'.join(insp['criteria_articles'])} → {', '.join(insp['criteria_files'])}")
        n_periodic_law = slots["PERIODIC"] - n_periodic_article

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

        # ★ 정기 칸의 근거는 세 갈래이고 무게가 다르다. 화면에서 섞어 보여주면
        #   '안 하면 위법'과 '하면 좋음'이 구별되지 않는다.
        #     조문     — 규칙이 직접 정한 정기 의무(법정). 주기가 '상시'처럼 느슨할 수 있다
        #     안전검사 — 법 제93조. 주기와 검사기준이 고시로 확정돼 있다(법정)
        #     가이드   — KOSHA 권고
        insp["periodic_article"] = n_periodic_article
        insp["periodic_law"] = n_periodic_law
        insp["periodic_guide"] = slots["PERIODIC"] - n_periodic_article - n_periodic_law
        insp["periodic_source"] = "+".join(
            s for s, v in (("안전검사", n_periodic_law), ("조문", n_periodic_article),
                           ("가이드", insp["periodic_guide"])) if v) or "없음"

        # 흐름이 통째로 빈 그룹의 사유를 남긴다. '자료가 없다'와 '이 그룹의 조문이 정의·적용범위뿐이라
        # 할 일이 없다'는 다른 말이고, 후자를 전자로 읽으면 데이터 결손으로 오해한다.
        own_skipped = sorted(set(gg["codes"]) & NO_DUTY,
                             key=lambda c: int(re.match(r"제(\d+)", c).group(1)))

        # src_key = 카탈로그(gimulmul_index)의 원래 그룹키. RESOLVE가 내는 group_key와 조인하려면
        # 분리 전 키가 있어야 한다(분리된 그룹은 no != src_key).
        report.append({"no": k, "src_key": gg["src_key"], "subject": gg["label"], "path": gg["path"], "name": nm,
                       "coord": list(gg["coord"]),
                       "guide": gcode, "apx3": [r["no"] for r in a3_rows],
                       "slots": slots, "filled": sum(1 for x, _ in SKELETON if slots[x]),
                       "items": items, "inspection": insp, "no_duty_articles": own_skipped,
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

    if skipped:
        ex = ", ".join(sorted(skipped, key=lambda c: int(re.match(r"제(\d+)", c).group(1)))[:6])
        print(f"\n의무 아닌 조문 {len(skipped)}종을 흐름에서 뺐다(목적·정의·적용 제외) — 예: {ex}")

    print(f"\n별표 3 붙은 그룹 {sum(1 for r in report if r['apx3'])}종 · "
          f"가이드 붙은 그룹 {sum(1 for r in report if r['guide'])}종 · "
          f"안전검사 대상 {sum(1 for r in report if r['inspection']['is_target'])}종")
    print("\n=== 정기 칸 근거 강도 ===")
    psrc = {}
    for r in report:
        s = r["inspection"]["periodic_source"]
        psrc[s] = psrc.get(s, 0) + 1
    for src, v in sorted(psrc.items(), key=lambda x: (x[0] == "없음", -x[1])):
        print(f"  {src:18} {v:>3}종")

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
