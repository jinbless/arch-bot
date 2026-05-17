#!/usr/bin/env python3
"""Part 3 — synthetic_observations_v*.jsonl의 KO enum 값을 EN code로 변환.

전제: synthetic_ko_codes_for_review.json + (사람 검토로 완성된) ko_to_en mapping JSON
이 필요. 매핑 만드는 흐름:

1. mine_synthetic_ko_codes.py 실행 → synthetic_ko_codes_for_review.json
   (auto_en이 채워진 항목 + need_llm 항목 구분)
2. need_llm 항목에 대해 LLM batch 또는 사람이 manual fill
3. 최종 ko_to_en 통합 mapping 작성 → synthetic_ko_to_en_final.json
4. 본 스크립트 --apply로 모든 v*.jsonl 변환
5. replay_synthetic_observations.py --save-baseline 로 새 baseline 저장

본 스크립트는 transform만 수행 (매핑은 외부 source).
"""
from __future__ import annotations
import argparse
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


ROOT = find_root()
SYNTH_DIR = ROOT / "data-team/05-enrichment/eval-data"
MAPPING_PATH = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_ko_to_en_final.json"

# synthetic uses plural axis keys
AXIS_KEYS = ("accident_types", "hazardous_agents", "work_contexts", "ppe_states", "environmental")


def load_mapping() -> dict:
    """Expected structure:
    {
      "version": "1.0",
      "mappings": {
        "accident_types": {"감전": "ELECTRIC_SHOCK", "절단": "AMPUTATION", ...},
        "hazardous_agents": {...},
        ...
      },
      "drop_list": ["없음", "기타", ...]  # KO values to DROP (not map)
    }
    """
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(
            f"{MAPPING_PATH} missing.\n"
            f"먼저: 1) mine_synthetic_ko_codes.py 실행\n"
            f"      2) LLM/사람 검토로 mapping 완성\n"
            f"      3) {MAPPING_PATH.name}으로 저장"
        )
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def transform_codes(codes: list, axis_mapping: dict[str, str], drop_set: set[str],
                     reloc_mapping: dict[str, dict]) -> tuple[list, dict, dict[str, list[str]]]:
    """Returns (new_codes_for_this_axis, stats, codes_to_relocate_other_axis).
    codes_to_relocate_other_axis = {target_axis_synth: [target_codes...]}
    """
    new_codes = []
    relocated: dict[str, list[str]] = {}
    stats = {"translated": 0, "dropped": 0, "untouched_en": 0, "unmapped_ko": 0, "relocated": 0}
    AXIS_SYNTH_INVERSE = {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }
    for c in codes:
        if not isinstance(c, str):
            new_codes.append(c)
            continue
        if any(ord(ch) > 127 for ch in c):
            # KO
            if c in drop_set:
                stats["dropped"] += 1
                continue
            if c in reloc_mapping:
                tgt = reloc_mapping[c]
                tgt_axis_singular = tgt.get("target_axis", "")
                tgt_axis_synth = AXIS_SYNTH_INVERSE.get(tgt_axis_singular, tgt_axis_singular)
                tgt_code = tgt.get("target_code", "")
                if tgt_axis_synth and tgt_code:
                    relocated.setdefault(tgt_axis_synth, []).append(tgt_code)
                    stats["relocated"] += 1
                continue  # don't keep in current axis
            if c in axis_mapping:
                new_codes.append(axis_mapping[c])
                stats["translated"] += 1
            else:
                stats["unmapped_ko"] += 1
                new_codes.append(c)  # keep as-is, flag in audit
        else:
            new_codes.append(c)
            stats["untouched_en"] += 1
    return new_codes, stats, relocated


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if not args.apply:
        args.dry_run = True

    mapping_data = load_mapping()
    mappings = mapping_data.get("mappings", {})
    # drop_list 호환: flat list 또는 per-axis dict 모두 지원
    raw_drop = mapping_data.get("drop_list", [])
    if isinstance(raw_drop, list):
        drop_per_axis: dict[str, set[str]] = {ax: set(raw_drop) for ax in AXIS_KEYS}
    else:
        drop_per_axis = {ax: set(raw_drop.get(ax, [])) for ax in AXIS_KEYS}
    reloc_per_axis: dict[str, dict] = mapping_data.get("reloc", {})  # axis_synth -> ko -> {target_axis, target_code}
    print(f"loaded mapping: {sum(len(v) for v in mappings.values())} total entries across {len(mappings)} axes")
    print(f"drop_list: {sum(len(v) for v in drop_per_axis.values())} (per-axis)")
    print(f"reloc: {sum(len(v) for v in reloc_per_axis.values())} (per-axis)")

    global_stats: dict[str, int] = defaultdict(int)
    file_summaries = []

    for fp in sorted(SYNTH_DIR.glob("synthetic_observations_v*.jsonl")):
        out_lines = []
        file_stat = defaultdict(int)
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                out_lines.append(line)
                continue
            exp = r.get("expected_features", {})
            # First pass: transform each axis, collect reloc targets
            all_reloc: dict[str, list[str]] = {}
            for axis in AXIS_KEYS:
                if axis in exp and isinstance(exp[axis], list):
                    axis_map = mappings.get(axis, {})
                    axis_reloc = reloc_per_axis.get(axis, {})
                    new_codes, stats, relocated = transform_codes(exp[axis], axis_map, drop_per_axis.get(axis, set()), axis_reloc)
                    exp[axis] = new_codes
                    for tgt_axis, tgt_codes in relocated.items():
                        all_reloc.setdefault(tgt_axis, []).extend(tgt_codes)
                    for k, v in stats.items():
                        file_stat[f"{axis}.{k}"] += v
                        global_stats[k] += v
            # Second pass: apply reloc into target axes
            for tgt_axis, tgt_codes in all_reloc.items():
                if tgt_axis not in exp:
                    exp[tgt_axis] = []
                for tc in tgt_codes:
                    if tc not in exp[tgt_axis]:
                        exp[tgt_axis].append(tc)
            out_lines.append(json.dumps(r, ensure_ascii=False))

        file_summaries.append({"file": fp.name, "stats": dict(file_stat)})
        if not args.dry_run:
            bak = fp.with_suffix(".jsonl.bak.part3")
            shutil.copy(fp, bak)
            fp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
            print(f"  {fp.name}: written (backup {bak.name})")
        else:
            tot = sum(file_stat[k] for k in file_stat if k.endswith(".translated"))
            untouched = sum(file_stat[k] for k in file_stat if k.endswith(".unmapped_ko"))
            print(f"  {fp.name}: would translate {tot}, leave {untouched} unmapped KO")

    print(f"\n=== Global stats ===")
    for k, v in sorted(global_stats.items()):
        print(f"  {k}: {v}")

    if args.dry_run:
        print(f"\nDRY mode. Re-run with --apply.")
    print(f"\nNext steps after --apply:")
    print(f"  1. Re-run replay_synthetic_observations.py --save-baseline")
    print(f"     (new baseline_v3 will reflect cleaned synthetic data)")
    print(f"  2. Document baseline delta in docs/status/evaluation-baseline.md")
    print(f"  3. Commit synthetic JSONL files + new baseline + audit")


if __name__ == "__main__":
    main()
