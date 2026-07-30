#!/usr/bin/env python3
"""변별 프로브 — H1(추출/전달) vs H2(랭킹) 분리 결정 실험.

배경: 본 랭킹 A/B에서 arm B top1 129장 = 정답 57 / 천장밖 9 / **미판정 51(40%)** / 판정된 오답 12.
"오답"의 71%가 실은 큐레이터가 판정한 적 없는 코드라 P@1이 변별력을 재지 못한다.
→ 본 프로브는 **큐레이터가 y/n을 실제로 매긴 코드만** 후보로 제시해 후보생성·미판정 노이즈를 제거하고
   **순수 변별력**만 측정한다. 추가 라벨링 0.

주지표 JPA(judged pair ordering accuracy) = 같은 사진의 (y코드, n코드) 쌍에서 y가 위에 온 비율.
사진 클러스터 부트스트랩(감독건 pjts_id 클러스터도 병기).

조건(arm) — 누적 적용, 차이는 **랭커 입력뿐**:
  P0 현행            : scene_text v1(observations+cues+hazard.name) · 렌더 v1(코드 제목 | violation_scene90 + 전문160 절단)
  P1 +정보배관       : scene_text v2(+hazards.location/description)      ← H1-a 검정
  P2 +근거렌더       : 렌더 v2(section 노출 + 전문 호(號) 발췌, 고정절단 폐기)  ← H3' 검정
해석: P0가 이미 높으면 H2(랭킹) 소규모 확정. P1/P2에서 오르면 H1-a/H3'가 원인으로 확정.

⚠ 조건부 규칙(제13조 분기 등)은 **프롬프트에 넣지 않는다** — arm C 실패 교훈(조건이 입력에 없으면
   조건절이 상수로 붕괴해 귀결절만 실행됨). 여기서는 '근거 복원'만 하고 지시는 추가하지 않는다.

사용: .venv/bin/python scripts/probe_discrimination.py [--reps 4] [--arms P0,P1,P2] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from build_article_signatures import _ensure_key  # noqa: E402
from gimulmul_match import RANK_SYS, RANK_SCHEMA  # noqa: E402

RANK_SYS_BLIND = RANK_SYS.replace("[기인물] 표시 조와 구체 위험조 우선.", "구체 위험조 우선.")
assert RANK_SYS_BLIND != RANK_SYS and "[기인물]" not in RANK_SYS_BLIND, "RANK_SYS 치환 실패"

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
GOLD_CSV = REPO / "real-test-photo" / "label_photo" / "label_curation_gold.csv"
SIGS = ART / "article_signatures.jsonl"
ARTICLES = REPO / "data-team" / "02-extraction" / "pipe-A" / "data" / "article-texts.json"
IN_VISION = ART / "intake_vision_gold.json"
OUT = ART / "probe_discrimination.json"
OUT_MD = ART / "probe_discrimination.md"
MODEL = "gpt-5.4"
NI_MARGIN = -0.03   # 사전지정 비열등 마진(JPA)

SIB = {"제13조", "제30조", "제42조", "제43조", "제44조", "제45조", "제56조", "제68조"}

# ── 판정 라벨(y/n) ──
def _norm_code(c):
    """gold CSV '조' 누락 오기 정규화(제45→제45조). 2026-07-30 발견."""
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


jy, jn, pjts = defaultdict(set), defaultdict(set), {}
with GOLD_CSV.open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        m = (r.get("match") or "").strip().lower()
        pf, code = r["photo_file"], _norm_code(r["article_code"])
        pjts[pf] = r.get("pjts_id", "")
        if m == "y":
            jy[pf].add(code)
        elif m == "n":
            jn[pf].add(code)

sig = {json.loads(l)["article_code"]: json.loads(l) for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
RULE_FULL = json.loads(ARTICLES.read_text(encoding="utf-8"))["laws"]["RULE"]
vis = {r["photo"]: r["result"] for r in json.loads(IN_VISION.read_text(encoding="utf-8"))["photos"]}


# ── 장면 텍스트 ──
def scene_v1(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def scene_v2(res):
    """H1-a 수정: hazards의 location·description을 포함(현행은 name만 → Vision 산출 52.9% 유실)."""
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    hz = []
    for h in res.get("hazards") or []:
        loc = (h.get("location") or "").strip()
        desc = (h.get("description") or "").strip()
        hz.append(f"{h.get('name','')}" + (f"[{loc}]" if loc else "") + (f" {desc}" if desc else ""))
    return f"{obs} 시각단서: {cues} 위험: {'; '.join(hz)}".strip()


# ── 후보 렌더 ──
def full_text(code):
    return (RULE_FULL.get(code, {}) or {}).get("fullText", "") or ""


HO_KEY = re.compile(r"안전난간|덮개|울타리|추락방호망|안전대|발끝막이|중간난간|난간대|폭|틈|고정|설치할 것|착용|표시")


def excerpt_v2(code, head=110, max_ho=2):
    """고정 절단 폐기: 본문 머리 + 관찰가능 의무를 담은 호(號) 최대 2개."""
    t = full_text(code)
    if not t:
        return ""
    parts = [p.strip() for p in t.split("\n") if p.strip()]
    out = [parts[0][:head]] if parts else []
    picked = 0
    for p in parts[1:]:
        if picked >= max_ho:
            break
        if HO_KEY.search(p):
            out.append(p[:120])
            picked += 1
    return " / ".join(out)


def render_v1(code):
    s = sig.get(code, {})
    return (f"- {code} {s.get('title','')} | {(s.get('violation_scene','') or '')[:90]}\n"
            f"  전문: {full_text(code)[:160]}")


def render_v2(code):
    """H3' 수정: section(장/절) 노출 + 호 발췌."""
    s = sig.get(code, {})
    sec = (s.get("section") or RULE_FULL.get(code, {}).get("section") or "")
    seg = [x.strip() for x in sec.split(">")]
    sec_short = " > ".join(seg[1:3]) if len(seg) >= 3 else sec
    return (f"- {code} {s.get('title','')} 〈{sec_short}〉 | {(s.get('violation_scene','') or '')[:90]}\n"
            f"  조문: {excerpt_v2(code)}")


ARMS = {
    "P0": (scene_v1, render_v1),
    "P1": (scene_v2, render_v1),
    "P2": (scene_v2, render_v2),
}

# ── OpenAI ──
_ensure_key()
from openai import OpenAI  # noqa: E402

client = OpenAI(max_retries=5, timeout=180.0)


def do_rank(scene, codes, render):
    lines = [f"[장면]\n{scene}", "", "[후보 조]"] + [render(c) for c in codes]
    user = "\n".join(lines) + "\n\n적용 조를 확신순 정렬."
    r = client.chat.completions.create(model=MODEL, messages=[
        {"role": "system", "content": RANK_SYS_BLIND}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": RANK_SCHEMA})
    rk = json.loads(r.choices[0].message.content)
    valid = set(codes)
    order = [x["article_code"] for x in rk["ranked"] if x["article_code"] in valid]
    # 누락 코드는 뒤에 원순서로 append(순위 미지정 = 최하위 취급)
    order += [c for c in codes if c not in order]
    return order


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def jpa_of(order, ys, ns):
    """(y,n) 쌍에서 y가 위에 온 비율 + 쌍 수."""
    pos = {c: i for i, c in enumerate(order)}
    win = tot = 0
    for y in ys:
        for n in ns:
            if y in pos and n in pos:
                tot += 1
                win += 1 if pos[y] < pos[n] else 0
    return (win / tot if tot else None), tot


def cluster_boot(units, n=4000, seed=17):
    """units=[(win,tot)] 클러스터(사진/감독건) 단위 리샘플 → JPA CI."""
    rnd = random.Random(seed)
    N = len(units)
    if N == 0:
        return (0.0, 0.0, 0.0)
    pt = sum(w for w, t in units) / max(1, sum(t for w, t in units))
    bs = []
    for _ in range(n):
        s = [units[rnd.randrange(N)] for _ in range(N)]
        tot = sum(t for w, t in s)
        bs.append(sum(w for w, t in s) / tot if tot else 0.0)
    bs.sort()
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def paired_boot(pairs, n=4000, seed=17):
    """pairs=[(win_a,tot,win_b)] 사진 단위 페어드 → ΔJPA CI."""
    rnd = random.Random(seed)
    N = len(pairs)
    if N == 0:
        return (0.0, 0.0, 0.0)

    def d(s):
        tot = sum(t for _, t, _ in s)
        return (sum(b for _, _, b in s) - sum(a for a, _, _ in s)) / tot if tot else 0.0

    pt = d(pairs)
    bs = sorted(d([pairs[rnd.randrange(N)] for _ in range(N)]) for _ in range(n))
    return (pt, bs[int(0.025 * n)], bs[int(0.975 * n) - 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4, help="짝수 — 홀수 rep은 후보 제시 역순")
    ap.add_argument("--arms", default="P0,P1,P2")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if args.reps % 2:
        sys.exit("--reps는 짝수(정순/역순 균형)")
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]

    # 채점 가능한 사진 = y·n 둘 다 있고 Vision 보유
    photos = sorted([p for p in vis if jy.get(p) and jn.get(p)])
    if args.limit:
        photos = photos[:args.limit]
    tot_pairs = sum(len(jy[p]) * len(jn[p]) for p in photos)
    sib_photos = [p for p in photos if (jy[p] & SIB) and (jn[p] & SIB)]
    sib_pairs = sum(len(jy[p] & SIB) * len(jn[p] & SIB) for p in sib_photos)
    print(f"채점가능 {len(photos)}장 · 판정쌍 {tot_pairs} · 형제쌍 {sib_pairs}({len(sib_photos)}장) · arms={arms} reps={args.reps}", flush=True)

    # 후보 = 판정된 코드 전부(조번호순; 홀수 rep 역순)
    def cand_of(pf):
        return sorted(jy[pf] | jn[pf], key=lambda c: (int(re.match(r"제(\d+)", c).group(1)) if re.match(r"제(\d+)", c) else 9999, c))

    jobs = [(pf, arm, rep) for arm in arms for rep in range(args.reps) for pf in photos]
    print(f"프로브 호출 {len(jobs)}건 시작", flush=True)
    res, fails = {}, []

    def _run(job):
        pf, arm, rep = job
        sfn, rfn = ARMS[arm]
        codes = cand_of(pf)
        if rep % 2:
            codes = codes[::-1]
        return job, do_rank(sfn(vis[pf]), codes, rfn)

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_run, j): j for j in jobs}
        for fu in as_completed(futs):
            job = futs[fu]
            try:
                _, order = fu.result()
                res[job] = order
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": job[0], "arm": job[1], "rep": job[2], "err": str(e)[:200]})
                print(f"  ERR {job[1]}/rep{job[2]} {job[0][:26]}: {str(e)[:110]}", flush=True)
            done += 1
            if done % 100 == 0:
                print(f"  ... {done}/{len(jobs)}", flush=True)

    # 사진×arm = rep 평균(win/tot)
    per = defaultdict(dict)
    for arm in arms:
        for pf in photos:
            ords = [res[(pf, arm, r)] for r in range(args.reps) if (pf, arm, r) in res]
            if len(ords) != args.reps:
                continue
            ws, ts = [], 0
            for o in ords:
                v, t = jpa_of(o, jy[pf], jn[pf])
                ws.append((v or 0) * t); ts = t
            per[pf][arm] = {"win": mean(ws), "tot": ts}
            # 형제 부분집합
            sy, sn = jy[pf] & SIB, jn[pf] & SIB
            if sy and sn:
                sw = []
                for o in ords:
                    v, t = jpa_of(o, sy, sn)
                    sw.append((v or 0) * t); st = t
                per[pf][arm + "_sib"] = {"win": mean(sw), "tot": st}

    scored = [p for p in photos if all(a in per[p] for a in arms)]
    agg, aggs = {}, {}
    for arm in arms:
        units = [(per[p][arm]["win"], per[p][arm]["tot"]) for p in scored]
        agg[arm] = cluster_boot(units)
        su = [(per[p][arm + "_sib"]["win"], per[p][arm + "_sib"]["tot"]) for p in scored if arm + "_sib" in per[p]]
        aggs[arm] = (cluster_boot(su), len(su), sum(t for _, t in su))

    comps = {}
    for lo, hi in [("P0", "P1"), ("P1", "P2"), ("P0", "P2")]:
        if lo in arms and hi in arms:
            pr = [(per[p][lo]["win"], per[p][lo]["tot"], per[p][hi]["win"]) for p in scored]
            d, l, h = paired_boot(pr)
            comps[f"{lo}->{hi}"] = {"delta": round(d, 4), "ci95": [round(l, 4), round(h, 4)],
                                    "verdict": ("gain" if l > 0 else "non_inferior" if l > NI_MARGIN
                                                else "harm" if h < 0 else "inconclusive")}

    out = {"n_photos": len(scored), "n_pairs": tot_pairs, "n_sib_pairs": sib_pairs,
           "reps": args.reps, "arms": arms, "model": MODEL, "ni_margin": NI_MARGIN,
           "n_fail": len(fails), "failures": fails,
           "jpa": {a: {"point": round(agg[a][0], 4), "ci95": [round(agg[a][1], 4), round(agg[a][2], 4)]} for a in arms},
           "jpa_sibling": {a: {"point": round(aggs[a][0][0], 4),
                               "ci95": [round(aggs[a][0][1], 4), round(aggs[a][0][2], 4)],
                               "n_photos": aggs[a][1], "n_pairs": aggs[a][2]} for a in arms},
           "paired": comps,
           "per_photo": {p: {"pjts": pjts.get(p, ""), "y": sorted(jy[p]), "n": sorted(jn[p]),
                             **{a: {"jpa": round(per[p][a]["win"] / per[p][a]["tot"], 3) if per[p][a]["tot"] else None,
                                    "order_rep0": res.get((p, a, 0), [])} for a in arms}} for p in scored}}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    NAME = {"P0": "P0 현행", "P1": "P1 +정보배관", "P2": "P2 +근거렌더"}
    L = [f"=== 변별 프로브 (판정코드만 제시 · {len(scored)}장 · 판정쌍 {tot_pairs} · reps {args.reps} · {MODEL}) ===",
         f"실패 {len(fails)}건", "",
         f"{'arm':16}{'JPA':>8}{'CI95':>20}   형제JPA(쌍/장)"]
    for a in arms:
        j, s = out["jpa"][a], out["jpa_sibling"][a]
        L.append(f"{NAME[a]:16}{j['point']:>8.3f}  [{j['ci95'][0]:+.3f},{j['ci95'][1]:+.3f}]"
                 f"   {s['point']:.3f} ({s['n_pairs']}쌍/{s['n_photos']}장)")
    L.append("")
    for k, c in comps.items():
        L.append(f"[{k}] ΔJPA {c['delta']:+.4f} CI[{c['ci95'][0]:+.4f},{c['ci95'][1]:+.4f}] → {c['verdict']}")
    L += ["", f"[판정프레임] 주지표 JPA. 비열등 마진 {NI_MARGIN:+.2f}. 우월성 = CI 하한 > 0.",
          "[해석] P0가 이미 높으면 H2(랭킹) 소규모 확정. P1/P2에서 오르면 H1-a(정보배관)/H3'(근거렌더)가 원인.",
          "[한계] 형제 판정쌍은 표본이 작아 탐색적 관찰 전용(사전 선언). 제13조↔제30조는 판정쌍 0으로 채점 불가."]
    txt = "\n".join(L)
    OUT_MD.write_text(txt, encoding="utf-8")
    print("\n" + txt)
    print(f"\n→ {OUT.name} · {OUT_MD.name}")


if __name__ == "__main__":
    main()
