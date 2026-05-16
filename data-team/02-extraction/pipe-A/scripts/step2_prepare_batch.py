#!/usr/bin/env python3
"""Step 2 준비: LLM 에이전트용 배치 입력 JSON 생성.

article-texts.json + penalty-routes.json을 읽어
agents/step3-ns-generation.md 스펙에 맞는 배치 입력을 생성한다.

Usage:
    python3 step2_prepare_batch.py --articles 제24조,제2조,제42조 --batch-id batch-001
    python3 step2_prepare_batch.py --law-id RULE --range 3-50 --batch-id batch-002
    python3 step2_prepare_batch.py --law-id RULE --all --batch-size 20
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
NS_DIR = DATA_DIR / "norm-statements"

sys.path.insert(0, str(SCRIPT_DIR))
from lib.ns_identifier import generate_ns_id


def load_data():
    with open(DATA_DIR / "article-texts.json", encoding="utf-8") as f:
        articles = json.load(f)
    penalty_path = DATA_DIR / "penalty-routes.json"
    penalties = {}
    if penalty_path.exists():
        with open(penalty_path, encoding="utf-8") as f:
            penalties = json.load(f)
    return articles, penalties


def build_sanction_block(route: dict) -> dict | None:
    """penalty-routes.json의 route를 NS용 hasSanction 블록으로 변환.

    v2: criminal/administrative 분리 구조.
    """
    has_penalty = route.get("hasPenalty", False)
    has_admin = route.get("hasAdministrativeFine", False)

    if not has_penalty and not has_admin:
        return None

    return {
        "criminal": route.get("criminal"),
        "administrative": route.get("administrative"),
    }


def prepare_article(law_id: str, article_code: str, article: dict, penalties: dict) -> dict:
    """단일 조문의 배치 입력 항목 생성."""
    paragraph_count = article["paragraphCount"]

    # preAssignedIds 생성 (paragraphCount + 단서 수)
    # 단서("다만,")가 별도 NS로 분리되므로 단서 수만큼 추가 ID 필요
    proviso_count = article["fullText"].count("다만,")
    max_ids = max(paragraph_count + proviso_count, 1)
    pre_assigned_ids = [
        generate_ns_id(law_id, article_code, seq)
        for seq in range(max_ids)
    ]

    # hasSanction 결정
    has_sanction = None
    if law_id == "RULE":
        route = penalties.get("routes", {}).get(article_code)
        if route:
            has_sanction = build_sanction_block(route)

    return {
        "articleCode": article_code,
        "lawId": law_id,
        "title": article["title"],
        "fullText": article["fullText"],
        "section": article["section"],
        "paragraphCount": paragraph_count,
        "deleted": article["deleted"],
        "preAssignedIds": pre_assigned_ids,
        "hasSanction": has_sanction,
    }


def main():
    parser = argparse.ArgumentParser(description="Step 2 배치 입력 생성")
    parser.add_argument("--articles", type=str, help="쉼표 구분 조문코드 (예: 제24조,제2조,제42조)")
    parser.add_argument("--law-id", type=str, default="RULE", help="법령 ID (기본: RULE)")
    parser.add_argument("--range", type=str, help="조문 번호 범위 (예: 3-50)")
    parser.add_argument("--all", action="store_true", help="해당 법령 전체 조문")
    parser.add_argument("--batch-id", type=str, help="배치 ID (예: batch-001)")
    parser.add_argument("--batch-size", type=int, default=20, help="--all 사용 시 배치 크기 (기본: 20)")
    parser.add_argument("--skip-deleted", action="store_true", default=True, help="삭제 조문 건너뜀 (기본: True)")
    args = parser.parse_args()

    articles_data, penalties_data = load_data()

    # 대상 조문 결정
    law_id = args.law_id
    law_articles = articles_data["laws"].get(law_id, {})

    if args.articles:
        target_codes = [c.strip() for c in args.articles.split(",")]
    elif args.range:
        start, end = map(int, args.range.split("-"))
        target_codes = [f"제{n}조" for n in range(start, end + 1) if f"제{n}조" in law_articles]
    elif args.all:
        target_codes = sorted(
            law_articles.keys(),
            key=lambda x: int("".join(filter(str.isdigit, x.split("조")[0].replace("제", ""))))
        )
    else:
        parser.error("--articles, --range, 또는 --all 중 하나를 지정하세요")
        return

    # 삭제 조문 필터링
    if args.skip_deleted:
        target_codes = [c for c in target_codes if not law_articles.get(c, {}).get("deleted", True)]

    if not target_codes:
        print("[ERROR] 대상 조문이 없습니다")
        sys.exit(1)

    # 배치 생성
    if args.all and not args.batch_id:
        # 전체 모드: 여러 배치 파일 생성
        batches = []
        for i in range(0, len(target_codes), args.batch_size):
            batch_codes = target_codes[i:i + args.batch_size]
            batch_num = (i // args.batch_size) + 1
            batch_id = f"batch-{batch_num:03d}"
            batches.append((batch_id, batch_codes))

        for batch_id, batch_codes in batches:
            batch_articles = []
            for code in batch_codes:
                art = law_articles.get(code)
                if art:
                    batch_articles.append(prepare_article(law_id, code, art, penalties_data))

            batch_output = {
                "batchId": batch_id,
                "lawId": law_id,
                "articles": batch_articles,
            }

            output_path = NS_DIR / f"{batch_id}-input.json"
            NS_DIR.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(batch_output, f, ensure_ascii=False, indent=2)
            print(f"[OK] {output_path.name}: {len(batch_articles)}조문")

        print(f"\n[DONE] {len(batches)}개 배치 생성 완료 (총 {len(target_codes)}조문)")

    else:
        # 단일 배치 모드
        batch_id = args.batch_id or "batch-001"
        batch_articles = []
        for code in target_codes:
            art = law_articles.get(code)
            if art:
                batch_articles.append(prepare_article(law_id, code, art, penalties_data))
            else:
                print(f"[WARN] {law_id}.{code} 없음 — 건너뜀")

        batch_output = {
            "batchId": batch_id,
            "lawId": law_id,
            "articles": batch_articles,
        }

        output_path = NS_DIR / f"{batch_id}-input.json"
        NS_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(batch_output, f, ensure_ascii=False, indent=2)

        print(f"[OK] {output_path.name}: {len(batch_articles)}조문")
        for art in batch_articles:
            ids = art["preAssignedIds"]
            sanction = "벌칙있음" if art["hasSanction"] else "벌칙없음"
            print(f"  {art['articleCode']} ({art['title']}): {art['paragraphCount']}항, IDs={ids[0]}~{ids[-1]}, {sanction}")

        print(f"\n[DONE] 배치 {batch_id} 생성 완료 ({len(batch_articles)}조문)")


if __name__ == "__main__":
    main()
