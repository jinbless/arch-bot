#!/usr/bin/env python3
"""Semantic review for CI no-action rows classified as CI mapping review.

This is a diagnostic report only.  It does not update ChecklistItem/SR
mapping, Guide profiles, runtime scoring, SHE approval, status, penalty, or
asserted legal links.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_REPORT = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports" / "ci_no_action_triage_ci_broad_sr_guard4.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "data-team/05-enrichment/eval-data" / "reports"
DEFAULT_PREFIX = "ci_mapping_review_semantic_ci_broad_sr_guard4"


CASE_REVIEW: dict[str, dict[str, str]] = {
    "SYN-0043": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "화학물질 누출 장면인데 콘크리트 슬래브 Guide가 top이다. CI-SR 매핑을 보강할 대상이 아니라 Guide 선택 경계 문제다.",
    },
    "SYN-V10-0097": {
        "semantic_category": "safe_or_followup_no_immediate",
        "next_action": "keep_no_action",
        "review_reason": "출입 차단과 환기가 이미 확보된 코팅 준비 장면이다. 현장 즉시조치보다는 후속 관리 또는 no-action이 적절하다.",
    },
    "SYN-V10-0182": {
        "semantic_category": "safe_or_followup_no_immediate",
        "next_action": "keep_no_action",
        "review_reason": "MSDS에 따라 폐액 분리와 라벨링을 완료한 안전 수행 장면이다. 즉시조치 CI를 강제로 만들 필요가 없다.",
    },
    "SYN-V10-0187": {
        "semantic_category": "safe_or_followup_no_immediate",
        "next_action": "keep_no_action",
        "review_reason": "작업허가서 발급, 감시원 배치 후 승인된 장면이다. 표준절차 follow-up은 가능하지만 즉시조치 대상은 아니다.",
    },
    "SYN-V10-0251": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "마취가스 누출 점검 장면인데 내화구조 Guide가 top이다. 수의·마취가스 corpus gap과 Guide 선택 오류가 섞여 있다.",
    },
    "SYN-V2-0035": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "고압 배관 플랜지 볼트 미체결인데 휴대용 연삭기 Guide가 top이다.",
    },
    "SYN-V2-0066": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "우천 중 임시 배전함 감전 장면인데 고령근로자 작업 Guide가 top이다.",
    },
    "SYN-V3-0014": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "젖은 도마와 식칼 절단 위험에 학교 급식실 Guide가 올라왔다. 도메인 확장은 검토가 필요하지만 CI 생성 후보로 볼 수 있다.",
    },
    "SYN-V3-0031": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "가스호스 균열은 외식업 가스기기 gap이다. 인화성 액체 분무공정 Guide에 CI를 붙이면 과한 비유가 된다.",
    },
    "SYN-V3-0032": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "가스레인지 지연점화는 공업용 가열로와 일부 원리는 유사하지만 현장 Guide로는 과한 비유다.",
    },
    "SYN-V3-0052": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "락스 원액 청소 노출인데 직업성 염소 급성중독 진료지침이 top이다. 진료지침은 사진 기반 즉시조치 Guide로 부적합하다.",
    },
    "SYN-V3-0065": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "냉장고 암모니아 냉매 누출은 배관 비상계획과 관련은 있지만 외식 냉동설비 현장조치 corpus gap이 크다.",
    },
    "SYN-V3-0096": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "부식성 세제 누출인데 생산관련 물류 리스크 평가 Guide가 top이다.",
    },
    "SYN-V3-0132": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "실내 LPG 용기 보관은 가스기기·위험물 저장 gap이다. 배관 비상계획 Guide는 후속관리 성격에 가깝다.",
    },
    "SYN-V3-0133": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "화기 주변 소화기 부재에 소규모사업장 화재·폭발 방지 Guide가 올라온 적절한 후보다.",
    },
    "SYN-V3-0136": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "가스레인지 지연점화는 공업용 가열로와 일부 유사하지만 외식업 가스기기 Guide gap으로 보는 편이 안전하다.",
    },
    "SYN-V4-0009": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "에어 임팩트 렌치 과압인데 가스용기 비상조치 Guide가 top이다.",
    },
    "SYN-V4-0022": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "염색약 눈 접촉 위험과 PPE Guide의 연결은 타당하다. 눈 보호·세안 CI 후보 검토가 필요하다.",
    },
    "SYN-V4-0027": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "UV 램프 직시와 PPE Guide의 연결은 타당하다. 보안경/직시금지 CI 후보 검토가 필요하다.",
    },
    "SYN-V4-0037": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "고객 목 과굴곡 위험인데 근골격계질환 근로자 Guide가 top이다. 보호대상이 달라 즉시조치 CI로 확장하면 위험하다.",
    },
    "SYN-V4-0058": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "장시간 기립 계산대 근무와 근골격계 예방 Guide는 타당한 후보다.",
    },
    "SYN-V4-0077": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "네일건 오발은 공구/타정기 Guide gap이다. 경량철골 천장공사 Guide는 제한적 비유에 그친다.",
    },
    "SYN-V4-0078": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "네일건 관통 위험은 타정기/수공구 gap이다. 현재 top Guide에 CI를 억지로 붙이면 업종 경계가 흐려진다.",
    },
    "SYN-V5-0001": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "PERC 누출과 드라이클리닝 공정 안전 Guide는 직접적인 후보다.",
    },
    "SYN-V5-0006": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "세탁 프레스 손 압착인데 고열 압력용기 보호 Guide가 top이다.",
    },
    "SYN-V5-0007": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "고온 증기 안면 분출과 PPE Guide는 즉시 보호구 CI 후보로 볼 수 있다.",
    },
    "SYN-V5-0011": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "산업용 세탁기 회전 중 개방인데 고열 압력용기 Guide가 top이다.",
    },
    "SYN-V5-0013": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "뜨거운 세탁물 취급은 열 화상 현장조치가 필요하지만 고온 염색기 Guide는 부분 비유다.",
    },
    "SYN-V5-0021": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "산성 얼룩 제거제 눈 튐과 PPE Guide는 직접적인 후보다.",
    },
    "SYN-V5-0023": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "세탁 얼룩제거 유기용제 노출인데 숙박시설 객실청소 Guide가 top이다.",
    },
    "SYN-V5-0036": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "세차 폼 세정제 눈 튐과 PPE Guide는 직접적인 후보다.",
    },
    "SYN-V5-0046": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "자동세차 컨베이어 손 끼임과 회전기계 끼임 Guide는 직접적인 후보다.",
    },
    "SYN-V5-0047": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "자동세차 컨베이어 레일 낙상과 넘어짐 방지 Guide는 타당한 후보다.",
    },
    "SYN-V5-0051": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "차량 실내 밀폐 화학분무는 환기/용제 노출 gap이다. 숙박 객실청소 Guide는 제한적 비유다.",
    },
    "SYN-V5-0052": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "차량 내부 비틀림 작업인데 산업폐기물 처리 Guide가 top이다.",
    },
    "SYN-V5-0061": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "펫샵 개 교상은 동물 취급 Guide gap이다. 동물원 Guide는 가까운 비유지만 업종 차이가 크다.",
    },
    "SYN-V5-0063": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "미용 가위 방치인데 급식실 시설 Guide가 top이다.",
    },
    "SYN-V5-0066": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "고양이 할큄은 동물 취급/감염 gap이다. 수공구 Guide와는 거리가 있다.",
    },
    "SYN-V5-0067": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "고양이 얼굴 할큄과 보안경/PPE Guide는 보호구 CI 후보로 볼 수 있다.",
    },
    "SYN-V5-0068": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "펫샵 고양이 교상은 동물 취급/교상 gap이다. 동물원 Guide는 가까운 비유지만 업종·작업장 경계가 커서 CI를 직접 확장하기엔 이르다.",
    },
    "SYN-V5-0081": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "동물 있는 케이지 청소는 동물 취급 gap이다. 동물원 Guide는 제한적 비유다.",
    },
    "SYN-V5-0083": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "케이지 청소 허리 굴곡인데 갱폼 Guide가 top이다.",
    },
    "SYN-V5-0086": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "맹견 먹이 급여는 동물 취급 gap이다. 동물원 Guide는 가까운 비유지만 업종 경계 검토가 필요하다.",
    },
    "SYN-V5-0088": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "파충류 급여는 동물 취급 gap이다. 소 사육장 Guide는 과한 비유다.",
    },
    "SYN-V5-0116": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "컨베이어 롤러 끼임과 회전기계 끼임 Guide는 직접적인 후보다.",
    },
    "SYN-V5-0148": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "질산암모늄과 가솔린 혼재 보관인데 내화구조 Guide가 top이다.",
    },
    "SYN-V5-0158": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "소화기 압력·점검 라벨 불량과 소규모사업장 화재·폭발 방지 Guide는 직접적인 후보다. 소화기 교체/점검 CI-SR 후보 검토가 필요하다.",
    },
    "SYN-V6-0186": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "매립지 침출수 취급인데 실험실 안전 Guide가 top이다. 화학 PPE gap은 있으나 현장 Guide 경계가 맞지 않는다.",
    },
    "SYN-V6-0192": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "산·알칼리 폐기물 혼합 반응은 화학폐기물 처리 gap이다. 유기도료 제조설비 Guide는 제한적 비유다.",
    },
    "SYN-V6-0242": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "치과 탐침·샤프 폐기 감염 위험은 의료 sharps gap이다. 가을철 발열성 질환 Guide는 부적절한 비유다.",
    },
    "SYN-V6-0251": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "주사바늘 recapping은 의료 sharps gap이다. 가을철 발열성 질환 Guide에 CI를 붙이면 의미가 어긋난다.",
    },
    "SYN-V6-0252": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "샤프 컨테이너 과적은 의료 sharps gap이다. 현재 top Guide는 감염 일반 비유에 그친다.",
    },
    "SYN-V6-0261": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "한방 침 폐기는 의료 sharps gap이다. 가을철 발열성 질환 Guide와는 직접성이 약하다.",
    },
    "SYN-V6-0296": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "장미 가시 찔림인데 배관지지물 Guide가 top이다.",
    },
    "SYN-V6-0303": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "어린이집 주방 가스 누출은 조리직종 Guide와 관련은 있지만 가스안전 현장조치 gap이 크다.",
    },
    "SYN-V7-0296": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "선박 기관실 무허가 화기작업인데 공업용 가열로 Guide가 top이다. 용접/화기작업 Guide 쪽으로 가야 한다.",
    },
    "SYN-V7-0312": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "연료 잔류 가능 위치에서 용접 불꽃과 소화기 부재가 있고 용접방화포 Guide가 올라온 타당한 후보다.",
    },
    "SYN-V8-0001": {
        "semantic_category": "corpus_gap_or_near_analogy",
        "next_action": "source_or_taxonomy_review",
        "review_reason": "체인톱 PPE는 임업/체인톱 Guide gap이다. 해체공사 Guide는 과한 비유다.",
    },
    "SYN-V8-0023": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "비닐하우스 CO 중독 위험인데 시안화수소 Guide가 top이다.",
    },
    "SYN-V8-0163": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "강알칼리 세제 눈 튐과 PPE Guide는 직접적인 후보다.",
    },
    "SYN-V8-0212": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "테이블쏘 킥백인데 목공용 기계 소음관리 Guide가 top이다. 같은 장비군이어도 사고축이 다르다.",
    },
    "SYN-V9-0103": {
        "semantic_category": "guide_selection_mismatch",
        "next_action": "guide_profile_or_scoring_review",
        "review_reason": "방청 도료 분무 유기용제 노출인데 배관 비파괴검사/열처리 Guide가 top이다.",
    },
    "SYN-V9-0056": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "고층 옥상 가장자리 안테나 설치와 추락방호망/추락방지 Guide는 가까운 현장조치 후보다. 안전대 체결·방호망·난간 CI-SR 후보 검토가 필요하다.",
    },
    "SYN-V9-0057": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "창문 밖 외벽 장비 점검과 건물 외벽 작업 Guide는 가까운 현장조치 후보다. 창문 밖 작업 금지, 안전대·고소작업차 사용 CI-SR 후보 검토가 필요하다.",
    },
    "SYN-V9-0146": {
        "semantic_category": "true_ci_mapping_candidate",
        "next_action": "ci_sr_mapping_candidate_review",
        "review_reason": "동절기 결빙면 미끄럼과 취약시기 건설현장 Guide는 가까운 후보다.",
    },
    "SYN-V9-0172": {
        "semantic_category": "safe_or_followup_no_immediate",
        "next_action": "keep_no_action",
        "review_reason": "용접 작업자가 환기팬과 흄 마스크를 사용 중인 통제 장면이다. 추가 즉시조치를 만들면 safe scene 과잉이 된다.",
    },
    "SYN-V9-0286": {
        "semantic_category": "safe_or_followup_no_immediate",
        "next_action": "keep_no_action",
        "review_reason": "냉동기 정비에서 LOTO, 냉매 회수, PPE가 이미 적용된 통제 장면이다.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _top(counter: Counter[str], limit: int = 20) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in counter.most_common(limit)]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _infer_baseline(path: Path) -> str:
    name = path.stem
    prefix = "ci_no_action_triage_"
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def _build_rows(source_report: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = _load_json(source_report)
    source_rows = [
        row
        for row in data.get("rows") or []
        if row.get("repair_group") == "ci_mapping_review"
    ]
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for row in source_rows:
        case_id = str(row.get("case_id"))
        review = CASE_REVIEW.get(case_id)
        if not review:
            missing.append(case_id)
            review = {
                "semantic_category": "needs_manual_review",
                "next_action": "manual_semantic_review",
                "review_reason": "현재 CASE_REVIEW에 없는 신규 CI mapping-review 행이다. 자동으로 CI-SR 매핑 후보로 승격하지 말고 수동 의미검토가 필요하다.",
            }
        rows.append(
            {
                **row,
                **review,
                "ci_mapping_should_be_added": review["semantic_category"] == "true_ci_mapping_candidate",
                "runtime_change_scope": (
                    "candidate_mapping_review"
                    if review["semantic_category"] == "true_ci_mapping_candidate"
                    else "no_direct_ci_runtime_change"
                ),
            }
        )

    unexpected = sorted(set(CASE_REVIEW) - {str(row.get("case_id")) for row in source_rows})

    category_counts = Counter(row["semantic_category"] for row in rows)
    next_action_counts = Counter(row["next_action"] for row in rows)
    true_ci_rows = [row for row in rows if row["semantic_category"] == "true_ci_mapping_candidate"]
    wrong_guide_rows = [row for row in rows if row["semantic_category"] == "guide_selection_mismatch"]
    corpus_gap_rows = [row for row in rows if row["semantic_category"] == "corpus_gap_or_near_analogy"]
    safe_rows = [row for row in rows if row["semantic_category"] == "safe_or_followup_no_immediate"]
    manual_rows = [row for row in rows if row["semantic_category"] == "needs_manual_review"]

    source_summary = data.get("summary") or {}
    baseline = source_summary.get("baseline") or _infer_baseline(source_report)
    summary: dict[str, Any] = {
        "generated_at": _now(),
        "baseline": baseline,
        "source_report": _display_path(source_report),
        "source_ci_mapping_review_count": len(source_rows),
        "reviewed_case_count": len(source_rows) - len(missing),
        "missing_review_case_count": len(missing),
        "missing_review_case_ids": sorted(missing),
        "retired_review_case_count": len(unexpected),
        "retired_review_case_ids": unexpected,
        "semantic_category_counts": dict(category_counts.most_common()),
        "next_action_counts": dict(next_action_counts.most_common()),
        "true_ci_mapping_candidate_count": len(true_ci_rows),
        "guide_selection_mismatch_count": len(wrong_guide_rows),
        "corpus_gap_or_near_analogy_count": len(corpus_gap_rows),
        "safe_or_followup_no_immediate_count": len(safe_rows),
        "needs_manual_review_count": len(manual_rows),
        "top_guides_true_ci_mapping_candidates": _top(Counter(row.get("top_guide") for row in true_ci_rows if row.get("top_guide"))),
        "top_guides_guide_selection_mismatch": _top(Counter(row.get("top_guide") for row in wrong_guide_rows if row.get("top_guide"))),
        "industries_true_ci_mapping_candidates": _top(Counter(row.get("industry_context") for row in true_ci_rows if row.get("industry_context"))),
        "industries_corpus_gap_or_near_analogy": _top(Counter(row.get("industry_context") for row in corpus_gap_rows if row.get("industry_context"))),
        "interpretation": (
            f"Only {len(true_ci_rows)} of {len(source_rows)} CI mapping-review rows are safe candidates for CI-SR/candidate mapping work. "
            "Most rows are Guide selection mismatch, source/taxonomy corpus gap, or safe/follow-up scenes where no immediate action is acceptable. "
            "Rows without explicit semantic review are kept as needs_manual_review and are not treated as mapping candidates."
        ),
    }
    return summary, rows


def _write_reports(summary: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path, prefix: str) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{prefix}.json"
    md_path = output_dir / f"{prefix}.md"
    csv_path = output_dir / f"{prefix}.csv"

    json_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        f"# CI Mapping Review Semantic Triage: {summary['baseline']}",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- source report: `{summary['source_report']}`",
        f"- source CI mapping-review rows: `{summary['source_ci_mapping_review_count']}`",
        f"- reviewed rows: `{summary['reviewed_case_count']}`",
        f"- needs manual review: `{summary['missing_review_case_count']}`",
        "",
        "## Semantic Categories",
        "",
    ]
    for key, count in summary["semantic_category_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(["", "## Next Actions", ""])
    for key, count in summary["next_action_counts"].items():
        md_lines.append(f"- `{key}`: `{count}`")
    md_lines.extend(
        [
            "",
            "## Practical Interpretation",
            "",
            f"- true CI mapping candidates: `{summary['true_ci_mapping_candidate_count']}`",
            f"- Guide selection/profile mismatch: `{summary['guide_selection_mismatch_count']}`",
            f"- corpus gap or near analogy: `{summary['corpus_gap_or_near_analogy_count']}`",
            f"- safe/follow-up no immediate action: `{summary['safe_or_followup_no_immediate_count']}`",
            f"- needs manual review: `{summary['needs_manual_review_count']}`",
            "",
            summary["interpretation"],
            "",
            "## True CI Mapping Candidate Examples",
            "",
        ]
    )
    for row in [row for row in rows if row["semantic_category"] == "true_ci_mapping_candidate"][:12]:
        md_lines.append(
            f"- `{row['case_id']}` `{row['industry_context']}` top Guide `{row['top_guide']}`: {row['review_reason']}"
        )
    md_lines.extend(["", "## Do Not Fix By CI Mapping", ""])
    for row in [row for row in rows if row["semantic_category"] != "true_ci_mapping_candidate"][:12]:
        md_lines.append(
            f"- `{row['case_id']}` `{row['semantic_category']}` top Guide `{row['top_guide']}`: {row['review_reason']}"
        )
    manual_rows = [row for row in rows if row["semantic_category"] == "needs_manual_review"]
    if manual_rows:
        md_lines.extend(["", "## Manual Review Required", ""])
        for row in manual_rows:
            md_lines.append(
                f"- `{row['case_id']}` `{row.get('industry_context')}` top Guide `{row.get('top_guide')}`: {row['review_reason']}"
            )
    md_lines.extend(
        [
            "",
            "This report is diagnostic only. It does not update runtime behavior, SHE approval, status, penalty, asserted legal mapping, Guide profiles, or CI-SR mappings.",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    fieldnames = [
        "case_id",
        "version",
        "industry_context",
        "work_context",
        "semantic_category",
        "next_action",
        "ci_mapping_should_be_added",
        "runtime_change_scope",
        "top_guide",
        "top_guide_title",
        "triage_category",
        "top_guide_ci_count",
        "top_guide_ci_with_sr_mapping_count",
        "top_guide_ci_matching_response_sr_count",
        "top_guide_ci_matching_non_broad_response_sr_count",
        "sr_count",
        "broad_sr_count",
        "review_reason",
        "photo_description",
        "expected_primary_risk",
        "expected_corrective_direction",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--report-prefix", default=DEFAULT_PREFIX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, rows = _build_rows(args.source_report)
    paths = _write_reports(summary, rows, args.output_dir, args.report_prefix)
    print(json.dumps({"summary": summary, "paths": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
