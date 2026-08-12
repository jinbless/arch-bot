"""'지금 당장' 정렬 스냅샷 — statute_actions 순위 규칙의 회귀 가드 (2026-08-12 Track B).

DB는 Fake(고정 SR 행)라 LLM 0·PG 0으로 돈다. 흐름 데이터는 repo의 app/data/trackA를 그대로 쓴다 —
데이터 재생성(B-B)으로 화기 그룹 항목이 바뀌면 이 스냅샷도 의도적으로 같이 갱신해야 한다.

고정하는 규칙:
  1. 화재 사진 코드(FIRE_AND_EXPLOSION→canonical EXPLOSION)가 SR legacy 별칭
     (FIRE_EXPLOSION→{EXPLOSION,FIRE_INJURY})을 통해 히트한다 — 별칭 없으면 영구 공집합(prod 5222).
  2. matched(AI 제안 대조) 부스트는 순위만 바꾸고 urgency는 못 바꾼다.
  3. 별표 항목(ref '제N조제M항 …')이 모집단에 들어오되 SR join 없이 hazard_hit/actable=False.
  4. 지게차×COLLISION 기존 동작 불변(버그 9호 수정 후 기준).
"""
from __future__ import annotations

import pytest

from app.services import flow_service

FIRE_GK = "절2 화기 등의 관리"
FORKLIFT_GK = "절10 차량계 하역운반기계등 > 관2 지게차"

# kosha-pg 실측값 사본(2026-08-12) — (article_code, sr_id, title, canonical, legacy, requirement_type)
FIRE_SRS = [
    ("제239조", "SR-FIRE_EXPLOSION-015", "폭발·화재 위험장소에서 화기·발화원 사용 금지", [], ["FIRE_EXPLOSION"], "PROCEDURAL"),
    ("제240조", "SR-FIRE_EXPLOSION-016", "위험물 잔류 배관·용기의 화재위험작업 전 제거조치", [], ["FIRE_EXPLOSION"], "PROCEDURAL"),
    ("제241조의2", "SR-FIRE_EXPLOSION-017", "용접·용단 작업장소 화재감시자 배치 및 장비 지급", [], ["FIRE_EXPLOSION"], "MANAGEMENT_SYSTEM"),
    ("제242조", "SR-FIRE_EXPLOSION-018", "화재·폭발 위험장소 화기 사용 금지", [], ["FIRE_EXPLOSION"], "PROCEDURAL"),
    ("제243조", "SR-FIRE_EXPLOSION-019", "폭발·화재 위험 장소 소화설비 설치 및 적합성 확보", [], ["FIRE_EXPLOSION"], "EMERGENCY_RESPONSE"),
    ("제244조", "SR-FIRE_EXPLOSION-020", "방화조치 준수", [], ["FIRE_EXPLOSION"], "PHYSICAL_PROTECTION"),
    ("제245조", "SR-FIRE_EXPLOSION-021", "화기사용 장소의 화재예방 설비", [], ["FIRE_EXPLOSION"], "PHYSICAL_PROTECTION"),
    ("제246조", "SR-FIRE_EXPLOSION-022", "소각장 화재방지", [], ["FIRE_EXPLOSION"], "PHYSICAL_PROTECTION"),
]

FORKLIFT_SRS = [
    ("제89조", "SR-FK-001", "기계 운전 시작 전 안전확인 및 신호조치", ["CAUGHT_IN"], ["CAUGHT_IN"], "PROCEDURAL"),
    ("제171조", "SR-FK-171", "차량계 하역운반기계등 전도·굴러떨어짐 방지 조치", ["COLLISION"], ["STRUCK_BY"], "PROCEDURAL"),
    ("제172조", "SR-FK-172", "차량계 하역운반기계등 접촉 위험 장소 출입 제한", ["COLLISION"], ["STRUCK_BY"], "PROCEDURAL"),
    ("제173조", "SR-FK-173", "차량계 하역운반기계등 화물 적재 시 안전기준 준수", ["COLLISION"], ["STRUCK_BY"], "PROCEDURAL"),
    ("제174조", "SR-FK-174", "차량계 하역운반기계등 이송 시 전도·낙하 방지", ["COLLISION"], ["STRUCK_BY"], "PROCEDURAL"),
    ("제175조", "SR-FK-175", "차량계 하역운반기계등 주용도 외 사용 제한", ["COLLISION"], ["STRUCK_BY"], "PROCEDURAL"),
    ("제183조", "SR-FK-183", "좌석식 지게차 운전 시 좌석 안전띠 착용", ["COLLISION"], ["STRUCK_BY"], "PPE_REQUIREMENT"),
]


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeDB:
    """execute()가 고정 행을 돌려준다 — statute_actions는 article_code로 dict lookup하므로
    쿼리 밖 조문 행이 섞여 있어도 무해하다."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return _FakeResult(self._rows)


def _flow(gk):
    wf = flow_service.by_group_key(gk)
    assert wf is not None, f"흐름 데이터에 {gk} 없음 — trackA 동기화 확인"
    return wf


def _appendix_item(wf, keyword):
    """별표 항목 (ref, text)를 데이터에서 찾는다 — 별표 항목들은 ref 문자열을 공유하므로
    matched 식별자는 (ref, text) 쌍이어야 한다(B-B의 ref 형식 변경에도 텍스트 기준이라 안 깨진다)."""
    for slot in wf.slots:
        if slot.key != "PRECHECK":
            continue
        for it in slot.items:
            if keyword in it.text:
                return (it.ref, it.text)
    pytest.fail(f"PRECHECK에 '{keyword}' 항목 없음 — 흐름 데이터 변경 여부 확인")


def test_fire_hits_via_legacy_alias():
    """화재 코드가 legacy 별칭으로 히트 → 행위형 4건 immediate, 소화설비(제243조) 상단 진입."""
    acts = flow_service.statute_actions_corrective(
        _flow(FIRE_GK), ["FIRE_AND_EXPLOSION"], _FakeDB(FIRE_SRS))
    by_id = {a.action_id: a for a in acts}
    assert "제243조" in by_id, "소화설비 조문이 스트립 6건에 없음"
    for ref in ("제240조", "제239조", "제242조", "제243조"):
        assert by_id[ref].urgency == "immediate", f"{ref} 가 immediate 아님"
    # EMERGENCY_RESPONSE(소화설비)는 행위형 — 상위 4건 안
    assert [a.action_id for a in acts].index("제243조") <= 3


def test_fire_without_fire_code_stays_planned():
    """화재 코드가 없으면(FALL만) 전부 planned — immediate 게이트는 결정론 유지."""
    acts = flow_service.statute_actions_corrective(_flow(FIRE_GK), ["FALL"], _FakeDB(FIRE_SRS))
    assert acts and all(a.urgency == "planned" for a in acts)


def test_matched_boost_appendix_item_to_top_without_urgency():
    """matched 부스트: 별표 '소화기구' 항목 **하나만** 1위로(같은 ref를 공유하는 형제 별표 항목은
    부스트 안 됨) — 단 urgency는 여전히 planned(정책), matched 필드로 근거 표시."""
    wf = _flow(FIRE_GK)
    ref, text = _appendix_item(wf, "소화기구")
    acts = flow_service.statute_actions_corrective(
        wf, ["FALL"], _FakeDB(FIRE_SRS), matched_refs={(ref, text)})
    assert acts[0].action_id == ref
    assert "소화기구" in acts[0].title
    assert acts[0].urgency == "planned"
    assert acts[0].matched is True
    assert sum(1 for a in acts if a.matched) == 1, "같은 ref의 형제 별표 항목까지 부스트되면 안 됨"


def test_appendix_items_do_not_displace_actable_articles():
    """별표 항목은 hazard_hit/actable=False — 무히트 장면에서도 행위형 금지 조문 4건이 위."""
    acts = flow_service.statute_actions_corrective(_flow(FIRE_GK), ["FALL"], _FakeDB(FIRE_SRS))
    top4 = [a.action_id for a in acts[:4]]
    assert top4 == ["제240조", "제239조", "제242조", "제243조"]


def test_forklift_collision_unchanged():
    """지게차×COLLISION 기존 동작(버그 9호 수정 후) 불변 — 별표 클래스 도입의 무회귀 가드."""
    acts = flow_service.statute_actions_corrective(
        _flow(FORKLIFT_GK), ["COLLISION"], _FakeDB(FORKLIFT_SRS))
    assert {a.action_id for a in acts} == {"제183조", "제171조", "제172조", "제173조", "제174조", "제175조"}
    assert all(a.urgency == "immediate" for a in acts)
