#!/usr/bin/env python3
"""정본 prefix/namespace 가드레일 — 온톨로지팀 .ttl 전수 검사.

cashtoss.info 네임스페이스마다 '정본 짧은 이름 1개 + 정본 IRI 1개'를 강제한다.
@prefix 선언과 SHACL sh:prefixes 블록(sh:prefix/sh:namespace) 둘 다 검사.

위반 유형:
  - NON_CANONICAL_PREFIX : IRI는 정본이나 짧은 이름이 비정본 (예: context: → ctx 이어야 함)
  - LEGACY_NAMESPACE     : cashtoss IRI인데 정본 집합에 없음 (예: …/ontology/agent# = 행위자 actor: 또는 화석)
  - UNKNOWN_PREFIX_FOR_IRI: 외부가 아닌데 매핑 불가

외부/표준(rdf/rdfs/owl/xsd/sh/prov/dct/obo/kb 등 비 cashtoss IRI)은 통과.

사용:
  python ontology-team/06-reasoning/ontology/scripts/validate_prefixes.py
  python .../validate_prefixes.py --root <ontology dir>
종료코드: 위반 0 → 0, 위반 있으면 1 (make verify-prefixes / CI 용).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ── 정본 map (SSOT) — plan의 정본 표준 표와 1:1 ──────────────────────────────
CASHTOSS = "https://cashtoss.info"
CANONICAL: dict[str, str] = {
    "core":     f"{CASHTOSS}/ontology#",
    "risk":     f"{CASHTOSS}/ontology/risk#",
    "haz":      f"{CASHTOSS}/ontology/risk/hazard#",
    "agent":    f"{CASHTOSS}/ontology/risk/agent#",       # 위험원 전용
    "ctx":      f"{CASHTOSS}/ontology/risk/context#",
    "she":      f"{CASHTOSS}/ontology/risk/situation#",
    "sr":       f"{CASHTOSS}/ontology/sr#",
    "guide":    f"{CASHTOSS}/ontology/guide#",
    "law":      f"{CASHTOSS}/ontology/law#",
    "pen":      f"{CASHTOSS}/ontology/penalty#",
    "app":      f"{CASHTOSS}/ontology/app#",
    "bridge":   f"{CASHTOSS}/ontology/bridge#",
    "industry": f"{CASHTOSS}/ontology/industry#",
    "actor":    f"{CASHTOSS}/ontology/actor#",            # 신규 — 행위자(Worker)
    "prod":     f"{CASHTOSS}/ontology/production#",
    "kr":       f"{CASHTOSS}/ontology/swrl-rules#",
    "krs":      f"{CASHTOSS}/ontology/shacl-rules#",
    "shape":    f"{CASHTOSS}/ontology/shape#",
    "demo":     f"{CASHTOSS}/ontology/demo#",
    # A5 SKOS 코드 체계 — 축별 namespace (gen_skos_scheme.py). A2에서 w3id로 마이그레이션.
    "code-accident-type":   f"{CASHTOSS}/ontology/code/accident-type#",
    "code-hazardous-agent": f"{CASHTOSS}/ontology/code/hazardous-agent#",
    "code-work-context":    f"{CASHTOSS}/ontology/code/work-context#",
}
# IRI → 정본 짧은 이름 (역매핑)
IRI_TO_PREFIX: dict[str, str] = {v: k for k, v in CANONICAL.items()}

# 표준/외부 prefix — 검사 면제 (비 cashtoss IRI는 자유)
STANDARD_PREFIXES = {"rdf", "rdfs", "owl", "xsd", "sh", "prov", "dct", "dc",
                     "skos", "obo", "kb", "foaf"}

# 검사 제외 파일 (구버전 base 스냅샷/읽기용 주석본 — 비활성, 표준화 비대상)
SKIP_FILES = {
    "kosha-ontology.annotated.ttl",     # 읽기용 주석본(archive/)
}

# ── 정규식 ───────────────────────────────────────────────────────────────────
RE_TTL_PREFIX = re.compile(r'@prefix\s+([\w.-]+):\s+<([^>]+)>\s*\.')
# SPARQL PREFIX: 줄 시작(@prefix 아님) — @prefix 줄 이중매칭 방지 위해 ^\s* 앵커
RE_SPARQL_PREFIX = re.compile(r'(?i)^\s*PREFIX\s+([\w.-]+):\s+<([^>]+)>')
# SHACL: [ sh:prefix "agent" ; sh:namespace "https://…"^^xsd:anyURI ]
RE_SH_PAIR = re.compile(r'sh:prefix\s+"([^"]+)"\s*;\s*sh:namespace\s+"([^"]+?)"')


def check_pair(prefix: str, ns: str) -> tuple[str, str] | None:
    """(prefix, namespace) 검증. 위반이면 (유형, 메시지), 정상이면 None."""
    if prefix in STANDARD_PREFIXES:
        return None
    if not ns.startswith(CASHTOSS):
        return None  # 외부 네임스페이스 — 면제
    if ns in IRI_TO_PREFIX:
        expected = IRI_TO_PREFIX[ns]
        if prefix != expected:
            return ("NON_CANONICAL_PREFIX",
                    f"'{prefix}:' → <{ns}> 는 정본 짧은 이름이 '{expected}:' 이어야 함")
        return None
    # cashtoss IRI인데 정본 집합에 없음 = 레거시/화석 네임스페이스
    return ("LEGACY_NAMESPACE",
            f"'{prefix}:' → <{ns}> 는 정본 네임스페이스가 아님 (레거시/오타?)")


def scan_file(path: Path) -> list[tuple[str, int, str, str]]:
    """파일에서 (유형, 줄번호, prefix, 메시지) 위반 목록."""
    out: list[tuple[str, int, str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        for rx in (RE_TTL_PREFIX, RE_SPARQL_PREFIX):
            for m in rx.finditer(line):
                v = check_pair(m.group(1), m.group(2))
                if v:
                    out.append((v[0], i, m.group(1), v[1]))
        for m in RE_SH_PAIR.finditer(line):
            v = check_pair(m.group(1), m.group(2))
            if v:
                out.append((v[0], i, m.group(1), v[1] + " [sh:prefixes]"))
    return out


def main() -> int:
    try:  # Windows cp949 콘솔에서도 한글/기호 출력 (크래시 방지)
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parents[1]
    ap.add_argument("--root", type=Path, default=default_root,
                    help="검사할 .ttl 루트 (기본: ontology 디렉토리)")
    args = ap.parse_args()

    files = sorted(p for p in args.root.rglob("*.ttl"))
    total_viol = 0
    scanned = 0
    skipped: list[str] = []
    for f in files:
        if f.name in SKIP_FILES:
            skipped.append(f.name)
            continue
        if "archive" in f.relative_to(args.root).parts:  # archive/ = 비활성, 표준화 비대상
            skipped.append(f.relative_to(args.root).as_posix())
            continue
        scanned += 1
        viols = scan_file(f)
        if viols:
            total_viol += len(viols)
            print(f"\n[FAIL] {f.name}")
            for vtype, lineno, prefix, msg in viols:
                print(f"    L{lineno:<5} [{vtype}] {msg}")

    print(f"\n{'='*70}")
    print(f"스캔 {scanned} 파일, 건너뜀 {len(skipped)} (화석/백업), 위반 {total_viol}건")
    if skipped:
        print(f"  건너뜀: {', '.join(skipped)}")
    if total_viol == 0:
        print("[OK] 모든 prefix가 정본 표준에 부합")
        return 0
    print("[FAIL] 비정본 prefix/namespace 발견 — 정본 map(CANONICAL) 기준으로 수정 필요")
    return 1


if __name__ == "__main__":
    sys.exit(main())
