---
name: omniailab-compatibility-codex
description: OmniArchitect × OpenAI Codex —— OmniArchitect 是一个标准 Agent Skill：仓库根目录的 SKILL.md 是入口，
version: 1.10.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# OmniArchitect × OpenAI Codex

OmniArchitect 是一个标准 Agent Skill：仓库根目录的 `SKILL.md` 是入口，
`knowledge/`、`skills/`、`adapters/specs/`、`docs/` 按需加载，不需要把 2500 行知识
一次性塞进上下文。

## 1. 把工作区设成项目根

Codex 是否可写取决于**工作区**，不是提示词。请先切换工作区：

```bash
cd "E:\SKILL\建筑室内设计skill\omniailab-ai-architect"
codex
```

桌面版：直接把项目文件夹作为工作区打开，再新建一个会话。

`AGENTS.md` 会固定开发路径与约定，但它**不能替代正确设置工作区**。

## 2. 三种接入方式

| 方式 | 命令 | 适用 |
|---|---|---|
| 直接用仓库 | 工作区指向本目录即可 | 开发与调试 |
| 指针安装 | `python -m omniarchitect install --target ~/.codex/skills --mode pointer` | 让 Codex 在任意项目里都能调用，且不复制知识库 |
| 完整安装 | `python -m omniarchitect install --target ~/.codex/skills --mode copy` | 需要完全自包含、可整体搬移 |

安装前先看会发生什么（不写任何文件）：

```bash
python -m omniarchitect install --target ~/.codex/skills --dry-run
```

安装后校验：

```bash
python -m omniarchitect compat --json
python -m omniarchitect manifest
```

卸载只做移动，不做删除：

```bash
python -m omniarchitect uninstall --target ~/.codex/skills
```

## 3. Codex 里的常用指令

```bash
python -m omniarchitect doctor          # 本机工具链
python -m omniarchitect tools           # 工具注册表 + 权限分级
python -m omniarchitect stages          # 八阶段与门禁
python -m omniarchitect knowledge       # 12 个原创知识域
python -m omniarchitect demo            # 示例项目跑通八阶段
python -m omniarchitect scenario --name all
```

## 4. 独立运行 vs 平台连接

- **独立模式（默认）**：不需要注册 OmniAiLab，不读取任何平台密钥，
  不联网即可产出 DXF、网格模型、工程量与汇报文件。
- **平台连接模式**：仅当检测到官方 SDK、本地配置或平台下发的 API 契约时启用；
  未通过验证的能力一律标记 `NOT_CONFIGURED`，不伪造成功结果。

```bash
python -m omniarchitect providers        # 查看当前连接状态
python -m omniarchitect providers --json # 机器可读
```

## 5. 环境要求

- Python ≥ 3.10；核心路径**零硬依赖**。
- 可选依赖见 `requirements.txt`：装了提升产物质量，不装自动降级。
- 本机若没有 Blender / FreeCAD / AutoCAD / IfcOpenShell，适配器输出可在有环境的机器上
  直接运行的脚本，并在报告中标注 `degraded`。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
