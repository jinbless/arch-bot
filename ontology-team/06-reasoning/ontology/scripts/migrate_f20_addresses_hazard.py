#!/usr/bin/env python3
"""F20 (hard merge) 1회성 ABox 마이그레이션 — sr:addressesHazard → sr:addressesAccidentType.

배경: 두 속성은 F4c 이후 domain(sr:SafetyRequirement)·range(haz:AccidentType)가 동일한
동의어였고, 데이터가 두 술어로 분산돼 있었다(addressesHazard 626행/738트리플,
addressesAccidentType 284행; both 284 · addressesHazard_only 342). 객체는 양쪽 모두
canonical 사고유형(fine 코드 없음)이라 **union 흡수**가 안전하다("addressesHazard 버리기"는
ChemicalExposure/ElectricShock 등 6종을 342 SR에서 잃으므로 금지).

방식: **바이트 단위 토큰 치환**. rdflib parse→serialize 라운드트립은 law:fullText 등
여러 줄 리터럴 공백을 정규화해 ~1,052개 무관 트리플을 변형(단일변수 위반)하므로 쓰지 않는다.
`sr:addressesHazard` 토큰만 `sr:addressesAccidentType`로 치환하면:
  - turtle은 한 주어에 같은 술어가 반복돼도 합법 → 객체 집합 union,
  - RDF set 의미로 중복(321) 자동 제거,
  - 그 외 모든 바이트(리터럴·줄끝 LF)는 무손실 보존(단일변수 보장).
치환으로 생기는 일부 중복 술어 라인은 cosmetic이며, 생성기(export_owl, 수정됨)의 다음 전체
PG 재export 시 깔끔히 단일화된다.

멱등: 재실행해도 남은 토큰이 없으면 무변경.
검증: scripts/compare_graphs.py 로 -addressesHazard / +addressesAccidentType 외 변경 0 확인.
"""
from __future__ import annotations

import sys
from pathlib import Path

ONT = Path(__file__).resolve().parents[1]
TARGET = ONT / "kosha-instances.ttl"
OLD = b"sr:addressesHazard"
NEW = b"sr:addressesAccidentType"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    data = TARGET.read_bytes()
    n = data.count(OLD)
    if n == 0:
        print(f"{TARGET.name}: sr:addressesHazard 토큰 0 — 무변경(멱등).")
        return 0
    # 경계 안전: guide:addressesHazard는 'sr:' prefix가 아니므로 영향 없음(bytes 토큰에 'sr:' 포함).
    data = data.replace(OLD, NEW)
    TARGET.write_bytes(data)
    print(f"{TARGET.name}: sr:addressesHazard → sr:addressesAccidentType {n}곳 치환.")
    print("  (turtle 반복 술어 = union; RDF set 중복 제거. 리터럴/줄끝 무손실.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
