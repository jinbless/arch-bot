#!/usr/bin/env python3
"""OWA→CWA A — 최적 파이프라인 매처 (rich+기인물 추출 → 결여조치 매칭 변별).

rich+기인물 추출(optimal_extractions.json)을 받아 기인물 앵커로 후보 국소화 후,
measure-aware RANK로 정렬: 사진 '결여조치(missing_measures)'를 각 후보 조의 '요구조치
(required_measures, 시그니처)'와 대조해, 결여=요구가 직접 일치하는 조를 우선. 형제조문(같은
절/관)은 결여조치로 변별. gold(label_sheet)로 채점, 기존 62.5% 대비.

--plain: 변별 없는 기본 RANK(가져온 gimulmul_match RANK)로 ablation.

사용: .venv/bin/python scripts/optimal_match.py [--plain]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from build_article_signatures import _ensure_key  # noqa: E402
from gimulmul_match import (RESOLVE_SYS, RESOLVE_SCHEMA, RANK_SYS, RANK_SCHEMA, CROSS)  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
EXTRACT = ART / "optimal_extractions.json"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
LABELS = ART / "label_sheet.csv"
OUT_MD = ART / "optimal_match.md"
MATCH_MODEL = "gpt-5.4"

RANK_SYS_MEASURE = (
    "너는 대한민국 산업안전보건 전문가다. 작업장 장면(기인물·관찰상태·결여조치 포함)과 후보 산업안전보건규칙 "
    "조를 받는다. 각 후보는 [기인물]/[횡단] 구분과 소속 절/관(형제조문 묶음), 그 조의 '요구조치'를 함께 제시한다.\n"
    "랭킹 원칙:\n"
    "1) [기인물] 전용 조를 [횡단] 일반의무보다 우선(사진의 주된 사고원인=기인물).\n"
    "2) 핵심 변별: 사진의 '결여조치'와 각 조의 '요구조치'를 대조하라. 사진에서 결여된 조치가 그 조가 요구하는 "
    "조치와 직접 일치하면 강한 위반 신호다(예: 결여=안전대 부착설비 → 제44; 결여=작업발판 → 제42; "
    "결여=개구부 덮개/난간 → 제43).\n"
    "3) 같은 절/관 형제조문이 여러 개면, 사진 결여조치에 가장 정확히 대응하는 하나를 1위로(나머지는 하위/maybe).\n"
    "4) 식별된 기인물의 전용 의무는 사진에 명시 안 돼도 미확인이면 maybe 포함.\n"
    "applies yes(명백)/maybe(정황·미확인)/no(무관). 적용 조를 확신 높은 순으로 정렬.")


def ext_scene(e: dict) -> str:
    parts = [e.get("scene_summary", "")]
    vo = e.get("visual_observations") or []
    if vo:
        parts.append("관찰: " + " / ".join(vo))
    vc = e.get("visual_cues") or []
    if vc:
        parts.append("시각단서: " + "; ".join(vc))
    for g in e.get("gimulmul") or []:
        mm = ", ".join(g.get("missing_measures") or [])
        parts.append(f"[기인물] {g.get('name','')}: {g.get('observed_state','')} / 결여: {mm} / 예상: {g.get('expected_accident','')}")
    return "\n".join(p for p in parts if p).strip()


def photo_missing(e: dict):
    out = []
    for g in e.get("gimulmul") or []:
        out += g.get("missing_measures") or []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plain", action="store_true", help="기본 RANK로 ablation")
    args = ap.parse_args()

    extractions = json.loads(EXTRACT.read_text(encoding="utf-8"))
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
    sig = {json.loads(l)["article_code"]: json.loads(l)
           for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}

    gold = defaultdict(set)
    for r in csv.DictReader(LABELS.open(encoding="utf-8-sig")):
        if (r.get("LABEL") or "").strip().lower().startswith("y"):
            gold[r["photo"]].add(r["article_code"])

    db = SessionLocal()
    full = {r[0]: r[1] for r in db.execute(text(
        "select article_code, full_text from articles where law_type='RULE' and not deleted")).fetchall()}
    sec = {r[0]: (r[1] or "") for r in db.execute(text(
        "select article_code, section from articles where law_type='RULE' and not deleted")).fetchall()}
    db.close()

    catalog = []
    for gk, g in groups.items():
        nobs = sum(1 for a in g["articles"] if a["observable"] in ("yes", "partial"))
        if nobs >= 1 and gk not in idx["cross_cutting"]:
            catalog.append(f"{gk}  ::기인물={g['gimulmul']} ({nobs}조)")
    catalog_text = "\n".join(sorted(catalog))

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    def chat(sys_p, user, schema):
        r = client.chat.completions.create(model=MATCH_MODEL, messages=[
            {"role": "system", "content": sys_p}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": schema})
        return json.loads(r.choices[0].message.content)

    def match_one(photo, model, e):
        st = ext_scene(e)
        miss = photo_missing(e)
        rv = chat(RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n주요 기인물의 group_key 선택.", RESOLVE_SCHEMA)
        gks = [k for k in rv["group_keys"] if k in groups]
        cand, seen, kind = [], set(), {}
        for gk in gks:
            for a in groups[gk]["articles"]:
                if a["observable"] in ("yes", "partial") and a["code"] not in seen:
                    seen.add(a["code"]); cand.append(a["code"]); kind[a["code"]] = "기인물"
        for c in cross_set:
            if c not in seen:
                seen.add(c); cand.append(c); kind[c] = "횡단"

        if args.plain:
            lines = [f"[장면]\n{st}", "", "[후보 조]"]
            for c in cand:
                s = sig.get(c, {})
                lines.append(f"- [{kind[c]}] {c} {s.get('title','')} | {s.get('violation_scene','')[:90]}\n  전문: {(full.get(c,'') or '')[:160]}")
            rk = chat(RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        else:
            lines = [f"[장면]\n{st}", f"\n[사진 결여조치(핵심 변별키)] {', '.join(miss) or '(미상)'}", "", "[후보 조]"]
            for c in cand:
                s = sig.get(c, {})
                rm = ", ".join(s.get("required_measures") or [])
                # 절/관 라벨(형제 묶음)
                import re as _re
                m = _re.search(r"(절\d+[^>]*)(?:.*?(관\d+[^>]*))?", sec.get(c, ""))
                glabel = (m.group(1).strip() + (" " + m.group(2).strip() if m and m.group(2) else "")) if m else "(상위)"
                lines.append(f"- [{kind[c]}|{glabel}] {c} {s.get('title','')} | 요구조치: {rm} | {s.get('violation_scene','')[:70]}\n  전문: {(full.get(c,'') or '')[:140]}")
            rk = chat(RANK_SYS_MEASURE, "\n".join(lines) + "\n\n결여조치↔요구조치 대조로 변별, 확신순 정렬.", RANK_SCHEMA)

        ranked = [x["article_code"] for x in rk["ranked"] if x["applies"] in ("yes", "maybe")]
        return photo, model, gks, ranked

    jobs = [(p, m, r["extraction"]) for p, bym in extractions.items() for m, r in bym.items() if "extraction" in r]
    matched = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed([ex.submit(match_one, p, m, e) for p, m, e in jobs]):
            photo, model, gks, ranked = fu.result()
            matched[(photo, model)] = (gks, ranked)
            print(f"  {photo:<12} {model:<20} grp{len(gks)} ranked{len(ranked)}", flush=True)

    KS = [1, 3, 5, 10]

    def metrics(ranked, g):
        if not g:
            return None
        out = {"p1": 1.0 if ranked and ranked[0] in g else 0.0}
        for k in KS:
            out[f"hit{k}"] = 1.0 if set(ranked[:k]) & g else 0.0
            out[f"r{k}"] = len(set(ranked[:k]) & g) / len(g)
        return out

    models = sorted({m for _, m in matched})
    agg = {m: defaultdict(list) for m in models}
    per = defaultdict(dict)
    for (photo, model), (gks, ranked) in matched.items():
        mt = metrics(ranked, gold.get(photo, set()))
        per[photo][model] = (ranked[:5], mt)
        if mt:
            for k, v in mt.items():
                agg[model][k].append(v)

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    mode = "PLAIN(ablation)" if args.plain else "MEASURE-AWARE(optimal)"
    print(f"\n=== 최적 파이프라인 [{mode}] (rich+기인물 추출) ===")
    print(f"{'model':<20}{'P@1':>7}{'Hit@3':>7}{'Hit@5':>7}{'R@5':>7}{'R@10':>7}")
    md = [f"# 최적 파이프라인 [{mode}]", "", "| 모델 | P@1 | Hit@3 | Hit@5 | R@5 | R@10 |", "|---|---|---|---|---|---|"]
    for m in models:
        a = agg[m]
        print(f"{m:<20}{mean(a['p1']):>7.1%}{mean(a['hit3']):>7.1%}{mean(a['hit5']):>7.1%}{mean(a['r5']):>7.1%}{mean(a['r10']):>7.1%}")
        md.append(f"| {m} | {mean(a['p1']):.1%} | {mean(a['hit3']):.1%} | {mean(a['hit5']):.1%} | {mean(a['r5']):.1%} | {mean(a['r10']):.1%} |")
    print("\n--- 사진별 top5 ---")
    for photo in per:
        md.append(f"\n### {photo} (gold {sorted(gold.get(photo,set()))})")
        for m in per[photo]:
            top, mt = per[photo][m]
            print(f"  {photo:<12} {m:<20} P@1={mt['p1']:.0f} | {top}" if mt else f"  {photo} {m} (no gold)")
            md.append(f"- {m}: {top} {'P@1='+str(int(mt['p1'])) if mt else ''}")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n→ {OUT_MD.name}")


if __name__ == "__main__":
    main()
