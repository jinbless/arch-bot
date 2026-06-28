# -*- coding: utf-8 -*-
"""관찰단서(observable cue) → 조문 카탈로그 생성 (E00).

입구 = 사진에서 보이는 단서 3종 → 조문:
  ① 기인물(물건·설비)  ② 위험장소·구조  ③ 환경조건
소스 = cue-pool.json (없으면 채굴 pool + 환경조건으로 seed). 수정은 cue-pool.json 편집 후 재생성.
출력 = E00-관찰단서카탈로그.md  (ssot_explorer.html이 렌더·조문검증)
재생성: python3 docs/knowledge/감독관-판단기준/build_cue_catalog.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = HERE / "cue-pool.json"
OUT = HERE / "E00-관찰단서카탈로그.md"
MINED = Path("/mnt/c/Users/airat/AppData/Local/Temp/claude/C--project-arch-bot/29d24c5f-8ae0-4690-b9f6-5b24b05c8da5/scratchpad/gimulmul_pool.json")

# category → 단서 유형(cue_type)
CUE_TYPE = {
    "운반인양기계": "기인물", "차량건설기계": "기인물", "동력기계설비": "기인물",
    "압력용기탱크": "기인물", "화학물질가스": "기인물", "전기설비": "기인물",
    "운반물자재": "기인물", "수공구": "기인물", "환기설비": "기인물", "열원화기": "기인물",
    "가설구조물고소설비": "위험장소·구조", "건축물구조물": "위험장소·구조", "자연물환경": "위험장소·구조",
    "환경조건": "환경조건",
}

# ③ 환경조건 (사진에서 보이는 상태 — 조문 검증 완료)
ENV = [
    {"canonical": "어두운 조명/저조도", "category": "환경조건", "aliases": ["조도부족", "어두운 작업장", "그림자"],
     "articles": ["제8조", "제7조", "제21조"], "hazards": ["H02"], "guides": [],
     "vision_keywords": ["어두움", "조명 부족", "그림자", "전등 없음"], "in_current_ssot": False,
     "sources": ["법령"], "freq_note": "제8조 조도·제7조 채광및조명·제21조 통로조명"},
    {"canonical": "미끄러운/오염 바닥", "category": "환경조건", "aliases": ["물기", "기름", "젖은 바닥"],
     "articles": ["제3조", "제4조"], "hazards": ["H02"], "guides": ["M-59"],
     "vision_keywords": ["물기", "기름", "미끄럼", "젖은 바닥", "결빙"], "in_current_ssot": True,
     "sources": ["법령"], "freq_note": "전도(제3조)·청결(제4조)"},
    {"canonical": "정리불량/적치", "category": "환경조건", "aliases": ["어수선", "통로 막힘", "적치물"],
     "articles": ["제4조", "제22조"], "hazards": ["H02"], "guides": ["M-59"],
     "vision_keywords": ["적치물", "어수선", "통로 막힘", "자재 방치"], "in_current_ssot": True,
     "sources": ["법령"], "freq_note": "청결(제4조)·통로(제22조)"},
    {"canonical": "분진 비산", "category": "환경조건", "aliases": ["먼지", "비산", "흩날림"],
     "articles": ["제4조의2"], "hazards": ["H09"], "guides": [],
     "vision_keywords": ["먼지", "분진", "비산", "뿌연 작업장"], "in_current_ssot": True,
     "sources": ["법령"], "freq_note": "분진 흩날림(제4조의2)"},
    {"canonical": "소음", "category": "환경조건", "aliases": ["강렬한 소음", "소음작업"],
     "articles": ["제513조", "제514조"], "hazards": ["보건(소음)"], "guides": [],
     "vision_keywords": ["귀마개 필요 환경", "소음원 기계 밀집"], "in_current_ssot": False,
     "sources": ["법령"], "freq_note": "소음감소(제513조)·주지(제514조), 대부분 [B]"},
    {"canonical": "고온·고열 환경", "category": "환경조건", "aliases": ["폭염", "고열작업", "열기"],
     "articles": ["제559조", "제562조", "제254조"], "hazards": ["H11"], "guides": ["H-26"],
     "vision_keywords": ["열기", "용융물", "가열로", "폭염 옥외"], "in_current_ssot": True,
     "sources": ["법령"], "freq_note": "고열작업(제559조)·폭염(제562조)·화상(제254조)"},
    {"canonical": "환기불량/밀폐", "category": "환경조건", "aliases": ["환기 안됨", "후드 없음", "밀폐"],
     "articles": ["제72조", "제73조", "제620조", "제232조"], "hazards": ["H09", "H12"], "guides": ["W-26"],
     "vision_keywords": ["밀폐 공간", "환기설비 없음", "후드 미설치", "가스 정체"], "in_current_ssot": False,
     "sources": ["법령"], "freq_note": "후드(제72조)·덕트(제73조)·밀폐환기(제620조)·폭발예방환기(제232조)"},
]


def seed():
    mined = json.loads(MINED.read_text(encoding="utf-8"))
    pool = mined["pool"] if isinstance(mined, dict) else mined
    cues = list(pool) + ENV
    POOL.write_text(json.dumps({"cues": cues}, ensure_ascii=False, indent=1), encoding="utf-8")
    return cues


_obj = json.loads(POOL.read_text(encoding="utf-8")) if POOL.exists() else {"cues": seed()}
cues = _obj["cues"]
proc = _obj.get("procedure_articles", [])
niche = _obj.get("niche_articles", [])
for c in cues:
    c["cue_type"] = c.get("cue_type") or CUE_TYPE.get(c.get("category", ""), "기인물")


def fmt(c):
    arts = "·".join(c.get("articles", [])[:6]) or "—"
    flow = "·".join(c.get("flow_articles", [])[:6]) or "—"
    hz = ",".join(c.get("hazards", [])[:3]) or "—"
    kw = ", ".join(c.get("vision_keywords", [])[:3]) or "—"
    gd = ",".join(c.get("guides", [])[:2]) or "—"
    flag = "기존" if c.get("in_current_ssot") else "신규"
    return f"| {c['canonical']} | {arts} | {flow} | {hz} | {kw} | {gd} | {flag} |"


def section(title, ctype, desc):
    rows = sorted([c for c in cues if c["cue_type"] == ctype], key=lambda c: (c.get("category", ""), c["canonical"]))
    head = ("| 단서 | 진입 조문 | 조치 흐름(식별後·점검·표지) | 재해 | Vision 키워드 | Guide | SSOT |\n"
            "|---|---|---|---|---|---|---|\n")
    return f"## {title} — {len(rows)}종\n> {desc}\n\n{head}" + "\n".join(fmt(c) for c in rows) + "\n"


n_obj = sum(1 for c in cues if c["cue_type"] == "기인물")
n_place = sum(1 for c in cues if c["cue_type"] == "위험장소·구조")
n_env = sum(1 for c in cues if c["cue_type"] == "환경조건")
n_new = sum(1 for c in cues if not c.get("in_current_ssot"))

md = f"""# 관찰단서 → 조문 카탈로그 (E00)

> **[생성물]** `build_cue_catalog.py`가 `cue-pool.json`에서 생성. 수정은 **cue-pool.json 편집 후 재생성**(직접 편집 금지).
> **입구 = 사진에서 보이는 단서 → 조문.** 기인물만이 아니라 **3종**: ① 기인물(물건·설비) · ② 위험장소·구조 · ③ 환경조건.
> 단서 총 {len(cues)}종 (기인물 {n_obj} · 위험장소구조 {n_place} · 환경조건 {n_env}) · 현 SSOT 신규 커버 {n_new}종.
> **진입 조문**=사진에서 보이는 설비·방호상태(채점) · **조치 흐름**=식별 後 감독관에게 보여줄 점검·표지·정비(진입 아님).
> 실제 조문 제목·[A]/[B] 가시성은 `ssot_explorer.html`의 조문 점검표에서 검증.

{section("① 기인물 (물건·설비)", "기인물", "Vision이 가장 안정적으로 인식 + 법령(편2 장1)이 이 축으로 조직. 고정밀 경로.")}
{section("② 위험장소·구조", "위험장소·구조", "기인물이 약한 추락·붕괴·질식의 입구. 개구부·계단·지붕·비계·맨홀·굴착면 등.")}
{section("③ 환경조건", "환경조건", "물건이 아니라 '상태'. 어두운 조명·미끄러운 바닥·소음·고온·환기불량 등 → 조문.")}

## ④ 출력층 (진입 단서 아님 — 식별 後 자문)
> 사진 진입 단서가 아니라, 기인물·작업 식별 後 감독관에게 제시하는 행정/측정/특수 조문.

- **행정·측정·교육·자격 (PROCEDURE · Track B) {len(proc)}건**: {' · '.join(proc) or '—'}
- **Niche·특수공정 (업종/공정 게이트) {len(niche)}건**: {' · '.join(niche) or '—'}
"""
OUT.write_text(md, encoding="utf-8")
print(f"OK → {OUT.name}")
print(f"  cues={len(cues)} (기인물 {n_obj} / 위험장소구조 {n_place} / 환경조건 {n_env}) 신규={n_new}")
print(f"  source: {POOL.name}")
