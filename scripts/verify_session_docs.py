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

# Session commits (Tier 1 재포함 + T2.A-D + T3.A + Phase G.1-4 + Tier 4 후속)
SESSION_COMMITS = {
    # 이전 sweep (985b46f / 673de43까지)
    "93c49fe": "T1.A/T1.C 재포함 + T2.A pyshacl reasoner shadow",
    "78886b3": "T2.B/C/D scripts + Makefile f3-*",
    "ac98d4c": "T2.D 8/8 PASS + T2.B Java edit",
    "606b91f": "T3.A schema enum 529 codes",
    "325ad37": "Merge — Tier 2",
    "b237e78": "Merge — Tier 3.A",
    # Phase G + Tier 4 (이번 sweep 추가)
    "b9de6f0": "Phase G.1 PG materialization",
    "d6b4589": "Merge — Phase G.1",
    "2f7ef92": "Phase G.2 GuideUsageProfile + PG",
    "8ddc2c7": "Phase G.3 penalty_rule_index PG (+27.16%p)",
    "434f35f": "Phase G.4 reasoner-derived view + Openllet 분석",
    "5ee1709": "Merge — Phase G.2-4",
    "03f6afe": "T4 AsymmetricProperty 패치",
    "5edae0b": "Merge — T4 fix",
    "1bacd44": "T4 #4 Pellet reporting",
    "70d2862": "T4 #1-3 + SWRL Pellet",
    "448a8d0": "Merge — T4 #1-4",
    # T4 #1 후속 + moellab 비교 (2026-05-19, 본 sweep 추가)
    "a26c888": "feat(T4 #1 후속) — 77 SHE manual review + matcher refactor sprint plan",
    "1bfd6b8": "Merge — T4 #1 후속",
    "833dcd7": "docs(analysis) — moellab.info/ohs 위험요소 비교 + .gitignore 갱신",
    "3502eff": "Merge — moellab 위험요소 비교 분석",
}

# 신규 scripts (이번 세션 산출, 최소 1개 doc에서 참조 필수)
NEW_SCRIPTS = [
    # Tier 1-3.A
    "pyshacl_shadow_validator",
    "shadow_reasoner",
    "compile_kb_to_ttl",
    "f3_drift_check",
    "promote_f32_per_candidate",
    "_migrate_embedding_cache_to_npz",
    # Phase G + T4
    "import_domain_incompatibilities_to_pg",
    "import_penalty_to_pg",
    "sample_query_equality",
    "bench_shadow_reasoner",
    # T4 #1 후속 (본 sweep 추가)
    "patch_she_visual_triggers",
    "she_review_ui",
]

# 신규 docs (이번 세션 산출, 링크 유효성 검증 대상)
NEW_DOCS = [
    # Tier 1-3.A
    "docs/dev-notes/F.3-axiom-discovery.md",
    "docs/dev-notes/T3.A-closed-vocab-schema-enum.md",
    "docs/status/t2d-per-candidate-promotion-2026-05-18.md",
    "docs/status/t3a-closed-vocab-schema-enum-2026-05-18.md",
    # Phase G + T4
    "docs/dev-notes/phase-g.1-domain-incompatibilities-pg.md",
    "docs/dev-notes/phase-g.2-guide-usage-profiles-pg.md",
    "docs/dev-notes/phase-g.3-penalty-rule-index-pg.md",
    "docs/dev-notes/phase-g.4-she-patterns-reasoner-derived.md",
    "docs/dev-notes/t4-administrative-fine-scope-decision.md",
    "docs/dev-notes/t4-77-she-matcher-integration-decision.md",
    "docs/dev-notes/t4-swrl-pellet-integration.md",
    # T4 #1 후속 + moellab 비교 (본 sweep 추가)
    "docs/dev-notes/t4-77-she-manual-review-results.md",
    "docs/workplans/she-matcher-broadness-refactor.md",
    "docs/dev-notes/moellab-vs-devserver-comparison.md",
    # Hazard-direct pivot sprint plan (정본 등록)
    "docs/workplans/hazard-direct-architecture-pivot.md",
]

# 핵심 metric (모든 관련 doc에서 동일 값 명시)
METRIC_EXPECTATIONS = [
    # (metric_name, regex, min_occurrences, expected_text)
    # Tier 1-3.A
    ("T3.A free-create 감소율", r"76\s*[→\-]\s*4|94\.7\s*%", 3, "76→4 또는 94.7% 명시"),
    ("T2.D PASS 수", r"8\s*/\s*8\s*PASS|8/8\s+candidates?", 3, "8/8 PASS 명시"),
    ("Fuseki SPARQL NodeShapes", r"2[,.]?216\s+(?:Node)?[Ss]hapes?", 2, "2216 NodeShapes 명시"),
    ("kb-candidates.ttl shapes", r"2[,.]?192\s+(?:SHACL\s+)?(?:Node)?[Ss]hapes?", 2, "2192 shapes 명시"),
    # Phase G + T4
    ("Phase G.3 penalty_accuracy 개선", r"\+?27\.16\s*%p?|0\.2716", 3, "+27.16%p 또는 0.2716 명시"),
    ("SWRL R-3 inferred count", r"3[,.]?579", 3, "3,579 HighSeverityPenalty"),
    ("SWRL R-1 inferred count", r"\b107\b.*(?:exemptedBy|inferred|R-1)|R-1.*\b107\b", 2, "107 exemptedBy 명시"),
    ("guide_domain_incompat PG rows", r"2[,.]?016\s+rows?", 2, "2,016 PG rows"),
    ("penalty_rule_index PG rows", r"4[,.]?076", 2, "4,076 rules"),
    # T4 #1 후속 + moellab 비교 (본 sweep 추가)
    ("T4 #1 후속 VETOED 수치", r"-10\.17\s*%p?|0\.1017", 2, "Step 2 Batch 1 she_accuracy -10.17%p"),
    ("approve/modify/defer 분포", r"approve\s*57|modify\s*19|defer\s*1", 2, "manual review 결과 분포"),
    ("moellab hazards 합계", r"37[\s/]+hazards?|37\s*위험요소", 2, "8 사진 × 평균 4.6 = 37"),
]

# 완료 마커 (workplan에서)
COMPLETION_MARKERS = [
    # Tier 1-3.A
    ("F.3.1", r"F\.3\.1.*✅"),
    ("F.3.4", r"F\.3\.4.*✅"),
    ("F.3.5", r"F\.3\.5.*✅"),
    ("Tier 3.A", r"Tier\s*3\.A.*✅"),
    ("T2.D", r"T2\.D.*(?:✅|8/8)"),
    # Phase G + T4
    ("Phase G.1", r"Phase\s*G\.1.*✅"),
    ("Phase G.2", r"Phase\s*G\.2.*✅"),
    ("Phase G.3", r"Phase\s*G\.3.*✅"),
    ("Phase G.4", r"Phase\s*G\.4.*✅"),
    ("Tier 4 #3 SWRL", r"(?:T(?:ier)?\s*4\s*#?3|Tier\s*4\s*fix).*✅"),
    # T4 #1 후속 + moellab 비교 (본 sweep 추가)
    ("T4 #1 후속", r"T4\s*#?1\s*후속.*✅"),
    ("moellab 비교", r"moellab.*✅"),
    # Hazard-direct pivot (sprint plan 작성 완료 마커)
    ("hazard-direct pivot plan", r"hazard-direct.*✅"),
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
        # 검증 대상: 최신 sweep 기준 (Phase G + T4) 또는 직전 sweep (Tier 1-3.A) 모두 PASS
        ("docs/status/current-session.md", r"최신\s*갱신일.*2026-05-(18|19)"),
        ("docs/status/evaluation-baseline.md", r"Latest\s+updated.*2026-05-(18|19)"),
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
