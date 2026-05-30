#!/usr/bin/env python3
"""Layer 4.7 (Continual) — pending/UNKNOWN open-class 코드 승격 후보 추적 (읽기전용).

근본: canonical SSOT는 미분류 코드를 pending bucket(UNCLASSIFIED/UNKNOWN_AGENT/
UNKNOWN_CONTEXT)으로 흡수(open-class, 억지 배정 금지). audit_code_consistency.py --gate가
이를 WARN으로 적발하지만 *빈도/추세*는 추적하지 못한다. 본 태스크가 live PG 빈도로
pending 코드를 랭킹 + tier 분류해 승격 후보 queue를 산출한다.

승격 자체는 사람/후속 LLM 클러스터링의 결정(본 스크립트는 mutate 금지):
  - PROMOTE: 정본 신규 코드 신설 또는 기존 canonical 매핑 → build_canonical_vocabulary 룰 보강.
  - WATCH: 빈도 누적 관찰.
  - NOISE: 1~2회성, 무시 가능.

사용:
  PYTHONIOENCODING=utf-8 python continual_pending_promotion.py
  ... --promote-threshold 8 --watch-threshold 3
출력: runtime-artifacts/continual_pending_promotion.json (gitignored, 재생성 가능) + stdout 표.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parents[3]
ART = REPO / "data-team/05-enrichment/runtime-artifacts"
OUT = ART / "continual_pending_promotion.json"
PG = "dbname=kosha user=kosha password=1229 host=localhost"

sys.path.insert(0, str(REPO / "shared" / "reference"))
import canonical_vocab as cv  # noqa: E402

AXES = ["accident_type", "hazardous_agent", "work_context"]
COL = {"accident_type": "accident_types", "hazardous_agent": "hazardous_agents", "work_context": "work_contexts"}


def pg_freq(cur) -> dict[str, dict[str, dict[str, int]]]:
    """axis → code → {sr, ci, guide} 빈도."""
    freq: dict[str, dict[str, dict[str, int]]] = {a: {} for a in AXES}

    def _bump(a, code, surface, n):
        freq[a].setdefault(code, {"sr": 0, "ci": 0, "guide": 0})
        freq[a][code][surface] += int(n)

    for a in AXES:
        for surface, table in (("sr", "safety_requirements"), ("ci", "checklist_items")):
            cur.execute(
                f"SELECT v, count(*) FROM {table}, jsonb_array_elements_text({COL[a]}) v GROUP BY v"
            )
            for code, n in cur.fetchall():
                _bump(a, code, surface, n)
        cur.execute(
            "SELECT feature_code, count(*) FROM guide_entity_feature_candidates "
            "WHERE entity_type='GUIDE' AND axis=%s GROUP BY feature_code",
            (a,),
        )
        for code, n in cur.fetchall():
            _bump(a, code, "guide", n)
    return freq


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promote-threshold", type=int, default=8, help="이 빈도 이상이면 PROMOTE 후보")
    ap.add_argument("--watch-threshold", type=int, default=3, help="이 빈도 이상이면 WATCH")
    args = ap.parse_args()

    conn = psycopg2.connect(PG)
    cur = conn.cursor()
    freq = pg_freq(cur)
    conn.close()

    out_axes: dict[str, dict] = {}
    total_promote = total_watch = total_noise = 0
    for a in AXES:
        pending = cv.pending_bucket(a)
        canon = cv.canonical_set(a)
        meta = cv.meta_set(a)
        cands = []
        for code, by in freq[a].items():
            if code in canon or code in meta or code == pending:
                continue
            a2, c2 = cv.to_canonical(a, code)
            # 자기 축 pending으로 떨어진 것만 open-class 후보 (교차축 해소는 제외).
            if not (a2 == a and c2 == pending):
                continue
            tot = by["sr"] + by["ci"] + by["guide"]
            if tot <= 0:
                continue
            tier = ("PROMOTE" if tot >= args.promote_threshold
                    else "WATCH" if tot >= args.watch_threshold else "NOISE")
            cands.append({"code": code, "freq": tot, "by_surface": by, "tier": tier})
        cands.sort(key=lambda x: -x["freq"])
        for c in cands:
            total_promote += c["tier"] == "PROMOTE"
            total_watch += c["tier"] == "WATCH"
            total_noise += c["tier"] == "NOISE"
        out_axes[a] = {"pending_bucket": pending, "candidates": cands}

    artifact = {
        "task": "Layer 4.7 Continual — pending open-class promotion queue",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {"promote": args.promote_threshold, "watch": args.watch_threshold},
        "source": "live PG (safety_requirements + checklist_items + guide_entity_feature_candidates)",
        "axes": out_axes,
        "summary": {"promote": total_promote, "watch": total_watch, "noise": total_noise},
    }
    ART.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # stdout 표
    print("=== Layer 4.7 Continual — pending 승격 후보 (live PG 빈도) ===")
    print(f"thresholds: PROMOTE>={args.promote_threshold}  WATCH>={args.watch_threshold}")
    for a in AXES:
        cands = out_axes[a]["candidates"]
        print(f"\n[{a}] pending={out_axes[a]['pending_bucket']}  후보 {len(cands)}개")
        for c in cands:
            b = c["by_surface"]
            print(f"  {c['tier']:8} {c['code']:30} freq={c['freq']:3}  "
                  f"(sr={b['sr']} ci={b['ci']} guide={b['guide']})")
        if not cands:
            print("  (없음)")
    s = artifact["summary"]
    print(f"\n요약: PROMOTE={s['promote']}  WATCH={s['watch']}  NOISE={s['noise']}")
    print(f"queue: {OUT.relative_to(REPO)}")
    print("\n승격 결정 시: build_canonical_vocabulary.py 룰 보강(신규 canonical/매핑) → 재생성 → make verify-codes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
