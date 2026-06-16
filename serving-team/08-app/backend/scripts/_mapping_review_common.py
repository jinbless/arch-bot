"""HITL mapping-review 공통 모듈 — result_json → 검토 행(SR/Guide/Scene) 평탄화 + 컬럼 스펙.

export_mapping_review_xlsx.py(행 생성) 와 import_mapping_review_xlsx.py(컬럼키·verdict옵션 공유)가 함께 쓴다.
서빙 미반영(읽기 전용). mapping_key 규약을 한 곳에 고정해 export/import/online이 동일 키로 수렴하게 한다.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

# ── verdict / reason 어휘 (Excel 드롭다운 + import 검증 공유) ───────────────
VERDICT_OPTIONS = ["approve", "reject", "partial", "uncertain"]
# reason 분류 — evaluation-baseline reject 분류 재사용 (SR/Guide 공통)
REASON_CODES = [
    "domain_mismatch", "over_broad", "wrong_section", "right_hazard_wrong_guide",
    "she_misfire", "article_wrong", "scene_misread", "other",
]
MAX_SR_PER_PHOTO = 25  # findings.sr_ids는 수십개라 SHE-귀속 우선·cap

# ── 컬럼 스펙: (key, 헤더, 너비, unlocked?, dropdown) ──────────────────────
# unlocked=True 인 컬럼만 reviewer 편집 가능(나머지 provenance는 잠금).
_VERDICT_TAIL = [
    ("verdict", "판정", 12, True, "verdict"),
    ("corrected_value", "교정값(올바른 id, 콤마)", 24, True, None),
    ("reason_code", "사유", 20, True, "reason"),
    ("notes", "메모", 32, True, None),
]
SR_COLS = [
    ("mapping_key", "key", 10, False, None),
    ("analysis_id", "analysis_id", 14, False, None),
    ("photo", "사진", 22, False, None),
    ("scene_summary", "장면 요약", 40, False, None),
    ("gpt_observation", "GPT 관찰", 40, False, None),
    ("hazard", "위험(SHE)", 26, False, None),
    ("sr_id", "SR id", 16, False, None),
    ("sr_title", "SR 제목", 40, False, None),
    ("via_she", "매칭 SHE 패턴", 26, False, None),
    ("she_status", "SHE status", 11, False, None),
    ("she_score", "SHE score", 9, False, None),
    ("matched_features", "매칭 축", 16, False, None),
    ("she_sr_confidence", "SHE→SR conf", 10, False, None),
    ("penalty_exposure", "벌칙노출", 10, False, None),
] + _VERDICT_TAIL
GUIDE_COLS = [
    ("mapping_key", "key", 10, False, None),
    ("analysis_id", "analysis_id", 14, False, None),
    ("photo", "사진", 22, False, None),
    ("scene_summary", "장면 요약", 40, False, None),
    ("gpt_observation", "GPT 관찰", 40, False, None),
    ("guide_code", "Guide 코드", 14, False, None),
    ("guide_title", "Guide 제목", 40, False, None),
    ("mapping_type", "매핑유형", 16, False, None),
    ("source_path", "경로", 12, False, None),
    ("confidence", "confidence", 10, False, None),
    ("evidence_summary", "근거", 36, False, None),
    ("relevant_section", "관련 섹션", 30, False, None),
] + _VERDICT_TAIL
# Scene 시트: 사진별 1행 — scene-correctness + recall 추가(누락 SR/Guide).
SCENE_COLS = [
    ("mapping_key", "key", 10, False, None),
    ("analysis_id", "analysis_id", 14, False, None),
    ("photo", "사진", 22, False, None),
    ("scene_summary", "장면 요약", 44, False, None),
    ("finding_status", "finding_status", 14, False, None),
    ("penalty_exposure", "벌칙노출", 10, False, None),
    ("sr_count_full", "전체SR수", 9, False, None),
    ("guide_count", "Guide수", 8, False, None),
    ("scene_label_correct", "장면인식 정확?", 13, True, "yesno"),
    ("missing_sr_ids", "누락 SR(콤마)", 22, True, None),
    ("missing_guide_codes", "누락 Guide(콤마)", 22, True, None),
    ("recall_complete", "누락점검 완료?", 12, True, "yesno"),
    ("notes", "메모", 32, True, None),
]
YESNO_OPTIONS = ["yes", "no", "unsure"]

SHEETS = {"SR_mapping": ("SR", SR_COLS), "GUIDE_mapping": ("GUIDE", GUIDE_COLS), "SCENE": ("SCENE", SCENE_COLS)}


def mapping_key(analysis_id: str, kind: str, target_id: str) -> str:
    """안정 식별자 — export/import/online 공유. recall/scene은 target_id에 '_scene' 등 suffix."""
    return f"{analysis_id}:{kind}:{target_id}"


def _join_obs(rj: dict, n: int = 2) -> str:
    obs = rj.get("observations") or []
    return " / ".join((o.get("text") or "").strip() for o in obs[:n] if o.get("text"))


def _sr_titles(db: Session, sr_ids: list[str]) -> dict[str, str]:
    if not sr_ids:
        return {}
    from app.db.models import PgSafetyRequirement
    rows = db.query(PgSafetyRequirement.identifier, PgSafetyRequirement.title).filter(
        PgSafetyRequirement.identifier.in_(list(set(sr_ids)))
    ).all()
    return {r[0]: r[1] for r in rows}


def _she_sr_conf(db: Session, she_ids: list[str]) -> dict[tuple, float]:
    if not she_ids:
        return {}
    rows = db.execute(
        text("SELECT she_id, sr_id, confidence FROM she_sr_mapping WHERE she_id = ANY(:ids)"),
        {"ids": list(set(she_ids))},
    ).fetchall()
    return {(r[0], r[1]): float(r[2]) if r[2] is not None else None for r in rows}


def build_rows_for_record(db: Session, analysis_id: str, rj: dict, image_path: Optional[str],
                          max_sr: int = MAX_SR_PER_PHOTO) -> dict[str, list[dict]]:
    """한 분석 레코드 → {'SR_mapping':[...], 'GUIDE_mapping':[...], 'SCENE':[scene 1행]}.

    SR 후보: situation_matches[].applies_sr_ids(SHE-귀속, 집중·provenance 풍부) 우선·dedup·cap.
             situation_matches가 없으면 findings[0].sr_ids로 fallback(cap).
    Guide 후보: standard_procedures(서빙 표준개선절차) 각 1행.
    """
    scene_summary = (rj.get("summary") or "")[:300]
    gpt_obs = _join_obs(rj)
    penalty = rj.get("penalty_exposure_status") or ""
    photo = image_path or ""

    matches = rj.get("situation_matches") or []
    # sr_id → 최초 surfacing SHE provenance
    sr_prov: dict[str, dict] = {}
    she_ids: list[str] = []
    for m in matches:
        pid = m.get("pattern_id")
        if pid:
            she_ids.append(pid)
        for sid in m.get("applies_sr_ids") or []:
            if sid not in sr_prov:
                sr_prov[sid] = {
                    "via_she": f"{pid}: {m.get('title') or ''}".strip(),
                    "she_status": m.get("status") or "",
                    "she_score": round(float(m.get("score") or 0.0), 3),
                    "matched_features": ", ".join(m.get("matched_features") or []),
                    "she_id": pid,
                }
    sr_candidates = list(sr_prov.keys())
    fallback = False
    if not sr_candidates:
        findings = rj.get("findings") or []
        sr_candidates = (findings[0].get("sr_ids") if findings else []) or []
        fallback = True
    sr_candidates = sr_candidates[:max_sr]

    sr_titles = _sr_titles(db, sr_candidates)
    conf_map = _she_sr_conf(db, she_ids)

    sr_rows = []
    for sid in sr_candidates:
        prov = sr_prov.get(sid, {})
        conf = conf_map.get((prov.get("she_id"), sid))
        sr_rows.append({
            "mapping_key": mapping_key(analysis_id, "SR", sid),
            "analysis_id": analysis_id, "photo": photo,
            "scene_summary": scene_summary, "gpt_observation": gpt_obs,
            "hazard": prov.get("via_she", "(facet 검색)" if fallback else ""),
            "sr_id": sid, "sr_title": sr_titles.get(sid, ""),
            "via_she": prov.get("via_she", "(facet 검색)" if fallback else ""),
            "she_status": prov.get("she_status", ""), "she_score": prov.get("she_score", ""),
            "matched_features": prov.get("matched_features", ""),
            "she_sr_confidence": "" if conf is None else round(conf, 3),
            "penalty_exposure": penalty,
        })

    # Guide 후보: standard_procedures. hazard_guide_relations에서 relevant_section 보강(코드 매칭).
    sec_by_guide: dict[str, str] = {}
    for rel in rj.get("hazard_guide_relations") or []:
        for g in rel.get("guides") or []:
            secs = g.get("relevant_sections") or []
            if g.get("guide_code") and secs:
                sec_by_guide.setdefault(g["guide_code"], secs[0].get("section_title") or secs[0].get("excerpt") or "")
    guide_rows = []
    for sp in rj.get("standard_procedures") or []:
        code = sp.get("guide_code") or sp.get("procedure_id")
        if not code:
            continue
        guide_rows.append({
            "mapping_key": mapping_key(analysis_id, "GUIDE", code),
            "analysis_id": analysis_id, "photo": photo,
            "scene_summary": scene_summary, "gpt_observation": gpt_obs,
            "guide_code": code, "guide_title": (sp.get("title") or "").split(": ", 1)[-1],
            "mapping_type": sp.get("mapping_type") or "",
            "source_path": sp.get("source_path") or "",
            "confidence": round(float(sp.get("confidence") or 0.0), 3),
            "evidence_summary": (sp.get("evidence_summary") or "")[:200],
            "relevant_section": sec_by_guide.get(code, ""),
        })

    scene_row = {
        "mapping_key": mapping_key(analysis_id, "SCENE", "scene"),
        "analysis_id": analysis_id, "photo": photo, "scene_summary": scene_summary,
        "finding_status": rj.get("finding_status") or "",
        "penalty_exposure": penalty,
        "sr_count_full": len((rj.get("findings") or [{}])[0].get("sr_ids") or []) if rj.get("findings") else 0,
        "guide_count": len(rj.get("standard_procedures") or []),
        "scene_label_correct": "", "missing_sr_ids": "", "missing_guide_codes": "",
        "recall_complete": "", "notes": "",
    }
    return {"SR_mapping": sr_rows, "GUIDE_mapping": guide_rows, "SCENE": [scene_row]}
