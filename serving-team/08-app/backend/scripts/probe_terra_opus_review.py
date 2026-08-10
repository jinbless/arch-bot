#!/usr/bin/env python3
"""terra A/B 불일치 사진의 Claude Opus 5 검수 프로브.

무엇을 하나: 현행(4.1+5.4)과 terra(5.6-terra)가 서로 다른 앵커(group_key)를 고른 사진에
대해, claude-opus-5가 **사진을 직접 보고** 어느 선택이 주 기인물 앵커로 더 부합하는지
블라인드 판정한다(선택지 순서는 사진명 해시로 뒤섞고 어느 쪽이 어느 모델인지 알리지 않음).
판정을 gold 채점과 대조해 "Opus 검수가 gold와 얼마나 일치하는가"와 "Opus가 어느 팔을
선호하는가"를 함께 잰다.

원칙 준수: Opus에게도 법령/조문 판단은 시키지 않는다 — 닫힌 카탈로그에서의 그룹 선택
적합성 판정만(RESOLVE와 같은 범위). 사유는 사진 관찰 근거로 쓰게 한다.

사용: ANTHROPIC_API_KEY 필요(backend/.env에서 자동 로드).
      .venv/bin/python scripts/probe_terra_opus_review.py [--workers 3] [--model claude-opus-5]
출력: runtime-artifacts/terra_opus_review.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))

import rank_ab_gold as R  # noqa: E402 — catalog_text·경로 재사용

ART = R.ART
PHOTO_DIR = R.REPO / "real-test-photo" / "label_photo"
REPORT = ART / "terra_ab_report.json"
CACHE_A = ART / "rank_ab_resolve_cache_v2.json"
OUT = ART / "terra_opus_review.json"

SYS = (
    "너는 산업안전 감독 사진 검수자다. 사진에서 출발해 '주 기인물 앵커'(닫힌 카탈로그의 "
    "group_key)를 고르는 시스템의 두 후보 선택을 검수한다. 사진에 실제로 보이는 주 기인물"
    "(위험의 근원이 되는 설비·장소·물질)과 각 선택이 부합하는지를 **사진 관찰 근거로만** "
    "판정하라. 법령 조문·벌칙 판단은 하지 말라. 카탈로그 밖의 키를 지어내지 말라.")

VERDICT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "choice": {"type": "string", "enum": ["1", "2", "둘다부적절", "동등"]},
        "better_keys": {"type": "array", "items": {"type": "string"},
                        "description": "둘다부적절일 때 카탈로그에서 더 적절한 group_key(없으면 빈 배열)"},
        "reason": {"type": "string", "description": "사진 관찰 근거 한두 문장"}},
    "required": ["choice", "better_keys", "reason"]}


def _ensure_anthropic_key() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    for envf in (BACKEND / ".env", BACKEND.parent / ".env"):
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        os.environ["ANTHROPIC_API_KEY"] = v
                        return
    raise SystemExit("ANTHROPIC_API_KEY가 없다 — backend/.env 확인")


def photo_b64(p: Path) -> str:
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--model", default="claude-opus-5")
    args = ap.parse_args()
    _ensure_anthropic_key()

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    cache_a = json.loads(CACHE_A.read_text(encoding="utf-8"))["photos"]
    cat_line = {l.split(" ::")[0]: l for l in R.catalog_text.splitlines() if l.strip()}

    probes = []
    for row in report["per_photo"]:
        p = row["photo"]
        pa = sorted(set((cache_a.get(p) or {}).get("group_keys", [])))
        pb = sorted(set(row.get("picked_b", [])))
        if pa == pb or not (PHOTO_DIR / p).exists():
            continue
        # gold 관점의 판가름(누가 옳은가) — Opus에게는 주지 않는다
        gv = ("A" if row["exact_a"] and not row["exact_b"] else
              "B" if row["exact_b"] and not row["exact_a"] else
              "both" if row["exact_a"] else "neither")
        probes.append({"photo": p, "picked_a": pa, "picked_b": pb, "gold_verdict": gv,
                       "flow_a": row["flow_a"], "flow_b": row["flow_b"]})
    if not probes:
        raise SystemExit("불일치 사진이 없다 — terra_ab_report부터 확인")
    print(f"불일치 {len(probes)}장 검수 시작 · model={args.model}")

    import anthropic
    client = anthropic.Anthropic(max_retries=3)

    def _lines(keys):
        return "\n".join(f"  - {cat_line.get(k, k)}" for k in keys) or "  (선택 없음)"

    def review(pr: dict) -> dict:
        # 블라인드: 사진명 해시 짝수면 A가 선택지1, 홀수면 B가 선택지1
        a_first = int(hashlib.sha256(pr["photo"].encode()).hexdigest(), 16) % 2 == 0
        opt1, opt2 = (pr["picked_a"], pr["picked_b"]) if a_first else (pr["picked_b"], pr["picked_a"])
        user_text = (
            "다음은 이 사진의 '주 기인물 앵커' 두 후보 선택이다(카탈로그의 group_key).\n\n"
            f"[선택지 1]\n{_lines(opt1)}\n\n[선택지 2]\n{_lines(opt2)}\n\n"
            "[전체 카탈로그 — 닫힌 집합]\n" + R.catalog_text + "\n\n"
            "사진을 보고 판정하라: 어느 선택이 사진의 주 기인물과 더 부합하는가?\n"
            "- 한쪽이 명확히 낫다 → \"1\" 또는 \"2\"\n"
            "- 둘 다 사진의 주 기인물이 아니다 → \"둘다부적절\" (+ better_keys에 카탈로그의 더 적절한 키)\n"
            "- 둘 다 그럴듯해 우열이 없다 → \"동등\"")
        kwargs = dict(
            model=args.model, max_tokens=8000, system=SYS,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": photo_b64(PHOTO_DIR / pr["photo"])}},
                {"type": "text", "text": user_text}]}])
        try:
            resp = client.messages.create(
                **kwargs, extra_body={"output_config": {"format": {"type": "json_schema",
                                                                   "schema": VERDICT_SCHEMA}}})
        except anthropic.BadRequestError:
            resp = client.messages.create(**kwargs)  # 구조화 출력 미지원 시 자유 JSON으로
        if resp.stop_reason == "refusal":
            return {**pr, "opus": {"choice": "refusal", "better_keys": [], "reason": "safety refusal"}}
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            v = json.loads(text[text.index("{"):text.rindex("}") + 1])
        except Exception:  # noqa: BLE001
            v = {"choice": "parse_error", "better_keys": [], "reason": text[:200]}
        # 블라인드 해제: 선택지 번호 → 팔
        ch = v.get("choice")
        arm = ("A" if (ch == "1") == a_first else "B") if ch in ("1", "2") else ch
        return {**pr, "blind_a_first": a_first, "opus": v, "opus_arm": arm}

    results, fails = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(review, pr): pr["photo"] for pr in probes}
        for i, fu in enumerate(as_completed(futs), 1):
            try:
                results.append(fu.result())
            except Exception as e:  # noqa: BLE001
                fails.append({"photo": futs[fu], "err": str(e)[:200]})
            print(f"  {i}/{len(probes)}", flush=True)
    results.sort(key=lambda r: r["photo"])

    # ── 집계 ──
    decisive = [r for r in results if r["gold_verdict"] in ("A", "B") and r.get("opus_arm") in ("A", "B")]
    agree = sum(1 for r in decisive if r["opus_arm"] == r["gold_verdict"])
    pref = {"A": 0, "B": 0, "둘다부적절": 0, "동등": 0}
    for r in results:
        k = r.get("opus_arm")
        if k in pref:
            pref[k] += 1
    summary = {
        "n_reviewed": len(results), "fails": fails,
        "opus_preference": {"현행(A)": pref["A"], "terra(B)": pref["B"],
                            "둘다부적절": pref["둘다부적절"], "동등": pref["동등"]},
        "gold_decisive": len(decisive), "opus_gold_agree": agree,
        "opus_gold_agree_rate": round(agree / len(decisive), 3) if decisive else None}
    OUT.write_text(json.dumps({"_model": args.model, "summary": summary, "items": results},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== Opus 검수 ({len(results)}장, 실패 {len(fails)}) ===")
    print(f"  선호: 현행 {pref['A']} · terra {pref['B']} · 둘다부적절 {pref['둘다부적절']} · 동등 {pref['동등']}")
    if decisive:
        print(f"  gold 판가름 사진 {len(decisive)}장 중 Opus 일치 {agree} ({agree/len(decisive):.0%})")
    for r in results:
        if r["gold_verdict"] in ("A", "B") and r.get("opus_arm") != r["gold_verdict"]:
            print(f"  [gold={r['gold_verdict']} vs opus={r.get('opus_arm')}] {r['photo'][:40]}: "
                  f"{r['opus'].get('reason', '')[:90]}")
    print(f"→ {OUT.name}")


if __name__ == "__main__":
    main()
