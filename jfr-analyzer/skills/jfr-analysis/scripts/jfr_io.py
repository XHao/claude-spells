#!/usr/bin/env python3
"""
JFR I/O Latency Analyzer
Parses jdk.FileRead, jdk.FileWrite, jdk.SocketRead, jdk.SocketWrite events.
Usage: python3 jfr_io.py <file_path>
"""

import re
import sys
from collections import Counter

DURATION_PATTERN = re.compile(r"duration\s*=\s*([\d.]+)\s*ms")
PATH_PATTERN = re.compile(r"path\s*=\s*\"?([^\"\n]+?)\"?\s*$")
BYTES_READ_PATTERN = re.compile(r"bytesRead\s*=\s*(\d+)")
BYTES_WRITTEN_PATTERN = re.compile(r"bytesWritten\s*=\s*(\d+)")
HOST_PATTERN = re.compile(r"host\s*=\s*\"?([^\"\n,\s]+)")
PORT_PATTERN = re.compile(r"port\s*=\s*(\d+)")

FILE_EVENTS = {"jdk.FileRead", "jdk.FileWrite"}
SOCKET_EVENTS = {"jdk.SocketRead", "jdk.SocketWrite"}


def fmt_bytes(b: float) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b:.0f} B"


def analyze_io(file_path: str) -> str:
    # Per-path file I/O stats: {path: {count, total_ms, max_ms, total_bytes}}
    file_stats: dict = {}
    # Per-endpoint socket I/O stats: {host:port: {count, total_ms, max_ms, total_bytes}}
    socket_stats: dict = {}
    # Type counters for summary
    type_count: Counter = Counter()
    type_ms: Counter = Counter()
    type_bytes: Counter = Counter()

    # Slow ops for top-N tables (duration, label, bytes)
    slow_file: list = []
    slow_socket: list = []

    in_file = False
    in_socket = False
    event_type = ""
    current: dict = {}

    def flush_file():
        if "duration_ms" not in current:
            return
        ms = current["duration_ms"]
        path = current.get("path", "<unknown>")
        b = current.get("bytes", 0)
        et = current.get("event_type", "jdk.FileRead")

        if path not in file_stats:
            file_stats[path] = {"count": 0, "total_ms": 0.0, "max_ms": 0.0, "total_bytes": 0}
        s = file_stats[path]
        s["count"] += 1
        s["total_ms"] += ms
        s["max_ms"] = max(s["max_ms"], ms)
        s["total_bytes"] += b

        type_count[et] += 1
        type_ms[et] += ms
        type_bytes[et] += b
        slow_file.append((ms, path, b, et))

    def flush_socket():
        if "duration_ms" not in current:
            return
        ms = current["duration_ms"]
        host = current.get("host", "<unknown>")
        port = current.get("port", "")
        endpoint = f"{host}:{port}" if port else host
        b = current.get("bytes", 0)
        et = current.get("event_type", "jdk.SocketRead")

        if endpoint not in socket_stats:
            socket_stats[endpoint] = {"count": 0, "total_ms": 0.0, "max_ms": 0.0, "total_bytes": 0}
        s = socket_stats[endpoint]
        s["count"] += 1
        s["total_ms"] += ms
        s["max_ms"] = max(s["max_ms"], ms)
        s["total_bytes"] += b

        type_count[et] += 1
        type_ms[et] += ms
        type_bytes[et] += b
        slow_socket.append((ms, endpoint, b, et))

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()

                matched_event = next((e for e in FILE_EVENTS | SOCKET_EVENTS if e in stripped), None)
                if matched_event:
                    if in_file:
                        flush_file()
                    elif in_socket:
                        flush_socket()
                    in_file = matched_event in FILE_EVENTS
                    in_socket = matched_event in SOCKET_EVENTS
                    event_type = matched_event
                    current = {"event_type": event_type}
                    continue

                if not (in_file or in_socket):
                    continue

                m = DURATION_PATTERN.search(line)
                if m:
                    current["duration_ms"] = float(m.group(1))
                    continue

                if in_file:
                    m = PATH_PATTERN.search(line)
                    if m:
                        current["path"] = m.group(1).strip()
                        continue
                    m = BYTES_READ_PATTERN.search(line)
                    if m:
                        current["bytes"] = int(m.group(1))
                        continue
                    m = BYTES_WRITTEN_PATTERN.search(line)
                    if m:
                        current["bytes"] = int(m.group(1))
                        continue

                if in_socket:
                    m = HOST_PATTERN.search(line)
                    if m:
                        current["host"] = m.group(1).strip()
                        continue
                    m = PORT_PATTERN.search(line)
                    if m:
                        current["port"] = m.group(1)
                        continue
                    m = BYTES_READ_PATTERN.search(line)
                    if m:
                        current["bytes"] = int(m.group(1))
                        continue
                    m = BYTES_WRITTEN_PATTERN.search(line)
                    if m:
                        current["bytes"] = int(m.group(1))
                        continue

                if not stripped:
                    if in_file:
                        flush_file()
                    elif in_socket:
                        flush_socket()
                    in_file = False
                    in_socket = False
                    current = {}

        if in_file:
            flush_file()
        elif in_socket:
            flush_socket()

    except FileNotFoundError:
        return f"**Error**: File not found: `{file_path}`"

    if not file_stats and not socket_stats:
        return "## I/O Analysis\n\nNo I/O events found.\n"

    lines = ["## I/O Analysis", ""]

    # --- Summary table ---
    lines += [
        "### I/O Event Summary",
        "",
        "| Event Type | Count | Total Duration (ms) | Total Bytes |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for et in ["jdk.FileRead", "jdk.FileWrite", "jdk.SocketRead", "jdk.SocketWrite"]:
        if type_count[et]:
            lines.append(f"| `{et}` | {type_count[et]:,} | {type_ms[et]:,.1f} | {fmt_bytes(type_bytes[et])} |")
    lines.append("")

    # --- Slow file ops ---
    if slow_file:
        top_file = sorted(slow_file, key=lambda x: -x[0])[:20]
        lines += [
            "### Slowest File Operations (Top 20)",
            "",
            "| Duration (ms) | Type | Path | Bytes |",
            "| ---: | :--- | :--- | ---: |",
        ]
        for ms, path, b, et in top_file:
            flag = " ⚠️" if ms >= 100 else ""
            short_path = path if len(path) <= 60 else "…" + path[-57:]
            lines.append(f"| {ms:,.1f}{flag} | `{et}` | `{short_path}` | {fmt_bytes(b)} |")
        lines.append("")

    # --- Slow socket ops ---
    if slow_socket:
        top_socket = sorted(slow_socket, key=lambda x: -x[0])[:20]
        lines += [
            "### Slowest Socket Operations (Top 20)",
            "",
            "| Duration (ms) | Type | Endpoint | Bytes |",
            "| ---: | :--- | :--- | ---: |",
        ]
        for ms, endpoint, b, et in top_socket:
            flag = " ⚠️" if ms >= 100 else ""
            lines.append(f"| {ms:,.1f}{flag} | `{et}` | `{endpoint}` | {fmt_bytes(b)} |")
        lines.append("")

    # --- Diagnosis ---
    issues = []
    slow_file_ops = [(ms, p) for ms, p, _, _ in slow_file if ms >= 100]
    slow_socket_ops = [(ms, e) for ms, e, _, _ in slow_socket if ms >= 100]
    if slow_file_ops:
        worst_ms, worst_path = max(slow_file_ops)
        short = worst_path if len(worst_path) <= 50 else "…" + worst_path[-47:]
        issues.append(f"⚠️ {len(slow_file_ops)} file operation(s) ≥ 100ms — worst: **{worst_ms:,.0f} ms** on `{short}`")
    if slow_socket_ops:
        worst_ms, worst_ep = max(slow_socket_ops)
        issues.append(f"⚠️ {len(slow_socket_ops)} socket operation(s) ≥ 100ms — worst: **{worst_ms:,.0f} ms** to `{worst_ep}`")

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
        print(analyze_io(text_path))
    finally:
        if tmp:
            tmp.cleanup()
