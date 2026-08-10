#!/usr/bin/env python3
"""A0 계측: RESOLVE 위치 편향(카탈로그 순서 셔플) + 언어화 confidence — 캐시 우회 러너.

왜 별도 러너인가 (적대적 검토 1·3번):
  - rerun_resolve_cache.py의 무효화 키는 **sorted(keys)의 SHA**라 카탈로그 줄 순서를
    바꿔도 캐시가 재사용된다 — 셔플이 LLM에 도달하지 못한 채 무셔플 결과를 침묵 보고한다.
  - 여기서는 (사진×팔) 키의 자체 캐시를 갖고, 매니페스트에 프롬프트·스키마·카탈로그 SHA를
    전부 적는다. 하나라도 다르면 캐시를 물러두고 처음부터 — 캐시가 스스로 낡음을 안다.

팔(arm) 구성 (사진당 6콜):
  orig       : 원순서(정렬) 1콜 — v2 캐시와 같은 조건의 신선한 재실행(시간 드리프트도 부수 측정)
  p1..p4     : 시드 고정 순열 4콜 — 순서 민감도
  conf       : 원순서 + confidence 스키마 포크 1콜 — 확신도-정답률 분리

사전등록 게이트 (실행 전 고정 — rank_ab_gold.NI_MARGIN 관행):
  G-SHUFFLE: exact 판정이 팔 간에 갈린 사진 비율 > 0.15
             AND 다수결(exact) - orig(exact) > +0.03  →  A1 '순서 무작위화+다수결' 후보
  G-CONF   : confidence < 70 버킷의 exact 오류율 − ≥70 버킷 오류율, bootstrap 95% CI 하한 > 0
             →  A1 '저확신 확인 유도' 후보

채점: measure_anchor_accuracy.py가 만든 anchor_accuracy.json의 per_photo truth(좌표)를
그대로 쓴다 — 채점 규칙을 두 곳에서 재계산하면 소리 없이 갈린다.

사용: .venv/bin/python scripts/measure_resolve_shuffle.py [--workers 6] [--limit 0]
출력: data-team/05-enrichment/runtime-artifacts/resolve_shuffle_report.json (+ 자체 캐시)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

import rank_ab_gold as R  # noqa: E402 — 프롬프트·모델·scene_text를 그대로(측정 조건 동일)

CACHE = R.ART / "resolve_shuffle_cache.json"
OUT = R.ART / "resolve_shuffle_report.json"
ACC = R.ART / "anchor_accuracy.json"

# ── 사전등록 게이트 (실행 전 고정 — 결과 보고 조정 금지) ────────────────
GATE_SHUFFLE_DISAGREE = 0.15
GATE_SHUFFLE_MAJ_GAIN = 0.03
GATE_CONF_THRESHOLD = 70
SEEDS = (1, 2, 3, 4)          # p1..p4 순열 시드

# confidence 포크 — 서빙 스키마는 건드리지 않는다(측정 전용, 적대적 검토 3번)
CONF_SYS = (R.RESOLVE_SYS +
            " 마지막으로 confidence(0~100 정수)에 '첫 번째로 고른 group_key가 사진의 주 기인물"
            " 그룹이 맞다'는 확신도를 적어라. 과신하지 말라 — 보기들이 비슷해 헷갈렸다면 낮게.")
CONF_SCHEMA = {"name": "resolve_conf", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "properties": {"gimulmul": {"type": "array", "items": {"type": "string"}},
                   "group_keys": {"type": "array", "items": {"type": "string"}},
                   "confidence": {"type": "integer"}},
    "required": ["gimulmul", "group_keys", "confidence"]}}


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


def _boot_diff(err_lo: list, err_hi: list, n=4000, seed=17):
    """저확신 오류율 − 고확신 오류율의 bootstrap CI."""
    rnd = random.Random(seed)
    pt = (sum(err_lo) / len(err_lo)) - (sum(err_hi) / len(err_hi))
    bs = []
    for _ in range(n):
        a = [err_lo[rnd.randrange(len(err_lo))] for _ in err_lo]
        b = [err_hi[rnd.randrange(len(err_hi))] for _ in err_hi]
        bs.append(sum(a) / len(a) - sum(b) / len(b))
    bs.sort()
    return pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    acc = json.loads(ACC.read_text(encoding="utf-8"))
    truth = {r["photo"]: {tuple(t) for t in r["truth"]} for r in acc["per_photo"]}
    vis = {r["photo"]: r["result"] for r in json.loads(R.IN_VISION.read_text(encoding="utf-8"))["photos"]}
    photos = sorted(p for p in truth if p in vis)
    if args.limit:
        photos = photos[:args.limit]

    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (R.ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((R.ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    gkey_coord = {k: {_coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
                  for k, g in gim.items()}

    lines = [l for l in R.catalog_text.splitlines() if l.strip()]
    cat_sha = hashlib.sha256("\n".join(sorted(l.split(" ::")[0] for l in lines)).encode()).hexdigest()[:12]
    manifest = {"catalog_sha": cat_sha, "model": R.MODEL,
                "prompt_sha": hashlib.sha256((R.RESOLVE_SYS + CONF_SYS).encode()).hexdigest()[:12],
                "schema_sha": hashlib.sha256(json.dumps(
                    [R.RESOLVE_SCHEMA, CONF_SCHEMA], sort_keys=True).encode()).hexdigest()[:12],
                "gates": {"shuffle_disagree": GATE_SHUFFLE_DISAGREE,
                          "shuffle_maj_gain": GATE_SHUFFLE_MAJ_GAIN,
                          "conf_threshold": GATE_CONF_THRESHOLD}}

    cache = {}
    if CACHE.exists():
        old = json.loads(CACHE.read_text(encoding="utf-8"))
        if old.get("_manifest") == manifest:
            cache = old.get("runs", {})
            print(f"자체 캐시 {len(cache)}런 재사용")
        else:
            bak = CACHE.with_suffix(".stale.json")
            bak.write_text(CACHE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"⚠ 매니페스트 변경 — 캐시 무효화({bak.name}로 물러둠)")

    def order_for(arm: str) -> list[str]:
        if arm in ("orig", "conf"):
            return lines
        perm = lines[:]
        random.Random(int(arm[1:])).shuffle(perm)
        return perm

    def call(photo: str, arm: str) -> dict:
        text = "\n".join(order_for(arm))
        sysp, schema = (CONF_SYS, CONF_SCHEMA) if arm == "conf" else (R.RESOLVE_SYS, R.RESOLVE_SCHEMA)
        rv = R.chat(sysp, f"[장면]\n{R.scene_text(vis[photo])}\n\n[기인물 그룹 카탈로그]\n{text}\n\n"
                          "주요 기인물의 group_key 선택.", schema)
        rv["_order_sha"] = hashlib.sha256(text.encode()).hexdigest()[:12]
        return rv

    arms = ["orig", *[f"p{s}" for s in SEEDS], "conf"]
    todo = [(p, a) for p in photos for a in arms if f"{p}||{a}" not in cache]
    print(f"사진 {len(photos)}장 × 팔 {len(arms)} = {len(photos)*len(arms)}런 (신규 {len(todo)})")

    fails = []
    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(call, p, a): (p, a) for p, a in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                p, a = futs[fu]
                try:
                    cache[f"{p}||{a}"] = fu.result()
                except Exception as e:  # noqa: BLE001
                    fails.append({"photo": p, "arm": a, "err": str(e)[:160]})
                if i % 30 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
                    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache},
                                                ensure_ascii=False), encoding="utf-8")
    CACHE.write_text(json.dumps({"_manifest": manifest, "runs": cache}, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    # ── 채점 ──
    def pred_coords(rv) -> set:
        out = set()
        for gk in (g.split(" ::")[0].strip() for g in (rv or {}).get("group_keys", [])):
            out |= gkey_coord.get(gk, set())
        return out

    def exact(photo, rv) -> bool:
        return bool(truth[photo] & pred_coords(rv))

    per_photo, conf_rows = [], []
    for p in photos:
        runs = {a: cache.get(f"{p}||{a}") for a in arms}
        if any(v is None for v in runs.values()):
            continue
        hits = {a: exact(p, runs[a]) for a in ["orig", *[f"p{s}" for s in SEEDS]]}
        firsts = [(runs[a].get("group_keys") or [""])[0].split(" ::")[0] for a in
                  ["orig", *[f"p{s}" for s in SEEDS]]]
        # 다수결: 5팔에서 3회 이상 등장한 group_key의 좌표 합집합으로 채점
        pool = Counter(gk.split(" ::")[0] for a in ["orig", *[f"p{s}" for s in SEEDS]]
                       for gk in runs[a].get("group_keys", []))
        maj_keys = [k for k, n in pool.items() if n >= 3]
        maj_coords = set().union(*(gkey_coord.get(k, set()) for k in maj_keys)) if maj_keys else set()
        per_photo.append({
            "photo": p, "hits": hits, "first_keys": firsts,
            "disagree_exact": len(set(hits.values())) > 1,
            "disagree_first": len(set(firsts)) > 1,
            "majority_exact": bool(truth[p] & maj_coords),
            "conf": runs["conf"].get("confidence"),
            "conf_exact": exact(p, runs["conf"]),
        })
        conf_rows.append((runs["conf"].get("confidence", 0), exact(p, runs["conf"])))

    n = len(per_photo)
    orig_acc = sum(1 for r in per_photo if r["hits"]["orig"]) / n
    perm_accs = {a: sum(1 for r in per_photo if r["hits"][a]) / n for a in [f"p{s}" for s in SEEDS]}
    maj_acc = sum(1 for r in per_photo if r["majority_exact"]) / n
    disagree_exact = sum(1 for r in per_photo if r["disagree_exact"]) / n
    disagree_first = sum(1 for r in per_photo if r["disagree_first"]) / n
    v2_acc = acc["exact_match"]["point"]

    lo = [(c, ok) for c, ok in conf_rows if (c or 0) < GATE_CONF_THRESHOLD]
    hi = [(c, ok) for c, ok in conf_rows if (c or 0) >= GATE_CONF_THRESHOLD]
    conf_gate = None
    if lo and hi:
        d, ci_l, ci_h = _boot_diff([0.0 if ok else 1.0 for _, ok in lo],
                                   [0.0 if ok else 1.0 for _, ok in hi])
        conf_gate = {"n_low": len(lo), "n_high": len(hi),
                     "err_low": round(sum(0.0 if ok else 1.0 for _, ok in lo) / len(lo), 3),
                     "err_high": round(sum(0.0 if ok else 1.0 for _, ok in hi) / len(hi), 3),
                     "diff": round(d, 3), "ci95": [round(ci_l, 3), round(ci_h, 3)],
                     "pass": ci_l > 0}

    shuffle_gate = {"disagree_exact": round(disagree_exact, 3),
                    "maj_gain_vs_orig": round(maj_acc - orig_acc, 3),
                    "pass": disagree_exact > GATE_SHUFFLE_DISAGREE and
                            (maj_acc - orig_acc) > GATE_SHUFFLE_MAJ_GAIN}

    report = {"_manifest": manifest, "n": n, "fails": fails,
              "acc": {"v2_cache": v2_acc, "orig_fresh": round(orig_acc, 3),
                      "perms": {k: round(v, 3) for k, v in perm_accs.items()},
                      "majority": round(maj_acc, 3)},
              "disagreement": {"exact": round(disagree_exact, 3), "first_key": round(disagree_first, 3)},
              "gate_shuffle": shuffle_gate, "gate_conf": conf_gate,
              "conf_hist": Counter((r["conf"] or 0) // 10 * 10 for r in per_photo).most_common(),
              "per_photo": per_photo}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== RESOLVE 셔플·confidence 계측 (채점 {n}장, 실패 {len(fails)}런) ===")
    print(f"  v2 캐시 exact        {v2_acc:.3f}  (기존 계측)")
    print(f"  원순서 재실행 exact  {orig_acc:.3f}  (드리프트 = {orig_acc - v2_acc:+.3f})")
    for k, v in perm_accs.items():
        print(f"  순열 {k} exact       {v:.3f}")
    print(f"  다수결 exact         {maj_acc:.3f}")
    print(f"  팔 간 exact 불일치   {disagree_exact:.1%} · 첫 키 불일치 {disagree_first:.1%}")
    print(f"  G-SHUFFLE: {'PASS' if shuffle_gate['pass'] else 'FAIL'} {shuffle_gate}")
    print(f"  G-CONF   : {conf_gate}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
