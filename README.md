# Claude Spells

> Claude Code plugins for Java/JVM performance engineering — JFR analysis, flamegraph profiling, and benchmark reporting.

Personal Claude Code plugins for everyday tooling.

## Installation

Plugins must be explicitly registered. Run the install script once to add this repo as a marketplace, then install individual plugins:

```bash
# 1. Register the marketplace
./install.sh

# 2. Install a plugin (inside Claude Code)
/plugin install jfr-analyzer@claude-spells
```

Requires `jq` (`brew install jq`).

## Structure

Each plugin lives in its own subdirectory and follows the Claude Code plugin format:

```
<plugin-name>/
├── .claude-plugin/
│   └── plugin.json       # Plugin metadata
├── commands/             # Slash commands
│   └── <command>.md
└── skills/               # Skills triggered by context
    └── <skill-name>/
        ├── SKILL.md
        ├── scripts/
        └── references/
```

## Plugins

### jfr-analyzer

Analyze Java Flight Recorder (JFR) text exports for performance bottlenecks. Also supports recording JFR profiles directly from live JVM processes.

**Analyze an existing file:**
- **Command**: `/jfr [file-path] [src=/path/to/src] [lang=zh|en]`
- **Analyzes**: GC pauses, CPU hotspots, memory allocation, thread activity, lock contention, I/O latency
- **Input**: `.jfr` binary files (auto-converted) or plain-text exports
- **Output**: Two Markdown documents — JFR technical report + project optimization plan

**Record from a live JVM process:**
- **Command**: `/jfr-record [pid=<pid>] [duration=60s] [output=/tmp/app] [analyze=true|false] [src=/path/to/src] [lang=zh|en]`
- **Requires**: JDK with `jcmd` in PATH (JDK 11+)
- **Flow**: lists Java processes → starts `jcmd JFR.start` → waits → converts `.jfr` → auto-analyzes
- **Default**: `duration=60s`, `analyze=true`, `lang=zh`

**End-to-end example:**
```
/jfr-record pid=12345 duration=120s src=~/projects/myapp lang=zh
```
Records 120s of profiling data from PID 12345, then produces a full Chinese-language analysis report.

See [`jfr-analyzer/`](./jfr-analyzer/) for details.

### esrally-analyze

Analyze esrally benchmark reports and generate structured technical summaries.

- **Skill**: invoke by providing `.md`, `.tar.gz`, or `.gz` rally result files, or ask to "分析压测结果" / "compare benchmark runs"
- **Supports**: single-run analysis, A/B comparison (e.g. different translog/indexing configs), multi-run baseline statistics
- **Output**: structured Markdown report with throughput, latency, and per-operation breakdowns
- **Languages**: Chinese (`lang=zh`) and English (`lang=en`)

See [`esrally-analyze/`](./esrally-analyze/) for details.

### flamegraph-analyzer

Analyze async-profiler HTML flamegraph files for any JVM application.

- **Skill**: invoke by providing a `.html` flamegraph file, or ask to "分析火焰图" / "analyze flamegraph"
- **Framework detection**: auto-detects Spring, Kafka, Flink, Elasticsearch, Lucene, Netty, gRPC, and more
- **Analyzes**: CPU hotspots, layer breakdowns, critical call chains, GC/safepoint/lock contention patterns
- **Focused analysis**: use `focus=translog,gc` or natural language like "重点关注 translog" to spotlight specific topics
- **Output**: Markdown report with per-layer CPU distribution, top hotspot methods, prioritized recommendations, and optional focused observations section
- **Languages**: Chinese (`lang=zh`) and English (`lang=en`)

See [`flamegraph-analyzer/`](./flamegraph-analyzer/) for details.
