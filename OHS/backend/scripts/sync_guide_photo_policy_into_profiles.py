#!/usr/bin/env python3
"""Synchronize Guide photo policy rows into the domain profile artifact.

Runtime policy lookup reads ``guide_photo_matchability.v1.json`` before falling
back to ``guide_domain_profiles.json``.  This script makes the profile artifact
and summary counts mirror the effective row-level runtime policy without
changing any SHE/SR/status/penalty logic.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "app" / "data"
PROFILE_PATH = DATA_DIR / "guide_domain_profiles.json"
PHOTO_PATH = DATA_DIR / "guide_photo_matchability.v1.json"

PHOTO_POLICY_FIELDS = (
    "photo_matchability",
    "top_procedure_policy",
    "followup_policy",
    "classification_reason",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_photo_profiles(photo_profiles: dict[str, dict[str, Any]]) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    counts = Counter(str(row.get("photo_matchability") or "unknown") for row in photo_profiles.values())
    by_role: dict[str, Counter[str]] = defaultdict(Counter)
    for row in photo_profiles.values():
        role = str(row.get("procedure_role") or "unknown")
        matchability = str(row.get("photo_matchability") or "unknown")
        by_role[role][matchability] += 1
        by_role[role]["total"] += 1
    return dict(sorted(counts.items())), {
        role: dict(sorted(role_counts.items()))
        for role, role_counts in sorted(by_role.items())
    }


def main() -> None:
    profile_data = read_json(PROFILE_PATH)
    photo_data = read_json(PHOTO_PATH)
    profiles = profile_data.get("profiles") or {}
    photo_profiles = photo_data.get("profiles") or {}

    missing_from_profiles = sorted(set(photo_profiles) - set(profiles))
    changed_rows = 0
    for guide_code, photo_row in photo_profiles.items():
        profile = profiles.get(guide_code)
        if not isinstance(profile, dict):
            continue
        changed = False
        for field in PHOTO_POLICY_FIELDS:
            if field in photo_row and profile.get(field) != photo_row.get(field):
                profile[field] = photo_row.get(field)
                changed = True
        if changed:
            changed_rows += 1

    counts, by_role = count_photo_profiles(photo_profiles)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    profile_data["photo_matchability_counts"] = counts
    profile_data["photo_matchability_policy"] = {
        **(profile_data.get("photo_matchability_policy") or {}),
        "synced_at": generated_at,
        "effective_source": str(PHOTO_PATH.relative_to(BACKEND_DIR.parent.parent)),
        "sync_method": "sync_guide_photo_policy_into_profiles.py",
    }
    photo_data["classification_counts"] = counts
    photo_data["classification_by_role"] = by_role
    photo_data["summary_synced_at"] = generated_at

    write_json(PROFILE_PATH, profile_data)
    write_json(PHOTO_PATH, photo_data)
    print(json.dumps({
        "profile_path": str(PROFILE_PATH),
        "photo_path": str(PHOTO_PATH),
        "changed_profile_rows": changed_rows,
        "missing_from_profiles": missing_from_profiles,
        "photo_matchability_counts": counts,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
