#!/usr/bin/env python3
"""별표 좌표(편·장·절·관) ↔ 우리 기인물 인덱스/조문 section 조인 커버리지.

별표 3(작업시작 전 점검)·별표 2(관리감독자 직무)는 각 행에 `제2편제1장제10절제2관` 같은
좌표를 갖는다. 우리 `gimulmul_index` 그룹키는 `절10 차량계 하역운반기계등 > 관2 지게차`,
`article_signatures.section`은 `편2 ... > 절10 ... > 관2 지게차` 형식이라 좌표만 정규화하면 조인된다.

이 스크립트는 "법이 작업 전 점검을 요구하는 작업 종류 중 우리가 인식·연결할 수 있는 비율"을 낸다.
LLM 호출 0.

사용: python data-team/01-parsing/rule-appendices/join_coverage.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARSED = Path(__file__).resolve().parent / "parsed"
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
SIGS = ART / "article_signatures.jsonl"
GIM = ART / "gimulmul_index.json"
CUE = ROOT / "docs" / "knowledge" / "감독관-판단기준" / "cue-pool.json"

COORD = re.compile(r"제(\d+)편|제(\d+)장|제(\d+)절|제(\d+)관")


def parse_coord(s: str) -> tuple:
    """'제2편제1장제10절제2관' → (2,1,10,2). 없는 층은 None."""
    p = j = jeol = gwan = None
    for m in COORD.finditer(s or ""):
        if m.group(1):
            p = int(m.group(1))
        elif m.group(2):
            j = int(m.group(2))
        elif m.group(3):
            jeol = int(m.group(3))
        elif m.group(4):
            gwan = int(m.group(4))
    return (p, j, jeol, gwan)


def sig_coord(section: str) -> tuple:
    """article_signatures.section '편2 ... > 절10 ... > 관2 지게차' → (2,None,10,2)."""
    p = j = jeol = gwan = None
    for tok in (section or "").split(">"):
        tok = tok.strip()
        m = re.match(r"(편|장|절|관)(\d+)", tok)
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


def main() -> None:
    sigs = [json.loads(l) for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()]
    gim = json.loads(GIM.read_text(encoding="utf-8"))["groups"]
    cues = json.loads(CUE.read_text(encoding="utf-8"))["cues"]

    # 조문 색인 — **편·장까지 포함한 완전 좌표**로 키를 만든다.
    # (절 번호만으로 키를 잡으면 '제2편제1장제3절 프레스'가 다른 편의 절3까지 끌어와 커버리지가 부풀려진다)
    by_full: dict[tuple, list] = {}
    by_pj: dict[tuple, list] = {}      # (편,장,절) — 관 없는 별표 좌표용
    for s in sigs:
        p, j, jeol, gwan = sig_coord(s.get("section", ""))
        by_full.setdefault((p, j, jeol, gwan), []).append(s)
        by_pj.setdefault((p, j, jeol), []).append(s)

    # 기인물 그룹의 완전 좌표 — 그룹키엔 편·장이 없으므로 소속 조문에서 역산한다
    gim_full, gim_pj = {}, {}
    sig_by_code = {s["article_code"]: s for s in sigs}
    for k, g in gim.items():
        codes = [a["code"] for a in g.get("articles", [])]
        coords = {sig_coord(sig_by_code[c]["section"]) for c in codes if c in sig_by_code}
        for p, j, jeol, gwan in coords:
            gim_full.setdefault((p, j, jeol, gwan), k)
            gim_pj.setdefault((p, j, jeol), k)

    # cue-pool 기인물 명칭(느슨한 이름 매칭용)
    cue_names = {}
    for c in cues:
        for n in [c["canonical"]] + (c.get("aliases") or []):
            cue_names[re.split(r"[(/·]", n)[0].strip()] = c["canonical"]

    for fname, label in (("appendix-03.json", "별표 3 작업시작 전 점검"),
                         ("appendix-02.json", "별표 2 관리감독자 직무")):
        o = json.loads((PARSED / fname).read_text(encoding="utf-8"))
        rows = o["rows"]
        print(f"\n=== {label} — {len(rows)}개 작업종류 ===")
        hit_art = hit_gim = hit_cue = 0
        misses = []
        for r in rows:
            p, j, jeol, gwan = parse_coord(r.get("section_ref", ""))
            if gwan is not None:
                arts = by_full.get((p, j, jeol, gwan), [])
                g = gim_full.get((p, j, jeol, gwan))
            else:
                arts = by_pj.get((p, j, jeol), [])
                g = gim_pj.get((p, j, jeol))
            subj = r["subject"]
            # 이름 매칭은 **긴 후보 우선** — 짧은 별칭이 부분문자열로 먼저 걸려 오매칭되는 것 방지
            cue = next((v for k, v in sorted(cue_names.items(), key=lambda kv: -len(kv[0]))
                        if len(k) >= 3 and k in subj), None)
            if arts:
                hit_art += 1
            if g:
                hit_gim += 1
            if cue:
                hit_cue += 1
            if not (g or cue):
                misses.append(f"{r['no']}. {subj[:34]}")
            mark = "O" if (g or cue) else "X"
            print(f" {mark} [{r['no']:>4}] {subj[:30]:32} 좌표{str((jeol,gwan)):9} "
                  f"조문{len(arts):3d} 기인물그룹{'O' if g else '-'} cue={cue or '-'}")
        n = len(rows)
        print(f"  → 조문 연결 {hit_art}/{n} ({hit_art/n:.0%}) · "
              f"기인물그룹 {hit_gim}/{n} ({hit_gim/n:.0%}) · cue-pool {hit_cue}/{n} ({hit_cue/n:.0%})")
        if misses:
            print("  미연결:", " | ".join(misses))


if __name__ == "__main__":
    main()
