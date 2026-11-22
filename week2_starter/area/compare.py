#!/usr/bin/env python3
"""Compare area/results.txt (yours) with area/reference_results.txt (from the guide)."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    rows = {}
    for line in path.read_text().splitlines():
        m = re.search(r"^(\S+).*area_um2=([\d.]+)", line)
        if m:
            rows[m.group(1)] = float(m.group(2))
    return rows


mine, ref = load(HERE / "results.txt"), load(HERE / "reference_results.txt")
print(f"{'block':44s} {'yours':>10s} {'reference':>10s} {'diff':>7s}")
for name, r in ref.items():
    y = mine.get(name)
    diff = f"{100 * (y / r - 1):+6.1f}%" if y else "   n/a"
    print(f"{name:44s} {y or 0:>10.0f} {r:>10.0f} {diff}")
