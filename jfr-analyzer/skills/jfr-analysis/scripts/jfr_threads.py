#!/usr/bin/env python3
"""
JFR Thread-Level Analyzer
Aggregates CPU samples and memory allocation per thread.
Also highlights translog-related threads and frames.
Usage: python3 jfr_threads.py <file_path>
"""

import re
import sys
from collections import Counter, defaultdict

TRANSLOG_KEYWORDS = ["TranslogWriter", "Translog.", "translog"]
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


def shorten(thread: str) -> str:
    # Remove common elasticsearch prefix for brevity
    return re.sub(r"elasticsearch\[[^\]]+\]", "es", thread)


def analyze_threads(file_path: str) -> str:
    # CPU samples per thread
    cpu_counts: Counter = Counter()
    # Allocation bytes per thread
    alloc_bytes: Counter = Counter()
    # Translog frame appearances per thread
    translog_cpu: Counter = Counter()

    in_exec = False
    in_alloc = False
    current_thread = ""
    in_stack = False

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()

                # --- ExecutionSample block ---
                if "jdk.ExecutionSample" in stripped:
                    in_exec = True
                    in_alloc = False
                    in_stack = False
                    current_thread = ""
                    continue

                # --- ObjectAllocationSample block ---
                if "jdk.ObjectAllocationSample" in stripped or "jdk.ObjectAllocationOutsideTLAB" in stripped:
                    in_alloc = True
                    in_exec = False
                    in_stack = False
                    current_thread = ""
                    continue

                if not (in_exec or in_alloc):
                    continue

                # Capture thread name
                m = THREAD_PATTERN.search(line)
                if m:
                    current_thread = m.group(1)
                    if in_exec:
                        cpu_counts[current_thread] += 1
                    continue

                # Allocation weight
                if in_alloc:
                    m = WEIGHT_PATTERN.search(line)
                    if m:
                        alloc_bytes[current_thread] += to_bytes(float(m.group(1)), m.group(2) or "B")
                    if not stripped:
                        in_alloc = False
                    continue

                # Stack trace frames (exec only)
                if in_exec:
                    if "stackTrace = [" in line:
                        in_stack = True
                        continue
                    if in_stack:
                        if stripped == "]":
                            in_stack = False
                            in_exec = False
                            continue
                        if any(kw in line for kw in TRANSLOG_KEYWORDS):
                            translog_cpu[current_thread] += 1

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not cpu_counts and not alloc_bytes:
        return "## Thread Analysis\n\nNo thread data found.\n"

    lines = ["## Thread Analysis", ""]

    # CPU per thread
    lines += [
        "### CPU Samples per Thread (Top 20)",
        "",
        "| Thread | CPU Samples | Translog Frames | Translog % |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for thread, count in cpu_counts.most_common(20):
        tlog = translog_cpu.get(thread, 0)
        pct = tlog / count * 100 if count else 0
        flag = " 🔴" if tlog > 0 else ""
        lines.append(f"| `{shorten(thread)}` | {count:,} | {tlog:,}{flag} | {pct:.1f}% |")

    lines += ["", "### Memory Allocation per Thread (Top 20)", "",
              "| Thread | Allocated |", "| :--- | ---: |"]
    for thread, size in alloc_bytes.most_common(20):
        lines.append(f"| `{shorten(thread)}` | {fmt_bytes(size)} |")

    lines.append("")

    # Translog thread summary
    translog_threads = [(t, c) for t, c in translog_cpu.most_common() if c > 0]
    if translog_threads:
        lines += [
            "### Translog Activity by Thread",
            "",
            "| Thread | Translog Frame Appearances | Total CPU Samples |",
            "| :--- | ---: | ---: |",
        ]
        for thread, tlog in translog_threads:
            total = cpu_counts.get(thread, 0)
            lines.append(f"| `{shorten(thread)}` | {tlog:,} | {total:,} |")
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
