"""장소성 라우팅 계측 (Track A) — 미니 gold(place_gold_v1.csv) + gold51 장소성 오탐.

서빙 코드 직수입으로 측정=서빙 조건을 고정한다: RESOLVE는 cue_article_service.resolve(서빙
카탈로그·프롬프트·정규화), judge는 flow_service.judge_anchor, 결정은 flow_service.route_decision
(순수 함수 — build()와 같은 규칙).

게이트 (사전등록 — 결과 보고 조정 금지):
  G-OLD-PLACE-FP : gold51에서 route==place **0장** (기존 앵커 사진의 장소성 재라우팅 오탐 금지)
  G-MINI-PROD    : prod 3장 전부 기대 결과 (5220·5221 place / 5222 anchor)
  G-MINI-PLACE   : place 기대 사진 정라우팅+주제 교집합 ≥ 0.8
  G-MINI-ANCHOR  : anchor 기대 사진의 주 앵커 그룹 일치 1.0 (포괄 강등/장소성의 과잉 방지)
  (expect=either 행은 비게이트 진단)

재추첨 금지: gold51의 Vision은 intake_vision_gold.json, RESOLVE는 커밋된
rank_ab_resolve_cache_v2.json(고정 표본)을 재사용한다 — 다시 뽑으면 경계 사진이 뒤집힌다
(선우개발 empty 0↔1 실측). 신규 사진의 Vision·RESOLVE와 모든 judge는 자체 캐시
(place_routing_cache.json)에 고정하고, manifest(프롬프트·카탈로그·매핑 SHA) 불일치 시
.<sha>.json으로 물러두고 재실행한다.

실행: cd serving-team/08-app/backend && .venv/bin/python scripts/measure_place_routing.py
전제: kosha PG(canonical 정규화용) + OPENAI_API_KEY(backend/.env).
"""
from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
REPO = BACKEND.parents[2]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE.parent))

from build_article_signatures import _ensure_key  # noqa: E402 — .env에서 OPENAI 키 로드

_ensure_key()

import gimulmul_match  # noqa: E402 — 프롬프트 미러 드리프트 가드
import intake_photos  # noqa: E402 — VIS_SYS/VIS_SCHEMA(측정 Vision과 동일 프롬프트)
from app.services import cue_article_service, flow_service  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_normalizer import normalize_risk_feature_candidates  # noqa: E402
from app.services import risk_rule_service  # noqa: E402

ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
PHOTOS = REPO / "real-test-photo"
GOLD_CSV = PHOTOS / "place_gold" / "place_gold_v1.csv"
IN_VISION = ART / "intake_vision_gold.json"
RESOLVE_CACHE = ART / "rank_ab_resolve_cache_v2.json"
OUT_CACHE = ART / "place_routing_cache.json"
OUT_REPORT = ART / "place_routing_report.json"
VISION_MODEL = os.environ.get("PLACE_VISION_MODEL", "gpt-4.1")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def _manifest(kn: dict) -> dict:
    return {
        "vis_sys": _sha(intake_photos.VIS_SYS),
        "catalog": _sha(kn["catalog_text"]),
        "resolve_sys": _sha(cue_article_service.RESOLVE_SYS),
        "judge_sys": _sha(flow_service.JUDGE_SYS + json.dumps(flow_service.JUDGE_SCHEMA, sort_keys=True)),
        "mapping": _sha(json.dumps(flow_service.PLACE_TOPIC_BY_CODE, sort_keys=True, ensure_ascii=False)
                        + "|".join(flow_service.PLACE_DEFAULT_TOPICS)),
        "vision_model": VISION_MODEL,
    }


def _vision_new(path: Path) -> dict:
    from openai import OpenAI
    client = OpenAI()
    b64 = base64.b64encode(path.read_bytes()).decode()
    ext = path.suffix.lstrip(".").lower().replace("jpg", "jpeg")
    r = client.chat.completions.create(
        model=VISION_MODEL, max_completion_tokens=3000,
        messages=[{"role": "system", "content": intake_photos.VIS_SYS},
                  {"role": "user", "content": [
                      {"type": "text", "text": "이 사진을 분석하라."},
                      {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}}]}],
        response_format={"type": "json_schema", "json_schema": intake_photos.VIS_SCHEMA})
    return json.loads(r.choices[0].message.content)


def _canonical(res: dict, db) -> dict:
    ctx = " ".join([*(o.get("text", "") for o in res.get("visual_observations") or []),
                    *(c.get("text", "") for c in res.get("visual_cues") or [])])
    normalized = normalize_risk_feature_candidates(res.get("risk_feature_candidates", []), context_text=ctx)
    return risk_rule_service.apply_risk_rules(normalized, db, allow_context_only_inference=False)


def _rows_for(gks: list, fl: dict) -> list:
    rows = []
    for gk in gks:
        for r in fl["by_src"].get(gk, []):
            if r not in rows:
                rows.append(r)
    return rows


async def _route_photo(name: str, res: dict, gks: list, fl: dict, db, cache: dict) -> dict:
    scene = cue_article_service.scene_text(res)
    rows = _rows_for(gks, fl)
    canonical = _canonical(res, db)
    topics = flow_service.place_signals(canonical)
    judge = None
    if rows:
        jkey = f"judge::{name}"
        if jkey in cache:
            judge = cache[jkey]
        else:
            judge = await flow_service.judge_anchor(scene, rows)
            if judge is None:
                raise RuntimeError(f"judge 실패: {name}")
            cache[jkey] = judge
    d = flow_service.route_decision(len(rows), topics, judge)
    d["pred_anchor"] = rows[d["primary"]].get("src_key") or rows[d["primary"]]["no"] \
        if d["route"] == "anchor" and rows else ""
    d["n_rows"] = len(rows)
    d["place_signal_topics"] = topics
    return d


async def main() -> None:
    kn = cue_article_service._load_knowledge()  # noqa: SLF001
    assert kn, "서빙 카탈로그 로드 실패"
    assert cue_article_service.RESOLVE_SYS == gimulmul_match.RESOLVE_SYS, "RESOLVE 프롬프트 미러 드리프트"
    fl = flow_service._flows()  # noqa: SLF001
    assert fl, "흐름 데이터 로드 실패"
    at_names = {t["name"] for t in flow_service.always_applicable().get("topics", [])}
    assert set(flow_service.PLACE_TOPIC_BY_CODE.values()) <= at_names, "매핑 주제명이 basics에 없음"
    assert set(flow_service.PLACE_DEFAULT_TOPICS) <= at_names, "기본 주제명이 basics에 없음"

    man = _manifest(kn)
    cache = {}
    if OUT_CACHE.exists():
        old = json.loads(OUT_CACHE.read_text(encoding="utf-8"))
        if old.get("_manifest") == man:
            cache = old.get("data", {})
        else:
            bak = OUT_CACHE.with_suffix(f".{_sha(json.dumps(old.get('_manifest', {}), sort_keys=True))}.json")
            bak.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
            print(f"manifest 불일치 — 기존 캐시를 {bak.name}으로 물러둠")

    rows_csv = list(csv.DictReader(GOLD_CSV.open(encoding="utf-8")))
    vis_gold = {r["photo"]: r["result"]
                for r in json.loads(IN_VISION.read_text(encoding="utf-8"))["photos"]}
    rc = json.loads(RESOLVE_CACHE.read_text(encoding="utf-8"))
    rc_photos = rc.get("photos", rc)
    cat_keys = set(rc.get("_catalog_keys") or [])

    db = SessionLocal()
    results = []
    for row in rows_csv:
        rel = row["photo_file"]
        name = Path(rel).name
        photo_path = PHOTOS / rel
        # gold51 소속은 고정 표본 재사용(재추첨 금지), 신규는 자체 캐시
        if name in vis_gold and name in rc_photos:
            res = vis_gold[name]
            gks = [cue_article_service._norm_gk(g, cat_keys)  # noqa: SLF001 — 측정과 동일 정규화
                   for g in rc_photos[name].get("group_keys", [])]
        else:
            vkey, rkey = f"vision::{name}", f"resolve::{name}"
            if vkey not in cache:
                assert photo_path.exists(), f"사진 없음: {photo_path}"
                cache[vkey] = _vision_new(photo_path)
            res = cache[vkey]
            if rkey not in cache:
                cache[rkey] = await cue_article_service.resolve(cue_article_service.scene_text(res))
            gks = list(cache[rkey].get("group_keys", []))
        d = await _route_photo(name, res, gks, fl, db, cache)
        expect_topics = [t for t in (row.get("expect_topics") or "").split(";") if t]
        ok = None
        if row["expect"] == "place":
            ok = d["route"] == "place" and bool(set(expect_topics) & set(d["topics"]))
        elif row["expect"] == "anchor":
            ok = d["route"] == "anchor" and d["pred_anchor"] == row.get("expect_group_key", "")
        results.append({"photo": name, "expect": row["expect"], "expect_topics": expect_topics,
                        "expect_group_key": row.get("expect_group_key", ""), "source": row.get("source"),
                        **d, "ok": ok})
        OUT_CACHE.write_text(json.dumps({"_manifest": man, "data": cache}, ensure_ascii=False), encoding="utf-8")

    # gold51 전체 — 장소성 재라우팅 오탐(FP) 검사. Vision·RESOLVE는 고정 표본, judge만 신규.
    fp = []
    for name, pv in sorted(rc_photos.items()):
        if name.startswith("_") or name not in vis_gold:
            continue
        gks = [cue_article_service._norm_gk(g, cat_keys) for g in pv.get("group_keys", [])]  # noqa: SLF001
        d = await _route_photo(f"g51::{name}", vis_gold[name], gks, fl, db, cache)
        if d["route"] == "place":
            fp.append({"photo": name, **d})
        OUT_CACHE.write_text(json.dumps({"_manifest": man, "data": cache}, ensure_ascii=False), encoding="utf-8")

    place_rows = [r for r in results if r["expect"] == "place"]
    anchor_rows = [r for r in results if r["expect"] == "anchor"]
    prod_rows = [r for r in results if r["source"] == "prod"]
    gates = {
        "G-OLD-PLACE-FP": {"value": len(fp), "pass": len(fp) == 0},
        "G-MINI-PROD": {"value": sum(1 for r in prod_rows if r["ok"]), "n": len(prod_rows),
                        "pass": all(r["ok"] for r in prod_rows)},
        "G-MINI-PLACE": {"value": (sum(1 for r in place_rows if r["ok"]) / len(place_rows)) if place_rows else None,
                         "pass": bool(place_rows) and sum(1 for r in place_rows if r["ok"]) / len(place_rows) >= 0.8},
        "G-MINI-ANCHOR": {"value": (sum(1 for r in anchor_rows if r["ok"]) / len(anchor_rows)) if anchor_rows else None,
                          "pass": bool(anchor_rows) and all(r["ok"] for r in anchor_rows)},
    }
    report = {"manifest": man, "gates": gates, "results": results, "gold51_place_fp": fp}
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    for r in results:
        mark = {True: "OK  ", False: "FAIL", None: "diag"}[r["ok"]]
        print(f"{mark} [{r['expect']:<6}] {r['photo'][:44]:<46} -> {r['route']:<6} "
              f"{(r['pred_anchor'] or ','.join(r['topics']))[:40]}")
    print(f"\ngold51 장소성 FP: {len(fp)}")
    for f in fp[:5]:
        print("  FP:", f["photo"][:50])
    print("\n게이트:")
    for g, v in gates.items():
        print(f"  {g}: {'PASS' if v['pass'] else 'FAIL'} ({v.get('value')})")
    print(f"\n→ {OUT_REPORT.relative_to(REPO)}")


if __name__ == "__main__":
    asyncio.run(main())
