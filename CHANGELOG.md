---
name: omniailab-changelog
description: 变更记录 —— 自 v1.0.0（八阶段工作流）增量开发，未重建项目、未覆盖既有成果、既有测试全部保留并通过。
version: 1.1.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
---

# 变更记录

## v1.2.0 — 平面确认后的概念效果图（OmniAiLab 画布）

**新增能力：平面方案通过门禁 G3 之后，立即以该平面为依据生成概念效果图，交给业主建立空间感受。**

### 新增

- **能力 `concept-visualization`（概念效果图）**：参与 S3 / S4，能力总数 29 → **30**。
- **门禁后置动作机制**：`stages.py: POST_GATE_ACTIONS = {"G3": ["concept-visualization"]}`。
  后置动作没有自己的门禁、不能单独确认，只在所在门禁通过的那一刻执行；
  门禁被打回时，其记录会被清除。新增铁律 **R5**：概念效果图只能在业主确认的平面上生成。
- **画布工作流** `providers/canvas.py`：
  - 机位规划取自统一空间模型（整户型 1 张 + 主要空间各 1 张，视高 / 镜头 / 光线 / 材料均来自模型）；
  - 提示词由模型数据组装，携带项目标识、修订号与方案号，并计算**提示词指纹**用于跨轮追踪；
  - 参考图为**已确认平面**的本地栅格化输出（与 DXF 共用绘图基元，图与图纸不会互相矛盾）；
  - 提交走 provider 编排：提交 → 轮询 → 取回，带**有界重试**；属 **L3 联网**操作，未授权时停在授权点；
  - 产出 `canvas-jobs.json` / `canvas-payload.json` / `canvas-brief.md` / `RUN-STATUS.md` / `models.json`
    / `reference/*.png`，平台已连接时另有 `renders/*.png` 与逐机位资产版本关联。
- **模型声明** `providers/omniailab.models.json`：推荐 **OmniP**（整体空间氛围、多机位一致）与
  **image2.5**（跟随已确认平面、材质细节），含取向规则与优先级；
  与平台契约的 `models` 交叉校验，冲突时**以契约为准**并记录偏差，不硬套平台不提供的模型。
- **契约模板** `providers/omniailab.api.example.json` + `providers/README.md`：
  含 `FILL_ME` 占位符的模板会被识别并**拒绝**——模板不等于可用契约。
- **汇报类型 `concept-rendering`**：逐机位一页（图 / 模型 / 状态 / 提示词指纹），
  页面内容读自 `canvas-jobs.json`，因此幻灯片不会描述一个从未被规划的机位；
  未生成的机位展示参考图并写明状态，**不用替代图充数**。
- **知识域** `ai-concept-visualization`（AI 概念表现方法论）：知识库 12 → **13** 个领域。
- **Schema** `schemas/concept-render.schema.json`。
- **CLI**：`concept-render`、`canvas-models` 两个命令。
- **文档** `docs/CONCEPT_RENDER.md`；README 中英双版、SKILL.md、AGENTS.md、WORKFLOW、ARCHITECTURE、
  OMNIAILAB_INTEGRATION、PRESENTATION 同步更新。
- **验收**：Scenario A 增加 6 项概念效果图检查（任务包存在 / 可解析 / 机位指向已确认平面 /
  逐张可追溯 / 模型按声明选择 / 状态口径未混淆且未伪造图像 + 汇报 PPTX 独立复核）。
- **测试** 164 → **180** 项（新增 `test_concept_render.py`，14 个模块）。

### 设计取舍

- **不做成第九个阶段**：概念效果图的成立条件完全由 G3 决定。做成独立阶段会诱导使用者
  "单独确认"这一步，从而绕过平面确认——那正是最贵的错误。
- **在 fork 上渲染**：G3 确认的是方案，方案在 S4 才安装为深化依据。因此门禁后置动作
  不改写统一空间模型，项目修订号也不会因为"确认了一下"而跳动。
- **不写占位图**：平台未连接时逐张标 `awaiting_platform`，状态与产出严格对应
  （有 `generated` 才有图），由验收脚本当作硬口径检查。


## v1.1.0 修订 — 内容自有化与署名规范

**全仓完成内容自有化**：移除全部外部项目痕迹，全部文档与交付物统一 OmniAiLab 署名格式。

### 移除

- 删除上游参考仓库的本地副本（可再生、未纳入本仓库历史）与全部相关声明文件；
  本仓库不再保留、不再分发任何外部项目内容。
- 代码与文档中的外部项目名、作者名、仓库地址、商业推广链接**全部清除**：
  `registry.py`、`workflow.py`、`stages.py`、`paths.py`、`changes.py`、`cli.py`、`docs/`、`AGENTS.md`、`.gitignore`、`pyproject.toml`。
- `python -m omniailab_ai_architect fusion` / `notices` 两个命令移除，改为 `criteria`（设计判据体系）。

### 新增

- **统一署名**：`registry.py: SIGNATURE`（长）/ `SIGNATURE_SHORT` / `SIGNATURE_SHORT_EN` 三个常量，
  51 份 Markdown 全部加上标准 front-matter（`author: OmniAiLab` / `developer: Mochiball` / `agent_created: true`）与末尾署名行；
  自动生成的阶段文档、汇报 Markdown 与交付包 README 同样带署名。
- **中英双语 README**：`README.md`（简体中文，主推中国站）+ `README_EN.md`（English，主推海外站），
  排版与格式对齐 OmniAiLab 产品线：居中标题 / 徽章 / 语言切换 / 一句话 / 能力一览 / 快速开始 / 文档地图 / 出处与致谢 / 页脚署名。
- `LICENSE`（MIT，© OmniAiLab / Mochiball）与 `VERSION`（1.1.0）。
- `docs/DESIGN_CRITERIA.md`：九组设计判据的正式说明（自有口径，源自通用设计原理与公开工程惯例）。

### 变更

- `ARCH_ATTRIBUTION` / `ARCH_FUSION` → `PROJECT_ATTRIBUTION` / `DESIGN_CRITERIA`（键名与内容全部自有化）。
- `compliance_audit.py` 从"第三方内容审计"改为**内容合规自检**：署名是否齐全 / 是否泄露个人信息 /
  用户面是否有外部链接 / 许可证文本是否只在 `LICENSE` 内；报告改为 `docs/CONTENT_AUDIT.md`。
- 新增源码级守卫测试：`test_every_document_carries_the_omniailab_signature`、
  `test_no_borrowed_branding_anywhere_in_the_tree`（全仓扫描，命中即失败）。
- 既有的 65 项与新增的 99 项测试**全部保留并通过**（164 项 / 13 个模块，零失败）。

## v1.1.0 — OmniAiLab 集成、原创化与交付能力

自 v1.0.0（八阶段工作流）增量开发，**未重建项目、未覆盖既有成果、既有测试全部保留并通过**。

### 目录与命名

- 项目根目录 `omniarchitect/` → **`omniailab-ai-architect/`**（同时是 Agent Skill 根）。
- Python 包改为根目录下的子目录 `omniailab_ai_architect/`（根目录名含连字符，不可直接导入）。
- 父目录遗留的 `out/`、`projects/` 已安全归并进项目，**未删除任何内容**。

### 新增

| 子系统 | 内容 |
| --- | --- |
| 内容合规 | `compliance_audit.py` 可执行扫描器（署名 / 隐私 / 外链 / 许可四类判定）、`docs/CONTENT_AUDIT.md` |
| 原创知识库 | `knowledge/` 12 个领域（约 2 480 行，全部原创）+ `INDEX.md` + 渐进式加载器；`cases/` 3 个通用案例模板；`schemas/case.schema.json` |
| 平台 provider | `providers/`：OmniAiLab 发现式适配器（SDK / 配置 / API 契约）+ 本地确定性 provider；能力发现、模型选择、任务提交、状态轮询、媒体取回、失败重试、成本估算、资产版本关联 |
| 工具执行 | `tools/`：统一工具注册表、L1–L4 权限分级、危险操作确认、产物独立校验、能力真实性规则；`schemas/tool-capability.schema.json` |
| 设计汇报 | `presentation/` + `skills/design-presentation.md` + `schemas/presentation.schema.json`：9 种汇报类型 → 可编辑 PPTX / Markdown / HTML / PDF |
| 独立运行 | `integration/`：Agent Skills 契约校验、运行环境探测、只移不删的安装器；`installer/`、`compatibility/` |
| 验收 | `scenarios.py`：Scenario A/B/C 端到端验收 + 验收报告；`scripts/verify_all.py` 增加 v1.1 子系统检查 |
| 命令 | `audit` `notices` `providers` `tools` `honesty` `knowledge` `present` `scenario` `compat` `install` `uninstall` `manifest` |

### 变更

- `SKILL.md` 重写为渐进式加载入口（241 行 / 11.4 KB，细节下沉到 `knowledge/`、`docs/`）。
- 能力目录 28 → **29 项**：新增跨阶段能力 `design-presentation`（S2–S8）。
- 用户面材料（`SKILL.md`、`README.md`、`skills/`、`knowledge/`、`cases/`、汇报模板）**不再出现第三方品牌名与推广链接**；
  全部文档与交付物统一署名（`registry.py: SIGNATURE`）。
- `render` 适配器改为向 provider 注册表查询可用后端，不再硬编码空列表。
- stage S2 的概念文档与意向板增加「项目 + 模型修订 + 生成时间」页脚，使汇报可追溯到同一修订。
- 工作流阶段 B 的验收不再跳过 S6 门禁（S7 必须在其确认后进行）。

### 修正

- `ezdxf.recover` 子模块需显式导入（此前在装了 ezdxf 的机器上会失败）。
- DXF 校验器现在同时支持 R12 与 R2007+ 方言，并按内容判定 `.dwg`（改名不等于 DWG）。
- DXF 读取容忍 UTF-8 方言，中文标注不再被解成 `?`。
- 知识库 front-matter 解析支持块状列表（此前 `review_results` 等字段会被读成空）。
- `knowledge.resolve()` 的阶段加权只放大已有命中，不再制造命中（原先回退逻辑永不触发）。
- 安装器 `--target` 语义明确为「运行时技能根」，避免误把技能根当作技能目录覆盖。
- 审计器区分「署名义务」「商业推广」「个人/客户信息」「测试夹具」，不再互相污染。

### 测试

`65 → 164` 项，13 个测试模块。新增：provider、tools、presentation、knowledge、integration（含审计与安装）、scenarios。

```bash
python scripts/run_tests.py        # 164 passed
python scripts/verify_all.py       # 目录 + 目录自检 + 工具链 + 闭环 + 测试 + v1.1 子系统
```

### 已知未完成

- **OmniAiLab provider 未连接**：本机未检测到官方 SDK、本地配置或平台下发的 API 契约，状态为
  `NOT_CONFIGURED`。接入方式与所需字段见 `docs/OMNIAILAB_INTEGRATION.md`。
- **Blender / FreeCAD / IfcOpenShell 未安装**：输出可执行的生成脚本与投影数据，阶段标 `degraded`。
- **写实效果图不可用**：表现任务包已生成；图像生成待平台接入，验收中记为**跳过**而非通过。
- **PDF 导出**需本机有 LibreOffice；否则降级为打印就绪 HTML，**不伪造 PDF**。

## v1.0.0 — 八阶段专业工作流

- 八阶段业务模型（S1–S8）+ 人工确认门禁 G1–G8。
- 28 项岗位能力，与阶段多对多映射；原 18 份说明书全部保留并注入阶段字段。
- Canonical Spatial Model 作为唯一几何权威；几何变更触发下游失效重算。
- 设计变更影响分析（诊断 → 影响面 → 回流 → 门禁重开）。
- 真实执行层：内置 DXF R12 写出器 + ezdxf R2010、OBJ/MTL 网格、Blender/FreeCAD 脚本、IFC 投影。
- 四条硬性专业逻辑（R1–R4）落为带测试的约束。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
