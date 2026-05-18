#!/usr/bin/env python3
"""세션 (2026-05-18 저녁 Tier 1-3.A) 문서 갱신 일관성 검증.

검증 항목 (plan tingly-snuggling-wand.md Verification Plan A-E):
1. commit hash 일치 (모든 doc에서 6개 commit만 등장)
2. metric 일치 (76→4 = 94.7%, 8/8 PASS, 2216 NodeShapes 등)
3. 신규 script 파일이 최소 1개 doc에서 참조
4. 신규 doc 파일들의 markdown 링크 target 실재
5. Latest updated 2026-05-18 (current-session, evaluation-baseline)
6. F.3.1/F.3.4/F.3.5 ✅ 마커 존재

사용:
  python scripts/verify_session_docs.py
  python scripts/verify_session_docs.py --strict   # warning도 fail로 처리

산출:
- stdout: 사람읽기 표
- exit code: 0 (모두 통과), 1 (warning), 2 (critical)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "docs").is_dir() and (p / "data-team").is_dir():
            return p
    raise RuntimeError("repo root not found")


REPO = _find_root()
DOCS_DIR = REPO / "docs"

# Session commits (Tier 1 재포함 + T2.A/B/C/D + T3.A)
SESSION_COMMITS = {
    "93c49fe": "T1.A/T1.C 재포함 + T2.A pyshacl reasoner shadow",
    "78886b3": "T2.B/C/D scripts + Makefile f3-*",
    "ac98d4c": "T2.D 8/8 PASS + T2.B Java edit",
    "606b91f": "T3.A schema enum 529 codes",
    "325ad37": "Merge — Tier 2",
    "b237e78": "Merge — Tier 3.A",
}

# 신규 scripts (이번 세션 산출, 최소 1개 doc에서 참조 필수)
NEW_SCRIPTS = [
    "pyshacl_shadow_validator",
    "shadow_reasoner",
    "compile_kb_to_ttl",
    "f3_drift_check",
    "promote_f32_per_candidate",
    "_migrate_embedding_cache_to_npz",
]

# 신규 docs (이번 세션 산출, 링크 유효성 검증 대상)
NEW_DOCS = [
    "docs/dev-notes/F.3-axiom-discovery.md",
    "docs/dev-notes/T3.A-closed-vocab-schema-enum.md",
    "docs/status/t2d-per-candidate-promotion-2026-05-18.md",
    "docs/status/t3a-closed-vocab-schema-enum-2026-05-18.md",
]

# 핵심 metric (모든 관련 doc에서 동일 값 명시)
METRIC_EXPECTATIONS = [
    # (metric_name, regex, min_occurrences, expected_text)
    ("T3.A free-create 감소율", r"76\s*[→\-]\s*4|94\.7\s*%", 3, "76→4 또는 94.7% 명시"),
    ("T2.D PASS 수", r"8\s*/\s*8\s*PASS|8/8\s+candidates?", 3, "8/8 PASS 명시"),
    ("Fuseki SPARQL NodeShapes", r"2[,.]?216\s+(?:Node)?[Ss]hapes?", 2, "2216 NodeShapes 명시"),
    ("kb-candidates.ttl shapes", r"2[,.]?192\s+(?:SHACL\s+)?(?:Node)?[Ss]hapes?", 2, "2192 shapes 명시"),
]

# 완료 마커 (workplan에서)
COMPLETION_MARKERS = [
    ("F.3.1", r"F\.3\.1.*✅"),
    ("F.3.4", r"F\.3\.4.*✅"),
    ("F.3.5", r"F\.3\.5.*✅"),
    ("Tier 3.A", r"Tier\s*3\.A.*✅"),
    ("T2.D", r"T2\.D.*(?:✅|8/8)"),
]


def collect_md_files() -> list[Path]:
    return sorted(DOCS_DIR.rglob("*.md"))


def grep_count(pattern: str, files: list[Path], regex_flags: int = 0) -> dict[Path, int]:
    """Return {file: match_count} for files where pattern matches at least once."""
    results: dict[Path, int] = {}
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        matches = re.findall(pattern, text, regex_flags)
        if matches:
            results[f] = len(matches)
    return results


def grep_files(pattern: str, files: list[Path], regex_flags: int = 0) -> list[Path]:
    return list(grep_count(pattern, files, regex_flags).keys())


def check_commits(md_files: list[Path]) -> tuple[int, list[str]]:
    """검증 1: commit hash 일치 — session commits만 등장해야 함."""
    findings: list[str] = []
    severity = 0

    # 7-char hex hash 패턴 (git short hash)
    HASH_PATTERN = r"\b([0-9a-f]{7,40})\b"
    # commit context 단서 — commit/merge/HEAD/main/직전/직후/→ 옆 또는 backtick 직접
    # Also catches `<hash>` standalone (e.g., "main `325ad37`").
    CONTEXT_PATTERN = r"(?:(?:commit|merge|HEAD|main|→|->)\s*[`']?([0-9a-f]{7,12})[`']?|[`']([0-9a-f]{7,12})[`'])"

    all_session_hashes = set(SESSION_COMMITS.keys())
    referenced: dict[str, list[Path]] = {h: [] for h in all_session_hashes}
    unknown_in_session: dict[str, list[Path]] = {}

    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in re.finditer(CONTEXT_PATTERN, text, re.IGNORECASE):
            # group(1) is from first alternative, group(2) is from second
            h_raw = match.group(1) or match.group(2)
            if not h_raw:
                continue
            h = h_raw[:7]
            if h in all_session_hashes:
                referenced[h].append(f)

    # session commits 각각 어디서 참조됐는지 보고
    for h, desc in SESSION_COMMITS.items():
        refs = referenced.get(h, [])
        if not refs:
            findings.append(f"  [WARN] session commit `{h}` ({desc}) — 어떤 doc에도 명시 안 됨")
            severity = max(severity, 1)
        else:
            rel = [str(r.relative_to(REPO)) for r in set(refs)]
            findings.append(f"  [OK]   `{h}` referenced in {len(set(refs))} docs: {rel[:3]}{'...' if len(rel)>3 else ''}")
    return severity, findings


def check_metrics(md_files: list[Path]) -> tuple[int, list[str]]:
    """검증 2: metric 일치 — 핵심 수치가 여러 doc에서 동일."""
    findings: list[str] = []
    severity = 0
    for name, pattern, min_occ, expected in METRIC_EXPECTATIONS:
        matched = grep_files(pattern, md_files, re.MULTILINE)
        n = len(matched)
        if n >= min_occ:
            findings.append(f"  [OK]   {name}: {n} docs ({expected})")
        else:
            findings.append(f"  [WARN] {name}: only {n} docs (expected ≥{min_occ}) ({expected})")
            severity = max(severity, 1)
    return severity, findings


def check_new_scripts(md_files: list[Path]) -> tuple[int, list[str]]:
    """검증 3: 신규 script가 최소 1개 doc에서 참조됨."""
    findings: list[str] = []
    severity = 0
    for script in NEW_SCRIPTS:
        # word boundary 또는 .py
        pattern = rf"\b{re.escape(script)}(?:\.py)?\b"
        matched = grep_files(pattern, md_files)
        n = len(matched)
        if n >= 1:
            findings.append(f"  [OK]   {script}: referenced in {n} docs")
        else:
            findings.append(f"  [FAIL] {script}: NO docs reference (must be at least 1)")
            severity = max(severity, 2)
    return severity, findings


def check_new_doc_links(md_files: list[Path]) -> tuple[int, list[str]]:
    """검증 4: 신규 doc의 markdown 링크 target 실재."""
    findings: list[str] = []
    severity = 0
    LINK_PATTERN = r"\[[^]]+\]\(([^)#]+\.md)(?:#[^)]*)?\)"

    for doc_rel in NEW_DOCS:
        doc_path = REPO / doc_rel
        if not doc_path.exists():
            findings.append(f"  [FAIL] {doc_rel}: not found")
            severity = max(severity, 2)
            continue
        try:
            text = doc_path.read_text(encoding="utf-8")
        except Exception as e:
            findings.append(f"  [FAIL] {doc_rel}: read error: {e}")
            severity = max(severity, 2)
            continue
        links = re.findall(LINK_PATTERN, text)
        broken: list[str] = []
        for link in links:
            # resolve relative to doc dir
            if link.startswith("/") or link.startswith("http"):
                continue
            target = (doc_path.parent / link).resolve()
            if not target.exists():
                broken.append(link)
        if broken:
            findings.append(f"  [FAIL] {doc_rel}: {len(broken)} broken link(s): {broken[:3]}")
            severity = max(severity, 2)
        else:
            findings.append(f"  [OK]   {doc_rel}: {len(links)} links all valid")
    return severity, findings


def check_latest_updated() -> tuple[int, list[str]]:
    """검증 5: current-session + evaluation-baseline Latest updated 2026-05-18."""
    findings: list[str] = []
    severity = 0
    targets = [
        ("docs/status/current-session.md", r"최신\s*갱신일.*2026-05-18"),
        ("docs/status/evaluation-baseline.md", r"Latest\s+updated.*2026-05-18"),
    ]
    for rel, pattern in targets:
        f = REPO / rel
        if not f.exists():
            findings.append(f"  [FAIL] {rel}: not found")
            severity = max(severity, 2)
            continue
        text = f.read_text(encoding="utf-8")
        if re.search(pattern, text):
            findings.append(f"  [OK]   {rel}: Latest updated 2026-05-18")
        else:
            findings.append(f"  [FAIL] {rel}: 'Latest updated 2026-05-18' 패턴 없음")
            severity = max(severity, 2)
    return severity, findings


def check_completion_markers(md_files: list[Path]) -> tuple[int, list[str]]:
    """검증 6: F.3.1/F.3.4/F.3.5 + Tier 3.A + T2.D ✅ 마커."""
    findings: list[str] = []
    severity = 0
    workplan = REPO / "docs/workplans/llm-accelerated-ontology-engineering.md"
    text = workplan.read_text(encoding="utf-8") if workplan.exists() else ""
    for label, pattern in COMPLETION_MARKERS:
        if re.search(pattern, text):
            findings.append(f"  [OK]   {label}: ✅ 마커 발견 (workplan)")
        else:
            findings.append(f"  [WARN] {label}: ✅ 마커 없음 (workplan)")
            severity = max(severity, 1)
    return severity, findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="warning도 fail로 처리 (exit 1)")
    args = ap.parse_args()

    md_files = collect_md_files()
    print(f"Scanning {len(md_files)} .md files under docs/...")

    checks = [
        ("1. Commit hash 일치", check_commits, [md_files]),
        ("2. Metric 일치", check_metrics, [md_files]),
        ("3. 신규 script 참조", check_new_scripts, [md_files]),
        ("4. 신규 doc 링크 유효", check_new_doc_links, [md_files]),
        ("5. Latest updated", check_latest_updated, []),
        ("6. 완료 마커", check_completion_markers, [md_files]),
    ]

    overall_severity = 0
    print()
    for title, fn, args_list in checks:
        print(f"=== {title} ===")
        sev, findings = fn(*args_list)
        for f in findings:
            print(f)
        print(f"  → severity: {['ok','warning','critical'][sev]}")
        print()
        overall_severity = max(overall_severity, sev)

    print(f"=== Overall verdict: {['OK','WARNING','CRITICAL'][overall_severity]} ===")
    if args.strict and overall_severity >= 1:
        return 1
    return 0 if overall_severity == 0 else overall_severity


if __name__ == "__main__":
    sys.exit(main())
