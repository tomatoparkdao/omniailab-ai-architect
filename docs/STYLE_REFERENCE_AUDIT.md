---
name: omniailab-style-reference-audit
description: 参考项目审计 —— 五个参考仓库的许可证结论、只借鉴的方法范围，以及本工程的内容来源声明。
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 参考项目审计：许可证与技术组织方法

> 本文件记录五个参考仓库的**许可证审计结论**，以及本工程从它们身上**只借鉴组织方法**的范围。
> 审计日期：2026-10-16。审计方式：GitHub REST API 读取仓库元信息、文件树与 `LICENSE` 原文。

## 一、结论速览

| 参考仓库 | 许可证 | 可否复用内容 | 本工程的处理 |
|---|---|---|---|
| `jac2020-2020/architectural-visualization-prompt-library` | **MIT**（Copyright 2026 ArchOne AI） | 可（须保留版权与许可声明） | **未复用任何内容**；仅借鉴其目录分层与来源记录实践 |
| `ur-grue/autopunk-media-skills` | **MIT**（Copyright 2026 ur-grue） | 可（须保留版权与许可声明） | **未复用任何内容**；仅借鉴其 skill/测试分离与结构化数据驱动 |
| `yanliudesign/design-style-skill` | **无 LICENSE 文件** | **不可** | **不复用任何内容**；仅借鉴「每风格配预览图」这一思路（思路不受版权保护） |
| `RyanZhang10/interior-design-visualizer` | **无 LICENSE 文件** | **不可** | **不复用任何内容**；仅借鉴 references 三分类的文档组织 |
| `chrzamz/ui-styles-skill` | **MIT**（Copyright 2026 chrzamz）**＋上游镜像声明** | **不可复用其 `prompts/` 内容** | **未复用任何内容**；仅借鉴 `catalog.json` 索引 + 每风格独立文件 |

### 需要特别指出的两点

1. **`yanliudesign/design-style-skill` 与 `RyanZhang10/interior-design-visualizer` 没有许可证。**
   按默认著作权规则，未授予许可即保留全部权利。本工程**未读取、未复制、未改写**其任何文件内容。

2. **`chrzamz/ui-styles-skill` 的 `LICENSE` 带有一段附加声明**（原文）：
   > `NOTE: The UI style prompts under ``prompts/`` are mirrored from the upstream project … and remain the intellectual work of their original authors. See ATTRIBUTION.md for details.`

   即该仓库的提示词本身是**二次分发**的，其著作权属于上游作者。因此即便该仓库采用 MIT，
   其提示词内容也**不可由本工程复用**。本工程**未读取其提示词文本**。

## 二、只借鉴了「技术组织方法」

方法、思路与数据组织方式不受著作权保护；表达受保护。本工程据此只借鉴了下面这些**方法层**的做法，
并且全部**独立实现**：

| 借鉴的方法 | 来源 | 本工程的独立实现 |
|---|---|---|
| 单一索引文件 + 每个条目独立文件，按需加载 | `chrzamz/ui-styles-skill` 的 `catalog.json` | `catalog.json`（仅存可搜索字段）+ `knowledge/styles/<style_id>.json`（完整记录）；`catalog.py` 的 `load_style()` 按需读取 |
| 每个风格一个独立目录/文件 | 同上 | 一风格一 JSON，文件名 = `style_id` |
| 提示词按风格分离存放 | 同上 | `positive_prompt_components.zh/.en` 内嵌于风格记录，由 `compiler.py` 组装 |
| 归属与来源单独记录 | 同上（`ATTRIBUTION.md`）+ 第一个仓库（`SOURCES.md`、`CITATION.cff`） | 本文件 + `THIRD_PARTY_NOTICES.md` |
| 测试与实现分离，且覆盖到每个条目/能力 | `ur-grue/autopunk-media-skills` | `omniarchitect/tests/test_style_*.py` 五个模块，覆盖全部 47 条风格与全部 8 种提示词目标，覆盖全部 47 条风格与全部 8 种提示词目标 |
| 结构化数据驱动（大量 JSON） | 同上 | 47 条风格结构化数据，20 个必需字段，Schema 强校验 |
| 入口文件 + 清单元数据 | 同上（`.claude-plugin/`） | `SKILL.md` + `VERSION` + `pyproject.toml` |
| 规范层文档三分类 | `RyanZhang10/interior-design-visualizer`（design-reasoning / prompt-template / qa-checklist） | `docs/STYLE-DATA-SPEC.md`（规范）+ `compiler.py`（提示词）+ `quality_checklist` 字段（质检） |
| 每个风格配可视化预览 | `yanliudesign/design-style-skill` | `examples/` 下的对比与色板输出（由本工程自行生成，不含任何第三方图像） |
| 来源可追溯、可引用 | `jac2020-2020/…` | 风格记录的 `source` 字段固定为 `OmniAiLab`；本文件记录参考来源 |

## 三、本工程的内容来源声明

**47 条风格数据、20 个字段的全部内容、全部判据与全部提示词组件，均由本项目独立撰写。**

写作依据为：公开的建筑与室内设计通行做法、通用的材料与照明工程惯例、以及本项目自身的设计判据体系。
内容中不包含：

- 任何第三方仓库的提示词文本、案例描述或词表；
- 任何事务所名、项目名、作品名或设计师个人署名；
- 任何第三方品牌名（涂料/家具/灯具品牌一律不出现，只写材料品类）；
- 任何外部 URL。

风格记录中的 `history_and_context.key_movements` 只写**公认的设计运动或流派名称**
（例如「现代主义建筑运动」「工艺美术运动」）—— 这类名称属于公共知识，不构成对特定主体表达的复制。

## 四、许可证原文留档

`refs/` 目录下保留了三份 `LICENSE` 原文副本，**仅用于本次审计留档与合规复查**：

```
refs/LICENSE-jac2020-2020_architectural-visualization-prompt-library.txt   ( MIT, ArchOne AI )
refs/LICENSE-ur-grue_autopunk-media-skills.txt                             ( MIT, ur-grue )
refs/LICENSE-chrzamz_ui-styles-skill.txt                                    ( MIT, chrzamz + 上游镜像声明 )
```

两份无许可证的仓库没有可留档的许可证文件，故此处只记录其状态为「无许可证」。

> 留档的是**法律文件本身**（不是作品内容），保留原因：日后复查许可条件时需要原始文本。
> 本工程不随附、不分发上述任何仓库的作品内容。

## 五、若日后需要复用 MIT 仓库的内容

两个 MIT 仓库虽然许可允许复用，本工程**仍选择不复用**，理由有二：

1. 它们的内容领域（UI 风格提示词、影视/媒体技能）与本工程的实际用途不同，抄过来也不适用；
2. 混合来源会让「这条判据是谁写的」变得不可回答 —— 而本工程的正向价值恰恰是每一条判据都可追溯到自己的设计方法。

如未来确需引入，必须：在 `THIRD_PARTY_NOTICES.md` 逐项登记（含版权方与来源链接）、
保留原始版权声明、并在对应文件注明来源与许可。**不得删除法律要求的署名。**

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
