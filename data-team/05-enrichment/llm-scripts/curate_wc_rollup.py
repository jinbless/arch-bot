#!/usr/bin/env python3
"""COV-2 — work_context rollup의 UNKNOWN_CONTEXT 코드를 적합한 canonical로 큐레이션.

배경: canonical-code-vocabulary.json work_context rollup의 71 코드가 UNKNOWN_CONTEXT로
폴백(예: OVEN_OPERATION) → canonical fallback 매칭 실패. 71 코드+한글라벨은 재사용,
canonical 배정만 LLM(enum 제약=catalog allowlist). 일부는 work_context 아닌 다른 facet
(설비결함/안전상태)일 수 있어 wrong_facet 플래그.

출력: runtime-artifacts/wc_rollup_curation.jsonl (proposal). --apply 시 high-conf만
canonical-code-vocabulary.json rollup 갱신(생성물 아님 — SSOT라 보수적: proposal→리뷰→apply).

ENV: ANTHROPIC_API_KEY 또는 OPENAI_API_KEY (없으면 --mock 자동, plumbing만).
사용:
  python curate_wc_rollup.py --dry-run          # 대상/후보 미리보기(LLM 0)
  python curate_wc_rollup.py --mock              # mock으로 plumbing 검증(키 불요)
  python curate_wc_rollup.py --run               # LLM 호출 → proposal jsonl
  python curate_wc_rollup.py --run --apply --min-conf 0.8   # vocabulary rollup 패치
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = next(a for a in HERE.parents if (a / "shared" / "reference").is_dir())
sys.path.insert(0, str(ROOT / "shared" / "reference"))
sys.path.insert(0, str(HERE.parent))
import canonical_vocab as cv  # noqa: E402
from llm_client import LLMClient  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VOCAB = ROOT / "shared" / "reference" / "canonical-code-vocabulary.json"
CATALOG = ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
F1 = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "f1_light_proposals.json"
OUT = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "wc_rollup_curation.jsonl"
AXIS = "work_context"

SYSTEM = """당신은 KOSHA 산업안전 작업맥락(work_context) 분류 전문가입니다.
주어진 fine 작업맥락 코드를 KOSHA 표준 canonical work_context 중 가장 적합한 1개에 배정합니다.
원칙:
1. 적합한 canonical이 명확하면 그 코드를, 모호하면 UNKNOWN_CONTEXT(보수).
2. 이 코드가 '작업맥락'이 아니라 다른 facet(설비결함·안전상태·사고유형·보호구 등)에 속하면 wrong_facet=true.
3. confidence는 배정 확신도(0~1). 의미적으로 명백할 때만 높게."""


def load_labels() -> dict[str, str]:
    lab: dict[str, str] = {}
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    for code, v in cat["axes"].get(AXIS, {}).get("codes", {}).items():
        if isinstance(v, dict) and v.get("label"):
            lab[code] = v["label"]
    if F1.exists():
        f1 = json.loads(F1.read_text(encoding="utf-8")).get("proposals", {}).get(AXIS, {})
        for code, props in f1.items():
            if code not in lab and props:
                lab.setdefault(code, props[0].get("alias", ""))
    return lab


def canonical_choices(labels: dict[str, str]) -> list[tuple[str, str]]:
    codes = sorted(cv.canonical_set(AXIS) | cv.meta_set(AXIS))
    return [(c, labels.get(c, "")) for c in codes if c != "UNKNOWN_CONTEXT"]


def build_tool(choice_codes: list[str]) -> dict:
    return {
        "name": "assign_canonical",
        "description": "fine work_context 코드를 canonical work_context에 배정.",
        "input_schema": {
            "type": "object",
            "properties": {
                "canonical": {"type": "string", "enum": sorted(set(choice_codes) | {"UNKNOWN_CONTEXT"}),
                              "description": "가장 적합한 canonical (모호하면 UNKNOWN_CONTEXT)"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "wrong_facet": {"type": "boolean", "description": "work_context가 아닌 다른 facet이면 true"},
                "reason": {"type": "string", "description": "1문장 한국어"},
            },
            "required": ["canonical", "confidence", "wrong_facet", "reason"],
        },
    }


_MOCK_KW = [("전기", "ELECTRICAL_WORK"), ("배터리", "ELECTRICAL_WORK"), ("기계", "MACHINE"),
            ("절단", "MACHINE"), ("칼", "MACHINE"), ("청소", "GENERAL_WORKPLACE"),
            ("고소", "FALL_PROTECTION"), ("난간", "FALL_PROTECTION"), ("소음", "NOISE_WORK"),
            ("환기", "VENTILATION"), ("화학", "CHEMICAL_WORK"), ("온실", "GENERAL_WORKPLACE")]


def mock_fn(code: str, label: str):
    def fn(system, user):
        for kw, canon in _MOCK_KW:
            if kw in (label or ""):
                return {"canonical": canon, "confidence": 0.6, "wrong_facet": False, "reason": f"mock:{kw}"}
        return {"canonical": "UNKNOWN_CONTEXT", "confidence": 0.0, "wrong_facet": False, "reason": "mock:no-kw"}
    return fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--tier", default="strong")
    ap.add_argument("--min-conf", type=float, default=0.8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    roll = data["axes"][AXIS].get("rollup", {})
    unknown = sorted([c for c in roll if roll[c] == "UNKNOWN_CONTEXT"])
    labels = load_labels()
    choices = canonical_choices(labels)
    choice_codes = [c for c, _ in choices]
    if args.limit:
        unknown = unknown[:args.limit]

    print(f"UNKNOWN work_context 코드: {len(unknown)} | canonical 선택지: {len(choice_codes)}")
    if args.dry_run:
        print("후보(상위 10) + 라벨:")
        for c in unknown[:10]:
            print(f"  {c:30s} | {labels.get(c, '(라벨없음)')}")
        print("canonical 선택지(상위 12):", [f"{c}({l})" for c, l in choices[:12]])
        return 0

    client = LLMClient(provider=args.provider, tier=args.tier, mock=args.mock)
    tool = build_tool(choice_codes)
    print(f"LLM: provider={client.provider} model={client.model} mock={client.mock}")

    choice_lines = "\n".join(f"  {c} : {l}" for c, l in choices)
    proposals = []
    for i, code in enumerate(unknown, 1):
        label = labels.get(code, "")
        user = (f"fine work_context 코드: {code}\n한글: {label}\n\n"
                f"canonical 선택지(코드 : 한글):\n{choice_lines}\n\n"
                "이 코드에 가장 적합한 canonical은? 작업맥락이 아니면 wrong_facet=true.")
        out = client.structured(SYSTEM, user, tool, mock_fn=mock_fn(code, label))
        rec = {"code": code, "label": label, **{k: out.get(k) for k in ("canonical", "confidence", "wrong_facet", "reason")},
               "valid": out.get("canonical") in set(choice_codes) | {"UNKNOWN_CONTEXT"}}
        proposals.append(rec)
        if i % 20 == 0:
            print(f"  ...{i}/{len(unknown)}")

    OUT.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in proposals) + "\n", encoding="utf-8")
    assigned = [p for p in proposals if p["valid"] and not p["wrong_facet"]
                and p["canonical"] not in (None, "UNKNOWN_CONTEXT") and (p["confidence"] or 0) >= args.min_conf]
    wrong = [p for p in proposals if p["wrong_facet"]]
    print(f"proposal {len(proposals)} → {OUT.relative_to(ROOT)}")
    print(f"  배정(conf>={args.min_conf}, valid, work_context): {len(assigned)}")
    print(f"  wrong_facet(다른 facet): {len(wrong)}")
    print("  배정 샘플:", [(p["code"], p["canonical"], p["confidence"]) for p in assigned[:8]])

    if args.apply and assigned:
        for p in assigned:
            roll[p["code"]] = p["canonical"]
        data["axes"][AXIS]["rollup"] = roll
        VOCAB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  [APPLY] rollup {len(assigned)}건 갱신 → {VOCAB.relative_to(ROOT)} (재검증: python shared/reference/canonical_vocab.py)")
    elif args.apply:
        print("  [APPLY] 배정 0 — 무변경")
    return 0


if __name__ == "__main__":
    sys.exit(main())
