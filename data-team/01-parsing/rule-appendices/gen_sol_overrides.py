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


def load_human_csv():
    """사람 검수 CSV(뷰어 내보내기) → 항목 단위 연산.

    ★ Sol 승인분과 달리 **항목 단위 정확 일치**로 적용한다 — (그룹, 칸, ref, text) 네 값이
      전부 맞아야 한다. 사람이 클릭한 것은 그 자리의 그 항목이지 조문 일반이 아니고,
      별표·가이드 항목(조문 ref가 아님)도 판정 대상이었기 때문이다.
    verdict: ok=기록만 / off=그 자리에서 제거 / move=correct_phase로 이동 / vague=기록만
    """
    import csv
    p = SRC.parent / "flow_review.csv"
    if not p.exists():
        return [], 0
    ops, n_ok = [], 0
    for r in csv.DictReader(p.open(encoding="utf-8-sig")):
        v = (r.get("verdict") or "").strip()
        if v == "off":
            ops.append({"group_no": r["no"], "phase": r["phase"], "ref": r["ref"],
                        "text": r["text"], "op": "drop"})
        elif v == "move" and (r.get("correct_phase") or "").strip() in SLOTS:
            ops.append({"group_no": r["no"], "phase": r["phase"], "ref": r["ref"],
                        "text": r["text"], "op": "move", "to": r["correct_phase"].strip()})
        elif v == "ok":
            n_ok += 1
    return ops, n_ok


# 크레인 4분할(2026-08-06 사용자 승인) 후 옛 그룹명을 참조하는 판정을 서브타입으로 부채질한다.
# 판정 당시 화면의 '양중기 > 크레인'은 세 서브타입 전체를 뜻했다 — 안 펼치면 판정이 증발한다.
GROUP_SPLIT = {"양중기 > 크레인": ["양중기 > 타워크레인", "양중기 > 천장·갠트리 등 주행형 크레인",
                                   "양중기 > 지브 크레인"],
               # 천공기 분리(2026-08-07): 옛 묶음을 참조하는 판정은 **캡 차량 쪽만** 받는다.
               # 판정 근거("밀폐 캡 차량")가 천공기에는 성립하지 않기 때문이다 —
               # 천공기 몫은 medium_resolutions.json이 명시적으로 정한다.
               "건설기계 등 > 차량계 건설기계 등": ["건설기계 등 > 차량계 건설기계"]}


def _fan(group: str) -> list[str]:
    return GROUP_SPLIT.get(group, [group])


# 게이트 감사(Sol, 2026-08-07)가 뒤집은 high 판정 — 통상 사용에서 성립하는 구체 상황이 제시됐다.
#   프레스·전단기 제95: 로터리 시어·슬리터형 전단기(회전날)가 실재 — 사용자가 제94를 남긴 것과 같은 논리
#   항타기 제90: PHC 말뚝머리 반복 타격 시 콘크리트 파쇄편 비산은 항타의 통상 위험
#   차량계 건설기계 제90: 노면파쇄기·로드밀링기는 회전 커터로 포장을 절삭한다 — '캡 차량' 전제 오류
GATE_REJECTED_HIGH = {("제95조", "프레스 및 전단기"),
                      ("제90조", "건설기계 등 > 항타기 및 항발기"),
                      ("제90조", "건설기계 등 > 차량계 건설기계")}


def load_practical():
    """실질 무관 후보(implausible_candidates.json) 중 **high만** — 사용자 일괄 승인(2026-08-06).
    medium 25건은 보류(상황에 따라 갈림 — 차량계 건설기계 묶음의 천공기 등)."""
    p = SRC.parent / "implausible_candidates.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for c in d.get("candidates", []):
        if c.get("confidence") != "high":
            continue
        for g in _fan(c["group"]):
            if (c["ref"], g) in GATE_REJECTED_HIGH:
                continue
            out.append({"ref": c["ref"], "group": g, "why": c["why"][:120]})
    # medium 판정(2026-08-07 위임): adopt만 드롭이 된다. keep은 기록으로만 남는다.
    mr = SRC.parent / "medium_resolutions.json"
    if mr.exists():
        for r in json.loads(mr.read_text(encoding="utf-8")).get("resolutions", []):
            if r["verdict"] == "adopt":
                out.append({"ref": r["ref"], "group": r["group"],
                            "why": "[medium 채택] " + r["why"][:100]})
    return out


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
            for g in _fan(p["item"]):
                pair_drops.append({"ref": p["ref"], "group": g, "why": p["why"][:120]})
    if bad:
        print(f"⚠ 형식이 안 맞아 버린 제안 {len(bad)}건: {[ (b['ref'], b['item']) for b in bad[:5] ]}")

    human_ops, n_ok = load_human_csv()
    practical = load_practical()

    OUT.write_text(json.dumps({
        "_note": "Sol 재판정 → Claude 판정 → 사용자 승인(2026-08-03: 정책 2건 뺀다 · 패턴 전부 승인) "
                 "+ 사람 검수 CSV(2026-08-06, 174건 판정). build_flow_slice_all.py가 조립 마지막에 적용한다. "
                 "근거 전문은 sol-review/. **human_item_ops가 최우선**(사람 검수는 모든 판정을 덮어쓴다).",
        "_upstream_warning": "article_phases.json·law3_targets.py는 이 승인분을 모른다 — 흐름 정본은 "
                             "flow_slice_all.json이고 오버라이드는 여기서만 적용된다. 상류를 다시 만들면 "
                             "이 파일이 계속 얹힌다(멱등).",
        "approved_by": "사용자 (2026-08-03 승인 + 2026-08-06 검수 CSV)",
        "ref_drops": ref_drops, "slot_drops": slot_drops,
        "slot_adds": slot_adds, "pair_drops": pair_drops,
        "practical_pair_drops": practical,
        "human_item_ops": human_ops, "human_ok_count": n_ok,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ref_drops {len(ref_drops)} · slot_drops {len(slot_drops)} · "
          f"slot_adds {len(slot_adds)} · pair_drops {len(pair_drops)} · "
          f"practical {len(practical)} · human_item_ops {len(human_ops)} (ok 기록 {n_ok})")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
