#!/usr/bin/env python3
"""
JFR GC Pause Analyzer
Parses jdk.GCPhasePause / GarbageCollection events from a JFR text export.
Usage: python3 jfr_gc.py <file_path>
"""

import re
import sys


def analyze_gc(file_path: str) -> str:
    durations = []
    pattern = re.compile(r"duration\s*=\s*([\d.]+)\s*ms")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    try:
                        durations.append(float(m.group(1)))
                    except ValueError:
                        pass
    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not durations:
        return "## GC Analysis\n\nNo GC pause duration events found.\n"

    durations.sort()
    n = len(durations)
    total_ms = sum(durations)
    avg_ms = total_ms / n
    median_ms = durations[n // 2]
    max_ms = durations[-1]
    p90_ms = durations[int(n * 0.90) - 1] if n >= 10 else durations[-1]
    p99_ms = durations[int(n * 0.99) - 1] if n >= 100 else durations[-1]
    total_hours = total_ms / 3_600_000

    lines = [
        "## GC Analysis",
        "",
        "| Metric | Value | Notes |",
        "| :--- | ---: | :--- |",
        f"| Total GC Pauses | {n:,} | |",
        f"| Total Pause Time | {total_ms:,.2f} ms ({total_hours:.2f} h) | Time lost to GC |",
        f"| Average Pause | {avg_ms:.2f} ms | |",
        f"| Median Pause | {median_ms:.2f} ms | |",
        f"| P90 Pause | {p90_ms:.2f} ms | 10% of pauses exceed this |",
        f"| P99 Pause | {p99_ms:.2f} ms | {'⚠️ High' if p99_ms > 200 else 'OK'} |",
        f"| Max Pause | {max_ms:.2f} ms | {'🔴 Critical' if max_ms > 500 else '⚠️ High' if max_ms > 200 else 'OK'} |",
        "",
    ]

    # Diagnosis
    issues = []
    if max_ms >= 500:
        issues.append(f"🔴 Max GC pause **{max_ms:.0f} ms** exceeds 500ms — risk of node timeout / request failures.")
    if p99_ms >= 200:
        issues.append(f"⚠️ P99 pause **{p99_ms:.0f} ms** severely impacts tail latency.")
    if total_hours > 1:
        issues.append(f"⚠️ Total GC time **{total_hours:.1f} h** — high allocation pressure, consider heap tuning.")

    if issues:
        lines.append("### Diagnosis")
        lines.extend(f"- {i}" for i in issues)
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "full_analysis.txt"
    print(analyze_gc(path))
