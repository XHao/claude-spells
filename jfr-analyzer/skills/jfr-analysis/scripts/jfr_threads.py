#!/usr/bin/env python3
"""
JFR Thread-Level Analyzer
Aggregates CPU samples and memory allocation per thread.
Usage: python3 jfr_threads.py <file_path>
"""

import re
import sys
from collections import Counter, defaultdict

WEIGHT_PATTERN = re.compile(r"weight\s*=\s*([\d.]+)\s*(kB|MB|GB|B)?")
THREAD_PATTERN = re.compile(r'(?:sampledThread|eventThread)\s*=\s*"([^"]+)"')


def to_bytes(value: float, unit: str) -> float:
    unit = (unit or "B").strip().upper()
    return value * {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(unit, 1)


def fmt_bytes(b: float) -> str:
    if b >= 1024**3:
        return f"{b/1024**3:.1f} GB"
    if b >= 1024**2:
        return f"{b/1024**2:.1f} MB"
    if b >= 1024:
        return f"{b/1024:.1f} KB"
    return f"{b:.0f} B"


def analyze_threads(file_path: str) -> str:
    cpu_counts: Counter = Counter()
    alloc_bytes: Counter = Counter()

    in_exec = False
    in_alloc = False
    current_thread = ""
    in_stack = False

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()

                if "jdk.ExecutionSample" in stripped:
                    in_exec = True
                    in_alloc = False
                    in_stack = False
                    current_thread = ""
                    continue

                if "jdk.ObjectAllocationSample" in stripped or "jdk.ObjectAllocationOutsideTLAB" in stripped:
                    in_alloc = True
                    in_exec = False
                    in_stack = False
                    current_thread = ""
                    continue

                if not (in_exec or in_alloc):
                    continue

                m = THREAD_PATTERN.search(line)
                if m:
                    current_thread = m.group(1)
                    if in_exec:
                        cpu_counts[current_thread] += 1
                    continue

                if in_alloc:
                    m = WEIGHT_PATTERN.search(line)
                    if m:
                        alloc_bytes[current_thread] += to_bytes(float(m.group(1)), m.group(2) or "B")
                    if not stripped:
                        in_alloc = False
                    continue

                if in_exec:
                    if "stackTrace = [" in line:
                        in_stack = True
                        continue
                    if in_stack and stripped == "]":
                        in_stack = False
                        in_exec = False

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not cpu_counts and not alloc_bytes:
        return "## Thread Analysis\n\nNo thread data found.\n"

    lines = ["## Thread Analysis", ""]

    lines += [
        "### CPU Samples per Thread (Top 20)",
        "",
        "| Thread | CPU Samples |",
        "| :--- | ---: |",
    ]
    for thread, count in cpu_counts.most_common(20):
        lines.append(f"| `{thread}` | {count:,} |")

    lines += ["", "### Memory Allocation per Thread (Top 20)", "",
              "| Thread | Allocated |", "| :--- | ---: |"]
    for thread, size in alloc_bytes.most_common(20):
        lines.append(f"| `{thread}` | {fmt_bytes(size)} |")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import os
    _DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _DIR)
    from jfr_convert import ensure_text_file
    path = sys.argv[1] if len(sys.argv) > 1 else "full_analysis.txt"
    text_path, tmp = ensure_text_file(path)
    try:
        print(analyze_threads(text_path))
    finally:
        if tmp:
            tmp.cleanup()
