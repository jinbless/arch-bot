#!/usr/bin/env python3
"""USE 1 — 기인물→절/관 alias 사전 (resolution 강화).

실제 사고데이터의 기인물 어휘(SIF gimulmul + 사례 품목)를 산업안전보건규칙 절/관 group_key로
매핑. RESOLVE를 "사전 조회(결정적) + LLM(미등록만)"으로 만들어 프레스↔사출·굴착기/백호 등
resolution 드리프트를 고정(A 후퇴 원인 보완).

산출:
  gimulmul_alias.json        {term: {group_keys:[...], freq, sources:[...]}}
  gimulmul_alias_review.csv  빈도 상위(사람 검수: CONFIRM 열에 ok / 정정 group_key)

사람 검수분이 신뢰 사전. 롱테일은 LLM 매핑 유지.

사용: .venv/bin/python scripts/build_gimulmul_alias.py [--review-top 150]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
INDEX = ART / "gimulmul_index.json"
SIF = REF / "parsed" / "sif_archive.jsonl"
CASE_CSV = REF / "기인물_사례별.csv"
OUT_JSON = ART / "gimulmul_alias.json"
OUT_CSV = ART / "gimulmul_alias_review.csv"
MODEL = "gpt-5.4"

SKIP = {"", "분류 불가", "미분류", "복합사례집·가이드", "기타", "기타(명시)"}

SYS = (
    "너는 대한민국 산업안전보건규칙 전문가다. '기인물 어휘 목록'과 '규칙 절/관 그룹 카탈로그'를 받는다. "
    "각 기인물 어휘를, 그 기인물(설비·기계·물질·구조물·작업)을 규율하는 절/관 group_key로 매핑하라. "
    "가장 정확한 1개(모호하면 최대 2개). 반드시 카탈로그에 있는 group_key 문자열 그대로. "
    "예: 백호/포크레인→굴착기 절, 시저리프트→고소작업대 절, 프레스↔사출성형기는 서로 다른 절로 구분. "
    "구조적 기인물(개구부·단부·지붕)은 추락 관련 절. 적합 그룹이 없으면 group_keys=[].")

SCHEMA = {"name": "alias", "strict": True, "schema": {"type": "object", "additionalProperties": False,
    "properties": {"mappings": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": {"term": {"type": "string"}, "group_keys": {"type": "array", "items": {"type": "string"}}},
        "required": ["term", "group_keys"]}}}, "required": ["mappings"]}}


def collect_terms():
    freq = Counter()
    src = {}
    for l in SIF.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        g = json.loads(l).get("gimulmul", "").strip()
        if g and g not in SKIP:
            freq[g] += 1
            src.setdefault(g, set()).add("SIF")
    if CASE_CSV.exists():
        for r in csv.DictReader(CASE_CSV.open(encoding="utf-8-sig")):
            g = (r.get("기인물_품목") or "").strip()
            if g and g not in SKIP:
                freq[g] += 1
                src.setdefault(g, set()).add("case")
    return freq, src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review-top", type=int, default=150)
    args = ap.parse_args()

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    groups = idx["groups"]
    cross = set(idx["cross_cutting"])
    catalog = []
    for gk, g in groups.items():
        tag = "[횡단]" if gk in cross else ""
        catalog.append(f"{gk} ::기인물={g['gimulmul']}{tag}")
    catalog_text = "\n".join(sorted(catalog))
    valid_gk = set(groups)

    freq, src = collect_terms()
    terms = [t for t, _ in freq.most_common()]
    print(f"distinct 기인물 어휘 {len(terms)}종 → 매핑(model={MODEL})")

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    def map_chunk(chunk):
        user = ("[기인물 어휘 목록]\n" + "\n".join(f"- {t}" for t in chunk) +
                "\n\n[규칙 절/관 그룹 카탈로그]\n" + catalog_text +
                "\n\n각 어휘를 group_key로 매핑.")
        r = client.chat.completions.create(model=MODEL, messages=[
            {"role": "system", "content": SYS}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": SCHEMA})
        return json.loads(r.choices[0].message.content)["mappings"]

    CH = 25
    chunks = [terms[i:i + CH] for i in range(0, len(terms), CH)]
    alias = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(map_chunk, c): c for c in chunks}
        done = 0
        for fu in as_completed(futs):
            for m in fu.result():
                t = m["term"]
                gks = [g for g in m["group_keys"] if g in valid_gk]
                if t in freq:
                    alias[t] = {"group_keys": gks, "freq": freq[t], "sources": sorted(src.get(t, []))}
            done += 1
            print(f"  chunk {done}/{len(chunks)}", flush=True)

    # 미매핑 보충(누락 term)
    for t in terms:
        alias.setdefault(t, {"group_keys": [], "freq": freq[t], "sources": sorted(src.get(t, []))})

    # 2차 복구 패스 — 1차 미매핑 중 빈출(freq≥3)을 작은 청크+강한 지시로 재매핑(크레인/리프트 등 누락 보완)
    recover = [t for t in terms if not alias[t]["group_keys"] and freq[t] >= 3]
    if recover:
        rsys = (SYS + " 이 어휘들은 1차에서 미매핑됐다. 양중기 하위(크레인·이동식크레인·호이스트·리프트·곤돌라), "
                "건설기계(천공기·로더·롤러), 비계 종류, 흙막이/붕괴, 줄걸이/와이어로프 등 반드시 가장 가까운 절/관을 찾아라. "
                "정말로 해당 없을 때만 빈 배열.")
        rchunks = [recover[i:i + 10] for i in range(0, len(recover), 10)]

        def rmap(chunk):
            user = ("[기인물 어휘 목록]\n" + "\n".join(f"- {t}" for t in chunk) +
                    "\n\n[규칙 절/관 그룹 카탈로그]\n" + catalog_text + "\n\n각 어휘를 group_key로 매핑.")
            r = client.chat.completions.create(model=MODEL, messages=[
                {"role": "system", "content": rsys}, {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": SCHEMA})
            return json.loads(r.choices[0].message.content)["mappings"]
        rec_n = 0
        with ThreadPoolExecutor(max_workers=6) as ex:
            for fu in as_completed([ex.submit(rmap, c) for c in rchunks]):
                for m in fu.result():
                    t = m["term"]
                    gks = [g for g in m["group_keys"] if g in valid_gk]
                    if t in alias and gks and not alias[t]["group_keys"]:
                        alias[t]["group_keys"] = gks
                        rec_n += 1
        print(f"  2차 복구: {rec_n}/{len(recover)}종 추가 매핑")

    OUT_JSON.write_text(json.dumps(alias, ensure_ascii=False, indent=1), encoding="utf-8")

    # 검수 시트(빈도순 상위)
    def glabel(gk):
        return groups.get(gk, {}).get("gimulmul", "")
    top = sorted(alias.items(), key=lambda kv: -kv[1]["freq"])[:args.review_top]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["term", "freq", "sources", "group_keys", "group_labels", "CONFIRM(ok/정정 group_key)"])
        for t, v in top:
            w.writerow([t, v["freq"], "/".join(v["sources"]),
                        " | ".join(v["group_keys"]),
                        " | ".join(glabel(g) for g in v["group_keys"]), ""])

    mapped = sum(1 for v in alias.values() if v["group_keys"])
    print(f"\nalias {len(alias)}종 (매핑됨 {mapped}, 미매핑 {len(alias)-mapped}) → {OUT_JSON.name}")
    print(f"검수 시트 top{args.review_top} → {OUT_CSV.name}")
    print("\n[빈도 상위 20 매핑 샘플]")
    for t, v in top[:20]:
        print(f"  {v['freq']:>4} {t:<20} → {' | '.join(v['group_keys']) or '(미매핑)'}")


if __name__ == "__main__":
    main()
