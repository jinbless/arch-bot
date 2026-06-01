#!/usr/bin/env python3
"""COV-3 — guide → fine work_context 태깅 (커버리지 확장).

배경: 서빙 graded matching이 발동하려면 guide가 fine work_context 코드로 태깅돼야 함.
현 GF는 fine wc 51종(산업 위주)뿐 → 제빵/주방 등 미태깅. guide 본문(title/domain/
sub_category)+재사용 도메인 힌트(guide_llm_domains)를 LLM이 읽어 catalog fine wc 코드
선택(enum 제약=allowlist). 서빙 _fine_wc_match_guides가 GF를 직접 조회하므로 즉시 반영.

출력: runtime-artifacts/guide_wc_fine_proposals.jsonl. --apply 시 GF에 INSERT
(entity_type='GUIDE', axis='work_context', method='llm_enriched_wc', review_status='candidate').

ENV: ANTHROPIC_API_KEY 또는 OPENAI_API_KEY (없으면 --mock 자동).
사용:
  python tag_guides_wc_fine.py --dry-run --limit 5
  python tag_guides_wc_fine.py --run --mock --limit 20
  python tag_guides_wc_fine.py --run --limit 30          # 파일럿(키 필요)
  python tag_guides_wc_fine.py --run --apply --min-conf 0.7   # 전체 + GF 적재
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
sys.path.insert(0, str(ROOT / "serving-team" / "08-app" / "backend"))
import canonical_vocab as cv  # noqa: E402
from llm_client import LLMClient  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CATALOG = ROOT / "serving-team" / "08-app" / "backend" / "app" / "data" / "risk_feature_catalog.json"
DOMAINS = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts" / "guide_llm_domains.json"
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
AXIS = "work_context"  # main에서 --axis로 재설정
AXIS_KO = {"work_context": "작업맥락", "accident_type": "사고유형", "hazardous_agent": "유해인자"}
AXIS_SHORT = {"work_context": "wc", "accident_type": "acc", "hazardous_agent": "agt"}


def build_system(axis_ko: str) -> str:
    return ("당신은 KOSHA 산업안전 가이드 분류 전문가입니다.\n"
            f"주어진 KOSHA Guide가 다루는 '구체적(fine) {axis_ko}'을 catalog 어휘에서 선택합니다.\n"
            "원칙:\n"
            f"1. Guide 제목/도메인에 비추어 **명백히 해당하는** fine {axis_ko}만 선택(과대 태깅 금지).\n"
            "2. 반드시 제공된 vocabulary 코드만 사용. 해당 없으면 빈 목록.\n"
            "3. 1~5개 이내. 가장 핵심 위주.\n"
            "4. confidence는 전체 선택의 확신도.")


def load_fine_vocab() -> list[tuple[str, str]]:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    canon = cv.canonical_set(AXIS) | cv.meta_set(AXIS)
    out = []
    for code, v in cat["axes"].get(AXIS, {}).get("codes", {}).items():
        if code in canon:
            continue
        lab = v.get("label", "") if isinstance(v, dict) else ""
        out.append((code, lab))
    return sorted(out)


def build_tool(fine_codes: list[str], axis_ko: str) -> dict:
    return {
        "name": "tag_fine_codes",
        "description": f"Guide가 다루는 fine {axis_ko} 코드 선택(vocabulary 내, 0~5개).",
        "input_schema": {
            "type": "object",
            "properties": {
                "fine_codes": {"type": "array", "items": {"type": "string", "enum": fine_codes},
                               "description": f"해당 fine {axis_ko} 코드들(없으면 빈 배열)"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reason": {"type": "string", "description": "1문장 한국어"},
            },
            "required": ["fine_codes", "confidence", "reason"],
        },
    }


def mock_fn(title: str, vocab: list[tuple[str, str]]):
    def fn(system, user):
        hits = [c for c, lab in vocab if lab and len(lab) >= 2 and lab[:2] in (title or "")][:3]
        return {"fine_codes": hits, "confidence": 0.5 if hits else 0.0, "reason": "mock:title-kw"}
    return fn


def fetch_guides(limit: int):
    from app.db.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        q = "SELECT guide_code, title, domain, sub_category FROM kosha_guides ORDER BY guide_code"
        if limit:
            q += f" LIMIT {int(limit)}"
        return [dict(guide_code=r[0], title=r[1], domain=r[2], sub_category=r[3]) for r in db.execute(text(q)).fetchall()]
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--tier", default="cheap")
    ap.add_argument("--min-conf", type=float, default=0.7)
    ap.add_argument("--axis", default="work_context", choices=["work_context", "accident_type", "hazardous_agent"])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    global AXIS
    AXIS = args.axis
    axis_ko = AXIS_KO[AXIS]
    out_path = ART / f"guide_{AXIS_SHORT[AXIS]}_fine_proposals.jsonl"
    method = f"llm_enriched_{AXIS_SHORT[AXIS]}"
    system = build_system(axis_ko)

    vocab = load_fine_vocab()
    fine_codes = [c for c, _ in vocab]
    domains = json.loads(DOMAINS.read_text(encoding="utf-8")).get("classifications", {}) if DOMAINS.exists() else {}
    guides = fetch_guides(args.limit)
    print(f"[{AXIS}] guides: {len(guides)} | fine vocab: {len(fine_codes)} | domain 힌트: {len(domains)}")

    if args.dry_run:
        for g in guides[:5]:
            dh = domains.get(g["guide_code"], {})
            print(f"  {g['guide_code']:14s} | {(g['title'] or '')[:34]:34s} | dom={dh.get('primary_domain','?')}")
        print("fine vocab 샘플:", [f"{c}({l})" for c, l in vocab[:10]])
        return 0

    client = LLMClient(provider=args.provider, tier=args.tier, mock=args.mock)
    tool = build_tool(fine_codes, axis_ko)
    print(f"LLM: provider={client.provider} model={client.model} mock={client.mock}")
    vocab_block = "\n".join(f"  {c} : {l}" for c, l in vocab)

    proposals = []
    for i, g in enumerate(guides, 1):
        dh = domains.get(g["guide_code"], {})
        user = (f"Guide: {g['guide_code']}\n제목: {g['title']}\n도메인: {g.get('domain') or ''} / "
                f"{g.get('sub_category') or ''}\nLLM 추정 도메인: {dh.get('primary_domain','?')} "
                f"{dh.get('domains','')}\n\nfine {axis_ko} vocabulary(코드 : 한글):\n{vocab_block}\n\n"
                f"이 Guide가 명백히 다루는 fine {axis_ko} 코드는?(없으면 빈 배열)")
        out = client.structured(system, user, tool, mock_fn=mock_fn(g["title"], vocab))
        codes = [c for c in dict.fromkeys(out.get("fine_codes") or []) if c in set(fine_codes)]  # 가이드 내 중복 제거
        conf = out.get("confidence") or 0.0
        for c in codes:
            a2, c2 = cv.to_canonical(AXIS, c)
            proposals.append({"guide_code": g["guide_code"], "feature_code": c, "canonical_code": c2,
                              "canonical_axis": a2, "confidence": conf, "reason": out.get("reason", "")})
        if i % 25 == 0:
            print(f"  ...{i}/{len(guides)}")

    out_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in proposals) + "\n", encoding="utf-8")
    # conf 필터 + (guide,feature) 전역 dedup — GF UNIQUE(entity_id,axis,feature_code,method) 위반 방지.
    kept, _seen = [], set()
    for p in proposals:
        k = (p["guide_code"], p["feature_code"])
        if p["confidence"] >= args.min_conf and k not in _seen:
            _seen.add(k)
            kept.append(p)
    fine_distinct = sorted({p["feature_code"] for p in kept})
    guides_tagged = len({p["guide_code"] for p in kept})
    print(f"proposal {len(proposals)} (guide-fine 쌍) → {out_path.relative_to(ROOT)}")
    print(f"  conf>={args.min_conf}: {len(kept)} 쌍 / guide {guides_tagged}개 / fine 코드 {len(fine_distinct)}종")
    print(f"  fine 코드 샘플: {fine_distinct[:12]}")

    if args.apply and kept:
        from app.db.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # 멱등: 이번에 처리한 guide의 기존 같은-method 행 제거 후 재삽입(중복 방지).
            processed = sorted({g["guide_code"] for g in guides})
            db.execute(text("DELETE FROM guide_entity_feature_candidates "
                            "WHERE method=:m AND axis=:ax AND guide_code = ANY(:gids)"),
                       {"m": method, "ax": AXIS, "gids": processed})
            nid = (db.execute(text("SELECT COALESCE(MAX(candidate_id),0) FROM guide_entity_feature_candidates")).scalar() or 0)
            ins = text("""INSERT INTO guide_entity_feature_candidates
                (candidate_id, entity_type, entity_id, guide_code, axis, feature_code, canonical_code,
                 canonical_axis, confidence, evidence, method, review_status, non_llm_evidence_count)
                VALUES (:cid,'GUIDE',:gid,:gc,:axis,:fc,:cc,:ca,:conf,:ev,:m,'candidate',0)""")
            for p in kept:
                nid += 1
                db.execute(ins, {"cid": nid, "gid": p["guide_code"], "gc": p["guide_code"], "axis": AXIS,
                                 "fc": p["feature_code"], "cc": p["canonical_code"], "ca": p["canonical_axis"],
                                 "conf": round(float(p["confidence"]), 4),
                                 "ev": f"LLM {AXIS} tag: {p['reason'][:180]}", "m": method})
            db.commit()
            print(f"  [APPLY] GF insert {len(kept)}행 (method={method}, candidate). 서빙 즉시 반영 — eval 재실행 권장.")
        finally:
            db.close()
    elif args.apply:
        print("  [APPLY] kept 0 — 무변경")
    return 0


if __name__ == "__main__":
    sys.exit(main())
