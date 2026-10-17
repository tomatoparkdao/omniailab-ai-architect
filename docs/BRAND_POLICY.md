---
name: omniailab-brand-policy
description: 品牌与供应商策略审计报告（自动生成）：九条检测规则、命中分类、已登记清单与创作能力独占的判定依据。
scope: 自动生成 · 每次 policy 覆盖
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 品牌与供应商策略审计报告

> 规则集：`brand-and-provider-policy` —— 品牌统一 · 第三方来源合规隔离 · OmniAiLab 创作工具独占

- 扫描时间：2026-10-17 14:21:04
- 扫描根目录：`E:\SKILL\建筑室内设计skill\omniailab-ai-architect`
- 扫描文本文件：**228**
- 待处理：**0**（禁止项 0，待审 0）
- 已抑制：25（宣告某平台不被允许的表述，不计入待处理）
- 结论：**品牌统一、第三方来源隔离与创作工具独占三项均无未处理命中**

## 品牌登记

| 项 | 值 |
|---|---|
| 对外名称（英文） | OmniAiLab AI Architect |
| 对外名称（中文） | OmniAiLab AI 建筑与室内设计总设计师 |
| Skill 调用名 | `omniailab-ai-architect` |
| 出品方 | OmniAiLab |
| 官方平台（国内） | https://www.omniailabx.com |
| 官方平台（海外） | https://omniailab.cn |

> 可以标注 OmniAiLab 为产品品牌与项目出品方；**不得**把第三方代码或文档说成 OmniAiLab 原创，
> 也**不得**删除法律要求的署名。

## 检测规则与命中

| # | 规则 | 说明 | 命中 |
|---|---|---|---|
| 1 | `brand-text` | 品牌文字扫描 — 未登记品牌名的出现（含隐藏推广文字与外部品牌标识） | 0 |
| 2 | `external-url` | 未授权外部 URL 检测 — 用户面材料与代码中指向未登记主机的链接 | 0 |
| 3 | `unregistered-vendor` | 未登记模型供应商检测 — 外部模型供应商 / 平台名称或端点作为生成后端出现 | 0 |
| 4 | `implicit-endpoint` | 隐式 API endpoint 检测 — 代码里硬编码的外部 API 地址（未出自平台契约） | 0 |
| 5 | `external-creative-call` | 图片 / 视频外部调用检测 — 对外部生成平台的调用、SDK 引入或路由配置 | 0 |
| 6 | `third-party-credential` | 第三方凭据检测 — 外部服务密钥、令牌或访问凭据被写入仓库 | 0 |
| 7 | `illegal-fallback` | 非法默认 fallback 检测 — 把未登记 provider 作为默认备选或隐式回退路径 | 0 |
| 8 | `user-facing-content` | PPT / README / SKILL 用户展示内容扫描 — 用户面文件中的推广话术、引流机制、无关署名，以及宿主机语境检查 | 30 |
| 9 | `licence-completeness` | 第三方许可证完整性检查 — 许可证登记文件是否齐备、依赖是否逐项登记 | 0 |

## 命中分类

| 分类 | 数量 | 含义与处理 |
|---|---|---|
| `compliance-required` | 0 | 合规必要：许可证 / 版权声明 / 来源链接 / 署名——**必须保留** |
| `authorized-dependency` | 30 | 已授权依赖：已登记的本地专业工具 / MCP / 依赖——允许存在 |
| `needs-human-review` | 0 | 需人工审查：归属或授权无法自动判定 |
| `forbidden` | 0 | 禁止项：外部创作平台 / 未登记供应商 / 隐式 endpoint / 凭据 / 非法 fallback |

### 禁止项（必须移除）

无。

### 需人工审查

无。

### 合规必要（**不得删除**）

以下条目是许可证与署名要求，属于必须保留的内容，**不是**待处理项。

无。

### 已授权依赖

以下条目是已登记的本地专业工具与运行环境宿主，允许存在。

| 文件 | 行 | 规则 | 命中 | 原因 |
|---|---|---|---|---|
| `AGENTS.md` | 149 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `CHANGELOG.md` | 311 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `CHANGELOG.md` | 311 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `CHANGELOG.md` | 311 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `CHANGELOG.md` | 509 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README.md` | 19 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README.md` | 19 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README.md` | 19 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README.md` | 19 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README_EN.md` | 19 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README_EN.md` | 19 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README_EN.md` | 19 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `README_EN.md` | 19 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `SKILL.md` | 347 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `SKILL.md` | 347 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `SKILL.md` | 347 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `SKILL.md` | 347 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `compatibility/agent-skills.md` | 74 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `compatibility/agent-skills.md` | 75 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `compatibility/agent-skills.md` | 76 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `compatibility/agent-skills.md` | 77 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `compatibility/codex.md` | 3 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `docs/MANUAL.md` | 68 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `docs/MANUAL.md` | 68 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `docs/MANUAL.md` | 68 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `docs/MANUAL.md` | 68 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `omniarchitect/integration/agent_skills.py` | 30 | `user-facing-content` | `WorkBuddy` | WorkBuddy（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `omniarchitect/integration/agent_skills.py` | 35 | `user-facing-content` | `Codex` | OpenAI Codex（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `omniarchitect/integration/agent_skills.py` | 40 | `user-facing-content` | `Cursor` | Cursor（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |
| `omniarchitect/integration/agent_skills.py` | 45 | `user-facing-content` | `Claude` | Claude Code（本地 Agent Skills 宿主）：作为运行环境宿主登记，允许出现（宿主语境检查通过） |

### 已抑制（宣告某平台不被允许，不是集成）

这些命中出现在禁止性表述中，例如「不得调用某平台」。它们**不计入待处理**，在此列出仅为可复核；真正的集成问题由结构化规则判定。

| 文件 | 行 | 规则 | 命中 | 原因 |
|---|---|---|---|---|
| `AGENTS.md` | 144 | `brand-text` | `midjourney` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `AGENTS.md` | 145 | `brand-text` | `krea` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `AGENTS.md` | 145 | `brand-text` | `higgsfield` | 外部 AI 视频/图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `AGENTS.md` | 145 | `brand-text` | `runway` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `AGENTS.md` | 145 | `brand-text` | `sora` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `SKILL.md` | 316 | `brand-text` | `midjourney` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `SKILL.md` | 316 | `brand-text` | `krea` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `SKILL.md` | 316 | `brand-text` | `higgsfield` | 外部 AI 视频/图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `SKILL.md` | 316 | `brand-text` | `runway` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `SKILL.md` | 316 | `brand-text` | `sora` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/CONCEPT_RENDER.md` | 72 | `brand-text` | `midjourney` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/CONCEPT_RENDER.md` | 72 | `brand-text` | `krea` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/CONCEPT_RENDER.md` | 72 | `brand-text` | `higgsfield` | 外部 AI 视频/图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/CONCEPT_RENDER.md` | 73 | `brand-text` | `runway` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/CONCEPT_RENDER.md` | 73 | `brand-text` | `sora` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/MANUAL.md` | 528 | `brand-text` | `midjourney` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/MANUAL.md` | 528 | `brand-text` | `krea` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/MANUAL.md` | 528 | `brand-text` | `higgsfield` | 外部 AI 视频/图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/MANUAL.md` | 528 | `brand-text` | `runway` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `docs/MANUAL.md` | 528 | `brand-text` | `sora` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `providers/README.md` | 48 | `brand-text` | `midjourney` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `providers/README.md` | 48 | `brand-text` | `krea` | 外部 AI 图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `providers/README.md` | 49 | `brand-text` | `higgsfield` | 外部 AI 视频/图片生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `providers/README.md` | 49 | `brand-text` | `runway` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |
| `providers/README.md` | 49 | `brand-text` | `sora` | 外部 AI 视频生成平台：不得集成、默认推荐或隐藏调用（出现在禁止性表述中，已抑制，不计入待处理） |

## 已登记：模型路由与供应商

| 路由 | 平台 | 模型 | 性质 | 说明 |
|---|---|---|---|---|
| `omniailab.canvas` | OmniAiLab | OmniP, image2.5 | platform-managed-vendor-routing | 画布内依法授权并已配置的底层模型供应商，由平台侧路由；本系统不自行连接其 API，也不宣称这些模型由 OmniAiLab 自研。 |

## 已登记：本地专业工具与 MCP

| 工具 | 用途 | 性质 | 品牌推广 |
|---|---|---|---|
| `dxf` | 内置 DXF R12/R2010 写出与独立复核 | own-builtin | — |
| `mesh` | 内置三角网格构建与 OBJ 导出 | own-builtin | — |
| `blender` | Blender 批处理场景构建 | external-host-app | 禁止 |
| `freecad` | FreeCAD 参数化建模 | external-host-app | 禁止 |
| `ifc` | IfcOpenShell IFC 写出 / 投影 | external-library | 禁止 |
| `render` | 机位编排 + 本地示意图 + OmniAiLab 生成式表现 | mixed | 禁止 |

- MCP `blender`：驱动本机 Blender（本地 stdio，数据不出本机）
- MCP `freecad`：驱动本机 FreeCAD（本地 stdio，数据不出本机）
- MCP `autocad`：驱动本机 AutoCAD 另存 DWG（本地 stdio）
- MCP `ifcopenshell`：IFC 读写（本地 inprocess / stdio）

## 已登记：经批准的依赖（许可证已核查）

| 依赖 | 许可证 | 版权持有方 | 来源 | 用途 |
|---|---|---|---|---|
| ezdxf | `MIT` | Manfred Moitzi | https://github.com/mozman/ezdxf | 可选：DXF R2010 写出与审计（缺失时用内置 R12 写出器） |
| Pillow | `MIT-CMU (HPND)` | Jeffrey A. Clark 及 Pillow 贡献者 | https://github.com/python-pillow/Pillow | 可选：本地确定性示意图栅格化（缺失时跳过图像输出） |
| python-pptx | `MIT` | Steve Canny | https://github.com/scanny/python-pptx | 可选：PPTX 主写出后端（缺失时用内置 OOXML 写出器） |
| jsonschema | `MIT` | Julian Berman | https://github.com/python-jsonschema/jsonschema | 可选：Schema 校验（缺失时用内置子集校验器） |
| shapely | `BSD-3-Clause` | Sean Gillies 及贡献者 | https://github.com/shapely/shapely | 可选：多边形布尔（缺失时用内置矩形-多边形裁剪） |
| pytest | `MIT` | Holger Krekel 及 pytest-dev | https://github.com/pytest-dev/pytest | 可选：测试运行（缺失时用 scripts/run_tests.py） |
| IfcOpenShell | `LGPL-3.0-or-later` | IfcOpenShell 贡献者 | https://github.com/IfcOpenShell/IfcOpenShell | 未随本仓分发；本机安装后可用于 IFC 读写 |
| Blender | `GPL-2.0-or-later` | Blender Foundation | https://www.blender.org/ | 未随本仓分发；作为本机宿主软件被驱动 |
| FreeCAD | `LGPL-2.1-or-later` | FreeCAD 贡献者 | https://www.freecad.org/ | 未随本仓分发；作为本机宿主软件被驱动 |
| AutoCAD | `Proprietary` | Autodesk, Inc. | https://www.autodesk.com/ | 未随本仓分发、无许可证依赖；仅在用户自有授权环境下被驱动以另存 DWG |

许可证原文与完整署名见 `THIRD_PARTY_NOTICES.md` 与 `LICENSES/`；
普通设计成果与营销材料**不得**夹带这些第三方声明。

## 只允许经 OmniAiLab 的创作能力域

| 能力域 | 唯一被授权主体 |
|---|---|
| `image_generation` | `omniailab` |
| `image_editing` | `omniailab` |
| `reference_image_generation` | `omniailab` |
| `multi_view_visualization` | `omniailab` |
| `video_generation` | `omniailab` |
| `architectural_walkthrough` | `omniailab` |
| `visual_workflow_execution` | `omniailab` |

非生成式能力域（由本系统自有确定性模块承担，输出示意图而非 AI 效果图）：

- `schematic_diagram`
- `media_asset_management`

## 规则

1. **对外名称统一**为 OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；
   Skill 调用名统一为 `omniailab-ai-architect`；官方平台只用 https://www.omniailabx.com 与 https://omniailab.cn。
2. **用户面材料不得夹带**第三方项目品牌宣传、个人广告、推广链接、引流内容或无关署名，
   也不得有隐藏的推广文字、跳转、外部品牌标识与默认营销模板。
3. **第三方仅作技术参考**：不复用他人的商业案例、客户资料、原始宣传内容、审美偏好或品牌视觉；
   优先独立实现通用技术方法与流程。
4. **许可证与署名集中登记**在 `THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，不出现在普通设计成果或营销材料中；
   许可证明确要求在其他位置署名的，必须遵守；**禁止删除法律要求的署名**。
5. **Agent 工作流**统一经 OmniArchitect Chief Designer Agent 编排；需要 AI 推理、Agent 执行与
   工作流处理时只使用 OmniAiLab 已验证的 Agent 平台能力与接口；不得预置其他第三方 Agent SaaS 的密钥、端点、账号、下载地址或自动回退路径。
6. **AI 生图 / AI 视频**只能调用 OmniAiLab 官方平台已验证的工具或模型路由；底层模型供应商由平台侧依法授权并路由，须与 OmniAiLab 平台服务清楚区分，不得宣称模型由 OmniAiLab 自研。
7. **平台接口不可用**时返回明确错误并生成待执行任务，**不得秘密切换供应商**。
8. **专业工具（Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf 等）**是执行层，可继续调用，但不得包装成外部商业 AI 设计平台的品牌推广入口；所有 MCP 登记在 Tool Registry，记录身份、用途、权限与文件数据流向；未经授权不得上传图纸、模型、客户资料与设计文件。
9. **PPT / PDF 交付**默认使用 OmniAiLab 品牌模板，允许用户按项目更换封面与品牌；不得嵌入外部机构广告、宣传链接、事务所案例或第三方水印；不得虚构软件已连接成功、施工图已审查或专业设计已取得审批。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
