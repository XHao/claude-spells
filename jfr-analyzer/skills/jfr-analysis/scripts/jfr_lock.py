#!/usr/bin/env python3
"""
JFR Lock Contention Analyzer
Parses jdk.JavaMonitorEnter and jdk.ThreadPark events from a JFR text export.
Usage: python3 jfr_lock.py <file_path>
"""

import re
import sys
from collections import Counter, defaultdict

DURATION_PATTERN = re.compile(r"duration\s*=\s*([\d.]+)\s*ms")
MONITOR_CLASS_PATTERN = re.compile(r"monitorClass\s*=\s*(.*?)(?:\s+\(.*\))?$")
PARKED_CLASS_PATTERN = re.compile(r"parkedClass\s*=\s*(.*?)(?:\s+\(.*\))?$")
THREAD_PATTERN = re.compile(r'(?:eventThread|sampledThread)\s*=\s*"([^"]+)"')


def analyze_lock(file_path: str) -> str:
    # monitor: synchronized blocks
    monitor_wait_ms: Counter = Counter()   # class -> total wait ms
    monitor_count: Counter = Counter()    # class -> event count
    monitor_max_ms: Counter = Counter()   # class -> max single wait ms

    # park: j.u.c locks (ReentrantLock, etc.)
    park_wait_ms: Counter = Counter()
    park_count: Counter = Counter()
    park_max_ms: Counter = Counter()

    # per-thread blocked time (both event types combined)
    thread_wait_ms: Counter = Counter()

    in_monitor = False
    in_park = False
    current: dict = {}

    def flush_monitor():
        if "duration_ms" not in current:
            return
        cls = current.get("monitorClass", "<unknown>")
        ms = current["duration_ms"]
        monitor_wait_ms[cls] += ms
        monitor_count[cls] += 1
        monitor_max_ms[cls] = max(monitor_max_ms.get(cls, 0), ms)
        if "thread" in current:
            thread_wait_ms[current["thread"]] += ms

    def flush_park():
        if "duration_ms" not in current:
            return
        cls = current.get("parkedClass", "<unknown>")
        ms = current["duration_ms"]
        park_wait_ms[cls] += ms
        park_count[cls] += 1
        park_max_ms[cls] = max(park_max_ms.get(cls, 0), ms)
        if "thread" in current:
            thread_wait_ms[current["thread"]] += ms

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()

                if "jdk.JavaMonitorEnter" in stripped:
                    if in_monitor:
                        flush_monitor()
                    elif in_park:
                        flush_park()
                    in_monitor = True
                    in_park = False
                    current = {}
                    continue

                if "jdk.ThreadPark" in stripped:
                    if in_monitor:
                        flush_monitor()
                    elif in_park:
                        flush_park()
                    in_park = True
                    in_monitor = False
                    current = {}
                    continue

                if not (in_monitor or in_park):
                    continue

                m = DURATION_PATTERN.search(line)
                if m:
                    current["duration_ms"] = float(m.group(1))
                    continue

                m = THREAD_PATTERN.search(line)
                if m:
                    current["thread"] = m.group(1)
                    continue

                if in_monitor:
                    m = MONITOR_CLASS_PATTERN.search(line)
                    if m:
                        current["monitorClass"] = m.group(1).strip()
                        continue

                if in_park:
                    m = PARKED_CLASS_PATTERN.search(line)
                    if m:
                        current["parkedClass"] = m.group(1).strip()
                        continue

                if not stripped:
                    if in_monitor:
                        flush_monitor()
                    elif in_park:
                        flush_park()
                    in_monitor = False
                    in_park = False
                    current = {}

        if in_monitor:
            flush_monitor()
        elif in_park:
            flush_park()

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not monitor_count and not park_count:
        return "## Lock Contention Analysis\n\nNo lock contention events found.\n"

    lines = ["## Lock Contention Analysis", ""]

    # --- Monitor (synchronized) ---
    if monitor_count:
        total_monitor_ms = sum(monitor_wait_ms.values())
        lines += [
            "### Monitor Contention (`synchronized`) — Top 20 by Total Wait",
            "",
            f"Total monitor wait time: **{total_monitor_ms:,.1f} ms**",
            "",
            "| Rank | Class | Wait Count | Total Wait (ms) | Max Wait (ms) |",
            "| ---: | :--- | ---: | ---: | ---: |",
        ]
        for rank, (cls, total_ms) in enumerate(monitor_wait_ms.most_common(20), 1):
            max_ms = monitor_max_ms[cls]
            count = monitor_count[cls]
            flag = " ⚠️" if max_ms >= 100 else ""
            lines.append(f"| {rank} | `{cls}` | {count:,} | {total_ms:,.1f} | {max_ms:,.1f}{flag} |")
        lines.append("")

    # --- Park (j.u.c) ---
    if park_count:
        total_park_ms = sum(park_wait_ms.values())
        lines += [
            "### Park Contention (`j.u.c` locks) — Top 20 by Total Wait",
            "",
            f"Total park wait time: **{total_park_ms:,.1f} ms**",
            "",
            "| Rank | Class | Wait Count | Total Wait (ms) | Max Wait (ms) |",
            "| ---: | :--- | ---: | ---: | ---: |",
        ]
        for rank, (cls, total_ms) in enumerate(park_wait_ms.most_common(20), 1):
            max_ms = park_max_ms[cls]
            count = park_count[cls]
            flag = " ⚠️" if max_ms >= 100 else ""
            lines.append(f"| {rank} | `{cls}` | {count:,} | {total_ms:,.1f} | {max_ms:,.1f}{flag} |")
        lines.append("")

    # --- Top blocked threads ---
    if thread_wait_ms:
        lines += [
            "### Top 10 Threads by Total Lock Wait Time",
            "",
            "| Thread | Total Wait (ms) |",
            "| :--- | ---: |",
        ]
        for thread, ms in thread_wait_ms.most_common(10):
            lines.append(f"| `{thread}` | {ms:,.1f} |")
        lines.append("")

    # --- Diagnosis ---
    issues = []
    all_max = list(monitor_max_ms.items()) + list(park_max_ms.items())
    severe = [(cls, ms) for cls, ms in all_max if ms >= 100]
    if severe:
        for cls, ms in sorted(severe, key=lambda x: -x[1])[:3]:
            issues.append(f"⚠️ `{cls}` — single wait **{ms:,.0f} ms** (≥100ms threshold)")
    total_lock_ms = sum(monitor_wait_ms.values()) + sum(park_wait_ms.values())
    if total_lock_ms >= 10_000:
        issues.append(f"⚠️ Total lock wait time **{total_lock_ms:,.0f} ms** — consider reducing lock scope or using lock-free structures.")

    if issues:
        lines.append("### Diagnosis")
        lines.extend(f"- {i}" for i in issues)
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
        print(analyze_lock(text_path))
    finally:
        if tmp:
            tmp.cleanup()
