#!/usr/bin/env python3
"""intake_vision_gold.json 재생성 — Vision v2(관찰 체크리스트) 채택분.

왜: Vision 프롬프트가 v2로 승격되면(intake_photos.VIS_SYS) gold Vision 캐시도 같은
프롬프트로 다시 만들어야 측정과 서빙이 같은 조건이 된다. 옛 캐시는 백업으로 물러둔다
(RANK A/B 등 과거 실측의 구성 요소 — 지우면 재현 불가).

비용 절약: measure_vision_v2_ab의 자체 캐시(vision_v2_ab_cache.json)에 이미 v2로 판독한
51장이 있다 — 재사용하고 나머지만 새로 부른다.

사용: .venv/bin/python scripts/regen_vision_gold.py [--workers 4]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

import intake_photos as IP  # noqa: E402 — VIS_SYS(v2)·VIS_SCHEMA·data_url

REPO = HERE.parents[4]
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
PHOTO_DIR = REPO / "real-test-photo" / "label_photo"
GOLD_CSV = PHOTO_DIR / "label_curation_gold.csv"
OUT = ART / "intake_vision_gold.json"
AB_CACHE = ART / "vision_v2_ab_cache.json"
VISION_MODEL = "gpt-4.1"
# ★ 프롬프트가 바뀔 때마다 갱신 — 캐시에 이 태그가 박혀 어느 프롬프트의 산물인지 남는다.
VIS_TAG = "v3-smoke-cues-2026-08-10"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    assert "관찰 체크리스트" in IP.VIS_SYS, "VIS_SYS가 v2가 아니다 — intake_photos부터 확인"

    photos = set()
    with GOLD_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            photos.add(r["photo_file"])
    photos = sorted(p for p in photos if (PHOTO_DIR / p).exists())

    # A/B 캐시 재사용은 **그 캐시가 지금 프롬프트로 만든 것일 때만**(vis_sys_sha 대조).
    # v2→v3처럼 프롬프트가 바뀌면 재사용이 곧 침묵 오염이다(rerun_resolve_cache의 교훈).
    import hashlib
    cur_sha = hashlib.sha256(IP.VIS_SYS.encode()).hexdigest()[:12]
    reuse = {}
    if AB_CACHE.exists():
        ab = json.loads(AB_CACHE.read_text(encoding="utf-8"))
        if (ab.get("_manifest") or {}).get("vis_sys_sha") == cur_sha:
            for name, run in ab.get("runs", {}).items():
                if "vision" in run:
                    reuse[name] = run["vision"]
        else:
            print("A/B 캐시는 다른 프롬프트 산물 — 재사용 안 함")

    if OUT.exists():
        old_tag = json.loads(OUT.read_text(encoding="utf-8")).get("_vis_prompt_tag", "v1")
        bak = OUT.with_suffix(f".{old_tag.split('-')[0]}.json")
        if not bak.exists():
            bak.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"옛 캐시({old_tag}) 백업 → {bak.name}")

    from build_article_signatures import _ensure_key
    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    def vision(name: str) -> dict:
        p = PHOTO_DIR / name
        r = client.chat.completions.create(model=VISION_MODEL, messages=[
            {"role": "system", "content": IP.VIS_SYS},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": IP.data_url(p)}}]}],
            response_format={"type": "json_schema", "json_schema": IP.VIS_SCHEMA})
        return json.loads(r.choices[0].message.content)

    results = {n: reuse[n] for n in photos if n in reuse}
    todo = [n for n in photos if n not in results]
    print(f"gold 사진 {len(photos)}장 · A/B 캐시 재사용 {len(results)} · 신규 판독 {len(todo)}")

    fails = []
    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(vision, n): n for n in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                n = futs[fu]
                try:
                    results[n] = fu.result()
                except Exception as e:  # noqa: BLE001
                    fails.append({"photo": n, "err": str(e)[:160]})
                if i % 10 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)

    OUT.write_text(json.dumps(
        {"_note": "gold Vision 캐시 — intake_photos.VIS_SYS와 동일 프롬프트",
         "_vis_prompt_tag": VIS_TAG, "_vis_sys_sha": cur_sha, "_model": VISION_MODEL,
         "photos": [{"photo": n, "result": results[n]} for n in sorted(results)]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"완료 {len(results)}장 · 실패 {len(fails)} → {OUT.name}")
    for f in fails[:5]:
        print(f"  ERR {f['photo'][:40]}: {f['err'][:80]}")


if __name__ == "__main__":
    main()
