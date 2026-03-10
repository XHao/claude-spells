---
description: Analyze a JFR text export file for GC, CPU hotspots, memory allocation, and thread-level bottlenecks. Outputs a Markdown report.
argument-hint: [file-path]
allowed-tools: Bash, Read
---

Analyze the JFR file specified by the user.

**File to analyze**: $ARGUMENTS

If no file path is provided in `$ARGUMENTS`, use `full_analysis.txt` in the current working directory.

Supported input formats:
- `.jfr` binary files — automatically converted via `jfr print` (requires JDK 17+ on PATH)
- Plain-text JFR exports (produced by `jfr print recording.jfr > output.txt`)

**Steps**:

1. Resolve the absolute path of the JFR file.
2. Run the full analysis script:
   ```
   python3 ~/.claude/plugins/local/jfr-analyzer/skills/jfr-analysis/scripts/jfr_full.py <file-path>
   ```
3. Present the complete Markdown output to the user.
4. Summarize the top findings: worst GC pauses, CPU hotspot #1, largest memory allocator, hottest thread, and any translog activity detected.

If the user asks for a specific section only (e.g., "just GC" or "translog"), run the corresponding individual script instead:
- GC: `jfr_gc.py`
- CPU / translog: `jfr_cpu.py`
- Memory: `jfr_alloc.py`
- Threads: `jfr_threads.py`
