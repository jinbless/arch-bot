#!/usr/bin/env python3
"""P2-Step 2: CI 배치 입력 생성.

각 가이드의 텍스트 JSON에서 인용 조문을 추출하고, SR 인덱스로 candidateSR을 계산하여
배치 입력 JSON을 생성한다.

Usage:
    python3 scripts/step3_prepare_ci_batch.py --domain D --batch-size 5
    python3 scripts/step3_prepare_ci_batch.py  # 전체 도메인
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 경로 설정 ──
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, BATCHES_DIR, PARSED_DIR, REPO_ROOT

# 레거시 참조 (shared/ 구버전 체크리스트 — 참고용)
LEGACY_DIR = REPO_ROOT / "shared" / "output" / "checklists"

# ── 인용 조문 추출 패턴 ──
# "제42조", "제42조의2", "제42조제1항" 등
_ARTICLE_RE = re.compile(r"제(\d+)조(?:의(\d+))?")

# SR 인덱스 키: "RULE:42" 형식
_LAW_TYPES = ["RULE", "OSHA", "SADA", "DECREE", "ENFORCE"]

MAX_CANDIDATE_SR = 50


def extract_cited_articles(text: str) -> list[str]:
    """텍스트에서 인용 조문을 추출.

    Returns: ["제42조", "제42조의2", ...] (중복 제거, 정렬)
    """
    articles = set()
    for m in _ARTICLE_RE.finditer(text):
        base = f"제{m.group(1)}조"
        if m.group(2):
            base += f"의{m.group(2)}"
        articles.add(base)
    return sorted(articles)


def article_to_index_keys(article: str) -> list[str]:
    """인용 조문을 SR 인덱스 키로 변환.

    "제42조" → ["RULE:42", "OSHA:42", ...]
    "제42조의2" → ["RULE:42-2", "OSHA:42-2", ...]
    """
    m = re.match(r"제(\d+)조(?:의(\d+))?", article)
    if not m:
        return []

    code = m.group(1)
    if m.group(2):
        code += f"-{m.group(2)}"

    return [f"{lt}:{code}" for lt in _LAW_TYPES]


def compute_candidate_sr(
    cited_articles: list[str],
    domain: str,
    article_index: dict,
    category_index: dict,
    keyword_index: dict,
    guide_text: str = "",
) -> list[dict]:
    """3단계 narrowing으로 candidateSR 계산.

    1. 인용 조문 → sr-article-index → 1차 후보
    2. 도메인 키워드 → sr-keyword-index → 2차 보충
    3. 중복 제거, 최대 MAX_CANDIDATE_SR개
    """
    candidates = {}  # sr_id → {id, title, sources[]}

    # 1단계: 인용 조문으로 SR 후보 추출
    for article in cited_articles:
        for key in article_to_index_keys(article):
            entry = article_index.get(key)
            if entry:
                for sr_id in entry["srIds"]:
                    if sr_id not in candidates:
                        candidates[sr_id] = {
                            "id": sr_id,
                            "title": "",
                            "source": "article",
                            "referencesArticle": [],
                        }
                    candidates[sr_id]["referencesArticle"].append(article)

    # SR 제목 매핑 (keyword_index의 srList에서 가져옴)
    sr_title_map = {}
    if "srList" in keyword_index:
        for sr in keyword_index["srList"]:
            sr_title_map[sr["identifier"]] = sr["title"]

    for sr_id, info in candidates.items():
        info["title"] = sr_title_map.get(sr_id, "")

    # 2단계: 카테고리 보충 (hazard 카테고리 기반)
    if len(candidates) < MAX_CANDIDATE_SR and guide_text:
        # hazard 카테고리 키워드 매핑
        _CATEGORY_KEYWORDS = {
            "FALL": ["추락", "낙하", "개구부", "비계", "사다리"],
            "ELECTRICAL": ["감전", "전기", "배선", "접지", "누전"],
            "CAUGHT_IN": ["끼임", "협착", "물림"],
            "STRUCK_BY": ["충돌", "낙하물", "비래"],
            "COLLAPSE": ["붕괴", "전도", "도괴"],
            "FIRE_EXPLOSION": ["화재", "폭발", "인화"],
            "SUFFOCATION": ["질식", "산소결핍", "밀폐"],
            "CHEMICAL": ["유해물질", "화학물질", "중독"],
            "CUTTING": ["절단", "베임", "찔림"],
            "OVEREXERTION": ["근골격", "중량물", "과로"],
            "HEAT_COLD": ["온도", "열사병", "동상"],
            "NOISE_VIBRATION": ["소음", "진동"],
        }
        for cat_name, cat_keywords in _CATEGORY_KEYWORDS.items():
            if any(kw in guide_text for kw in cat_keywords):
                cat_entry = category_index.get(cat_name, {})
                for sr_id in cat_entry.get("srIds", [])[:5]:
                    if sr_id not in candidates:
                        candidates[sr_id] = {
                            "id": sr_id,
                            "title": sr_title_map.get(sr_id, ""),
                            "source": "category",
                            "referencesArticle": [],
                        }
                    if len(candidates) >= MAX_CANDIDATE_SR:
                        break
            if len(candidates) >= MAX_CANDIDATE_SR:
                break

    # 3단계: 키워드 보충 (후보가 여전히 부족한 경우)
    if len(candidates) < 15 and guide_text:
        kw_index = keyword_index.get("index", {})
        for kw, kw_entry in kw_index.items():
            if re.search(kw, guide_text):
                for sr_id in kw_entry["srIds"][:5]:
                    if sr_id not in candidates:
                        candidates[sr_id] = {
                            "id": sr_id,
                            "title": sr_title_map.get(sr_id, ""),
                            "source": "keyword",
                            "referencesArticle": [],
                        }
                    if len(candidates) >= MAX_CANDIDATE_SR:
                        break
            if len(candidates) >= MAX_CANDIDATE_SR:
                break

    # 최대 개수 제한
    result = list(candidates.values())[:MAX_CANDIDATE_SR]
    return result


def get_guide_full_text(parsed_path: Path) -> str:
    """guide-text JSON에서 전체 텍스트를 추출."""
    if not parsed_path.exists():
        return ""
    try:
        doc = json.loads(parsed_path.read_text(encoding="utf-8"))
        texts = []
        for s in doc.get("sections", []):
            texts.append(s.get("text", ""))
            for sub in s.get("subsections", []):
                texts.append(sub.get("text", ""))
        return "\n".join(t for t in texts if isinstance(t, str))
    except Exception:
        return ""


def find_legacy_reference(short_code: str) -> str | None:
    """legacy CI 파일 경로 탐색."""
    if not LEGACY_DIR.exists():
        return None
    for pattern in [f"cl-{short_code}-*.json", f"*-{short_code}-*.json"]:
        matches = list(LEGACY_DIR.glob(pattern))
        if matches:
            return str(matches[0].relative_to(REPO_ROOT))
    return None


def main():
    parser = argparse.ArgumentParser(description="CI 배치 입력 생성")
    parser.add_argument("--domain", type=str, help="특정 도메인만 (A/B/C/D/E)")
    parser.add_argument("--batch-size", type=int, default=5, help="배치당 가이드 수 (기본: 5)")
    parser.add_argument("--guides-file", type=str, help="특정 가이드 목록 JSON (pilot-guides.json 등)")
    parser.add_argument("--batch-prefix", type=str, default="pipeb-batch", help="배치 ID 접두사 (기본: pipeb-batch)")
    args = parser.parse_args()

    print("[START] CI 배치 입력 생성")

    # 데이터 로드
    inventory = json.loads((DATA_DIR / "guide-inventory.json").read_text(encoding="utf-8"))
    guides = inventory["guides"]

    article_index_data = json.loads((DATA_DIR / "sr-article-index.json").read_text(encoding="utf-8"))
    article_index = article_index_data["index"]

    category_index_data = json.loads((DATA_DIR / "sr-category-index.json").read_text(encoding="utf-8"))
    category_index = category_index_data["index"]

    keyword_index_data = json.loads((DATA_DIR / "sr-keyword-index.json").read_text(encoding="utf-8"))

    # 가이드 필터 (--guides-file 우선)
    pilot_short_codes = None
    if args.guides_file:
        gf_path = Path(args.guides_file)
        if not gf_path.is_absolute():
            gf_path = DATA_DIR.parent / gf_path
        pilot_data = json.loads(gf_path.read_text(encoding="utf-8"))
        pilot_short_codes = {g["shortCode"] for g in pilot_data["guides"]}
        print(f"  파일럿 모드: {len(pilot_short_codes)}개 가이드만 처리")

    # 도메인 필터
    processing_order = inventory["metadata"]["processingOrder"]
    if args.domain:
        processing_order = [args.domain.upper()]

    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    total_batches = 0
    total_guides_processed = 0

    for domain in processing_order:
        domain_guides = [g for g in guides if g["domain"] == domain]
        if pilot_short_codes:
            domain_guides = [g for g in domain_guides if g["shortCode"] in pilot_short_codes]
        if not domain_guides:
            continue

        print(f"\n  [{domain}] {len(domain_guides)}개 가이드")

        # 크기별 분류 (parsed 파일의 totalPages 기준)
        small, medium, large = [], [], []
        for g in domain_guides:
            parsed_path = PARSED_DIR / f"guide-{g['shortCode']}.json"
            pages = 10  # 기본값 (파싱 전)
            if parsed_path.exists():
                try:
                    doc = json.loads(parsed_path.read_text(encoding="utf-8"))
                    pages = doc.get("metadata", {}).get("totalPages", 10)
                except Exception:
                    pass

            if pages <= 15:
                small.append(g)
            elif pages <= 40:
                medium.append(g)
            else:
                large.append(g)

        print(f"    소형({len(small)}) 중형({len(medium)}) 대형({len(large)})")

        # 배치 생성
        def make_batches(guide_list, batch_size):
            for i in range(0, len(guide_list), batch_size):
                yield guide_list[i:i + batch_size]

        batch_num = 1
        all_batches_for_domain = []

        # 소형: 기본 batch-size
        for batch_guides in make_batches(small, args.batch_size):
            all_batches_for_domain.append(batch_guides)

        # 중형: batch-size의 60%
        med_size = max(1, int(args.batch_size * 0.6))
        for batch_guides in make_batches(medium, med_size):
            all_batches_for_domain.append(batch_guides)

        # 대형: 1개씩
        for g in large:
            all_batches_for_domain.append([g])

        for batch_guides in all_batches_for_domain:
            batch_id = f"{args.batch_prefix}-{domain}-{batch_num:03d}"
            batch_entries = []

            for g in batch_guides:
                sc = g["shortCode"]
                parsed_path = PARSED_DIR / f"guide-{sc}.json"
                full_text = get_guide_full_text(parsed_path)

                # 인용 조문 추출
                cited = extract_cited_articles(full_text)

                # candidateSR 계산
                candidate_sr = compute_candidate_sr(
                    cited, domain, article_index,
                    category_index, keyword_index_data,
                    guide_text=full_text,
                )

                # preAssignedId 범위 (가이드당 최대 200개 CI)
                pre_assigned = {
                    "start": f"CI-{sc}-001",
                    "end": f"CI-{sc}-200",
                }

                # legacy 참조
                legacy_ref = find_legacy_reference(sc)

                batch_entries.append({
                    "guideCode": g["guideCode"],
                    "shortCode": sc,
                    "title": g["title"],
                    "textJsonPath": f"data-team/01-parsing/kosha-guides/parsed/guide-{sc}.json",
                    "citedArticles": cited,
                    "candidateSR": candidate_sr,
                    "preAssignedIdRange": pre_assigned,
                    "legacyReference": legacy_ref,
                })

            batch_data = {
                "metadata": {
                    "batchId": batch_id,
                    "domain": domain,
                    "guideCount": len(batch_entries),
                    "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
                "guides": batch_entries,
            }

            fp = BATCHES_DIR / f"{batch_id}-input.json"
            fp.write_text(json.dumps(batch_data, ensure_ascii=False, indent=2), encoding="utf-8")

            total_batches += 1
            total_guides_processed += len(batch_entries)
            batch_num += 1

        print(f"    배치 {batch_num - 1}개 생성")

    print(f"\n[DONE] 배치 생성 완료")
    print(f"  총 배치: {total_batches}개")
    print(f"  총 가이드: {total_guides_processed}개")
    print(f"  출력 디렉토리: {BATCHES_DIR}")


if __name__ == "__main__":
    main()
