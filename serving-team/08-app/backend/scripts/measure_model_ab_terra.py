#!/usr/bin/env python3
"""모델 A/B — 현행(vision gpt-4.1 + RESOLVE gpt-5.4) vs terra(둘 다 gpt-5.6-terra).

배경: 사용자 실험 요청(2026-08-10) — "서빙 이미지 분석과 RESOLVE 모두 gpt-5.6 terra로
바꿔서 다시 측정". 프롬프트(VIS_SYS v2 체크리스트·RESOLVE_SYS)·카탈로그·채점 규칙은
현행과 완전 동일하게 고정하고 **모델만** 바꾼다 — 차이가 나오면 모델 몫이다.

A/B 설계:
  A(현행) = anchor_accuracy.json per_photo (정식 계측 결과 그대로 — 재호출 없음)
  B(terra)= gpt-5.6-terra로 Vision 재판독 → gpt-5.6-terra로 RESOLVE → 같은 채점
  비교    = exact·flow_valid의 사진 단위 flip

★ 정본 보호: intake_vision_gold.json·rank_ab_resolve_cache_v2.json은 건드리지 않는다.
  자체 캐시(terra_ab_cache.json)는 매니페스트(모델명·프롬프트·카탈로그 SHA)로 자기 무효화.

사용: .venv/bin/python scripts/measure_model_ab_terra.py [--workers 4]
      [--vision-model gpt-5.6-terra] [--resolve-model gpt-5.6-terra]
출력: runtime-artifacts/terra_ab_report.json (+ 자체 캐시 terra_ab_cache.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

import intake_photos as IP          # noqa: E402 — VIS_SYS(v2)·VIS_SCHEMA·data_url
import rank_ab_gold as R            # noqa: E402 — RESOLVE 프롬프트·카탈로그·scene_text
from measure_anchor_accuracy import norm_gk  # noqa: E402 — 서빙과 같은 키 정규화

ART = R.ART
PHOTO_DIR = R.REPO / "real-test-photo" / "label_photo"
ACC = ART / "anchor_accuracy.json"
CACHE = ART / "terra_ab_cache.json"
OUT = ART / "terra_ab_report.json"


def _coord(section: str) -> tuple:
    p = j = jeol = gwan = None
    for tok in re.split(r"[>\s]+", section or ""):
        m = re.match(r"(편|장|절|관)(\d+)", tok.strip())
        if not m:
            continue
        lvl, n = m.group(1), int(m.group(2))
        p, j, jeol, gwan = (n, j, jeol, gwan) if lvl == "편" else (p, n, jeol, gwan) if lvl == "장" \
            else (p, j, n, gwan) if lvl == "절" else (p, j, jeol, n)
    return (p, j, jeol, gwan)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--vision-model", default="gpt-5.6-terra")
    ap.add_argument("--resolve-model", default="gpt-5.6-terra")
    args = ap.parse_args()

    assert "관찰 체크리스트" in IP.VIS_SYS, "VIS_SYS가 v2가 아니다 — intake_photos부터 확인"

    acc = json.loads(ACC.read_text(encoding="utf-8"))
    per_a = {r["photo"]: r for r in acc["per_photo"]}
    photos = sorted(per_a)
    truth = {p: {tuple(t) for t in per_a[p]["truth"]} for p in photos}

    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    gkey_coord = {k: {_coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
                  for k, g in gim.items()}
    flow_refs_by_key: dict[str, set] = {}
    for fr in json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))["rows"]:
        refs = {m.group(0) for its in (fr.get("items") or {}).values() for it in its
                if (m := re.match(r"제\d+조(의\d+)?", (it.get("ref") or "").strip()))}
        for kk in {fr.get("src_key"), fr.get("no")}:
            if kk:
                flow_refs_by_key.setdefault(kk, set()).update(refs)
    import csv as _csv
    gold_arts: dict[str, set] = {}
    with (R.REPO / "real-test-photo" / "label_photo" / "label_curation_gold_v2.csv").open(encoding="utf-8-sig") as f:
        for row in _csv.DictReader(f):
            if (row.get("match") or "").strip().lower() == "y":
                c = row["article_code"].strip()
                m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
                if m and not m.group(2):
                    c = f"제{m.group(1)}조"
                gold_arts.setdefault(row["photo_file"], set()).add(c)

    manifest = {"vision_model": args.vision_model, "resolve_model": args.resolve_model,
                "vis_sys_sha": hashlib.sha256(IP.VIS_SYS.encode()).hexdigest()[:12],
                "catalog_sha": hashlib.sha256("\n".join(sorted(R.catalog_text.splitlines())).encode()).hexdigest()[:12]}
    cache = {}
    if CACHE.exists():
        old = json.loads(CACHE.read_text(encoding="utf-8"))
        if old.get("_manifest") == manifest:
            cache = old.get("runs", {})
            print(f"자체 캐시 {len(cache)}장 재사용")
        else:
            print("⚠ 매니페스트 변경(모델·프롬프트·카탈로그) — 캐시 재실행")

    from openai import OpenAI
    client = OpenAI(max_retries=3, timeout=300.0)

    # terra류 reasoning 모델은 max_completion_tokens 여유가 필요(bbox 프로브 전례 12000)
    def run_one(name: str) -> dict:
        p = PHOTO_DIR / name
        if not p.exists():
            return {"error": "file_not_found"}
        r = client.chat.completions.create(model=args.vision_model, max_completion_tokens=12000, messages=[
            {"role": "system", "content": IP.VIS_SYS},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": IP.data_url(p)}}]}],
            response_format={"type": "json_schema", "json_schema": IP.VIS_SCHEMA})
        vis = json.loads(r.choices[0].message.content)
        st = R.scene_text(vis)
        r2 = client.chat.completions.create(model=args.resolve_model, max_completion_tokens=12000, messages=[
            {"role": "system", "content": R.RESOLVE_SYS},
            {"role": "user", "content": f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{R.catalog_text}\n\n"
                                        "주요 기인물의 group_key 선택."}],
            response_format={"type": "json_schema", "json_schema": R.RESOLVE_SCHEMA})
        rv = json.loads(r2.choices[0].message.content)
        return {"vision": vis, "resolve": rv}

    todo = [p for p in photos if p not in cache]
    print(f"사진 {len(photos)}장 (신규 {len(todo)}) · vision={args.vision_model} · resolve={args.resolve_model}")
    fails = []
    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(run_one, p): p for p in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                name = futs[fu]
                try:
                    cache[name] = fu.result()
                except Exception as e:  # noqa: BLE001
                    fails.append({"photo": name, "err": str(e)[:200]})
                if i % 5 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache},
                                                ensure_ascii=False), encoding="utf-8")
    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache}, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    # ── 채점 (measure_anchor_accuracy / vision_v2_ab와 동일 규칙) ──
    cat_set = {l.split(" ::")[0].strip() for l in R.catalog_text.splitlines() if l.strip()}
    rows = []
    for p in photos:
        run = cache.get(p)
        if not run or "resolve" not in run:
            continue
        picked = [norm_gk(g, cat_set) for g in run["resolve"].get("group_keys", [])]
        pred = set().union(*(gkey_coord.get(k, set()) for k in picked)) if picked else set()
        exact_b = bool(truth[p] & pred)
        frefs = set().union(*(flow_refs_by_key.get(k, set()) for k in picked)) if picked else set()
        flow_b = exact_b or bool(gold_arts.get(p, set()) & frefs)
        rows.append({"photo": p, "exact_b": exact_b, "flow_b": flow_b,
                     "exact_a": per_a[p]["exact"], "flow_a": per_a[p].get("flow_valid", per_a[p]["exact"]),
                     "picked_b": picked})
    n = len(rows)
    if not n:
        raise SystemExit(f"채점 0장 — 실패 {len(fails)}건: {fails[:3]}")
    ea = sum(1 for r in rows if r["exact_a"]) / n
    eb = sum(1 for r in rows if r["exact_b"]) / n
    fa = sum(1 for r in rows if r["flow_a"]) / n
    fb = sum(1 for r in rows if r["flow_b"]) / n
    fixed = [r["photo"] for r in rows if r["exact_b"] and not r["exact_a"]]
    broke = [r["photo"] for r in rows if not r["exact_b"] and r["exact_a"]]
    ffixed = [r["photo"] for r in rows if r["flow_b"] and not r["flow_a"]]
    fbroke = [r["photo"] for r in rows if not r["flow_b"] and r["flow_a"]]

    OUT.write_text(json.dumps({"_manifest": manifest, "n": n, "fails": fails,
                               "exact": {"A": round(ea, 3), "B": round(eb, 3)},
                               "flow_valid": {"A": round(fa, 3), "B": round(fb, 3)},
                               "exact_fixed": fixed, "exact_broke": broke,
                               "flow_fixed": ffixed, "flow_broke": fbroke,
                               "per_photo": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== 모델 A/B: 현행 vs {args.vision_model} (채점 {n}장, 실패 {len(fails)}) ===")
    print(f"  exact      A {ea:.3f} → B {eb:.3f}")
    print(f"  flow_valid A {fa:.3f} → B {fb:.3f}")
    print(f"  exact 회복 {len(fixed)}: {[p[:34] for p in fixed]}")
    print(f"  exact 악화 {len(broke)}: {[p[:34] for p in broke]}")
    print(f"  flow 회복 {len(ffixed)} / 악화 {len(fbroke)}: {[p[:34] for p in fbroke]}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
