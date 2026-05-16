#!/usr/bin/env python3
"""
fix_parsed_schema.py — v1 파싱 결과를 v2 스키마에 맞게 자동 보정.

용도: guide-text-v2.schema.json 검증 실패한 파싱 JSON을 자동 수정.
입력: data-team/01-parsing/kosha-guides/parsed/guide-{shortCode}.json
출력: 같은 파일 덮어쓰기 (--dry-run 시 변경 내역만 출력)

보정 규칙:
  R1. images: imageId/imageIndex → imageNumber
  R2. images: caption 누락 → null
  R3. images: extractedData, pageNumber, title(이미지) 등 추가 속성 제거
  R4. tables: tableIndex → tableNumber, headers/rows → content 변환
  R5. tables: caption/content 누락 → null/자동생성
  R6. sections: pages [] → null (빈 배열 → null)
  R7. metadata.tocSections: sectionNumber "" → "N/A"
  R8. subsections: tables/images 누락 → []
  R9. sections: sectionNumber "" → "N/A"
"""

import argparse
import json
import os
import sys
import copy

# 허용된 image 속성
IMAGE_ALLOWED = {"imageNumber", "caption", "description", "page"}
# 허용된 table 속성
TABLE_ALLOWED = {"tableNumber", "caption", "content", "page"}


def fix_image(img: dict, changes: list, path: str) -> dict:
    """이미지 객체를 v2 스키마에 맞게 보정."""
    if not isinstance(img, dict):
        return img
    # R1. imageId/imageIndex → imageNumber
    if "imageNumber" not in img:
        if "imageId" in img:
            img["imageNumber"] = img.pop("imageId")
            changes.append(f"  {path}: imageId → imageNumber")
        elif "imageIndex" in img:
            img["imageNumber"] = str(img.pop("imageIndex")) if isinstance(img.get("imageIndex"), int) else img.pop("imageIndex")
            changes.append(f"  {path}: imageIndex → imageNumber")
        else:
            img["imageNumber"] = None
            changes.append(f"  {path}: imageNumber 추가 (null)")

    # R2. caption 누락 → null
    if "caption" not in img:
        if "title" in img:
            img["caption"] = img.pop("title")
            changes.append(f"  {path}: title → caption")
        else:
            img["caption"] = None
            changes.append(f"  {path}: caption 추가 (null)")

    # R3. 추가 속성 제거
    extra_keys = set(img.keys()) - IMAGE_ALLOWED
    for k in extra_keys:
        del img[k]
        changes.append(f"  {path}: 추가속성 '{k}' 제거")

    return img


def fix_table(tbl: dict, changes: list, path: str) -> dict:
    """테이블 객체를 v2 스키마에 맞게 보정."""
    if not isinstance(tbl, dict):
        return tbl
    # R4. tableIndex → tableNumber
    if "tableNumber" not in tbl:
        if "tableIndex" in tbl:
            tbl["tableNumber"] = str(tbl.pop("tableIndex")) if isinstance(tbl.get("tableIndex"), int) else tbl.pop("tableIndex")
            changes.append(f"  {path}: tableIndex → tableNumber")
        else:
            tbl["tableNumber"] = None
            changes.append(f"  {path}: tableNumber 추가 (null)")

    # R5. caption 누락
    if "caption" not in tbl:
        tbl["caption"] = None
        changes.append(f"  {path}: caption 추가 (null)")

    # R5. content 누락 — headers/rows 변환
    if "content" not in tbl:
        if "headers" in tbl and "rows" in tbl:
            # Markdown 테이블로 변환
            headers = tbl.pop("headers")
            rows = tbl.pop("rows")
            lines = []
            if headers:
                lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                if isinstance(row, list):
                    lines.append("| " + " | ".join(str(c) for c in row) + " |")
                elif isinstance(row, dict):
                    lines.append("| " + " | ".join(str(v) for v in row.values()) + " |")
            tbl["content"] = "\n".join(lines) if lines else "(표 내용 없음)"
            changes.append(f"  {path}: headers/rows → content (markdown)")
        else:
            tbl["content"] = "(표 내용 없음)"
            changes.append(f"  {path}: content 추가 (placeholder)")

    # 추가 속성 제거
    extra_keys = set(tbl.keys()) - TABLE_ALLOWED
    for k in extra_keys:
        del tbl[k]
        changes.append(f"  {path}: 추가속성 '{k}' 제거")

    return tbl


def fix_section(sec: dict, changes: list, path: str) -> dict:
    """섹션 객체를 v2 스키마에 맞게 보정 (재귀)."""
    # R9. sectionNumber "" → "N/A"
    if sec.get("sectionNumber") == "":
        sec["sectionNumber"] = "N/A"
        changes.append(f"  {path}: sectionNumber '' → 'N/A'")

    # R6. pages [] → null
    if "pages" in sec and isinstance(sec["pages"], list) and len(sec["pages"]) == 0:
        sec["pages"] = None
        changes.append(f"  {path}: pages [] → null")

    # pages가 1개짜리 배열이면 [start, start]로 보정
    if "pages" in sec and isinstance(sec["pages"], list) and len(sec["pages"]) == 1:
        sec["pages"] = [sec["pages"][0], sec["pages"][0]]
        changes.append(f"  {path}: pages [x] → [x, x]")

    # R8. tables/images 누락 → []
    if "tables" not in sec:
        sec["tables"] = []
        changes.append(f"  {path}: tables 추가 ([])")
    if "images" not in sec:
        sec["images"] = []
        changes.append(f"  {path}: images 추가 ([])")

    # sectionTitle 누락
    if "sectionTitle" not in sec:
        sec["sectionTitle"] = sec.get("title", "N/A")
        if "title" in sec and "sectionTitle" not in {"title"}:
            pass  # title은 section에서 허용되지 않을 수 있으므로 나중에 제거
        changes.append(f"  {path}: sectionTitle 추가")

    # text 누락
    if "text" not in sec:
        sec["text"] = ""
        changes.append(f"  {path}: text 추가 ('')")

    # Fix images
    sec["images"] = [img for img in sec["images"] if isinstance(img, dict)]
    for i, img in enumerate(sec["images"]):
        fix_image(img, changes, f"{path}.images[{i}]")

    # Fix tables
    sec["tables"] = [tbl for tbl in sec["tables"] if isinstance(tbl, dict)]
    for i, tbl in enumerate(sec["tables"]):
        fix_table(tbl, changes, f"{path}.tables[{i}]")

    # 재귀: subsections
    if "subsections" in sec:
        sec["subsections"] = [sub for sub in sec["subsections"] if isinstance(sub, dict)]
        for i, sub in enumerate(sec["subsections"]):
            fix_section(sub, changes, f"{path}.subsections[{i}]")

    # 허용 속성만 남기기 (section)
    section_allowed = {"sectionNumber", "sectionTitle", "pages", "text", "tables", "images", "subsections"}
    extra_keys = set(sec.keys()) - section_allowed
    for k in extra_keys:
        del sec[k]
        changes.append(f"  {path}: 추가속성 '{k}' 제거")

    return sec


def fix_guide(data: dict) -> tuple:
    """가이드 JSON 전체를 보정. (data, changes) 반환."""
    changes = []

    # metadata 보정
    meta = data.get("metadata", {})

    # R7. tocSections sectionNumber "" → "N/A"
    for i, toc in enumerate(meta.get("tocSections", [])):
        if not isinstance(toc, dict):
            continue
        if toc.get("sectionNumber") == "":
            toc["sectionNumber"] = "N/A"
            changes.append(f"  metadata.tocSections[{i}]: sectionNumber '' → 'N/A'")
        # tocSections 추가속성 제거
        toc_allowed = {"sectionNumber", "title", "startPage"}
        for k in list(toc.keys()):
            if k not in toc_allowed:
                del toc[k]
                changes.append(f"  metadata.tocSections[{i}]: 추가속성 '{k}' 제거")

    # metadata 추가속성 제거
    meta_allowed = {"guideCode", "shortCode", "title", "totalPages", "pdfPath", "parsedAt", "parsedBy", "tocSections"}
    for k in list(meta.keys()):
        if k not in meta_allowed:
            del meta[k]
            changes.append(f"  metadata: 추가속성 '{k}' 제거")

    # sections 보정
    for i, sec in enumerate(data.get("sections", [])):
        fix_section(sec, changes, f"sections[{i}]")

    # 최상위 추가속성 제거
    top_allowed = {"metadata", "sections"}
    for k in list(data.keys()):
        if k not in top_allowed:
            del data[k]
            changes.append(f"  root: 추가속성 '{k}' 제거")

    return data, changes


def main():
    parser = argparse.ArgumentParser(description="파싱 JSON을 v2 스키마에 맞게 보정")
    parser.add_argument("--guides-file", default="data/pilot-guides.json",
                        help="파일럿 가이드 목록 JSON (default: data/pilot-guides.json)")
    parser.add_argument("--guide", type=str, help="단일 가이드 shortCode")
    parser.add_argument("--dry-run", action="store_true", help="변경 사항만 출력, 파일 수정 안 함")
    parser.add_argument("--verbose", action="store_true", help="모든 변경 상세 출력")
    args = parser.parse_args()

    # 스크립트 위치 기준 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # pipe-B/
    repo_root = os.path.dirname(project_root)   # koshaontology/
    base_root = os.path.dirname(repo_root)      # arch-bot/

    # 보정 대상 가이드 목록
    if args.guide:
        short_codes = [args.guide]
    else:
        guides_path = os.path.join(project_root, args.guides_file)
        with open(guides_path) as f:
            pilot = json.load(f)
        short_codes = [g["shortCode"] for g in pilot["guides"]]

    total_changes = 0
    results = []

    for sc in short_codes:
        parsed_path = os.path.join(base_root, "kosha-guides", "parsed", f"guide-{sc}.json")
        if not os.path.exists(parsed_path):
            print(f"[SKIP] {sc}: 파일 없음")
            results.append({"shortCode": sc, "status": "SKIP", "changes": 0})
            continue

        try:
            with open(parsed_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[ERR]  {sc}: JSON 파싱 실패 ({e})")
            results.append({"shortCode": sc, "status": "JSON_ERROR", "changes": 0})
            continue

        original = copy.deepcopy(data)
        fixed, changes = fix_guide(data)

        if not changes:
            print(f"[OK]   {sc}: 변경 없음")
            results.append({"shortCode": sc, "status": "OK", "changes": 0})
            continue

        total_changes += len(changes)
        results.append({"shortCode": sc, "status": "FIXED", "changes": len(changes)})
        print(f"[FIX]  {sc}: {len(changes)}건 보정")

        if args.verbose:
            for c in changes:
                print(c)

        if not args.dry_run:
            with open(parsed_path, "w") as f:
                json.dump(fixed, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(short_codes)}개 가이드, {total_changes}건 보정" +
          (" (dry-run)" if args.dry_run else ""))

    return results


if __name__ == "__main__":
    main()
