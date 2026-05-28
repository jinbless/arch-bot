#!/usr/bin/env python3
"""Phase I — F.3.2 candidate 자동 batch promotion (self-contained).

Plan B Phase I + Sprint C 보강 절차:
- KB JSON (guide_domain_incompatibilities.json) 의 candidate 중 confidence ≥ --min-conf
  자동 batch promotion (1-by-1 Gate 3 wrap, per_candidate 의존성 제거).
- Gate 3 PASS → vetted 유지 + SHACL constraint ttl append (sh:Info severity).
- Gate 3 FAIL → KB rollback (해당 candidate만).
- LLM call 없음 (기존 confidence 활용).

본 sprint 정착된 SHACL constraint 패턴 (R-27 + Phase G allValuesFrom + R-14~R-30 SHACL):
- Pellet OWL DL 영향 0 (SHACL은 raw triple로 취급)
- pyshacl shadow check에서 reporting (sh:Info severity)
- AC-4 (< 100 candidate) 충족 + Pellet 부담 회피

사용:
  # Dry-run (실행 시뮬레이션, KB 변경 X)
  python promote_f32_auto_batch.py --min-conf 0.85

  # 실제 1 batch (50 candidate, 5-15분/batch)
  python promote_f32_auto_batch.py --apply --max-batches 1

  # 전체 batch (1,272 candidate, ~6-7시간)
  python promote_f32_auto_batch.py --apply --min-conf 0.85

산출:
- KB 갱신: candidate level → vetted
- SHACL ttl append: kosha-vetted-disjoint-shapes.ttl (sh:NodeShape sh:Info)
- summary: f32_auto_batch_results.json
- audit: incompatibility_audit.jsonl
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("Cannot locate repo root")


REPO = _find_root()
KB_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"
RESULTS_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/f32_auto_batch_results.json"
AUDIT_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/incompatibility_audit.jsonl"
SHACL_OUT = REPO / "ontology-team/06-reasoning/ontology/kosha-vetted-disjoint-shapes.ttl"

DEFAULT_BASELINE = REPO / "data-team/05-enrichment/runtime-artifacts/replay_baseline.json"
REPLAY_SCRIPT = REPO / "serving-team/08-app/backend/scripts/replay_synthetic_observations.py"
REGRESSION_SCRIPT = REPO / "serving-team/08-app/backend/scripts/regression_gate.py"
BACKEND_VENV_PY = REPO / "serving-team/08-app/backend/.venv/Scripts/python.exe"


def load_kb() -> dict:
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def save_kb(data: dict) -> None:
    tmp = KB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(KB_PATH)


def find_eligible_candidates(data: dict, min_conf: float) -> list[tuple[int, dict]]:
    """level=candidate (source != self_refine) + confidence >= min_conf."""
    entries = data.get("incompatibilities", [])
    eligible = []
    for idx, e in enumerate(entries):
        if (e.get("incompatible")
                and e.get("level") == "candidate"
                and e.get("source") != "self_refine"
                and float(e.get("confidence", 0.0)) >= min_conf):
            eligible.append((idx, e))
    return eligible


def append_audit(rows: list[dict]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_shacl_shape(entry: dict, batch_idx: int) -> str:
    """SHACL sh:Info shape 생성 후 SHACL_OUT에 append."""
    SHACL_OUT.parent.mkdir(parents=True, exist_ok=True)
    if not SHACL_OUT.exists():
        # 헤더 생성
        SHACL_OUT.write_text(_shacl_header(), encoding="utf-8")

    da = entry.get("domain_a", "?").replace(".", "_")
    db = entry.get("domain_b", "?").replace(".", "_")
    conf = entry.get("confidence", 0.0)
    pair_id = f"V_{da}__{db}"
    shape = f"""
kb:Shape_{pair_id} a sh:NodeShape ;
    rdfs:comment "Sprint C vetted incompatibility (conf={conf:.2f}, batch={batch_idx}): {da} x {db}"@ko ;
    sh:message "Vetted incompatible: {da} x {db}"@ko ;
    sh:severity sh:Info ;
    kb:confidence {conf:.6e} ;
    kb:domainA industry:Industry_{da} ;
    kb:domainB industry:Industry_{db} ;
    kb:level "vetted" .
"""
    with SHACL_OUT.open("a", encoding="utf-8") as f:
        f.write(shape)
    return pair_id


def _shacl_header() -> str:
    return """# Sprint C — F.3.2 vetted disjoint SHACL constraints (sh:Info severity).
#
# Sprint A-2 정착된 SHACL constraint 패턴으로 vetted disjoint를 표현.
# Pellet OWL DL 영향 없음 (raw triple로만 취급).
# pyshacl shadow check에서 sh:Info severity로 reporting.
#
# 각 shape은 batch promotion 시 자동 append (auto_batch.py).

@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix industry: <https://cashtoss.info/ontology/industry#> .
@prefix kb: <https://kosha.example/kb-candidate#> .

"""


def run_gate3(baseline: str | None, tolerance: float) -> tuple[bool, str]:
    """Backend Gate 3 replay + regression_gate. Returns (PASS bool, output)."""
    if not BACKEND_VENV_PY.exists():
        return (False, f"backend venv not found: {BACKEND_VENV_PY}")
    if not REPLAY_SCRIPT.exists() or not REGRESSION_SCRIPT.exists():
        return (False, f"backend scripts missing")

    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
        replay_out = Path(tf.name)

    # 1. replay
    cmd_replay = [str(BACKEND_VENV_PY), str(REPLAY_SCRIPT), "--output", str(replay_out)]
    p1 = subprocess.run(cmd_replay, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", cwd=str(REPLAY_SCRIPT.parent.parent))
    if p1.returncode != 0:
        return (False, f"replay failed: {p1.stderr[-300:]}")

    # 2. regression_gate
    cmd_gate = [str(BACKEND_VENV_PY), str(REGRESSION_SCRIPT), str(replay_out)]
    if baseline:
        cmd_gate.extend(["--baseline", baseline])
    cmd_gate.extend(["--tolerance", str(tolerance)])
    p2 = subprocess.run(cmd_gate, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", cwd=str(REGRESSION_SCRIPT.parent.parent))
    output = p2.stdout + (p2.stderr if p2.stderr else "")
    return (p2.returncode == 0, output)


def main():
    parser = argparse.ArgumentParser(description="F.3.2 candidate self-contained batch promotion (Sprint C)")
    parser.add_argument("--apply", action="store_true",
                        help="실제 KB 변경 + Gate 3 + SHACL append. 기본은 dry-run.")
    parser.add_argument("--min-conf", type=float, default=0.85)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--baseline", type=str, default=None)
    parser.add_argument("--tolerance", type=float, default=0.02)
    parser.add_argument("--max-batches", type=int, default=None,
                        help="제한 (debug). None이면 전체.")
    parser.add_argument("--gate3-mode", choices=["per-candidate", "batch", "skip"], default="batch",
                        help="Gate 3 frequency: per-candidate (8min/cand), batch (8min/batch, default), skip (KB transition + SHACL append only)")
    args = parser.parse_args()

    if not KB_PATH.exists():
        print(f"ERROR: KB not found: {KB_PATH}", file=sys.stderr)
        sys.exit(1)

    data = load_kb()
    eligible = find_eligible_candidates(data, args.min_conf)
    total = len(eligible)
    n_batches = (total + args.batch_size - 1) // args.batch_size

    print(f"=== F.3.2 self-contained auto-batch ({datetime.now().isoformat()}) ===")
    print(f"KB: {KB_PATH}")
    print(f"min-conf: {args.min_conf}, batch-size: {args.batch_size}")
    print(f"Eligible: {total}, planned batches: {n_batches}")

    if not args.apply:
        print(f"\n[DRY-RUN]")
        print("Top 5 by confidence:")
        sorted_e = sorted(eligible, key=lambda t: -float(t[1].get("confidence", 0.0)))
        for idx, e in sorted_e[:5]:
            print(f"  [{idx}] conf={e['confidence']:.3f} {e.get('domain_a', '?')} x {e.get('domain_b', '?')}")
        print(f"\nRe-run with --apply (1 batch ~ 5-15min Gate 3, 전체 1,272 ~ 6-7시간)")
        sys.exit(0)

    # Real execution
    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "min_conf": args.min_conf,
        "batch_size": args.batch_size,
        "total_eligible": total,
        "batches": [],
    }

    batches = [eligible[i:i + args.batch_size] for i in range(0, total, args.batch_size)]
    if args.max_batches is not None:
        batches = batches[:args.max_batches]

    baseline_path = args.baseline or str(DEFAULT_BASELINE)

    promoted = 0
    rolled_back = 0
    audit_rows = []

    for bi, batch in enumerate(batches, 1):
        print(f"\n--- Batch {bi}/{len(batches)} ({len(batch)} candidates) ---")
        batch_record = {
            "batch_index": bi,
            "size": len(batch),
            "candidates": [(idx, e.get("domain_a"), e.get("domain_b"), e.get("confidence")) for idx, e in batch],
            "promoted": 0,
            "rolled_back": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if args.gate3_mode == "per-candidate":
            # 1-by-1 Gate 3 (느림: 8min × N)
            for idx, entry in batch:
                entry_before = copy.deepcopy(data["incompatibilities"][idx])
                data["incompatibilities"][idx]["level"] = "vetted"
                data["incompatibilities"][idx]["source"] = entry.get("source") or "f32_auto_batch"
                save_kb(data)
                t0 = time.time()
                ok, out = run_gate3(baseline_path, args.tolerance)
                elapsed = time.time() - t0
                if ok:
                    promoted += 1
                    batch_record["promoted"] += 1
                    pair_id = append_shacl_shape(data["incompatibilities"][idx], bi)
                    audit_rows.append({"ts": datetime.now(timezone.utc).isoformat(), "action": "auto_batch_promote",
                                       "idx": idx, "domain_a": entry.get("domain_a"), "domain_b": entry.get("domain_b"),
                                       "confidence": entry.get("confidence"), "shacl_shape": pair_id,
                                       "gate3_elapsed_sec": round(elapsed, 1)})
                    print(f"  [{idx}] PROMOTED  conf={entry['confidence']:.2f}  ({elapsed:.1f}s)")
                else:
                    data["incompatibilities"][idx] = entry_before
                    save_kb(data)
                    rolled_back += 1
                    batch_record["rolled_back"] += 1
                    audit_rows.append({"ts": datetime.now(timezone.utc).isoformat(), "action": "auto_batch_rollback",
                                       "idx": idx, "reason": "gate3_fail",
                                       "gate3_output_tail": out[-300:] if out else "",
                                       "gate3_elapsed_sec": round(elapsed, 1)})
                    print(f"  [{idx}] ROLLBACK  Gate 3 FAIL")
        elif args.gate3_mode == "batch":
            # Batch-level Gate 3 (8min per batch)
            backup = copy.deepcopy(data)
            transitioned = []
            for idx, entry in batch:
                data["incompatibilities"][idx]["level"] = "vetted"
                data["incompatibilities"][idx]["source"] = entry.get("source") or "f32_auto_batch"
                transitioned.append((idx, entry))
            save_kb(data)
            t0 = time.time()
            ok, out = run_gate3(baseline_path, args.tolerance)
            elapsed = time.time() - t0
            if ok:
                for idx, entry in transitioned:
                    promoted += 1
                    pair_id = append_shacl_shape(data["incompatibilities"][idx], bi)
                    audit_rows.append({"ts": datetime.now(timezone.utc).isoformat(), "action": "auto_batch_promote",
                                       "idx": idx, "domain_a": entry.get("domain_a"), "domain_b": entry.get("domain_b"),
                                       "confidence": entry.get("confidence"), "shacl_shape": pair_id,
                                       "gate3_elapsed_sec": round(elapsed, 1), "gate3_mode": "batch"})
                batch_record["promoted"] = len(transitioned)
                print(f"  Batch {bi}: {len(transitioned)} promoted (Gate 3 PASS, {elapsed:.1f}s)")
            else:
                # Full batch rollback
                data = backup
                save_kb(data)
                rolled_back += len(transitioned)
                batch_record["rolled_back"] = len(transitioned)
                audit_rows.append({"ts": datetime.now(timezone.utc).isoformat(), "action": "auto_batch_rollback",
                                   "batch_index": bi, "reason": "gate3_fail",
                                   "gate3_output_tail": out[-300:] if out else "",
                                   "gate3_elapsed_sec": round(elapsed, 1)})
                print(f"  Batch {bi}: {len(transitioned)} rolled back (Gate 3 FAIL, {elapsed:.1f}s)")
        else:  # skip
            # KB + SHACL transition only, no Gate 3 (mitigation 패턴 일관: SHACL constraint는 Pellet 영향 0)
            for idx, entry in batch:
                data["incompatibilities"][idx]["level"] = "vetted"
                data["incompatibilities"][idx]["source"] = entry.get("source") or "f32_auto_batch"
                pair_id = append_shacl_shape(data["incompatibilities"][idx], bi)
                promoted += 1
                audit_rows.append({"ts": datetime.now(timezone.utc).isoformat(), "action": "auto_batch_promote_no_gate3",
                                   "idx": idx, "domain_a": entry.get("domain_a"), "domain_b": entry.get("domain_b"),
                                   "confidence": entry.get("confidence"), "shacl_shape": pair_id})
            save_kb(data)
            batch_record["promoted"] = len(batch)
            print(f"  Batch {bi}: {len(batch)} promoted (Gate 3 skip)")

        batch_record["finished_at"] = datetime.now(timezone.utc).isoformat()
        summary["batches"].append(batch_record)

    append_audit(audit_rows)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["total_promoted"] = promoted
    summary["total_rolled_back"] = rolled_back

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== DONE ===")
    print(f"Promoted: {promoted}, Rolled back: {rolled_back}")
    print(f"Results: {RESULTS_PATH}")
    print(f"SHACL: {SHACL_OUT}")
    print(f"Audit: {AUDIT_PATH}")


if __name__ == "__main__":
    main()
