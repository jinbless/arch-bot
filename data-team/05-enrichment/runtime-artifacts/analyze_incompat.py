"""Quick analysis of guide_domain_incompatibilities.json"""
import json
from collections import Counter
from pathlib import Path

data = json.loads(
    Path(__file__).parent.joinpath("guide_domain_incompatibilities.json").read_text(encoding="utf-8")
)
incompats = data["incompatibilities"]
print(f"total incompatibles: {len(incompats)}")
print()

print("--- confidence distribution ---")
buckets = Counter()
for r in incompats:
    c = r["confidence"]
    if c >= 0.9:
        buckets[">=0.9"] += 1
    elif c >= 0.8:
        buckets["0.8-0.9"] += 1
    elif c >= 0.7:
        buckets["0.7-0.8"] += 1
    elif c >= 0.6:
        buckets["0.6-0.7"] += 1
    else:
        buckets["0.5-0.6"] += 1
for k in sorted(buckets):
    print(f"  {k}: {buckets[k]}")

print()
print("--- sample highest conf ---")
for r in sorted(incompats, key=lambda x: -x["confidence"])[:5]:
    print(f"  [{r['confidence']:.2f}] {r['domain_a']} x {r['domain_b']}: {r['reason'][:120]}")

print()
print("--- sample lowest conf (watch hyponym) ---")
for r in sorted(incompats, key=lambda x: x["confidence"])[:5]:
    print(f"  [{r['confidence']:.2f}] {r['domain_a']} x {r['domain_b']}: {r['reason'][:120]}")

print()
print("--- 8-photo over-promote pairs check ---")
checks = [
    ("물류", "목재"),
    ("외식", "건설"),
    ("외식", "교량"),
    ("화학", "건설"),
    ("화학", "외식"),
    ("크레인", "교량"),
    ("주방", "교량"),
    ("주방", "건설"),
]
for needle_a, needle_b in checks:
    found = False
    for r in incompats:
        a = r["domain_a"]
        b = r["domain_b"]
        if (needle_a in a and needle_b in b) or (needle_a in b and needle_b in a):
            print(f"  {needle_a}/{needle_b} : [{r['confidence']:.2f}] {a} x {b}: {r['reason'][:100]}")
            found = True
            break
    if not found:
        print(f"  {needle_a}/{needle_b} : NO match")

print()
print("--- DUBIOUS pairs (subsumption-like, should NOT be incompatible) ---")
suspicious_pairs = [
    ("건설", "고소"),
    ("화학", "화학물질"),
    ("화학", "화학·생명과학"),
    ("제조", "금속"),
    ("물류", "창고"),
    ("외식", "주방"),
]
for needle_a, needle_b in suspicious_pairs:
    for r in incompats:
        a = r["domain_a"]
        b = r["domain_b"]
        if (needle_a in a and needle_b in b) or (needle_a in b and needle_b in a):
            print(f"  ! [{r['confidence']:.2f}] {a} x {b}: {r['reason'][:100]}")
            break
