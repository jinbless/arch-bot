#!/usr/bin/env python3
"""Step 0 (.md): legalize-kr Markdown에서 조문 추출 → article-texts.json

legalize-kr 업스트림이 JSON→Markdown으로 전환되어 기존 step0_extract_articles.py
(JSON reader)를 대체한다. 의N(제N조의M) 하위조항을 보존하며, 동일 커밋 → 동일 출력.

구 파이프라인 버그: 의N이 base 코드로 붕괴되어 silent overwrite → 의N 누락 + base 오염.
신 파이프라인: legalize_md_reader가 의N 보존 + 중복 코드 DuplicateArticleError로 차단.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
SCHEMA_DIR = PROJECT_ROOT / "schemas"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SCRIPT_DIR))
from lib.legalize_md_reader import parse_law_file
from lib.schema_validator import validate_and_write


def get_git_commit(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_path,
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main():
    with open(CONFIG_DIR / "law-sources.json", encoding="utf-8") as f:
        law_sources = json.load(f)

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
        articles = parse_law_file(law_path, law_id)

        active = sum(1 for a in articles.values() if not a["deleted"])
        deleted = sum(1 for a in articles.values() if a["deleted"])
        sub = sum(1 for c in articles if "조의" in c)
        print(f"  → {len(articles)}조 추출 (활성 {active}, 삭제 {deleted}, 의N {sub})")

        all_laws[law_id] = articles
        total_articles += len(articles)
        total_deleted += deleted
        source_info[law_id] = {
            "name": source["name"],
            "path": source["path"],
            "articleCount": len(articles),
        }

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
