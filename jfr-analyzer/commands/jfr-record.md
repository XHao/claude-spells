---
description: Record a JFR profile from a live JVM process using jcmd, then optionally run full performance analysis. Usage: /jfr-record [pid=<pid>] [duration=60s] [output=/tmp/app] [analyze=true|false] [src=/path] [lang=zh|en]
argument-hint: [pid=<pid>] [duration=60s] [output=/tmp/app] [analyze=true|false] [src=/path/to/src] [lang=zh|en]
allowed-tools: Bash, Read, Write, WebSearch, WebFetch
---

Record a JFR profile from a running JVM and optionally analyze the result.

**Arguments**: $ARGUMENTS

---

Find the jfr-record skill. Try paths in order until one exists:
1. `~/.claude/plugins/cache/claude-spells/jfr-analyzer/1.0.0/skills/jfr-record/SKILL.md`
2. `~/.claude/plugins/local/jfr-analyzer/skills/jfr-record/SKILL.md`

Read the located SKILL.md and execute it with the arguments above.
