#!/usr/bin/env python3
"""WS-DEEP-1 — 이중경로 합의/불일치 집계기.

DEEP-1 merge가 `analysis_log.jsonl`에 emit한 `path_agreement`(guides·SR별
she_only/hazard_direct_only/both)를 코퍼스 전체로 aggregate해 두 경로
(SHE/facet · hazard-direct)의 **구조적 합의율(agreement_rate)** 을 산출한다.

설계 메모:
  - 별도 pipeline 재실행 불요 — replay(hazards 주입, EVAL-1)가 served 경로에서 이미
    emit한 path_agreement 엔트리를 읽어 집계(같은 yardstick·중복비용 0).
  - per-path independent_recall(경로별 정답 대비 recall)은 ground-truth가 있어야 산출 →
    **WS-EVAL-2 gold set 의존**. gold 부재 시 구조적 분포만 산출(observe-only).
    8-photo set은 overlap GT 부재(plan)라 recall 산출에 사용 금지.
  - 측정·관측 전용. scoring/게이트 아님(FN-방향 게이트는 regression_gate의 procedures 비감소).

사용:
  python scripts/replay_dualpath_agreement.py [--log <analysis_log.jsonl>] [--json] [--since-tail N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _find_log() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        d = ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
        if d.is_dir():
            return d / "analysis_log.jsonl"
    raise RuntimeError("analysis_log.jsonl 경로를 찾을 수 없음")


def _agg_axis(rows: list[dict], axis: str) -> dict:
    keys = ("she_only", "hazard_direct_only", "both")
    out = {k: 0 for k in keys}
    n = 0
    for pa in rows:
        sub = pa.get(axis) or {}
        if not any(k in sub for k in keys):
            continue
        n += 1
        for k in keys:
            out[k] += int(sub.get(k, 0) or 0)
    total_units = sum(out.values())
    out["entries"] = n
    out["total_units"] = total_units
    # agreement_rate = both / (전체 단위) — 두 경로가 같은 guide/SR를 합의한 비율(구조적).
    out["agreement_rate"] = round(out["both"] / total_units, 4) if total_units else 0.0
    # disagreement_rate = (she_only + hazard_direct_only) / total
    out["disagreement_rate"] = (
        round((out["she_only"] + out["hazard_direct_only"]) / total_units, 4) if total_units else 0.0
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", type=Path, default=None, help="analysis_log.jsonl 경로(기본 자동탐색)")
    ap.add_argument("--json", action="store_true", help="JSON으로 stdout 출력")
    ap.add_argument("--since-tail", type=int, default=0,
                    help="마지막 N줄만 집계(0=전체). 최근 replay만 보고 싶을 때.")
    args = ap.parse_args()

    log_path = args.log or _find_log()
    if not log_path.exists():
        print(f"analysis_log 없음: {log_path}", file=sys.stderr)
        return 2

    lines = log_path.read_text(encoding="utf-8").splitlines()
    if args.since_tail > 0:
        lines = lines[-args.since_tail:]

    pa_rows: list[dict] = []
    parsed = 0
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            entry = json.loads(ln)
        except Exception:
            continue
        parsed += 1
        pa = entry.get("path_agreement")
        if pa:
            pa_rows.append(pa)

    guides = _agg_axis(pa_rows, "guides")
    srs = _agg_axis(pa_rows, "sr")
    result = {
        "log_path": str(log_path),
        "lines_scanned": len(lines),
        "entries_parsed": parsed,
        "path_agreement_entries": len(pa_rows),
        "guides": guides,
        "sr": srs,
        "independent_recall": None,
        "note": (
            "구조적 합의율(observe-only). per-path independent_recall은 WS-EVAL-2 gold set 의존 → "
            "gold 안정화 후 산출. path_agreement_entries==0이면 DEEP-1 merge 미발동(hazards 미주입 코퍼스)."
        ),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"log            : {log_path}")
        print(f"lines scanned  : {len(lines)} (parsed {parsed})")
        print(f"path_agreement : {len(pa_rows)} entries")
        print()
        for axis, agg in (("guides", guides), ("sr", srs)):
            print(f"[{axis}] she_only={agg['she_only']} hazard_direct_only={agg['hazard_direct_only']} "
                  f"both={agg['both']} (units={agg['total_units']})")
            print(f"    agreement_rate={agg['agreement_rate']:.4f}  "
                  f"disagreement_rate={agg['disagreement_rate']:.4f}")
        print()
        print("  · agreement_rate = both / 전체단위 (두 경로 구조적 합의). observe-only.")
        print("  · independent_recall = WS-EVAL-2 gold set 의존(현재 미산출).")
        if not pa_rows:
            print("  ⚠ path_agreement 엔트리 0 — DEEP-1 merge 미발동(hazards 주입 replay 후 재실행 필요).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
