#!/usr/bin/env python3
"""
JFR Object Allocation Analyzer
Parses jdk.ObjectAllocationSample and jdk.ObjectAllocationOutsideTLAB events.
Usage: python3 jfr_alloc.py <file_path>
"""

import re
import sys
from collections import Counter

CLASS_PATTERN = re.compile(r"objectClass\s*=\s*(.*?)(?:\s+\(.*\))?$")
WEIGHT_PATTERN = re.compile(r"weight\s*=\s*([\d.]+)\s*(kB|MB|GB|B)?")
SIZE_PATTERN = re.compile(r"allocationSize\s*=\s*(\d+)")


def to_bytes(value: float, unit: str) -> float:
    unit = (unit or "B").strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    return value * multipliers.get(unit, 1)


def fmt_bytes(b: float) -> str:
    if b >= 1024**3:
        return f"{b/1024**3:.1f} GB"
    if b >= 1024**2:
        return f"{b/1024**2:.1f} MB"
    if b >= 1024:
        return f"{b/1024:.1f} KB"
    return f"{b:.0f} B"


def analyze_alloc(file_path: str) -> str:
    alloc_counts: Counter = Counter()
    alloc_bytes: Counter = Counter()

    in_event = False
    current: dict = {}
    event_types = {"jdk.ObjectAllocationSample", "jdk.ObjectAllocationOutsideTLAB"}

    def flush():
        if "objectClass" in current:
            cls = current["objectClass"]
            alloc_counts[cls] += 1
            alloc_bytes[cls] += current.get("bytes", 0)

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()

                if any(et in stripped for et in event_types):
                    flush()
                    in_event = True
                    current = {}
                    continue

                if not in_event:
                    continue

                m = CLASS_PATTERN.search(line)
                if m:
                    current["objectClass"] = m.group(1).strip()
                    continue

                # weight field (ObjectAllocationSample)
                m = WEIGHT_PATTERN.search(line)
                if m:
                    current["bytes"] = to_bytes(float(m.group(1)), m.group(2) or "B")
                    continue

                # allocationSize field (ObjectAllocationOutsideTLAB)
                m = SIZE_PATTERN.search(line)
                if m:
                    current["bytes"] = float(m.group(1))
                    continue

                # blank line ends event
                if not stripped:
                    flush()
                    in_event = False
                    current = {}

        flush()

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not alloc_counts:
        return "## Memory Allocation Analysis\n\nNo allocation events found.\n"

    total_bytes = sum(alloc_bytes.values())

    lines = [
        "## Memory Allocation Analysis",
        "",
        f"Total tracked allocation: **{fmt_bytes(total_bytes)}**",
        "",
        "### Top 20 by Allocation Count",
        "",
        "| Rank | Count | Class | Total Size |",
        "| ---: | ---: | :--- | ---: |",
    ]
    for rank, (cls, count) in enumerate(alloc_counts.most_common(20), 1):
        lines.append(f"| {rank} | {count:,} | `{cls}` | {fmt_bytes(alloc_bytes[cls])} |")

    lines += [
        "",
        "### Top 20 by Allocation Size",
        "",
        "| Rank | Total Size | Class | Count |",
        "| ---: | ---: | :--- | ---: |",
    ]
    for rank, (cls, size) in enumerate(alloc_bytes.most_common(20), 1):
        lines.append(f"| {rank} | {fmt_bytes(size)} | `{cls}` | {alloc_counts[cls]:,} |")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "full_analysis.txt"
    print(analyze_alloc(path))
