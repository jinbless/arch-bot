#!/usr/bin/env python3
"""P3-Step 3: SR Phase 3 예약 필드 채우기 (deterministic 4/5 필드).

Pipe-B CI/WP/ES/DR 데이터를 기반으로 safety_requirements 테이블의 예약 필드를 UPDATE.
파일럿에서는 deterministic 필드만 채움 (LLM 의존 필드 제외).

필드:
1. requires_ppe ← WP.requiredPPE 집계 (via ci_sr_mapping → WP의 source_guide와 동일 가이드)
2. has_corrective_action ← null (LLM 의존 — 파일럿 제외)
3. has_incident_response ← DR(INCIDENT_REPORT) 존재 여부
4. applicable_industry ← 가이드 도메인 집계
5. hazard_assessment ← DR(RISK_ASSESSMENT) 존재 여부

Usage:
    python3 scripts/step7_fill_sr_phase3.py          # 전체 SR 업데이트
    python3 scripts/step7_fill_sr_phase3.py --pilot   # 파일럿 SR만
"""

import argparse
import json
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def fill_requires_ppe(cur) -> int:
    """requires_ppe: SR과 연결된 WP의 PPE 집계."""
    # ci_sr_mapping으로 SR↔CI 연결
    # CI.source_guide = WP.source_guide (같은 가이드)
    # WP→wp_ppe에서 PPE 수집
    cur.execute("""
        WITH sr_ppe AS (
            SELECT DISTINCT m.sr_id, p.ppe_type
            FROM ci_sr_mapping m
            JOIN checklist_items ci ON m.ci_id = ci.identifier
            JOIN work_processes wp ON wp.source_guide = ci.source_guide
            JOIN wp_ppe p ON p.wp_id = wp.identifier
        ),
        sr_ppe_agg AS (
            SELECT sr_id, json_agg(DISTINCT ppe_type) AS ppe_list
            FROM sr_ppe
            GROUP BY sr_id
        )
        UPDATE safety_requirements sr
        SET requires_ppe = a.ppe_list
        FROM sr_ppe_agg a
        WHERE sr.identifier = a.sr_id
    """)
    count = cur.rowcount
    return count


def fill_has_incident_response(cur) -> int:
    """has_incident_response: DR(INCIDENT_REPORT)과 연결된 SR."""
    cur.execute("""
        WITH sr_incident AS (
            SELECT DISTINCT m.sr_id
            FROM ci_sr_mapping m
            JOIN checklist_items ci ON m.ci_id = ci.identifier
            JOIN document_requirements dr ON dr.source_guide = ci.source_guide
            WHERE dr.document_type = 'INCIDENT_REPORT'
        )
        UPDATE safety_requirements sr
        SET has_incident_response = 'true'::jsonb
        FROM sr_incident i
        WHERE sr.identifier = i.sr_id
    """)
    count = cur.rowcount
    return count


def fill_applicable_industry(cur) -> int:
    """applicable_industry: SR과 연결된 가이드의 도메인 집계."""
    cur.execute("""
        WITH sr_domains AS (
            SELECT DISTINCT m.sr_id, g.domain
            FROM ci_sr_mapping m
            JOIN checklist_items ci ON m.ci_id = ci.identifier
            JOIN kosha_guides g ON g.guide_code = ci.source_guide
        ),
        sr_domain_agg AS (
            SELECT sr_id, json_agg(DISTINCT domain ORDER BY domain) AS domains
            FROM sr_domains
            GROUP BY sr_id
        )
        UPDATE safety_requirements sr
        SET applicable_industry = a.domains
        FROM sr_domain_agg a
        WHERE sr.identifier = a.sr_id
    """)
    count = cur.rowcount
    return count


def fill_has_corrective_action(cur) -> int:
    """has_corrective_action: CI 텍스트에서 시정조치 키워드 탐지."""
    # CI 텍스트에 시정/조치/개선/보수/교체/중지 키워드가 있으면 해당 SR에 true 설정
    cur.execute("""
        WITH sr_corrective AS (
            SELECT DISTINCT m.sr_id
            FROM ci_sr_mapping m
            JOIN checklist_items ci ON m.ci_id = ci.identifier
            WHERE ci.text ~ '(시정|조치|개선|보수|교체|중지|수리|정비|복구)'
        )
        UPDATE safety_requirements sr
        SET has_corrective_action = 'true'::jsonb
        FROM sr_corrective c
        WHERE sr.identifier = c.sr_id
    """)
    count = cur.rowcount
    return count


def fill_hazard_assessment(cur) -> int:
    """hazard_assessment: DR(RISK_ASSESSMENT)과 연결된 SR."""
    cur.execute("""
        WITH sr_hazard AS (
            SELECT DISTINCT m.sr_id
            FROM ci_sr_mapping m
            JOIN checklist_items ci ON m.ci_id = ci.identifier
            JOIN document_requirements dr ON dr.source_guide = ci.source_guide
            WHERE dr.document_type = 'RISK_ASSESSMENT'
        )
        UPDATE safety_requirements sr
        SET hazard_assessment = 'true'::jsonb
        FROM sr_hazard h
        WHERE sr.identifier = h.sr_id
    """)
    count = cur.rowcount
    return count


def main():
    parser = argparse.ArgumentParser(description="SR Phase 3 예약 필드 채우기")
    parser.add_argument("--pilot", action="store_true", help="파일럿 모드 (로그만)")
    args = parser.parse_args()

    conn = psycopg2.connect(PG_CONNINFO)
    conn.autocommit = False
    cur = conn.cursor()

    print("[START] SR Phase 3 필드 채우기")

    # 1. requires_ppe
    n = fill_requires_ppe(cur)
    print(f"  requires_ppe: {n}개 SR 업데이트")

    # 2. has_corrective_action — 키워드 기반 (시정, 조치, 개선, 보수, 교체, 중지)
    n = fill_has_corrective_action(cur)
    print(f"  has_corrective_action: {n}개 SR 업데이트")

    # 3. has_incident_response
    n = fill_has_incident_response(cur)
    print(f"  has_incident_response: {n}개 SR 업데이트")

    # 4. applicable_industry
    n = fill_applicable_industry(cur)
    print(f"  applicable_industry: {n}개 SR 업데이트")

    # 5. hazard_assessment
    n = fill_hazard_assessment(cur)
    print(f"  hazard_assessment: {n}개 SR 업데이트")

    conn.commit()

    # 결과 요약
    cur.execute("SELECT count(*) FROM safety_requirements WHERE requires_ppe IS NOT NULL")
    ppe_filled = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM safety_requirements WHERE has_incident_response IS NOT NULL")
    ir_filled = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM safety_requirements WHERE applicable_industry IS NOT NULL")
    ai_filled = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM safety_requirements WHERE hazard_assessment IS NOT NULL")
    ha_filled = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM safety_requirements")
    total_sr = cur.fetchone()[0]

    print(f"\n[DONE] Phase 3 필드 현황 (총 SR: {total_sr})")
    print(f"  requires_ppe:          {ppe_filled}/{total_sr}")
    cur.execute("SELECT count(*) FROM safety_requirements WHERE has_corrective_action IS NOT NULL")
    ca_filled = cur.fetchone()[0]
    print(f"  has_corrective_action: {ca_filled}/{total_sr}")
    print(f"  has_incident_response: {ir_filled}/{total_sr}")
    print(f"  applicable_industry:   {ai_filled}/{total_sr}")
    print(f"  hazard_assessment:     {ha_filled}/{total_sr}")

    conn.close()


if __name__ == "__main__":
    main()
