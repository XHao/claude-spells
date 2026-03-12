---
name: jfr-record
description: Record a JFR (Java Flight Recorder) profile from a running JVM process using jcmd, then optionally trigger full analysis. Use when the user wants to profile a live Java process, start JFR recording, capture performance data from a running JVM, or run "jfr-record".
version: 1.0.0
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
argument-hint: [pid=<pid>] [duration=60s] [output=/tmp/app] [analyze=true|false] [src=/path/to/src] [lang=zh|en]
---

Record a JFR profile from a live JVM process and optionally analyze the result.

**Arguments**: $ARGUMENTS

---

## Phase 0 — Parse Arguments + Intent Resolution

Parse `$ARGUMENTS`:
- `PID`: extract from `pid=<value>`. Empty if not provided.
- `DURATION`: extract from `duration=<value>` (e.g. `30s`, `2m`, `120s`). Default: `60s`.
- `OUTPUT`: extract from `output=<path>` (path without extension). Default: `/tmp/jfr_recording`.
- `ANALYZE`: extract from `analyze=true` or `analyze=false`. Default: `true`.
- `SRC_PATH`: extract from `src=<path>`. Empty if not provided.
- `LANG`: extract from `lang=zh` or `lang=en`. Default: `zh`.

Normalize DURATION to seconds as integer `DURATION_SECS` (e.g. `2m` → `120`, `60s` → `60`).

**Step 0a — Ambiguity check (run before asking for missing params):**

Inspect `$ARGUMENTS` for signals that the user may have intended a different action:

| Signal in input | Likely intent | Offer as option |
|---|---|---|
| Contains a file path ending in `.jfr` or `.txt` | Analyze an existing file, not record | "Analyze existing file `<path>` with `/jfr`?" |
| Contains only a number with no `pid=` prefix | Ambiguous — could be PID or irrelevant | "Did you mean `pid=<number>`?" |
| Empty arguments | Unclear — record or analyze? | Present choice menu (see below) |

**If arguments are completely empty**, present a single disambiguation menu before doing anything else:

```
I can help with JFR profiling. What would you like to do?

  1. Record a new JFR profile from a running Java process
  2. Analyze an existing JFR file (.jfr or .txt)
  3. Record and analyze in one step (recommended)

Enter a number, or describe what you need:
```

Map responses:
- `1` → continue this skill with `ANALYZE=false`
- `2` → hand off to jfr-analysis skill: tell user to run `/jfr <file-path>`
- `3` → continue this skill with `ANALYZE=true`
- Free text → re-parse for intent signals and proceed with best match, stating the assumption

**Step 0b — Ask for missing required parameters** (only if intent is confirmed as "record"):

Combine into a single interaction. Only ask what is missing:

| Missing | Ask |
|---|---|
| `PID` only | Run `jcmd -l` first, display process table, ask user to enter PID |
| `LANG` only | Ask: "Output language — Chinese (zh) or English (en)?" |
| Both | Run `jcmd -l`, display table, ask PID and language together |
| Neither | Skip — proceed to Phase 1 |

When asking for PID, always show the process list from `jcmd -l` so the user can identify the right process. Accept either the number alone or `pid=<number>` format.

---

## Phase 1 — Environment Check + List Java Processes

**1a. Check jcmd availability:**
```bash
which jcmd
```
If `jcmd` is not found:
- Tell the user: "`jcmd` not found. Please ensure JDK (not just JRE) is installed and `$JAVA_HOME/bin` is in PATH."
- Stop execution.

**1b. Check jfr availability (for binary conversion):**
```bash
which jfr
```
Note whether `jfr` is available. If absent, warn the user that `.jfr` → text conversion will be skipped and only the raw `.jfr` file will be produced (analysis unavailable without conversion).

**1c. List running Java processes:**
```bash
jcmd -l
```
Display the output as a table to the user so they can identify the target process. Format:
```
PID     Main Class / Description
------  ----------------------------
12345   org.elasticsearch.bootstrap.Elasticsearch
67890   com.example.MyApp
```

If `PID` was already provided by the user, confirm the process name matches expectations.

---

## Phase 2 — Start JFR Recording

Construct the JFR output file path: `JFR_FILE = <OUTPUT>.jfr`.

Run:
```bash
jcmd <PID> JFR.start name=claude_rec duration=<DURATION> filename=<JFR_FILE> settings=profile
```

- `settings=profile` enables CPU sampling, allocation profiling, lock contention, and I/O events — the full set needed for analysis.
- If the command fails (non-zero exit), display the error and stop.

Tell the user:
- Recording started on PID `<PID>`.
- Duration: `<DURATION>` (`<DURATION_SECS>` seconds).
- Output: `<JFR_FILE>`.
- Recording will stop automatically when duration expires.

---

## Phase 3 — Wait for Recording to Complete

Wait for the recording to finish:
```bash
sleep <DURATION_SECS + 3>
```
(Add 3 seconds buffer for JVM flush.)

While waiting, inform the user: "Recording in progress… (waiting `<DURATION_SECS>`s + 3s buffer)"

After sleep, verify the file exists and is non-empty:
```bash
ls -lh <JFR_FILE>
```

If the file is missing or empty:
- Try to check recording status: `jcmd <PID> JFR.check name=claude_rec`
- Report the status to the user and stop with an error message.

---

## Phase 4 — Convert .jfr to Text

Run `jfr print` to convert the binary recording to a plain-text export:

```bash
jfr print <JFR_FILE> > <OUTPUT>.txt
```

Set `TXT_FILE = <OUTPUT>.txt`.

After conversion, confirm the file is non-empty:
```bash
ls -lh <TXT_FILE>
```

If conversion fails or the output file is empty:
- Warn the user that analysis cannot proceed without a text export.
- Tell the user they can convert manually: `jfr print <JFR_FILE> > output.txt`
- Stop execution (skip Phase 5).

Tell the user: "Converted to text: `<TXT_FILE>`"

---

## Phase 5 — Trigger Analysis (Conditional)

**Execute only if `ANALYZE` is `true` and `TXT_FILE` exists.**

Find the full analysis script. Try paths in order:
1. `~/.claude/plugins/cache/claude-spells/jfr-analyzer/1.0.0/skills/jfr-analysis/scripts/jfr_full.py`
2. `~/.claude/plugins/local/jfr-analyzer/skills/jfr-analysis/scripts/jfr_full.py`

Run:
```bash
python3 <SCRIPT_DIR>/jfr_full.py <TXT_FILE>
```

Capture full Markdown output as `RAW_REPORT`.

Then proceed through the full jfr-analysis workflow (Phases 2–7 of `jfr-analysis` SKILL.md):
- Extract key signals (GC severity, CPU hotspots, lock contention, I/O)
- Source code call-chain analysis if `SRC_PATH` is provided
- Web documentation search if LIBRARY hotspots or CRITICAL GC
- Write JFR technical report: `<OUTPUT>_jfr_report.md`
- Write optimization plan: `<OUTPUT>_optimization_plan.md`
- Present summary to user

All prose in the language specified by `LANG`.

If `ANALYZE` is `false`, tell the user:
- Recording complete.
- JFR binary: `<JFR_FILE>`
- Text export: `<TXT_FILE>`
- To analyze later: `/jfr <TXT_FILE> lang=<LANG>`

---

## Error Handling

| Situation | Action |
|---|---|
| `jcmd` not found | Stop, instruct JDK installation |
| PID not found in `jcmd -l` | Warn user, ask to reconfirm PID |
| `JFR.start` fails with "JFR not supported" | Inform that JFR requires JDK (not OpenJ9), Oracle JDK, or OpenJDK 11+ with `--enable-preview` off |
| `.jfr` file missing after sleep | Check `JFR.check`, report status |
| `jfr print` conversion fails | Offer the raw `.jfr` for manual conversion and skip analysis |
