#!/usr/bin/env python3
"""P2-Step 1: SR 조회 인덱스 생성.

Pipe-A PostgreSQL DB에서 3종 역인덱스를 자동 생성한다.

1. sr-article-index.json — 조문코드 → SR 목록
2. sr-category-index.json — 위험유형(addresses_hazard) → SR 목록
3. sr-keyword-index.json — SR 키워드 → SR ID

Usage:
    python3 scripts/step2_build_sr_index.py
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("[ERROR] psycopg2 필요: pip install psycopg2-binary")
    sys.exit(1)

# ── 경로 설정 ──
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, DB_CONN_STR


def build_article_index(conn) -> dict:
    """조문코드 → SR 목록 역인덱스.

    sr_article_mapping + articles 테이블에서 생성.
    키: "{law_type}:{article_code}" (예: "RULE:38")
    값: SR identifier 리스트
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT sam.sr_id, sam.law_type, sam.article_code, a.title
        FROM sr_article_mapping sam
        JOIN articles a ON a.law_type = sam.law_type AND a.article_code = sam.article_code
        ORDER BY sam.sr_id
    """)

    index = defaultdict(list)
    article_meta = {}

    for row in cur:
        key = f"{row['law_type']}:{row['article_code']}"
        index[key].append(row["sr_id"])
        if key not in article_meta:
            article_meta[key] = {
                "lawType": row["law_type"],
                "articleCode": row["article_code"],
                "title": row["title"],
            }

    # 딕셔너리로 변환
    result = {}
    for key, sr_ids in sorted(index.items()):
        result[key] = {
            "article": article_meta[key],
            "srIds": sorted(set(sr_ids)),
            "count": len(set(sr_ids)),
        }

    return result


def build_category_index(conn) -> dict:
    """위험유형(addresses_hazard) → SR 목록 역인덱스.

    safety_requirements.addresses_hazard (JSONB)에서 카테고리 추출.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT identifier, addresses_hazard, requirement_type
        FROM safety_requirements
        WHERE addresses_hazard IS NOT NULL
        ORDER BY identifier
    """)

    index = defaultdict(list)

    for row in cur:
        hazard = row["addresses_hazard"]
        if isinstance(hazard, dict):
            # hazard 구조: {"category": "...", "subcategory": "...", ...}
            cat = hazard.get("category", "UNKNOWN")
            index[cat].append(row["identifier"])
        elif isinstance(hazard, list):
            for h in hazard:
                if isinstance(h, dict):
                    cat = h.get("category", "UNKNOWN")
                    index[cat].append(row["identifier"])
                elif isinstance(h, str):
                    index[h].append(row["identifier"])

    result = {}
    for cat, sr_ids in sorted(index.items()):
        result[cat] = {
            "srIds": sorted(set(sr_ids)),
            "count": len(set(sr_ids)),
        }

    return result


def build_keyword_index(conn) -> dict:
    """SR 키워드 → SR ID 매핑.

    SR의 title + text에서 핵심 키워드를 추출하여 역인덱스 생성.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT identifier, title, text, requirement_type, binding_force
        FROM safety_requirements
        ORDER BY identifier
    """)

    # SR 목록 (키워드 인덱스 + 전체 목록)
    sr_list = []
    index = defaultdict(set)

    # 핵심 키워드 패턴
    keyword_patterns = [
        r"추락", r"낙하", r"감전", r"화재", r"폭발", r"질식",
        r"끼임", r"충돌", r"전도", r"붕괴", r"넘어짐",
        r"안전대", r"안전모", r"보호구", r"안전망", r"가설",
        r"비계", r"거푸집", r"굴착", r"해체", r"크레인",
        r"용접", r"도장", r"밀폐", r"산소결핍", r"유해물질",
        r"소음", r"진동", r"분진", r"온도", r"환기",
        r"작업발판", r"사다리", r"개구부", r"난간",
        r"전기", r"배선", r"접지", r"누전",
        r"화학물질", r"가스", r"위험물", r"인화성",
        r"보건", r"건강", r"검진", r"측정",
    ]

    for row in cur:
        sr_id = row["identifier"]
        title = row["title"]
        text = row["text"]
        combined = f"{title} {text}"

        sr_list.append({
            "identifier": sr_id,
            "title": title,
            "requirementType": row["requirement_type"],
            "bindingForce": row["binding_force"],
        })

        # 키워드 매칭
        for kw in keyword_patterns:
            if re.search(kw, combined):
                index[kw].add(sr_id)

    result = {}
    for kw, sr_ids in sorted(index.items()):
        result[kw] = {
            "srIds": sorted(sr_ids),
            "count": len(sr_ids),
        }

    return result, sr_list


def main():
    print("[START] SR 조회 인덱스 생성")

    try:
        conn = psycopg2.connect(DB_CONN_STR)
        print(f"  DB 연결 성공: {DB_CONN_STR.split('password=')[0]}...")
    except Exception as e:
        print(f"[ERROR] DB 연결 실패: {e}")
        sys.exit(1)

    try:
        # 기본 통계
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM safety_requirements")
        sr_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sr_article_mapping")
        mapping_count = cur.fetchone()[0]
        print(f"  SR: {sr_count}개, SR-Article 매핑: {mapping_count}개")

        # 1. Article Index
        print("\n  [1/3] 조문코드 → SR 인덱스 생성...")
        article_index = build_article_index(conn)
        article_output = {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalArticles": len(article_index),
            "index": article_index,
        }
        fp1 = DATA_DIR / "sr-article-index.json"
        fp1.write_text(json.dumps(article_output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    저장: {fp1.name} ({len(article_index)} 조문)")

        # 2. Category Index
        print("  [2/3] 위험유형 → SR 인덱스 생성...")
        category_index = build_category_index(conn)
        category_output = {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalCategories": len(category_index),
            "index": category_index,
        }
        fp2 = DATA_DIR / "sr-category-index.json"
        fp2.write_text(json.dumps(category_output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    저장: {fp2.name} ({len(category_index)} 카테고리)")

        # 3. Keyword Index
        print("  [3/3] 키워드 → SR 인덱스 생성...")
        keyword_index, sr_list = build_keyword_index(conn)
        keyword_output = {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "totalKeywords": len(keyword_index),
            "totalSRs": len(sr_list),
            "srList": sr_list,
            "index": keyword_index,
        }
        fp3 = DATA_DIR / "sr-keyword-index.json"
        fp3.write_text(json.dumps(keyword_output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    저장: {fp3.name} ({len(keyword_index)} 키워드, {len(sr_list)} SR)")

        print(f"\n[DONE] SR 조회 인덱스 3종 생성 완료")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
