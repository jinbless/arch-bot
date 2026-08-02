#!/usr/bin/env python3
"""법·시행령·시행규칙 별표 파싱 manifest (SHA-256 provenance).

산업안전보건기준규칙 별표는 `data-team/01-parsing/rule-appendices/`가 담당한다.
여기는 **법 시행령·시행규칙의 별표**만 다룬다 — 흐름 6칸에 필요한 것만 골라 전사했다.

  시행령 별표 20  방호조치가 필요한 기계·기구        (법 제80조 → 영 제70조)
  시행령 별표 21  대여자 등이 안전조치를 해야 하는 기계 (법 제81조 → 영 제71조)
  시행규칙 별표 4  안전보건교육 교육과정별 교육시간     (법 제29조 → 규칙 제26조)
  시행규칙 별표 5  안전보건교육 교육대상별 교육내용     (같은 조. **특별교육 대상 작업 39종**)

사용: python data-team/01-parsing/law-appendices/build_manifest.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PARSED = HERE / "parsed"
RAW = ROOT / "data-team" / "01-parsing" / "rule-appendices" / "rawPDF"
OUT = HERE / "manifest" / "law-appendices-manifest.json"

FILES = {
    "decree-20": (RAW / "산업안전보건법시행령별표",
                  "[별표 20] 유해ㆍ위험 방지를 위한 방호조치가 필요한 기계ㆍ기구(제70조 관련)(산업안전보건법 시행령).pdf"),
    "decree-21": (RAW / "산업안전보건법시행령별표",
                  "[별표 21] 대여자 등이 안전조치 등을 해야 하는 기계ㆍ기구ㆍ설비 및 건축물 등(제71조 관련)(산업안전보건법 시행령).pdf"),
    "enforce-4": (RAW / "산업안전보건법시행규칙별표",
                  "[별표 4] 안전보건교육 교육과정별 교육시간(제26조제1항 등 관련)(산업안전보건법 시행규칙).pdf"),
    "enforce-5": (RAW / "산업안전보건법시행규칙별표",
                  "[별표 5] 안전보건교육 교육대상별 교육내용(제26조제1항 등 관련)(산업안전보건법 시행규칙).pdf"),
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    entries = []
    for key, (d, fn) in FILES.items():
        pj = PARSED / f"{key}.json"
        if not pj.exists():
            print(f"⚠ 파싱 결과 없음: {pj.name}")
            continue
        j = json.loads(pj.read_text(encoding="utf-8"))
        raw = d / fn
        entries.append({
            "key": key, "appendix_id": j["appendix_id"], "law": j["law"], "title": j["title"],
            "related_article": j["related_article"],
            "parsed_file": pj.name, "n_rows": len(j["rows"]), "last_no": j["last_no"],
            "raw_file": fn, "raw_bytes": raw.stat().st_size if raw.exists() else None,
            "raw_sha256": sha256(raw) if raw.exists() else None,
        })
        print(f"  {j['appendix_id']:8} {j['title'][:40]:42} {len(j['rows']):3d}행  마지막 {j['last_no']}")

    manifest = {
        "_note": "산업안전보건법 시행령·시행규칙 별표 파싱 manifest. raw PDF는 미추적(.gitignore), 파싱 산출물만 추적.",
        "source": "국가법령정보센터 (사용자가 브라우저로 직접 수집)",
        "parse_method": "VLM 시각 판독(Claude Read) — PDF 텍스트 레이어는 한글 공백이 소실되어 부적합",
        "parsed_at": "2026-08-02",
        "n_appendix": len(entries),
        "appendices": entries,
        # ★ 방법에 관한 정직한 기록. 이 프로젝트는 텍스트 추출을 금지하는데,
        #   검산 단계에서 그 규칙이 지켜지지 않았다.
        "verification": {
            "검산_방법_문제": (
                "enforce-4·enforce-5의 검산 에이전트가 pdftotext -layout(텍스트 추출)에 의존했고 "
                "'페이지 렌더 이미지로 육안 재확인은 하지 않았다'고 스스로 기록했다. "
                "이 프로젝트는 텍스트 추출을 금지한다(한글 공백 소실). 띄어쓰기 판정이 추정에 기댔다는 뜻이다."
            ),
            "사람_육안_대조": (
                "enforce-5의 특별교육 대상작업 39종 중 제1~6호(PDF 2쪽)와 제36~39호(8쪽)를 "
                "렌더 이미지로 직접 대조했다. 작업명·띄어쓰기 모두 원문과 일치했다"
                "('화재예방 및 초기대응에 관한사항'이 붙여 쓰인 것까지 그대로). 나머지 29종은 미대조."
            ),
            "검산이_잡은_전사_오기": [
                "제1호 라목 제4호: '인화점에 관한 사항' → '인화점 등에 관한 사항'('등' 누락)",
                "제1호 라목 제18호: '공동작업 신호' → '공통작업 신호'",
            ],
            "원문_오식_미수정": [
                "제8호 '팬·풍기(風旗)' — 통상 風機이나 원문 그대로 두었다",
                "제15호 '기계·기구에 특성 및 동작원리' — '의'가 맞아 보이나 원문 그대로",
            ],
        },
        "not_obtained": [
            "「유해·위험작업의 취업 제한에 관한 규칙」 — 법 제140조의 자격·면허 필요 작업 목록. "
            "이 목록이 없어 법 제140조는 대상 기계를 특정하지 못하고 기계류 전반에 조문 존재만 알린다",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n별표 {len(entries)}종 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
