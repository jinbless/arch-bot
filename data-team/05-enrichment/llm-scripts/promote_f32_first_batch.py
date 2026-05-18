#!/usr/bin/env python3
"""Quick win — F.3.2 first batch 8 candidates 수동 vetted 승격.

F.3.3 Gate 3 PASS (eb7843f) 검증된 8 axioms. 50회 자동 대기 불필요.
src='f32_axiom_miner' 필터로 정확히 8개만 promote.

사용:
  python promote_f32_first_batch.py            # dry-run
  python promote_f32_first_batch.py --apply
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path


def find_root() -> Path:
    for p in Path(__file__).resolve().parents:
        if (p / "data-team" / "05-enrichment" / "eval-data").is_dir():
            return p
    raise RuntimeError("root")


REPO = find_root()
KB_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json"
AUDIT_PATH = REPO / "data-team/05-enrichment/runtime-artifacts/incompatibility_audit.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    entries = data.get("incompatibilities", [])
    f32 = [e for e in entries if e.get("source") == "f32_axiom_miner" and e.get("incompatible")]
    f32_candidates = [e for e in f32 if e.get("level") == "candidate"]

    print(f"Found f32_axiom_miner entries: {len(f32)}")
    print(f"  level=candidate: {len(f32_candidates)}")
    print(f"  level=vetted   : {sum(1 for e in f32 if e.get('level') == 'vetted')}")
    print()

    if not f32_candidates:
        print("Nothing to promote.")
        return 0

    print("Will promote (set level=vetted):")
    for e in f32_candidates:
        print(f"  {e['domain_a']:35s} × {e['domain_b']:35s}  conf={e.get('confidence')}")

    if not args.apply:
        print("\n[dry-run] re-run with --apply to commit.")
        return 0

    ts = datetime.now(timezone.utc).isoformat()
    audit = []
    for e in f32_candidates:
        e["level"] = "vetted"
        e["promoted_at"] = ts
        e["promotion_reason"] = "f32_first_batch_manual_after_f33_gate3_pass"
        audit.append({
            "ts": ts, "action": "manual_promote",
            "domain_a": e["domain_a"], "domain_b": e["domain_b"],
            "confidence": e.get("confidence"),
            "reason": "f32_first_batch manual promote (F.3.3 Gate 3 PASS 검증됨)",
        })

    # Update header counts
    vetted_count = sum(1 for e in entries if e.get("incompatible") and e.get("level") == "vetted")
    candidate_count = sum(1 for e in entries if e.get("incompatible") and e.get("level") == "candidate")
    if "vetted_count" in data:
        data["vetted_count"] = vetted_count
    if "candidate_count" in data:
        data["candidate_count"] = candidate_count
    data["_last_promoted_at"] = ts

    # Atomic write
    tmp = KB_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(KB_PATH)

    # Audit append
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        for row in audit:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n✅ Promoted {len(f32_candidates)} F.3.2 candidates → vetted.")
    print(f"   KB: vetted={vetted_count}, candidate={candidate_count}")
    print(f"   Audit: {AUDIT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
