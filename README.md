# Claude Code Local Plugins

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
