#!/usr/bin/env python3
"""RESOLVE만 다시 돌려 앵커 캐시를 새로 만든다 (카탈로그가 바뀐 뒤 재측정용).

왜 필요한가: `rank_ab_resolve_cache.json`은 **그때의 카탈로그**로 만들어진 결과다.
카탈로그에서 빠져 있던 그룹은 RESOLVE가 고를 방법이 아예 없었으므로,
카탈로그를 바꾼 뒤에도 옛 캐시로 재면 바뀐 부분이 보이지 않는다.

실제로 그랬다 — 비계 6종을 카탈로그에 올렸는데(2026-08-02) 옛 캐시로 재니
비계 사진 15장이 전부 오인식으로 남았다. RESOLVE의 자유 텍스트는 '비계(발판)'이라고
정확히 말하고 있었는데 카탈로그에 없어 group_key로 옮기지 못한 것이다.

★ **기존 캐시를 덮어쓰지 않는다.** `rank_ab_resolve_cache.json`은 RANK A/B 실측의
  구성 요소라 지우면 그 측정이 재현 불가가 된다. 새 파일에 쓰고, 측정 스크립트가
  새 파일이 있으면 그걸 쓴다.

사용: .venv/bin/python scripts/rerun_resolve_cache.py [--workers 6] [--limit 0]
출력: data-team/05-enrichment/runtime-artifacts/rank_ab_resolve_cache_v2.json
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))

import rank_ab_gold as R  # noqa: E402  — 프롬프트·스키마·모델을 그대로 쓴다(측정 조건 동일)

OUT = R.ART / "rank_ab_resolve_cache_v2.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    vis = {r["photo"]: r["result"] for r in json.loads(R.IN_VISION.read_text(encoding="utf-8"))["photos"]}
    photos = sorted([p for p in R.gold if p in vis])
    if args.limit:
        photos = photos[:args.limit]

    # 카탈로그는 **지금** 인덱스에서 만든다 — rank_ab_gold 모듈 로드 시점 값을 그대로 쓴다.
    print(f"사진 {len(photos)}장 · 카탈로그 {R.catalog_text.count(chr(10)) + 1}종 · model={R.MODEL}", flush=True)

    cache, fails = {}, []
    if OUT.exists():
        cache = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"기존 v2 캐시 {len(cache)}장 재사용 — 새로 부를 것 {len([p for p in photos if p not in cache])}장")
    todo = [p for p in photos if p not in cache]

    def _resolve(pf):
        st = R.scene_text(vis[pf])
        return pf, R.chat(R.RESOLVE_SYS,
                          f"[장면]\n{st}\n\n[기인물 그룹 카탈로그]\n{R.catalog_text}\n\n주요 기인물의 group_key 선택.",
                          R.RESOLVE_SCHEMA)

    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(_resolve, p): p for p in todo}
            for i, fu in enumerate(as_completed(futs), 1):
                try:
                    pf, rv = fu.result()
                    cache[pf] = rv
                except Exception as e:  # noqa: BLE001
                    fails.append({"photo": futs[fu], "err": str(e)[:200]})
                if i % 20 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
        OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n완료 {len(cache)}장 · 실패 {len(fails)}장")
    for f in fails[:5]:
        print(f"  ERR {f['photo'][:36]}: {f['err'][:100]}")

    # 카탈로그에 새로 들어온 그룹을 실제로 고르기 시작했는지 바로 확인한다
    old_p = R.ART / "rank_ab_resolve_cache.json"
    if old_p.exists():
        old = json.loads(old_p.read_text(encoding="utf-8"))
        newly = {}
        for pf, rv in cache.items():
            was = set((old.get(pf) or {}).get("group_keys", []))
            for gk in set(rv.get("group_keys", [])) - was:
                newly[gk] = newly.get(gk, 0) + 1
        print("\n[새 캐시에서 새로 선택된 그룹 상위]")
        for gk, n in sorted(newly.items(), key=lambda x: -x[1])[:12]:
            print(f"  {n:3d}장  {gk}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
