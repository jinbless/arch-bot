#!/usr/bin/env python3
"""문서 ↔ 코드/온톨로지/PG 정합 검증 (doc-sync).

verify_axiom_100pct.py 패턴 답습. axiom-100% + guide-accuracy Sprint 후
hand-maintained 정본 문서가 실제 PG/ontology 상태와 일치하는지 자동 검증한다.

5 step:
  1. GROUND_TRUTH    — PG(psycopg2) + ontology(rdflib) 실제 수치 추출 (+ JSON dump)
  2. DOC_ASSERTIONS  — 정본 문서가 핵심 사실/수치 문자열을 포함하는지
  3. GT_CONSISTENCY  — ground truth 수치가 문서에 실제로 반영됐는지 (live ↔ doc)
  4. AUTO_GEN_FRESH  — 재생성 auto-gen 산출물 유효성 (serving-validation PASS, dashboard 존재)
  5. LINK_INTEGRITY  — docs/README.md + CLAUDE.md 상대 링크가 실제 파일로 resolve

사용:
  PYTHONIOENCODING=utf-8 python scripts/verify_docs_sync.py
  PYTHONIOENCODING=utf-8 python scripts/verify_docs_sync.py --dump  # ground truth JSON 저장

exit 0 = OK, 1 = FAIL. PG 미가동 시 명확히 FAIL 사유 출력.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
ONT = REPO / "ontology-team" / "06-reasoning" / "ontology"
GT_DUMP = REPO / "scripts" / "doc_sync_ground_truth.json"


# ─────────────────────────────────────────────────────────────────────────
# Step 1 — GROUND TRUTH
# ─────────────────────────────────────────────────────────────────────────
def collect_ground_truth() -> tuple[dict, list[str]]:
    errors: list[str] = []
    gt: dict = {}

    # PG
    try:
        import psycopg2

        conn = psycopg2.connect(PG_CONNINFO)
        cur = conn.cursor()

        def scalar(sql: str) -> int:
            cur.execute(sql)
            return int(cur.fetchone()[0])

        gt["ci_total"] = scalar("SELECT COUNT(*) FROM checklist_items")
        gt["ci_max_gf"] = scalar("SELECT MAX(guide_frequency) FROM checklist_items")
        gt["ci_gf_gt1"] = scalar("SELECT COUNT(*) FROM checklist_items WHERE guide_frequency>1")
        gt["guide_hazard_rows"] = scalar(
            "SELECT COUNT(*) FROM guide_entity_feature_candidates "
            "WHERE entity_type='GUIDE' AND method='guide_hazard_weighted_majority'"
        )
        gt["guide_hazard_guides"] = scalar(
            "SELECT COUNT(DISTINCT guide_code) FROM guide_entity_feature_candidates "
            "WHERE entity_type='GUIDE' AND method='guide_hazard_weighted_majority'"
        )
        gt["sr_total"] = scalar("SELECT COUNT(*) FROM safety_requirements")
        gt["penalty_rule_index"] = scalar("SELECT COUNT(*) FROM penalty_rule_index")
        gt["guide_domain_incompat"] = scalar("SELECT COUNT(*) FROM guide_domain_incompatibilities")
        gt["kosha_guides"] = scalar("SELECT COUNT(*) FROM kosha_guides")
        conn.close()
    except Exception as e:
        errors.append(f"  PG 연결/쿼리 실패 (Docker kosha-pg Up 확인): {e}")

    # Ontology (rdflib) — guide-hazard ABox triple count
    try:
        from rdflib import Graph

        g = Graph()
        g.parse(str(ONT / "kosha-instances-guide-hazard.ttl"), format="turtle")
        q = """
            PREFIX guide: <https://cashtoss.info/ontology/guide#>
            SELECT (COUNT(*) AS ?c) WHERE {
              ?s ?p ?o .
              FILTER(?p IN (guide:addressesHazard, guide:guideAddressesAgent, guide:guideAppliesToContext))
            }
        """
        gt["guide_hazard_triples"] = int(list(g.query(q))[0][0])
        gt["guide_hazard_guide_subjects"] = len(set(g.subjects()))
    except Exception as e:
        errors.append(f"  guide-hazard ABox parse 실패: {e}")

    return gt, errors


# ─────────────────────────────────────────────────────────────────────────
# Step 2 — DOC ASSERTIONS (정본 문서가 핵심 사실 포함)
# ─────────────────────────────────────────────────────────────────────────
# (path, [must_contain], [must_not_contain])
DOC_ASSERTIONS: list[tuple[str, list[str], list[str]]] = [
    ("docs/status/evaluation-baseline.md",
     ["2026-05-28", "guide-accuracy", "axiom-100%", "53,378", "guide:addressesHazard"],
     []),
    ("docs/status/current-session.md",
     ["2026-05-28", "axiom-100%", "guide-accuracy", "SHACL CONSTRUCT", "guide_frequency"],
     []),
    ("docs/architecture/4-layer-architecture.md",
     ["SHACL CONSTRUCT", "kosha-rules-r14-r30-shacl-construct.ttl", "guide-accuracy"],
     ["`kosha-rules.swrl` (기존 8개)"]),
    ("docs/ontology/04-guide-layer.md",
     ["guide:addressesHazard", "guide_frequency", "guide-accuracy", "2,115"],
     []),
    ("serving-team/README.md",
     ["get_guides_by_hazard_features", "guide_frequency", "ci_weight"],
     []),
    ("ontology-team/README.md",
     ["SHACL CONSTRUCT", "guide:addressesHazard", "53,378", "2026-05-28"],
     []),
    ("docs/README.md",
     ["2026-05-28", "ontology-axiom-100pct.md", "guide-recommendation-accuracy.md"],
     []),
    ("docs/workplans/llm-accelerated-ontology-engineering.md",
     ["2026-05-28", "axiom-100%", "guide-accuracy"],
     []),
]


def check_doc_assertions() -> list[str]:
    errors: list[str] = []
    for rel, must, must_not in DOC_ASSERTIONS:
        p = REPO / rel
        if not p.exists():
            errors.append(f"  MISSING doc: {rel}")
            continue
        text = p.read_text(encoding="utf-8")
        for s in must:
            if s not in text:
                errors.append(f"  {rel}: 필수 문자열 누락: {s!r}")
        for s in must_not:
            if s in text:
                errors.append(f"  {rel}: stale 문자열 잔존: {s!r}")
    return errors


# ─────────────────────────────────────────────────────────────────────────
# Step 3 — GROUND TRUTH ↔ DOC CONSISTENCY (live 수치가 문서에 반영됐는지)
# ─────────────────────────────────────────────────────────────────────────
def check_gt_consistency(gt: dict) -> list[str]:
    errors: list[str] = []

    # (a) PG guide-hazard weighted rows == ABox triple count == 문서 인용 "2,115"
    rows = gt.get("guide_hazard_rows")
    triples = gt.get("guide_hazard_triples")
    if rows is not None and triples is not None and rows != triples:
        errors.append(
            f"  guide-hazard PG rows({rows}) != ABox triples({triples}) — ABox export 재실행 필요"
        )
    if rows is not None:
        token = f"{rows:,}"  # 2,115
        for rel in ("docs/status/evaluation-baseline.md", "docs/ontology/04-guide-layer.md",
                    "ontology-team/README.md", "docs/status/current-session.md"):
            t = (REPO / rel).read_text(encoding="utf-8")
            if token not in t:
                errors.append(f"  {rel}: guide-hazard rows {token} 미반영 (PG와 불일치)")

    # (b) PG max guide_frequency == 문서 인용 (max 130)
    mgf = gt.get("ci_max_gf")
    if mgf is not None:
        for rel in ("docs/status/evaluation-baseline.md", "serving-team/README.md",
                    "docs/ontology/04-guide-layer.md"):
            t = (REPO / rel).read_text(encoding="utf-8")
            if str(mgf) not in t:
                errors.append(f"  {rel}: ci_max_gf {mgf} 미반영")

    # (c) PG penalty_rule_index == 문서 인용 (4,076)
    pri = gt.get("penalty_rule_index")
    if pri is not None:
        t = (REPO / "docs/status/evaluation-baseline.md").read_text(encoding="utf-8")
        if f"{pri:,}" not in t:
            errors.append(f"  evaluation-baseline.md: penalty_rule_index {pri:,} 미반영")

    return errors


# ─────────────────────────────────────────────────────────────────────────
# Step 4 — AUTO-GEN FRESHNESS (재생성 산출물 유효)
# ─────────────────────────────────────────────────────────────────────────
def check_auto_gen() -> list[str]:
    errors: list[str] = []
    # (파일, health 마커) — validation report는 result: PASS, workprocess audit는 hard issue count: 0
    targets = [
        ("serving-validation-report-ci_cross_guide_broad_only_guard1.md", "result: `PASS`"),
        ("serving-workprocess-alignment-ci_cross_guide_broad_only_guard1.md", "hard issue count: `0`"),
    ]
    for name, marker in targets:
        f = ONT / name
        if not f.exists():
            errors.append(f"  MISSING auto-gen: {name}")
            continue
        t = f.read_text(encoding="utf-8")
        if "generated_at" not in t:
            errors.append(f"  {name}: generated_at 누락 (재생성 안 됨?)")
        if marker not in t:
            errors.append(f"  {name}: health 마커 없음: {marker!r} (hard violation 가능)")
    dash = ONT.parent / "visualization" / "dashboard.html"
    if not dash.exists() or dash.stat().st_size < 50_000:
        errors.append("  dashboard.html 없음/비정상 (build+assemble 재실행 필요)")
    return errors


# ─────────────────────────────────────────────────────────────────────────
# Step 5 — LINK INTEGRITY (인덱스/진입점 링크 resolve)
# ─────────────────────────────────────────────────────────────────────────
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def check_links() -> list[str]:
    errors: list[str] = []
    for rel in ("docs/README.md", "CLAUDE.md"):
        p = REPO / rel
        text = p.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"  {rel}: 죽은 링크 → {target}")
    return errors


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    dump = "--dump" in sys.argv
    overall_ok = True
    print("=== verify_docs_sync.py ===\n")

    print("Step 1/5: GROUND_TRUTH (PG + ontology)")
    gt, gt_errs = collect_ground_truth()
    for k, v in gt.items():
        print(f"  {k} = {v}")
    for e in gt_errs:
        print(e)
    ok = len(gt_errs) == 0
    print(f"  {'OK' if ok else 'FAIL'}")
    overall_ok = overall_ok and ok
    if dump and gt:
        GT_DUMP.write_text(json.dumps(gt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  dumped → {GT_DUMP.name}")

    print("\nStep 2/5: DOC_ASSERTIONS")
    errs = check_doc_assertions()
    print(f"  {'OK' if not errs else 'FAIL'} — {len(DOC_ASSERTIONS)} docs")
    for e in errs:
        print(e)
    overall_ok = overall_ok and not errs

    print("\nStep 3/5: GT_CONSISTENCY (live 수치 ↔ doc)")
    errs = check_gt_consistency(gt) if gt else ["  (ground truth 없음 — Step 1 실패)"]
    print(f"  {'OK' if not errs else 'FAIL'}")
    for e in errs:
        print(e)
    overall_ok = overall_ok and not errs

    print("\nStep 4/5: AUTO_GEN_FRESHNESS")
    errs = check_auto_gen()
    print(f"  {'OK' if not errs else 'FAIL'}")
    for e in errs:
        print(e)
    overall_ok = overall_ok and not errs

    print("\nStep 5/5: LINK_INTEGRITY (docs/README.md + CLAUDE.md)")
    errs = check_links()
    print(f"  {'OK' if not errs else 'FAIL'}")
    for e in errs:
        print(e)
    overall_ok = overall_ok and not errs

    print(f"\n=== Overall verdict: {'OK' if overall_ok else 'FAIL'} ===")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
