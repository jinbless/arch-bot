#!/usr/bin/env python3
"""조문 원문 → 작업 흐름 6단계 시점 라벨 병합 (LLM 판정을 결정론으로 검산).

**왜 필요한가.** `build_flow_slice_all.py`의 `phase_of()`는 조문 **제목**만 정규식으로 본다.
그래서 669개 조문 중 **642개(96%)가 EXEC 한 칸**에 몰렸다. 제89조는 본문에
"그 날의 작업을 시작하기 전에"가 있는데도 제목('운전 시작 전 조치')이 규칙에 안 걸려 EXEC로 갔다.
타임라인이라고 부르지만 실제로는 한 덩어리였다.

**어떻게 고치는가.** 조문 원문(`article-texts.json`의 fullText)을 읽고 시점을 판정한다.
판정은 LLM이 하되 **혼자 결정하게 두지 않는다.** 그리고 **양방향으로** 검증한다:

  1차   원문을 읽고 시점 + 원문 인용 (12배치)         → ext_batch*.json
  2차   독립 심판이 비-EXEC 주장을 반박               → ver_batch*.json
  3차   반박된 것만 재심                              → retrial.json
  역방향 EXEC 단독 조문에서 **놓친 시점**을 탐색       → add*.json
  역검증 새 주장을 심판이 반박                        → rver*.json
  보완  작업 중이 빠진 조문 · 제목이 같은데 갈린 묶음   → add_noexec.json, add_consistency.json
  대조  이 스크립트가 인용문이 원문에 **글자 그대로** 있는지 검사 (결정론)

★ 역방향이 없으면 파이프라인이 **편향된 래칫**이 된다. 1차에 "EXEC가 안전한 기본값"이라고
  지시했기 때문에 2·3차는 비-EXEC를 EXEC로 깎기만 하고 EXEC에서 꺼내는 경로가 없다.
  실제로 2차 반박 27건이 27건 모두 결론이 EXEC였다. 그래서 반대 방향을 따로 돌린다.

★ 인용 대조가 마지막 안전장치다. 원문에 없는 인용은 지어낸 것이므로 통째로 버린다.
  LLM 출력은 `article_phase_llm/`에 원본 그대로 두어 이 스크립트를 다시 돌리면 같은 결과가 나온다.

사용: python data-team/01-parsing/rule-appendices/build_article_phases.py [--in DIR]
출력: data-team/05-enrichment/runtime-artifacts/article_phases.json
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
TEXTS = ROOT / "data-team" / "02-extraction" / "pipe-A" / "data" / "article-texts.json"
LLM_DIR = ART / "article_phase_llm"
OUT = ART / "article_phases.json"

PHASES = ["PLAN", "ASSIGN", "PRECHECK", "EXEC", "POST", "PERIODIC"]
LABEL = {"PLAN": "계획·사전조사", "ASSIGN": "인적 배치·자격", "PRECHECK": "작업 시작 전 점검",
         "EXEC": "작업 중", "POST": "종료·이탈", "PERIODIC": "정기점검"}


def norm(s: str) -> str:
    """인용 대조용 정규화 — 공백/유사문자만 접는다.

    ★ 조사·어미는 절대 건드리지 않는다. '작업을 시작하기 전에'와 '작업 시작 전'은
      다른 문구이고, 그 차이가 곧 판정 근거이기 때문이다.
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("ㆍ", "·").replace("․", "·").replace("‧", "·")
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", "", s)


def read_all(d: Path, pat: str, key: str) -> list[dict]:
    """패턴에 맞는 파일들에서 key 배열을 이어 붙인다. 깨진 파일은 **이름을 남긴다**.

    ⚠ 배열을 통째로 쓴 파일도 받는다 — 실제로 한 에이전트가 {"additions":[…]} 대신 […]로 썼다.
      조용히 건너뛰면 그 배치가 통째로 사라진다(실제로 add07.json은 아예 안 쓰여서
      트랜스크립트에서 복구했다).
    """
    out, bad = [], []
    for p in sorted(d.glob(pat)):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            out.extend(j if isinstance(j, list) else (j.get(key) or []))
        except Exception as e:  # noqa: BLE001
            bad.append(f"{p.name}: {e}")
    if bad:
        print("⚠ 읽지 못한 파일:\n  " + "\n  ".join(bad))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(LLM_DIR))
    src = Path(ap.parse_args().src)

    texts = json.loads(TEXTS.read_text(encoding="utf-8"))["laws"]["RULE"]
    codes = [json.loads(l)["article_code"]
             for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    nbody = {c: norm(texts[c]["fullText"]) for c in codes if c in texts}

    # ── 주장 모으기 ────────────────────────────────────────────────────
    # 1차: 조문별 phases 전체 / 역방향·보완: 추가분만. 출처를 남겨야 왜 들어왔는지 추적된다.
    claims: dict[str, dict[str, dict]] = defaultdict(dict)   # code → phase → claim
    no_duty: dict[str, bool] = {}
    for a in read_all(src, "ext_batch*.json", "articles"):
        c = a.get("code")
        if c not in nbody or c in no_duty:
            continue
        no_duty[c] = bool(a.get("no_duty"))
        for p in a.get("phases") or []:
            if p.get("phase") in PHASES:
                claims[c].setdefault(p["phase"], {**p, "origin": "1차"})
    for pat, origin in (("add[0-9]*.json", "역방향"), ("add_noexec.json", "보완(작업중 누락)"),
                        ("add_consistency.json", "보완(칸 불일치)")):
        for a in read_all(src, pat, "additions"):
            c = a.get("code")
            if c in nbody and a.get("phase") in PHASES:
                claims[c].setdefault(a["phase"], {**a, "origin": origin})

    # ── 반박 모으기 ────────────────────────────────────────────────────
    # ★ 2차 반박은 **최종이 아니다.** 3차 재심이 그 27건을 다시 봐서 19건만 기각하고 8건은 살렸다.
    #   여기서 2차를 그대로 적용하면 재심에서 부활한 8건이 조용히 죽는다.
    ref2 = {f"{v['code']}/{v['phase']}": v.get("why", "")
            for v in read_all(src, "ver_batch*.json", "verdicts") if v.get("refuted")}
    refR = {f"{v['code']}/{v['phase']}": v.get("why", "")
            for v in read_all(src, "rver*.json", "verdicts") if v.get("refuted")}
    rt = json.loads((src / "retrial.json").read_text(encoding="utf-8")) if (src / "retrial.json").exists() else {}
    final_drop = set(rt.get("기각목록") or [])
    if final_drop:
        revived = set(ref2) - final_drop
        ref2 = {k: w for k, w in ref2.items() if k in final_drop}
        print(f"  3차 재심: 2차 반박 {len(ref2) + len(revived)}건 중 {len(ref2)}건 기각 · {len(revived)}건 부활")
    # 역검증(rver*)은 재심 단계가 없으므로 그대로 최종이다.
    refuted = {**ref2, **refR}

    # ★ 파이프라인이 스스로와 충돌한 건 — 1차·역방향은 찬성, 2차·3차는 반대(2:2).
    #   조용히 한쪽으로 기울면 어느 쪽이 죽었는지 아무도 모른다. 관점이 다른 3인이 다수결로 정한 결과가
    #   tiebreak.json이고, **다른 모든 판정을 덮어쓴다.**
    tb_p = src / "tiebreak.json"
    tiebreak = json.loads(tb_p.read_text(encoding="utf-8")) if tb_p.exists() else {}
    tb_ok, tb_no = set(tiebreak.get("채택") or []), set(tiebreak.get("기각") or [])
    for k in tb_ok:
        refuted.pop(k, None)
    for k in tb_no:
        refuted.setdefault(k, "최종판정에서 기각(3인 다수결)")
    if tb_ok or tb_no:
        print(f"  최종판정: 동점 {len(tb_ok) + len(tb_no)}건 중 채택 {len(tb_ok)} · 기각 {len(tb_no)}")

    # ── 병합 + 인용 대조 ───────────────────────────────────────────────
    out, stat = {}, Counter()
    for c in codes:
        title = texts.get(c, {}).get("title", "")
        keep, drop = [], []
        for ph in PHASES:                                  # 칸 순서를 고정해 출력이 흔들리지 않게
            p = claims.get(c, {}).get(ph)
            if not p:
                continue
            q, key = p.get("quote") or "", f"{c}/{ph}"
            if ph == "EXEC" and p["origin"] == "1차":
                keep.append({**p, "verified": "기본값(1차)"})
                stat["EXEC 유지(1차 기본값)"] += 1
                continue
            if norm(q) not in nbody[c]:                    # ★ 마지막 안전장치
                drop.append({**p, "why": "인용문이 원문에 없다(인용 대조 실패)"})
                stat["기각: 인용 대조 실패"] += 1
                continue
            if key in refuted:
                drop.append({**p, "why": refuted[key]})
                stat[f"기각: 적대 검증({p['origin']})"] += 1
                continue
            # ★ 보완 두 갈래(작업중 누락·칸 불일치)는 적대 검증 단계를 거치지 않았다.
            #   인용 대조만 통과한 상태다. '검증 통과'라고 쓰면 거짓말이 된다.
            v = ("최종판정 채택(3인 다수결)" if key in tb_ok
                 else f"인용 대조만 통과({p['origin']})" if p["origin"].startswith("보완")
                 else f"검증 통과({p['origin']})")
            keep.append({**p, "verified": v, "contested": key in tb_ok})
            stat[f"확정: {ph}"] += 1
        if not keep:
            keep.append({"phase": "EXEC", "quote": "", "reason": "시점 판정이 모두 기각됨",
                         "origin": "복귀", "verified": "기본값 복귀"})
            stat["전부 기각 → EXEC 복귀"] += 1

        # ── evidence: 화면·검수 뷰어에 '이 칸에 있는 이유'로 보여줄 문구 ─────────
        # ★ quote와 evidence는 다르다.
        #   1차의 EXEC quote는 근거가 아니라 **자리표시**다 — "시점 문구가 없으면 EXEC 하나만 내고
        #   quote에는 핵심 의무 문장을 넣어라"고 지시했기 때문이다. 그걸 근거로 띄우면
        #   제388조처럼 한 문장이 '작업 전'과 '작업 중'에 나란히 떠서 중복으로 읽힌다.
        #   또 두 칸의 인용이 **글자까지 같으면** 어느 칸이 왜 다른지 설명하지 못하므로 낮은 등급 쪽을 비운다.
        #   ⚠ 항목 자체는 빼지 않는다. 제620조("작업을 시작하기 전과 작업 중에")처럼 한 문장이
        #     정말 두 시점을 다 말하는 경우가 섞여 있어, 빼면 맞는 라벨이 사라진다.
        RANK = {"최종판정": 3, "검증 통과": 2, "인용 대조만": 1}
        def rank(x):
            return next((v for k, v in RANK.items() if x["verified"].startswith(k)), 0)
        for x in keep:
            x["evidence"] = "" if rank(x) == 0 else x.get("quote", "")
        for x in keep:
            if not x["evidence"]:
                continue
            # 마침표 유무만 다른 것도 같은 인용이다(실제로 제39조가 그랬다).
            def ek(s):
                return norm(s).rstrip(".·,")
            same = [y for y in keep if y is not x and ek(y.get("quote", "")) == ek(x["evidence"])]
            if same and any(rank(y) > rank(x) for y in same):
                x["evidence"] = ""
                stat["중복 인용 — 근거 표시 생략"] += 1

        out[c] = {"title": title, "no_duty": no_duty.get(c, False), "phases": keep, "dropped": drop}

    # ── 리포트 ────────────────────────────────────────────────────────
    n = len(codes)
    print(f"\n=== 조문 {n}종 시점 재판정 ===")
    for k, v in stat.most_common():
        print(f"  {v:5d}  {k}")

    dist = Counter(p["phase"] for a in out.values() for p in a["phases"])
    multi = sum(1 for a in out.values() if len(a["phases"]) > 1)
    print(f"\n  칸별 조문 수 (한 조문이 여러 칸에 들어갈 수 있다 — 다중 {multi}종)")
    LEX = {"PLAN": r"사전조사|작업계획서|계획을 수립|설계도서",
           "ASSIGN": r"작업지휘자|지휘자|유도자|신호수|자격|특별교육|선임|배치",
           "PRECHECK": r"작업 ?시작 ?전|시작하기 전|사용 ?전|시동 ?전|작업 전 확인|미리 점검",
           "POST": r"이탈|종료|해체|반출|정리정돈|작업 후", "PERIODIC": r"정기|주기|월 1회|연 1회|자체검사"}
    before = Counter(next((p for p in PHASES if p != "EXEC" and re.search(LEX[p], texts.get(c, {}).get("title", "")))
                          , "EXEC") for c in codes)
    print(f"    {'칸':12} {'이전(제목 정규식)':>16} {'이후(원문 판독)':>14}")
    for ph in PHASES:
        print(f"    {LABEL[ph]:12} {before[ph]:>16} {dist[ph]:>14}")

    nd = [c for c, a in out.items() if a["no_duty"]]
    print(f"\n  의무 없는 조문(목적·정의·적용 제외) {len(nd)}종 — 흐름에서 뺀다")
    print("    " + ", ".join(f"{c}({out[c]['title'][:8]})" for c in nd[:8]) + (" …" if len(nd) > 8 else ""))

    OUT.write_text(json.dumps({
        "_note": "조문 원문 기반 시점(6단계) 라벨. LLM 양방향 판정 + 적대 검증 + 인용 대조(결정론). 사람 검수 전.",
        "_method": "1차 판독 → 2·3차 반박/재심 → 역방향 탐색 → 역검증 → 인용문 원문 대조(실패는 무조건 기각)",
        "_warning": "no_duty=true인 조문은 사업주 행위 의무가 아니다(목적·정의·적용 제외). 흐름 항목으로 쓰지 마라.",
        "reviewed_by_human": False,
        "n_articles": len(out),
        "articles": out,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
