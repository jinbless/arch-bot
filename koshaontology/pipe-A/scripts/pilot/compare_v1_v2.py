#!/usr/bin/env python3
"""Step 6: v1 vs v2 비교 리포트 + 게이트 G1~G4 평가.

생성 파일: pipe-A/data/pilot/reports/comparison.md
콘솔 요약 + PASS/FAIL 게이트 출력.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

PIPE_A_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPE_A_ROOT / "data"
PILOT_DIR = DATA_DIR / "pilot"
REPORT_DIR = PILOT_DIR / "reports"

PG_CONNINFO = "dbname=kosha user=kosha password=1229 host=localhost"


def load_sample_articles() -> list[str]:
    data = json.loads((PILOT_DIR / "sample-articles.json").read_text(encoding="utf-8"))
    return [s["articleCode"] for s in data["samples"]]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sample_codes = load_sample_articles()
    placeholder = ", ".join(["%s"] * len(sample_codes))

    md: list[str] = ["# Multi-SR Pilot 비교 리포트 (v1 vs v2)", ""]
    md.append(f"- 생성: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"- Sample articles: {sample_codes}")
    md.append("")

    with psycopg2.connect(PG_CONNINFO) as conn:
        cur = conn.cursor()

        # ── 1. SR 수 비교 (sample article 한정) ──
        cur.execute(f"""SELECT COUNT(DISTINCT sr_id) FROM sr_article_mapping
                        WHERE article_code IN ({placeholder})""", sample_codes)
        v1_sr_total = cur.fetchone()[0]
        cur.execute(f"""SELECT COUNT(DISTINCT sr_id) FROM sr_article_mapping_v2
                        WHERE article_code IN ({placeholder})""", sample_codes)
        v2_sr_total = cur.fetchone()[0]

        md.append("## 1. SR 수 (sample 10 article 한정)")
        md.append(f"- v1: **{v1_sr_total}** SR")
        md.append(f"- v2: **{v2_sr_total}** SR  (배수: {v2_sr_total / max(1, v1_sr_total):.1f}x)")
        md.append("")

        # ── 2. article별 multi-SR 분포 ──
        md.append("## 2. Article별 SR 수 (v1 vs v2)")
        md.append("| Article | v1 | v2 | 분리율 |")
        md.append("|---|---:|---:|---:|")
        cur.execute(f"""
            SELECT a.article_code,
                   COALESCE(v1.cnt, 0) AS v1_cnt,
                   COALESCE(v2.cnt, 0) AS v2_cnt
            FROM (SELECT DISTINCT article_code FROM sr_article_mapping_v2
                  WHERE article_code IN ({placeholder})) a
            LEFT JOIN (SELECT article_code, COUNT(DISTINCT sr_id) cnt
                       FROM sr_article_mapping GROUP BY article_code) v1
              ON a.article_code = v1.article_code
            LEFT JOIN (SELECT article_code, COUNT(DISTINCT sr_id) cnt
                       FROM sr_article_mapping_v2 GROUP BY article_code) v2
              ON a.article_code = v2.article_code
            ORDER BY v2_cnt DESC, a.article_code
        """, sample_codes)
        rows = cur.fetchall()
        multi_sr_articles = 0
        for ac, v1c, v2c in rows:
            ratio = v2c / max(1, v1c)
            md.append(f"| {ac} | {v1c} | {v2c} | {ratio:.1f}x |")
            if v2c >= 2:
                multi_sr_articles += 1
        md.append("")
        g1_rate = multi_sr_articles / max(1, len(rows))
        md.append(f"**G1 (Multi-SR 발생률)**: {multi_sr_articles}/{len(rows)} = **{g1_rate:.0%}** "
                  f"(기준: ≥ 80%) — **{'PASS' if g1_rate >= 0.8 else 'FAIL'}**")
        md.append("")

        # ── 3. coApplicable 후보 쌍 ──
        cur.execute("""
            SELECT a.sr_id sr1, b.sr_id sr2, a.article_code
            FROM sr_article_mapping_v2 a
            JOIN sr_article_mapping_v2 b USING(article_code)
            WHERE a.sr_id < b.sr_id ORDER BY a.article_code, a.sr_id
        """)
        pairs = cur.fetchall()
        md.append(f"## 3. coApplicable 후보 쌍 (G3)")
        md.append(f"- 총 후보 쌍: **{len(pairs)}**")
        md.append(f"- 기준 (G3): ≥ 2 × multi-SR article 수 = ≥ **{2 * multi_sr_articles}**")
        g3_pass = len(pairs) >= 2 * multi_sr_articles
        md.append(f"- **{'PASS' if g3_pass else 'FAIL'}**")
        md.append("")
        md.append("샘플 5쌍:")
        for sr1, sr2, ac in pairs[:5]:
            md.append(f"- `{sr1}` ↔ `{sr2}` (article {ac})")
        md.append("")

        # ── 4. Title trigram similarity (G2 의미 분리도) ──
        cur.execute("""
            SELECT a.sr_id, b.sr_id, similarity(s1.title, s2.title) AS sim, a.article_code
            FROM sr_article_mapping_v2 a
            JOIN sr_article_mapping_v2 b USING(article_code)
            JOIN safety_requirements_v2 s1 ON s1.identifier = a.sr_id
            JOIN safety_requirements_v2 s2 ON s2.identifier = b.sr_id
            WHERE a.sr_id < b.sr_id
            ORDER BY sim DESC
        """)
        sim_rows = cur.fetchall()
        sims = [r[2] for r in sim_rows if r[2] is not None]
        avg_sim = sum(sims) / len(sims) if sims else 0
        max_sim = max(sims) if sims else 0
        high_sim_count = sum(1 for s in sims if s and s > 0.7)

        md.append("## 4. Title Trigram Similarity (G2)")
        md.append(f"- 평균: **{avg_sim:.3f}** (기준: < 0.4)")
        md.append(f"- 최대: {max_sim:.3f}")
        md.append(f"- > 0.7 쌍 (의심 인위 분할): {high_sim_count}건")
        md.append("")
        md.append("최고 유사도 5쌍:")
        for sr1, sr2, sim, ac in sim_rows[:5]:
            md.append(f"- `{sr1}` ↔ `{sr2}` ({ac}): {sim:.3f}" if sim is not None else f"- `{sr1}` ↔ `{sr2}` (NULL)")
        md.append("")

        # ── 5. NS 중복 검사 (R12V2) ──
        cur.execute("""
            SELECT n.ns_id, COUNT(DISTINCT n.sr_id) cnt, ARRAY_AGG(DISTINCT n.sr_id) srs
            FROM sr_ns_mapping_v2 n
            GROUP BY n.ns_id HAVING COUNT(DISTINCT n.sr_id) > 1
        """)
        ns_dup = cur.fetchall()
        md.append(f"## 5. NS 중복 검사 (paragraph 무결성)")
        md.append(f"- 같은 NS가 여러 SR에 들어간 케이스: **{len(ns_dup)}** (기준: 0)")
        md.append("")

        # ── 6. Hazard 다양성 (G2 보조) ──
        cur.execute("""
            SELECT m.article_code,
                   COUNT(DISTINCT s.identifier) sr_cnt,
                   COUNT(DISTINCT (s.addresses_hazard::text)) distinct_hazards
            FROM sr_article_mapping_v2 m
            JOIN safety_requirements_v2 s ON s.identifier = m.sr_id
            GROUP BY m.article_code
            ORDER BY sr_cnt DESC
        """)
        haz_rows = cur.fetchall()
        md.append(f"## 6. Article별 Hazard 다양성")
        md.append("| Article | SR 수 | distinct hazard set |")
        md.append("|---|---:|---:|")
        for ac, src, dh in haz_rows:
            md.append(f"| {ac} | {src} | {dh} |")
        md.append("")

        # ── 7. v1 ↔ v2 SR mapping (NS 교집합 기반) ──
        md.append("## 7. v1 SR ↔ v2 SR 매핑 (sample article 한정, NS 공유 기반)")
        cur.execute(f"""
            SELECT v1m.sr_id v1_sr, v2m.sr_id v2_sr, v1m.ns_id
            FROM sr_ns_mapping v1m
            JOIN sr_ns_mapping_v2 v2m ON v1m.ns_id = v2m.ns_id
            WHERE v1m.sr_id IN (
              SELECT DISTINCT sr_id FROM sr_article_mapping
              WHERE article_code IN ({placeholder})
            )
            ORDER BY v1m.sr_id, v2m.sr_id
        """, sample_codes)
        mapping = cur.fetchall()
        v1_to_v2: dict[str, set[str]] = {}
        for v1, v2, _ns in mapping:
            v1_to_v2.setdefault(v1, set()).add(v2)
        md.append("| v1 SR | v2 SR 분리 수 | v2 SR ID들 |")
        md.append("|---|---:|---|")
        for v1, v2set in sorted(v1_to_v2.items()):
            md.append(f"| `{v1}` | {len(v2set)} | {', '.join(sorted(v2set))} |")
        md.append("")

        # ── 8. v1 무손상 (G4) ──
        cur.execute("SELECT COUNT(*) FROM safety_requirements")
        v1_total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sr_article_mapping")
        v1_art_map = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ci_sr_mapping")
        ci_map = cur.fetchone()[0]
        md.append("## 8. v1 무손상 + 하류 호환성 (G4)")
        md.append(f"- v1 safety_requirements: **{v1_total}** (기대: 626) — {'PASS' if v1_total == 626 else 'FAIL'}")
        md.append(f"- v1 sr_article_mapping: **{v1_art_map}** (기대: 626) — {'PASS' if v1_art_map == 626 else 'FAIL'}")
        md.append(f"- ci_sr_mapping: **{ci_map}** (Pipe-B 미접촉 — Pipe-B 적재 직후 값 그대로)")
        g4_pass = v1_total == 626 and v1_art_map == 626

        # ── 게이트 종합 ──
        g2_pass = avg_sim < 0.4 and len(ns_dup) == 0
        g3_pass_final = len(pairs) >= 2 * multi_sr_articles

        md.append("")
        md.append("---")
        md.append("## 종합 게이트")
        md.append("| 게이트 | 결과 | 값 |")
        md.append("|---|---|---|")
        md.append(f"| G1. Multi-SR 발생률 ≥ 80% | {'PASS' if g1_rate >= 0.8 else 'FAIL'} | {g1_rate:.0%} |")
        md.append(f"| G2. title sim 평균 < 0.4 AND NS 중복 = 0 | {'PASS' if g2_pass else 'FAIL'} | sim={avg_sim:.3f}, dup={len(ns_dup)} |")
        md.append(f"| G3. coApplicable 후보 ≥ 2 × multi-SR article | {'PASS' if g3_pass_final else 'FAIL'} | {len(pairs)} ≥ {2 * multi_sr_articles} |")
        md.append(f"| G4. v1 무손상 + 하류 미접촉 | {'PASS' if g4_pass else 'FAIL'} | v1 SR={v1_total}/626 |")
        md.append("")
        all_pass = g1_rate >= 0.8 and g2_pass and g3_pass_final and g4_pass
        md.append(f"## **종합 판정: {'GO (전체 626 SR 재생성 진행)' if all_pass else 'NO-GO (재pilot 또는 chunking 재검토)'}**")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / "comparison.md"
    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n[OK] saved: {out_path}")

    print("\n" + "=" * 60)
    print(f"[G1] Multi-SR 발생률: {g1_rate:.0%} ({multi_sr_articles}/{len(rows)})  → {'PASS' if g1_rate >= 0.8 else 'FAIL'}")
    print(f"[G2] title sim 평균: {avg_sim:.3f}, NS 중복: {len(ns_dup)}        → {'PASS' if g2_pass else 'FAIL'}")
    print(f"[G3] coApplicable 후보: {len(pairs)} (≥ {2 * multi_sr_articles})        → {'PASS' if g3_pass_final else 'FAIL'}")
    print(f"[G4] v1 무손상 (SR={v1_total}/626)                       → {'PASS' if g4_pass else 'FAIL'}")
    print("=" * 60)
    print(f"종합: {'GO' if all_pass else 'NO-GO'}")


if __name__ == "__main__":
    main()
