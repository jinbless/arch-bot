#!/usr/bin/env python3
"""안전검사 대상기계 15종 ↔ 기존 데이터셋 커버리지 조인 (LLM 호출 0).

흐름 골격 6단계 중 '정기점검' 칸은 산업안전보건기준규칙이 아니라 산업안전보건법 제93조
안전검사 체계가 규율한다. 그 원천(안전검사 고시)을 새로 확보했으니, 기존 데이터와
**몇 종이 붙는지**를 숫자로 낸다.

조인 대상:
  1) rule-appendices/parsed/appendix-03.json   별표 3 작업시작 전 점검 19종 (section_ref 좌표 보유)
  2) runtime-artifacts/gimulmul_index.json     기인물 그룹 113종 (편/장/절/관 필드 보유)
  3) runtime-artifacts/article_signatures.jsonl 기준규칙 669조 (제목·section 보유)

⚠ 좌표 비교는 **(편, 장, 절, 관) 튜플 전체**로만 한다. 절 번호만 보면 다른 편의 같은 번호 절을
  통째로 끌어온다(과거 '슬링'에 140조문이 붙었던 버그). 이 스크립트에서 좌표는 *검증용*이고
  매칭 자체는 이름으로 한다 — 그래도 비교할 땐 튜플 전체를 쓴다.

산출:
  parsed/safety-inspection.json 의 rule_articles 갱신 (--write 지정 시)
  parsed/coverage-report.json   매칭/미매칭 상세

사용: python data-team/01-parsing/safety-inspection/join_inspection_coverage.py [--write]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SI = HERE / "parsed" / "safety-inspection.json"
APX3 = ROOT / "data-team" / "01-parsing" / "rule-appendices" / "parsed" / "appendix-03.json"
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"

# 「제2편제1장제10절제2관」 형태 (별표 3의 section_ref)
COORD_PACKED = re.compile(r"제(\d+)편제(\d+)장제(\d+)절(?:제(\d+)관)?")

# 시행령 용어 ↔ 별표 3/기준규칙 용어가 다른 경우에만 두는 명시 별칭.
# 유사어를 임의로 넓히지 않는다. 아래 둘은 근거가 원문에 있다:
#   전단기 ← "프레스등"  : 안전검사 고시 제3조제3호가 "프레스, 전단기(이하 "프레스등"이라 한다)"로 정의
#   산업용 로봇 ← "로봇" : 안전검사 고시 제25조제1항제1호가 "산업용 로봇(이하 "로봇"이라 한다)"으로 정의
ALIAS = {
    "전단기": ["프레스등"],
    "산업용 로봇": ["로봇"],
}


def coord_packed(s: str) -> tuple | None:
    """별표 3 좌표 문자열 → (편, 장, 절, 관). 관이 없으면 None."""
    m = COORD_PACKED.search(s or "")
    if not m:
        return None
    return tuple(int(x) if x else None for x in m.groups())


def coord_spaced(section: str) -> tuple:
    """'편2 안전기준 > 장1 … > 절10 … > 관2 지게차' → (편, 장, 절, 관).

    구분자를 '>'로만 쪼개면 공백 구분 좌표가 한 토큰으로 뭉쳐 절·관이 소실된다.
    """
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)$", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        if lvl == "편":
            p = n
        elif lvl == "장":
            j = n
        elif lvl == "절":
            jeol = n
        else:
            gwan = n
    return (p, j, jeol, gwan)


def norm(s: str) -> str:
    """이름 비교용 정규화 — 공백·중점·괄호 제거."""
    return re.sub(r"[\s·ㆍ()（）]", "", s or "")


def flatten_criteria(path: Path) -> list[str]:
    """고시 별표(번호/구분/내용) → '제N호 구분 — 내용' 평탄화.

    호 번호를 앞에 붙이는 이유: 고시 본문 단서가 호 단위로 검사기준을 제외한다
    (예: 제6조 단서 "별표 2의 제74호 나목"). 번호를 버리면 그 단서를 적용할 수 없다.
    """
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in d.get("rows", []):
        head = f"제{r['no']}호 {r.get('category', '')}".strip()
        if r.get("subtable"):
            head = f"[{r['subtable']}] {head}"
        for it in r.get("items", []) or []:
            out.append(f"{head} — {it}")
        if not (r.get("items") or []):
            out.append(head)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="safety-inspection.json 의 rule_articles 갱신")
    args = ap.parse_args()

    si = json.loads(SI.read_text(encoding="utf-8"))
    apx3 = json.loads(APX3.read_text(encoding="utf-8"))
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    sigs = [json.loads(l) for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # 기인물 그룹 좌표 — pyeon/jang/jeol/gwan 필드에서 직접 뽑는다
    gim_rows = []
    for key, g in gim.items():
        c = coord_spaced(" ".join([g.get("pyeon", ""), g.get("jang", ""), g.get("jeol", ""), g.get("gwan", "")]))
        gim_rows.append({"key": key, "name": g.get("gimulmul", ""), "coord": c,
                         "articles": [a["code"] for a in g.get("articles", [])]})

    apx3_rows = [{"no": r["no"], "subject": r["subject"], "coord": coord_packed(r.get("section_ref", ""))}
                 for r in apx3["rows"]]

    report = []
    for m in si["machines"]:
        # 파쇄기 또는 분쇄기처럼 한 호에 두 기계가 묶인 경우 각각으로 쪼개 찾는다
        keys = [norm(x) for x in re.split(r"\s*또는\s*", m["name"]) if x.strip()]
        keys += [norm(a) for a in ALIAS.get(m["name"], [])]

        g_hits = [g for g in gim_rows
                  if any(k and (k == norm(g["name"]) or k in norm(g["name"]) or k in norm(g["key"])) for k in keys)]
        a_hits = [{"no": r["no"], "subject": r["subject"], "coord": r["coord"]} for r in apx3_rows
                  if any(k and k in norm(r["subject"]) for k in keys)]
        t_hits = [{"code": s["article_code"], "title": s["title"], "coord": coord_spaced(s.get("section", ""))}
                  for s in sigs if any(k and k in norm(s.get("title", "")) for k in keys)]
        # article_signatures.equipment — 기존 파이프라인이 조문마다 붙여 둔 설비 목록.
        # 조문 번호를 추측하는 게 아니라 이미 있는 데이터셋을 조인하는 것이다.
        e_hits = [{"code": s["article_code"], "title": s["title"]}
                  for s in sigs
                  if any(k and k in norm(e or "") for k in keys for e in (s.get("equipment") or []))]

        # 좌표 교차검증 — 튜플 전체 비교. 관까지 같으면 exact, 편·장·절만 같으면 jeol
        cross = []
        for g in g_hits:
            for a in a_hits:
                if a["coord"] is None:
                    continue
                if g["coord"] == a["coord"]:
                    cross.append({"gimulmul": g["key"], "apx3_no": a["no"], "level": "exact"})
                elif g["coord"][:3] == a["coord"][:3]:
                    cross.append({"gimulmul": g["key"], "apx3_no": a["no"], "level": "jeol"})

        # ★ 출처를 섞지 않는다. 절/관 소속(section)은 '이 기계를 다루는 조문'이 아니라 '이웃 조문'이다.
        #   '화학설비ㆍ압력용기 등' 절 25조문을 전부 압력용기 조문이라고 하면 과다부착이 된다
        #   (절 번호만 보고 슬링에 140조문을 붙였던 것과 같은 종류의 실수).
        def srt(codes):
            return sorted(set(codes), key=lambda x: (int(re.match(r"제(\d+)", x).group(1)), x))

        by_src = {"title": srt(t["code"] for t in t_hits),
                  "equipment": srt(e["code"] for e in e_hits),
                  "section": srt(c for g in g_hits for c in g["articles"])}
        report.append({
            "no": m["no"], "name": m["name"],
            "gimulmul_groups": [{"key": g["key"], "coord": g["coord"], "n_articles": len(g["articles"])} for g in g_hits],
            "appendix_03": a_hits,
            "title_articles": t_hits,
            "equipment_articles": e_hits,
            "coord_cross": cross,
            "rule_articles": srt(by_src["title"] + by_src["equipment"]),
            "rule_articles_by_source": by_src,
        })

    # ── 리포트 ─────────────────────────────────────────────────────────
    print(f"=== 안전검사 대상 {len(report)}종 × 기존 데이터 커버리지 ===\n")
    hdr = f"{'no':>3} {'기계':16} {'기인물그룹':>6} {'별표3':>6} {'좌표교차':>8} {'제목':>5} {'equip':>6} {'직접계':>6} {'절소속':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in report:
        cx = next((c["level"] for c in r["coord_cross"] if c["level"] == "exact"),
                  next((c["level"] for c in r["coord_cross"]), "-"))
        s = r["rule_articles_by_source"]
        print(f"{r['no']:>3} {r['name'][:15]:16} {len(r['gimulmul_groups']):>6} {len(r['appendix_03']):>6} "
              f"{cx:>8} {len(s['title']):>5} {len(s['equipment']):>6} {len(r['rule_articles']):>6} {len(s['section']):>6}")

    n_g = sum(1 for r in report if r["gimulmul_groups"])
    n_a = sum(1 for r in report if r["appendix_03"])
    n_r = sum(1 for r in report if r["rule_articles"])
    n_x = sum(1 for r in report if any(c["level"] == "exact" for c in r["coord_cross"]))
    print(f"\n기인물 그룹 매칭 {n_g}/{len(report)}  ·  별표 3 매칭 {n_a}/{len(report)}  ·  "
          f"조문 확보 {n_r}/{len(report)}  ·  좌표 완전일치 {n_x}/{len(report)}")

    miss_g = [r["name"] for r in report if not r["gimulmul_groups"]]
    miss_a = [r["name"] for r in report if not r["appendix_03"]]
    if miss_g:
        print(f"  기인물 그룹 없음: {', '.join(miss_g)}")
    if miss_a:
        print(f"  별표 3 없음    : {', '.join(miss_a)}")

    # 별표 3 쪽 미매칭(안전검사 대상이 아닌 작업종류)
    matched_apx = {a["no"] for r in report for a in r["appendix_03"]}
    only_apx = [f"{r['no']} {r['subject'][:22]}" for r in apx3_rows if r["no"] not in matched_apx]
    print(f"\n별표 3 19종 중 안전검사 대상과 안 붙는 것 {len(only_apx)}종:")
    for x in only_apx:
        print(f"    · {x}")

    # ── 흐름 골격 '정기점검' 칸 충족 여부 (별표 3 19종 기준) ──────────────
    hit = {}
    for r in report:
        for a in r["appendix_03"]:
            hit.setdefault(a["no"], []).append(r["name"])
    periodic = [{"no": r["no"], "subject": r["subject"], "machines": hit.get(r["no"], []),
                 "filled": bool(hit.get(r["no"]))} for r in apx3_rows]
    n_p = sum(1 for x in periodic if x["filled"])
    print(f"\n=== 흐름 골격 '정기점검' 칸 (별표 3 19종 기준) ===")
    print(f"안전검사 절차로 채워지는 작업종류 {n_p}/{len(periodic)}종")
    print(f"나머지 {len(periodic) - n_p}종은 데이터 결손이 아니라 시행령 제78조의 안전검사 대상이 아니다:")
    print(f"    {', '.join(x['subject'][:14] for x in periodic if not x['filled'])}")

    out = HERE / "parsed" / "coverage-report.json"
    out.write_text(json.dumps({
        "periodic_slot": {"filled": n_p, "total": len(periodic),
                          "_note": "미충족분은 안전검사 대상이 아니라서 이 원천으로는 못 채운다(지게차·차량계 건설기계 등).",
                          "rows": periodic},
        "_note": "안전검사 대상 15종 ↔ 별표3 19종 ↔ 기인물그룹 113종 조인. 매칭은 이름, 좌표는 (편,장,절,관) 튜플 전체 비교로 검증만.",
        "n_machines": len(report), "n_apx3": len(apx3_rows), "n_gimulmul_groups": len(gim_rows),
        "summary": {"gimulmul_matched": n_g, "apx3_matched": n_a, "articles_found": n_r, "coord_exact": n_x},
        "machines": report,
        "apx3_unmatched": only_apx,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {out.relative_to(ROOT)}")

    # ── 고시 별표 → inspection_items 평탄화 ────────────────────────────
    print("\n=== 고시 별표 검사기준 연결 ===")
    for m in si["machines"]:
        f = m.get("inspection_criteria_file", "")
        items = flatten_criteria(HERE / "parsed" / f) if f else []
        m["_items"] = items
        mark = "" if items else "   ← 별표 파일 없음/비어 있음"
        print(f"  {m['no']:>3} {m['name'][:14]:16} {f:28} {len(items):>4}건{mark}")
    n_i = sum(1 for m in si["machines"] if m["_items"])
    print(f"검사기준 확보 {n_i}/{len(si['machines'])}종 · 총 {sum(len(m['_items']) for m in si['machines'])}건")

    if args.write:
        by_no = {r["no"]: r for r in report}
        for m in si["machines"]:
            m["rule_articles"] = by_no[m["no"]]["rule_articles"]
            m["rule_articles_by_source"] = by_no[m["no"]]["rule_articles_by_source"]
            m["inspection_items"] = m.pop("_items")
        SI.write_text(json.dumps(si, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n→ {SI.relative_to(ROOT)} 의 rule_articles · inspection_items 갱신")
    else:
        for m in si["machines"]:
            m.pop("_items", None)
        print("\n(--write 미지정 — safety-inspection.json 은 변경하지 않았다)")


if __name__ == "__main__":
    main()
