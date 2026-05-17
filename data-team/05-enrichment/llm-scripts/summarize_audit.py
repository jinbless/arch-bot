"""Phase 3A audit summary — category breakdown, top samples, KOSHA22 alignment."""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_v1.json"
HUMAN = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_human_queue.json"
OUT = ROOT / "data-team/05-enrichment/runtime-artifacts/synthetic_audit_summary.md"

audit = json.loads(AUDIT.read_text(encoding="utf-8"))
human = json.loads(HUMAN.read_text(encoding="utf-8"))
results = audit["results"]

matrix = defaultdict(Counter)
for r in results:
    matrix[r["axis"]][r["consensus"]["category"]] += 1

samples = defaultdict(list)
for r in results:
    samples[r["consensus"]["category"]].append(r)
for cat in samples:
    samples[cat].sort(key=lambda x: -x["freq"])

kosha22 = Counter()
for r in results:
    if r["axis"] == "accident_type":
        km = r["consensus"].get("kosha_22_match", "")
        if km:
            kosha22[km] += 1

reloc = Counter()
for r in results:
    if r["consensus"]["category"] == "WRONG_AXIS":
        reloc[(r["axis"], r["consensus"].get("correct_axis", "?"))] += 1

sub_parents = Counter()
for r in results:
    if r["consensus"]["category"] == "SUB_CLASS_OF":
        pc = r["consensus"].get("parent_code", "")
        if pc:
            sub_parents[pc] += 1

new_axes = Counter()
for r in results:
    if r["consensus"]["category"] == "NEW_CODE_NEEDED":
        new_axes[r["axis"]] += 1

lines = []
lines.append("# Phase 3A — Synthetic KO Audit Summary\n\n")
lines.append(f"Generated: {audit['generated_at']}\n\n")
lines.append("## Config\n\n")
for k, v in audit["config"].items():
    lines.append(f"- {k}: {v}\n")
lines.append("\n## Overall Stats\n\n")
lines.append(f"- Total: {audit['stats']['total_audited']}\n")
lines.append(f"- by status: {audit['stats']['by_status']}\n")
lines.append(f"- by category: {audit['stats']['by_category']}\n")
lines.append(f"- by axis: {audit['stats']['by_axis']}\n\n")

lines.append("## Category x Axis Matrix\n\n")
all_cats = sorted({c for axis in matrix for c in matrix[axis]})
lines.append("| axis | " + " | ".join(all_cats) + " |\n")
lines.append("|---|" + "---|" * len(all_cats) + "\n")
for axis in sorted(matrix.keys()):
    row = [axis] + [str(matrix[axis][c]) for c in all_cats]
    lines.append("| " + " | ".join(row) + " |\n")
lines.append("\n")

lines.append("## KOSHA 22 mapping (accident_type)\n\n")
lines.append("| KOSHA KO | matched count |\n|---|---|\n")
for k, n in kosha22.most_common():
    lines.append(f"| {k} | {n} |\n")
lines.append("\n")

lines.append("## WRONG_AXIS top reloc proposals\n\n")
lines.append("| from | to | count |\n|---|---|---|\n")
for (f, t), n in reloc.most_common(15):
    lines.append(f"| {f} | {t} | {n} |\n")
lines.append("\n")

lines.append("## SUB_CLASS_OF top parents\n\n")
lines.append("| parent | sub count |\n|---|---|\n")
for p, n in sub_parents.most_common(15):
    lines.append(f"| {p} | {n} |\n")
lines.append("\n")

lines.append("## NEW_CODE_NEEDED by axis\n\n")
lines.append("| axis | count |\n|---|---|\n")
for ax, n in new_axes.most_common():
    lines.append(f"| {ax} | {n} |\n")
lines.append("\n")

for cat in ["EXISTING_EQUIV", "SUB_CLASS_OF", "NEW_CODE_NEEDED", "WRONG_AXIS", "NOT_A_CODE"]:
    items = samples.get(cat, [])[:15]
    lines.append(f"## Top 15 freq -- {cat}\n\n")
    lines.append("| axis | ko_code | freq | status | canonical_en | parent | reloc |\n|---|---|---|---|---|---|---|\n")
    for r in items:
        c = r["consensus"]
        lines.append(f"| {r['axis']} | {r['ko_code']} | {r['freq']} | {c['status']} | {c.get('canonical_label_en','-')} | {c.get('parent_code','-')} | {c.get('correct_axis','-')} |\n")
    lines.append("\n")

lines.append("## HUMAN Queue Distribution\n\n")
hba = Counter(r["axis"] for r in human["items"])
hbc = Counter(r["consensus"]["category"] for r in human["items"])
lines.append(f"- total: {human['count']}\n")
lines.append(f"- by axis: {dict(hba)}\n")
lines.append(f"- by category: {dict(hbc)}\n\n")
lines.append("## HUMAN Queue Top 25 (freq)\n\n")
lines.append("| axis | ko_code | freq | consensus_cat | voice categories |\n|---|---|---|---|---|\n")
for r in sorted(human["items"], key=lambda x: -x["freq"])[:25]:
    reasons = " / ".join(f"{v.get('category','?')}" for v in r["voices"])
    lines.append(f"| {r['axis']} | {r['ko_code']} | {r['freq']} | {r['consensus']['category']} | {reasons} |\n")
lines.append("\n")

OUT.write_text("".join(lines), encoding="utf-8")
print(f"Saved: {OUT}")
print(f"\n=== KEY METRICS ===")
N = audit['stats']['total_audited']
for k, v in audit['stats']['by_status'].items():
    print(f"  {k}: {v} ({100*v/N:.1f}%)")
print()
for k in ["NEW_CODE_NEEDED", "SUB_CLASS_OF", "WRONG_AXIS", "EXISTING_EQUIV", "NOT_A_CODE"]:
    v = audit['stats']['by_category'].get(k, 0)
    print(f"  {k}: {v} ({100*v/N:.1f}%)")
