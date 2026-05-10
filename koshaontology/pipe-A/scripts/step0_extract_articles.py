#!/usr/bin/env python3
"""Step 0: legalize-kr에서 조문 추출 → article-texts.json

100% 결정론적 스크립트. LLM 불필요.
동일 legalize-kr 커밋 → 동일 출력 보장.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트 기준 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from lib.legalize_reader import load_law_json, extract_articles
from lib.schema_validator import validate_and_write


def get_git_commit(repo_path: Path) -> str:
    """legalize-kr의 현재 git commit hash를 반환."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main():
    # 1. config 로드
    with open(CONFIG_DIR / "law-sources.json", encoding="utf-8") as f:
        law_sources = json.load(f)

    # 2. 각 법령에서 조문 추출
    all_laws = {}
    total_articles = 0
    total_deleted = 0
    source_info = {}
    legalize_kr_path = None

    for law_id, source in sorted(law_sources.items()):
        law_path = (PROJECT_ROOT / source["path"]).resolve()
        if legalize_kr_path is None:
            legalize_kr_path = law_path.parent.parent.parent  # legalize-kr root

        print(f"[{law_id}] 로딩: {law_path.name}")
        law_json = load_law_json(law_path)
        articles = extract_articles(law_json, law_id)

        active = sum(1 for a in articles.values() if not a["deleted"])
        deleted = sum(1 for a in articles.values() if a["deleted"])
        print(f"  → {len(articles)}조 추출 (활성 {active}, 삭제 {deleted})")

        all_laws[law_id] = articles
        total_articles += len(articles)
        total_deleted += deleted
        source_info[law_id] = {
            "name": source["name"],
            "path": source["path"],
            "articleCount": len(articles),
        }

    # 3. 출력 데이터 구성
    source_commit = get_git_commit(legalize_kr_path) if legalize_kr_path else "unknown"

    output = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sourceCommit": source_commit,
            "totalArticles": total_articles,
            "deletedArticles": total_deleted,
            "lawSources": source_info,
        },
        "laws": all_laws,
    }

    # 4. 스키마 검증 후 저장
    schema_path = SCHEMA_DIR / "article-texts.schema.json"
    output_path = DATA_DIR / "article-texts.json"

    errors = validate_and_write(output, schema_path, output_path)
    if errors:
        print(f"\n[FAIL] 스키마 검증 실패 ({len(errors)}건)")
        sys.exit(1)

    print(f"\n[DONE] article-texts.json 생성 완료")
    print(f"  총 조문: {total_articles} (활성 {total_articles - total_deleted}, 삭제 {total_deleted})")
    print(f"  소스 커밋: {source_commit[:8]}")


if __name__ == "__main__":
    main()
