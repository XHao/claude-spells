---
description: Analyze a JFR text export for GC, CPU, memory, threads, lock, and I/O. Supports source code call-chain analysis, web doc search, language selection (zh/en), and outputs two documents: a JFR technical report and a project optimization plan.
argument-hint: [file-path] [src=/path/to/source] [lang=en|zh]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
---

Analyze the JFR file specified by the user.

**Arguments**: $ARGUMENTS

---

## Phase 0 — Parse Arguments + Intent Resolution

Parse `$ARGUMENTS`:
- `JFR_FILE`: first positional argument (no `=`). Empty if not provided.
- `SRC_PATH`: extract from `src=<path>` token. Empty if not provided.
- `LANG`: extract from `lang=en` or `lang=zh` token. Empty if not provided.

Derive `<input-file>` = filename without extension (e.g. `full_analysis` for `full_analysis.txt`).

Output filenames (write to current working directory):
- JFR technical report: `<input-file>_jfr_report.md`
- Optimization plan: `<input-file>_optimization_plan.md`

**Step 0a — Ambiguity check:**

Inspect `$ARGUMENTS` for signals that require clarification before proceeding:

| Signal | Likely intent | Action |
|---|---|---|
| `JFR_FILE` is empty | No file specified — may want to record instead | Present choice menu (see below) |
| `JFR_FILE` given but file does not exist on disk | Typo or wrong path | Show the error and ask: "Did you mean one of these?" then list `.jfr`/`.txt` files in the current directory |
| `JFR_FILE` looks like a PID (plain integer) | May have confused `/jfr` with `/jfr-record` | Ask: "Looks like a process ID — did you want to record from PID `<N>`? Run `/jfr-record pid=<N>`" |

**If `JFR_FILE` is empty**, present a disambiguation menu:

```
I need a JFR file to analyze. What would you like to do?

  1. Specify a file path (I'll analyze it now)
  2. Record a new JFR from a running Java process first → use /jfr-record
  3. Scan current directory for JFR/txt files to choose from

Enter a number, or paste the file path directly:
```

Map responses:
- `1` → ask user to enter the file path, then set `JFR_FILE` and continue
- `2` → tell user to run `/jfr-record` and stop
- `3` → run `find . -maxdepth 2 \( -name "*.jfr" -o -name "*.txt" \) | head -20`, display results, ask user to choose
- File path entered directly → set as `JFR_FILE` and continue

**Step 0b — Ask for missing optional parameters** (only after `JFR_FILE` is confirmed):

Combine into a single interaction. Only ask what is missing:

| Missing params | Ask |
|---|---|
| Both `SRC_PATH` and `LANG` missing | Ask both: source directory path + preferred language |
| Only `LANG` missing | Ask only: preferred language (English or Chinese) |
| Only `SRC_PATH` missing | Ask only: source code directory path (or "none" to skip) |
| Both provided | Skip — go directly to Phase 1 |

If the user enters "none", "skip", or leaves source path blank, set `SRC_PATH` to empty (skip Phase 3).

---

## Phase 1 — Run Python Data Collection

Find the analysis script. Try paths in order until one exists:
1. `~/.claude/plugins/cache/claude-spells/jfr-analyzer/1.0.0/skills/jfr-analysis/scripts/jfr_full.py`
2. `~/.claude/plugins/local/jfr-analyzer/skills/jfr-analysis/scripts/jfr_full.py`

Run:
```bash
python3 <script-dir>/jfr_full.py <JFR_FILE>
```

Capture the full Markdown output as `RAW_REPORT` (hold in memory; do not write to disk yet).

---

## Phase 2 — Extract Key Signals

From `RAW_REPORT`, extract and record internally:

**CPU Hotspots** — Top 10 methods, classify each as:
- `CUSTOM`: user/application code (does not match any known library prefix)
- `LIBRARY`: matches a known library prefix

Known library prefixes:
`org.apache.lucene`, `org.elasticsearch`, `org.apache.kafka`, `io.netty`,
`com.fasterxml.jackson`, `java.`, `javax.`, `jdk.`, `sun.`,
`com.google`, `org.springframework`

**GC Severity**:
- `CRITICAL` — Max pause ≥ 500 ms
- `WARNING` — Max pause ≥ 200 ms
- `OK` — Max pause < 200 ms

**Lock Contention**: Top 3 lock classes + max wait time for each.

**I/O**: Any operation ≥ 100 ms (slow I/O flag).

**Dominant Library**: the library prefix appearing most frequently in LIBRARY hotspots (used to direct web searches).

---

## Phase 3 — Source Code Call-Chain Analysis (Conditional)

**Execute only if `SRC_PATH` is non-empty and the directory exists.**

For each CUSTOM method in Top 10 CPU hotspots (up to 5 methods):

1. Locate source file:
   ```bash
   find <SRC_PATH> -name "<ClassName>.java" -maxdepth 8 -type f
   ```
2. Read the located file; find and read the relevant method body.
3. Find callers:
   ```bash
   grep -r "<methodName>" <SRC_PATH> --include="*.java" -l | head -5
   ```
4. Read the top 2 caller files and build a call chain in this format:
   ```
   EntryClass.entryMethod()
     → IntermediateClass.method()  [file.java:NNN]
       → HotspotClass.method()  [N samples, N% CPU]
         Purpose: <what this method does>
         Why hot: <reason this method is a hotspot>
   ```

Store all call chains as `CALLCHAIN_RESULTS`.

---

## Phase 4 — Web Documentation Search (Conditional)

**Execute only if LIBRARY hotspots exist OR GC severity is CRITICAL. Maximum 4 searches total.**

Trigger rules:

| Condition | Search target |
|---|---|
| `org.apache.lucene.*` in hotspots | Lucene component (e.g. `IndexingChain`) performance tuning docs |
| `org.elasticsearch.*` in hotspots | Elasticsearch index write throughput tuning docs |
| GC is CRITICAL | JVM GC tuning docs for detected GC type (G1/ZGC/Shenandoah) |
| Severe lock contention (single wait ≥ 100 ms) | Optimization docs for that synchronizer class |

For each triggered search:
1. Use `WebSearch` to find relevant results.
2. Use `WebFetch` on the most relevant URL.
3. Extract concrete configuration parameters, JVM flags, or code patterns.

Store all findings as `WEB_FINDINGS` (compact bullet points).

---

## Phase 5 — Write Document 1: JFR Technical Report

Write file `<input-file>_jfr_report.md` to the current working directory using the Write tool.

All prose and section headings must be in the language specified by `LANG`.
Technical identifiers (class names, JVM flags, metric values, code snippets) stay in their original form regardless of language.

Structure:

### 1. Executive Summary
Severity table: one row per dimension (GC / CPU / Memory / Threads / Lock / I/O), with severity level and one-sentence finding.

### 2. GC Analysis
Full GC table from `RAW_REPORT` + interpretation paragraph in `LANG`.

### 3. CPU Hotspot Analysis
Full CPU table from `RAW_REPORT` + interpretation.

### 4. Memory Allocation Analysis
Full allocation table from `RAW_REPORT` + interpretation.

### 5. Thread Analysis
Thread data from `RAW_REPORT` + interpretation.

### 6. Lock Contention Analysis
Lock data from `RAW_REPORT` + interpretation.

### 7. I/O Analysis
I/O data from `RAW_REPORT` + interpretation.

### 8. Call-Chain Analysis
*(Include only if `CALLCHAIN_RESULTS` is non-empty)*
Present each call chain built in Phase 3.

### 9. Reference Documents
*(Include only if `WEB_FINDINGS` is non-empty)*
List sources with URLs and the key findings extracted from each.

---

## Phase 6 — Write Document 2: Project Performance Optimization Plan

Write file `<input-file>_optimization_plan.md` to the current working directory using the Write tool.

All content in `LANG`. Audience: developers and Tech Leads. Actionable and specific.

Structure:

### 1. Problem Summary
Business-impact description: latency, throughput, stability effects.

### 2. Prioritized Action Items

Priority levels:
- **P1 — Critical**: Must fix immediately; risk of outage or severe degradation.
- **P2 — Important**: Fix in next sprint; significant performance impact.
- **P3 — Optimize**: Improvement opportunity; low risk.

For each action item:
- **Problem**: what is observed
- **Root Cause**: why it happens
- **Action Steps**: numbered steps
- **Expected Outcome**: measurable improvement
- **Effort**: S / M / L
- **Example**: code snippet or configuration example

### 3. JVM Tuning Recommendations
Table with columns: Parameter | Recommended Value | Reason.
Base recommendations on GC type detected and `WEB_FINDINGS`.

### 4. Code Hotspot Optimization
*(Include only if `CALLCHAIN_RESULTS` is non-empty)*
Per-method: current behavior → optimization suggestion → expected gain.

### 5. Monitoring and Validation
How to re-record a JFR after applying fixes, and what metrics to compare.

---

## Phase 7 — Present Summary to User

In `LANG`, tell the user:
1. Analysis complete.
2. Full paths to both output files.
3. Top 3 most critical findings (one sentence each).
4. Whether source-code call-chain analysis was performed (yes/no, brief reason if skipped).
5. Whether web searches were performed (yes/no, which topics if yes).

---

## Single-Module Mode (unchanged)

If the user requests only a specific analysis section (GC / CPU / Memory / Threads / Lock / I/O):
- Run the corresponding individual script (`jfr_gc.py`, `jfr_cpu.py`, `jfr_alloc.py`, `jfr_threads.py`, `jfr_lock.py`, `jfr_io.py`).
- Write output to `<input-file>_<section>_report.md`.
- Do NOT generate the optimization plan document.
