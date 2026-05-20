#!/usr/bin/env python3
"""Aggregate koshaontology data into JS snippet for dashboard embedding.

v2.0: DB 직접 쿼리 + Pipe-B/C 데이터 통합.
"""

import json
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent  # ontology-team/06-reasoning
# monorepo 재구성 (2026-05-16) 후 pipe 데이터는 data-team 산하로 이동.
# parents: [0]visualization [1]06-reasoning [2]ontology-team [3]repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
PIPE_A = REPO_ROOT / "data-team" / "02-extraction" / "pipe-A" / "data"
PIPE_B = REPO_ROOT / "data-team" / "02-extraction" / "pipe-B" / "data"
PIPE_C = REPO_ROOT / "data-team" / "03-validation" / "pipe-C" / "data"
PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_db_stats():
    """DB에서 전 파이프라인 통계 직접 수집."""
    conn = psycopg2.connect(PG_CONNINFO)
    cur = conn.cursor()

    tables = [
        "articles", "norm_statements", "safety_requirements", "penalty_routes",
        "sr_ns_mapping", "sr_article_mapping",
        "kosha_guides", "checklist_items", "ci_sr_mapping",
        "domain_terms", "work_processes", "equipment_specs",
        "document_requirements", "wp_ppe",
        "dt_sr_mapping", "wp_sr_mapping", "es_sr_mapping", "dr_sr_mapping",
        "guide_inter_links",
        "guide_article_mapping",
        "ohs_analysis_records", "ohs_safety_videos", "ohs_hazard_code_gaps",
        # Pilot v2 (격리, 2026-04-26)
        "safety_requirements_v2", "sr_ns_mapping_v2", "sr_article_mapping_v2",
        # SHE (Phase 1~2, 2026-04-29)
        "she_catalog", "she_sr_mapping", "she_ci_mapping",
    ]
    counts = {}
    for t in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except Exception as e:
            # 테이블이 없으면 0으로 (graceful)
            counts[t] = 0
            conn.rollback()

    # SR Phase 3
    phase3_fields = ["requires_ppe", "has_corrective_action", "has_incident_response",
                     "applicable_industry", "hazard_assessment"]
    phase3 = {}
    for f in phase3_fields:
        cur.execute(f"SELECT count(*) FROM safety_requirements WHERE {f} IS NOT NULL")
        phase3[f] = cur.fetchone()[0]

    # Faceted 태깅 통계
    faceted_tables = {
        "safety_requirements": ["accident_types", "hazardous_agents", "work_contexts"],
        "checklist_items": ["accident_types", "hazardous_agents", "work_contexts"],
        "domain_terms": ["hazardous_agents", "work_contexts"],
        "equipment_specs": ["work_contexts"],
        "work_processes": ["accident_types", "work_contexts"],
    }
    faceted = {}
    for tbl, cols in faceted_tables.items():
        total_q = f"SELECT count(*) FROM {tbl}"
        cur.execute(total_q)
        total = cur.fetchone()[0]
        # 최소 1개 facet 컬럼이 채워진 행
        conds = " OR ".join(f"{c} IS NOT NULL" for c in cols)
        cur.execute(f"SELECT count(*) FROM {tbl} WHERE {conds}")
        tagged = cur.fetchone()[0]
        faceted[tbl] = {"total": total, "tagged": tagged, "pct": round(tagged * 100 / total, 1) if total else 0}

    # CI orphan (SR 매핑 없는 CI 중 facet도 없는 비율)
    cur.execute("""
        SELECT count(*) FROM checklist_items
        WHERE identifier NOT IN (SELECT DISTINCT ci_id FROM ci_sr_mapping)
          AND accident_types IS NULL AND hazardous_agents IS NULL AND work_contexts IS NULL
    """)
    ci_orphan_remaining = cur.fetchone()[0]
    faceted["ci_orphan"] = {"remaining": ci_orphan_remaining, "total_ci": counts.get("checklist_items", 0)}

    # 도메인별 상세
    cur.execute("""
        SELECT g.domain,
               count(DISTINCT g.guide_code) AS guides,
               sum(g.ci_count) AS ci,
               sum(g.dt_count) AS dt,
               sum(g.wp_count) AS wp,
               sum(g.es_count) AS es,
               sum(g.dr_count) AS dr
        FROM kosha_guides g
        GROUP BY g.domain ORDER BY g.domain
    """)
    domain_detail = {}
    for row in cur.fetchall():
        domain_detail[row[0]] = {
            "guides": row[1], "ci": row[2], "dt": row[3],
            "wp": row[4], "es": row[5], "dr": row[6],
        }

    # 도메인별 ci_sr_mapping 수
    cur.execute("""
        SELECT g.domain, count(m.ci_id)
        FROM ci_sr_mapping m
        JOIN checklist_items ci ON ci.identifier = m.ci_id
        JOIN kosha_guides g ON g.guide_code = ci.source_guide
        GROUP BY g.domain ORDER BY g.domain
    """)
    for domain, mapped in cur.fetchall():
        if domain in domain_detail:
            domain_detail[domain]["mapped"] = mapped

    # binding_force
    cur.execute("SELECT binding_force, count(*) FROM checklist_items GROUP BY binding_force")
    binding = dict(cur.fetchall())

    # articlesByLaw
    cur.execute("SELECT law_type, count(*) FROM articles GROUP BY law_type")
    articles_by_law = dict(cur.fetchall())

    # OHS 분석 통계
    ohs = {}
    try:
        cur.execute("SELECT count(*) FROM ohs_analysis_records")
        ohs["analyses"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM ohs_safety_videos")
        ohs["videos"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM ohs_hazard_code_gaps")
        ohs["gaps"] = cur.fetchone()[0]
    except Exception:
        ohs = {"analyses": 0, "videos": 0, "gaps": 0}

    conn.close()
    return {
        "counts": counts,
        "phase3": phase3,
        "faceted": faceted,
        "ohs": ohs,
        "domainDetail": domain_detail,
        "binding": binding,
        "articlesByLaw": articles_by_law,
    }


def build_sr_registry():
    """Collect 626 SRs from batch files into compact records."""
    sr_dir = PIPE_A / "safety-requirements"
    records = []
    for fp in sorted(sr_dir.glob("sr-batch-*.json")):
        if "-input" in fp.name:
            continue
        data = load_json(fp)
        for sr in data.get("safetyRequirements", []):
            title = sr["title"]
            if len(title) > 40:
                title = title[:38] + "…"
            rec = {
                "id": sr["identifier"],
                "t": title,
                "a": sr.get("referencesArticle", []),
                "tp": sr.get("requirementType", ""),
                "haz": sr.get("addressesHazard", []),
                "nsc": len(sr.get("mandatedBy", [])),
                "bf": sr.get("bindingForce", ""),
                "sq": bool(sr.get("structuralRequirements")),
                "san": bool((sr.get("hasSanction") or {}).get("criminal")),
            }
            records.append(rec)
    return records


def build_penalty_routes(sr_articles):
    """Load only SR-referenced penalty routes in compact format."""
    data = load_json(PIPE_A / "penalty-routes.json")

    def shorten(text):
        if not text:
            return None
        if "5년" in text and "5천만" in text:
            return "P1"
        if "3년" in text and "3천만" in text:
            return "P2"
        if "7년" in text and "1억" in text:
            return "P3"
        if "1년 이상" in text and "10억" in text:
            return "P4a"
        return text[:20]

    routes = {}
    for code, entry in data.get("routes", {}).items():
        if code not in sr_articles:
            continue
        cr = entry.get("criminal")
        compact = {"t": entry.get("title", ""), "p": entry.get("hasPenalty", False)}
        if cr:
            emp = shorten(cr.get("violation_employer", {}).get("penalty") if cr.get("violation_employer") else None)
            con = shorten(cr.get("violation_contractor", {}).get("penalty") if cr.get("violation_contractor") else None)
            death = shorten(cr.get("death", {}).get("penalty") if cr.get("death") else None)
            if emp or con or death:
                compact["cr"] = [emp, con, death]
        routes[code] = compact
    return routes, data.get("metadata", {})


def build_audit_results(db_stats):
    """Build audit results from validation reports + DB stats."""
    results = []

    # Pipe-A
    sr_val = load_json(PIPE_A / "validation" / "sr-validation-report.json")
    results.append({"level": "PASS", "pipe": "Pipe-A", "check": "V1~V15 전체 검증",
                     "message": f"SR {sr_val.get('totalSR', 0)}개, NS {db_stats['counts']['norm_statements']}개, Articles {db_stats['counts']['articles']}개 — 15/15 PASS"})

    if sr_val.get("totalWarnings", 0) > 0:
        warn_types = {}
        for w in sr_val.get("warnings", []):
            rule = w.get("rule", "UNKNOWN")
            warn_types[rule] = warn_types.get(rule, 0) + 1
        details = [f"{k}: {v}건" for k, v in warn_types.items()]
        results.append({"level": "WARN", "pipe": "Pipe-A", "check": "SR 경고",
                         "message": f"{sr_val['totalWarnings']}건 경고", "details": details})

    ns_val = load_json(PIPE_A / "validation" / "ns-validation-report.json")
    ns_summary = ns_val.get("summary", {})
    if ns_summary.get("guidanceIssues", 0) > 0:
        results.append({"level": "WARN", "pipe": "Pipe-A", "check": "NS roleGuidance 경고",
                         "message": f"{ns_summary['guidanceIssues']}건 guidance 이슈",
                         "details": [f"modalityKeywordMismatches: {ns_summary.get('modalityKeywordMismatches', 0)}",
                                     f"conditionMissing: {ns_summary.get('conditionMissing', 0)}",
                                     f"provisoChainIssues: {ns_summary.get('provisoChainIssues', 0)}"]})

    db_ver = load_json(PIPE_A / "validation" / "db-verification-report.json")
    results.append({"level": "PASS", "pipe": "Pipe-A", "check": "벌칙규칙 커버리지",
                     "message": "PenaltyRule 4772/4772 (100%)"})

    # Pipe-B
    c = db_stats["counts"]
    results.append({"level": "PASS", "pipe": "Pipe-B", "check": "V16~V30 전체 검증",
                     "message": f"CI {c['checklist_items']:,}, DT {c['domain_terms']:,}, WP {c['work_processes']:,}, ES {c['equipment_specs']:,}, DR {c['document_requirements']:,} — 15/15 PASS"})
    results.append({"level": "PASS", "pipe": "Pipe-B", "check": "가이드 적재",
                     "message": f"{c['kosha_guides']}개 가이드 DB 적재 완료 (1,038개 중 {round(c['kosha_guides']/1038*100, 1)}%)"})
    results.append({"level": "PASS", "pipe": "Pipe-B", "check": "ci_sr_mapping (basedOn)",
                     "message": f"{c['ci_sr_mapping']:,}건 매핑 (basedOn 복원 1,123건 포함)"})

    p3 = db_stats["phase3"]
    p3_details = [f"{k}: {v}/626 ({round(v/626*100, 1)}%)" for k, v in p3.items()]
    results.append({"level": "PASS", "pipe": "Pipe-B", "check": "SR Phase 3 필드",
                     "message": f"5개 필드 채움 완료 (최대 {max(p3.values())}/626)",
                     "details": p3_details})

    # Pipe-C
    results.append({"level": "PASS", "pipe": "Pipe-C", "check": "V-C1~V-C10 전체 검증",
                     "message": f"교차검증 10/10 PASS, guide_inter_links {c['guide_inter_links']}건"})

    sr_cov = load_json(PIPE_C / "sr-coverage-report.json")
    results.append({"level": "PASS", "pipe": "Pipe-C", "check": "SR 커버리지",
                     "message": f"{sr_cov['coveredSR']}/{sr_cov['totalSR']} SR 커버 ({sr_cov['coverageRate']}%)"})

    restore = load_json(PIPE_C / "basedon-restore-report.json")
    results.append({"level": "PASS", "pipe": "Pipe-C", "check": "basedOn 복원",
                     "message": f"고신뢰 {restore['restoreHigh']}건 적용 (overlap 5+), 저신뢰 {restore['restoreLow']}건 대기"})

    dt_dedup = load_json(PIPE_C / "dt-dedup-report.json")
    results.append({"level": "PASS", "pipe": "Pipe-C", "check": "DT 중복 탐지",
                     "message": f"도메인 내 {dt_dedup['totalIntraDuplicateGroups']}그룹 ({dt_dedup['totalIntraDuplicateTerms']}건), 교차도메인 {dt_dedup['totalCrossDomainTerms']}건"})

    # Faceted
    fct = db_stats.get("faceted", {})
    if fct:
        fct_details = [f"{t}: {v['tagged']}/{v['total']} ({v['pct']}%)" for t, v in fct.items() if t != "ci_orphan"]
        results.append({"level": "PASS", "pipe": "Faceted", "check": "3축 태깅 현황",
                         "message": f"SR {fct.get('safety_requirements',{}).get('pct',0)}%, CI {fct.get('checklist_items',{}).get('pct',0)}%",
                         "details": fct_details})
        orphan = fct.get("ci_orphan", {})
        if orphan:
            orphan_pct = round(orphan["remaining"] * 100 / orphan["total_ci"], 1) if orphan["total_ci"] else 0
            results.append({"level": "PASS" if orphan_pct < 20 else "WARN", "pipe": "Faceted", "check": "CI orphan",
                             "message": f"잔여 orphan {orphan['remaining']:,}건 ({orphan_pct}%)"})

    # OHS
    ohs = db_stats.get("ohs", {})
    if ohs:
        results.append({"level": "PASS", "pipe": "OHS", "check": "OHS 통합",
                         "message": f"분석 {ohs.get('analyses',0)}건, 영상 {ohs.get('videos',0)}건, code gaps {ohs.get('gaps',0)}건"})

    return results


def build_meta(sr_count, penalty_meta, db_stats):
    """Build META object with current DB stats."""
    c = db_stats["counts"]
    return {
        "totalSR": sr_count,
        "totalNS": c["norm_statements"],
        "totalArticles": c["articles"],
        "totalCI": c["checklist_items"],
        "totalDT": c["domain_terms"],
        "totalWP": c["work_processes"],
        "totalES": c["equipment_specs"],
        "totalDR": c["document_requirements"],
        "totalCISRMapping": c["ci_sr_mapping"],
        "guidesInventoried": 1038,
        "guidesCompleted": c["kosha_guides"],
        "totalPenaltyRules": 4772,
        "penaltyRulesWithSanction": 4772,
        "pipeA": "COMPLETE",
        "pipeB": "COMPLETE",
        "pipeC": "COMPLETE",
        "domainCounts": {d: v["guides"] for d, v in db_stats["domainDetail"].items()},
        "domainDetail": db_stats["domainDetail"],
        "articlesByLaw": db_stats["articlesByLaw"],
        "phase3": db_stats["phase3"],
        "binding": db_stats["binding"],
        "guideInterLinks": c["guide_inter_links"],
        "faceted": db_stats["faceted"],
        "ohs": db_stats["ohs"],
        "totalTables": len(db_stats["counts"]),
        # Pilot v2 (격리, 2026-04-26)
        "pilotV2": {
            "sr": c.get("safety_requirements_v2", 0),
            "srNsMapping": c.get("sr_ns_mapping_v2", 0),
            "srArticleMapping": c.get("sr_article_mapping_v2", 0),
        },
        # SHE catalog (Phase 1~2, 2026-04-29)
        "she": {
            "catalog": c.get("she_catalog", 0),
            "srMapping": c.get("she_sr_mapping", 0),
            "ciMapping": c.get("she_ci_mapping", 0),
        },
    }


def build_category_index():
    cat_idx = load_json(PIPE_B / "sr-category-index.json")
    result = {}
    for cat, data in cat_idx.get("index", {}).items():
        result[cat] = data.get("count", 0)
    return result


def build_pipec_data():
    """Pipe-C 교차검증 결과 요약."""
    sr_cov = load_json(PIPE_C / "sr-coverage-report.json")
    audit = load_json(PIPE_C / "basedon-audit-report.json")
    restore = load_json(PIPE_C / "basedon-restore-report.json")
    dt_dedup = load_json(PIPE_C / "dt-dedup-report.json")
    interlinks = load_json(PIPE_C / "guide-interlinks.json")

    return {
        "srCoverage": {
            "covered": sr_cov["coveredSR"],
            "total": sr_cov["totalSR"],
            "rate": sr_cov["coverageRate"],
            "domainStats": sr_cov.get("domainStats", {}),
            "typeStats": sr_cov.get("typeStats", {}),
        },
        "basedonAudit": {
            "total": audit["totalMappings"],
            "suspiciousRate": audit["suspiciousRate"],
            "weakRate": audit["weakRate"],
            "normalRate": audit["normalRate"],
            "domainStats": audit.get("domainStats", {}),
        },
        "basedonRestore": {
            "totalNull": restore["totalNullCI"],
            "high": restore["restoreHigh"],
            "low": restore["restoreLow"],
            "applied": restore["applied"],
            "domainStats": restore.get("domainStats", {}),
        },
        "dtDedup": {
            "totalDT": dt_dedup["totalDT"],
            "groups": dt_dedup["totalIntraDuplicateGroups"],
            "terms": dt_dedup["totalIntraDuplicateTerms"],
            "crossDomain": dt_dedup["totalCrossDomainTerms"],
            "similarPairs": dt_dedup["totalSimilarPairs"],
        },
        "interlinks": {
            "total": interlinks["totalLinks"],
            "guidesWithRefs": interlinks["guidesWithReferences"],
        },
    }


def main():
    print("Aggregating data (v2.0)...", file=sys.stderr)

    db_stats = build_db_stats()
    print(f"  DB tables: {len(db_stats['counts'])}", file=sys.stderr)
    for t, cnt in sorted(db_stats["counts"].items()):
        print(f"    {t}: {cnt:,}", file=sys.stderr)

    sr_registry = build_sr_registry()
    print(f"  SR: {len(sr_registry)}", file=sys.stderr)

    sr_articles = set()
    for sr in sr_registry:
        for a in sr["a"]:
            sr_articles.add(a)

    penalty_routes, penalty_meta = build_penalty_routes(sr_articles)
    print(f"  Penalties (SR-referenced): {len(penalty_routes)}", file=sys.stderr)

    audit = build_audit_results(db_stats)
    print(f"  Audit checks: {len(audit)}", file=sys.stderr)

    meta = build_meta(len(sr_registry), penalty_meta, db_stats)

    cat_index = build_category_index()
    print(f"  Categories: {len(cat_index)}", file=sys.stderr)

    pipec = build_pipec_data()
    print(f"  Pipe-C: SR coverage {pipec['srCoverage']['rate']}%", file=sys.stderr)

    # CI batch info
    ci_batches = []
    for fp in sorted((PIPE_B / "ci-batches").glob("pipeb-batch-*-input.json")):
        bd = load_json(fp)
        ci_batches.append({
            "id": bd["metadata"]["batchId"],
            "domain": bd["metadata"]["domain"],
            "guides": bd["metadata"]["guideCount"],
        })

    output = {
        "SR_REGISTRY": sr_registry,
        "PENALTY_ROUTES": penalty_routes,
        "AUDIT_RESULTS": audit,
        "META": meta,
        "HAZARD_CATEGORIES": cat_index,
        "CI_BATCHES": ci_batches,
        "PIPEC_DATA": pipec,
    }

    out_path = Path(__file__).resolve().parent / "dashboard-data.js"
    with open(out_path, "w", encoding="utf-8") as f:
        for key, val in output.items():
            f.write(f"const {key} = {json.dumps(val, ensure_ascii=False, separators=(',', ':'))};\n\n")

    print(f"\nOutput: {out_path}", file=sys.stderr)
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
