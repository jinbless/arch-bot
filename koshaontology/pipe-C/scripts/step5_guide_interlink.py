#!/usr/bin/env python3
"""P-C Step 5: GuideInterLink — 가이드 간 상호참조 탐지.

파싱된 가이드 JSON 텍스트에서 다른 가이드를 참조하는 패턴을 regex로 탐지.

Usage:
    python3 scripts/step5_guide_interlink.py
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, PARSED_DIR, PG_CONNINFO

import psycopg2

# 가이드 참조 패턴
GUIDE_REF_PATTERNS = [
    # "KOSHA GUIDE C-47-2014", "KOSHA 가이드 A-G-4-2025"
    re.compile(r"KOSHA\s*(?:GUIDE|가이드)\s*([A-Z][\-\s]*[A-Z]?[\-\s]*\d+[\-\s]*\d{4})", re.IGNORECASE),
    # "C-47-2014", "D-C-13-2026" 형태 (가이드 코드 직접)
    re.compile(r"(?:참조|참고|관련)\s*[:：]?\s*([A-Z]-[A-Z]?-?\d+-\d{4})"),
    # "코샤가이드 C-47"
    re.compile(r"코샤\s*가이드\s*([A-Z][\-\s]*[A-Z]?[\-\s]*\d+)", re.IGNORECASE),
]


def extract_full_text(doc: dict) -> str:
    """파싱 JSON에서 전체 텍스트 추출."""
    texts = []

    def visit(section):
        texts.append(section.get("text", ""))
        for t in section.get("tables", []):
            if isinstance(t, dict):
                texts.append(t.get("content", ""))
                texts.append(t.get("caption", ""))
        for sub in section.get("subsections", []):
            visit(sub)

    for s in doc.get("sections", []):
        visit(s)

    return "\n".join(str(t) for t in texts if t)


def normalize_guide_code(raw: str) -> str:
    """참조 패턴에서 추출한 문자열을 정규 guideCode로 변환."""
    # 공백 제거, 하이픈 정규화
    raw = re.sub(r'\s+', '', raw)
    raw = re.sub(r'-+', '-', raw)
    return raw.upper()


def main():
    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor()

    print("[START] GuideInterLink 탐지 (Pipe-C Step 5)")

    # 가이드 코드 → shortCode 매핑 로드
    cur.execute("SELECT guide_code, short_code FROM kosha_guides")
    gc_to_sc = {}
    all_guide_codes = set()
    for gc, sc in cur.fetchall():
        gc_to_sc[gc] = sc
        all_guide_codes.add(gc)
    conn.close()

    # 인벤토리에서 전체 가이드 코드 로드 (DB에 없는 것도 포함)
    inv_path = Path(__file__).resolve().parent.parent.parent / "pipe-B" / "data" / "guide-inventory.json"
    if inv_path.exists():
        inv = json.loads(inv_path.read_text())
        for g in inv.get("guides", []):
            gc = g["guideCode"]
            sc = g["shortCode"]
            gc_to_sc[gc] = sc
            all_guide_codes.add(gc)

    # 파싱된 가이드 스캔
    parsed_files = sorted(PARSED_DIR.glob("guide-*.json"))
    print(f"  파싱 가이드 수: {len(parsed_files)}")

    links = []
    guide_ref_counts = defaultdict(int)

    for pf in parsed_files:
        source_sc = pf.stem.replace("guide-", "")
        try:
            doc = json.loads(pf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        full_text = extract_full_text(doc)

        for pattern in GUIDE_REF_PATTERNS:
            for m in pattern.finditer(full_text):
                raw_ref = m.group(1)
                ref_code = normalize_guide_code(raw_ref)

                # 자기 참조 제외
                ref_sc = gc_to_sc.get(ref_code)
                if not ref_sc:
                    # 부분 매칭 시도 (년도 없는 코드)
                    for gc in all_guide_codes:
                        if gc.startswith(ref_code) or ref_code in gc:
                            ref_sc = gc_to_sc.get(gc)
                            break
                if not ref_sc or ref_sc == source_sc:
                    continue

                # 중복 방지
                link_key = (source_sc, ref_sc)
                if not any(l["sourceGuide"] == source_sc and l["referencedGuide"] == ref_sc for l in links):
                    context_start = max(0, m.start() - 30)
                    context_end = min(len(full_text), m.end() + 30)
                    links.append({
                        "sourceGuide": source_sc,
                        "referencedGuide": ref_sc,
                        "referenceType": "explicit",
                        "referenceText": full_text[context_start:context_end].strip(),
                        "rawMatch": raw_ref,
                    })
                    guide_ref_counts[source_sc] += 1

    # 보고서
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalParsedGuides": len(parsed_files),
        "totalLinks": len(links),
        "guidesWithReferences": len(guide_ref_counts),
        "topReferrers": sorted(
            [{"guide": k, "refCount": v} for k, v in guide_ref_counts.items()],
            key=lambda x: x["refCount"], reverse=True
        )[:20],
        "links": links,
    }

    report_path = DATA_DIR / "guide-interlinks.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"\n  발견된 상호참조: {len(links)}건")
    print(f"  참조를 가진 가이드: {len(guide_ref_counts)}개")

    if links:
        print(f"\n  상호참조 샘플 (상위 10건):")
        for l in links[:10]:
            print(f"    {l['sourceGuide']} → {l['referencedGuide']} ({l['rawMatch']})")
            print(f"      \"{l['referenceText'][:60]}...\"")

    print(f"\n[DONE] 보고서: {report_path}")


if __name__ == "__main__":
    main()
