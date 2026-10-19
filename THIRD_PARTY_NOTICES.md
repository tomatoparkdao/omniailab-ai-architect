---
name: omniailab-third-party-notices
description: 第三方许可证与署名集中登记 —— 本仓唯一的第三方版权声明、许可证标识与来源链接存放处；普通设计成果与营销材料中不出现。
scope: 许可证与署名登记（唯一处）
version: 1.9.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 第三方许可证与署名登记

本文件是 OmniAiLab AI Architect（`omniailab-ai-architect`）仓库中**唯一**集中存放
第三方版权声明、许可证标识与来源链接的位置。

## 使用规则

1. **本文件与 `LICENSES/` 目录是第三方声明唯一合法的落点。**
   普通设计成果、汇报 PPT / PDF、README、SKILL.md、提示词、示例与用户界面中
   **不得**出现这里的第三方声明——它们只在需要履行署名义务的位置出现。
2. **本文件中的内容不得删除。** 删除第三方署名或版权声明以冒充自主开发，
   是明确禁止的行为。许可证要求的署名位置必须遵守。
3. **本仓不打包、不分发下列任何第三方源码或二进制。** 所列项目由使用者按需自行安装；
   本仓只在运行时通过其公开接口 / 命令行驱动，或在缺失时改用自有实现。
4. **OmniAiLab 不是这些项目的作者**，也不声称与其存在隶属或背书关系；
   同理，本仓不会把任何第三方代码或文档宣称为 OmniAiLab 原创。
5. 新增依赖前必须先做许可证核查，通过后在本文件登记，并在
   `omniarchitect/brand_policy.py: APPROVED_DEPENDENCIES` 同步。
   `python -m omniarchitect policy` 会逐项核对两边是否一致。

## 可选的 Python 依赖（缺失时均有自有降级实现）

本系统的核心路径**零硬依赖**。下表依赖全部为可选：装了就增强，不装就走自有实现。

| 项目 | 许可证（SPDX） | 版权持有方 | 来源 | 在本系统中的用途 |
|---|---|---|---|---|
| ezdxf | `MIT` | Manfred Moitzi | https://pypi.org/project/ezdxf/ · https://github.com/mozman/ezdxf | DXF R2010 写出与审计；缺失时用内置 R12 写出器 |
| Pillow | `MIT-CMU (HPND)` | Jeffrey A. Clark 及 Pillow 贡献者 | https://pypi.org/project/Pillow/ · https://github.com/python-pillow/Pillow | 本地确定性示意图栅格化；缺失时跳过图像输出 |
| python-pptx | `MIT` | Steve Canny | https://pypi.org/project/python-pptx/ · https://github.com/scanny/python-pptx | PPTX 主写出后端；缺失时用内置 OOXML 写出器 |
| jsonschema | `MIT` | Julian Berman | https://pypi.org/project/jsonschema/ · https://github.com/python-jsonschema/jsonschema | Schema 校验；缺失时用内置子集校验器 |
| shapely | `BSD-3-Clause` | Sean Gillies 及贡献者 | https://pypi.org/project/shapely/ · https://github.com/shapely/shapely | 多边形布尔运算；缺失时用内置矩形-多边形裁剪 |
| pytest | `MIT` | Holger Krekel 及 pytest-dev | https://pypi.org/project/pytest/ · https://github.com/pytest-dev/pytest | 测试运行；缺失时用 `scripts/run_tests.py` |

上述项目的许可证全文与完整版权声明，请以其官方发布包内 `LICENSE` 文件为准；
如需再分发其代码或二进制，必须随附其许可证全文与版权声明。

## 设计风格系统的内容来源（全部自有）

**`knowledge/styles/` 的 47 条风格记录全部由本项目独立原创撰写**，写作依据为公开的
建筑与室内设计通行做法、通用的材料与照明工程惯例，以及本项目自有的设计判据体系。

内容中不包含：

- 任何第三方的提示词文本、案例描述、词表、审美偏好或品牌视觉；
- 任何第三方项目名、作者名、事务所名、项目名或作品名；
- 任何第三方品牌名（涂料 / 家具 / 灯具品牌一律不出现，只写材料品类）；
- 任何外部链接。

风格记录的 `source` 字段固定为 `OmniAiLab`；`history_and_context.key_movements`
只写**公认的设计运动或流派名称**（如「现代主义建筑运动」）——这类名称属于公共知识，
不构成对特定主体表达的复制。

写作纪律（违反即返工）见 `docs/DESIGN_STYLES.md`「三、内容纪律」，
集成方式见 `docs/STYLE_INTEGRATION.md`。

**本节不登记任何第三方项目，因此 `LICENSES/` 下不存在与本系统相关的许可证留档。**

---

## 未随本仓分发的宿主软件与库

以下软件**不由本仓提供**，也不构成对本仓的许可证依赖。使用者在本机自行安装后，
本系统可通过命令行或 MCP 驱动它们完成几何建模、BIM 与专业文件处理。

| 项目 | 许可证（SPDX） | 版权持有方 | 来源 | 在本系统中的角色 |
|---|---|---|---|---|
| Blender | `GPL-2.0-or-later` | Blender Foundation | https://www.blender.org/ | 本机三维场景构建与渲染宿主 |
| FreeCAD | `LGPL-2.1-or-later` | FreeCAD 贡献者 | https://www.freecad.org/ | 本机参数化建模宿主 |
| IfcOpenShell | `LGPL-3.0-or-later` | IfcOpenShell 贡献者 | https://ifcopenshell.org/ · https://github.com/IfcOpenShell/IfcOpenShell | IFC 读写能力来源 |
| AutoCAD | `Proprietary` | Autodesk, Inc. | https://www.autodesk.com/ | 仅在用户自有授权环境下驱动，用于另存 DWG |

**注意**：`GPL` / `LGPL` 项目以独立进程方式被调用，本仓代码不与其链接、不修改其源码、
不随本仓分发。若在分发场景中需要更多说明，请参考各项目的许可证文本。

## 规范与格式

本仓生成的文件用到以下公开规范命名空间，它们**不是**第三方广告或推广链接：

| 命名空间 / 规范 | 用途 |
|---|---|
| `http://schemas.openxmlformats.org/...` | OOXML（PPTX）包结构 |
| `http://purl.org/dc/elements/1.1/` | Dublin Core 元数据 |
| `http://www.w3.org/...` | XML / SVG 规范 |
| `https://json-schema.org/...` | JSON Schema 元 schema |

## 与品牌策略的关系

本仓的品牌与供应商策略（`omniarchitect/brand_policy.py`、
`docs/BRAND_POLICY.md`）规定：

- **合规必要项**（本文件与 `LICENSES/` 中的许可证、版权声明、来源链接、署名）
  一律保留，被扫描器归入 `compliance-required`，**不计入待处理项**；
- **已授权依赖**（上表中的可选依赖、本机宿主软件、已登记的本地 MCP）
  被归入 `authorized-dependency`，允许存在但位置受限；
- 外部商业 AI 创作平台、未登记模型供应商、隐式 endpoint、第三方凭据与非法
  fallback 被归入 `forbidden`，必须移除。

许可证原文目录见 `LICENSES/`。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
