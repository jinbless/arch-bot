#!/usr/bin/env python3
"""assembly manifest 정합 가드레일 — '무엇이 온톨로지인가' 단일 정본 강제.

검사:
  1. SSOT(manifest_source.ENTRIES)가 가리키는 모든 file이 dir에 존재.
  2. dir의 모든 ontology 파일(*.ttl/*.owl/*.swrl, top-level + archive/)이 SSOT에 등록
     (silent orphan 0 — 이게 핵심: 등록 안 된 파일이 있으면 "온톨로지에 뭐가 있는지" 모름).
  3. assembly-manifest.json(생성물)이 SSOT 재생성과 동일(freshness — 수동편집/재생성 누락 차단).

사용: python ontology-team/06-reasoning/ontology/scripts/validate_manifest.py  (make verify-manifest)
종료코드: 위반 0 → 0, 있으면 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scripts/
ONT = HERE.parent                                # ontology dir
ASM = ONT / "assembly"
sys.path.insert(0, str(ASM))
import gen_manifest  # noqa: E402
import manifest_source as ms  # noqa: E402

MANIFEST = ONT / "assembly-manifest.json"
ONT_EXTS = (".ttl", ".owl", ".swrl")


def _dir_files() -> set[str]:
    """dir의 ontology 파일 상대경로(top-level + archive/ subtree)."""
    out: set[str] = set()
    for p in ONT.iterdir():
        if p.is_file() and p.suffix in ONT_EXTS:
            out.add(p.name)
    arc = ONT / "archive"
    if arc.is_dir():
        for p in arc.rglob("*"):
            if p.is_file() and p.suffix in ONT_EXTS:
                out.add(p.relative_to(ONT).as_posix())
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    fail = 0

    # 1. SSOT file 존재 + expected JSON (build()는 누락 시 SystemExit)
    try:
        expected = gen_manifest.build()
    except SystemExit:
        print("[FAIL] SSOT가 가리키는 파일이 dir에 없음 (위 gen_manifest 출력 참조)")
        return 1

    ssot_files = {e["file"] for e in ms.ENTRIES}
    dir_files = _dir_files()

    # 2. silent orphan: dir에 있으나 SSOT에 없음
    orphan = sorted(dir_files - ssot_files)
    if orphan:
        fail += len(orphan)
        print(f"[FAIL] SSOT 미등록 파일 {len(orphan)}개 (silent orphan — manifest_source.py에 등록 필요):")
        for f in orphan:
            print("   +", f)

    # 2b. SSOT에 있으나 dir에 없음 (build()가 이미 잡지만 이중 확인)
    ghost = sorted(ssot_files - dir_files)
    if ghost:
        fail += len(ghost)
        print(f"[FAIL] SSOT에 있으나 dir에 없는 파일 {len(ghost)}개:")
        for f in ghost:
            print("   -", f)

    # 3. freshness: 생성물이 재생성과 동일?
    if not MANIFEST.exists():
        fail += 1
        print("[FAIL] assembly-manifest.json 없음 — make gen-manifest 필요")
    else:
        on_disk = MANIFEST.read_text(encoding="utf-8")
        fresh = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
        if on_disk != fresh:
            fail += 1
            print("[FAIL] assembly-manifest.json이 SSOT 재생성과 불일치 — make gen-manifest 필요")

    print(f"\n{'='*64}")
    print(f"SSOT {len(ssot_files)} files / dir {len(dir_files)} files / "
          f"profiles {len(ms.PROFILES)} / archive {len(ms.archive_files())}")
    if fail == 0:
        print("[OK] manifest 정합 — 모든 dir 파일이 단일 정본에 등록됨")
        return 0
    print(f"[FAIL] {fail} 위반")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
