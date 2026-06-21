#!/usr/bin/env python3
"""자석 SR 교차도메인 링크 prune 초안(B) — she_sr_mapping 정밀화.

근본원인(조사 2026-06-21): bootstrap_she_from_synthetic.py가 강한 매칭(≥2축) SR이 없을 때
line 156 `or [top1]` fallback으로 단일축 SR을 억지로 붙였다(PAINTING FALL → SR-CARGO-004 하역).
broad 경로 query_sr_for_facets도 1축이면 SR 반환(line 360).

규칙: 각 magnet 링크의 (she_pattern features) vs (SR facets) matched_axes 계산
      (accident/hazardous_agent/work_context, canonical 포함). **matched_axes<2 = 약한 fallback = prune 후보.**
  → inversion 링크(같은 도메인, 2축↑)는 KEEP, bootstrap 단일축 자석은 PRUNE.

출력(미적용, 검토용): she_sr_crossdomain_prune.json + magnet_prune_review.md. 적용은 사람 승인 후 별도.
사용: .venv/bin/python scripts/draft_magnet_pruning.py   (DATABASE_URL 필요)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
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
PRUNE_JSON = ART / "she_sr_crossdomain_prune.json"
REVIEW_MD = ART / "magnet_prune_review.md"

MAGNETS = {
    "SR-CARGO-004": "제390조 하역작업장 조명·통로·안전난간",
    "SR-CHEMICAL-001": "제421조 환기 불충분 실내작업장 유해물질",
    "SR-CHEMICAL-002": "제422조 유해물질 발산원 국소배기장치",
    "SR-ELECTRIC-012": "제312조 폭발위험장소 변전실 설치 금지",
    "SR-MACHINE-002": "제87조 원동기·회전축 방호설비",
}


def main():
    db = SessionLocal()
    try:
        cv = _canonical_vocab()

        srf = {}
        for r in db.execute(text("""
            select identifier, accident_types, hazardous_agents, work_contexts,
                   accident_types_canonical, hazardous_agents_canonical, work_contexts_canonical
            from safety_requirements where identifier = any(:m)
        """), {"m": list(MAGNETS)}).fetchall():
            srf[r[0]] = {
                "acc": set(r[1] or []), "haz": set(r[2] or []), "wc": set(r[3] or []),
                "acc_can": set(r[4] or []), "haz_can": set(r[5] or []), "wc_can": set(r[6] or []),
            }

        links = db.execute(text("""
            select m.sr_id, m.she_id, m.source,
                   s.features->>'work_context', s.features->>'accident_type', s.features->>'hazardous_agent', s.name
            from she_sr_mapping m join she_catalog s on s.she_id=m.she_id
            where m.sr_id = any(:m)
            order by m.sr_id, m.source
        """), {"m": list(MAGNETS)}).fetchall()

        total_links = dict(db.execute(text(
            "select she_id, count(*) from she_sr_mapping group by she_id")).fetchall())

        def canon(axis, code):
            if not code:
                return None
            try:
                _, c = cv.to_canonical(axis, code)
                return c
            except Exception:  # noqa: BLE001
                return None

        def matched_axes(wc, acc, haz, f):
            wc_exp = set(_expand_work_contexts_for_query([wc])) if wc else set()
            acc_hit = bool(acc and (acc in f["acc"] or canon("accident_type", acc) in f["acc_can"]))
            haz_hit = bool(haz and (haz in f["haz"] or canon("hazardous_agent", haz) in f["haz_can"]))
            ctx_hit = bool(wc and ((f["wc"] & wc_exp) or (canon("work_context", wc) in f["wc_can"])))
            return acc_hit, haz_hit, ctx_hit

        prunes = []
        keeps = []
        per_sr = defaultdict(lambda: {"keep": 0, "prune": 0, "prune_wc": Counter()})
        prune_by_she = Counter()
        for sr_id, she_id, source, wc, acc, haz, name in links:
            f = srf[sr_id]
            ah, hh, ch = matched_axes(wc, acc, haz, f)
            ma = sum([ah, hh, ch])
            rec = {"sr_id": sr_id, "she_id": she_id, "source": source, "work_context": wc,
                   "accident_type": acc, "hazardous_agent": haz, "matched_axes": ma,
                   "axes": {"accident": ah, "agent": hh, "context": ch}, "she_name": name}
            if ma < 2:
                rec["reason"] = f"matched_axes={ma}<2 (단일축 fallback 자석); SR domain wc={sorted(f['wc'])} ≠ she wc={wc}"
                prunes.append(rec)
                per_sr[sr_id]["prune"] += 1
                per_sr[sr_id]["prune_wc"][wc] += 1
                prune_by_she[she_id] += 1
            else:
                keeps.append(rec)
                per_sr[sr_id]["keep"] += 1

        # orphan 체크: prune 후 SR 링크 0개 되는 she_id
        orphans = [she for she, n in prune_by_she.items() if total_links.get(she, 0) - n <= 0]

        PRUNE_JSON.write_text(json.dumps({
            "description": "자석 SR 교차도메인 prune 후보 (matched_axes<2). 미적용 — 사람 승인 후 prune.",
            "rule": "she_pattern vs SR facets matched_axes<2 → 약한 단일축 fallback 링크",
            "generated_by": "draft_magnet_pruning.py",
            "n_prune": len(prunes), "n_keep": len(keeps), "orphans_after_prune": orphans,
            "prunes": prunes,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        # 검토 MD
        md = ["# 자석 SR 교차도메인 prune 초안 (검토용, 미적용)", "",
              f"규칙: she_pattern↔SR **matched_axes<2**(단일축 fallback 자석) → prune. inversion 동도메인(≥2축)=KEEP.",
              f"총 prune **{len(prunes)}** / keep {len(keeps)} · orphan(=prune 후 0링크) {len(orphans)}건", ""]
        for sr_id, label in MAGNETS.items():
            f = srf.get(sr_id, {})
            st = per_sr[sr_id]
            md += [f"## {sr_id} — {label}",
                   f"- SR facets: acc={sorted(f.get('acc',[]))} haz={sorted(f.get('haz',[]))} wc={sorted(f.get('wc',[]))}",
                   f"- **prune {st['prune']}** / keep {st['keep']}",
                   f"- prune work_context: {dict(st['prune_wc'].most_common())}", ""]
        if orphans:
            md += ["## ⚠ orphan 경고 (prune 후 SR 링크 0 — 서빙 SHE 자격 상실, 별도 판단 필요)",
                   ", ".join(orphans[:30]), ""]
        REVIEW_MD.write_text("\n".join(md), encoding="utf-8")

        print(f"prune={len(prunes)} keep={len(keeps)} orphans={len(orphans)}")
        for sr_id, label in MAGNETS.items():
            st = per_sr[sr_id]
            f = srf.get(sr_id, {})
            sparse = " ⚠SR-facet-sparse(haz없음)" if not f.get("haz") and not f.get("acc") else ""
            print(f"  {sr_id}: prune {st['prune']} / keep {st['keep']}{sparse}")
        print(f"→ {PRUNE_JSON.name}, {REVIEW_MD.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
