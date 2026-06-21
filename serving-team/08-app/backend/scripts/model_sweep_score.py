#!/usr/bin/env python3
"""OWA→CWA #4 — Stage1 모델 스윕 채점.

model_sweep_extractions.json의 각 (사진, 모델) 기인물-first 추출을 받아, 고정 매칭단(gpt-5.4
RESOLVE→ASSEMBLE→RANK)으로 조문 매칭 후 gold(label_sheet)로 채점. 매칭단을 고정해 Stage1
추출모델 효과만 분리. 추출 완전성 지표(기인물 수, gold 기인물조문 회수 여부)도 집계.

산출 model_sweep.md + model_sweep_results.json.

사용: .venv/bin/python scripts/model_sweep_score.py
"""
from __future__ import annotations

import csv
import json
import os
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
EXTRACT = ART / "model_sweep_extractions.json"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
LABELS = ART / "label_sheet.csv"
OUT_MD = ART / "model_sweep.md"
OUT_JSON = ART / "model_sweep_results.json"
MATCH_MODEL = "gpt-5.4"  # 고정 매칭단


def ext_scene(e: dict) -> str:
    parts = [e.get("scene_summary", "")]
    for g in e.get("gimulmul") or []:
        mm = ", ".join(g.get("missing_measures") or [])
        parts.append(f"[기인물] {g.get('name','')}: {g.get('observed_state','')} / 결여: {mm} / 예상사고: {g.get('expected_accident','')}")
    return "\n".join(p for p in parts if p).strip()


def main():
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
        lines = [f"[장면]\n{st}", "", "[후보 조]"]
        for c in cand:
            s = sig.get(c, {})
            lines.append(f"- [{kind[c]}] {c} {s.get('title','')} | {s.get('violation_scene','')[:90]}\n  전문: {(full.get(c,'') or '')[:160]}")
        rk = chat(RANK_SYS, "\n".join(lines) + "\n\n적용 조를 확신순 정렬.", RANK_SCHEMA)
        ranked = [x["article_code"] for x in rk["ranked"] if x["applies"] in ("yes", "maybe")]
        return photo, model, gks, ranked

    # 작업목록
    jobs = []
    for photo, bym in extractions.items():
        for model, res in bym.items():
            if "extraction" in res:
                jobs.append((photo, model, res["extraction"]))

    matched = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(match_one, p, m, e) for p, m, e in jobs]
        for fu in as_completed(futs):
            photo, model, gks, ranked = fu.result()
            matched[(photo, model)] = (gks, ranked)
            print(f"  matched {photo:<12} {model:<14} grp{len(gks)} ranked{len(ranked)}", flush=True)

    KS = [1, 3, 5, 10]

    def metrics(ranked, g):
        if not g:
            return None
        out = {"p1": 1.0 if ranked and ranked[0] in g else 0.0}
        for k in KS:
            out[f"hit{k}"] = 1.0 if set(ranked[:k]) & g else 0.0
            out[f"r{k}"] = len(set(ranked[:k]) & g) / len(g)
        return out

    # 모델별 집계
    models = sorted({m for _, m in matched})
    agg = {m: defaultdict(list) for m in models}
    extstat = {m: {"ngim": [], "ok": 0, "err": 0} for m in MODELS_ORDER if (m in models or True)}
    per_photo = defaultdict(dict)
    for photo, bym in extractions.items():
        for model, res in bym.items():
            if "extraction" not in res:
                if model in extstat:
                    extstat.setdefault(model, {"ngim": [], "ok": 0, "err": 0})["err"] += 1
                continue
            extstat.setdefault(model, {"ngim": [], "ok": 0, "err": 0})
            extstat[model]["ok"] += 1
            extstat[model]["ngim"].append(len(res["extraction"].get("gimulmul", [])))
            gks, ranked = matched.get((photo, model), ([], []))
            m = metrics(ranked, gold.get(photo, set()))
            per_photo[photo][model] = (ranked[:5], m)
            if m:
                for k, v in m.items():
                    agg[model][k].append(v)

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    md = ["# Stage1 기인물-first 모델 스윕 (매칭단 고정 gpt-5.4)", "",
          "| 모델 | 추출OK | 평균기인물 | P@1 | Hit@3 | Hit@5 | R@5 | R@10 |",
          "|---|---|---|---|---|---|---|---|"]
    print("\n=== 모델별 (매칭단 고정 gpt-5.4) ===")
    print(f"{'model':<14}{'P@1':>7}{'Hit@3':>7}{'Hit@5':>7}{'R@5':>7}{'R@10':>7}{'gim':>6}")
    order = [m for m in MODELS_ORDER if m in models] + [m for m in models if m not in MODELS_ORDER]
    summary = {}
    for m in order:
        a = agg[m]
        es = extstat.get(m, {"ngim": [], "ok": 0})
        ng = mean(es["ngim"])
        row = {"P@1": mean(a["p1"]), "Hit@3": mean(a["hit3"]), "Hit@5": mean(a["hit5"]),
               "R@5": mean(a["r5"]), "R@10": mean(a["r10"]), "ngim": ng, "ok": es["ok"]}
        summary[m] = row
        print(f"{m:<14}{row['P@1']:>7.1%}{row['Hit@3']:>7.1%}{row['Hit@5']:>7.1%}{row['R@5']:>7.1%}{row['R@10']:>7.1%}{ng:>6.1f}")
        md.append(f"| {m} | {es['ok']} | {ng:.1f} | {row['P@1']:.1%} | {row['Hit@3']:.1%} | {row['Hit@5']:.1%} | {row['R@5']:.1%} | {row['R@10']:.1%} |")

    md.append("\n## 사진별 top5 (모델별)")
    for photo in per_photo:
        md.append(f"\n### {photo}  (gold {sorted(gold.get(photo,set()))})")
        for m in order:
            if m in per_photo[photo]:
                top, mm = per_photo[photo][m]
                p1 = f"P@1={mm['p1']:.0f}" if mm else "-"
                md.append(f"- {m}: {top}  {p1}")

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"summary": summary, "match_model": MATCH_MODEL}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT_MD.name} / {OUT_JSON.name}")


MODELS_ORDER = ["gpt-4.1", "gpt-5-mini", "gpt-5-nano", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4"]

if __name__ == "__main__":
    main()
