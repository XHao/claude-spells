# claude-spells

Claude Code plugin marketplace for Java/JVM performance engineering.

## Project Structure

```
<plugin>/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata (name, version, keywords)
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md         # Skill definition (frontmatter + step instructions)
│       ├── scripts/         # Helper scripts (data extraction logic)
│       └── references/      # Reference material (thresholds, format specs)
└── commands/                # Slash commands (if any)
.claude-plugin/
└── marketplace.json         # Plugin registry
```

## Plugins

| Plugin | Skills | Purpose |
|--------|--------|---------|
| `jfr-analyzer` | `jfr-analysis` | JFR profiling data analysis |
| `esrally-analyze` | `esrally-analyze` | esrally benchmark report analysis |
| `flamegraph-analyzer` | `flamegraph-analyze` | async-profiler HTML flamegraph analysis |

---

## Skill Authoring Guidelines

### Frontmatter Fields

```yaml
---
name: skill-name
description: >        # LLM 触发判断用，只有 description 常驻 context
  ...
argument-hint: "..."  # 命令行补全提示，给用户看的
allowed-tools: Bash, Read, Write   # 免确认的工具白名单
disable-model-invocation: true     # 有副作用（写文件/发请求）的 skill 必须加
context: fork                      # 重型/长任务 skill 加，避免污染主对话上下文
version: 1.0.0
---
```

**必须加 `disable-model-invocation: true` 的情况：**
- 会写文件（Write 工具）
- 会执行有副作用的 Bash 命令
- 需要用户明确意图才能运行

**应该加 `context: fork` 的情况：**
- 多步骤分析、读取大文件等重型任务
- 输出内容大（生成完整报告）
- 不需要访问主对话历史

---

### Description 写法

description 是唯一**常驻 context** 的部分（SKILL.md 正文按需加载），要在有限字数里完成触发判断和参数提取。

**推荐结构：**

```yaml
description: >
  <一句话说这个 skill 做什么>.
  Trigger when: user provides <文件类型特征>; or asks to "<中文短语1>"、"<中文短语2>"、
  "<English phrase 1>", "<English phrase 2>".
  Supports <param>=<values> to skip <X> prompt.
```

**要点：**
- 用 `Trigger when:` 作为意图匹配的显式信号
- 中英文短语并列，覆盖用户的自然表达习惯
- 文件类型特征（`.html`、`.jfr`、`.tar.gz`）比功能描述更稳定
- 把 `lang=zh|en` 等可选参数写进 description，LLM 主动提取，减少交互轮次
- 不要用 `Keywords:` 标签，直接写进描述

---

### SKILL.md 正文结构

**职责分离：**

| 内容类型 | 放在哪里 |
|---------|---------|
| 触发判断、参数提取 | frontmatter description |
| 步骤指令、数据流定义 | SKILL.md 正文 |
| 解读规则、阈值参考、API 格式 | `references/` 子目录 |
| 数据提取脚本 | `scripts/` 子目录 |

**步骤编写原则：**
- 每步的输出要显式定义（"保存 JSON 供后续步骤使用"），避免步骤间丢失上下文
- 脚本层负责数据提取，SKILL.md 层负责解读和叙述，不混合
- 关键步骤提供 fallback（脚本报错时的手动处理路径）
- 长度控制在 500 行以内；超出时把 reference content 移到 `references/`

**减少用户交互轮次：**
- 可选参数写进 description，LLM 主动从用户输入中提取
- 支持自然语言参数（如「重点关注 translog」等价于 `focus=translog`），在 description 中注明
- 多个缺失参数合并成单次询问

---

### 泛化原则（通用工具类 skill）

- 框架/应用特定逻辑用注册表/配置驱动，不硬编码
- 报告模板从运行时数据动态生成，不硬编码应用特定的行/列
- 输出 `detected_frameworks` 等字段，让 LLM 根据检测结果条件性分析
- 应用特定的观察/建议放在条件判断下，保持通用路径干净

---

### 插件缓存更新

改动 SKILL.md 后需重新安装才能更新缓存：

```
/plugin uninstall <name>
/plugin install <name>@claude-spells
/reload-plugins
```

`/plugin` 显示 "already at latest version" 不代表缓存是最新的，需先 uninstall 再 install。
