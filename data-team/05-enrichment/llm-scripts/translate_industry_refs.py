#!/usr/bin/env python3
"""Part 2 — guide_llm_domains.json + guide_domain_profiles.json의 KO 산업명 참조를
industry_ko_to_en_map.json의 EN code로 결정론 변환.

대상 필드:
- guide_llm_domains.json: closed_vocabulary, classifications[*].primary_domain,
  classifications[*].domains, classifications[*].vote_count keys
- guide_domain_profiles.json: domain_family (앞부분 산업명 prefix만), 다른 산업 참조

intended_workplaces / intended_tasks / negative_boundaries 등 비-산업 KO 어휘는
Part 2.5로 별도 처리 (LLM batch 필요).
"""
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
MAP_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/industry_ko_to_en_map.json"
LLM_DOMAINS_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/guide_llm_domains.json"
PROFILES_PATH = ROOT / "serving-team/08-app/backend/app/data/guide_domain_profiles.json"


def load_map() -> dict[str, str]:
    payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return payload["mappings"]


def translate_value(v, m: dict[str, str], stats: dict, unmapped: dict[str, int]) -> object:
    """If v is a KO string in map, translate to EN. Otherwise leave."""
    if isinstance(v, str):
        en = m.get(v.strip())
        if en:
            stats["translated"] += 1
            return en
        # KO not in map — track but keep original
        if any(ord(c) > 127 for c in v):
            unmapped[v] = unmapped.get(v, 0) + 1
        return v
    elif isinstance(v, list):
        return [translate_value(x, m, stats, unmapped) for x in v]
    elif isinstance(v, dict):
        # translate both keys and values
        out = {}
        for k, val in v.items():
            new_k = translate_value(k, m, stats, unmapped) if isinstance(k, str) else k
            new_v = translate_value(val, m, stats, unmapped)
            out[new_k] = new_v
        return out
    return v


def fix_llm_domains(m: dict[str, str], dry: bool) -> dict:
    """Translate industry refs in guide_llm_domains.json."""
    data = json.loads(LLM_DOMAINS_PATH.read_text(encoding="utf-8"))
    stats = {"translated": 0, "guides_touched": 0}
    unmapped: dict[str, int] = {}

    # closed_vocabulary
    old_vocab = data.get("closed_vocabulary", [])
    new_vocab = [m.get(v, v) for v in old_vocab]
    # dedupe + maintain order
    seen, deduped = set(), []
    for v in new_vocab:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    data["closed_vocabulary"] = deduped

    # classifications
    classifications = data.get("classifications", {})
    for gid, info in classifications.items():
        before = json.dumps(info, ensure_ascii=False)
        # primary_domain
        info["primary_domain"] = translate_value(info.get("primary_domain", ""), m, stats, unmapped)
        # domains
        info["domains"] = translate_value(info.get("domains", []), m, stats, unmapped)
        # vote_count (dict)
        vc = info.get("vote_count", {})
        if isinstance(vc, dict):
            new_vc: dict[str, int] = {}
            for k, n in vc.items():
                en_k = m.get(k, k)
                new_vc[en_k] = new_vc.get(en_k, 0) + n  # merge duplicates after dedup
            info["vote_count"] = new_vc
        after = json.dumps(info, ensure_ascii=False)
        if before != after:
            stats["guides_touched"] += 1

    # audit
    data.setdefault("_part2_audit", []).append({
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "industry_translations": stats["translated"],
        "guides_touched": stats["guides_touched"],
        "vocab_before": len(old_vocab),
        "vocab_after": len(deduped),
        "unmapped_ko_terms_distinct": len(unmapped),
    })

    print(f"  guide_llm_domains.json:")
    print(f"    closed_vocabulary: {len(old_vocab)} -> {len(deduped)} (after dedup)")
    print(f"    industry translations: {stats['translated']}")
    print(f"    guides touched: {stats['guides_touched']} / {len(classifications)}")
    if unmapped:
        print(f"    unmapped KO terms: {len(unmapped)} distinct (sample: {list(unmapped.keys())[:5]})")

    if not dry:
        bak = LLM_DOMAINS_PATH.with_suffix(".json.bak.part2")
        shutil.copy(LLM_DOMAINS_PATH, bak)
        LLM_DOMAINS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"    saved (backup: {bak.name})")

    return {"stats": stats, "unmapped": unmapped}


def fix_profiles(m: dict[str, str], dry: bool) -> dict:
    """Translate industry refs in guide_domain_profiles.json (downstream artifact).
    profiles는 dict (key=guide_code, value=profile object).
    domain_family 끝의 KO는 산업명이 아니라 화학물질명인 경우가 많아 (구리/알루미늄)
    industry_ko_to_en_map.json에 매칭되는 것만 변환. 화학물질명은 Part 2.5 대상.
    """
    data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = data.get("profiles", {}) if isinstance(data, dict) else {}
    if not isinstance(profiles, dict):
        print(f"  unexpected profiles structure: {type(profiles).__name__}")
        return {"stats": {}, "unmapped": {}}

    stats = {
        "domain_family_industry_fixed": 0,
        "intended_workplaces_industry_fixed": 0,
        "negative_boundaries_industry_fixed": 0,
        "industry_alignment_industry_fixed": 0,
        "rows": 0,
    }
    unmapped: dict[str, int] = {}

    # exact-match only (산업명만, 화학물질명/일반어휘 건드리지 않음)
    for gid, p in profiles.items():
        stats["rows"] += 1
        # domain_family suffix exact-match only
        df = p.get("domain_family", "")
        if isinstance(df, str):
            # check if KO industry name appears as suffix after underscore
            for ko, en in m.items():
                if df.endswith("_" + ko):
                    p["domain_family"] = df[: -len(ko)] + en
                    stats["domain_family_industry_fixed"] += 1
                    break
        # intended_workplaces list — exact-match industry
        for field, stat_key in [
            ("intended_workplaces", "intended_workplaces_industry_fixed"),
            ("negative_boundaries", "negative_boundaries_industry_fixed"),
            ("industry_alignment", "industry_alignment_industry_fixed"),
        ]:
            lst = p.get(field, [])
            if isinstance(lst, list):
                new_lst = []
                for x in lst:
                    if isinstance(x, str) and x.strip() in m:
                        new_lst.append(m[x.strip()])
                        stats[stat_key] += 1
                    else:
                        if isinstance(x, str) and any(ord(c) > 127 for c in x):
                            unmapped[x] = unmapped.get(x, 0) + 1
                        new_lst.append(x)
                p[field] = new_lst

    print(f"  guide_domain_profiles.json (profiles dict):")
    print(f"    profiles: {stats['rows']}")
    print(f"    domain_family suffix-industry fixed: {stats['domain_family_industry_fixed']}")
    print(f"    intended_workplaces industry-fixed: {stats['intended_workplaces_industry_fixed']}")
    print(f"    negative_boundaries industry-fixed: {stats['negative_boundaries_industry_fixed']}")
    print(f"    industry_alignment industry-fixed: {stats['industry_alignment_industry_fixed']}")
    print(f"    unmapped KO terms (chemicals/general/etc) in lists: {len(unmapped)} distinct")
    print(f"    (Part 2.5 candidates, sample: {list(unmapped.keys())[:8]})")

    if not dry:
        bak = PROFILES_PATH.with_suffix(".json.bak.part2")
        shutil.copy(PROFILES_PATH, bak)
        PROFILES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"    saved (backup: {bak.name})")

    return {"stats": stats, "unmapped": unmapped}


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

    print("--- guide_llm_domains.json ---")
    r1 = fix_llm_domains(m, args.dry_run)
    print("\n--- guide_domain_profiles.json ---")
    r2 = fix_profiles(m, args.dry_run)

    if args.dry_run:
        print("\nDRY mode — no files written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
