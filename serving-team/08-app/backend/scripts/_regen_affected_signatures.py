#!/usr/bin/env python3
"""[1회성 보정] 의N 조문 누락/오염 수정 후, 영향받은 RULE 조문의 관찰 시그니처만
targeted 동기 재생성하여 article_signatures.jsonl에 병합.

영향대상 = (현 signatures에 없음) OR (sig.title != 현 DB title)  → 신규 의N + 오염 교정 base.
전체 672 재배치(build_article_signatures batch) 대신 ~27건만 동기 호출.
사용: .venv/bin/python scripts/_regen_affected_signatures.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE.parent))

from build_article_signatures import SYS, SCHEMA, MODEL, OUT, _ensure_key, _articles  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    arts = {a["code"]: a for a in _articles()}            # 현 DB RULE 조문 (교정 반영됨)
    existing = {}
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                existing[r["article_code"]] = r

    affected = []
    for code, a in arts.items():
        sig = existing.get(code)
        if sig is None or (sig.get("title") or "") != (a["title"] or ""):
            affected.append(code)
    affected.sort(key=lambda c: (int(c.split("조")[0][1:]), int(c.split("의")[1]) if "의" in c else 0))

    print(f"DB RULE 조문 {len(arts)} | 기존 sig {len(existing)} | 영향대상 {len(affected)}")
    sub = [c for c in affected if "조의" in c]
    print(f"  신규/의N {len(sub)} | 오염 base 교정 {len(affected)-len(sub)}")
    print("  대상:", ", ".join(affected))
    if args.dry_run:
        return
    if not affected:
        print("영향대상 없음 — 종료.")
        return

    _ensure_key()
    from openai import OpenAI
    client = OpenAI()

    counts = {"yes": 0, "partial": 0, "no": 0}
    for i, code in enumerate(affected, 1):
        a = arts[code]
        user = (
            f"[조문] {a['code']} {a['title']}\n"
            f"[분류(편/장/절/관)] {a['section']}\n"
            f"[전문]\n{a['full'][:2500]}\n\n위 조문을 관찰 시그니처로 변환하라."
        )
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}],
                    response_format={"type": "json_schema", "json_schema": SCHEMA},
                )
                data = json.loads(resp.choices[0].message.content)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  [{code}] 시도{attempt+1} 실패: {str(e)[:80]}")
                time.sleep(2)
        else:
            print(f"  [{code}] 3회 실패 — 스킵")
            continue
        obs = data.get("observable", "no")
        counts[obs] = counts.get(obs, 0) + 1
        existing[code] = {
            "article_code": code, "title": a["title"], "section": a["section"],
            "observable": obs, "observable_reason": data.get("observable_reason", ""),
            "context": data.get("context", ""), "equipment": data.get("equipment", []),
            "visual_cues": data.get("visual_cues", []), "required_measures": data.get("required_measures", []),
            "violation_scene": data.get("violation_scene", ""), "by_model": MODEL,
        }
        print(f"  [{i}/{len(affected)}] {code} {a['title'][:20]} → {obs}")

    # backup + write merged
    if OUT.exists():
        shutil.copy2(OUT, OUT.with_suffix(".jsonl.pre-regen-backup"))
    ordered = sorted(existing.values(),
                     key=lambda r: (int(r["article_code"].split("조")[0][1:].lstrip("제")) if r["article_code"].startswith("제") else 0,
                                    int(r["article_code"].split("의")[1]) if "의" in r["article_code"] else 0))
    with OUT.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n병합 완료: {OUT.name} 총 {len(existing)}행 | 재생성 관찰성 {counts}")


if __name__ == "__main__":
    main()
