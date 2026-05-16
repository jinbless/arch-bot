"""Utilities for temporary, rollback-only SHE candidate evaluation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text


def parse_priority_filter(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    values = {item.strip() for item in raw.split(",") if item.strip()}
    if not values or "all" in values:
        return None
    return values


def load_shadow_candidates(
    path: Path,
    *,
    priorities: set[str] | None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if priorities is not None and row.get("review_priority") not in priorities:
            continue
        rows.append(row)
        if limit and len(rows) >= limit:
            break
    return rows


def install_shadow_she_candidates(
    db: Any,
    candidate_path: Path,
    *,
    priorities: str | None = "high",
    limit: int = 0,
    use_runtime_match_features: bool = False,
    require_visual_trigger: bool = False,
    min_visual_score: float = 0.2,
) -> dict[str, Any]:
    """Insert SHE candidates into the current DB session only.

    The caller must rollback/close the session after the replay. Inserted rows
    are marked approved_auto only inside the transaction so the existing matcher
    can see them without changing product data.
    """
    priority_filter = parse_priority_filter(priorities)
    candidates = load_shadow_candidates(candidate_path, priorities=priority_filter, limit=limit)
    inserted = 0
    conflicts = 0
    mapping_rows = 0
    no_sr = 0
    priorities_seen: dict[str, int] = {}

    for candidate in candidates:
        features = (
            candidate.get("runtime_match_features")
            if use_runtime_match_features and candidate.get("runtime_match_features")
            else candidate.get("features")
        ) or {}
        source_sr_ids = [str(sr_id) for sr_id in (candidate.get("source_sr_ids") or []) if sr_id]
        if not source_sr_ids:
            no_sr += 1
        priorities_seen[candidate.get("review_priority", "unknown")] = (
            priorities_seen.get(candidate.get("review_priority", "unknown"), 0) + 1
        )
        notes = dict(candidate.get("notes") or {})
        if require_visual_trigger:
            notes["runtime_match_policy"] = {
                "require_visual_trigger": True,
                "min_visual_score": min_visual_score,
                "policy_reason": "shadow broad runtime features require candidate visual trigger support",
            }
        notes["shadow_evaluation"] = {
            "source_status": candidate.get("status"),
            "source_review_status": candidate.get("review_status"),
            "source_review_priority": candidate.get("review_priority"),
            "source_sr_evidence_strength": candidate.get("source_sr_evidence_strength"),
            "promotion_blockers": candidate.get("promotion_blockers") or [],
            "use_runtime_match_features": use_runtime_match_features,
            "require_visual_trigger": require_visual_trigger,
            "min_visual_score": min_visual_score if require_visual_trigger else None,
            "inserted_features": features,
            "policy": "temporary_session_insert_rollback_required",
        }

        inserted_row = db.execute(
            text(
                """
                INSERT INTO she_catalog (
                    she_id, name, name_pattern, features, visual_triggers, rationale,
                    status, broadness_score, source_model, source_prompt_hash,
                    source_sr_ids, notes
                )
                VALUES (
                    :she_id, :name, :name_pattern,
                    CAST(:features AS jsonb), CAST(:visual_triggers AS jsonb), :rationale,
                    'approved_auto', :broadness_score, :source_model, :source_prompt_hash,
                    CAST(:source_sr_ids AS jsonb), :notes
                )
                ON CONFLICT (she_id) DO NOTHING
                RETURNING she_id
                """
            ),
            {
                "she_id": candidate["she_id"],
                "name": candidate.get("name") or candidate["she_id"],
                "name_pattern": candidate.get("name_pattern"),
                "features": json.dumps(features, ensure_ascii=False),
                "visual_triggers": json.dumps(candidate.get("visual_triggers") or [], ensure_ascii=False),
                "rationale": candidate.get("rationale") or "Temporary shadow SHE candidate.",
                "broadness_score": candidate.get("broadness_score") or 0.5,
                "source_model": f"{candidate.get('source_model') or 'unknown'}/shadow",
                "source_prompt_hash": candidate.get("source_prompt_hash") or "0" * 32,
                "source_sr_ids": json.dumps(source_sr_ids, ensure_ascii=False),
                "notes": json.dumps(notes, ensure_ascii=False),
            },
        ).scalar()
        if not inserted_row:
            conflicts += 1
            continue
        inserted += 1

        for sr_id in source_sr_ids:
            db.execute(
                text(
                    """
                    INSERT INTO she_sr_mapping (she_id, sr_id, confidence, source)
                    VALUES (:she_id, :sr_id, :confidence, 'shadow')
                    ON CONFLICT (she_id, sr_id) DO NOTHING
                    """
                ),
                {
                    "she_id": candidate["she_id"],
                    "sr_id": sr_id,
                    "confidence": 0.80 if candidate.get("source_sr_evidence_strength") == "medium" else 0.65,
                },
            )
            mapping_rows += 1

    return {
        "candidate_path": str(candidate_path),
        "priority_filter": "all" if priority_filter is None else sorted(priority_filter),
        "candidate_rows_loaded": len(candidates),
        "inserted": inserted,
        "conflicts": conflicts,
        "no_source_sr": no_sr,
        "she_sr_mapping_rows": mapping_rows,
        "review_priority_counts": priorities_seen,
        "use_runtime_match_features": use_runtime_match_features,
        "require_visual_trigger": require_visual_trigger,
        "min_visual_score": min_visual_score if require_visual_trigger else None,
        "temporary_insert_policy": "session_rollback_required",
    }
