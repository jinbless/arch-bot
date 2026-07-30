#!/usr/bin/env python3
"""cue-pool A/B 측정 — 실제 감독관 gold 사진에서 후보천장(cand_any) 비교.

세 후보생성 arm을 같은 Vision 출력에서 만들어 gold(match=y)와 조인:
  ① baseline  = gimulmul(RESOLVE→ASSEMBLE): 큐레이션 ∪ alias ∪ RESOLVE그룹 ∪ 횡단 (관찰가능)
  ② cue-pool  = cue-matcher(Vision텍스트→발화 cue→entry조문) [+flow 변형]
  ③ union     = ① ∪ ②(entry+flow)
지표: recall(=포착 y-코드/전체 y-코드), photo_any(≥1 gold 포착 사진율), photo_all(전 gold 포착), 평균 후보수.

Vision은 전체 한글 파일명 키로 intake_vision_gold.json에 **영구 저장**(재사용).
PG 불필요(RANK excerpt는 signature violation_scene 사용). Vision=gpt-4.1, RESOLVE=gpt-5.4.

사용: .venv/bin/python scripts/measure_cuepool_gold.py [--limit N] [--reuse-vision]
"""
from __future__ import annotations
import argparse, base64, csv, json, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402
from gimulmul_match import RESOLVE_SYS, RESOLVE_SCHEMA, CROSS  # noqa: E402
from intake_photos import VIS_SYS, VIS_SCHEMA, scene_text, data_url  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
SSOT = REPO / "docs" / "knowledge" / "감독관-판단기준"
GOLD_CSV = REPO / "real-test-photo" / "label_photo" / "label_curation_gold.csv"
PHOTO_DIR = REPO / "real-test-photo" / "label_photo"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
ALIAS = ART / "gimulmul_alias.json"
CURATED = REF / "parsed" / "case_rule_mapping.json"
OUT_VISION = ART / "intake_vision_gold.json"   # 영구 저장(한글명 키)
OUT_RESULTS = ART / "cuepool_ab_results.json"
RESOLVE_MODEL = "gpt-5.4"

# ── gold ──
def _norm_code(c):
    """gold CSV '조' 누락 오기 정규화(제45→제45조). 2026-07-30 발견."""
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


gold = {}
with GOLD_CSV.open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if (r.get("match") or "").strip().lower() == "y":
            gold.setdefault(r["photo_file"], set()).add(_norm_code(r["article_code"]))

# ── indices ──
idx = json.loads(INDEX.read_text(encoding="utf-8"))
groups = idx["groups"]
cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
sig = {json.loads(l)["article_code"]: json.loads(l) for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
alias = json.loads(ALIAS.read_text(encoding="utf-8")) if ALIAS.exists() else {}
curated = json.loads(CURATED.read_text(encoding="utf-8"))["gimulmul_articles"] if CURATED.exists() else {}
OBS_OK = ("yes", "partial")

def curated_lookup(gim):
    base = gim.split("(")[0].strip()
    for k, v in curated.items():
        if k.split("(")[0].strip() == base or base in k or k in base:
            return [a["code"] for a in v["articles"]]
    return []

catalog = []
for gk, g in groups.items():
    nobs = sum(1 for a in g["articles"] if a["observable"] in OBS_OK)
    if nobs >= 1 and gk not in idx["cross_cutting"]:
        catalog.append(f"{gk} ::기인물={g['gimulmul']} ({nobs}조)")
catalog_text = "\n".join(sorted(catalog))

# ── cue-pool matcher ──
cpool = json.loads((SSOT / "cue-pool.json").read_text(encoding="utf-8"))["cues"]
def cue_terms(c):
    ts = set()
    for a in c.get("aliases", []) + c.get("vision_keywords", []):
        a = a.strip()
        if len(a) >= 2:
            ts.add(a)
    can = re.split(r"[(/·]", c["canonical"])[0].strip()
    if len(can) >= 2:
        ts.add(can)
    return ts
CUE_TERMS = [(c, cue_terms(c)) for c in cpool]

def cue_candidates(res):
    parts = []
    for o in res.get("visual_observations", []): parts.append(o.get("text", ""))
    for o in res.get("visual_cues", []): parts.append(o.get("text", ""))
    for h in res.get("hazards", []):
        parts += [h.get("name", ""), h.get("description", ""), h.get("location", "")]
    txt = " | ".join(parts)
    entry, flow = set(), set()
    for c, ts in CUE_TERMS:
        if any(t in txt for t in ts):
            entry |= set(c.get("articles", []))
            flow |= set(c.get("flow_articles", []))
    # 관찰가능 필터(baseline과 동일 조건으로 공정 비교)
    entry = {a for a in entry if sig.get(a, {}).get("observable") in OBS_OK}
    flow = {a for a in flow if sig.get(a, {}).get("observable") in OBS_OK}
    return entry, flow

# ── OpenAI ──
_ensure_key()
from openai import OpenAI  # noqa: E402
client = OpenAI()

def vision(p):
    r = client.chat.completions.create(model="gpt-4.1", max_completion_tokens=3000, messages=[
        {"role": "system", "content": VIS_SYS},
        {"role": "user", "content": [{"type": "text", "text": "이 사진을 분석하라."},
                                     {"type": "image_url", "image_url": {"url": data_url(p)}}]}],
        response_format={"type": "json_schema", "json_schema": VIS_SCHEMA})
    return json.loads(r.choices[0].message.content)

def resolve(st):
    r = client.chat.completions.create(model=RESOLVE_MODEL, messages=[
        {"role": "system", "content": RESOLVE_SYS},
        {"role": "user", "content": f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n주요 기인물의 group_key 선택."}],
        response_format={"type": "json_schema", "json_schema": RESOLVE_SCHEMA})
    return json.loads(r.choices[0].message.content)

def baseline_candidates(rv):
    gks = [k for k in rv["group_keys"] if k in groups]
    gims = rv.get("gimulmul", [])
    cand = set()
    def add(code):
        if sig.get(code, {}).get("observable") in OBS_OK:
            cand.add(code)
    for gim in gims:
        for c in curated_lookup(gim): add(c)
        for gk in alias.get(gim, {}).get("group_keys", []):
            for a in groups.get(gk, {}).get("articles", []): add(a["code"])
    for gk in gks:
        for a in groups[gk]["articles"]: add(a["code"])
    for c in cross_set: add(c)
    return cand, gims, gks

def process(pf, cached_res=None):
    p = PHOTO_DIR / pf
    try:
        res = cached_res if cached_res is not None else vision(p)
        st = scene_text(res)
        rv = resolve(st)
    except Exception as e:  # noqa: BLE001
        return pf, {"error": str(e)[:200]}
    base, gims, gks = baseline_candidates(rv)
    entry, flow = cue_candidates(res)
    return pf, {"photo": pf, "industry": res.get("industry", ""), "result": res,
                "baseline": sorted(base), "cue_entry": sorted(entry), "cue_flow": sorted(flow),
                "gimulmul": gims, "group_keys": gks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reuse-vision", action="store_true", help="intake_vision_gold.json 있으면 Vision 재사용")
    args = ap.parse_args()

    photos = sorted(gold.keys())
    if args.limit:
        photos = photos[:args.limit]
    print(f"gold 사진 {len(photos)}장 측정 시작", flush=True)

    cache = {}
    if args.reuse_vision and OUT_VISION.exists():
        for rec in json.loads(OUT_VISION.read_text(encoding="utf-8"))["photos"]:
            cache[rec["photo"]] = rec["result"]

    recs = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(process, pf, cache.get(pf)) for pf in photos]
        for fu in as_completed(futs):
            pf, rec = fu.result()
            if "error" in rec:
                print(f"  ERR {pf[:30]}: {rec['error']}", flush=True); continue
            recs[pf] = rec
            g = gold[pf]
            bc = len(g & set(rec["baseline"])); cc = len(g & set(rec["cue_entry"]))
            print(f"  OK {pf[:34]} | gold {len(g)} base∩{bc} cue∩{cc} | 후보 base {len(rec['baseline'])} cue {len(rec['cue_entry'])}", flush=True)

    # ── Vision 영구 저장(한글명 키) ──
    vision_out = {"_note": "intake rich vision — gold 사진(한글 파일명 키)", "photos":
                  [{"photo": pf, "industry": r.get("industry", ""), "result": r["result"]}
                   for pf, r in recs.items() if "result" in r]}
    OUT_VISION.write_text(json.dumps(vision_out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 채점 ──
    scored = [pf for pf in photos if pf in recs and "baseline" in recs[pf]]
    def agg(key_fn):
        cap = tot = pany = pall = ncand = 0
        for pf in scored:
            g = gold[pf]; c = key_fn(recs[pf])
            hit = len(g & c)
            cap += hit; tot += len(g); ncand += len(c)
            pany += 1 if hit > 0 else 0
            pall += 1 if hit == len(g) else 0
        n = len(scored) or 1
        return {"recall": round(cap / (tot or 1), 3), "photo_any": round(pany / n, 3),
                "photo_all": round(pall / n, 3), "avg_cand": round(ncand / n, 1)}

    arms = {
        "baseline(gimulmul)": lambda r: set(r["baseline"]),
        "cue_entry": lambda r: set(r["cue_entry"]),
        "cue_entry+flow": lambda r: set(r["cue_entry"]) | set(r["cue_flow"]),
        "union(base∪cue_all)": lambda r: set(r["baseline"]) | set(r["cue_entry"]) | set(r["cue_flow"]),
    }
    metrics = {name: agg(fn) for name, fn in arms.items()}

    OUT_RESULTS.write_text(json.dumps({"n_photos": len(scored), "n_gold_codes": sum(len(gold[pf]) for pf in scored),
                                       "metrics": metrics, "per_photo": {pf: {"gold": sorted(gold[pf]),
                                       "baseline": recs[pf]["baseline"], "cue_entry": recs[pf]["cue_entry"],
                                       "cue_flow": recs[pf]["cue_flow"]} for pf in scored}}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== cue-pool A/B (gold {len(scored)}장 · y-코드 {sum(len(gold[pf]) for pf in scored)}) ===")
    print(f"{'arm':24} {'recall':>7} {'photo_any':>10} {'photo_all':>10} {'avg_cand':>9}")
    for name, m in metrics.items():
        print(f"{name:24} {m['recall']:>7.3f} {m['photo_any']:>10.3f} {m['photo_all']:>10.3f} {m['avg_cand']:>9.1f}")
    print(f"\nVision → {OUT_VISION.name} · 결과 → {OUT_RESULTS.name}")


if __name__ == "__main__":
    main()
