#!/usr/bin/env python3
"""
JFR CPU Execution Sample Analyzer
Parses jdk.ExecutionSample events from a JFR text export.
Usage: python3 jfr_cpu.py <file_path>
"""

import re
import sys
from collections import Counter, defaultdict

FRAME_PATTERN = re.compile(
    r"^\s+([a-zA-Z_$][\w$./<>\[\]]+\(.*?\))\s+line:"
)


def analyze_cpu(file_path: str) -> str:
    method_counts: Counter = Counter()
    thread_method_counts: defaultdict = defaultdict(Counter)
    total_samples = 0

    in_sample = False
    current_thread = ""
    in_stack = False

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "jdk.ExecutionSample" in line:
                    in_sample = True
                    in_stack = False
                    current_thread = ""
                    total_samples += 1
                    continue

                if not in_sample:
                    continue

                if "sampledThread" in line or "eventThread" in line:
                    m = re.search(r'"([^"]+)"', line)
                    if m:
                        current_thread = m.group(1)
                    continue

                if "stackTrace = [" in line:
                    in_stack = True
                    continue

                if in_stack:
                    stripped = line.strip()
                    if stripped == "]":
                        in_stack = False
                        in_sample = False
                        continue
                    if stripped.startswith("..."):
                        continue
                    m = FRAME_PATTERN.match(line)
                    if m:
                        frame = m.group(1)
                        method_counts[frame] += 1
                        if current_thread:
                            thread_method_counts[current_thread][frame] += 1

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not method_counts:
        return "## CPU Hotspot Analysis\n\nNo ExecutionSample stack traces found.\n"

    lines = [
        "## CPU Hotspot Analysis",
        "",
        f"Total execution samples processed: **{total_samples:,}**",
        "",
        "### Top 50 Hotspot Methods",
        "",
        "| Rank | Count | Method |",
        "| ---: | ---: | :--- |",
    ]
    for rank, (method, count) in enumerate(method_counts.most_common(50), 1):
        lines.append(f"| {rank} | {count:,} | `{method}` |")

    lines.append("")

    # Thread breakdown — top 10 threads by sample count
    thread_totals = {t: sum(c.values()) for t, c in thread_method_counts.items()}
    top_threads = sorted(thread_totals.items(), key=lambda x: -x[1])[:10]

    lines += [
        "### Top 10 Threads by CPU Samples",
        "",
        "| Thread | Samples | Top Method |",
        "| :--- | ---: | :--- |",
    ]
    for thread, count in top_threads:
        top_method = thread_method_counts[thread].most_common(1)[0][0] if thread_method_counts[thread] else "-"
        lines.append(f"| `{thread}` | {count:,} | `{top_method[:80]}` |")

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
        print(analyze_cpu(text_path))
    finally:
        if tmp:
            tmp.cleanup()
