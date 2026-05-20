#!/usr/bin/env python3
"""Assemble the final dashboard HTML by combining data + template."""

import sys
from pathlib import Path

# monorepo 재구성 (2026-05-16) 후 dashboard 파일은 visualization/ 산하에 위치.
HERE = Path(__file__).resolve().parent  # ontology-team/06-reasoning/visualization
DATA_JS = HERE / "dashboard-data.js"
TEMPLATE = HERE / "dashboard-template.html"
OUTPUT = HERE / "dashboard.html"


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
