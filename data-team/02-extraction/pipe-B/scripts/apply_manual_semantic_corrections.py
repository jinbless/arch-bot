#!/usr/bin/env python3
"""Apply conservative semantic corrections to manual domain-guard batches.

This script keeps all rows candidate-only. It does not delete SR candidates and
does not import to DB. It only demotes high-risk field-control SR links on
document/risk-method Guides to needs_review with serving-safe confidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PIPE_B_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPE_B_ROOT / "data"

CONFIDENCE_CAP = 0.64
CORRECTION_NOTE = (
    "Semantic audit 2026-05-09: document/risk-method profile field-control "
    "SR candidates demoted to needs_review for review-only use; semantic "
    "candidate rows preserved."
)

CORRECTIONS: dict[str, set[str]] = {
    "X-78-2018": {"SR-FIRE_EXPLOSION-001", "SR-FIRE_EXPLOSION-048"},
    "M-137-2023": {"SR-MACHINE-002", "SR-MACHINE-003", "SR-MACHINE-008"},
    "P-79-2011": {"SR-MACHINE-002"},
    "C-C-21-2026": {"SR-FIRE_EXPLOSION-001", "SR-FIRE_EXPLOSION-019"},
    "C-C-22-2026": {
        "SR-FIRE_EXPLOSION-001",
        "SR-FIRE_EXPLOSION-008",
        "SR-FIRE_EXPLOSION-010",
        "SR-FIRE_EXPLOSION-015",
        "SR-FIRE_EXPLOSION-019",
        "SR-ELECTRIC-024",
    },
    "C-C-30-2026": {
        "SR-FIRE_EXPLOSION-037",
        "SR-FIRE_EXPLOSION-038",
        "SR-FIRE_EXPLOSION-049",
        "SR-FIRE_EXPLOSION-050",
    },
    "C-C-67-2026": {
        "SR-ELECTRIC-024",
        "SR-FIRE_EXPLOSION-003",
        "SR-FIRE_EXPLOSION-019",
    },
    "C-C-75-2026": {"SR-FIRE_EXPLOSION-032"},
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_note(existing: Any) -> str:
    if not existing:
        return CORRECTION_NOTE
    text = str(existing)
    if CORRECTION_NOTE in text:
        return text
    return f"{text} {CORRECTION_NOTE}"


def main() -> int:
    changed_files = 0
    changed_candidates = 0
    correction_rows: list[dict[str, Any]] = []

    for path in sorted(DATA_DIR.glob("manual-enrichment-domain-guard-batch-*.json")):
        data = read_json(path)
        file_changed = False
        batch_id = (data.get("scope") or {}).get("batch_id") or path.stem.rsplit("-", 1)[-1]
        for guide in data.get("guides", []) or []:
            code = guide.get("guide_code")
            targets = CORRECTIONS.get(code)
            if not targets:
                continue
            guide_changed = False
            for candidate in guide.get("sr_link_candidates", []) or []:
                sr_id = candidate.get("sr_id")
                if sr_id not in targets:
                    continue
                before = {
                    "confidence": candidate.get("confidence"),
                    "review_status": candidate.get("review_status"),
                }
                candidate["review_status"] = "needs_review"
                candidate["confidence"] = min(float(candidate.get("confidence") or 0), CONFIDENCE_CAP)
                after = {
                    "confidence": candidate.get("confidence"),
                    "review_status": candidate.get("review_status"),
                }
                if before != after:
                    changed_candidates += 1
                    guide_changed = True
                    correction_rows.append(
                        {
                            "batch_id": batch_id,
                            "guide_code": code,
                            "title": guide.get("title"),
                            "sr_id": sr_id,
                            "before": before,
                            "after": after,
                            "reason": "document/risk-method Guide field-control SR; keep review-only before import",
                        }
                    )
            if guide_changed:
                guide["notes"] = append_note(guide.get("notes"))
                file_changed = True
        if file_changed:
            write_json(path, data)
            changed_files += 1

    report = {
        "generated_at": "2026-05-09",
        "method": "codex_manual_semantic_correction",
        "external_api_used": False,
        "db_imported": False,
        "asserted_mapping_updates": 0,
        "confidence_cap": CONFIDENCE_CAP,
        "changed_files": changed_files,
        "changed_candidates": changed_candidates,
        "corrections": correction_rows,
    }
    json_path = DATA_DIR / "manual-enrichment-domain-guard-semantic-corrections.json"
    write_json(json_path, report)

    rows = "\n".join(
        f"| {row['guide_code']} | {row['sr_id']} | {row['before']['confidence']} / {row['before']['review_status']} | "
        f"{row['after']['confidence']} / {row['after']['review_status']} |"
        for row in correction_rows
    )
    md_path = DATA_DIR / "manual-enrichment-domain-guard-semantic-corrections.md"
    md_path.write_text(
        f"""# Manual Domain Guard Semantic Corrections

Generated: 2026-05-09

These corrections demote high-risk field-control SR candidates on document/risk-method Guides. They preserve all candidate rows, do not call external APIs, do not import to PostgreSQL, and do not promote asserted mappings.

| Item | Count |
|---|---:|
| Changed files | {changed_files} |
| Changed SR candidates | {changed_candidates} |
| Asserted mapping updates | 0 |

## Corrections

| Guide | SR | Before | After |
|---|---|---|---|
{rows}
""",
        encoding="utf-8",
    )

    print(json_path.relative_to(PIPE_B_ROOT))
    print(md_path.relative_to(PIPE_B_ROOT))
    print(json.dumps({"changed_files": changed_files, "changed_candidates": changed_candidates}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
