#!/usr/bin/env python3
"""RANK A/B — cue-pool 후보확장이 최종 순위(P@1)를 해치는가. [해악 검출 설계]

후보천장 A/B(measure_cuepool_gold.py)에서 union이 cand_any 84.5%→93.0%를 달성했으나
'천장 ≠ 최종정확도'. 후보 +15.5개(distractor)가 랭킹을 해칠 수 있어 RANK를 걸어 판정.

★설계 성격(사전등록): n=129·이득경로 headroom(사전등록 시점 추정 11장 → 2026-07-29 실측 12장,
  최대 +9.3pt) < MDE80 0.066 → **이득은 원리적으로 검출 불가, 해악만 검출 가능**.
  주지표 = A→B의 P@1, 사전지정 비열등 마진 NI_MARGIN=-0.05.
  Δ≈0은 '이득 없음'이 아니라 '이 표본으로는 볼 수 없음'.
  (수치 정정 이력을 남긴다 — 사전등록 값을 소급 수정하지 않는다.)

3 arm (paired — 같은 사진·Vision·RESOLVE 공유):
  A base_plain   : baseline(gimulmul) 후보
  B union_plain  : baseline ∪ cue(entry+flow) 후보    ← A와 차이 = 후보집합뿐
  C union_expert : union 후보 + 감독관 검수 rank_hint  ← B와 차이 = 프롬프트뿐 (⚠누출: 상한추정)

제시 중립화(M1): 후보 출처를 텍스트(태그)로도 순서(블록)로도 노출하지 않는다.
 - RANK_SYS의 "[기인물] 표시 조 우선" 문구 제거(RANK_SYS_BLIND) + 후보 라인 태그 미렌더
 - 정렬 = kind 비의존 단일 정책(조번호순) → A·B 공유 코드의 상대순서 보존, 신규 코드는 전역 분산
 - 정순/역순 counterbalancing(홀수 rep 역순) + order_sensitivity 게이트

사용: .venv/bin/python scripts/rank_ab_gold.py [--reps 4] [--arms A,B,C] [--limit N]
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
from gimulmul_match import RESOLVE_SYS, RESOLVE_SCHEMA, RANK_SYS, RANK_SCHEMA, CROSS  # noqa: E402

# ── M1-a: tag-blind 시스템 프롬프트(치환 실패 시 즉시 실패 — silent-overwrite 이력 대비) ──
RANK_SYS_BLIND = RANK_SYS.replace("[기인물] 표시 조와 구체 위험조 우선.", "구체 위험조 우선.")
assert RANK_SYS_BLIND != RANK_SYS and "[기인물]" not in RANK_SYS_BLIND, \
    "RANK_SYS 태그 문구 치환 실패 — gimulmul_match.RANK_SYS 원문 확인"

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
REF = REPO / "data-team" / "05-enrichment" / "reference-data" / "기인물참고자료"
SSOT = REPO / "docs" / "knowledge" / "감독관-판단기준"
GOLD_CSV = REPO / "real-test-photo" / "label_photo" / "label_curation_gold.csv"
INDEX = ART / "gimulmul_index.json"
SIGS = ART / "article_signatures.jsonl"
ALIAS = ART / "gimulmul_alias.json"
CURATED = REF / "parsed" / "case_rule_mapping.json"
ARTICLES = REPO / "data-team" / "02-extraction" / "pipe-A" / "data" / "article-texts.json"
IN_VISION = ART / "intake_vision_gold.json"
RESOLVE_CACHE = ART / "rank_ab_resolve_cache.json"
OUT = ART / "rank_ab_results.json"
OUT_MD = ART / "rank_ab_results.md"
MODEL = "gpt-5.4"
OBS_OK = ("yes", "partial")

# ── M3: 사전지정 통계 프레임 ──
NI_MARGIN = -0.05   # 비열등 마진: CI 하한 > -0.05 → "랭킹을 해치지 않음"
EXPECT_CEILING = {"A": (0.845, 29.8), "B": (0.930, 45.3)}   # G3 게이트(직전 천장 A/B 재현)

# ── 감독관 검수 rank_hint (arm C) — docs/knowledge/감독관-판단기준 SSOT 파생 ──
EXPERT_HINT = (
    "\n\n[감독관 판단기준 — 시설 우선 원칙 (실제 감독관 검수 반영)]\n"
    "1) 시설·장소를 먼저 특정하고 그 시설의 전용 조문을 1순위로 둔다(계단·개구부·비계·이동식비계·지붕·"
    "차량계 장비·전기설비 등). 재해유형을 먼저 분류하지 않는다.\n"
    "2) 안전난간 조건부(택일): 계단(1m↑)·개구부·비계·이동식비계에 난간이 '없으면' 그 장소조문"
    "(계단 제30조·개구부 제43조·비계 제56조·이동식비계 제68조). 난간이 '있으나 구조 미달'(상부·중간난간대·"
    "발끝막이판10cm·난간기둥·100kg)이면 제13조. 제13조는 난간이 존재할 때만 쓰며 단독 1순위로 두지 않는다.\n"
    "3) 단계적 대체: 제42조 작업발판 → 곤란시 추락방호망 → 곤란시 안전대 → 제44조(부착설비·작업전 점검). "
    "사진에 실제로 보이는 단계의 조문을 상위로.\n"
    "4) 장비는 총칙 먼저: 차량계 하역운반 제171조~제178조 / 건설기계 제199조~제206조를 세부조문"
    "(지게차 제179조~제183조 등)과 함께 고려.\n"
    "5) 포괄조항 강등: 제3조·제5조·제22조·제23조는 특정조문이 있으면 하위로.\n"
    "6) 절차조문(제38조·제39조·제40조 작업계획서·지휘자·신호)은 사진으로 확인 불가 → no 또는 최하위.\n"
)

# ── M5: arm C 누출 경고 ──
LEAKAGE_WARN = (
    "arm C(EXPERT_HINT)는 본 gold 129장을 본 뒤 작성된 규칙이다. 타임라인: gold 라벨링 → 동일 129장 "
    "조문별 오류분석(cuepool-candidate-ceiling-ab) → SSOT 규칙 커밋 9c322b4 → 본 하네스. 홀드아웃 분할 없음. "
    "힌트가 명시 지목한 조문이 gold y의 약 53%를 덮고, 억제 대상 제3·5·38·39·40조는 gold y-count 0. "
    "따라서 B->C / A->C Δ는 일반화 이득이 아니라 상한 추정치이며 bootstrap CI가 이 자유도를 잡지 못한다. "
    "채택 판단은 A->B만 사용한다."
)

# ── gold ──
def _norm_code(c):
    """gold CSV '조' 누락 오기 정규화(제45→제45조). 2026-07-30 발견 — 미정규화 시 해당 gold는 영영 미적중."""
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    return f"제{m.group(1)}조" if (m and not m.group(2)) else c


gold = defaultdict(set)
with GOLD_CSV.open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if (r.get("match") or "").strip().lower() == "y":
            gold[r["photo_file"]].add(_norm_code(r["article_code"]))

# ── indices ──
idx = json.loads(INDEX.read_text(encoding="utf-8"))
groups = idx["groups"]
cross_set = sorted(set(CROSS) & set(idx["observable_codes"]))
sig = {json.loads(l)["article_code"]: json.loads(l) for l in SIGS.read_text(encoding="utf-8").splitlines() if l.strip()}
alias = json.loads(ALIAS.read_text(encoding="utf-8")) if ALIAS.exists() else {}
curated = json.loads(CURATED.read_text(encoding="utf-8"))["gimulmul_articles"] if CURATED.exists() else {}
RULE_FULL = json.loads(ARTICLES.read_text(encoding="utf-8"))["laws"]["RULE"]


def full_text(code):
    return (RULE_FULL.get(code, {}) or {}).get("fullText", "") or ""


def curated_lookup(gim):
    base = gim.split("(")[0].strip()
    for k, v in curated.items():
        if k.split("(")[0].strip() == base or base in k or k in base:
            return [a["code"] for a in v["articles"]]
    return []


# ★ 카탈로그는 서빙(cue_article_service._load_knowledge)과 **같은 규칙**이어야 한다.
#   여기서만 다르면 측정한 조건과 서비스하는 조건이 갈린다.
#   우산 그룹(총칙·통칙·기계 등의 일반기준) 제외 — 내용이 전부 하위에 상속돼 있어 앵커로 고르면
#   오히려 덜 보인다. 목록은 흐름 데이터가 데이터로 판정해 내려준다.
UMBRELLA_SRC = set(json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))
                   .get("umbrella_src_keys") or [])
catalog = []
for gk, g in groups.items():
    nobs = sum(1 for a in g["articles"] if a["observable"] in OBS_OK)
    if nobs >= 1 and gk not in idx["cross_cutting"] and gk not in UMBRELLA_SRC:
        catalog.append(f"{gk} ::기인물={g['gimulmul']} ({nobs}조)")
catalog_text = "\n".join(sorted(catalog))

# ── cue-pool matcher (measure_cuepool_gold.py와 동일 규칙) ──
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


def scene_text(res):
    obs = " ".join(o.get("text", "") for o in res.get("visual_observations") or [])
    cues = "; ".join(c.get("text", "") for c in res.get("visual_cues") or [])
    haz = "; ".join(h.get("name", "") for h in res.get("hazards") or [])
    return f"{obs} 시각단서: {cues} 위험: {haz}".strip()


def cue_text(res):
    parts = []
    for o in res.get("visual_observations", []):
        parts.append(o.get("text", ""))
    for o in res.get("visual_cues", []):
        parts.append(o.get("text", ""))
    for h in res.get("hazards", []):
        parts += [h.get("name", ""), h.get("description", ""), h.get("location", "")]
    return " | ".join(parts)


def cue_candidates(res):
    txt = cue_text(res)
    entry, flow = set(), set()
    for c, ts in CUE_TERMS:
        if any(t in txt for t in ts):
            entry |= set(c.get("articles", []))
            flow |= set(c.get("flow_articles", []))
    entry = {a for a in entry if sig.get(a, {}).get("observable") in OBS_OK}
    flow = {a for a in flow if sig.get(a, {}).get("observable") in OBS_OK}
    return entry, flow - entry


def baseline_candidates(rv):
    """kind = 결과 JSON/디버깅용 출처 태그(프롬프트에는 렌더하지 않음 — M1-b)."""
    kind = {}

    def add(code, tag):
        if code in kind or sig.get(code, {}).get("observable") not in OBS_OK:
            return
        kind[code] = tag

    gims = rv.get("gimulmul", [])
    for gim in gims:
        for c in curated_lookup(gim):
            add(c, "큐레이션")
    for gim in gims:
        for gk in alias.get(gim, {}).get("group_keys", []):
            for a in groups.get(gk, {}).get("articles", []):
                add(a["code"], "기인물")
    for gk in [k for k in rv.get("group_keys", []) if k in groups]:
        for a in groups[gk]["articles"]:
            add(a["code"], "기인물")
    for c in cross_set:
        add(c, "횡단")
    return kind


def code_num(c):
    m = re.match(r"제(\d+)조(?:의(\d+))?", c)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (99999, 0)


def build_arm_candidates(rv, res, arm):
    """arm A=baseline / B,C=union.
    제시 순서 = kind 비의존 단일 정책(조번호 오름차순), 전 arm 동일 → A와의 차이 = 후보집합뿐."""
    kind = baseline_candidates(rv)
    if arm != "A":
        entry, flow = cue_candidates(res)
        for c in entry:
            kind.setdefault(c, "단서")
        for c in flow:
            kind.setdefault(c, "흐름")
    codes = sorted(kind.keys(), key=code_num)
    return codes, kind


# ── OpenAI ──
_ensure_key()
from openai import OpenAI  # noqa: E402

client = OpenAI(max_retries=5, timeout=180.0)


def chat(sysp, user, schema):
    r = client.chat.completions.create(model=MODEL, messages=[
        {"role": "system", "content": sysp}, {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": schema})
    return json.loads(r.choices[0].message.content)


def rank_prompt(st, codes):
    """M1-b: 후보 출처 태그 미렌더."""
    lines = [f"[장면]\n{st}", "", "[후보 조]"]
    for c in codes:
        s = sig.get(c, {})
        lines.append(f"- {c} {s.get('title','')} | {(s.get('violation_scene','') or '')[:90]}\n"
                     f"  전문: {full_text(c)[:160]}")
    return "\n".join(lines) + "\n\n적용 조를 확신순 정렬."


def do_rank(st, codes, expert):
    sysp = RANK_SYS_BLIND + (EXPERT_HINT if expert else "")
    rk = chat(sysp, rank_prompt(st, codes), RANK_SCHEMA)
    valid = set(codes)
    keep, halluc = [], 0
    for x in rk["ranked"]:
        c = x["article_code"]
        if x["applies"] not in ("yes", "maybe"):
            continue
        if c in valid:
            keep.append(c)
        else:
            halluc += 1
    return keep, halluc


# ── metrics ──
KS = [1, 3, 5, 10]
MKEYS = ["p1", "hit1", "hit3", "hit5", "hit10", "r5", "r10", "mrr"]


def photo_metrics(ranked, g):
    out = {"p1": 1.0 if ranked and ranked[0] in g else 0.0}
    for k in KS:
        top = set(ranked[:k])
        out[f"hit{k}"] = 1.0 if top & g else 0.0
        out[f"r{k}"] = len(top & g) / len(g)
    mrr = 0.0
    for i, c in enumerate(ranked, 1):
        if c in g:
            mrr = 1.0 / i
            break
    out["mrr"] = mrr
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def bootstrap_ci(pairs, n=4000, seed=17):
    rnd = random.Random(seed)
    N = len(pairs)
    if N == 0:
        return (0.0, 0.0, 0.0)
    d = mean([b - a for a, b in pairs])
    boots = []
    for _ in range(n):
        s = [pairs[rnd.randrange(N)] for _ in range(N)]
        boots.append(mean([b - a for a, b in s]))
    boots.sort()
    return (d, boots[int(0.025 * n)], boots[int(0.975 * n) - 1])


def discordance(pairs):
    """페어드 불일치 카운트(McNemar 스타일 — 정식 검정 아님, 기술통계)."""
    return sum(1 for a, b in pairs if a > b), sum(1 for a, b in pairs if b > a)


def mde(pairs, z_a=1.96, z_b=0.8416):
    """관측 페어드 분산에서 SE·CI반폭·MDE(80% power)."""
    n = len(pairs)
    if n == 0:
        return None
    ds = [b - a for a, b in pairs]
    m = mean(ds)
    se = (mean([(d - m) ** 2 for d in ds]) / n) ** 0.5
    return {"disc_rate": round(mean([1.0 if a != b else 0.0 for a, b in pairs]), 3),
            "se": round(se, 4), "ci_halfwidth": round(z_a * se, 4),
            "mde80": round((z_a + z_b) * se, 4)}


def verdict_of(lo_ci, hi_ci):
    """사전지정 판정 사다리(순서 고정)."""
    if lo_ci > 0:
        return "gain"
    if lo_ci > NI_MARGIN:
        return "non_inferior"
    if hi_ci < 0:
        return "harm"
    return "inconclusive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=4, help="arm당 RANK 반복(짝수 — 정순/역순 균형)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="G3 천장 게이트 불일치에도 진행")
    args = ap.parse_args()
    if args.reps % 2:
        sys.exit("--reps는 짝수여야 한다(정순/역순 counterbalancing)")
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]

    if not IN_VISION.exists():
        sys.exit(f"Vision 캐시 없음: {IN_VISION} — measure_cuepool_gold.py 먼저 실행")
    vis = {r["photo"]: r["result"] for r in json.loads(IN_VISION.read_text(encoding="utf-8"))["photos"]}

    photos = sorted([p for p in gold if p in vis])
    if args.limit:
        photos = photos[:args.limit]
    print(f"gold {len(gold)}장 · Vision 보유 {len(photos)}장 · arms={arms} reps={args.reps}", flush=True)

    # ── RESOLVE 1회 (arm·rep 공유 → 교란 제거) ──
    rcache = json.loads(RESOLVE_CACHE.read_text(encoding="utf-8")) if RESOLVE_CACHE.exists() else {}
    todo = [p for p in photos if p not in rcache]
    resolve_fails = []
    if todo:
        print(f"RESOLVE {len(todo)}장 (캐시 {len(rcache)})", flush=True)

        def _resolve(pf):
            st = scene_text(vis[pf])
            return pf, chat(RESOLVE_SYS, f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{catalog_text}\n\n주요 기인물의 group_key 선택.",
                            RESOLVE_SCHEMA)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(_resolve, p): p for p in todo}
            for fu in as_completed(futs):
                try:
                    pf, rv = fu.result()
                    rcache[pf] = rv
                except Exception as e:  # noqa: BLE001
                    resolve_fails.append({"photo": futs[fu], "err": str(e)[:200]})
                    print(f"  RESOLVE ERR {futs[fu][:28]}: {str(e)[:120]}", flush=True)
        RESOLVE_CACHE.write_text(json.dumps(rcache, ensure_ascii=False, indent=1), encoding="utf-8")
    photos = [p for p in photos if p in rcache]

    # ── 후보 구성(결정적) ──
    cands = {}
    for pf in photos:
        for arm in arms:
            cands[(pf, arm)] = build_arm_candidates(rcache[pf], vis[pf], arm)

    # ── G3: 천장 자기검증 ──
    ceiling = {}
    for arm in arms:
        anys, recs, sizes = [], [], []
        for pf in photos:
            codes = set(cands[(pf, arm)][0])
            g = gold[pf]
            anys.append(1.0 if codes & g else 0.0)
            recs.append(len(codes & g) / len(g))
            sizes.append(len(codes))
        ceiling[arm] = {"cand_any": round(mean(anys), 3), "cand_recall": round(mean(recs), 3),
                        "avg_cand": round(mean(sizes), 1)}
    print("천장 자기검증:", json.dumps(ceiling, ensure_ascii=False), flush=True)
    g3 = {"pass": True, "detail": []}
    if not args.limit:
        for arm, (exp_any, exp_n) in EXPECT_CEILING.items():
            if arm in ceiling:
                d_any = abs(ceiling[arm]["cand_any"] - exp_any)
                d_n = abs(ceiling[arm]["avg_cand"] - exp_n)
                if d_any > 0.01 or d_n > 1.0:
                    g3["pass"] = False
                    g3["detail"].append(f"{arm}: cand_any {ceiling[arm]['cand_any']}(기대 {exp_any}) "
                                        f"avg_cand {ceiling[arm]['avg_cand']}(기대 {exp_n})")
        if not g3["pass"]:
            print("⛔ G3 실패 — 후보구성이 직전 천장 A/B와 갈라짐:", g3["detail"], flush=True)
            if not args.force:
                sys.exit("중단(--force로 강행 가능). 코드 diff 확인 요망.")

    # ── RANK 실행 (홀수 rep = 역순 제시) ──
    jobs = [(pf, arm, rep) for arm in arms for rep in range(args.reps) for pf in photos]
    print(f"RANK 호출 {len(jobs)}건 시작 (workers={args.workers})", flush=True)
    ranked_all, halluc_all, fails = {}, {}, []

    def _rank(job):
        pf, arm, rep = job
        codes, _kind = cands[(pf, arm)]
        if rep % 2:
            codes = codes[::-1]
        return job, do_rank(scene_text(vis[pf]), codes, expert=(arm == "C"))

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_rank, j): j for j in jobs}
        for fu in as_completed(futs):
            job = futs[fu]
            try:
                _, (ranked, halluc) = fu.result()
                ranked_all[job] = ranked
                halluc_all[job] = halluc
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": job[0], "arm": job[1], "rep": job[2], "err": str(e)[:200]})
                print(f"  RANK ERR {job[1]}/rep{job[2]} {job[0][:28]}: {str(e)[:120]}", flush=True)
            done += 1
            if done % 50 == 0:
                print(f"  ... {done}/{len(jobs)}", flush=True)

    # ── 집계: 사진×arm = rep 평균 (rep 전량 성공한 것만) ──
    per_photo = defaultdict(dict)
    for arm in arms:
        for pf in photos:
            ms = [photo_metrics(ranked_all[(pf, arm, rep)], gold[pf])
                  for rep in range(args.reps) if (pf, arm, rep) in ranked_all]
            if len(ms) == args.reps:
                per_photo[pf][arm] = {k: mean([m[k] for m in ms]) for k in ms[0]}

    scored = [pf for pf in photos if all(a in per_photo[pf] for a in arms)]
    dropped = [pf for pf in photos if pf not in scored]
    if not scored:
        sys.exit("채점 가능한 사진 0장 — RANK 전량 실패")
    agg = {arm: {k: round(mean([per_photo[pf][arm][k] for pf in scored]), 3) for k in MKEYS} for arm in arms}

    # ── 상수/사소 기저선(무LLM) ──
    base_arm = "A" if "A" in arms else arms[0]
    _rnd = random.Random(17)

    def _bl(order_fn):
        ms = [photo_metrics(order_fn(pf), gold[pf]) for pf in scored]
        return {k: round(mean([m[k] for m in ms]), 3) for k in MKEYS}

    def _cand(pf):
        return list(cands[(pf, base_arm)][0])

    def _const43(pf):
        c = _cand(pf)
        return (["제43조"] + [x for x in c if x != "제43조"]) if "제43조" in c else c

    def _shuf(pf):
        c = _cand(pf)
        _rnd.shuffle(c)
        return c

    trivial = {"const_제43조": _bl(_const43), "cand_order": _bl(_cand), "random_perm": _bl(_shuf)}

    _cs = set(cross_set)
    cross_diag = {
        "cross_codes": cross_set,
        "source": "label_sheet.csv(8장·y 20건, 2026-06-21) y라벨 + 빈출 후보 큐레이션. "
                  "129장 curation gold와 다른 라벨링 회차이나 사진 중복 여부 미확인",
        "gold_ymass_in_cross": round(sum(len(gold[pf] & _cs) for pf in scored)
                                     / max(1, sum(len(gold[pf]) for pf in scored)), 3),
        "photos_gold_subset_of_cross": sum(1 for pf in scored if gold[pf] and gold[pf] <= _cs),
        "photos_caught_only_by_cross": sum(1 for pf in scored
                                           if (set(_cand(pf)) & gold[pf]) and not ((set(_cand(pf)) - _cs) & gold[pf])),
    }

    # ── G2: order sensitivity (정순 rep짝수 − 역순 rep홀수) ──
    def _dir_mean(arm, parity):
        vals = [photo_metrics(ranked_all[(pf, arm, r)], gold[pf])["p1"]
                for pf in scored for r in range(parity, args.reps, 2) if (pf, arm, r) in ranked_all]
        return mean(vals)

    order_sensitivity = {arm: round(_dir_mean(arm, 0) - _dir_mean(arm, 1), 4) for arm in arms}

    # ── 페어드 비교 ──
    comps = {}
    for lo, hi in [("A", "B"), ("B", "C"), ("A", "C")]:
        if lo in arms and hi in arms:
            c = {}
            for k in ["p1", "hit3", "hit5", "mrr"]:
                pairs = [(per_photo[pf][lo][k], per_photo[pf][hi][k]) for pf in scored]
                d, lo_ci, hi_ci = bootstrap_ci(pairs)
                a_only, b_only = discordance(pairs)
                c[k] = {"delta": round(d, 4), "ci95": [round(lo_ci, 4), round(hi_ci, 4)],
                        f"{lo}_win": a_only, f"{hi}_win": b_only,
                        "mde": mde(pairs), "verdict": verdict_of(lo_ci, hi_ci)}
            comps[f"{lo}->{hi}"] = c

    # ── headroom 서브그룹(탐색적) ──
    headroom = []
    if "A" in arms and "B" in arms:
        headroom = [pf for pf in scored
                    if not (set(cands[(pf, "A")][0]) & gold[pf]) and (set(cands[(pf, "B")][0]) & gold[pf])]
    headroom_sub = {"n": len(headroom), "photos": headroom,
                    "note": "A후보가 gold를 놓치고 B가 포착한 사진 = 후보확장의 유일한 이득경로. 탐색적 관찰 전용(유의성 판정 금지)",
                    "metrics": {arm: {k: round(mean([per_photo[pf][arm][k] for pf in headroom]), 3)
                                      for k in ["p1", "hit3", "hit5", "mrr"]} for arm in arms} if headroom else {}}

    g2_max = max(abs(v) for v in order_sensitivity.values()) if order_sensitivity else 0.0
    gates = {
        "G1_no_failure": {"pass": len(fails) == 0 and not dropped,
                          "n_rank_fail": len(fails), "n_dropped": len(dropped)},
        "G2_order_not_dominant": {"pass": g2_max <= 0.05, "max_abs": round(g2_max, 4),
                                  "by_arm": order_sensitivity},
        "G3_ceiling_reproduced": g3,
        "G4_beats_constant": {"pass": agg.get(base_arm, {}).get("p1", 0) > trivial["const_제43조"]["p1"],
                              "arm_p1": agg.get(base_arm, {}).get("p1"), "const_p1": trivial["const_제43조"]["p1"]},
    }

    result = {
        "n_photos": len(scored), "n_candidate_photos": len(photos),
        "n_gold_codes": sum(len(gold[pf]) for pf in scored),
        "reps": args.reps, "arms": arms, "model": MODEL, "ni_margin": NI_MARGIN,
        "primary_metric": "paired['A->B']['p1']",
        "design_note": "해악 검출 설계 — 이득경로 headroom장이 상한. Δ≈0은 '이득 없음'이 아님.",
        "caveat": {"arm_C_holdout": LEAKAGE_WARN, "adoption_criterion": "A->B"},
        "gates": gates,
        "n_rank_fail": len(fails), "fail_by_arm": {a: sum(1 for f in fails if f["arm"] == a) for a in arms},
        "rank_failures": fails, "dropped_photos": dropped,
        "n_resolve_fail": len(resolve_fails), "resolve_failures": resolve_fails,
        "hallucinated_by_arm": {a: sum(v for (p, ar, r), v in halluc_all.items() if ar == a) for a in arms},
        "ceiling": ceiling, "order_sensitivity": order_sensitivity,
        "trivial_baselines": trivial, "cross_diag": cross_diag,
        "metrics": agg, "paired": comps, "headroom_subgroup": headroom_sub,
        "per_photo": {pf: {"gold": sorted(gold[pf]),
                           **{arm: {"metrics": {k: round(v, 3) for k, v in per_photo[pf][arm].items()},
                                    "n_cand": len(cands[(pf, arm)][0]),
                                    "candidates": cands[(pf, arm)][0],
                                    "kind": cands[(pf, arm)][1],
                                    # 전체 랭킹 전 rep 저장 — rank fusion/게이팅 사후 시뮬레이션에 필수
                                    "ranked": {str(rep): ranked_all.get((pf, arm, rep), [])
                                               for rep in range(args.reps)},
                                    "top5": ranked_all.get((pf, arm, 0), [])[:5]} for arm in arms}}
                      for pf in scored},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── MD 리포트 ──
    NAME = {"A": "A base_plain", "B": "B union_plain", "C": "C union_expert"}
    L = [f"=== RANK A/B (gold {len(scored)}장 · y-코드 {result['n_gold_codes']} · reps {args.reps} · {MODEL}) ===",
         f"제외 {len(dropped)}장(후보구성 {len(photos)}) · RANK 실패 {len(fails)}건 {result['fail_by_arm']}"
         f" · RESOLVE 실패 {len(resolve_fails)}건 · 후보밖코드 {result['hallucinated_by_arm']}", ""]
    if "C" in arms:
        L += ["⚠ " + LEAKAGE_WARN, ""]
    L += [f"{'arm':16}{'P@1':>8}{'Hit@3':>8}{'Hit@5':>8}{'R@5':>8}{'MRR':>8}{'천장':>8}{'후보':>7}"]
    for arm in arms:
        m, ce = agg[arm], ceiling[arm]
        L.append(f"{NAME[arm]:16}{m['p1']:>8.3f}{m['hit3']:>8.3f}{m['hit5']:>8.3f}{m['r5']:>8.3f}"
                 f"{m['mrr']:>8.3f}{ce['cand_any']:>8.3f}{ce['avg_cand']:>7.1f}")
    L.append("")
    for name, c in comps.items():
        sfx = "  ⚠상한추정" if name.endswith("C") else ""
        L.append(f"[{name}] " + " · ".join(
            f"{k} Δ{c[k]['delta']:+.3f} CI[{c[k]['ci95'][0]:+.3f},{c[k]['ci95'][1]:+.3f}] {c[k]['verdict']}"
            for k in ["p1", "hit3", "hit5", "mrr"]) + sfx)
    L.append("")
    for name, c in comps.items():
        L.append(f"[{name}] MDE80 " + " · ".join(
            f"{k} {c[k]['mde']['mde80']:.3f}(불일치 {c[k]['mde']['disc_rate']:.2f})" for k in ["p1", "hit3", "hit5", "mrr"]))
    L += ["", "[상수 기저선(무LLM) — arm 절대치는 이 대비 순증으로 읽을 것]",
          f"{'baseline':16}{'P@1':>8}{'Hit@3':>8}{'Hit@5':>8}{'R@5':>8}{'MRR':>8}"]
    for nm, m in trivial.items():
        L.append(f"{nm:16}{m['p1']:>8.3f}{m['hit3']:>8.3f}{m['hit5']:>8.3f}{m['r5']:>8.3f}{m['mrr']:>8.3f}")
    L += ["", f"[CROSS 상수 {len(cross_set)}조] gold y-mass {cross_diag['gold_ymass_in_cross']:.3f} · "
              f"gold전부CROSS내 {cross_diag['photos_gold_subset_of_cross']}장 · "
              f"CROSS로만 포착 {cross_diag['photos_caught_only_by_cross']}장",
          f"  출처: {cross_diag['source']}",
          "  주: CROSS는 전 arm 공통 상수 → 페어드 Δ는 무편향. 영향은 절대수준 해석에 한정.", ""]
    L.append("[유효성 게이트]")
    for gk, gv in gates.items():
        L.append(f"  {'PASS' if gv.get('pass') else 'FAIL'}  {gk}: "
                 + json.dumps({k: v for k, v in gv.items() if k != 'pass'}, ensure_ascii=False))
    L += ["", f"[headroom 서브그룹] {headroom_sub['n']}장 (A 놓침·B 포착 = 이득 유일경로, 탐색적)"]
    if headroom_sub["metrics"]:
        for arm in arms:
            hm = headroom_sub["metrics"][arm]
            L.append(f"  {NAME[arm]:16} P@1 {hm['p1']:.3f} · Hit@3 {hm['hit3']:.3f} · Hit@5 {hm['hit5']:.3f} · MRR {hm['mrr']:.3f}")
    L += ["", f"[판정프레임] 주지표=A->B의 P@1. 사전지정 비열등 마진 {NI_MARGIN:+.2f}. "
              "판정 사다리: CI하한>0 gain / >마진 non_inferior / CI상한<0 harm / else inconclusive.",
          f"[해석 한계] n={len(scored)} · 이득경로 {headroom_sub['n']}장(최대 "
          f"+{100 * headroom_sub['n'] / max(len(scored), 1):.1f}pt) · MDE80 "
          f"{comps.get('A->B', {}).get('p1', {}).get('mde', {}).get('mde80', float('nan')):.3f} → "
          "이 설계는 **해악 검출용**이다. Δ가 0 근처인 것은 '이득 없음'이 아니라 '이 표본으로는 이득을 볼 수 없음'이다.",
          "  arm 절대값은 상수 기저선 대비 순증으로만 읽고, 배포 성능 주장에 쓰지 않는다(태그·순서 중립화로 배포와 다름)."]
    txt = "\n".join(L)
    OUT_MD.write_text(txt, encoding="utf-8")
    print("\n" + txt)
    print(f"\n→ {OUT.name} · {OUT_MD.name}")


if __name__ == "__main__":
    main()
