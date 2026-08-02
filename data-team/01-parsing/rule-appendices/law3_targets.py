#!/usr/bin/env python3
"""법·시행령·시행규칙 43개 조문을 **어느 기인물 그룹에 붙일지** 정한 표.

흐름 6칸의 재료는 원래 산업안전보건기준규칙(669조)과 그 별표 2·3·4, 안전검사 고시뿐이었다.
법·시행령·시행규칙 554조를 훑어 기인물 단위로 매달 수 있는 의무 43건을 찾았고
(`law3_flow_gap_candidates.json`), 이 파일이 그 43건의 **적용 대상**을 명시한다.

★ 왜 표로 적나. 붙이는 대상을 코드가 알아서 정하게 두면 과부착한다 —
  같은 유형의 버그가 이 프로젝트에서 **7번** 났다(제41·99조 상속, 제98·86조 상속,
  제133·178조 절 총칙, 안전검사 주기까지). 조문마다 근거를 적어 두고 사람이 읽을 수 있게 한다.

붙이는 방식(kind):
  machines   기계 이름 목록 → 그룹. 목록은 법령이 정한 닫힌 목록이어야 한다
  coord      좌표 접두사 (편,장,절[,관]) → 그 아래 전부
  all_machine 편2장1 전체(기계·기구 및 그 밖의 설비) — 기계류 공통 의무
  none       붙이지 않는다. 대상 목록을 확보하지 못한 경우 등. reason 필수
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARSED = Path(__file__).resolve().parent / "parsed"
LAW_APX = ROOT / "data-team" / "01-parsing" / "law-appendices" / "parsed"


def nkey(s: str) -> str:
    """이름 매칭용 정규화. 공백·가운뎃점·괄호를 지운다."""
    return re.sub(r"[\s·ㆍ()（）\[\]]", "", unicodedata.normalize("NFKC", s or ""))


def load_list(name: str) -> list[str]:
    """법령 별표의 기계 이름 목록. 괄호 안 부연은 매칭에 방해되므로 떼어 별도 후보로 둔다."""
    f = {"영 별표 20": LAW_APX / "decree-20.json", "영 별표 21": LAW_APX / "decree-21.json"}.get(name)
    if not f or not f.exists():
        return []
    d = json.loads(f.read_text(encoding="utf-8"))
    return [r["subject"] for r in d["rows"]]


def _vehicle_construction() -> list[str]:
    """규칙 별표 6 '차량계 건설기계' — 불도저·로더·스크레이퍼 …가 여기 묶여 있다.

    ★ 영 별표 21은 불도저·모터 그레이더·로더를 낱개로 열거하는데, 기인물 카탈로그에는
      그 이름의 그룹이 없다. 규칙 별표 6이 이들을 '차량계 건설기계'로 묶으므로 그걸 경유한다.
      경유하지 않으면 25종 중 12종이 아무 데도 안 붙는다.
    """
    p = PARSED / "appendix-06.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    ds = d if isinstance(d, list) else [d]
    out = []
    for x in ds:
        for r in x.get("rows", []):
            s = r.get("subject", "")
            out.append(s)
            # ★ 괄호를 **뗀** 이름도 넣어야 한다. '로더(포크 등 부착물 …)'를 통째로만 넣으면
            #   영 별표 21의 '로더'와 매칭되지 않는다(실제로 72건이 조용히 안 붙었다).
            out.append(re.sub(r"[(（][^)）]*[)）]", "", s))
            # '도저형 건설기계(불도저, 스트레이트도저 …)' → 괄호 안 낱개 이름도 후보로
            m = re.search(r"[(（]([^)）]*)[)）]", s)
            if m:
                for y in re.split(r"[,、ㆍ·]", m.group(1)):
                    # '드래그라인 등' 같은 꼬리를 떼지 않으면 '드래그라인'과 안 붙는다
                    y = re.sub(r"\s*등$", "", y.strip())
                    y = re.sub(r"\([^)]*\)|[a-zA-Z:,]+.*$", "", y).strip()
                    if len(y) >= 3:
                        out.append(y)
    return [x.strip() for x in out if x.strip()]


def resolve_machines(names: list[str], groups: list[dict]) -> tuple[set[str], list[str]]:
    """기계 이름 목록 → 그룹키 집합. 못 붙인 이름도 함께 돌려준다.

    ★ 가장 구체적인 것 하나만 고른다. '이동식 크레인'이 '크레인'과 '이동식 크레인' 두 그룹에
      다 걸리면 안 된다(부분 문자열 매칭의 함정). 완전 일치가 있으면 그것만 쓴다.
    ★ 못 붙인 이름을 **버리지 않고 돌려준다.** 예초기·공기압축기·금속절단기처럼
      법령이 대상으로 정했는데 기인물 카탈로그에 그룹이 없는 기계가 실제로 있다.
    """
    veh = {nkey(x) for x in _vehicle_construction()}
    hit, miss = set(), []
    for n in names:
        k = nkey(re.sub(r"[(（][^)）]*[)）]", "", n))       # 괄호 부연 제거
        if len(k) < 2:
            continue
        exact = [g for g in groups if nkey(g["name"]) == k]
        part = exact or [g for g in groups if k in nkey(g["name"]) or nkey(g["name"]) in k]
        # 규칙 별표 6 경유. 두 별표의 표기가 조금씩 달라(콘크리트 펌프 ↔ 콘크리트 펌프카,
        # 스크레이퍼 도저 ↔ 스크레이퍼) 완전 일치만 보면 놓친다.
        if not part and any(len(v) >= 3 and (k in v or v in k) for v in veh):
            part = [g for g in groups if nkey(g["name"]) == nkey("차량계 건설기계 등")]
        if part:
            # 완전 일치가 없으면 이름이 가장 긴(= 가장 구체적인) 것 하나만
            best = exact or [max(part, key=lambda g: len(nkey(g["name"])))]
            hit |= {g["key"] for g in best}
        else:
            miss.append(n)
    return hit, miss


# ── 43건의 적용 대상 ──────────────────────────────────────────────
# 근거는 전부 조문 원문이다. `law3_flow_gap_candidates.json`의 quote와 짝을 이룬다.
# (법, 조문코드, 칸) → 대상
LAW = "산업안전보건법"
DEC = "산업안전보건법 시행령"
ENF = "산업안전보건법 시행규칙"

# 자주 쓰는 좌표 (편,장,절[,관]) — ★ 전부 실제 산출물에서 확인한 값이다.
#   처음엔 눈대중으로 적었다가 석면(3,1,2)·화학설비(2,1,4)·비계(2,4,1)가 전부 틀렸다.
#   좌표는 **반드시 대조하고 쓴다.** 이 프로젝트에서 같은 유형 버그가 7번 났다.
C_석면해체 = (3, 2, 6)       # 보건기준 > 허가대상 유해물질 및 석면 > 석면의 해체ㆍ제거 작업 …
C_허가대상 = (3, 2)          # 허가대상 유해물질 및 석면 전체
C_관리대상 = (3, 1)          # 관리대상 유해물질
C_금지 = (3, 3)             # 금지유해물질
C_이상기압 = (3, 5)
C_비계 = (1, 7)             # 총칙 > 비계
C_거푸집 = (2, 4, 1)        # 건설작업 등 > 거푸집 및 동바리

TARGETS: dict[tuple[str, str, str], dict] = {
    # ── 방호조치 (영 별표 20 = 예초기·원심기·공기압축기·금속절단기·지게차·포장기계) ──
    (LAW, "제80조", "PERIODIC"): {"kind": "machines", "list": "영 별표 20",
                                  "note": "제3항 방호조치 상시 점검·정비"},
    (LAW, "제80조", "EXEC"): {"kind": "machines", "list": "영 별표 20",
                              "note": "제4항 방호조치 해체 시 조치"},
    (DEC, "제70조", "PRECHECK"): {"kind": "machines", "list": "영 별표 20",
                                  "note": "방호조치 대상 기계 목록 자체"},
    (ENF, "제98조", "PRECHECK"): {"kind": "machines", "list": "영 별표 20",
                                  "note": "기계별 방호장치를 1:1로 지정"},
    (ENF, "제99조", "EXEC"): {"kind": "machines", "list": "영 별표 20",
                              "note": "제98조가 방호조치를 지정한 기계로 대상이 닫힌다"},

    # ── 대여 (영 별표 21) ──
    (DEC, "제71조", "PRECHECK"): {"kind": "machines", "list": "영 별표 21"},
    (ENF, "제100조", "PRECHECK"): {"kind": "machines", "list": "영 별표 21",
                                   "note": "대여자가 미리 점검·보수. 대여받는 쪽에서도 확인 대상"},
    (ENF, "제101조", "ASSIGN"): {"kind": "machines", "list": "영 별표 21",
                                 "note": "조작자의 자격·기능 확인"},
    (ENF, "제101조", "EXEC"): {"kind": "machines", "names": ["타워크레인"],
                               "note": "제2항은 타워크레인만 지목한다"},

    # ── 안전인증 · 자율안전확인 (영 제74조 / 제77조 목록) ──
    (LAW, "제87조", "PRECHECK"): {"kind": "machines",
                                  "names": ["프레스", "전단기", "절곡기", "크레인", "리프트", "압력용기",
                                            "롤러기", "사출성형기", "고소작업대", "곤돌라"],
                                  "note": "영 제74조제1호 기계·설비. 방호장치·보호구는 기인물 그룹이 아니라 제외"},
    (DEC, "제74조", "PRECHECK"): {"kind": "machines",
                                  "names": ["프레스", "전단기", "절곡기", "크레인", "리프트", "압력용기",
                                            "롤러기", "사출성형기", "고소작업대", "곤돌라"]},
    (ENF, "제107조", "PRECHECK"): {"kind": "machines",
                                   "names": ["크레인", "리프트", "곤돌라", "프레스", "전단기", "절곡기",
                                             "압력용기", "롤러기", "사출성형기", "고소작업대"],
                                   "note": "설치·이전 시 / 주요 구조 변경 시 안전인증 대상"},
    (LAW, "제92조", "PRECHECK"): {"kind": "machines",
                                  "names": ["연삭기", "산업용 로봇", "혼합기", "파쇄기", "분쇄기",
                                            "식품가공용 기계", "컨베이어", "자동차정비용 리프트",
                                            "공작기계", "고정형 목재가공용 기계", "인쇄기"],
                                  "note": "영 제77조제1항제1호 자율안전확인대상 기계"},
    (DEC, "제77조", "PRECHECK"): {"kind": "machines",
                                  "names": ["연삭기", "산업용 로봇", "혼합기", "파쇄기", "분쇄기",
                                            "식품가공용 기계", "컨베이어", "자동차정비용 리프트",
                                            "공작기계", "고정형 목재가공용 기계", "인쇄기"]},

    # ── 건설공사도급인 (영 제66조 = 타워크레인·건설용 리프트·항타기·항발기) ──
    (LAW, "제76조", "EXEC"): {"kind": "machines", "names": ["타워크레인", "리프트", "항타기", "항발기"]},
    (DEC, "제66조", "EXEC"): {"kind": "machines", "names": ["타워크레인", "리프트", "항타기", "항발기"]},
    (ENF, "제94조", "PRECHECK"): {"kind": "machines", "names": ["타워크레인", "리프트", "항타기", "항발기"],
                                  "note": "작업 시작 전 합동 안전점검"},
    (LAW, "제82조", "ASSIGN"): {"kind": "machines", "names": ["타워크레인"],
                                "note": "설치·해체는 등록업자에게만 시킬 수 있다"},

    # ── 석면 ── 절 하나로 좁힌다. (3,2) 전체에 붙이면 베릴륨·방독마스크 그룹까지 간다
    (LAW, "제119조", "PLAN"): {"kind": "coord", "prefixes": [C_석면해체]},
    (LAW, "제122조", "ASSIGN"): {"kind": "coord", "prefixes": [C_석면해체]},
    (LAW, "제123조", "EXEC"): {"kind": "coord", "prefixes": [C_석면해체]},
    (LAW, "제124조", "POST"): {"kind": "coord", "prefixes": [C_석면해체]},
    (ENF, "제176조", "PLAN"): {"kind": "coord", "prefixes": [C_석면해체]},
    (ENF, "제182조", "POST"): {"kind": "coord", "prefixes": [C_석면해체]},
    (ENF, "제185조", "POST"): {"kind": "coord", "prefixes": [C_석면해체]},

    # ── 물질안전보건자료(MSDS) ── 대상은 '물질안전보건자료대상물질'이라 화학물질 3개 장 전체
    (LAW, "제115조", "EXEC"): {"kind": "coord", "prefixes": [C_관리대상, C_허가대상, C_금지]},
    (ENF, "제167조", "EXEC"): {"kind": "coord", "prefixes": [C_관리대상, C_허가대상, C_금지]},
    (ENF, "제168조", "EXEC"): {"kind": "coord", "prefixes": [C_관리대상, C_허가대상, C_금지]},
    (ENF, "제169조", "ASSIGN"): {"kind": "coord", "prefixes": [C_관리대상, C_허가대상, C_금지]},
    (ENF, "제170조", "EXEC"): {"kind": "coord", "prefixes": [C_관리대상, C_허가대상, C_금지]},

    # ── 도급 (화학설비·유해작업) ──
    (LAW, "제58조", "ASSIGN"): {"kind": "coord", "prefixes": [C_허가대상],
                                "note": "허가대상물질 제조·사용 작업 도급금지. 도금·수은납카드뮴 작업은 "
                                        "기인물 카탈로그에 대응 그룹이 없다"},
    (LAW, "제65조", "PRECHECK"): {"kind": "machines", "names": ["화학설비"],
                                  "note": "규칙 별표 7 화학설비 및 그 부속설비"},
    (ENF, "제83조", "PRECHECK"): {"kind": "machines", "names": ["화학설비"]},
    (ENF, "제86조", "PLAN"): {"kind": "machines", "names": ["타워크레인", "리프트", "항타기", "항발기",
                                                           "차량계 건설기계 등"],
                             "note": "건설공사용 기계·기구의 배치 및 이동계획"},

    # ── 유해위험방지계획서 · 설계변경 ──
    (LAW, "제42조", "PLAN"): {"kind": "machines",
                              "names": ["용해로", "화학설비", "건조설비", "가스집합 용접장치",
                                        "국소 배기장치"],
                              "note": "영 제42조제2항 대상 기계·설비"},
    (DEC, "제42조", "PLAN"): {"kind": "machines",
                              "names": ["용해로", "화학설비", "건조설비", "가스집합 용접장치",
                                        "국소 배기장치"]},
    # 가설구조물은 이름이 아니라 좌표로 잡는다. '비계'는 이름 매칭이 6개 관에 다 걸리는데
    # 그게 맞고(비계 절 전체), 흙막이 지보공은 대응 그룹이 없어 이름 매칭이 조용히 실패한다.
    (DEC, "제58조", "PLAN"): {"kind": "coord", "prefixes": [C_비계, C_거푸집],
                              "note": "높이 31m 이상 비계 · 작업발판 일체형 또는 5m 이상 거푸집 동바리. "
                                      "흙막이 지보공·터널 지보공은 대응 그룹이 없다. 규격 조건은 항목 문구에 남는다"},

    # ── 이상기압 (고압실 작업) ──
    (LAW, "제139조", "ASSIGN"): {"kind": "coord", "prefixes": [C_이상기압]},
    (DEC, "제99조", "EXEC"): {"kind": "coord", "prefixes": [C_이상기압]},

    # ── 특별교육 (시행규칙 별표 5) — 작업명 매칭은 build 쪽에서 별도 처리 ──
    (LAW, "제29조", "ASSIGN"): {"kind": "byeolpyo5"},
    (ENF, "제26조", "ASSIGN"): {"kind": "byeolpyo5"},
    (ENF, "제27조", "ASSIGN"): {"kind": "byeolpyo5"},

    # ── 대상 목록을 확보하지 못한 것 ──
    # 법 제140조의 작업 목록은 「유해·위험작업의 취업 제한에 관한 규칙」에 있고 우리에게 없다.
    # 추측으로 기계를 고르면 과부착이다. 기계류 전반에 **조문의 존재만** 알린다.
    (LAW, "제140조", "ASSIGN"): {"kind": "all_machine",
                                 "note": "자격·면허 필요 작업 목록은 별도 규칙 — 미확보. 조문 존재만 알린다"},
}
