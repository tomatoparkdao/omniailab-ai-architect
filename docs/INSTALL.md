---
name: omniailab-install
description: 安装与独立运行 —— OmniArchitect 支持独立安装：不强制注册 OmniAiLab，不读取任何平台密钥，
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd?from=from_copylink
---

# 安装与独立运行

OmniArchitect 支持**独立安装**：不强制注册 OmniAiLab，不读取任何平台密钥，
离线可跑通几何、图纸、模型、工程量与汇报全链路。

---

## 1. 环境要求

| 项 | 要求 |
|---|---|
| Python | ≥ 3.10（开发与验证使用 3.13） |
| 硬依赖 | **无**。核心路径零第三方依赖 |
| 网络 | 非必需 |
| 平台账号 | 非必需 |

可选依赖（装了提升产物质量，不装自动降级，不阻断交付）：

```bash
python -m pip install ezdxf shapely jsonschema pyyaml Pillow python-pptx pytest
```

## 2. 直接使用（不安装）

```bash
cd "E:\SKILL\建筑室内设计skill\omniailab-ai-architect"
python -m omniarchitect doctor
python -m omniarchitect demo --out out
```

## 3. 安装到 Agent 运行环境

### 3.1 先试运行（不写任何文件）

```bash
python installer/install.py --dry-run
python installer/install.py --dry-run --target ~/.codex/skills
```

`--target` 是运行时的**技能根目录**，安装器会追加 `omniailab-ai-architect`。
也可以直接给出技能目录本身，两种写法等价。

### 3.2 两种模式

| 模式 | 内容 | 适用 |
|---|---|---|
| `pointer`（默认） | `SKILL.md` + `omniailab-home.txt` + `manifest.json` | 开发中；升级只需 `git pull`，不产生知识库副本 |
| `copy` | 整包复制（排除 `out/`、`.git/`） | 离线分发或整体搬移 |

```bash
python installer/install.py                              # 自动选已检测到的运行环境
python installer/install.py --target ~/.codex/skills
python installer/install.py --target ~/.codex/skills --mode copy
python installer/install.py --target ~/.workbuddy/skills
```

### 3.3 校验

```bash
python installer/verify_install.py --check-python
python installer/verify_install.py --target ~/.codex/skills/omniailab-ai-architect
python -m omniarchitect compat
```

校验内容：`SKILL.md` front-matter 合法性、正文引用是否都存在、指针是否指回真实仓库、
`manifest.json` 是否完整、Python 包能否导入、闭环工具（dxf / mesh）是否可用。

### 3.4 卸载

```bash
python -m omniarchitect uninstall --target ~/.codex/skills
python -m omniarchitect uninstall --dry-run
```

**卸载只移动，不删除**：内容进入 `<技能根>/_backup/omniailab-ai-architect-uninstalled-<时间戳>`。
同理，重复安装会先把旧安装移到 `_backup/omniailab-ai-architect-<时间戳>`，绝不覆盖丢失。

## 4. 运行环境探测

不假设存在，逐个探测：

| key | 路径 |
|---|---|
| `workbuddy` | `~/.workbuddy/skills` |
| `codex` | `~/.codex/skills` |
| `cursor` | `~/.cursor/skills-cursor` |
| `claude` | `~/.claude/skills` |
| `project-workbuddy` | `<项目>/.workbuddy/skills` |
| `project-agent` | `<项目>/.agent/skills` |

缺省按上表顺序选择第一个**已存在**的目录。

## 5. 清单与可复现性

```bash
python -m omniarchitect manifest --out installer/manifest.json
```

清单包含：技能元信息、文件清单（可选 sha256 前缀）、总字节数、
`standalone` 声明（是否需要平台账号 / 是否需要网络 / 硬依赖列表）。
`installer/manifest.json` 随仓库提供，便于分发方核对。

## 6. 自检与验收

```bash
python scripts/run_tests.py                 # 全部测试
python -m omniarchitect scenario --name all   # Scenario A/B/C 验收
```

验收口径：文件真实存在、格式经独立解析有效、内容与项目关联、可追溯版本、
可重复运行、**未以 Mock 通过宣称生产功能可用**。
缺少真实 MCP / API 的功能在报告中记为**跳过**，不记为通过。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
