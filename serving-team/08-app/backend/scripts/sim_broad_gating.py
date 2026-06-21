#!/usr/bin/env python3
"""broad 경로 domain-gating 빠른 시뮬레이션 (파이프라인 재실행 불요).

query_sr_for_facets는 현재 1축만 겹쳐도 SR 반환(hazard_rule_engine.py:360 or_). 가설:
**matched_axes>=2**를 요구하면 자석(단일축) noise가 사라져 broad precision이 급등한다.

dump의 broad SR + expected_features(scene facet)로 case×SR matched_axes를 offline 재계산해
임계별(≥1 현행 / ≥2 / ≥3) broad article 집합을 gold와 채점한다. ※expected_features(raw)+canonical
기반 근사치 — 실값은 코드수정+재dump로 확정. 방향성 판단용.

사용: .venv/bin/python scripts/sim_broad_gating.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = HERE.parents[4]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.db.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.services.hazard_rule_engine import _canonical_vocab, _expand_work_contexts_for_query  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
DUMP = ART / "synthetic_sr_article_dump.jsonl"
CLAUDE = ART / "claude_gold_v2.jsonl"
GOLD_AUTO = ART / "gold_auto.jsonl"


def _load_jsonl(p):
    out = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln:
            d = json.loads(ln)
            out[d["case_id"]] = d
    return out


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def main():
    db = SessionLocal()
    try:
        cv = _canonical_vocab()
        dump = [json.loads(l) for l in DUMP.read_text(encoding="utf-8").splitlines() if l.strip()]

        sr_ids = sorted({c["sr_id"] for d in dump for c in (d.get("broad") or [])})
        srf = {}
        for r in db.execute(text("""
            select identifier, accident_types, hazardous_agents, work_contexts,
                   accident_types_canonical, hazardous_agents_canonical, work_contexts_canonical
            from safety_requirements where identifier = any(:m)
        """), {"m": sr_ids}).fetchall():
            srf[r[0]] = {"acc": set(r[1] or []), "haz": set(r[2] or []), "wc": set(r[3] or []),
                         "acc_can": set(r[4] or []), "haz_can": set(r[5] or []), "wc_can": set(r[6] or [])}

        def canon_set(axis, codes):
            out = set()
            for c in codes or []:
                try:
                    _, cc = cv.to_canonical(axis, c)
                    out.add(cc)
                except Exception:  # noqa: BLE001
                    pass
            return out

        def matched_axes(ef, f):
            acc = set(ef.get("accident_types") or [])
            haz = set(ef.get("hazardous_agents") or [])
            wc = set(_expand_work_contexts_for_query(list(ef.get("work_contexts") or [])))
            acc_hit = bool((acc & f["acc"]) or (canon_set("accident_type", acc) & f["acc_can"]))
            haz_hit = bool((haz & f["haz"]) or (canon_set("hazardous_agent", haz) & f["haz_can"]))
            ctx_hit = bool((wc & f["wc"]) or (canon_set("work_context", wc) & f["wc_can"]))
            return acc_hit + haz_hit + ctx_hit

        def total_hits(ef, f):
            acc = set(ef.get("accident_types") or [])
            haz = set(ef.get("hazardous_agents") or [])
            wc = set(_expand_work_contexts_for_query(list(ef.get("work_contexts") or [])))
            hits = set()
            hits |= (acc & f["acc"]) | (canon_set("accident_type", acc) & f["acc_can"])
            hits |= (haz & f["haz"]) | (canon_set("hazardous_agent", haz) & f["haz_can"])
            hits |= (wc & f["wc"]) | (canon_set("work_context", wc) & f["wc_can"])
            return len(hits)

        def ranked_articles(d):
            """query_sr_for_facets 점수식(0.25+axes*0.25+hits*0.05) 재현 → article_code를 점수순 dedup."""
            ef = d.get("expected_features") or {}
            scored = []
            for c in d.get("broad") or []:
                f = srf.get(c["sr_id"])
                if not f:
                    continue
                ma = matched_axes(ef, f)
                sc = 0.25 + ma * 0.25 + total_hits(ef, f) * 0.05
                scored.append((sc, ma, c["article_code"]))
            scored.sort(key=lambda x: x[0], reverse=True)
            ranked, seen = [], set()
            for sc, ma, art in scored:
                if art not in seen:
                    seen.add(art)
                    ranked.append((art, ma))
            return ranked

        claude = _load_jsonl(CLAUDE)
        auto = _load_jsonl(GOLD_AUTO)

        def native_articles(d):
            """dump broad 리스트 원순서(=시스템 실제 랭킹) → article dedup."""
            out, seen = [], set()
            for c in d.get("broad") or []:
                a = c["article_code"]
                if a not in seen:
                    seen.add(a)
                    out.append((a, 9))  # ma 미상 → 9
            return out

        def score(gold_map, label="", gate2=False, native=False):
            KS = (1, 2, 3, 5, 10, 999)
            agg = {k: [0, 0, 0] for k in KS}  # tp, fp, fn
            ncase = 0
            for d in dump:
                cid = d["case_id"]
                if cid not in gold_map:
                    continue
                gold = set(gold_map[cid])
                if not gold:
                    continue
                ncase += 1
                ranked = native_articles(d) if native else ranked_articles(d)
                if gate2:
                    ranked = [(a, m) for a, m in ranked if m >= 2]
                arts = [a for a, m in ranked]
                for k in KS:
                    pred = set(arts[:k])
                    agg[k][0] += len(pred & gold)
                    agg[k][1] += len(pred - gold)
                    agg[k][2] += len(gold - pred)
            print(f"\n[{label}] cases={ncase}  gate(matched_axes>=2)={gate2}")
            print("  k     precision recall   F1     tp    fp    fn")
            for k in KS:
                tp, fp, fn = agg[k]
                p, r, f = _prf(tp, fp, fn)
                kk = "all" if k == 999 else str(k)
                print(f"  @{kk:<4} {p:<9} {r:<8} {f:<6} {tp:<5} {fp:<5} {fn:<5}")

        cl_pos = {cid: d.get("gold_codes") or [] for cid, d in claude.items() if d.get("gold_codes")}
        core_pos = {cid: a.get("core") or [] for cid, a in auto.items() if a.get("core")}
        score(cl_pos, label="claude_gold_v2 (점수랭킹)")
        score(cl_pos, label="claude_gold_v2 (native broad 순서=시스템 실제 랭킹)", native=True)
        score(core_pos, label="consensus core (점수랭킹)")
        score(core_pos, label="consensus core + gate≥2", gate2=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
