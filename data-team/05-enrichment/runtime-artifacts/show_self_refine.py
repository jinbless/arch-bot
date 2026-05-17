"""Show 31 self-refined incompatibility pairs from Phase C.2."""
import json
from pathlib import Path

d = json.loads(
    Path("/mnt/c/project/arch-bot/data-team/05-enrichment/runtime-artifacts/guide_domain_incompatibilities.json").read_text(encoding="utf-8")
)
self_refine = [e for e in d["incompatibilities"] if e.get("source") == "self_refine"]
print(f"self_refine entries: {len(self_refine)}\n")
print("Top 15 by confidence:")
for e in sorted(self_refine, key=lambda x: -x.get("confidence", 0))[:15]:
    print(f"  [{e['confidence']:.2f}] freq={e.get('freq_when_added'):3d}  {e['domain_a']} x {e['domain_b']}")
    print(f"           {e['reason'][:140]}")
print()
print("\nBottom 5 by confidence (still ≥0.7):")
for e in sorted(self_refine, key=lambda x: x.get("confidence", 0))[:5]:
    print(f"  [{e['confidence']:.2f}] freq={e.get('freq_when_added'):3d}  {e['domain_a']} x {e['domain_b']}")
