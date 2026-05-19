#!/usr/bin/env python3
"""T4 #1 후속 (2026-05-19) — modify 19 SHE의 visual_triggers patch proposal 자동 생성.

입력: pending_review_she_REVIEWED.json (사용자 수동 검토 결과)
출력: pending_review_she_PATCH_PROPOSAL.json (PG UPDATE 전 dry-run 검토용)
실행 모드:
  --propose (default): proposal JSON 생성, PG 변경 없음
  --apply:             proposal JSON을 읽어서 PG she_catalog 실제 UPDATE

테마별 자동 처리:
  Theme A (PPE 과도, 8건):
    - visual_triggers 중 "안전화/안전모/PPE" 키워드 단서 제거
    - features.ppe_state 비우거나 generic ('UNKNOWN')
  Theme B (사진 불가, 3건):
    - 사용자가 지적한 특정 trigger를 keyword 매칭으로 식별 + 제거
  Theme C (좁은 조건, 4건):
    - features axis 일반화 (수동 매핑 dict)
  Theme D (비현실, 3건):
    - keyword 기반 trigger 제거 + warning 표시
  Theme E (도메인 불일치, 1건):
    - propose에 'manual_review_required' 마크만, 자동 patch 안 함

사용:
  python patch_she_visual_triggers.py --propose
  python patch_she_visual_triggers.py --apply --proposal PATCH_PROPOSAL.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def find_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return ancestor
    raise RuntimeError("Cannot locate repo root")


REPO_ROOT = find_root()
sys.path.insert(0, str(REPO_ROOT / "serving-team" / "08-app" / "backend"))

ARTIFACTS = REPO_ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
REVIEWED_PATH = ARTIFACTS / "pending_review_she_REVIEWED.json"
PROPOSAL_PATH = ARTIFACTS / "pending_review_she_PATCH_PROPOSAL.json"

# Keyword patterns for each theme's automatic trigger removal
PPE_KEYWORDS = [
    "안전화",
    "안전모",
    "안전 신발",
    "절단 방지 장갑",  # context-dependent — sometimes PPE 과도 케이스
]

PHOTO_IMPOSSIBLE_KEYWORDS = {
    "SHE-DISPLAYSETUP-c34c9b3805": ["찰과", "절상 흔적", "찰과·절상"],
    "SHE-BOXHANDLING-8a9f239d9a": ["발 위로", "낙하하는 순간"],
    "SHE-CONFINEDSPACE-b6fbefaf2c": ["사고 후", "구조 작업 중", "쓰러진"],
}

UNREALISTIC_KEYWORDS = {
    "SHE-BREADSLICER-d9856258a4": ["청소 도구", "어지럽게 놓인 청소"],
    "SHE-CHEMICALCLEANI-0d81697d9b": ["맨손으로 농축", "맨손으로 알칼리"],
    "SHE-CLEANINGWET-532fa157a6": ["아동", "어린이", "뛰는"],
}

# Theme C — feature generalization mapping
SCOPE_GENERALIZATION = {
    "SHE-COMPRESSIONDEV-e7351932ea": {
        "environmental": {"from": "CONFINED_SPACE", "to": "NARROW_OR_OPEN_SPACE", "note": "좁은 기계실 외 공간도 위험"},
    },
    "SHE-CONFINEDCOATIN-da85e838ef": {
        "hazardous_agent": {"from": "LEAD_PAINT_DUST", "to": "TOXIC_PAINT_DUST", "note": "납 외 도료/색상 일반화"},
    },
    "SHE-CONFINEDCOATIN-fc99086394": {
        "hazardous_agent": {"from": "ACRYLATE_VAPOR", "to": "TOXIC_CHEMICAL_VAPOR", "note": "아크릴레이트 외 화학물질 일반화"},
    },
    "SHE-INTERLOCKBYPAS-ac30fa32ae": {
        "_note": "환경 단서(공구·전선) 제거; 인터록 우회 자체로 위험",
    },
}

# Theme E — domain mismatch (manual only)
DOMAIN_MISMATCH_IDS = {"SHE-DENTALPROCEDUR-798a8c199d"}


def classify_theme(decision: str, note: str, she_id: str) -> str:
    if decision != "modify":
        return ""
    if she_id in DOMAIN_MISMATCH_IDS or "안 맞" in note or "안맞" in note:
        return "E"
    if she_id in SCOPE_GENERALIZATION:
        return "C"
    if she_id in PHOTO_IMPOSSIBLE_KEYWORDS:
        return "B"
    if she_id in UNREALISTIC_KEYWORDS:
        return "D"
    if any(k in note for k in ("안전화", "안전모", "PPE")):
        return "A"
    if any(k in note for k in ("없어도", "아니어도", "다른 종류", "다른 물질", "다른 색")):
        return "C"
    if any(k in note for k in ("사진", "찍을", "발견하기")) or "사고가 난 이후" in note:
        return "B"
    if any(k in note for k in ("없을것", "맨손", "즉시 녹", "아동")):
        return "D"
    return "Z"  # uncategorized


def build_patch_for_row(row: dict, note: str, theme: str) -> dict:
    """Return patch proposal for one SHE: triggers_remove, features_change, manual_required."""
    she_id = row["she_id"]
    triggers = row.get("visual_triggers", [])
    patch: dict = {
        "she_id": she_id,
        "theme": theme,
        "user_note": note,
        "before": {
            "visual_triggers": list(triggers),
            "features": dict(row.get("features", {})),
        },
        "actions": [],
        "after": {
            "visual_triggers": list(triggers),
            "features": dict(row.get("features", {})),
        },
        "manual_required": False,
        "warning": "",
    }

    if theme == "A":
        # PPE keyword 매칭 trigger 제거 + ppe_state 비우기
        kept = []
        removed = []
        for t in triggers:
            if any(k in t for k in PPE_KEYWORDS):
                removed.append(t)
            else:
                kept.append(t)
        if removed:
            patch["actions"].append({
                "kind": "remove_triggers",
                "items": removed,
                "reason": "PPE 부재 단서는 일반 환경에서 false positive 유발",
            })
            patch["after"]["visual_triggers"] = kept
        if patch["after"]["features"].get("ppe_state") and "ABSENT" in patch["after"]["features"]["ppe_state"]:
            patch["actions"].append({
                "kind": "set_feature",
                "field": "ppe_state",
                "from": patch["after"]["features"]["ppe_state"],
                "to": "UNKNOWN",
                "reason": "PPE absence를 hard signal에서 제거",
            })
            patch["after"]["features"]["ppe_state"] = "UNKNOWN"

    elif theme == "B":
        keys = PHOTO_IMPOSSIBLE_KEYWORDS.get(she_id, [])
        if keys:
            kept = []
            removed = []
            for t in triggers:
                if any(k in t for k in keys):
                    removed.append(t)
                else:
                    kept.append(t)
            if removed:
                patch["actions"].append({
                    "kind": "remove_triggers",
                    "items": removed,
                    "reason": "Vision LLM 시점에서 촬영 불가능한 단서",
                })
                patch["after"]["visual_triggers"] = kept
            if she_id == "SHE-BOXHANDLING-8a9f239d9a":
                patch["actions"].append({
                    "kind": "suggest_add_trigger",
                    "item": "옮기는 박스가 위태롭게 기울어져 보이는 상태",
                    "reason": "사용자 제안 — 낙하 순간 대신 사진 가능한 단서",
                })

    elif theme == "C":
        spec = SCOPE_GENERALIZATION.get(she_id, {})
        for field, change in spec.items():
            if field.startswith("_"):
                continue
            if isinstance(change, dict) and "from" in change:
                patch["actions"].append({
                    "kind": "generalize_feature",
                    "field": field,
                    "from": change["from"],
                    "to": change["to"],
                    "reason": change["note"],
                })
                # Apply (best-effort — actual feature axis name may differ)
                if field in patch["after"]["features"]:
                    patch["after"]["features"][field] = change["to"]
        if spec.get("_note"):
            patch["actions"].append({
                "kind": "remove_environment_constraint",
                "reason": spec["_note"],
            })

    elif theme == "D":
        keys = UNREALISTIC_KEYWORDS.get(she_id, [])
        if keys:
            kept = []
            removed = []
            for t in triggers:
                if any(k in t for k in keys):
                    removed.append(t)
                else:
                    kept.append(t)
            if removed:
                patch["actions"].append({
                    "kind": "remove_triggers",
                    "items": removed,
                    "reason": "비현실적 시나리오 단서",
                })
                patch["after"]["visual_triggers"] = kept
        patch["warning"] = "Theme D: 자동 patch 적용 전 사용자 한 번 더 확인 권장"

    elif theme == "E":
        patch["manual_required"] = True
        patch["warning"] = "Theme E: features 부정합 — 자동 patch 안 함. matcher refactor sprint에서 별도 처리 or reject 결정"

    elif theme == "Z":
        patch["manual_required"] = True
        patch["warning"] = "분류 실패 (uncategorized). 수동 검토 필요"

    return patch


def propose(reviewed: dict, original: dict) -> dict:
    """Generate patch proposals for all modify rows."""
    by_id = {r["she_id"]: r for r in original["rows"]}
    proposals = []
    theme_counts: dict = {}
    for r in reviewed["rows"]:
        if r["decision"] != "modify":
            continue
        note = r.get("suggested_changes", "") or r.get("reason", "")
        theme = classify_theme(r["decision"], note, r["she_id"])
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
        src = by_id.get(r["she_id"])
        if not src:
            continue
        proposals.append(build_patch_for_row(src, note, theme))

    return {
        "generated_at": str(date.today()),
        "source_reviewed": REVIEWED_PATH.name,
        "total_modify": len(proposals),
        "theme_counts": theme_counts,
        "apply_safety_note": "Theme E/Z는 manual_required=true; Theme D는 warning 있음 — 적용 전 검토",
        "patches": proposals,
    }


def apply_patches(proposal: dict) -> int:
    """Apply patches to PG she_catalog. Returns count of patched rows."""
    from app.db.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    n = 0
    try:
        for p in proposal["patches"]:
            if p.get("manual_required"):
                print(f"SKIP {p['she_id']} (manual_required)")
                continue
            she_id = p["she_id"]
            new_triggers = p["after"]["visual_triggers"]
            new_features = p["after"]["features"]
            # Update visual_triggers (jsonb) + features (jsonb)
            db.execute(
                text("""
                    UPDATE she_catalog
                    SET visual_triggers = CAST(:triggers AS jsonb),
                        features        = CAST(:features AS jsonb),
                        updated_at      = NOW()
                    WHERE she_id = :sid
                """),
                {
                    "triggers": json.dumps(new_triggers, ensure_ascii=False),
                    "features": json.dumps(new_features, ensure_ascii=False),
                    "sid": she_id,
                },
            )
            n += 1
            print(f"PATCH {she_id} (theme={p['theme']}, actions={len(p['actions'])})")
        db.commit()
    finally:
        db.close()
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--propose", action="store_true", help="generate proposal JSON (no DB change)")
    parser.add_argument("--apply", action="store_true", help="apply proposal to PG she_catalog")
    parser.add_argument("--proposal", type=str, default=str(PROPOSAL_PATH), help="proposal JSON path")
    parser.add_argument("--reviewed", type=str, default=str(REVIEWED_PATH))
    args = parser.parse_args()

    if not (args.propose or args.apply):
        args.propose = True

    if args.propose:
        reviewed = json.loads(Path(args.reviewed).read_text(encoding="utf-8"))
        original = json.loads((ARTIFACTS / "pending_review_she_for_manual_review.json").read_text(encoding="utf-8"))
        proposal = propose(reviewed, original)
        out = Path(args.proposal)
        out.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote: {out}")
        print(f"Total modify: {proposal['total_modify']}")
        print(f"Theme counts: {proposal['theme_counts']}")
        # Highlight manual_required
        mr = [p["she_id"] for p in proposal["patches"] if p.get("manual_required")]
        if mr:
            print(f"Manual required ({len(mr)}): {mr}")
        warned = [p["she_id"] for p in proposal["patches"] if p.get("warning") and not p.get("manual_required")]
        if warned:
            print(f"Warned (auto-applicable but check) ({len(warned)}): {warned}")
        return 0

    if args.apply:
        proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
        n = apply_patches(proposal)
        print(f"Applied {n} patches (manual_required skipped)")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
