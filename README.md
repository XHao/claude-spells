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

Analyze Java Flight Recorder (JFR) text exports for performance bottlenecks.

- **Command**: `/jfr [file-path]`
- **Analyzes**: GC pauses, CPU hotspots, memory allocation, thread activity, lock contention, I/O latency
- **Input**: `.jfr` binary files (auto-converted) or plain-text exports
- **Output**: Markdown report with top findings

See [`jfr-analyzer/`](./jfr-analyzer/) for details.
