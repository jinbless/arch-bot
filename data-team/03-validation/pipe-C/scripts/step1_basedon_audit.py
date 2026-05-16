#!/usr/bin/env python3
"""P-C Step 1: basedOn 기존 매핑 정확성 감사.

ci_sr_mapping의 CI 텍스트와 SR 텍스트 간 키워드 겹침을 계산하여
의심 매핑(overlap=0)을 탐지한다. 도메인별 분리 분석.

Usage:
    python3 scripts/step1_basedon_audit.py
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, PG_CONNINFO

# 불용어 (한국어 조사, 접미사, 일반어)
STOPWORDS = {"하여야", "한다", "있다", "없다", "않는다", "경우", "것이", "따라",
             "위한", "대한", "관한", "의한", "이상", "이하", "이내", "해당",
             "사항", "조치", "등의", "또는", "및", "중", "시", "후", "전"}


def keyword_overlap(ci_text: str, sr_text: str) -> int:
    """CI 텍스트와 SR 텍스트 간 공통 키워드 수 (길이 2+ 단어, 불용어 제외)."""
    ci_words = set(re.split(r'\s+', ci_text))
    ci_words = {w for w in ci_words if len(w) > 2 and w not in STOPWORDS}

    count = 0
    for w in ci_words:
        if w in sr_text:
            count += 1
    return count


def main():
    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor()

    print("[START] basedOn 매핑 정확성 감사 (Pipe-C Step 1)")

    # 모든 ci_sr_mapping + CI 텍스트 + SR 텍스트 로드
    cur.execute("""
        SELECT m.ci_id, m.sr_id, ci.text, sr.text, ci.binding_force,
               g.domain, g.short_code
        FROM ci_sr_mapping m
        JOIN checklist_items ci ON m.ci_id = ci.identifier
        JOIN safety_requirements sr ON m.sr_id = sr.identifier
        JOIN kosha_guides g ON ci.source_guide = g.guide_code
        ORDER BY m.ci_id
    """)
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    print(f"  총 매핑: {total}건")

    suspicious = []
    weak = []
    normal = []
    domain_stats = defaultdict(lambda: {"total": 0, "suspicious": 0, "weak": 0, "normal": 0})

    for ci_id, sr_id, ci_text, sr_text, bf, domain, sc in rows:
        overlap = keyword_overlap(ci_text, sr_text)
        entry = {
            "ciId": ci_id, "srId": sr_id,
            "overlap": overlap, "domain": domain,
            "guide": sc, "bindingForce": bf,
            "ciTextSnippet": ci_text[:80],
            "srTextSnippet": sr_text[:80],
        }

        domain_stats[domain]["total"] += 1
        if overlap == 0:
            suspicious.append(entry)
            domain_stats[domain]["suspicious"] += 1
        elif overlap <= 2:
            weak.append(entry)
            domain_stats[domain]["weak"] += 1
        else:
            normal.append(entry)
            domain_stats[domain]["normal"] += 1

    # 보고서
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalMappings": total,
        "suspicious": len(suspicious),
        "suspiciousRate": round(len(suspicious) / total * 100, 1) if total > 0 else 0,
        "weak": len(weak),
        "weakRate": round(len(weak) / total * 100, 1) if total > 0 else 0,
        "normal": len(normal),
        "normalRate": round(len(normal) / total * 100, 1) if total > 0 else 0,
        "domainStats": dict(domain_stats),
        "suspiciousList": suspicious[:50],  # 상위 50건만
        "weakList": weak[:30],
    }

    report_path = DATA_DIR / "basedon-audit-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # 출력
    print(f"\n  의심 (overlap=0): {len(suspicious)}건 ({report['suspiciousRate']}%)")
    print(f"  약함 (overlap 1~2): {len(weak)}건 ({report['weakRate']}%)")
    print(f"  정상 (overlap 3+): {len(normal)}건 ({report['normalRate']}%)")

    print(f"\n  도메인별:")
    for d in sorted(domain_stats.keys()):
        s = domain_stats[d]
        print(f"    {d}: 총 {s['total']}, 의심 {s['suspicious']}, 약함 {s['weak']}, 정상 {s['normal']}")

    if suspicious:
        print(f"\n  의심 매핑 샘플 (상위 5건):")
        for e in suspicious[:5]:
            print(f"    {e['ciId']} → {e['srId']} (domain={e['domain']})")
            print(f"      CI: {e['ciTextSnippet']}...")
            print(f"      SR: {e['srTextSnippet']}...")

    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
