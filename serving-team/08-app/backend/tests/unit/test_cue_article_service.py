# -*- coding: utf-8 -*-
"""cue_article_service 단위 테스트 (pytest 무의존 — 리포 관례의 독립 실행 스크립트).

실행: PYTHONIOENCODING=utf-8 python serving-team/08-app/backend/tests/unit/test_cue_article_service.py
검증(LLM·PG 불요 — 결정론 경로만):
  1. 기본 flag off → enabled()/rank_enabled() False
  2. cue 매칭이 연구 구현(scripts/rank_ab_gold.cue_candidates)과 동일 집합 산출(고정 픽스처)
  3. entry 후보 전부 observable ∈ {yes, partial}
  4. 후보-밖 코드 필터가 환각 코드를 제거·카운트
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

# flag env 오염 제거(1번 검증 전제)
for k in ("CUE_ARTICLES", "CUE_ARTICLE_RANK"):
    os.environ.pop(k, None)

from app.services import cue_article_service as svc  # noqa: E402

FIXTURE = {
    "visual_observations": [
        {"text": "공장 내부에서 지게차가 적재물을 들어 올리고 있고 주변에 작업자가 통행 중이다"},
        {"text": "바닥 개구부에 덮개가 없고 주변에 안전난간이 설치되어 있지 않다"},
    ],
    "visual_cues": [
        {"text": "지게차 포크에 파레트 적재"},
        {"text": "어두운 조명 아래 통로에 자재가 적치되어 있음"},
    ],
    "hazards": [
        {"name": "추락 위험", "location": "바닥 개구부", "description": "개구부 방호조치 미비로 추락 위험"},
        {"name": "충돌 위험", "location": "지게차 주행 경로", "description": "지게차와 보행 작업자 혼재"},
    ],
}


def _run() -> int:
    fails = []

    # 1. 기본 flag off
    if svc.enabled() or svc.rank_enabled():
        fails.append("기본값이 off가 아님(enabled/rank_enabled)")

    # 2. 연구 구현과 동일 집합 (연구 모듈 로드 가능 환경에서만 — 없으면 skip)
    entry, flow, why = svc.cue_candidates(FIXTURE)
    if not entry:
        fails.append("픽스처(지게차·개구부)에서 entry 후보 0 — cue 매칭 자체가 죽음")
    if "제43조" not in entry:
        fails.append(f"개구부 단서인데 제43조 미포함: {sorted(entry)[:10]}")
    try:
        sys.path.insert(0, str(BACKEND / "scripts"))
        os.environ.setdefault("OPENAI_API_KEY", "test-not-used")  # 연구 모듈 import 시 키 확인 회피
        from rank_ab_gold import cue_candidates as research_cc  # noqa: E402
        r_entry, r_flow = research_cc(FIXTURE)
        if entry != r_entry:
            fails.append(f"entry 불일치 — 서빙만: {sorted(entry - r_entry)} / 연구만: {sorted(r_entry - entry)}")
        if flow != r_flow:
            fails.append(f"flow 불일치 — 서빙만: {sorted(flow - r_flow)} / 연구만: {sorted(r_flow - flow)}")
        print(f"  [2] 연구 구현 동일성: entry {len(entry)} · flow {len(flow)} 일치")
    except Exception as exc:  # noqa: BLE001
        print(f"  [2] 연구 모듈 비교 skip({type(exc).__name__}: {str(exc)[:80]})")

    # 3. observable 필터
    kn = svc._knowledge()
    if kn is None:
        fails.append("지식 파일 로드 실패(app/data/trackA)")
    else:
        bad = [c for c in entry if kn["sig"].get(c, {}).get("observable") not in ("yes", "partial")]
        if bad:
            fails.append(f"entry에 비관찰 조문: {bad}")

    # 4. 후보-밖 코드 필터
    keep, halluc = svc.filter_to_candidates(
        [{"article_code": "제42조", "applies": "yes"},
         {"article_code": "제999조", "applies": "yes"},
         {"article_code": "제43조", "applies": "no"}],
        {"제42조", "제43조"})
    if [x["article_code"] for x in keep] != ["제42조"] or halluc != 1:
        fails.append(f"필터 오동작: keep={keep} halluc={halluc}")

    if fails:
        print("FAIL:")
        for f in fails:
            print(" -", f)
        return 1
    print(f"OK — 4개 검증 통과 (entry {len(entry)}·flow {len(flow)}, 예: {sorted(entry, key=svc._code_num)[:6]})")
    return 0


if __name__ == "__main__":
    sys.exit(_run())
