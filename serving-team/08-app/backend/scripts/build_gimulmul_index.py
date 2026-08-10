#!/usr/bin/env python3
"""OWA→CWA 정밀화 — 기인물(起因物) 인덱스 구축.

사용자 통찰: 산업안전보건규칙의 편/장/절/관 계층은 대부분 '기인물'(사고를 일으키는
기계·설비·물질·구조물)별로 조직돼 있다. 절8=사출성형기, 절10관2=지게차, 절12관1=차량계
건설기계처럼 절/관 이름 자체가 기인물이다. 따라서 사진의 기인물을 먼저 식별하면 →
해당 절/관 → 그 안의 조문으로 좁히는 게 자유 의미매칭보다 P@1이 높다.

산출 gimulmul_index.json:
  groups: {group_key: {gimulmul, pyeon, jang, jeol, gwan, articles:[{code,title,observable}]}}
  cross_cutting: 기인물 무관 횡단 관찰조문 그룹키 목록(보호구·추락·전도·통로·작업장 등)
  observable_codes: 관찰가능(yes/partial) 조문코드 집합

사용: .venv/bin/python scripts/build_gimulmul_index.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SIGS = ART / "article_signatures.jsonl"
OUT = ART / "gimulmul_index.json"

# 기인물 무관 '횡단' 일반의무 — 어떤 기인물 사진에도 적용 가능(장 단위)
#
# ★ 이 목록의 효과는 **하나뿐이다: RESOLVE 앵커 카탈로그에서 뺀다.**
#   (조문 후보의 '항상 포함'은 cue_article_service.CROSS의 16개 조문이 따로 담당한다.
#    제3·5·13·14·20조=작업장 / 제22·23조=통로 / 제32조=보호구 / 제42~46조=추락 / 제88·92·93조=기계 일반)
#
# ⚠ **'장7 비계'를 뺐다(2026-08-02).** 비계는 횡단이 아니다:
#   - 사진에서 형태로 뚜렷이 식별된다(강관·달비계·말비계·시스템 비계)
#   - 흐름에 **시간축이 있다** — 계획·인적 배치·작업 전 점검·작업 중이 골고루 찬다
#     (작업장·통로·보호구는 '작업 중' 한 칸뿐이라 진짜 횡단이다)
#   - CROSS 16개 조문에도 비계는 하나도 없다 → 카탈로그에서도 빠지고 항상-후보에도 없어
#     **앵커로 도달할 경로가 통째로 없었다.** 사진에 비계가 찍혀도 비계 흐름이 뜨지 않았다
#   alias는 이미 비계 어휘 9종을 매핑하고 있어 조문 후보에는 들어가고 있었다 — 흐름만 못 받았다
#
# ⚠ 이 목록을 바꾸면 RESOLVE 카탈로그가 바뀌므로 **앵커 정확도를 재측정해야 한다**
#   (measure_anchor_accuracy.py). 0.711은 비계를 뺀 99종 카탈로그에서 잰 값이다.
CROSS_CUTTING_JANG = [
    "장2 작업장", "장3 통로", "장4 보호구",
    "장6 추락 또는 붕괴에 의한 위험 방지",
]

# ── 크레인 세분류 (사용자 승인 2026-08-06) ──────────────────────────────
# 관2 '크레인'은 실제로 네 종류가 섞여 있다 — 조문이 스스로 종류를 지목한다:
#   제142조 "타워크레인의 지지" / 제139·140조 "주행 크레인" / 제144·145조 "주행 크레인 또는
#   선회 크레인" / 제138조 "지브 크레인". 사진 식별력도 서로 뚜렷하다(수직 마스트 vs 천장
#   거더 vs 벽부착 지브). 종류를 안 가르면 타워크레인 사진에 천장크레인 통로 조문이 붙는다.
# 전용에 없는 나머지(제136·137·141·143·146)는 **공통** — 세 서브타입 모두에 들어간다.
# ⚠ 카탈로그가 바뀌므로 RESOLVE 재실행 + 앵커 재측정 필수(캐시가 sha로 자동 감지).
# ⚠ gimulmul 라벨에 괄호 설명을 넣으면 안 된다 — 흐름 조립기의 이름 매칭(name_variants)이
#   이 라벨을 매칭 키로 쓰는데, 괄호는 벗겨져도 내용물이 키에 섞여 별표 4 이름매칭이 조용히
#   빠진다(실제로 타워크레인 작업계획서가 안 붙었다). ㆍ구분 나열은 조각별로 쪼개져 안전하다.
CRANE_KEY = "절9 양중기 > 관2 크레인"
# 제144·145조는 문언이 "주행 크레인 **또는 선회 크레인**" — 지브가 선회형이므로 두 서브타입이
# 공유한다(게이트 감사가 잡았다, 2026-08-07).
CRANE_SPLIT = [
    ("타워크레인", "타워크레인", ["제142조"]),
    ("천장·갠트리 등 주행형 크레인", "천장크레인ㆍ갠트리크레인ㆍ호이스트 등 주행형",
     ["제139조", "제140조", "제144조", "제145조"]),
    ("지브 크레인", "지브 크레인ㆍ벽부착 선회형", ["제138조", "제144조", "제145조"]),
]

# ── 천공기 분리 (medium 해소, 사용자 승인 2026-08-07) ─────────────────
# '차량계 건설기계 등' 묶음은 밀폐 캡 차량(불도저·로더·롤러)과 **회전 로드가 노출되는
# 천공기류**를 섞고 있다. 그래서 공작기계 조문(제87·94·95)의 실질 무관 판정이 medium에
# 묶였다 — 묶음을 가르면 캡 차량 쪽은 high로 풀리고 천공기는 그 조문을 유지한다.
# 크레인과 달리 전용 조문이 없어 조문 배분은 없다(전 조문 공유, 라벨만 다르다).
DRILL_KEY = "절12 건설기계 등 > 관1 차량계 건설기계 등"
DRILL_SPLIT = [
    ("차량계 건설기계", "불도저ㆍ로더ㆍ스크레이퍼ㆍ롤러 등 밀폐 캡 차량형 건설기계", None),
    ("천공기 등 회전 로드형 건설기계", "천공기ㆍ어스드릴ㆍ어스오거 등 회전 로드 노출형", None),
]

# ── 판별 단서 보강 (A0 오류 분해 후속, 2026-08-10) ─────────────────────
# gimulmul 라벨이 절 이름 그대로라('사출성형기 등') RESOLVE가 그라인더·석면 해체
# 현장을 이 그룹과 연상하지 못했다(gold 51 진짜 오인식 7건 중 6건의 원인 축 —
# docs/dev-notes/anchor-a0-metrics-2026-08-09.md S2). 라벨을 **소속 조문의 실제
# 대상 나열**로 보강한다 — 각 조각은 그룹 소속 조문 제목에 근거한 사실이지 추측이 아니다.
# ⚠ 괄호 금지(위 name_variants 규칙 — 괄호 내용물이 이름 매칭 키를 오염시킨다). ㆍ나열만.
# ⚠ 카탈로그 서술이 바뀌므로 RESOLVE 재실행 + 앵커 재측정 필수.
GIM_ENRICH = {
    # 제121~131조: 사출성형기·연삭숫돌·롤러기·버프연마기·식품가공… — 소형 가공기계 모음
    # ⚠ '롤러기'는 라벨에 못 넣는다 — 영 별표 21(대여 목록)에 동명의 '롤러기'(도로 롤러)가
    #   있어 LAW3 이름 매칭이 대여 조문(시행규칙 제100·101조)을 오부착한다(동명이기 함정).
    #   제123조 롤러기 조문 자체는 전용 조문이라 흐름에 그대로 있다.
    "절8 사출성형기 등": "사출성형기ㆍ연삭기ㆍ핸드그라인더ㆍ버프연마기 등 소형 가공기계",
    # 제490·492·495조: 경고표지·출입 금지·밀폐 조치 — 사진에서는 비닐 밀폐·표지가 보인다
    "절6 석면의 해체ㆍ제거 작업 및 유지ㆍ관리 등의 조치기준":
        "석면 해체ㆍ제거 작업장ㆍ출입구 비닐 밀폐ㆍ경고표지ㆍ출입금지 구역",
    # 제239~246조: 화기 사용·용접·소화설비·화재감시자
    "절2 화기 등의 관리": "화기 작업ㆍ용접ㆍ소화기ㆍ소화설비ㆍ흡연구역 화재방지",
    # 제301~312조: 충전부·접지·누전차단기 — 절2(배선·이동전선)와의 판별 단서
    "절1 전기 기계ㆍ기구 등으로 인한 위험 방지":
        "전기 기계ㆍ기구ㆍ충전부 방호ㆍ접지ㆍ누전차단기ㆍ분전반 기기",
}


def parse(section: str):
    def g(p):
        m = re.search(p, section or "")
        return m.group(1).strip() if m else ""
    return {
        "pyeon": g(r"(편\d+[^>]*)"),
        "jang": g(r"(장\d+[^>]*)"),
        "jeol": g(r"(절\d+[^>]*)"),
        "gwan": g(r"(관\d+[^>]*)"),
    }


def group_key(p):
    if p["jeol"]:
        return p["jeol"] + (" > " + p["gwan"] if p["gwan"] else "")
    return p["jang"] or p["pyeon"] or "(상위)"


def gimulmul_label(p):
    """기인물 = 가장 깊은 절/관 이름(번호 제거)."""
    deepest = p["gwan"] or p["jeol"] or p["jang"]
    return re.sub(r"^[편장절관]\d+\s*", "", deepest).strip()


def main():
    obs = {}
    if SIGS.exists():
        for l in SIGS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                obs[r["article_code"]] = r["observable"]

    db = SessionLocal()
    rows = db.execute(text(
        "select article_code, title, coalesce(section,'') from articles "
        "where law_type='RULE' and not deleted and length(full_text)>10 order by article_code")).fetchall()
    db.close()

    groups = {}
    for code, title, section in rows:
        p = parse(section)
        gk = group_key(p)
        g = groups.setdefault(gk, {"gimulmul": gimulmul_label(p), **p, "articles": []})
        g["articles"].append({"code": code, "title": title, "observable": obs.get(code, "no")})

    if CRANE_KEY in groups:
        src = groups.pop(CRANE_KEY)
        specific = {c for _, _, arts in CRANE_SPLIT for c in arts}
        common = [a for a in src["articles"] if a["code"] not in specific]
        for name, gim_label, arts in CRANE_SPLIT:
            own = [a for a in src["articles"] if a["code"] in arts]
            groups[f"절9 양중기 > 관2 {name}"] = {
                "gimulmul": gim_label, "pyeon": src["pyeon"], "jang": src["jang"],
                "jeol": src["jeol"], "gwan": f"관2 {name}",
                "articles": own + common}
        print(f"크레인 세분류: {len(CRANE_SPLIT)}종 (전용 {len(specific)}조 배분 · 공통 {len(common)}조 공유)")

    if DRILL_KEY in groups:
        src = groups.pop(DRILL_KEY)
        for name, gim_label, _ in DRILL_SPLIT:
            groups[f"절12 건설기계 등 > 관1 {name}"] = {
                "gimulmul": gim_label, "pyeon": src["pyeon"], "jang": src["jang"],
                "jeol": src["jeol"], "gwan": f"관1 {name}",
                "articles": list(src["articles"])}
        print(f"천공기 분리: {len(DRILL_SPLIT)}종 (조문 전체 공유 · 라벨로 구분)")

    enriched = 0
    for gk, gim_label in GIM_ENRICH.items():
        if gk in groups:
            groups[gk]["gimulmul"] = gim_label
            enriched += 1
        else:
            print(f"⚠ 판별 단서 대상 그룹이 없다(키 확인): {gk}")
    if enriched:
        print(f"판별 단서 보강: {enriched}종 (조문 제목 근거 나열)")

    def is_cross(gk, g):
        return any(g["jang"].startswith(c) or c in g["jang"] for c in CROSS_CUTTING_JANG) and not g["jeol"] or \
               any(c in (g["jang"] or "") for c in CROSS_CUTTING_JANG)

    cross = sorted([gk for gk, g in groups.items()
                    if any(c in (g["jang"] or "") for c in CROSS_CUTTING_JANG)])

    out = {
        "groups": groups,
        "cross_cutting": cross,
        "observable_codes": sorted([c for c, o in obs.items() if o in ("yes", "partial")]),
        "n_groups": len(groups),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 요약 출력
    print(f"groups={len(groups)}  cross_cutting_groups={len(cross)}  observable={len(out['observable_codes'])}")
    print("\n=== 기인물 그룹(관찰가능 조문 ≥2개, 상위 35) ===")
    ranked = sorted(groups.items(),
                    key=lambda kv: -sum(1 for a in kv[1]["articles"] if a["observable"] in ("yes", "partial")))
    for gk, g in ranked[:35]:
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs < 2:
            continue
        cc = " [횡단]" if gk in cross else ""
        print(f"  {nobs:>2}obs | {g['gimulmul'][:24]:<24} | {gk[:46]}{cc}")


if __name__ == "__main__":
    main()
