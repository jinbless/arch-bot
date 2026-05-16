#!/usr/bin/env python3
"""P2-Step 5: 추출 엔티티 검증 (B1~B20 규칙).

Usage:
    python3 scripts/step6_validate_entities.py
    python3 scripts/step6_validate_entities.py --input-dir data/ci-output
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import DATA_DIR, BATCHES_DIR, SCHEMA_DIR

CI_OUTPUT_DIR = DATA_DIR / "ci-output"
CI_SCHEMA_PATH = SCHEMA_DIR / "ci-file.schema.json"

# ── 유효 값 ──
VALID_BINDING = {"MANDATORY", "RECOMMENDED"}
VALID_REQ_TYPE = {
    "PHYSICAL_PROTECTION", "PPE_REQUIREMENT", "PROCEDURAL", "TRAINING",
    "EQUIPMENT_STANDARD", "ENVIRONMENTAL", "MANAGEMENT_SYSTEM", "EMERGENCY_RESPONSE",
    None,
}
VALID_DOC_TYPE = {
    "WORK_PLAN", "RISK_ASSESSMENT", "SAFETY_CHECKLIST",
    "MSDS", "INCIDENT_REPORT", "TRAINING_RECORD",
}
ID_PATTERNS = {
    "CI": re.compile(r"^CI-[A-Z0-9]+-[0-9]+$"),
    "DT": re.compile(r"^DT-[A-Z0-9]+-[0-9]+$"),
    "WP": re.compile(r"^WP-[A-Z0-9]+-[0-9]+$"),
    "ES": re.compile(r"^ES-[A-Z0-9]+-[0-9]+$"),
    "DR": re.compile(r"^DR-[A-Z0-9]+-[0-9]+$"),
}
SR_PATTERN = re.compile(r"^SR-[A-Z_]+-[0-9]+$")


def load_candidate_sr_map() -> dict:
    """배치 파일에서 가이드별 candidateSR 목록을 로드."""
    result = {}  # shortCode -> set of SR IDs
    for bp in sorted(BATCHES_DIR.glob("pipeb-*-input.json")):
        batch = json.loads(bp.read_text(encoding="utf-8"))
        for g in batch["guides"]:
            sc = g["shortCode"]
            sr_ids = {sr["id"] for sr in g.get("candidateSR", [])}
            result[sc] = sr_ids
    return result


def validate_file(data: dict, candidate_srs: set, short_code: str) -> dict:
    """단일 ci-output 파일을 B1~B20 규칙으로 검증."""
    hard_errors = []  # B1~B14
    soft_warnings = []  # B15~B20

    all_ids = set()
    sc = short_code

    # === B1: JSON Schema 검증 ===
    try:
        from jsonschema import Draft202012Validator
        schema = json.loads(CI_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for err in validator.iter_errors(data):
            path = ".".join(str(p) for p in err.absolute_path)
            hard_errors.append(f"B1 [{path}] {err.message}")
    except ImportError:
        pass

    # === B2: identifier 형식 검증 ===
    for entity_type, items_key in [
        ("CI", "checklistItems"), ("DT", "domainTerms"),
        ("WP", "workProcesses"), ("ES", "equipmentSpecs"),
        ("DR", "documentRequirements"),
    ]:
        for i, item in enumerate(data.get(items_key, [])):
            eid = item.get("identifier", "")
            if not ID_PATTERNS[entity_type].match(eid):
                hard_errors.append(f"B2 {items_key}[{i}]: invalid ID format '{eid}'")
            if eid in all_ids:
                hard_errors.append(f"B3 {items_key}[{i}]: duplicate ID '{eid}'")
            all_ids.add(eid)

            # B4: identifier가 해당 가이드 shortCode를 포함하는지
            if sc and f"-{sc}-" not in eid:
                hard_errors.append(f"B4 {items_key}[{i}]: ID '{eid}' does not contain shortCode '{sc}'")

    # === B5: basedOn이 candidateSR 범위 내인지 ===
    for i, ci in enumerate(data.get("checklistItems", [])):
        based_on = ci.get("basedOn")
        if based_on:
            for sr_id in based_on:
                if not SR_PATTERN.match(sr_id):
                    hard_errors.append(f"B5 CI[{i}]: invalid SR format in basedOn: '{sr_id}'")
                elif sr_id not in candidate_srs:
                    hard_errors.append(f"B5 CI[{i}]: basedOn SR '{sr_id}' not in candidateSR")

    # === B6: relatedSR 형식 + candidateSR 범위 검증 (DT/WP/ES/DR) ===
    for items_key in ["domainTerms", "workProcesses", "equipmentSpecs", "documentRequirements"]:
        for i, item in enumerate(data.get(items_key, [])):
            related = item.get("relatedSR")
            if related:
                for sr_id in related:
                    if not SR_PATTERN.match(sr_id):
                        hard_errors.append(f"B6 {items_key}[{i}]: invalid SR format in relatedSR: '{sr_id}'")
                    elif sr_id not in candidate_srs:
                        hard_errors.append(f"B6 {items_key}[{i}]: relatedSR '{sr_id}' not in candidateSR")

    # === B7: bindingForce 값 검증 ===
    for i, ci in enumerate(data.get("checklistItems", [])):
        if ci.get("bindingForce") not in VALID_BINDING:
            hard_errors.append(f"B7 CI[{i}]: invalid bindingForce '{ci.get('bindingForce')}'")

    # === B8: requirementType 값 검증 ===
    for i, ci in enumerate(data.get("checklistItems", [])):
        rt = ci.get("requirementType")
        if rt not in VALID_REQ_TYPE:
            hard_errors.append(f"B8 CI[{i}]: invalid requirementType '{rt}'")

    # === B9: documentType 값 검증 ===
    for i, dr in enumerate(data.get("documentRequirements", [])):
        dt = dr.get("documentType")
        if dt not in VALID_DOC_TYPE:
            hard_errors.append(f"B9 DR[{i}]: invalid documentType '{dt}'")

    # === B10: 빈 문자열 금지 (minLength:1 필드) ===
    min_len_fields = {
        "checklistItems": ["text", "sourceSection"],
        "domainTerms": ["term", "definition", "sourceSection"],
        "workProcesses": ["processName", "sourceSection"],
        "equipmentSpecs": ["equipmentName", "sourceSection"],
        "documentRequirements": ["title", "sourceSection"],
    }
    for items_key, fields in min_len_fields.items():
        for i, item in enumerate(data.get(items_key, [])):
            for field in fields:
                val = item.get(field)
                if val is not None and isinstance(val, str) and len(val) == 0:
                    hard_errors.append(f"B10 {items_key}[{i}]: empty string in '{field}'")

    # === B11: metadata 필수 필드 ===
    meta = data.get("metadata", {})
    for field in ["guideCode", "shortCode", "domain"]:
        if not meta.get(field):
            hard_errors.append(f"B11 metadata.{field} 누락")

    # === B12: domain 유효 값 ===
    if meta.get("domain") not in {"A", "B", "C", "D", "E"}:
        hard_errors.append(f"B12 metadata.domain invalid: '{meta.get('domain')}'")

    # === B13: WP.processOrder 양수 정수 ===
    for i, wp in enumerate(data.get("workProcesses", [])):
        po = wp.get("processOrder")
        if not isinstance(po, int) or po < 1:
            hard_errors.append(f"B13 WP[{i}]: processOrder must be positive int, got '{po}'")

    # === B14: ES.specifications가 빈 객체 ===
    for i, es in enumerate(data.get("equipmentSpecs", [])):
        specs = es.get("specifications")
        if specs is not None and isinstance(specs, dict) and len(specs) == 0:
            hard_errors.append(f"B14 ES[{i}]: specifications is empty object {{}}")

    # ── Soft Warnings (B15~B20) ──

    # B15: CI가 0건인 가이드
    ci_count = len(data.get("checklistItems", []))
    if ci_count == 0:
        soft_warnings.append(f"B15 CI 0건 — 가이드에 점검항목이 없음")

    # B16: MANDATORY CI 중 basedOn null 비율
    mandatory = [ci for ci in data.get("checklistItems", []) if ci.get("bindingForce") == "MANDATORY"]
    mandatory_no_based = [ci for ci in mandatory if not ci.get("basedOn")]
    if mandatory and len(mandatory_no_based) / len(mandatory) > 0.5:
        soft_warnings.append(f"B16 MANDATORY CI 중 basedOn null {len(mandatory_no_based)}/{len(mandatory)} ({len(mandatory_no_based)/len(mandatory)*100:.0f}%)")

    # B17: DT 0건
    if len(data.get("domainTerms", [])) == 0:
        soft_warnings.append(f"B17 DT 0건")

    # B18: WP 0건
    if len(data.get("workProcesses", [])) == 0:
        soft_warnings.append(f"B18 WP 0건")

    # B19: candidateSR 매칭률 (basedOn 배열에 사용된 SR 수 / candidateSR 수)
    used_srs = set()
    for ci in data.get("checklistItems", []):
        for sr in (ci.get("basedOn") or []):
            used_srs.add(sr)
    if candidate_srs:
        match_rate = len(used_srs & candidate_srs) / len(candidate_srs) * 100
        if match_rate < 10:
            soft_warnings.append(f"B19 candidateSR 매칭률 {match_rate:.0f}% (사용 {len(used_srs)}/{len(candidate_srs)})")

    # B20: CI 텍스트 평균 길이가 너무 짧으면 경고
    if ci_count > 0:
        avg_len = sum(len(ci.get("text", "")) for ci in data["checklistItems"]) / ci_count
        if avg_len < 10:
            soft_warnings.append(f"B20 CI 텍스트 평균 길이 {avg_len:.0f}자 — 너무 짧음")

    return {
        "shortCode": sc,
        "hardErrors": hard_errors,
        "softWarnings": soft_warnings,
        "counts": {
            "CI": ci_count,
            "DT": len(data.get("domainTerms", [])),
            "WP": len(data.get("workProcesses", [])),
            "ES": len(data.get("equipmentSpecs", [])),
            "DR": len(data.get("documentRequirements", [])),
        },
        "mandatoryCI": len(mandatory),
        "mandatoryNoBasedOn": len(mandatory_no_based),
        "usedSR": len(used_srs),
        "candidateSR": len(candidate_srs),
    }


def main():
    parser = argparse.ArgumentParser(description="추출 엔티티 검증 (B1~B20)")
    parser.add_argument("--input-dir", type=str, default="data/ci-output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = DATA_DIR.parent / args.input_dir

    print("[START] 엔티티 검증 (B1~B20)")

    # candidateSR 맵 로드
    candidate_map = load_candidate_sr_map()
    print(f"  candidateSR 로드: {len(candidate_map)}개 가이드")

    # ci-output 파일 수집
    ci_files = sorted(input_dir.glob("ci-*.json"))
    ci_files = [f for f in ci_files
                if not f.name.endswith("-raw-response.txt")
                and not f.name.endswith(".split-meta.json")]
    print(f"  CI output 파일: {len(ci_files)}개\n")

    results = []
    total_hard = 0
    total_soft = 0
    global_ids = {}  # id → shortCode (크로스 파일 중복 검사용)

    for fp in ci_files:
        sc = fp.stem.replace("ci-", "")
        data = json.loads(fp.read_text(encoding="utf-8"))
        candidate_srs = candidate_map.get(sc, set())

        result = validate_file(data, candidate_srs, sc)

        # 크로스 파일 ID 중복 검사
        for items_key in ["checklistItems", "domainTerms", "workProcesses", "equipmentSpecs", "documentRequirements"]:
            for item in data.get(items_key, []):
                eid = item.get("identifier", "")
                if eid in global_ids and global_ids[eid] != sc:
                    result["hardErrors"].append(f"B3X cross-file duplicate ID '{eid}' (also in {global_ids[eid]})")
                global_ids[eid] = sc

        results.append(result)

        n_hard = len(result["hardErrors"])
        n_soft = len(result["softWarnings"])
        total_hard += n_hard
        total_soft += n_soft

        status = "PASS" if n_hard == 0 else f"FAIL({n_hard})"
        warn = f" WARN({n_soft})" if n_soft > 0 else ""
        counts = result["counts"]
        print(f"  [{sc:8s}] {status:10s}{warn}  CI={counts['CI']} DT={counts['DT']} WP={counts['WP']} ES={counts['ES']} DR={counts['DR']}")

        if n_hard > 0:
            for e in result["hardErrors"][:5]:
                print(f"           → {e}")
            if n_hard > 5:
                print(f"           → ... +{n_hard - 5}건")

    # 결과 요약
    passed = sum(1 for r in results if len(r["hardErrors"]) == 0)
    failed = len(results) - passed

    print(f"\n[DONE] 검증 완료")
    print(f"  PASS: {passed}  FAIL: {failed}")
    print(f"  Hard errors: {total_hard}  Soft warnings: {total_soft}")

    total_ci = sum(r["counts"]["CI"] for r in results)
    total_dt = sum(r["counts"]["DT"] for r in results)
    total_wp = sum(r["counts"]["WP"] for r in results)
    total_es = sum(r["counts"]["ES"] for r in results)
    total_dr = sum(r["counts"]["DR"] for r in results)
    print(f"  총 엔티티: CI={total_ci} DT={total_dt} WP={total_wp} ES={total_es} DR={total_dr}")

    # 보고서 저장
    report = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalFiles": len(results),
        "passed": passed,
        "failed": failed,
        "totalHardErrors": total_hard,
        "totalSoftWarnings": total_soft,
        "results": results,
    }
    report_path = DATA_DIR / "entity-validation-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"  보고서: {report_path}")


if __name__ == "__main__":
    main()
