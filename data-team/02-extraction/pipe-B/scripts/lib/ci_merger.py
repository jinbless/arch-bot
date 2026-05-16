"""CI parts merger — 분할 추출 결과를 단일 ci-{shortCode}.json으로 병합."""

import re
from datetime import datetime, timezone


# ID 패턴 (entity별)
_ID_PATTERNS = {
    "checklistItems": re.compile(r"^CI-[A-Z0-9]+-[0-9]+$"),
    "domainTerms": re.compile(r"^DT-[A-Z0-9]+-[0-9]+$"),
    "workProcesses": re.compile(r"^WP-[A-Z0-9]+-[0-9]+$"),
    "equipmentSpecs": re.compile(r"^ES-[A-Z0-9]+-[0-9]+$"),
    "documentRequirements": re.compile(r"^DR-[A-Z0-9]+-[0-9]+$"),
}

_ENTITY_KEYS = list(_ID_PATTERNS.keys())


def merge_ci_parts(
    part_outputs: list[dict],
    short_code: str,
    guide_code: str,
    domain: str,
    batch_id: str | None,
    extracted_by: str,
) -> tuple[dict, list[str]]:
    """N개 part output을 단일 ci-file dict로 병합.

    - 5개 entity 배열 part 순서로 concat → identifier 정렬
    - WP processOrder 글로벌 1..N 재정렬
    - 중복 ID 검출

    Returns:
        (merged_dict, validation_errors)
    """
    errors: list[str] = []

    merged: dict = {
        "metadata": {
            "guideCode": guide_code,
            "shortCode": short_code,
            "domain": domain,
            "extractedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "extractedBy": extracted_by,
            "batchId": batch_id,
        },
        "checklistItems": [],
        "domainTerms": [],
        "workProcesses": [],
        "equipmentSpecs": [],
        "documentRequirements": [],
    }

    seen_ids: dict[str, int] = {}  # id -> first part_index

    for part_idx, part in enumerate(part_outputs, start=1):
        if not isinstance(part, dict):
            errors.append(f"part{part_idx}: not a dict")
            continue

        for key in _ENTITY_KEYS:
            for item in part.get(key, []) or []:
                if not isinstance(item, dict):
                    continue
                eid = item.get("identifier", "")
                if eid in seen_ids:
                    errors.append(
                        f"DUPLICATE_ID {key}: '{eid}' part{part_idx} & part{seen_ids[eid]}"
                    )
                    continue
                seen_ids[eid] = part_idx

                merged[key].append(dict(item))  # 얕은 복사 (수정 시 원본 보존)

    # ID 정렬 (downstream 가독성)
    for key in _ENTITY_KEYS:
        merged[key].sort(key=lambda x: x.get("identifier", ""))

    # WP processOrder 글로벌 재정렬 (1, 2, 3, ...)
    for i, wp in enumerate(merged["workProcesses"], start=1):
        wp["processOrder"] = i

    # ID 형식 검증 (B2/B4 사전 점검)
    errors.extend(_validate_id_ranges(merged, short_code))

    return merged, errors


def _validate_id_ranges(merged: dict, short_code: str) -> list[str]:
    """ID가 가이드 shortCode를 포함하는지 + 형식 검증."""
    errors: list[str] = []
    for key, pattern in _ID_PATTERNS.items():
        for item in merged.get(key, []):
            eid = item.get("identifier", "")
            if not pattern.match(eid):
                errors.append(f"INVALID_ID_FORMAT {key}: '{eid}'")
            if f"-{short_code}-" not in eid:
                errors.append(f"WRONG_SHORTCODE {key}: '{eid}' lacks '-{short_code}-'")
    return errors
