#!/usr/bin/env python3
"""Part 2.5 — guide_domain_profiles.json + guide_llm_domains.json의
domain_family chemical suffix를 KO -> EN 변환.

CONTEXT_REQUIRED_DOMAIN_FAMILIES와의 회귀 우려 없음 (해당 set은 EN
하드코딩, 매칭 안 됨). 다른 KO 필드(intended_workplaces, negative_boundaries 등)는
backend가 의도적으로 KO 매칭 사용하므로 미건드림."""
from __future__ import annotations
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
MAP_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/chemical_ko_to_en_map.json"
PROFILES = ROOT / "serving-team/08-app/backend/app/data/guide_domain_profiles.json"
LLM_DOMAINS = ROOT / "data-team/05-enrichment/runtime-artifacts/guide_llm_domains.json"

PREFIX = "work_environment_measurement_analysis_"


def load_map() -> dict[str, str]:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))["mappings"]


def translate_df(df: str, m: dict[str, str]) -> tuple[str, bool]:
    """Translate KO suffix in domain_family. Return (new, changed)."""
    if not isinstance(df, str) or not df.startswith(PREFIX):
        return df, False
    suffix = df[len(PREFIX):]
    if suffix in m:
        return PREFIX + m[suffix], True
    return df, False


def fix_profiles(m: dict[str, str], dry: bool) -> int:
    data = json.loads(PROFILES.read_text(encoding="utf-8"))
    profiles = data.get("profiles", {})
    n = 0
    for gid, p in profiles.items():
        new_df, changed = translate_df(p.get("domain_family", ""), m)
        if changed:
            p["domain_family"] = new_df
            n += 1
    if not dry:
        shutil.copy(PROFILES, PROFILES.with_suffix(".json.bak.part25"))
        PROFILES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  guide_domain_profiles.json: {n} domain_family translated")
    return n


def fix_llm_domains(m: dict[str, str], dry: bool) -> int:
    """guide_llm_domains.json has domain_family in any field? Search and translate."""
    data = json.loads(LLM_DOMAINS.read_text(encoding="utf-8"))
    classifications = data.get("classifications", {})
    n = 0
    for gid, info in classifications.items():
        # domain_family field if present
        if "domain_family" in info:
            new_df, changed = translate_df(info["domain_family"], m)
            if changed:
                info["domain_family"] = new_df
                n += 1
    if not dry and n > 0:
        shutil.copy(LLM_DOMAINS, LLM_DOMAINS.with_suffix(".json.bak.part25"))
        LLM_DOMAINS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  guide_llm_domains.json: {n} domain_family translated (may be 0 if field absent)")
    return n


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True
    print(f"mode: {'DRY' if args.dry_run else 'APPLY'}")
    m = load_map()
    print(f"loaded chemical map: {len(m)} entries")
    fix_profiles(m, args.dry_run)
    fix_llm_domains(m, args.dry_run)
    if args.dry_run:
        print("\nDRY mode — no files written. Re-run with --apply.")


if __name__ == "__main__":
    raise SystemExit(main())
