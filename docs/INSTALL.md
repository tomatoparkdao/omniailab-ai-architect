---
name: omniailab-install
description: 安装与独立运行 —— OmniArchitect 支持独立安装：不强制注册 OmniAiLab，不读取任何平台密钥，
version: 1.21.2
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
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
python -m omniarchitect workspace        # 先看产物会写去哪
python -m omniarchitect demo             # 示例项目跑通八阶段（结果写工作区，不写技能目录）
```

产物默认落在**外部运行工作区**，不在技能目录里 —— 见第 7 节。

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
| `copy` | **白名单复制**：只发能力（技能定义 / 代码 / 知识 / 风格 / Schema / 文档 / 安装器），不含项目、测试、开发脚本、缓存 | 离线分发或整体搬移 |

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

## 7. 运行工作区（设计成果不放技能目录）

技能包是**能力定义**：技能描述、代码、知识库、风格库、Schema、MCP 适配器、安装脚本。
房子不该盖在工具箱里 —— 客户项目、图纸、模型、效果图、视频、PPT、交付文件、
测试产物、缓存，全部写进**外部运行工作区**。

| 分区 | 内容 | 可再生 |
|---|---|---|
| `projects/` | 真实客户项目（`project.json` 与版本记录） | 否，需备份 |
| `outputs/` | CAD / 模型 / 效果图 / PPT / HTML / 工程量 / 交付文件 | 由项目重算 |
| `tests/` | 测试与演示产物、截图、验收报告 | 是 |
| `cache/` | 中间缓存（栅格化、下载、场景） | 是 |
| `archive/` | 历史运行资料与旧验收产物留档 | 否 |

默认根目录：

| 平台 | 默认路径 |
|---|---|
| Windows | `E:\OmniAiLab-Workspace\Architect`（`E:` 不存在时用 `%USERPROFILE%\OmniAiLab-Workspace\Architect`） |
| macOS | `~/Library/Application Support/OmniAiLab/Architect` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/omniailab/architect` |

覆盖方式（优先级从低到高）：

```bash
OMNIAILAB_WORKSPACE          # 工作区根，改这个五个分区整体搬家
OMNIAILAB_PROJECTS_DIR       # 单分区覆盖
OMNIAILAB_OUTPUT_DIR
OMNIAILAB_TESTS_DIR
OMNIAILAB_CACHE_DIR
OMNIAILAB_ARCHIVE_DIR
OMNI_TEST_OUTPUT             # 兼容旧变量，等价于 OMNIAILAB_TESTS_DIR
```

`--out` 之类**显式**给出的路径原样使用，不会被重定向。

```bash
python -m omniarchitect workspace          # 打印五个分区与技能目录体积
python -m omniarchitect workspace --json
```

## 8. 分发审计（装之前先看包里有什么）

```bash
python -m omniarchitect package            # 白名单清单 + 夹带检查
python -m omniarchitect package --json
```

八项检查：包总大小、单文件大小（1 MB 上限）、禁止分发的扩展名、
是否混入项目/测试/缓存、`manifest.json` 与包内容是否逐条一致、
非文档文件里是否写死本机绝对路径、是否像凭据、顶层目录分布。
违规时退出码非 0，安装前就能拦住 —— 而不是装完了才发现带了一堆效果图。

`installer/manifest.json` 由 `python -m omniarchitect manifest` 重建，
文件列表等于白名单，多一个少一个都会被审计判为过期。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
