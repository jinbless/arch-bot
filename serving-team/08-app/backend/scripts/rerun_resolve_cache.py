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

★★ 캐시가 **스스로 낡았는지 안다**. 위 실수를 두 번 했다(비계 6종, 우산 7종). 사람이
   "카탈로그 바꿨으니 재실행해야지"를 기억하는 것에 의존하면 또 놓친다. 그래서 캐시 파일에
   **그때 쓴 카탈로그 자체**를 함께 적는다.
     - 카탈로그가 달라졌으면 옛 캐시를 `.<sha>.json`으로 물러두고 처음부터 다시 부른다
     - 측정 스크립트는 캐시에 적힌 카탈로그로 채점 범위를 정한다 —
       재계산하지 않으므로 측정과 캐시가 어긋날 수 없다

사용: .venv/bin/python scripts/rerun_resolve_cache.py [--workers 6] [--limit 0]
출력: data-team/05-enrichment/runtime-artifacts/rank_ab_resolve_cache_v2.json
"""
from __future__ import annotations

import argparse
import hashlib
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

    keys = sorted(l.split(" ::")[0] for l in R.catalog_text.splitlines() if l.strip())
    # ★ 해시는 **줄 전체 + Vision 캐시 내용**으로 — 키만 해시하면 판별 단서 서술이 바뀌어도,
    #   카탈로그만 해시하면 Vision 프롬프트가 바뀌어 장면 서술이 달라져도 캐시가 재사용되어
    #   LLM이 새 입력을 본 적 없는 채로 옛 답을 침묵 보고한다(A0 적대적 검토 3번 + v2 채택).
    vis_sha = hashlib.sha256(R.IN_VISION.read_bytes()).hexdigest()[:12]
    # RESOLVE 프롬프트도 무효화 입력에 — 프롬프트 개정(A-2 이탈구도 등)이 캐시 재사용으로
    # 침묵되면 측정이 옛 프롬프트를 채점한다(카탈로그·Vision과 같은 클래스의 누락이었음).
    sys_sha = hashlib.sha256(R.RESOLVE_SYS.encode()).hexdigest()[:12]
    sha = hashlib.sha256(("\n".join(sorted(R.catalog_text.splitlines())) + "|vis:" + vis_sha
                          + "|sys:" + sys_sha)
                         .encode()).hexdigest()[:12]

    cache, fails = {}, []
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        old_sha = old.get("_catalog_sha") if isinstance(old, dict) else None
        old_photos = old.get("photos") if old_sha else old      # 옛 형식 = 사진 dict 그대로
        if old_sha == sha:
            cache = dict(old_photos or {})
            print(f"기존 캐시 {len(cache)}장 재사용 (카탈로그 동일 {sha})")
        else:
            # ★ 카탈로그가 달라졌다 — 옛 답은 **그때의 보기 목록**으로 고른 것이라 재사용하면 안 된다.
            #   지우지도 않는다. 물러두고 처음부터 다시 부른다.
            bak = OUT.with_suffix(f".{old_sha or 'legacy'}.json")
            bak.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
            n_old = len(old_photos or {})
            print(f"⚠ 카탈로그가 바뀌었다 ({old_sha or '기록없음'} → {sha}) — 캐시 {n_old}장 전부 재실행")
            print(f"  옛 캐시는 {bak.name} 로 물러뒀다")
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
    # 카탈로그를 함께 적는다. 측정 스크립트는 이 목록으로 채점 범위를 정한다 —
    # 재계산하지 않으므로 "LLM이 본 보기"와 "채점이 인정하는 정답"이 어긋날 수 없다.
    OUT.write_text(json.dumps({"_note": "RESOLVE 앵커 캐시. _catalog_keys = 이 답을 낼 때 LLM에게 준 보기 목록.",
                               "_catalog_sha": sha, "_catalog_keys": keys, "_model": R.MODEL,
                               "photos": cache}, ensure_ascii=False, indent=1), encoding="utf-8")

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
