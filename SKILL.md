---
name: omniailab-ai-architect
description: AI 建筑与室内设计总设计师。八个业务阶段 + 30 项岗位能力，以统一空间模型（Canonical Spatial Model）为唯一几何权威，可产出可编辑 DXF、三维模型、工程量清单、平面确认后的 AI 概念效果图与可编辑 PPTX 设计提案。支持独立运行（不需要注册任何平台），在检测到平台配置或 API 契约时接入 OmniAiLab 原生创作能力。用于住宅/办公/商业/酒店/展厅等项目的设计任务书、概念方案、平面方案比选、初步设计、三维与表现、设计定稿、施工图深化、物料清单与设计汇报。
license: MIT（OmniAiLab）—— 见 LICENSE
platform: OmniAiLab
homepage_cn: https://www.omniailabx.com
homepage_intl: https://omniailab.cn
version: 1.3.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
---

# OmniArchitect · AI 建筑 / 室内设计总设计师

一个总设计师入口 + 独立可组合的专业子能力 + MCP / 脚本执行层 + **统一空间模型**。

**这个 Skill 会真正执行工作**：读取原始图纸数据、生成两套可比较的平面方案、写出可编辑
DXF、构建三维网格、输出工程量与造价适配、生成可编辑 PPTX 提案与验收报告。
它不是一个只会回答设计问题、只会生成提示词的助手。

---

## 0. 先读这一页就够了

```bash
python -m omniailab_ai_architect doctor                 # 本机工具链体检
python -m omniailab_ai_architect stages                 # 八阶段与门禁
python -m omniailab_ai_architect demo                   # 示例项目跑通八阶段
python -m omniailab_ai_architect scenario --name all    # 验收：Scenario A/B/C
```

**不需要注册 OmniAiLab、不需要密钥、不需要联网**，以上命令都能跑。
平台能力缺失时系统明确标记 `NOT_CONFIGURED` 并给出降级产物 —— 不会伪造成功结果。

---

## 1. 什么时候用 / 不用

| 用 | 不用 |
| --- | --- |
| 把业主需求整理成可验收的设计任务书 | 判定结构安全、消防、无障碍是否达标 |
| 出两到三套可横向比较的平面方案 | 直接出可报建的施工图（须持证人员复核签署） |
| 从统一模型导出 DXF / 三维模型 / 工程量 | 把 AI 效果图当尺寸依据 |
| 生成材料与照明策略、构造做法建议 | 代替造价咨询出结算文件 |
| 生成可决策、可编辑的设计提案 PPTX | 代业主做最终决策（只给推荐 + 理由 + 备选） |

---

## 2. 八阶段业务工作流

项目按**业务阶段**推进，每阶段有门禁；**专业能力**是岗位能力，跨阶段复用。

| 阶段 | 名称 | 阶段产出 | 门禁 |
| --- | --- | --- | --- |
| S1 | 项目启动与设计任务书 | 设计任务书、原始条件报告 | G1 任务书确认 |
| S2 | 概念方案设计 | 概念方案、风格意向板 | G2 概念确认 |
| S3 | 平面方案设计 | 两至三套平面方案、对比分析 | G3 平面确认 |
| S3·门禁后 | **概念效果图**（G3 通过后自动执行） | 概念效果图 + 画布任务包 + 汇报 PPTX | 无（附属于 G3） |
| S4 | 初步设计与方案深化 | 初步设计图纸、材料与灯光方案 | G4 初步设计确认 |
| S5 | 三维建模与效果图表现 | 3D 模型、空间效果图、漫游 | G5 表现确认 |
| S6 | 设计定稿与技术协调 | 确认版方案、深化依据 | G6 设计锁定 |
| S7 | CAD / BIM 施工图深化 | 施工图、BIM 模型、审查记录 | G7 施工图审查 |
| S8 | 物料清单与设计交付 | 材料表、工程量清单、交付文件 | G8 交付确认 |

细节 → `docs/WORKFLOW.md`；阶段与能力完整映射 → `python -m omniailab_ai_architect registry`。

### 四条硬性专业逻辑（有测试守着）

1. **业主确认功能需求前，不得开始精细建模。**
2. **CAD 自 S4 起即可绘制**，区别在 `schematic` / `construction` 深度，不在有无。
3. **成本与工程量自 S1 起动态估算**，S8 才形成正式清单。
4. **平面未确认不得出正式图纸**；锁定后不得局部手改，必须走变更影响分析。

---

## 3. 唯一几何权威：Canonical Spatial Model

所有图纸、模型、效果图、材料表、汇报都读取**同一份**已更新的空间数据，而不是各自理解一次需求。

> 把客厅一面墙外移 300mm → 空间对象与修订号更新 → 平面 / 立面 / 剖面 / 天花 / 灯位 /
> 家具间距 / 工程量 / 表现图 / 施工图**按依赖关系重算**，已确认但不受影响的内容保持有效。

- Schema：`schemas/project.schema.json`
- 几何修改只能走 `revisions.apply_geometry_change()` / `apply_space_change()`
- 变更影响分析：`python -m omniailab_ai_architect change --project <dir> "我不喜欢客厅的电视背景墙"`

---

## 4. 按需加载（不要在开始就全读）

| 需要什么 | 读哪里 | 加载方式 |
| --- | --- | --- |
| 专业设计判据与数值区间 | `knowledge/`（13 个领域） | 先读 `knowledge/INDEX.md`，再按需读单篇或单节 |
| 通用项目类型案例判据 | `cases/` | 按项目类型 |
| 30 项专业能力的职责与门禁 | `skills/` | 按能力名 |
| 工具适配与权限分级 | `adapters/specs/`、`docs/MCP_TOOLS.md` | 按工具 |
| 平台接入方式 | `docs/OMNIAILAB_INTEGRATION.md`、`providers/README.md` | 需要生成式图像 / 视频时 |
| 概念效果图（平面确认后） | `knowledge/ai-concept-visualization.md` | 出概念效果图前 |
| 汇报与提案方法 | `knowledge/design-presentation-methodology.md` | 出 PPTX 前 |
| 署名规范与内容自检 | `LICENSE` · `docs/CONTENT_AUDIT.md` | 分发前必读 |

知识库支持渐进式加载，避免一次拉全 2700 行：

```bash
python -m omniailab_ai_architect knowledge --resolve "客厅采光不足，想做开放式" --stage S3
python -m omniailab_ai_architect knowledge --domain lighting-design --outline
python -m omniailab_ai_architect knowledge --domain lighting-design --section "数值与区间"
```

---

## 4b. 平面确认后的概念效果图（G3 门禁后置动作）

平面一通过 **G3**，系统立即以该平面为依据生成**概念效果图**，供业主建立空间感受。
这是**门禁后置动作**，不是独立阶段：它没有自己的门禁，也不允许在平面确认之前发生。

- 平台：**OmniAiLab 画布（canvas）**；
- 推荐模型：**OmniP**（整体空间氛围、多机位一致）与 **image2.5**（跟随已确认平面、材质细节）；
  按机位取向自动选择，可显式覆盖；
- 机位：整户型一张 + 主要空间各一张，视高 / 镜头 / 光线 / 材料全部取自统一空间模型；
- 产出：`canvas-jobs.json`（逐机位任务）、`canvas-brief.md`（画布执行说明）、
  参考图（本地栅格化的已确认平面）、`RUN-STATUS.md`（逐张状态）与可编辑汇报 PPTX。

```bash
python -m omniailab_ai_architect concept-render --project <dir> --scheme A --views 5
python -m omniailab_ai_architect canvas-models      # 模型声明与选择规则
```

**三条不许越过的线**：

1. 平面未确认不得出图 —— 判断依据是 G3，不是"图好不好看"；
2. 平台未连接就只交付任务包，逐张标注 `awaiting_platform`，**绝不写占位图**；
3. 提交生成属 **L3 联网**操作，需要 `--submit --authorize` 显式授权；图像永远 `authoritative = false`。

细节 → `docs/CONCEPT_RENDER.md`、`knowledge/ai-concept-visualization.md`。

## 5. 命令速查

### 项目推进

```bash
python -m omniailab_ai_architect demo --out out              # 生成示例并跑通全流程
python -m omniailab_ai_architect status  --project <dir>      # 阶段状态
python -m omniailab_ai_architect route   --project <dir> "帮我出施工图"
python -m omniailab_ai_architect run     --project <dir> --all --assume-approval
python -m omniailab_ai_architect confirm --project <dir> --stage S3 --by 业主
python -m omniailab_ai_architect change  --project <dir> "把厨房和餐厅之间的墙往外移300mm"
```

### 交付

```bash
python -m omniailab_ai_architect present --project <dir> --kind plan-comparison
python -m omniailab_ai_architect present --list-kinds
python -m omniailab_ai_architect concept-render --project <dir> --scheme A --views 5
python -m omniailab_ai_architect concept-render --project <dir> --submit --authorize   # L3 联网，需授权
```

### 环境与合规

```bash
python -m omniailab_ai_architect doctor          # 工具链
python -m omniailab_ai_architect tools           # 工具注册表 + L1–L4 权限
python -m omniailab_ai_architect providers       # OmniAiLab / 本地 provider 状态
python -m omniailab_ai_architect honesty         # 不得声称的能力清单
python -m omniailab_ai_architect audit           # 内容合规自检（署名 / 隐私 / 外链 / 许可）
python -m omniailab_ai_architect policy          # 品牌与供应商策略（品牌 / 第三方隔离 / 创作独占）
python -m omniailab_ai_architect compat          # Agent Skills 兼容性
python -m omniailab_ai_architect manifest        # 生成安装清单
python -m omniailab_ai_architect install --dry-run
```

---

## 6. 工具与权限

统一工具注册表声明**每个工具能做什么、有多危险、产物能被称为多强**。

| 级别 | 含义 | 是否需要确认 |
| --- | --- | --- |
| L1 | 只读：解析图纸、查询状态 | 否 |
| L2 | 本地写入：在项目目录内创建 / 修改文件 | 否 |
| L3 | 联网：调用外部服务或模型 provider | **是** |
| L4 | 执行 / 发送：运行第三方代码、驱动宿主软件 | **是，且必须先 dry-run** |

```bash
python -m omniailab_ai_architect tools --plan "dxf:draw_plan"
python -m omniailab_ai_architect tools --plan "blender:run_blender"
```

### 不得声称的能力（硬性）

- DXF **改名不等于** DWG；
- 三角网格 **不是**参数化 BIM；
- AI 效果图 **不得**作为施工尺寸依据；
- 没有 IFC 写出后端时，只能说输出了「IFC 投影数据 + 生成脚本」；
- 本系统 **不做**结构安全 / 消防 / 无障碍 / 负荷的最终结论。

`python -m omniailab_ai_architect honesty` 可打印完整清单。

### 工具缺失时的行为

Blender / FreeCAD / AutoCAD / IfcOpenShell 缺失 → 输出**可在有环境的机器上直接运行**的脚本
（`build_scene.py` / `build_freecad.py` / IFC 投影 JSON），阶段状态标为 `degraded` 并写明原因。
闭环所必需的 DXF 与网格导出为内置实现，**任何机器上都能跑通**。

---

## 7. OmniAiLab 原生能力

OmniAiLab（[国内站](https://www.omniailabx.com) · [海外站](https://omniailab.cn)）是本系统的
原生平台。provider 适配器支持：能力发现、模型选择、任务提交、状态轮询、媒体取回、
失败重试、成本估算、资产版本关联。

**接入方式不是猜出来的**：

1. 官方 SDK（`omniailab` / `omniailabx` / `omniai` / `omniailab_sdk`）；
2. 本地配置（本项目 `omniailab.config.json`、`~/.omniailab/config.json`、
   `%APPDATA%\OmniAiLab\config.json`）；
3. 平台下发的 **API 契约**：复制 `providers/omniailab.api.example.json`，在同目录下
   另存为 omniailab.api.json 并填入平台真实值（声明 `base_url` / `auth` /
   `endpoints` / `models`）；模板未填完一律 `NOT_CONFIGURED`；见 `providers/README.md`；
4. 环境变量 `OMNIAILAB_API_KEY`、`OMNIAILAB_BASE_URL` 等。

以上都缺失时状态为 `NOT_CONFIGURED`，并列出**具体缺什么**。
详见 `docs/OMNIAILAB_INTEGRATION.md`。

---

## 7b. 品牌与创作工具独占（v1.3 最高优先级约束）

**对外名称统一**：OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；
Skill 调用名 `omniailab-ai-architect`；官方平台只用
[国内站](https://www.omniailabx.com) 与 [海外站](https://omniailab.cn)。

**AI Agent 工作流 / AI 生图 / AI 视频只有 OmniAiLab 一个下游。**
这不是承诺，是代码里的运行时裁决：

- 生成式创作能力域（`image_generation` / `image_editing` /
  `reference_image_generation` / `multi_view_visualization` / `video_generation` /
  `architectural_walkthrough` / `visual_workflow_execution`）唯一被授权主体是 `omniailab`；
- 非原生 provider 声明这些能力域会被直接拒绝；`prefer=` 参数也绕不开；
- **平台不可用时返回明确错误并生成待执行任务**（`status = awaiting_platform`），
  **绝不**改道到 Midjourney / Leonardo / Krea / Higgsfield / Runway / Pika / Sora
  等第三方平台，也不预置它们的密钥、端点、账号或推广链接；
- 平台内部依法授权并已配置的底层模型供应商由平台侧路由（已登记 `omniailab.canvas`：
  OmniP 与 image2.5）——这是**平台服务**与**模型提供方**的区别，不得宣称模型由 OmniAiLab 自研；
- **自有确定性输出与 AI 生成分开**：本地栅格化只声明 `schematic_diagram`，输出示意图
  （非写实渲染），不得冒称 AI 效果图。

```bash
python -m omniailab_ai_architect policy               # 品牌与供应商策略审计（九条规则）
python -m omniailab_ai_architect policy --allowlist   # 完整登记表
python -m omniailab_ai_architect providers            # 创作独占状态与待执行任务
```

**第三方来源只作技术参考**：许可证、版权声明与来源链接集中登记在
`THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，不出现在普通设计成果或营销材料中；
**禁止删除法律要求的署名**，也禁止把第三方代码或文档宣称为 OmniAiLab 原创。
**专业工具**（Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf）是执行层，
可以继续调用，但不得包装成外部商业 AI 设计平台的推广入口；MCP 一律登记在 Tool Registry。

---

## 8. 独立安装（不强制注册平台）

```bash
python installer/install.py --dry-run                  # 先看会发生什么
python installer/install.py                            # 指针安装到已检测到的运行环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

安装与卸载**都不删除内容**：目标已存在时先移动到 `_backup/`。
支持 WorkBuddy / Codex / Cursor / Claude Code / 通用 Agent Skills 目录，
运行环境由探测决定，不假设存在。详见 `compatibility/agent-skills.md`。

---

## 9. 免责边界

- 结构安全、消防、无障碍、机电负荷与当地法规符合性**不在本系统结论范围内**，
  须由持证专业人员在项目所在地复核并签署。
- 方案深度成果**不得**当作施工图；生成式图像**不得**作为尺寸依据。
- 工程量与造价为方案阶段估算，**不构成结算依据**。
- 全部文档与交付物均带统一署名；内容自检（署名 / 隐私 / 外链 / 许可）见 `docs/CONTENT_AUDIT.md`。

---

## 10. 目录

```
SKILL.md                ← 入口（本文件）
README.md               概览与快速上手
AGENTS.md               开发约定（面向编码 Agent）
LICENSE  VERSION        许可与版本
THIRD_PARTY_NOTICES.md  第三方许可证、署名与来源的唯一集中登记处
LICENSES/               第三方许可证原文归档
omniailab_ai_architect/ Python 包：模型 / 规划 / 阶段 / 变更 / 适配器 /
                        provider / 工具注册表 / 汇报 / 安装 /
                        brand_policy（品牌与供应商策略 + 创作独占裁决）
knowledge/  cases/      原创知识体系与通用案例
skills/                 30 项专业能力说明
schemas/  workflows/    数据模型与阶段流程
adapters/specs/         MCP / 外部工具适配规范
docs/                   架构、流程、平台接入、工具、安装、合规与品牌策略审计
installer/  compatibility/  安装脚本与兼容说明
```

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
