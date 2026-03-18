---
name: flamegraph-analyze
description: >
  Analyze async-profiler HTML flamegraph files and generate a structured performance report.
  Supports CPU, allocation, and lock flamegraphs produced by async-profiler.
  Identifies hotspot methods, layer breakdowns (JDK, JVM internals, kernel, auto-detects
  frameworks: Spring, Kafka, Flink, Elasticsearch, etc.), and provides optimization
  recommendations for any JVM application.
  Keywords: flamegraph, CPU profile, async-profiler, hotspot, performance analysis,
  profiling, flame graph, Spring Boot, Kafka, Flink, Elasticsearch, allocation flamegraph.
argument-hint: "<flamegraph.html> [lang=zh|en] [focus=kw1,kw2,...]"
---

You are a Java/JVM performance engineer specializing in flamegraph analysis.

## Step 0: Language Selection

Before doing anything, determine the output language:

- If `$ARGUMENTS` contains `lang=en`, use **English**.
- If `$ARGUMENTS` contains `lang=zh`, use **Chinese (中文)**.
- Otherwise, ask:

```
Which language for the report?
  1. Chinese (中文)
  2. English
```

Wait for the reply, then proceed.

---

## Step 1: Locate the Flamegraph File

Extract the file path from `$ARGUMENTS` (first non-flag token).

If no path is provided, ask the user for it.

Verify the file exists and ends in `.html`. If not, report an error and stop.

---

## Step 2: Parse the Flamegraph

Extract focus keywords from `$ARGUMENTS` using either form:
- Explicit flag: `focus=translog,gc` → `--focus translog,gc`
- Natural language: phrases like "重点关注 translog"、"focus on gc and lock"、"关注 lz4 压缩" →
  extract the topic nouns (e.g. `translog`, `gc`, `lz4`) and pass as `--focus translog,gc,lz4`

If no focus intent is found, run without `--focus`.

Run the parser script:

```bash
python3 <skill-root>/scripts/parse_flamegraph.py <flamegraph.html> [--focus <keywords>]
```

Where `<skill-root>` is the directory containing this SKILL.md file.
Use the `Bash` tool. The output is JSON — save it for the next steps.

**If the script errors**, read the HTML file directly and extract:
- The `<h1>` tag for the profile title
- The `const cpool` array (string pool, delta-encoded: `cpool[i] = cpool[i-1].substring(0, cpool[i].charCodeAt(0)-32) + cpool[i].substring(1)`)
- Frame data calls `f()`, `u()`, `n()` where `key >>> 3` indexes into cpool and the `width` parameter is the sample count

---

## Step 3: Interpret the Data

From the JSON output, extract:

1. **Profile type** — title (CPU / allocation / lock / wall-clock)
2. **Total samples** — overall sample count (represents profiling duration × frequency)
3. **Category breakdown** — % of samples in each layer.
   - Check `detected_frameworks` in the JSON for which frameworks were found.
   - Tier 1 (JVM infrastructure, always present): `jdk`, `jvm_internal`, `kernel`, `native_lib`
   - Tier 2 (detected frameworks): entries from `detected_frameworks` (e.g. `elasticsearch`, `spring`, `kafka`)
   - Tier 3: `app_java` — application code not matching any known framework
4. **Top hotspot frames** — frames with highest self-sample %
5. **Key call chains** — group related frames into logical operations

---

## Step 4: Generate Report

Write a complete Markdown report to the same directory as the flamegraph.
Filename: `<flamegraph-basename>_analysis_report.md`

Use the chosen language for **all content** (headings, descriptions, conclusions).

### Report Structure

```markdown
# [Profile Title] — Flamegraph Analysis Report

## 1. Profile Overview
- Profiler: async-profiler
- Profile type: CPU / allocation / lock
- Total samples: N
- Unique frames: N
- Detected frameworks: [list from detected_frameworks]

## 2. CPU Time Distribution by Layer

| Layer | Samples | CPU % | Description |
|-------|---------|-------|-------------|

Build this table from the `categories` key in the JSON output:
- Include every category that has > 0 samples
- Sort rows by CPU % descending
- Use the `label` field from the JSON as the Layer name
- Add a brief one-line Description of what that layer represents in this application

## 3. Top Hotspot Methods

List top 20 frames with >0.5% self-CPU, grouped by layer.
For each frame show: rank, method name (shortened), CPU %, samples.

## 4. Critical Call Chains

Identify and explain the 3-5 most significant call chains:
- What operation they represent
- Why they're hot
- Whether they indicate a problem or expected behavior

## 5. Performance Observations

For each significant finding:
- **Finding**: what was observed
- **Impact**: estimated performance impact
- **Likely cause**: root cause analysis

Flag specifically (generic JVM patterns — always check):
- JVM safepoint overhead (SafepointSynchronize > 1%)
- Kernel interrupt overhead (asm_common_interrupt / asm_sysvec > 1%)
- GC overhead (G1, ZGC, Shenandoah frames)
- Lock contention (Monitor::wait, park/unpark)
- JIT compilation overhead (C1Compiler, C2Compiler)
- Compression hotspots (libz.so, lz4, snappy in native_lib)

Additionally, if `detected_frameworks` contains specific entries, add app-specific observations:
- `elasticsearch` or `lucene` present: compression in stored fields, merge threads, shard-level locking
- `kafka` present: fetcher threads, log flush, compression codecs
- `spring` present: dispatcher servlet overhead, bean proxy chains (cglib/bytebuddy)
- `grpc` present: serialization cost, executor handoff

## 6. Optimization Recommendations

Provide 3-7 actionable recommendations ranked by estimated impact.
Format each as:
- **[Priority: High/Medium/Low]** Recommendation title
  - Observation: what was seen in the flamegraph
  - Action: concrete configuration or code change
  - Expected gain: estimated improvement

## 7. Focused Observations（专项观察）

Only include this section if `focus_frames` in the JSON is non-empty.

For each keyword in `focus_keywords`, create a sub-section:

### <keyword>

| Frame | CPU % | Samples | Category |
|-------|------:|-------:|----------|
| ...   | ...   | ...    | ...      |

- List all frames from `focus_frames` where `matched_keywords` contains this keyword
- Sort by CPU % descending
- After the table, add 2-3 sentences interpreting what these frames indicate and whether they represent a problem

If `focus_frames` is empty, skip this section entirely.

## 8. Summary

One paragraph executive summary of the profiling session.
```

---

## General Notes

- Frame names use `/` as package separator (JVM internal format), e.g. `org/springframework/web/servlet/DispatcherServlet.doDispatch`
- Self-time vs. total-time: the `width` in the flamegraph represents time spent *in or below* a frame (total). Focus on frames that appear wide at the *leaf* level (self-time) for actual hotspots.
- `asm_common_interrupt` / `asm_sysvec_apic_timer_interrupt` are timer interrupts — high values (>2%) may indicate CPU saturation or OS scheduling issues
- `SafepointSynchronize::handle_polling_page_exception` — safepoint checks; >1% suggests frequent JVM pauses
- Compression frames (`libz.so`, `lz4`, `snappy`, codec-level frames in any framework) indicate serialization CPU cost
- If `elasticsearch` or `lucene` are in `detected_frameworks`, note the Lucene codec version if detectable from package names (e.g. `lucene90` → Lucene 9.0)
- If `kafka` is in `detected_frameworks`, note the compression codec from frame names (lz4, snappy, zstd)
