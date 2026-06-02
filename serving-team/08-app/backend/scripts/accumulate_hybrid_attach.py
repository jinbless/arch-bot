#!/usr/bin/env python3
"""Phase 4 (v5) — hybrid_attach 누적 batch (design-a: 파생 캐시 자동, SSOT 수동).

검증된 semantic attach(rerank on)를 코퍼스에 대해 실행 → alias(name→codes)·link(code_sig→guide/sr)
누적 → support_count≥k 승격(자동) → 파생 캐시 저장 + SSOT 후보 curation report(수동 검토).

- 파생 캐시(learned.json): 자동. 서빙은 HYBRID_ATTACH_CACHE=on일 때 promoted만 읽음(LLM 미호출).
- SSOT(canonical_vocab/SHE/TBox): 본 batch는 후보 report만. 사람 승인 + reasoner/SHACL/manifest 게이트.

실행: ./.venv/bin/python scripts/accumulate_hybrid_attach.py [--limit N] [--k 2]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.database import SessionLocal  # noqa: E402
from app.services.hazard_to_guide_service import match_hazards_to_guides  # noqa: E402
from app.services import hybrid_attach_store as store  # noqa: E402
from replay_synthetic_observations import load_synthetic_cases  # noqa: E402
from eval_semantic_attach import synth  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
CURATION = REPO / "data-team" / "05-enrichment" / "runtime-artifacts" / "hybrid_attach_curation.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=300, help="누적 대상 case 수 (rerank LLM 비용 고려)")
    ap.add_argument("--k", type=int, default=2, help="promote 임계 support_count")
    args = ap.parse_args()

    # 검증된(rerank) attach 누적 — recall+온톨로지검증+rerank를 통과한 결과만 기록
    os.environ["SEMANTIC_ATTACH"] = "on"
    os.environ["SEMANTIC_ATTACH_RERANK"] = "on"

    cases = load_synthetic_cases(limit=args.limit)
    data = store.load(force=True)
    # 멱등: 재실행 누적 왜곡 방지 위해 빈 store에서 시작
    data = {"aliases": {}, "links": {}, "meta": {"promote_k": args.k}}
    print(f"accumulating over {len(cases)} cases (rerank on) ...")

    with SessionLocal() as db:
        for i, case in enumerate(cases):
            if i % 50 == 0:
                print(f"  {i}/{len(cases)}", flush=True)
            hz, canonical = synth(case)
            name = hz["name"]
            codes = canonical.get("hazard_name_to_codes", {}).get(name, [])
            if not codes:
                continue
            try:
                rels, _ = match_hazards_to_guides(db, [hz], canonical, industry_contexts=[])
            except Exception as e:  # noqa: BLE001
                print(f"  attach 실패 {case.get('case_id')}: {e}")
                continue
            rel = rels[0] if rels else {}
            guides = rel.get("guides") or []
            srs = rel.get("semantic_sr_ids") or []
            if not guides:
                continue
            store.record_link(data, codes, guides, srs, confidence=1.0)
            store.record_alias(data, name, codes, confidence=1.0)

    pstats = store.promote(data, k=args.k)
    store.save_store(data)
    s = store.stats()
    print(f"\n누적 완료: links={s['links']}(promoted {s['links_promoted']}) "
          f"aliases={s['aliases']}(promoted {s['aliases_promoted']}) k={args.k}")
    print(f"store: {store.STORE_PATH}")

    # ── SSOT curation report (수동 검토 — 자동 적용 금지) ──
    promoted_links = sorted(
        ((sig, l) for sig, l in data["links"].items() if l["status"] == "promoted"),
        key=lambda kv: kv[1]["support"], reverse=True,
    )
    lines = [
        "# hybrid_attach SSOT curation 후보 (수동 검토)",
        "",
        "> ⚠️ 자동 생성. **SSOT(canonical_vocab/SHE TTL/TBox) 자동 적용 금지.** ",
        "> 사람 승인 + reasoner 일관성 + SHACL + manifest 게이트 후 편입.",
        f"> 파생 캐시(learned.json)는 자동 승격됨(support≥{args.k}). 본 report는 SSOT 편입 후보만.",
        "",
        f"## link 후보 (code_sig → verified guide), promoted {len(promoted_links)}건",
        "SHE 패턴 미커버분은 신규 she:SituationalHazardPattern anchor 후보.",
        "",
        "| support | code_sig | top guides |",
        "|---|---|---|",
    ]
    for sig, l in promoted_links[:60]:
        top = ", ".join(g for g, _ in sorted(l["guides"].items(), key=lambda kv: kv[1], reverse=True)[:3])
        lines.append(f"| {l['support']} | `{sig}` | {top} |")

    promoted_aliases = sorted(
        ((sig, a) for sig, a in data["aliases"].items() if a["status"] == "promoted"),
        key=lambda kv: kv[1]["support"], reverse=True,
    )
    lines += ["", f"## alias 후보 (name → codes), promoted {len(promoted_aliases)}건",
              "canonical_vocab alias 편입 후보 (0-코드 hazard 해소).", "",
              "| support | name_norm | codes |", "|---|---|---|"]
    for sig, a in promoted_aliases[:60]:
        cs = ", ".join(c for c, _ in sorted(a["codes"].items(), key=lambda kv: kv[1], reverse=True)[:4])
        lines.append(f"| {a['support']} | {sig[:40]} | {cs} |")

    CURATION.write_text("\n".join(lines), encoding="utf-8")
    print(f"curation report: {CURATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
