#!/usr/bin/env python3
"""절1 추락·절2 붕괴 카탈로그 편입 게이트 (2026-08-13, 사전등록 — plan/dev-note 참조).

exact는 집합 교집합이라 '주 앵커(첫 순위) 절도'를 못 잡는다(적대 검증 F2-1) —
G-FIRST가 그 채널을 따로 본다. 기준본은 git HEAD의 anchor_accuracy.json(편입 전 51장)과
물러둔 구캐시, 비교본은 재추첨 캐시(106종)와 새 anchor_accuracy.json.

게이트: G1 기존 채점 히트→미스 0 · G-FIRST 기존 exact-hit의 첫 키 gold 좌표 밖 이탈 0 ·
       G2 정답 그룹 밀림 0. 신규 채점 사진은 보고만(기대치 근거 없음).
실행: .venv/bin/python scripts/measure_fall_catalog_gates.py [--base-rev <rev>] [--old-cache <sha8>]
2026-08-13 실측: G1 0/0 · G-FIRST 변경 10(전부 gold 안 — 라벨 표기차) · G2 0 → PASS.
       신규 채점 46장 전부 exact — 0.784/51장 → 0.959/97장, flow 0.961 → 0.990.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
import measure_anchor_accuracy as M  # noqa: E402 — coord/norm_gk 재사용(채점과 동일 규칙)

REPO = HERE.parents[3]
AA_REL = "data-team/05-enrichment/runtime-artifacts/anchor_accuracy.json"


def pt(v):
    return v.get("point", v.get("value")) if isinstance(v, dict) else v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-rev", default="HEAD",
                    help="기준 anchor_accuracy를 읽을 git rev (기본 HEAD — 계측 결과 커밋 전 실행 기준)")
    ap.add_argument("--old-cache", default="61f43ddf627c", help="물러둔 구캐시의 카탈로그 sha 접두")
    args = ap.parse_args()

    base_aa = json.loads(subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{args.base_rev}:{AA_REL}"]).decode("utf-8"))
    new_aa = json.loads((M.ART / "anchor_accuracy.json").read_text(encoding="utf-8"))
    bp = {r["photo"]: r for r in base_aa["per_photo"]}
    np_ = {r["photo"]: r for r in new_aa["per_photo"]}
    print(f"기준 채점 {len(bp)}장 (exact {pt(base_aa['exact_match'])} · flow {pt(base_aa['flow_valid'])}) → "
          f"새 채점 {len(np_)}장 (exact {pt(new_aa['exact_match'])} · flow {pt(new_aa['flow_valid'])})")

    # ── G1: 기존 채점 사진의 히트→미스 전환 0 ──────────────────────────
    missing = [p for p in bp if p not in np_]
    g1_exact = [p for p in bp if p in np_ and bp[p]["exact"] and not np_[p]["exact"]]
    g1_flow = [p for p in bp if p in np_ and bp[p]["flow_valid"] and not np_[p]["flow_valid"]]
    print(f"\nG1: exact 히트→미스 {len(g1_exact)}장 {g1_exact} · flow 히트→미스 {len(g1_flow)}장 {g1_flow}"
          f" · 채점 이탈 {len(missing)}장 {missing}")

    old_c = json.loads((M.ART / f"rank_ab_resolve_cache_v2.{args.old_cache}.json").read_text(encoding="utf-8"))
    new_c = json.loads((M.ART / "rank_ab_resolve_cache_v2.json").read_text(encoding="utf-8"))
    new_keys, old_ph, new_ph = set(new_c["_catalog_keys"]), old_c["photos"], new_c["photos"]
    sigs = {json.loads(l)["article_code"]: json.loads(l)
            for l in (M.ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    gim = json.loads((M.ART / "gimulmul_index.json").read_text(encoding="utf-8"))["groups"]
    gkey_coord = {k: {M.coord(sigs[a["code"]]["section"]) for a in g.get("articles", []) if a["code"] in sigs}
                  for k, g in gim.items()}

    # ── G-FIRST: 기존 exact-hit 사진에서 첫 키가 gold 좌표 밖 그룹으로 바뀜 0 ──
    gfirst_bad, gfirst_changed = [], []
    for p in bp:
        if not bp[p]["exact"] or p not in new_ph or p not in old_ph:
            continue
        of = next(iter(old_ph[p].get("group_keys") or []), None)
        nf = next(iter(new_ph[p].get("group_keys") or []), None)
        if of == nf:
            continue
        truth = {tuple(t) for t in np_[p]["truth"]}  # gold 좌표(새 카탈로그 기준 — 사전등록 정의)
        hit = bool(gkey_coord.get(M.norm_gk(nf or "", new_keys), set()) & truth)
        gfirst_changed.append((p, of, nf, "gold좌표 안" if hit else "★gold좌표 밖"))
        if not hit:
            gfirst_bad.append(p)
    print(f"\nG-FIRST: 기존 exact-hit 중 첫 키 변경 {len(gfirst_changed)}장 · gold 좌표 밖 이탈 {len(gfirst_bad)}장")
    for p, of, nf, v in gfirst_changed:
        print(f"  {p[:44]:<44} {str(of)[:38]} → {str(nf)[:38]}  [{v}]")

    # ── G2: 기존 정답 그룹이 후보 밖으로 밀림 0 (G1 exact와 동치 — 명시 재확인) ──
    g2_bad = [p for p in bp if p in np_ and bp[p]["exact"] and not np_[p]["exact"]]
    print(f"\nG2: 정답 그룹 밀림 {len(g2_bad)}장 {g2_bad}")

    # ── 신규 채점 사진 보고 ─────────────────────────────────────────────
    new_only = [p for p in np_ if p not in bp]
    ok = sum(1 for p in new_only if np_[p]["exact"])
    fv = sum(1 for p in new_only if np_[p]["flow_valid"])
    print(f"\n신규 채점 {len(new_only)}장: exact {ok}장 · flow_valid {fv}장 (게이트 아님 — 보고)")

    verdict = not (g1_exact or g1_flow or missing or gfirst_bad or g2_bad)
    print(f"\n=== 게이트 판정: {'PASS' if verdict else 'FAIL'} ===")
    sys.exit(0 if verdict else 1)


if __name__ == "__main__":
    main()
