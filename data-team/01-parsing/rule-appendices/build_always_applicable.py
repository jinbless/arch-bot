#!/usr/bin/env python3
"""사진과 무관하게 **늘 지켜야 하는 것** 목록 — '기본 안전수칙' 카테고리의 재료.

왜 필요한가. 흐름 6칸은 사진에서 잡은 앵커에 매달린다. 그런데 규칙에는 앵커가 될 수 없는
의무가 있다 — 작업장 시설, 통로·계단 구조, 보호구 지급처럼 **시간축이 없고 현장이 늘 갖춰야 할 상태**다.
이런 것들은 앵커에 안 걸리면 사업주가 볼 방법이 아예 없다.

사용자 판단(2026-08-02):
> "작업장은 흐름이라기보다 작업 중에 해야 하는 것들이라 별도 흐름은 필요없어 보인다."
> "보호구는 흐름이 없어."
> "이런 것들은 따로 모아서 사진인식이 아닌 기본적으로 알아야 하는 서비스 카테고리를 만들어야 하나?"

★ 담는 기준 — 셋을 **모두** 만족해야 한다:
  1. RESOLVE 앵커 카탈로그 **밖**이다(= 사진으로 자동 지목되지 않는다)
  2. 그 조문이 **다른 흐름에 이미 들어가 있지 않다**(중복이면 두 번 보여줄 이유가 없다.
     실제로 315건 중 252건이 중복이었다 — 양중기 총칙·차량계 총칙·기계 일반기준은
     각 기인물 흐름에 상속되므로 여기 또 넣으면 안 된다)
  3. **기인물 그룹이 아니다.** 곤돌라는 카탈로그 밖이지만(전용 조문 제160조 하나가 관찰 불가)
     사진에 뚜렷이 보이는 기인물이고 흐름이 41건 있다 — 상시가 아니라 앵커 쪽 과제다

사용: python data-team/01-parsing/rule-appendices/build_always_applicable.py
출력: data-team/05-enrichment/runtime-artifacts/always_applicable.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
IDX = ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "trackA" / "gimulmul_index.json"
OUT = ART / "always_applicable.json"

OBS_OK = ("yes", "partial")

# 주제 묶음 — 그룹키 → (주제, 한 줄 설명). 사업주가 읽을 순서대로.
# ⚠ 설명은 조문을 요약하지 않는다. '무엇에 관한 묶음인지'만 말한다.
TOPICS = [
    ("작업장 시설", "작업장이 늘 갖추고 있어야 하는 것 — 바닥·조명·출입구·안전난간·비상구",
     ["장2 작업장"]),
    ("통로·계단", "통로와 계단의 구조 기준. 만들 때 지켜야 하고, 이후 그 상태를 유지해야 한다",
     ["장3 통로"]),
    ("추락·붕괴 방지", "어느 현장에나 걸리는 추락·붕괴 예방 조치",
     ["절1 추락에 의한 위험 방지", "절2 붕괴 등에 의한 위험 방지"]),
    ("보호구", "지급·착용시켜야 하는 보호구. 위험의 원인이 아니라 대응 수단이라 흐름이 없다",
     ["장4 보호구"]),
    ("특수형태근로종사자·배달종사자", "고용 형태에 걸리는 의무. 사진 속 대상이 아니다",
     ["편4 특수형태근로종사자 등에 대한 안전조치 및 보건조치"]),
]


def main() -> None:
    fl = json.loads((ART / "flow_slice_all.json").read_text(encoding="utf-8"))
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    catalog = {gk for gk, g in idx["groups"].items()
               if sum(1 for a in g["articles"] if a.get("observable") in OBS_OK) >= 1
               and gk not in idx["cross_cutting"]}

    rows = {r["no"]: r for r in fl["rows"]}
    # ② 다른 흐름(카탈로그 안 그룹)에 이미 나오는 조문 — 중복이므로 뺀다
    in_flow = {it["ref"] for r in fl["rows"] if r["src_key"] in catalog
               for v in r["items"].values() for it in v}

    topics, total, dropped = [], 0, 0
    for name, desc, keys in TOPICS:
        items = []
        for k in keys:
            r = rows.get(k)
            if r is None:
                print(f"⚠ 그룹 없음: {k}")
                continue
            if r["src_key"] in catalog:
                print(f"⚠ {k} 는 앵커 카탈로그 안에 있다 — 상시가 아니라 흐름으로 가야 한다")
                continue
            # ★ 조문 단위로 합친다. 흐름에서는 한 조문이 여러 칸에 걸치는 게 정상이지만
            #   (제44조 = 작업 전 점검 + 작업 중), **여기는 시간축이 없다.**
            #   그대로 펼치면 같은 조문이 두 번 뜬다(실제로 제15·42·44조가 그랬다).
            #   근거 문구는 있는 것만 모아 합친다 — 자리표시(빈 문자열)는 버린다.
            seen: dict[str, dict] = {}
            for its in r["items"].values():
                for it in its:
                    if it["ref"] in in_flow:
                        dropped += 1
                        continue
                    cur = seen.get(it["ref"])
                    if cur is None:
                        seen[it["ref"]] = {"text": it["text"], "ref": it["ref"], "source": it["source"],
                                           "evidences": [it["evidence"]] if it.get("evidence") else [],
                                           "tier": "권고" if "권고" in it["source"] else "법정",
                                           "group": r["subject"]}
                    elif it.get("evidence") and it["evidence"] not in cur["evidences"]:
                        cur["evidences"].append(it["evidence"])
            for v in seen.values():
                v["evidence"] = " / ".join(v.pop("evidences"))
                items.append(v)
        items.sort(key=lambda x: (0 if x["tier"] == "법정" else 1,
                                  int("".join(c for c in x["ref"].split("조")[0] if c.isdigit()) or 0)))
        topics.append({"name": name, "desc": desc, "n": len(items), "items": items})
        total += len(items)
        print(f"  {name:22} {len(items):3d}건")

    OUT.write_text(json.dumps({
        "_note": "사진과 무관하게 늘 지켜야 하는 것. 흐름 6칸은 앵커에 매달리는데, 앵커가 될 수 없는 의무가 여기 모인다.",
        "_기준": "① 앵커 카탈로그 밖 ② 다른 흐름에 이미 없음 ③ 기인물 그룹이 아님",
        "_warning": "라벨(어느 주제인가)은 사람 검수 전이다. 조문 자체는 규칙 원문이다.",
        "reviewed_by_human": False,
        "n_total": total, "n_dropped_duplicate": dropped,
        "topics": topics,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n총 {total}건 · 다른 흐름과 중복이라 뺀 것 {dropped}건")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
