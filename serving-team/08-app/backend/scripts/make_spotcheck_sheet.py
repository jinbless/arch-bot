#!/usr/bin/env python3
"""USE 2 보조 — 텍스트 semi-gold 사람 검수 시트 생성(LLM 무호출).

text_semigold.jsonl + article_signatures.jsonl → 검수 친화 CSV.
한 행 = (사례 × gold 조문). 사람은 '감소대책'과 그 조의 '요구조치'를 대조해
CONFIRM에 ok / X(무관) / 정정조문코드 표기. ok 비율 = LLM-gold 신뢰도.

사용: .venv/bin/python scripts/make_spotcheck_sheet.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
SEMI = ART / "text_semigold.jsonl"
SIGS = ART / "article_signatures.jsonl"
OUT = ART / "text_semigold_spotcheck.csv"


def main():
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
    rows = [json.loads(l) for l in SEMI.read_text(encoding="utf-8").splitlines() if l.strip()]
    scored = [r for r in rows if r.get("gold")]

    # 기존 검수 입력 보존(재생성 시 CONFIRM/사유 carry-over)
    CONF, RSN = "CONFIRM(ok/X/정정조문)", "사유(X·정정 이유, 선택)"
    prev = {}
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8-sig")):
            cc = next((c for c in r if c.startswith("CONFIRM")), None)
            rc = next((c for c in r if c.startswith("사유")), None)
            prev[(r.get("id"), r.get("gold_조문"))] = (r.get(cc, "") if cc else "", r.get(rc, "") if rc else "")

    out = []
    for r in scored:
        pred3 = r.get("pred", [])[:3]
        for gc in r["gold"]:
            s = sig.get(gc, {})
            pc, pr = prev.get((r["id"], gc), ("", ""))
            out.append({
                "id": r["id"], "domain": r["domain"], "기인물": r["gim"],
                "감소대책": " / ".join(r["measures"]),
                "gold_조문": gc, "gold_제목": s.get("title", ""),
                "gold_요구조치": ", ".join(s.get("required_measures") or []),
                "matcher_top3": " ".join(pred3),
                "gold이_top3에": "Y" if gc in pred3 else "",
                "재해개요": (r.get("situ") or ""),
                CONF: pc,
                RSN: pr,
            })
    # 기인물·domain 정렬(유사 사례 묶음 → 빠른 검수)
    out.sort(key=lambda x: (x["기인물"], x["domain"]))

    cols = ["id", "domain", "기인물", "감소대책", "gold_조문", "gold_제목", "gold_요구조치",
            "matcher_top3", "gold이_top3에", "재해개요", CONF, RSN]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"검수 행 {len(out)} (사례 {len(scored)}) → {OUT.name}")
    print("CONFIRM 열: ok(감소대책↔요구조치 대응 맞음) / X(무관) / 정정조문코드(예: 제43조)")


if __name__ == "__main__":
    main()
