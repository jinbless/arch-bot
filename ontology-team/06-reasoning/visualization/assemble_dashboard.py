#!/usr/bin/env python3
"""Assemble the final dashboard HTML by combining data + template."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "scripts" / "dashboard-data.js"
TEMPLATE = ROOT / "scripts" / "dashboard-template.html"
OUTPUT = ROOT / "kosha-ontology-dashboard.html"


def main():
    data_js = DATA_JS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    # Replace the placeholder in template with actual data
    html = template.replace("/* %%DATA_PLACEHOLDER%% */", data_js)

    OUTPUT.write_text(html, encoding="utf-8")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Dashboard written to: {OUTPUT}")
    print(f"Size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
