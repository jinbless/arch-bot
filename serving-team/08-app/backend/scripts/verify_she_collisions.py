#!/usr/bin/env python3
"""SHE 시그니처 충돌 게이트 — CAT-3 (F20). `make verify-she-collisions`.

서빙 SHE(approved_auto/approved_manual)를 서빙 가시 3축 시그니처
(work_context, hazardous_agent, accident_type)로 그룹핑해 충돌(동일 시그니처
≥2 패턴)을 측정한다. 시그니처가 같은 패턴들은 matcher가 8차원 의미가 아닌
점수 동률 타이브레이크로만 구분하므로, 충돌이 늘수록 "매칭된 패턴의 정체"가
휴리스틱에 좌우된다(F20: 현재 서빙 1,675건 중 ~55%가 비유일).

운영 의미론:
- 기존 충돌(~200그룹)은 **동결 기준선**(she_collision_baseline.json, 커밋됨) —
  소급 차단하지 않는다(기존 카탈로그 큐레이션은 별도 작업).
- **신규 증가만 hard fail**: 새 충돌그룹 생성 또는 기존 그룹 크기 증가 → exit 1.
  즉 "카탈로그가 커질수록 변별력이 조용히 나빠지는" 방향만 차단.
- 의도적 중복은 supersede로 해소: she_catalog.superseded_by(FK) 지정 +
  status 강등(pending_review) → 서빙 집계에서 빠져 게이트 통과.

사용:
  python scripts/verify_she_collisions.py            # 검증 (기본)
  python scripts/verify_she_collisions.py --capture  # 기준선 재캡처(의도적 채택 시만)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def _find_repo_root() -> Path:
    for a in Path(__file__).resolve().parents:
        if (a / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return a
    raise RuntimeError("repo root not found")


REPO_ROOT = _find_repo_root()
BASELINE = (REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
            / "she_collision_baseline.json")

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


def fetch_signature_groups() -> dict[str, list[str]]:
    """서빙 SHE의 시그니처 → she_id 목록 (superseded 제외는 status 강등으로 처리됨)."""
    session = SessionLocal()
    try:
        rows = session.execute(text("""
            SELECT she_id,
                   COALESCE(features->>'work_context', '')    AS wc,
                   COALESCE(features->>'hazardous_agent', '') AS ha,
                   COALESCE(features->>'accident_type', '')   AS at
            FROM she_catalog
            WHERE status IN ('approved_auto', 'approved_manual')
            ORDER BY she_id
        """)).all()
    finally:
        session.close()
    groups: dict[str, list[str]] = {}
    for she_id, wc, ha, at in rows:
        groups.setdefault(f"{wc}|{ha}|{at}", []).append(she_id)
    return groups


def summarize(groups: dict[str, list[str]]) -> dict:
    collisions = {sig: ids for sig, ids in groups.items() if len(ids) > 1}
    return {
        "serving_total": sum(len(v) for v in groups.values()),
        "distinct_signatures": len(groups),
        "collision_groups": len(collisions),
        "colliding_patterns": sum(len(v) for v in collisions.values()),
        "max_group_size": max((len(v) for v in collisions.values()), default=0),
        # 기준선 비교 단위: 충돌 시그니처 → 그룹 크기
        "collision_sizes": {sig: len(ids) for sig, ids in sorted(collisions.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true",
                        help="현재 상태를 동결 기준선으로 저장(의도적 채택 시만)")
    args = parser.parse_args()

    current = summarize(fetch_signature_groups())

    if args.capture:
        BASELINE.write_text(json.dumps(current, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"Captured collision baseline: {BASELINE.name}")
        print(f"  serving {current['serving_total']} / 충돌그룹 {current['collision_groups']} "
              f"/ 충돌패턴 {current['colliding_patterns']} / 최대그룹 {current['max_group_size']}")
        return 0

    if not BASELINE.exists():
        print(f"기준선 부재: {BASELINE} — 먼저 --capture 실행", file=sys.stderr)
        return 2

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_sizes: dict[str, int] = base.get("collision_sizes", {})
    cur_sizes: dict[str, int] = current["collision_sizes"]

    new_groups = sorted(set(cur_sizes) - set(base_sizes))
    grown = sorted((sig, base_sizes[sig], n) for sig, n in cur_sizes.items()
                   if sig in base_sizes and n > base_sizes[sig])

    print(f"serving {current['serving_total']} / 충돌그룹 {current['collision_groups']} "
          f"(기준선 {base.get('collision_groups')}) / 충돌패턴 {current['colliding_patterns']} "
          f"(기준선 {base.get('colliding_patterns')}) / 최대그룹 {current['max_group_size']}")

    if new_groups or grown:
        print("\nverify-she-collisions FAIL — 시그니처 충돌 신규 증가:")
        for sig in new_groups[:10]:
            print(f"  ✗ 신규 충돌그룹 {sig} (크기 {cur_sizes[sig]})")
        for sig, b, c in grown[:10]:
            print(f"  ✗ 그룹 확대 {sig}: {b} → {c}")
        print("\n해소: (a) 신규 패턴의 8차원 차별화(ppe/env/activity를 OTHER가 아닌 "
              "구체값으로), (b) 기존 패턴 supersede(superseded_by 지정 + status 강등), "
              "(c) 의도적 채택이면 --capture로 기준선 갱신(사유 커밋 메시지 필수).")
        return 1

    print("verify-she-collisions PASS — 기준선 대비 신규 충돌 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
