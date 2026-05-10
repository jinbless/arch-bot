#!/usr/bin/env python3
"""P-C Step 3: basedOn null 복원 (도메인별 전략).

RECOMMENDED(법령 근거 미확인) CI를 SR 626개와 키워드 매칭하여
복원 후보를 생성한다.

Usage:
    python3 scripts/step3_basedon_restore.py                # 분석만 (DB 변경 없음)
    python3 scripts/step3_basedon_restore.py --apply         # DB 적용 (복원 실행)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, PG_CONNINFO

# 불용어
STOPWORDS = {"하여야", "한다", "있다", "없다", "않는다", "경우", "것이", "따라",
             "위한", "대한", "관한", "의한", "이상", "이하", "이내", "해당",
             "사항", "조치", "등의", "또는", "및", "중", "시", "후", "전",
             "하는", "되는", "수", "것", "때", "위해", "대해", "통해"}

THRESHOLD_HIGH = 5    # 겹침 5개 이상 → 자동 복원 후보
THRESHOLD_LOW = 3     # 겹침 3~4개 → 약한 후보


def keyword_set(text: str) -> set:
    """텍스트에서 키워드 집합 추출 (길이 2+, 불용어 제외)."""
    words = set(re.split(r'\s+', text))
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def main():
    parser = argparse.ArgumentParser(description="basedOn null 복원")
    parser.add_argument("--apply", action="store_true", help="DB 적용 (ci_sr_mapping INSERT + bindingForce 변경)")
    args = parser.parse_args()

    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor()

    print("[START] basedOn null 복원 (Pipe-C Step 3)")

    # 1) SR 626개 텍스트 로드
    cur.execute("SELECT identifier, text, title FROM safety_requirements")
    sr_data = {}
    for sr_id, sr_text, sr_title in cur.fetchall():
        sr_data[sr_id] = {
            "text": sr_text, "title": sr_title,
            "keywords": keyword_set(sr_text + " " + sr_title),
        }
    print(f"  SR 로드: {len(sr_data)}개")

    # 2) null basedOn CI (RECOMMENDED + "법령 근거 미확인") 로드
    cur.execute("""
        SELECT ci.identifier, ci.text, ci.guide_context, ci.binding_force,
               g.domain, g.short_code
        FROM checklist_items ci
        JOIN kosha_guides g ON ci.source_guide = g.guide_code
        WHERE NOT EXISTS (SELECT 1 FROM ci_sr_mapping m WHERE m.ci_id = ci.identifier)
    """)
    null_ci = cur.fetchall()
    print(f"  null basedOn CI: {len(null_ci)}건")

    # 3) 도메인별 키워드 매칭
    restore_high = []   # 겹침 >= THRESHOLD_HIGH
    restore_low = []    # THRESHOLD_LOW <= 겹침 < THRESHOLD_HIGH
    no_match = []
    domain_stats = defaultdict(lambda: {"total": 0, "high": 0, "low": 0, "none": 0})

    for ci_id, ci_text, guide_ctx, bf, domain, sc in null_ci:
        ci_kw = keyword_set(ci_text)
        domain_stats[domain]["total"] += 1

        best_sr = None
        best_score = 0
        top3 = []

        for sr_id, sr_info in sr_data.items():
            overlap = len(ci_kw & sr_info["keywords"])
            if overlap > 0:
                top3.append((sr_id, overlap, sr_info["title"]))

        top3.sort(key=lambda x: x[1], reverse=True)
        top3 = top3[:3]

        if top3 and top3[0][1] >= THRESHOLD_HIGH:
            restore_high.append({
                "ciId": ci_id, "domain": domain, "guide": sc,
                "bestSR": top3[0][0], "bestScore": top3[0][1],
                "top3": [(s, sc_, t[:50]) for s, sc_, t in top3],
                "ciSnippet": ci_text[:80],
            })
            domain_stats[domain]["high"] += 1
        elif top3 and top3[0][1] >= THRESHOLD_LOW:
            restore_low.append({
                "ciId": ci_id, "domain": domain, "guide": sc,
                "bestSR": top3[0][0], "bestScore": top3[0][1],
                "top3": [(s, sc_, t[:50]) for s, sc_, t in top3],
                "ciSnippet": ci_text[:80],
            })
            domain_stats[domain]["low"] += 1
        else:
            no_match.append({"ciId": ci_id, "domain": domain, "guide": sc})
            domain_stats[domain]["none"] += 1

    # 4) DB 적용 (--apply)
    applied = 0
    if args.apply and restore_high:
        print(f"\n  [APPLY] {len(restore_high)}건 자동 복원 중...")
        for r in restore_high:
            # ci_sr_mapping INSERT
            cur.execute(
                "INSERT INTO ci_sr_mapping (ci_id, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (r["ciId"], r["bestSR"]),
            )
            # bindingForce → MANDATORY 복원 + guideContext "(법령 근거 미확인)" 제거
            cur.execute("""
                UPDATE checklist_items
                SET binding_force = 'MANDATORY',
                    guide_context = REPLACE(COALESCE(guide_context, ''), '(법령 근거 미확인)', '')
                WHERE identifier = %s
            """, (r["ciId"],))
            applied += 1
        conn.commit()
        print(f"  [APPLY] {applied}건 복원 완료")

    conn.close()

    # 보고서
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalNullCI": len(null_ci),
        "restoreHigh": len(restore_high),
        "restoreLow": len(restore_low),
        "noMatch": len(no_match),
        "restoreRate": round((len(restore_high) + len(restore_low)) / len(null_ci) * 100, 1) if null_ci else 0,
        "applied": applied,
        "thresholdHigh": THRESHOLD_HIGH,
        "thresholdLow": THRESHOLD_LOW,
        "domainStats": dict(domain_stats),
        "restoreHighList": restore_high[:100],
        "restoreLowList": restore_low[:50],
    }

    report_path = DATA_DIR / "basedon-restore-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # 출력
    print(f"\n  null CI: {len(null_ci)}건")
    print(f"  복원 가능 (겹침 {THRESHOLD_HIGH}+): {len(restore_high)}건")
    print(f"  약한 후보 (겹침 {THRESHOLD_LOW}~{THRESHOLD_HIGH-1}): {len(restore_low)}건")
    print(f"  매칭 없음: {len(no_match)}건")
    print(f"  복원률: {report['restoreRate']}%")

    print(f"\n  도메인별:")
    for d in sorted(domain_stats.keys()):
        s = domain_stats[d]
        print(f"    {d}: 총 {s['total']}, 강({s['high']}), 약({s['low']}), 없음({s['none']})")

    if restore_high:
        print(f"\n  복원 후보 샘플 (상위 5건):")
        for r in restore_high[:5]:
            print(f"    {r['ciId']} → {r['bestSR']} (score={r['bestScore']}, {r['domain']})")

    print(f"\n  적용 여부: {'적용됨 ({applied}건)' if applied else '분석만 (--apply로 적용)'}")
    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
