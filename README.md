# Claude Code Local Plugins

Personal Claude Code plugins for everyday tooling.

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
- **Analyzes**: GC pauses, CPU hotspots, memory allocation, thread activity
- **Input**: `.jfr` binary files (auto-converted) or plain-text exports
- **Output**: Markdown report with top findings

See [`jfr-analyzer/`](./jfr-analyzer/) for details.
