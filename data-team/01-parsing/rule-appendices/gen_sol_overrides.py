#!/usr/bin/env python3
"""Sol 검토 승인분 → 조립기가 소비할 오버라이드 파일 생성.

입력: runtime-artifacts/sol-review/sol_review_final.json (판정 전문, 근거 인용 포함)
      + 사용자 승인 (2026-08-03): ①정책 2건 모두 뺀다 · ②패턴 전부 승인 · ③78건은 미포함
출력: rule-appendices/sol_review_overrides.json — build_flow_slice_all.py가 조립 마지막에 적용

★ 왜 SCOPE 손편집이 아니라 파일 하나인가: 승인된 것이 57개 배선 + 조문 154개 시점이라
  손으로 옮기면 옮기다 틀린다(좌표 실수 9번 났다). 판정 파일에서 기계적으로 뽑고,
  사람 승인 사실만 이 파일 상단에 기록한다.

⚠ ③(판정불가 78건)은 여기 없다 — human_decisions는 사용자 검수 대상으로 남는다.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "sol-review" / "sol_review_final.json"
OUT = Path(__file__).resolve().parent / "sol_review_overrides.json"

SLOTS = {"PLAN", "ASSIGN", "PRECHECK", "EXEC", "POST", "PERIODIC"}


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    ref_drops, slot_drops, slot_adds, pair_drops = [], [], [], []
    bad = []
    for p in d["proposals"]:
        if p["kind"] == "Q1_의무아님":
            ref_drops.append({"ref": p["ref"], "why": p["why"][:120]})
        elif p["kind"] == "Q1_칸불일치":
            if p["item"] not in SLOTS:
                bad.append(p)
                continue
            (slot_drops if p["action"] == "drop" else slot_adds).append(
                {"ref": p["ref"], "slot": p["item"], "evidence": p["quote"], "why": p["why"][:120]})
        elif p["kind"] == "Q2":
            if p["action"] != "drop":
                bad.append(p)
                continue
            pair_drops.append({"ref": p["ref"], "group": p["item"], "why": p["why"][:120]})
    if bad:
        print(f"⚠ 형식이 안 맞아 버린 제안 {len(bad)}건: {[ (b['ref'], b['item']) for b in bad[:5] ]}")

    OUT.write_text(json.dumps({
        "_note": "Sol 재판정 → Claude 판정 → 사용자 승인(2026-08-03: 정책 2건 뺀다 · 패턴 전부 승인). "
                 "build_flow_slice_all.py가 조립 마지막에 적용한다. 근거 전문은 sol-review/sol_review_final.json.",
        "_upstream_warning": "article_phases.json·law3_targets.py는 이 승인분을 모른다 — 흐름 정본은 "
                             "flow_slice_all.json이고 오버라이드는 여기서만 적용된다. 상류를 다시 만들면 "
                             "이 파일이 계속 얹힌다(멱등).",
        "approved_by": "사용자 (2026-08-03)",
        "ref_drops": ref_drops, "slot_drops": slot_drops,
        "slot_adds": slot_adds, "pair_drops": pair_drops,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ref_drops {len(ref_drops)} · slot_drops {len(slot_drops)} · "
          f"slot_adds {len(slot_adds)} · pair_drops {len(pair_drops)}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
