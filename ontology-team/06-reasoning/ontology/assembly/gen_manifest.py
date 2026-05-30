"""assembly-manifest.json 생성기 — manifest_source.py(SSOT) → JSON 산출물.

gen_canonical_code_shape.py 패턴. 산출물은 git-tracked·수동편집 금지. 소비자(6개)는
이 JSON의 profiles[name] ordered list를 로드한다. Java는 번들 Jena JSON으로 읽음.

사용: PYTHONIOENCODING=utf-8 python assembly/gen_manifest.py   (make gen-manifest)
빌드시 검증: 모든 entry file이 dir에 존재해야 함(없으면 exit 1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONT = HERE.parent  # ontology dir
sys.path.insert(0, str(HERE))
import manifest_source as ms  # noqa: E402

OUT = ONT / "assembly-manifest.json"


def build() -> dict:
    missing = [e["file"] for e in ms.ENTRIES if not (ONT / e["file"]).exists()]
    if missing:
        print("[gen-manifest] FAIL — SSOT가 가리키는 파일이 dir에 없음:", file=sys.stderr)
        for m in missing:
            print("   -", m, file=sys.stderr)
        sys.exit(1)
    profiles = {p: [{"file": e["file"], "format": e["format"]} for e in ms.by_profile(p)]
                for p in ms.PROFILES}
    return {
        "_comment": "AUTO-GENERATED from assembly/manifest_source.py — 수동편집 금지. "
                    "재생성: make gen-manifest. 정합성: make verify-manifest.",
        "profiles": profiles,
        "archive": ms.archive_files(),
        "files": ms.ENTRIES,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = len(ms.ENTRIES)
    print(f"[gen-manifest] wrote {OUT.name} — {n} files, {len(ms.PROFILES)} profiles")
    for p in ms.PROFILES:
        print(f"    {p:<20} {len(data['profiles'][p]):>3} files")
    print(f"    {'archive':<20} {len(data['archive']):>3} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
