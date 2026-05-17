#!/usr/bin/env python3
"""C (Part 2 후속) — guide_domain_incompatibilities.json의 KO 산업명을
industry_ko_to_en_map.json 매핑으로 EN UPPER_SNAKE_CASE로 결정론 변환.

배경: Part 2 (translate_industry_refs.py)는 guide_llm_domains.json + profiles만
처리했고, incompat KB는 남겨둠. F.3.0에서 KB가 KO인데 reject log는 EN이라
axiom_missing 비율이 81%로 잘못 측정되는 노이즈 발견 → cleanup 필요.

처리 대상:
- 각 entry의 domain_a, domain_b 필드 (EN 변환)
- reason 텍스트는 한국어 narrative 그대로 보존 (사람 읽기용)
- error 등 메타 필드 보존

KO인데 매핑에 없는 경우: 원본 그대로 두고 unmapped 카운트만 audit.
변환 후 EN으로 통일된 pair set이 F.3.0/F.3.2 mining 정확도를 normalize.

사용:
  python translate_incompat_industries.py --dry-run
  python translate_incompat_industries.py --apply
"""
from __future__ import annotations
import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


ROOT = find_root()
MAP_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/industry_ko_to_en_map.json"
INCOMPAT_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"


def load_map() -> dict[str, str]:
    payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return dict(payload.get("mappings") or {})


def is_ko(s: str) -> bool:
    return any(ord(c) > 127 for c in s)


def is_en_enum(s: str) -> bool:
    return bool(s) and s.replace("_", "").isascii() and s.isupper()


def translate(name: str, m: dict[str, str], unmapped: Counter) -> tuple[str, str]:
    """Return (translated_name, status) where status ∈ {translated, already_en, unmapped_ko, empty}."""
    if not name:
        return ("", "empty")
    stripped = name.strip()
    if stripped in m:
        return (m[stripped], "translated")
    if is_en_enum(stripped):
        return (stripped, "already_en")
    if is_ko(stripped):
        unmapped[stripped] += 1
        return (stripped, "unmapped_ko")
    return (stripped, "already_en")  # ASCII fallback


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True

    print(f"mode: {'DRY' if args.dry_run else 'APPLY'}")
    m = load_map()
    print(f"loaded mapping: {len(m)} KO -> {len(set(m.values()))} EN\n")

    data = json.loads(INCOMPAT_PATH.read_text(encoding="utf-8"))
    entries = data.get("incompatibilities") or []
    print(f"loaded incompatibilities: {len(entries)} entries\n")

    unmapped: Counter = Counter()
    status_counter: Counter = Counter()
    entries_touched = 0

    for e in entries:
        a_orig = str(e.get("domain_a") or "")
        b_orig = str(e.get("domain_b") or "")
        a_new, a_st = translate(a_orig, m, unmapped)
        b_new, b_st = translate(b_orig, m, unmapped)
        status_counter[a_st] += 1
        status_counter[b_st] += 1
        if a_new != a_orig or b_new != b_orig:
            e["domain_a"] = a_new
            e["domain_b"] = b_new
            entries_touched += 1

    print("Translation status (per side, total = 2 × entries):")
    for st, n in sorted(status_counter.items(), key=lambda x: -x[1]):
        print(f"  {st:18s} {n:5d}")
    print(f"\nEntries touched: {entries_touched} / {len(entries)}")
    if unmapped:
        print(f"Unmapped KO terms (distinct): {len(unmapped)}")
        for term, cnt in unmapped.most_common(10):
            print(f"  freq={cnt:3d}  {term}")

    # audit
    data.setdefault("_partC_audit", []).append({
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "script": "translate_incompat_industries.py",
        "entries_total": len(entries),
        "entries_touched": entries_touched,
        "status_counter": dict(status_counter),
        "unmapped_ko_distinct": len(unmapped),
        "unmapped_ko_sample": dict(unmapped.most_common(20)),
    })

    if args.dry_run:
        print("\nDRY mode — no file written. Re-run with --apply.")
        return 0

    bak = INCOMPAT_PATH.with_suffix(".json.bak.partC")
    shutil.copy(INCOMPAT_PATH, bak)
    INCOMPAT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nsaved {INCOMPAT_PATH} (backup: {bak.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
