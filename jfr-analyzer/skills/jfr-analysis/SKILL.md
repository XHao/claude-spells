---
name: jfr-analysis
description: >
  Analyze Java Flight Recorder (JFR) profiling data for any JVM application.
  Trigger when: user provides a .jfr file, a JFR text export (.txt), or a pre-parsed
  full_analysis.txt; or asks to "分析 JFR"、"查看 GC 停顿"、"内存分配分析"、"线程分析"、
  "锁竞争"、"CPU 热点"、"analyze JFR", "check GC pauses", "memory allocation",
  "thread bottleneck", "lock contention", "CPU hotspots in JFR".
  Covers: GC pause statistics, CPU hotspot methods, object allocation, thread activity,
  lock contention, file/socket I/O latency.
  Supports lang=zh|en to skip language selection prompt.
version: 1.0.0
argument-hint: "<jfr-file-or-full_analysis.txt> [lang=zh|en]"
disable-model-invocation: true
context: fork
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
| `scripts/jfr_cpu.py` | CPU hotspot methods (Top 50) |
| `scripts/jfr_alloc.py` | Object allocation (Top 20 by count and by size) |
| `scripts/jfr_threads.py` | Per-thread CPU samples and allocation |
| `scripts/jfr_lock.py` | Lock contention (monitor + j.u.c park, Top 20 by wait time) |
| `scripts/jfr_io.py` | File and socket I/O latency (Top 20 slowest ops) |

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

### Phase 0 — Intent Resolution

This phase runs before any analysis. It ensures a valid file path is confirmed and clarifies ambiguous inputs.

**Step 0a — Ambiguity check:**

Inspect the user's input for signals that require clarification:

| Signal | Likely intent | Action |
|---|---|---|
| No file path given | Unknown — analyze or record? | Present choice menu (see below) |
| File path given but does not exist on disk | Typo or wrong path | Show error, list `.jfr`/`.txt` files in current dir, ask user to choose |
| Input is a plain integer | May have confused analysis with recording | Ask: "Looks like a process ID — did you want to record from PID `<N>`? Use `/jfr-record pid=<N>`" |
| Input is a `.jfr` binary file | Valid — will auto-convert via `jfr print` | Confirm: "Will convert `<file>.jfr` to text first, then analyze. Proceed?" |

**If no file path is given**, present a disambiguation menu:

```
I need a JFR file to analyze. What would you like to do?

  1. Specify a file path (paste it here)
  2. Scan current directory for JFR/txt files to choose from
  3. Record a new JFR from a running Java process → use /jfr-record

Enter a number, or paste the file path directly:
```

Map responses:
- `1` → ask user to enter the file path, set as `JFR_FILE`, continue
- `2` → run `find . -maxdepth 2 \( -name "*.jfr" -o -name "*.txt" \) | head -20`, display as a numbered list, ask user to choose by number
- `3` → tell user to run `/jfr-record` and stop
- File path entered directly → set as `JFR_FILE` and continue

**Step 0b — Ask for missing optional parameters** (only after `JFR_FILE` is confirmed):

Combine into a single interaction:

| Missing params | Ask |
|---|---|
| Both `SRC_PATH` and `LANG` missing | Ask both: source directory path + preferred language |
| Only `LANG` missing | Ask only: preferred language (English or Chinese) |
| Only `SRC_PATH` missing | Ask only: source code directory path (or "none" to skip) |
| Both provided | Skip |

If the user enters "none", "skip", or leaves blank, set `SRC_PATH` to empty (skip call-chain analysis).

---

1. Run Phase 0 to resolve file path and parameters.
2. Run `jfr_full.py` for a complete report, or individual scripts for targeted questions.
3. Parse the Markdown output and present findings to the user.

## Additional Resources

- **`references/jfr-format.md`** — JFR event types, field names, and format reference
- **`references/interpretation-guide.md`** — Thresholds and diagnostic rules for interpreting JFR results
