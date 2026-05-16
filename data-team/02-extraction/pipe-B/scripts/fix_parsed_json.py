#!/usr/bin/env python3
"""파싱된 가이드 JSON의 구조 불일치를 정규화하는 스크립트.

에이전트가 출력한 JSON이 guide-text-v2.schema.json과 다를 때 자동 수정한다.
수정 항목:
- metadata 래퍼 누락 시 생성
- guideCode, shortCode, totalPages 누락 시 인벤토리에서 보충
- tocSections 누락 시 sections에서 생성
- tocSections[].sectionTitle → title 변환
- sections[].title → sectionTitle 변환
- images[].figureNumber → imageNumber 변환
- sections[].number → sectionNumber 변환
- 스키마 외 필드 제거 (additionalProperties: false)
"""
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import validate, ValidationError

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from lib.paths import DATA_DIR, SCHEMA_DIR, PARSED_DIR, GUIDES_PDF

SCHEMA = json.loads((SCHEMA_DIR / "guide-text-v2.schema.json").read_text())
INV = json.loads((DATA_DIR / "guide-inventory.json").read_text())
GUIDES = INV if isinstance(INV, list) else INV.get("guides", INV)
INV_MAP = {g["shortCode"]: g for g in GUIDES}

METADATA_ALLOWED = {"guideCode", "shortCode", "title", "totalPages", "pdfPath", "parsedAt", "parsedBy", "tocSections"}
TOC_ALLOWED = {"sectionNumber", "title", "startPage"}
SECTION_ALLOWED = {"sectionNumber", "sectionTitle", "pages", "text", "tables", "images", "subsections"}
TABLE_ALLOWED = {"tableNumber", "caption", "content", "page"}
IMAGE_ALLOWED = {"imageNumber", "caption", "description", "page"}


def get_pdf_pages(pdf_path):
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return 0


def fix_section(sec):
    """섹션 구조 정규화 (재귀)."""
    # number → sectionNumber
    if "sectionNumber" not in sec and "number" in sec:
        sec["sectionNumber"] = str(sec.pop("number"))
    if "sectionNumber" not in sec and "id" in sec:
        sec["sectionNumber"] = str(sec.pop("id"))
    if "sectionNumber" not in sec:
        sec["sectionNumber"] = "?"
    # 빈 문자열 → "?" (minLength: 1 위반 방지)
    if not sec["sectionNumber"].strip():
        sec["sectionNumber"] = "?"

    # title → sectionTitle
    if "sectionTitle" not in sec and "title" in sec:
        sec["sectionTitle"] = sec.pop("title")
    if "sectionTitle" not in sec:
        sec["sectionTitle"] = sec.get("sectionNumber", "?")

    # pages 정규화: [None, None] 또는 null 포함 또는 길이≠2 → null
    if "pages" in sec and sec["pages"] is not None:
        if not isinstance(sec["pages"], list) or len(sec["pages"]) != 2 or any(p is None for p in sec["pages"]):
            sec["pages"] = None

    # 필수 필드 기본값
    sec.setdefault("text", "")
    sec.setdefault("tables", [])
    sec.setdefault("images", [])

    # images 정규화
    for img in sec.get("images", []):
        if "imageNumber" not in img:
            img["imageNumber"] = img.pop("figureNumber", img.pop("imageIndex", img.pop("number", img.pop("id", None))))
        # int → str 변환
        if isinstance(img.get("imageNumber"), (int, float)):
            img["imageNumber"] = str(int(img["imageNumber"]))
        img.setdefault("caption", None)
        # 스키마 외 필드 제거
        for k in list(img.keys()):
            if k not in IMAGE_ALLOWED:
                del img[k]

    # tables 정규화 — 빈 content 테이블 제거
    tables = sec.get("tables", [])
    cleaned_tables = []
    for tbl in tables:
        # tableIndex → tableNumber
        if "tableNumber" not in tbl and "tableIndex" in tbl:
            tbl["tableNumber"] = str(tbl.pop("tableIndex"))
        tbl.setdefault("tableNumber", None)
        # int → str 변환
        if isinstance(tbl.get("tableNumber"), (int, float)):
            tbl["tableNumber"] = str(int(tbl["tableNumber"]))
        tbl.setdefault("caption", None)
        tbl.setdefault("content", "")
        # headers+rows → markdown content 변환
        if not tbl.get("content", "").strip() and "headers" in tbl:
            headers = tbl.pop("headers", [])
            rows = tbl.pop("rows", [])
            if headers and rows:
                lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
                lines.append("|" + "|".join(["---"] * len(headers)) + "|")
                for row in rows:
                    lines.append("| " + " | ".join(str(c) for c in row) + " |")
                tbl["content"] = "\n".join(lines)
        # minLength: 1 위반하는 빈 content → 테이블 자체 제거
        if not tbl["content"].strip():
            continue
        for k in list(tbl.keys()):
            if k not in TABLE_ALLOWED:
                del tbl[k]
        cleaned_tables.append(tbl)
    sec["tables"] = cleaned_tables

    # subsections 재귀
    for sub in sec.get("subsections", []):
        fix_section(sub)

    # 스키마 외 필드 제거
    for k in list(sec.keys()):
        if k not in SECTION_ALLOWED:
            del sec[k]


def fix_document(doc, shortCode):
    """전체 문서 구조 정규화."""
    guide = INV_MAP.get(shortCode, {})

    # 1. metadata 래퍼 누락 처리
    if "metadata" not in doc:
        metadata = {}
        for k in list(doc.keys()):
            if k != "sections":
                metadata[k] = doc.pop(k)
        doc["metadata"] = metadata

    m = doc["metadata"]

    # 2. 인벤토리에서 필수 메타데이터 보충
    if not m.get("guideCode") and guide:
        m["guideCode"] = guide["guideCode"]
    if not m.get("shortCode"):
        m["shortCode"] = shortCode
    if not m.get("title") and guide:
        m["title"] = guide["title"]
    if not m.get("totalPages"):
        if guide:
            pdf_path = GUIDES_PDF / guide["pdfPath"]
            m["totalPages"] = get_pdf_pages(pdf_path)
    if not m.get("pdfPath") and guide:
        m["pdfPath"] = f"kosha-guides/{guide['pdfPath']}"
    m.setdefault("parsedBy", "step2-text-extraction v2.0")
    m.setdefault("parsedAt", datetime.now(timezone.utc).isoformat())

    # 3. tocSections 정규화
    if "tocSections" not in m or not m["tocSections"]:
        # sections에서 생성
        toc = []
        for s in doc.get("sections", []):
            entry = {
                "sectionNumber": s.get("sectionNumber", s.get("number", s.get("id", "?"))),
                "title": s.get("sectionTitle", s.get("title", "?")),
            }
            toc.append(entry)
        m["tocSections"] = toc if toc else [{"sectionNumber": "1", "title": "본문"}]

    for toc in m["tocSections"]:
        # sectionTitle → title
        if "title" not in toc and "sectionTitle" in toc:
            toc["title"] = toc.pop("sectionTitle")
        if "title" not in toc:
            toc["title"] = toc.get("sectionNumber", "?")
        toc.setdefault("sectionNumber", "?")
        # 빈 sectionNumber → "?"
        if not toc["sectionNumber"].strip():
            toc["sectionNumber"] = "?"
        # startPage: 없으면 생략 (null 허용)
        if "startPage" not in toc:
            toc["startPage"] = None
        # 스키마 외 필드 제거
        for k in list(toc.keys()):
            if k not in TOC_ALLOWED:
                del toc[k]

    # 4. sections 정규화
    for sec in doc.get("sections", []):
        fix_section(sec)

    # 5. metadata 스키마 외 필드 제거
    for k in list(m.keys()):
        if k not in METADATA_ALLOWED:
            del m[k]

    # 6. 최상위 스키마 외 필드 제거
    for k in list(doc.keys()):
        if k not in ("metadata", "sections"):
            del doc[k]

    return doc


def main():
    import argparse
    parser = argparse.ArgumentParser(description="파싱된 가이드 JSON 구조 정규화")
    parser.add_argument("files", nargs="*", help="정규화할 JSON 파일 (미지정 시 전체)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        paths = sorted(PARSED_DIR.glob("guide-*.json"))

    fixed = 0
    passed = 0
    failed = 0

    for p in paths:
        sc = p.stem.replace("guide-", "")
        if "-opus" in sc or "-sonnet" in sc or "-part" in sc:
            continue

        doc = json.loads(p.read_text(encoding="utf-8"))

        # 정규화 전 검증
        try:
            validate(doc, SCHEMA)
            passed += 1
            continue
        except ValidationError:
            pass

        # 정규화
        doc = fix_document(doc, sc)

        # 정규화 후 검증
        try:
            validate(doc, SCHEMA)
            if not args.dry_run:
                p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            fixed += 1
            print(f"  FIXED: {sc}")
        except ValidationError as e:
            failed += 1
            print(f"  FAIL:  {sc} — {e.message[:100]}")

    print(f"\n총 {len(paths)}개: passed={passed} fixed={fixed} failed={failed}")


if __name__ == "__main__":
    main()
