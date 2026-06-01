#!/usr/bin/env python3
"""Phase 2 검증 — GPT 위험요소 rich text → hybrid recall(SR/NS/CI) 적합성 확인.

실행: ./.venv/bin/python scripts/test_hybrid_search.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from app.services.hybrid_search import hybrid_search, get_index, COLLECTIONS  # noqa: E402

# 라이브 지게차 GPT 위험요소(rich text) 그대로
CASES = [
    ("지게차 충돌", "지게차가 운행 중이며 주변에 작업자가 도보로 이동하고 있습니다. 지게차와 작업자 간 충돌 및 협착 위험이 높음. 보행로와 물류 차량 경로가 분리되어 있지 않음."),
    ("프레스 끼임", "대형 동력 프레스기 금형 사이에 신체가 진입하여 협착·절단될 위험. 광전자식 방호장치·양수조작 식별 불가."),
    ("주방 화재", "음식점 주방 가스레인지에서 가스 누출·점화원으로 화재·폭발 위험. 협소공간 기름 바닥."),
]

print("collection counts:", {k: get_index(c).count() for k, c in COLLECTIONS.items()})
for label, q in CASES:
    print(f"\n=== [{label}] {q[:46]}…")
    for kind in ("sr", "ns"):
        rows = hybrid_search(kind, q, 5)
        if not rows:
            continue
        print(f"  -- {kind} top5:")
        for r in rows:
            title = (r.get("meta") or {}).get("title") or r["doc"][:50]
            print(f"     {r['id']:18s} rrf={r['rrf']} v={r.get('vscore')} b={r.get('bscore')}  {title[:52]}")
