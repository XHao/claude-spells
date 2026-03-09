---
name: jfr-analysis
description: This skill should be used when the user asks to "analyze JFR file", "JFR performance analysis", "check GC pauses", "CPU hotspots in JFR", "memory allocation analysis", "thread analysis", "translog analysis", "elasticsearch performance bottleneck", "analyze full_analysis.txt", or wants to understand Java Flight Recorder profiling data from Elasticsearch or other JVM applications.
version: 1.0.0
---

# JFR Analysis Skill

Analyze Java Flight Recorder (JFR) text export files to identify performance bottlenecks across GC, CPU, memory allocation, and thread activity.

## Overview

JFR text exports contain structured event records. This skill uses pre-built Python scripts to parse and aggregate those events efficiently — avoiding the need to grep a 500MB+ file manually.

## Scripts Location

All scripts are in `scripts/` relative to this SKILL.md:

| Script | Purpose |
| :--- | :--- |
| `scripts/jfr_full.py` | **Full report** — runs all analyses, outputs Markdown |
| `scripts/jfr_gc.py` | GC pause statistics (count, P90/P99/Max, total time) |
| `scripts/jfr_cpu.py` | CPU hotspot methods (Top 50) + translog frame detection |
| `scripts/jfr_alloc.py` | Object allocation (Top 20 by count and by size) |
| `scripts/jfr_threads.py` | Per-thread CPU samples, allocation, translog activity |

## Usage

### Full analysis (recommended)

```bash
python3 <skill-root>/scripts/jfr_full.py <path-to-jfr-text-file>
# Example:
python3 ~/.claude/plugins/local/jfr-analyzer/skills/jfr-analysis/scripts/jfr_full.py full_analysis.txt
```

Output is a complete Markdown report with four sections: GC, CPU Hotspots, Memory Allocation, Thread Analysis.

### Targeted analysis

```bash
python3 <skill-root>/scripts/jfr_gc.py full_analysis.txt      # GC only
python3 <skill-root>/scripts/jfr_cpu.py full_analysis.txt     # CPU only
python3 <skill-root>/scripts/jfr_alloc.py full_analysis.txt   # Allocation only
python3 <skill-root>/scripts/jfr_threads.py full_analysis.txt # Threads only
```

## Workflow

1. Determine the JFR file path (default: `full_analysis.txt` in current directory).
2. Run `jfr_full.py` for a complete report, or individual scripts for targeted questions.
3. Parse the Markdown output and present findings to the user.
4. For follow-up questions (e.g., "is translog still a problem?"), use `jfr_cpu.py` or `jfr_threads.py` output — they include a dedicated **Translog Activity** section.

## Interpreting Results

- **GC Max > 500ms**: Risk of node timeout; investigate allocation hot paths.
- **GC P99 > 200ms**: Significant tail latency impact.
- **Translog frames in CPU samples**: Indicates translog sync is still occurring despite `async` durability setting — check `TranslogWriter.sync()` call stack.
- **flush threads with high allocation**: Large segment flushes consuming heap; consider tuning `indices.memory.index_buffer_size`.

## Additional Resources

- **`references/jfr-format.md`** — JFR event types, field names, and format reference
