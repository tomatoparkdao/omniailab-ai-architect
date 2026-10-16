# Agent Skills 兼容规范对照

OmniArchitect 遵循通用 Agent Skills 约定，不绑定任何单一厂商运行时。

## 1. 目录约定

```
omniailab-ai-architect/          ← 技能根（工作区根）
├── SKILL.md                     ← 唯一入口，YAML front-matter + 渐进式加载指引
├── AGENTS.md                    ← 开发约定（面向编码 Agent）
├── README.md
├── THIRD_PARTY_NOTICES.md       ← 第三方声明（唯一集中处）
├── knowledge/                   ← 12 个原创知识域 + INDEX.md（渐进式加载）
├── skills/                      ← 29 项专业能力说明（按需加载）
├── schemas/                     ← 统一空间模型 / 案例 / 工具能力 / 汇报
├── workflows/                   ← 阶段工作流定义
├── adapters/specs/              ← MCP / 外部工具适配规范
├── omniailab_ai_architect/      ← Python 包（真实执行代码）
├── installer/                   ← 安装与校验脚本
└── compatibility/               ← 本目录
```

## 2. SKILL.md front-matter

```yaml
---
name: omniailab-ai-architect
description: ...          # ≤1024 字符
version: 1.1.0
license: ...
---
```

约束（由 `python -m omniailab_ai_architect compat` 校验）：

- `name` 必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`；
- `description` 必填且 ≤1024 字符；
- `SKILL.md` 常驻加载体积 ≤24 000 字节 / ≤400 行，细节下沉到 `knowledge/` 与 `docs/`；
- 正文里出现的所有相对链接必须真实存在。

## 3. 渐进式信息加载

| 层级 | 内容 | 何时加载 |
| --- | --- | --- |
| L0 常驻 | `SKILL.md` | 每次会话 |
| L1 索引 | `knowledge/INDEX.md`、`skills/*` 的 front-matter | 判断需要哪个专业域时 |
| L2 领域 | `knowledge/<domain>.md` 单篇 | 该领域命中时 |
| L3 小节 | `knowledge` 单节 | 只需一条判据时 |
| L4 深层 | `docs/`、`cases/`、`adapters/specs/` | 需要规范、案例或适配细节时 |

```bash
python -m omniailab_ai_architect knowledge --resolve "客厅采光不足怎么改" --stage S3
python -m omniailab_ai_architect knowledge --domain lighting-design --outline
python -m omniailab_ai_architect knowledge --domain lighting-design --section "数值与区间"
```

## 4. 支持与已验证的运行环境

运行环境由 `detect_runtimes()` **探测**，不假设存在：

| key | 默认路径 | 说明 |
| --- | --- | --- |
| `workbuddy` | `~/.workbuddy/skills` | WorkBuddy 用户级技能目录 |
| `codex` | `~/.codex/skills` | OpenAI Codex 用户级技能目录 |
| `cursor` | `~/.cursor/skills-cursor` | Cursor 技能目录 |
| `claude` | `~/.claude/skills` | Claude Code 技能目录 |
| `project-workbuddy` | `<项目>/.workbuddy/skills` | 仅当前项目生效 |
| `project-agent` | `<项目>/.agent/skills` | 通用 Agent Skills 项目级 |

```bash
python -m omniailab_ai_architect compat
```

## 5. 安装模式

- **pointer（默认）**：技能目录里放 `SKILL.md` + `omniailab-home.txt` + `manifest.json`。
  真实工具链留在原仓库，升级只需 `git pull`，不会产生多份知识库副本。
- **copy**：整包复制（排除 `out/`、`third_party/`、`.git/`），适合整体搬移或离线分发。

安全约定：**任何安装/卸载都不删除内容**。目标已存在时先移动到
`<目标父目录>/_backup/`。请先 `--dry-run`。

## 6. 最小可用契约

任何运行环境只要满足以下三条即可驱动 OmniArchitect：

1. 能读写工作区文件；
2. 能执行 `python -m omniailab_ai_architect <cmd>`；
3. 能加载 `SKILL.md` 并按其指引按需读取 `knowledge/`。

不满足第 2 条（无 Python 执行能力）时，`SKILL.md`、`knowledge/`、`schemas/`、
`workflows/` 仍可作为纯知识与规范资产被读取——但**不会**产出图纸与模型，
此时系统不会声称具备执行能力。
