#!/usr/bin/env python3
"""safety-inspection.json의 scope·cycle을 법령 원문과 **글자 단위로** 대조한다.

원천(모두 `data-team/02-extraction/pipe-A/data/article-texts.json`에 이미 있다):
  OSHA   제93조   안전검사            — 근거
  DECREE 제78조   안전검사대상기계등    — **각 호 = 대상 15종 + 괄호 단서(scope)**
  ENFORCE 제124조 안전검사의 신청 등
  ENFORCE 제125조 안전검사의 면제      — 11개 사유
  ENFORCE 제126조 주기와 합격표시      — **각 호 = 검사 주기(cycle)**

⚠ 왜 스크립트로 하나. 눈으로 옮겨 적으면 반드시 틀린다 — 실제로 사출성형기의
  '294킬로뉴턴(KN)'을 '(kN)'으로 옮겨 적어 두었다. 한 글자 차이가 법령 인용에서는 오류다.
  그래서 `--write`는 **scope를 사람이 옮긴 값이 아니라 시행령 원문에서 직접 잘라 넣는다.**
  전사(轉寫) 단계를 없애면 이 부류의 오류가 원리적으로 생기지 않는다.

⚠ cycle의 first/then/special은 원문을 **쪼갠** 것이라 그 자체는 원문이 아니다.
  각 조각이 해당 호의 **부분 문자열인지** 검사하고, 호 전문을 `verbatim`으로 함께 남긴다.

사용:
  python data-team/01-parsing/safety-inspection/verify_against_law.py          대조만
  python data-team/01-parsing/safety-inspection/verify_against_law.py --write  대조 + 반영
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEXTS = ROOT / "data-team" / "02-extraction" / "pipe-A" / "data" / "article-texts.json"
SI = Path(__file__).resolve().parent / "parsed" / "safety-inspection.json"

OPEN, CLOSE = "([[{", ")]]}"


def split_paren(item: str) -> tuple[str, str]:
    """'크레인(정격 하중이 2톤 미만인 것은 제외한다)' → ('크레인', '정격 하중이 …')

    ★ 괄호가 중첩된다. 사출성형기는 대괄호 안에 소괄호가 들어 있다:
      '사출성형기[형 체결력(型 締結力) 294킬로뉴턴(KN) 미만은 제외한다]'
      단순 정규식으로 자르면 '型 締結力'에서 끊긴다. 뒤에서부터 짝을 맞춰 연다.
    """
    s = item.strip()
    if not s or s[-1] not in CLOSE:
        return s, ""
    want = OPEN[CLOSE.index(s[-1])]
    depth, i = 0, len(s) - 1
    while i >= 0:
        if s[i] in CLOSE and CLOSE.index(s[i]) == OPEN.index(want):
            depth += 1
        elif s[i] == want:
            depth -= 1
            if depth == 0:
                return s[:i].strip(), s[i + 1:-1].strip()
        i -= 1
    return s, ""


def ho_items(full_text: str, para: str = "①") -> dict[str, str]:
    """조문 본문에서 '1. …' 형태의 각 호를 뽑는다. para 이후 다음 항 전까지만 본다."""
    body = full_text.split(para, 1)[-1]
    body = re.split(r"\n②", body)[0]
    out = {}
    for line in body.split("\n"):
        m = re.match(r"^(\d+)\.\s*(.+)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main() -> None:
    write = argparse.ArgumentParser().parse_known_args()[1] or sys.argv[1:]
    write = "--write" in write

    laws = json.loads(TEXTS.read_text(encoding="utf-8"))["laws"]
    decree = laws["DECREE"]["제78조"]
    rule126 = laws["ENFORCE"]["제126조"]
    si = json.loads(SI.read_text(encoding="utf-8"))

    # ── 시행령 제78조제1항 각 호 → 대상 + 괄호 단서 ────────────────────
    d_items = ho_items(decree["fullText"])
    d_parsed = {no: split_paren(t) for no, t in d_items.items()}

    # ── 시행규칙 제126조제1항 각 호 → 대상 목록 + 주기 본문 ─────────────
    r_items = ho_items(rule126["fullText"])
    r_parsed = {}
    for no, t in r_items.items():
        head, _, tail = t.partition(":")
        # 대상 목록에서도 괄호 단서를 뗀다('크레인(이동식 크레인은 제외한다)')
        targets = [split_paren(x)[0] for x in re.split(r",|\s및\s", head) if x.strip()]
        r_parsed[no] = {"targets": [x.strip() for x in targets if x.strip()],
                        "body": tail.strip(), "raw": t}

    print("═══ 시행령 제78조제1항 — 안전검사 대상 ═══")
    for no, (name, scope) in d_parsed.items():
        print(f"  {no:>2}. {name:16} {scope}")
    print(f"\n═══ 시행규칙 제126조제1항 — 검사 주기 ═══")
    for no, r in r_parsed.items():
        print(f"  {no}. {' · '.join(r['targets'])}\n      → {r['body']}")

    # ── 대조 ──────────────────────────────────────────────────────────
    diffs, oks = [], 0
    by_name = {name: (no, scope) for no, (name, scope) in d_parsed.items()}
    # 시행규칙 각 호가 어느 대상을 규율하는지 역인덱스
    ho_of = {t: no for no, r in r_parsed.items() for t in r["targets"]}

    print("\n═══ 글자 단위 대조 ═══")
    for m in si["machines"]:
        nm, tag = m["name"], f"[{m.get('no', '?')}] {m['name']}"
        # ① 이름이 시행령 각 호에 그대로 있는가
        if nm not in by_name:
            diffs.append((tag, "name", nm, "시행령 각 호에 같은 이름이 없다"))
            continue
        d_no, d_scope = by_name[nm]
        # ② scope 대조
        if (m.get("scope") or "") != d_scope:
            diffs.append((tag, "scope", m.get("scope") or "(빈 값)", d_scope))
        else:
            oks += 1
        # ③ source_ref(호 번호) 대조
        want_ref = f"시행령 제78조제1항제{d_no}호"
        if m.get("source_ref") and m["source_ref"] != want_ref:
            diffs.append((tag, "source_ref", m["source_ref"], want_ref))
        # ④ cycle 조각이 시행규칙 해당 호의 부분 문자열인가
        for cyc, label in [(m.get("cycle"), nm)] + [(v, v.get("subtype")) for v in m.get("cycle_variants") or []]:
            if not cyc:
                continue
            ho = ho_of.get(label)
            if ho is None:
                diffs.append((tag, f"cycle[{label}]", cyc.get("ref", ""), "시행규칙 각 호에 이 대상이 없다"))
                continue
            raw = r_parsed[ho]["raw"]
            if cyc.get("ref") != f"시행규칙 제126조제1항제{ho}호":
                diffs.append((tag, f"cycle[{label}].ref", cyc.get("ref"), f"시행규칙 제126조제1항제{ho}호"))
            for k in ("first", "then", "special"):
                v = cyc.get(k)
                if v and v not in raw:
                    diffs.append((tag, f"cycle[{label}].{k}", v, f"제{ho}호 본문에 그대로 있지 않다"))
                elif v:
                    oks += 1

    # ⑤ 역방향 — 시행령 각 호 중 파일에 없는 대상이 있는가
    have = {m["name"] for m in si["machines"]}
    for no, (name, _) in d_parsed.items():
        if name not in have:
            diffs.append((f"제{no}호 {name}", "누락", "(파일에 없음)", "시행령 각 호에 있다"))

    # ⑥ 호의 괄호 단서가 **특정 기계를 지목**하면 그 기계에만 special이 붙어야 한다.
    #    부분 문자열 검사만으로는 "제3호의 압력용기 단서가 컨베이어에 붙는" 오배정을 못 잡는다.
    for no, r in r_parsed.items():
        _, paren = split_paren(r["body"])
        if not paren:
            continue
        named = [t for t in r["targets"] if t in paren]
        should = set(named) if named else set(r["targets"])
        for m in si["machines"]:
            for cyc, label in ([(m.get("cycle"), m["name"])]
                               + [(v, v.get("subtype")) for v in m.get("cycle_variants") or []]):
                if not cyc or ho_of.get(label) != no:
                    continue
                has = bool(cyc.get("special"))
                if has and label not in should:
                    diffs.append((f"[{m.get('no', '?')}] {label}", "cycle.special 오배정",
                                  cyc["special"], f"제{no}호 단서는 {'·'.join(named)}만 지목한다"))
                elif not has and label in should:
                    diffs.append((f"[{m.get('no', '?')}] {label}", "cycle.special 누락",
                                  "(없음)", f"제{no}호 단서: {paren}"))
                else:
                    oks += 1

    if diffs:
        print(f"\n  불일치 {len(diffs)}건")
        for tag, field, got, want in diffs:
            print(f"\n  ✗ {tag} · {field}")
            print(f"      파일: {got}")
            print(f"      원문: {want}")
            if len(got) == len(want):
                col = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
                if col is not None:
                    print(f"      {col + 1}번째 글자: '{got[col]}' → '{want[col]}'")
    else:
        print("\n  ✓ 불일치 없음")
    print(f"  일치 확인 {oks}건")

    # ── 혼합기·파쇄기 적용 제외 범위 ───────────────────────────────────
    print("\n═══ 혼합기·파쇄기 적용 제외 범위 ═══")
    for no in ("14", "15"):
        name, scope = d_parsed[no]
        print(f"  제{no}호 {name}: 괄호 단서 {'있음 — ' + scope if scope else '**없음**'}")
    para2 = decree["fullText"].split("②", 1)[-1].strip()
    print(f"  시행령 제78조제2항: {para2}")
    print("  → 시행령 자체에는 제외 범위가 없다. 세부 종류·규격·형식은 제2항이 고시로 위임하는데,")
    print("     확보한 「안전검사 고시」는 검사기준만 정하고 적용범위를 정하지 않는다(제1~33조 전문 확인).")

    if not write:
        print("\n(대조만 했다. 파일에 반영하려면 --write)")
        return

    # ── 반영 ──────────────────────────────────────────────────────────
    # ★ scope를 사람이 옮긴 값이 아니라 **시행령 원문에서 직접** 넣는다. 전사 단계를 없앤다.
    for m in si["machines"]:
        if m["name"] in by_name:
            d_no, d_scope = by_name[m["name"]]
            m["scope"] = d_scope
            m["source_ref"] = f"시행령 제78조제1항제{d_no}호"
        for cyc, label in [(m.get("cycle"), m["name"])] + [(v, v.get("subtype")) for v in m.get("cycle_variants") or []]:
            if cyc and label in ho_of:
                cyc["verbatim"] = r_parsed[ho_of[label]]["raw"]

    v = si["verification"]
    v["원문_확보"] = [
        "안전검사 고시 본문 (고용노동부고시 제2026-49호, 15쪽) — 제1조~제33조 및 부칙 전문 확인",
        "안전검사 고시 별표 1~14 (검사기준, 107쪽)",
        "산업안전보건법 제93조 (article-texts.json · OSHA)",
        "산업안전보건법 시행령 제78조 (article-texts.json · DECREE, 개정 2024.6.25.)",
        "산업안전보건법 시행규칙 제124조·제125조·제126조 (article-texts.json · ENFORCE, 개정 2024.6.28.)",
    ]
    v["원문_미확보"] = [
        "「안전검사대상기계등의 규격 및 형식별 적용범위」에 관한 고시 — 시행령 제78조제2항이 위임한 별도 고시",
    ]
    v["미검증_필드"] = {} if not diffs else {"대조_불일치": [f"{t} · {f}" for t, f, _, _ in diffs]}
    v["법령_대조"] = {
        "대조일": "2026-08-02",
        "방법": "verify_against_law.py — 시행령 제78조제1항 각 호 / 시행규칙 제126조제1항 각 호와 글자 단위 대조",
        "scope": "시행령 제78조제1항 각 호의 괄호 단서를 **원문에서 직접 잘라 넣는다**(전사하지 않는다)",
        "cycle": "first/then/special은 해당 호를 쪼갠 것이며 각 조각이 호 본문의 부분 문자열임을 검사했다. 호 전문은 cycle.verbatim",
        "불일치": len(diffs),
        "일치_확인": oks,
    }
    # ★ 대조하다 드러난 공백. 데이터에 없는 것을 "없다"고 적어 두지 않으면
    #   화면이 '법정 — 2년마다'만 보여주고 면제 가능성을 통째로 숨긴다.
    ex = laws["ENFORCE"]["제125조"]
    v["알려진_공백"] = {
        "안전검사_면제": (f"시행규칙 제125조가 면제 사유 {len(ho_items(ex['fullText'], '제93조제2항'))}개를 정하는데 "
                     "이 파일에 반영돼 있지 않다(건설기계관리법·고압가스법·전기안전관리법 등 다른 법령 검사를 "
                     "받은 경우). 화면이 '법정 — N년마다'만 보여주면 면제 가능성이 숨는다."),
        "안전검사_신청": "시행규칙 제124조(주기 만료일 30일 전 신청, 만료일 전후 30일 이내 검사)도 미반영.",
    }
    v["미해결"] = (
        "혼합기·파쇄기 또는 분쇄기의 **적용 제외 범위는 시행령에 없다**(제14호·제15호에 괄호 단서 없음). "
        "시행령 제78조제2항이 세부 종류·규격·형식을 고용노동부장관 고시로 위임하며, 확보한 「안전검사 고시」는 "
        "검사기준만 정하고 적용범위를 정하지 않는다. 적용범위는 위임받은 별도 고시에 있을 것으로 보이나 "
        "그 고시를 확보하지 못했다. 추정하지 않고 비워 둔다."
    )
    SI.write_text(json.dumps(si, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {SI.relative_to(ROOT)} 갱신")


if __name__ == "__main__":
    main()
