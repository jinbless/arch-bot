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
    # ★ 절12 전체(2,1,12)로 걸었던 것은 과잉상속이었다(버그 9번째, gpt-5.6-sol 프로브가 잡았다).
    #   열거에 있는 건 항타기·항발기(관2)뿐이다 — 차량계 건설기계·굴착기는 제99조가 따로 규율하므로
    #   빼도 구멍이 생기지 않는다(제99조 ①: "차량계 하역운반기계등, 차량계 건설기계의 운전자가…").
    "제41조": {"allow": {(2, 1, 9), (2, 1, 12, 2), (2, 6, 2)}},
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
    # 제168·170조 — 문언이 "크레인 또는 이동식 크레인의 고리걸이 용구"로 자기한정한다(버그 10번째,
    # 게이트 감사가 잡았다). 와이어로프 상속이 리프트·곤돌라·승강기까지 번지지 않게 크레인류로 좁힌다.
    # 관2는 크레인 서브타입 3종이 공유하는 좌표다.
    "제168조": {"allow": {(2, 1, 9, 2), (2, 1, 9, 3)}},
    "제170조": {"allow": {(2, 1, 9, 2), (2, 1, 9, 3)}},
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

# ★ 예전에 "전 기인물 공통 주입"이라며 제38·39·35조를 126개 그룹에 무조건 넣었다. **틀렸다.**
#   셋 다 적용 대상이 닫힌 목록이다:
#     제38조제1항  13개 작업만 열거(별표 4와 1:1) → 실제 대상 10개 그룹, 116개가 오부착이었다
#     제39조제1항  그중 제2·6·8·10·11호만. 제2항은 항타기·항발기
#     제35조       별표 2(제1항)·별표 3(제2항)이 정하는 작업
#   이 주입이 계획·인적·작업전 칸의 '겉보기 100%'를 만들고 있었다.
#   제39조제1항이 지목하는 별표 4 호 번호. 원문: "제38조제1항제2호ㆍ제6호ㆍ제8호ㆍ제10호 및 제11호"
A39_HO = {"2", "6", "8", "10", "11"}

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

    # ── 특별교육(시행규칙 별표 5 제1호 라목) — 작업 39종 → 그룹 ──────────
    b5_p = ART / "byeolpyo5_job_groups.json"
    b5_groups: set[str] = set()
    if b5_p.exists():
        b5 = json.loads(b5_p.read_text(encoding="utf-8"))
        for m in b5["mappings"]:
            for gk in m["group_keys"]:
                if gk not in G:
                    continue
                b5_groups.add(gk)
                # 작업 자체를 항목으로 넣는다. '이 기인물의 어떤 작업이 특별교육 대상인가'가 핵심이고,
                # 조문(법 제29조 등)만 넣으면 그게 안 보인다.
                by_group.setdefault(gk, []).append({
                    "phase": "ASSIGN", "text": f"특별교육 대상 작업 — {m['작업명'][:80]}",
                    "evidence": m["작업명"],
                    "ref": f"시행규칙 별표 5 제1호라목제{m['no']}호", "note": ""})
        miss = ", ".join(f"제{u['no']}호" for u in b5.get("unmapped") or [])
        print(f"특별교육 대상작업 {b5['n_mapped']}/{b5['n_jobs']}종을 {len(b5_groups)}개 그룹에 붙였다"
              + (f" (대응 그룹 없음: {miss})" if miss else ""))

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
        elif kind == "byeolpyo5":
            # 특별교육은 **작업 종류**가 대상이라 기계 목록이나 좌표로는 못 잡는다.
            # 별표 5 제1호 라목의 작업 39종을 그룹에 매핑한 표(byeolpyo5_job_groups.json)를 쓴다.
            keys = b5_groups
        else:
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
    # 크레인 4분할(2026-08-06) 이전에 만든 coverage-report는 옛 관2 키를 가리킨다.
    # 분할 전 '크레인' 검사가 관2 전체를 커버했으므로 세 서브타입 모두로 부채질한다(행동 보존).
    # ⚠ 타워크레인은 건설기계관리법 검사와의 면제 관계(시행규칙 제125조)가 별도 백로그다 —
    #   그 결정 전까지는 검사 항목을 보여주는 쪽이 안전하다(없다고 하는 것보다).
    FAN = {"절9 양중기 > 관2 크레인": [
        "절9 양중기 > 관2 타워크레인", "절9 양중기 > 관2 천장·갠트리 등 주행형 크레인",
        "절9 양중기 > 관2 지브 크레인"]}
    by_group: dict[str, list] = {}
    for m in c["machines"]:
        for g in m["gimulmul_groups"]:
            for key in FAN.get(g["key"], [g["key"]]):
                by_group.setdefault(key, []).append(by_name[m["name"]])
    return by_group, by_name


def pg(sql: str) -> list[str]:
    r = subprocess.run(["docker", "exec", "kosha-pg", "sh", "-c",
                        f'psql -U $POSTGRES_USER -d $POSTGRES_DB -tAF"|" -c "{sql}"'],
                       capture_output=True, text=True, encoding="utf-8")
    return [x for x in (r.stdout or "").splitlines() if x.strip()]


def main() -> None:
    si_by_group, _ = load_inspection()
    APH, NO_DUTY = load_article_phases()
    # Sol 검토 승인분 (사용자 승인 2026-08-03). 생성: gen_sol_overrides.py
    _ov_p = Path(__file__).resolve().parent / "sol_review_overrides.json"
    _ov = json.loads(_ov_p.read_text(encoding="utf-8")) if _ov_p.exists() else {}

    def _ov_pk(ref):
        m = re.match(r"^(법|시행령|시행규칙)?\s*(제\d+조(?:의\d+)?)", (ref or "").strip())
        return (m.group(1) or "", m.group(2)) if m else None

    OV_REF_DROPS = {_ov_pk(x["ref"]) for x in _ov.get("ref_drops", [])}
    OV_SLOT_DROPS = {(_ov_pk(x["ref"]), x["slot"]) for x in _ov.get("slot_drops", [])}
    # 문언 기준(Sol 검토)과 실질 기준(사용자 검수 확장, high 32건 일괄 승인 2026-08-06)을
    # 한 집합으로 적용한다 — 출처는 overrides 파일이 구분해 기록한다.
    OV_PAIR_DROPS = {(_ov_pk(x["ref"]), x["group"])
                     for x in _ov.get("pair_drops", []) + _ov.get("practical_pair_drops", [])}
    OV_SLOT_ADDS = {(_ov_pk(x["ref"]), x["slot"]): x.get("evidence", "")
                    for x in _ov.get("slot_adds", [])}
    # 사람 검수 CSV — (그룹 no, 칸, ref, text) 정확 일치. 별표·가이드 항목도 대상이라
    # 조문 파싱을 거치지 않는다. 사람 검수는 모든 판정을 덮어쓴다.
    OV_HUMAN = {(x["group_no"], x["phase"], x["ref"], x["text"]): x
                for x in _ov.get("human_item_ops", [])}
    if _ov:
        print(f"[Sol 승인분] ref_drops {len(OV_REF_DROPS)} · slot_drops {len(OV_SLOT_DROPS)} · "
              f"slot_adds {len(OV_SLOT_ADDS)} · pair_drops {len(OV_PAIR_DROPS)} · "
              f"사람검수 item_ops {len(OV_HUMAN)}")
    # 사진 앵커로 쓸 수 있는가. 카탈로그 127종은 규칙의 절·관 구조를 그대로 옮긴 것이라
    # 통칙·보호구·관리처럼 **사진으로 지목할 수 없는 칸**이 섞여 있다.
    av_p = ART / "anchor_validity.json"
    ANCHOR = ({g["group_key"]: g for g in json.loads(av_p.read_text(encoding="utf-8"))["groups"]}
              if av_p.exists() else {})
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

        # ── 양중기 와이어로프(관7) → 형제 기계 관으로 상속 ─────────────
        # 사용자 판단(2026-08-06): "와이어로프는 양중기에서 무게를 지탱하는 부속품이고,
        # 대형 사고 예방을 위해 별도 관으로 뺐을 뿐 실제 흐름은 양중기 각 내용 안에
        # 포함되어야 한다." 문언도 이를 지지한다 — 제163조 등이 '양중기의 와이어로프'를
        # 대상으로 하므로 크레인·리프트를 쓰는 사업주의 의무다.
        # 관7 자신은 이 상속으로 고유 항목이 사라져 우산 판정에 자동으로 걸린다(별도 흐름 소멸).
        WIRE_GWAN = (2, 1, 9, 7)
        if here == (2, 1, 9) and gwan not in (None, 1, 7):
            wire_key = next((kk for kk, g2 in G.items() if tuple(g2["coord"]) == WIRE_GWAN), None)
            if wire_key:
                for c in G[wire_key]["codes"]:
                    if c not in own and applies(c, gg["coord"]):
                        add_article("조문(와이어로프 상속)", c)
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

        # ★★ 제35·38·39조는 **닫힌 목록**이다. 전 그룹에 주입하면 안 된다.
        #   제38조제1항은 13개 작업만 열거한다(별표 4와 1:1). 그런데 126개 그룹에 주입돼
        #   추락 방지·비계·보호구 그룹에도 '사전조사 및 작업계획서'가 떠 있었다 — 92%가 오부착.
        #   계획·인적·작업전 칸이 '겉보기 100%'였던 것이 순전히 이 때문이다.
        #   적용범위 무시 버그의 **8번째** 발현이고 가장 컸다.
        #   → 아래 별표 4 매칭이 끝난 뒤에 대상을 정한다(add_common 참조).
        #   제35조는 따로 넣지 않는다 — 별표 2·3 항목이 이미 `제35조제1항/제2항`을 ref로 달고 있어
        #   조문을 또 넣으면 같은 말이 두 번 뜬다.

        # ── 법·시행령·시행규칙 조문 ────────────────────────────────────
        # 규칙 조문과 출처를 구분한다. 사람이 검수할 때 '이건 법이고 이건 규칙'이 보여야 한다.
        for x in LAW3.get(k, []):
            add(x["phase"], f"법령({x['ref'].split()[0]})", x["text"], x["ref"], x["evidence"])

        # ── PRECHECK: 별표 3 (좌표 정확 일치 — 19종만) ────────────────
        a3_rows = list(a3_by_coord.get(gg["coord"], []))
        # 와이어로프 통합(위 상속과 같은 사용자 판단): 관7 좌표에 붙는 별표 3 점검
        # (와이어로프·달기체인·섬유로프)도 양중기 각 기계의 작업 전 점검이다.
        if here == (2, 1, 9) and gwan not in (None, 1, 7):
            a3_rows += [r for r in a3_by_coord.get(WIRE_GWAN, []) if r not in a3_rows]
        for r in a3_rows:
            for it in r["items"]:
                add("PRECHECK", "별표 3", it, f"제35조제2항 · {r['subject'][:20]}")

        # ── PLAN: 별표 4 (이름 매칭) ──────────────────────────────────
        nm = gg["name"]
        a4_hits = set()
        for rr in a4["rows"]:
            if name_hit(nm, rr["subject"]):
                a4_hits.add(str(rr["no"]))
                for it in rr["items"]:
                    add("PLAN", "별표 4(이름매칭)", it, f"제38조제1항 · {rr['subject'][:20]}")
                for it in (rr.get("values") or {}).get("사전조사 내용", []) or []:
                    add("PLAN", "별표 4(사전조사·이름매칭)", it, rr["subject"][:20])

        # ── 제38·39조: 별표 4 대상 작업에만 ───────────────────────────
        # 제38조제1항 = 별표 4의 13개 작업. 제39조제1항 = 그중 **제2·6·8·10·11호만**
        # (차량계 하역운반기계등 / 굴착 / 교량 / 해체 / 중량물 취급).
        # 제39조제2항은 항타기·항발기 조립·해체·변경·이동 — 별표 4에 없는 별개 대상이다.
        if a4_hits and "제38조" in sigs and "제38조" not in own:
            ev = next((x["quote"] for x in APH.get("제38조", []) if x["phase"] == "PLAN"), "")
            add("PLAN", "조문(총칙)", sigs["제38조"]["title"], "제38조", ev)
        hangta = ("항타기" in nm or "항발기" in nm)
        if (a4_hits & A39_HO or hangta) and "제39조" in sigs and "제39조" not in own:
            ev = next((x["quote"] for x in APH.get("제39조", []) if x["phase"] == "ASSIGN"), "")
            add("ASSIGN", "조문(총칙)", sigs["제39조"]["title"], "제39조", ev)

        # ── ASSIGN: 별표 2 (좌표 우선, 없으면 이름) ───────────────────
        for rr in a2["rows"]:
            cc = packed_coord(rr.get("section_ref", ""))
            by_coord = cc == gg["coord"] or (cc[:3] == here and cc[3] is None and jeol is not None)
            if by_coord or name_hit(nm, rr["subject"]):
                src = "별표 2" if by_coord else "별표 2(이름매칭)"
                for it in rr["items"]:
                    add("ASSIGN", src, it, f"제35조제1항 · {rr['subject'][:20]}")

        # ── Sol 검토 승인분 적용 (sol_review_overrides.json) ──────────
        # 사용자 승인(2026-08-03)을 거친 판정만 들어있다. 근거 전문은 sol-review/.
        # 여기(별표까지 조립 끝, 안전검사·가이드 전)가 적용 지점인 이유:
        #   승인분의 ref는 전부 조문이고, 안전검사·가이드 항목의 ref는 조문이 아니라 매칭될 일이 없다.
        #   그리고 아래 PERIODIC 집계가 slots를 읽기 전에 숫자를 맞춰놔야 한다.
        def _pk(ref):
            # 접두사+조번호 프리픽스 매칭 — '시행규칙 제126조제1항'도 제126조로 잡는다.
            # 별표 항목('제38조제1항 · 지게차')의 오폭은 아래 source 게이트가 막는다.
            m = re.match(r"^(법|시행령|시행규칙)?\s*(제\d+조(?:의\d+)?)", (ref or "").strip())
            return (m.group(1) or "", m.group(2)) if m else None

        # ★ 스냅샷을 **드롭 전에** 뜬다. '칸 이동'(drop PRECHECK + add PLAN)에서 조문의 유일한
        #   칸을 먼저 지우면 복제할 원본이 사라져 이동이 삭제가 된다(실제로 시행규칙 제100조가
        #   그렇게 증발할 뻔했다).
        present0 = {}
        for ph in items:
            for it in items[ph]:
                if it["source"].startswith(("조문", "법령")):
                    ipk = _pk(it["ref"])
                    if ipk:
                        present0.setdefault(ipk, it)
        for ph in list(items):
            kept = []
            for it in items[ph]:
                # 승인분의 대상은 전부 조문·법령 항목이다. 별표·안전검사·가이드는 건드리지 않는다.
                if not it["source"].startswith(("조문", "법령")):
                    kept.append(it)
                    continue
                ipk = _pk(it["ref"])
                if ipk is None:
                    kept.append(it)
                    continue
                if ipk in OV_REF_DROPS:
                    continue
                if (ipk, ph) in OV_SLOT_DROPS:
                    continue
                if (ipk, gg["label"]) in OV_PAIR_DROPS:
                    continue
                kept.append(it)
            items[ph] = kept
        # slot_adds: 드롭 전 이 그룹에 있던 조문만. ref/pair 드롭된 조문은 되살리지 않는다.
        for (apk, slot), ev in OV_SLOT_ADDS.items():
            src_it = present0.get(apk)
            if (src_it is None or apk in OV_REF_DROPS
                    or (apk, gg["label"]) in OV_PAIR_DROPS
                    or any(_pk(it["ref"]) == apk for it in items[slot])):
                continue
            items[slot].append({"source": src_it["source"], "text": src_it["text"],
                                "ref": src_it["ref"], "evidence": ev})
        # ── 사람 검수 CSV 적용 (최후·최우선 — 사람 검수는 모든 판정을 덮어쓴다) ──
        # off = 그 자리에서 제거. move = correct_phase로 이동(항목 그대로 옮긴다).
        moves = []
        for ph in list(items):
            kept = []
            for it in items[ph]:
                h = OV_HUMAN.get((k, ph, it["ref"], it["text"]))
                if h is None:
                    kept.append(it)
                elif h["op"] == "move":
                    moves.append((h["to"], it))
                # drop이면 버린다
            items[ph] = kept
        for to, it in moves:
            if not any(x["ref"] == it["ref"] and x["text"] == it["text"] for x in items[to]):
                items[to].append(it)
        for ph in items:
            slots[ph] = len(items[ph])

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
                       # 사진 앵커 적격. 부적격이라도 조문이 무의미한 게 아니라
                       # **사진으로 지목할 수 없다**는 뜻이다(통칙·보호구·관리·상위 개념).
                       "anchor_kind": (ANCHOR.get(k) or {}).get("kind", ""),
                       "anchor_why": (ANCHOR.get(k) or {}).get("why", ""),
                       "detail": {x: [y["text"] for y in v[:3]] for x, v in items.items()}})

    # ── 우산 그룹 판정 ────────────────────────────────────────────────
    # 총칙·통칙은 **하위 기인물에 상속되어 운영되는 것**이지 그 자체가 별도의 흐름이 아니다.
    # 크레인 사진에 '양중기 > 총칙'을 앵커로 잡으면 21건만 보이고 크레인 전용 55건을 못 본다.
    #
    # ★ 이름('총칙'·'통칙')으로 고르지 않는다 — 이름은 거짓말을 하고, 반대로 이름이 총칙이 아닌
    #   우산도 있다(절1 기계 등의 일반기준). 대신 **데이터로** 판정한다:
    #     "이 그룹의 (조문, 칸) 전부가 다른 적격 그룹에도 있는가"
    #   전부 있으면 이 그룹을 빼도 사업주가 못 보게 되는 조문이 하나도 없다. 없으면 못 뺀다.
    #   이 기준은 스스로를 검사한다 — 상속이 나중에 깨지면 고유 항목이 생기고 우산에서 자동 탈락한다.
    def _pairs(r):
        return {(x["ref"], s) for s, v in r["items"].items() for x in v}

    covered = set()
    for r in report:
        if r["anchor_kind"] != "부적격":
            covered |= _pairs(r)
    # 한 문장으로: **앵커 부적격이면서 자기만의 의무가 없는 그룹**이 우산이다. 두 모양이 있다.
    #   상속형 — 항목이 있는데 전부 다른 적격 그룹에도 있다 (양중기 > 총칙)
    #   공백형 — 항목이 아예 없다. 조문이 목적·정의·적용범위뿐이다 (편3 각 장의 통칙 9종)
    # 둘 다 "빼도 사업주가 못 보게 되는 의무가 0건"이라는 같은 말이다.
    # 적격 그룹은 아무리 겹쳐도 우산으로 보지 않는다 — 지게차와 구내운반차는 서로 많이 겹치지만
    # 둘 다 사진에 보이는 기인물이다.
    umbrella = []
    for r in report:
        ps = _pairs(r)
        r["umbrella"] = r["anchor_kind"] == "부적격" and not (ps - covered)
        r["umbrella_kind"] = ("상속형" if r["umbrella"] and ps else "공백형" if r["umbrella"] else "")
        if r["umbrella"]:
            umbrella.append(r)

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

    # 예전에는 '겉보기 채움'과 '실질 채움'을 나눠 냈다. 제38·39·35조를 126개 그룹에 무조건
    # 주입해서 계획·인적·작업전이 100%로 보였기 때문이다. 그 주입을 적용범위대로 좁힌 뒤로는
    # 둘이 같다 — 이제 채움률을 그대로 믿어도 된다.
    for x, lab in SKELETON:
        empty = sum(1 for r in report if not r["slots"][x])
        print(f"  {lab:6} 빈 그룹 {empty:>3}종 · 채움 {(n - empty) / n:>4.0%}")
    rdist = {}
    for r in report:
        rdist[r["filled"]] = rdist.get(r["filled"], 0) + 1
    print("  칸 수 분포: " + " · ".join(f"{f}칸 {rdist[f]}종" for f in sorted(rdist, reverse=True)))

    if skipped:
        ex = ", ".join(sorted(skipped, key=lambda c: int(re.match(r"제(\d+)", c).group(1)))[:6])
        print(f"\n의무 아닌 조문 {len(skipped)}종을 흐름에서 뺐다(목적·정의·적용 제외) — 예: {ex}")

    if ANCHOR:
        ak = {}
        for r in report:
            ak[r["anchor_kind"] or "미분류"] = ak.get(r["anchor_kind"] or "미분류", 0) + 1
        print("\n=== 사진 앵커 적격 ===")
        for kk in ("기인물", "장소", "환경", "부적격", "미분류"):
            if ak.get(kk):
                print(f"  {kk:6} {ak[kk]:>3}종")
        print("  ⚠ 부적격 = 규칙 편제상의 칸(통칙·보호구·관리·상위 개념). 조문이 무의미한 게 아니라"
              " 사진으로 지목할 수 없다는 뜻이다")

    if umbrella:
        n_inh = sum(1 for r in umbrella if r["umbrella_kind"] == "상속형")
        print(f"\n=== 우산 그룹 {len(umbrella)}종 — 별도 흐름으로 내보내지 않는다 ===")
        print(f"  (상속형 {n_inh}종 · 공백형 {len(umbrella) - n_inh}종. 앵커 카탈로그·검수·정정 목록에서 제외)")
        for r in sorted(umbrella, key=lambda x: -sum(x["slots"].values())):
            c = sum(r["slots"].values())
            why = "전부 하위 기인물에 있음" if c else "의무 조문 자체가 없음(목적·정의·적용범위뿐)"
            print(f"  [{r['umbrella_kind']}] {r['subject'][:40]:42} {c:3d}건 → {why}")

    # 부적격인데 우산이 **아닌** 그룹 = 앵커로 못 잡는데 내용이 여기서만 있는 그룹.
    # 지우면 증발하므로 남겨둔다. 기본 안전수칙(always_applicable)이 다뤄야 할 후보다.
    orphan = [r for r in report if r["anchor_kind"] == "부적격" and not r["umbrella"]]
    if orphan:
        tot = sum(len(_pairs(r) - covered) for r in orphan)
        print(f"\n  ⚠ 부적격이지만 우산이 아닌 그룹 {len(orphan)}종 — 고유 항목 {tot}건은 여기서만 있다.")
        print("    빼면 증발한다. 앵커로 못 잡으니 기본 안전수칙 쪽에서 다뤄야 할 후보다:")
        for r in sorted(orphan, key=lambda x: -len(_pairs(x) - covered))[:8]:
            print(f"      {r['subject'][:42]:44} 고유 {len(_pairs(r) - covered):3d}건")

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

    # RESOLVE 카탈로그에서 뺄 키는 **src_key**다(카탈로그는 gimulmul_index의 원래 그룹키를 쓴다).
    # ★ 한 src_key에 여러 행이 붙어 있을 수 있다 — '절1 통칙'에는 편3의 12개 장 통칙이 다 뭉쳐 있다.
    #   그래서 "그 키에 붙은 행이 **전부** 우산이거나 빈 행일 때만" 뺀다. 하나라도 실제 흐름이
    #   있으면 빼지 않는다. 안 그러면 뭉친 키 하나 때문에 멀쩡한 앵커가 같이 사라진다.
    by_src: dict[str, list] = {}
    for r in report:
        by_src.setdefault(r.get("src_key") or r["no"], []).append(r)
    umb_src = sorted(k for k, rs in by_src.items() if all(r["umbrella"] for r in rs))

    # ── 관찰조문 0인데 사진 적격인 그룹 (곤돌라) ─────────────────────
    # 카탈로그 필터 `관찰가능 조문 ≥1`의 질문("조문이 관찰 가능한가")과 앵커의 질문
    # ("기인물이 사진에 보이는가")이 어긋나는 지점이다. 곤돌라는 전용 조문(제160조)이
    # 관찰 불가라 필터에 걸리지만, 외벽에 매달린 곤돌라는 사진에서 바로 지목된다.
    # anchor_validity가 적격(기인물·장소·환경)이라 한 그룹은 nobs=0이어도 카탈로그에 넣는다.
    OBS_OK_ = ("yes", "partial")
    gim_idx = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))
    eligible_zero = sorted(
        gk for gk, gg2 in gim_idx["groups"].items()
        if sum(1 for a in gg2["articles"] if a.get("observable") in OBS_OK_) == 0
        and gk not in gim_idx["cross_cutting"] and gk not in umb_src
        and (ANCHOR.get(gk) or {}).get("kind") in ("기인물", "장소", "환경"))
    if eligible_zero:
        print(f"관찰조문 0이지만 사진 적격이라 카탈로그에 넣는 그룹: {', '.join(eligible_zero)}")

    out = ART / "flow_slice_all.json"
    out.write_text(json.dumps({"_note": "기인물 그룹 113종 × 골격 6단계. 칸이 차는지만 본다(라벨 정확도는 사람 검수).",
                               "_umbrella": "총칙·통칙 등 내용이 전부 하위에 상속되는 그룹. 앵커·검수·정정 목록에서 뺀다. "
                                            "행은 남긴다 — 상속의 원본이고, 빠졌는지 대조할 근거이기 때문이다.",
                               "n_groups": n, "umbrella_group_keys": sorted(r["no"] for r in umbrella),
                               "umbrella_src_keys": umb_src,
                               "anchor_eligible_zero_obs_src_keys": eligible_zero,
                               "rows": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nRESOLVE 카탈로그에서 뺄 src_key {len(umb_src)}종: {', '.join(umb_src)}")
    print(f"\n→ {out.name}")


if __name__ == "__main__":
    main()
