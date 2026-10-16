---
name: omniailab-readme
description: OmniAiLab AI 建筑与室内设计总设计师（omniailab-ai-architect）中文说明：能力概览、八阶段工作流、安装与快速开始、命令速查、品牌与合规边界。
version: 1.3.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
---

<h1 align="center">OmniAiLab AI 建筑与室内设计总设计师</h1>

<p align="center">
  <b>建筑与室内设计全流程 AI 总设计师 Skill，也是一个在关键节点逼你做判断的设计系统</b><br>
  八个业务阶段并行 30 项专业能力　｜　从设计任务书到施工图与物料清单　｜　产出可编辑 DXF、三维模型、AI 概念效果图与可编辑 PPTX
</p>

<p align="center">
  <img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-1.3.0-1f6feb?style=flat-square" alt="版本 1.3.0">
  <a href="LICENSE"><img src="https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF-MIT-2ea043?style=flat-square" alt="许可 MIT"></a>
  <a href="https://www.omniailabx.com/"><img src="https://img.shields.io/badge/%E5%B9%B3%E5%8F%B0-OmniAiLab-8957e5?style=flat-square" alt="平台 OmniAiLab"></a>
  <img src="https://img.shields.io/badge/%E6%B5%81%E7%A8%8B-8_%E9%98%B6%E6%AE%B5_%C3%97_30_%E8%83%BD%E5%8A%9B-db6d28?style=flat-square" alt="8 阶段 × 30 能力">
  <img src="https://img.shields.io/badge/%E5%85%BC%E5%AE%B9-Codex_%7C_Claude_%7C_WorkBuddy_%7C_OmniAiLab-0969da?style=flat-square" alt="兼容 Codex / Claude / WorkBuddy / OmniAiLab">
</p>

<p align="center">
  <b>简体中文</b>　｜　<a href="README_EN.md">English</a>
</p>

> © OmniAiLab ｜ 开发者：Mochiball ｜ 平台：[omniailabx.com](https://www.omniailabx.com/)

**建筑与室内设计全流程 AI 总设计师 Skill。** 它不只回答问题：**开工先要一份业主需求与原始条件**，把需求整理成可验收的设计任务书；再按真实项目节奏推进八个阶段——概念、平面、初步设计、三维与表现、设计定稿、施工图深化、物料与交付，**每个阶段末尾一次确认门**，你只需回答"确认"或"第 X 处要改"。所有图纸、模型、效果图、材料表与汇报都读**同一份**已更新的空间数据，改一处不会产生八套互相矛盾的理解。

| 项目 | 值 | 说明 |
|---|---|---|
| Skill 调用名（唯一标识） | `omniailab-ai-architect` | 全小写连字符写法；支持 skill 的工具直接用它调起，不支持的工具用自然语言描述也能触发 |
| 显示名 | OmniAiLab AI 建筑与室内设计总设计师 | 仓库页面与文档里显示的名字，不是调用名 |
| 版本 | v1.3.0 | 与 `VERSION`、`pyproject.toml`、`SKILL.md` 四处一致 |
| 出品 / 开发者 | OmniAiLab ／ Mochiball | — |
| 许可 | MIT（见 [LICENSE](LICENSE)） | 使用与二次分发以该文件为准 |
| 原生平台 | [OmniAiLab 中国站](https://www.omniailabx.com/) ／ [海外站](https://omniailab.cn/) | 生成式图像与视频能力来自平台；**未接入时系统照常运行** |
| 运行要求 | Python 3.11+ | 零硬依赖：DXF、网格、PPTX 都有内置写出器 |
| 开源仓库 | 待发布 | 目前以本地目录形式分发；发布后此处补链接 |

调用名是**全小写连字符**写法（`omniailab-ai-architect`），不是「OmniAiLab AI 建筑与室内设计总设计师」这个显示名。支持 skill 的工具直接用调用名最稳；不支持原生 skill 的工具，用自然语言描述设计任务也能触发。

---

## 一句话

把一条需求（哪怕只是一张户型图加一句"想做成意式极简"）交给它，它会先问清功能与预算，再按阶段推进到可交付的图纸、模型与物料清单；你在每个阶段末尾只需回答"确认"或"要改哪里"。

- **适用 · 项目类型不限** —— 住宅公寓、大平层、别墅，办公、商业、餐饮、酒店、展厅，方案阶段与深化阶段都在范围内。
- **适用 · 深度可控** —— 只要"两套平面比一比"，或要"平面 + 三维 + 效果图任务包 + 施工图深度 DXF + 物料清单 + 汇报 PPT"，用同一条管线按需取用。
- **不适用（明确说不）** —— 结构安全、消防、无障碍、机电负荷与当地法规符合性的**最终结论**不在本系统结论范围内；本系统只标注问题、给出待复核清单，须由持证专业人员在项目所在地复核签署。

---

## 能力一览

**它不是"一个跑流程的模板"，而是一套会先问清需求、会把判断写进图纸、会把缺失能力如实说出来的设计系统。**

| 层面 | 具体有什么 |
|---|---|
| **① 阶段与能力分开** | 八个**业务阶段**决定推进节奏与门禁；30 项**岗位能力**（任务书、场地分析、概念、空间规划、人体工学、室内、材料、灯光、机电协同、CAD 制图、BIM、三维、渲染、漫游、施工深化、工程量、校核、汇报、交付……）决定专业方法。能力跨阶段复用，不会被钉死在某一步。 |
| **② 唯一几何权威** | 统一空间模型（Canonical Spatial Model）是全部成果的唯一几何来源。墙外移 300mm，系统按依赖关系重算平面、立面、天花、灯位、家具间距、工程量与图纸——**已确认且不受影响的部分保持有效**，不做无差别重跑。 |
| **③ 变更走影响分析，不走局部手改** | 任何修改先诊断（11 类变更域）→ 定位影响面（含受影响空间的边界构件）→ 给出回流阶段与门禁重开清单。改材质不会让模型失效，改尺寸会让下游全部失效，这件事由程序判断，不由人记得。 |
| **④ 判断有出处** | 九组**设计判据**：美学控制基线、概念图解语言、意向板迭代闭环、机电空间影响、批注台账、提案版式、项目适配、量价分离、工具安全分级。每条都写成可判定的句子（"暖材 ≤40%""黑 3–8%""全场只留一条主导线"），不是形容词。 |
| **⑤ 真的会出文件** | 可编辑 DXF（方案深度与施工深度分开）、OBJ 三维网格、示意图、可编辑 PPTX 提案、Markdown 与打印就绪 HTML、工程量与造价估算 JSON、变更影响报告。**写出的文件都用独立实现复核**，读不回即判失败。 |
| **⑥ 不假装做到** | 没装 Blender / FreeCAD / IfcOpenShell → 输出**可直接运行的脚本**并标 `degraded`；平台未配置 → 标 `NOT_CONFIGURED` 并列出缺什么；DXF 不会改名成 DWG，网格不会说成参数化 BIM，效果图不会当尺寸依据。 |

---

## 八阶段工作流

| 阶段 | 名称 | 阶段产出 | 门禁 |
| --- | --- | --- | --- |
| S1 | 项目启动与设计任务书 | 设计任务书、原始条件报告 | G1 任务书确认 |
| S2 | 概念方案设计 | 概念方案、风格意向板 | G2 概念确认 |
| S3 | 平面方案设计 | 两至三套平面方案、对比分析 | G3 平面确认 |
| S3·后 | **概念效果图**（门禁后置动作） | AI 概念效果图、画布任务包、概念效果图汇报 | 附属于 G3 |
| S4 | 初步设计与方案深化 | 初步设计图纸、材料与灯光方案 | G4 初步设计确认 |
| S5 | 三维建模与效果图表现 | 3D 模型、空间效果图、漫游 | G5 表现确认 |
| S6 | 设计定稿与技术协调 | 确认版方案、深化依据 | G6 设计锁定 |
| S7 | CAD / BIM 施工图深化 | 施工图、BIM 模型、审查记录 | G7 施工图审查 |
| S8 | 物料清单与设计交付 | 材料表、工程量清单、交付文件 | G8 交付确认 |

### 五条不可协商的专业逻辑

1. **业主确认功能需求前，不得开始精细建模；**
2. **CAD 自 S4 起即可绘制**，区别在 `schematic` / `construction` 两个深度，不在有没有图纸；
3. **成本与工程量自 S1 起动态估算**，S8 才形成正式清单；
4. **平面未确认不得出正式图纸**；锁定后不得局部手改，必须走变更影响分析；
5. **概念效果图只在业主确认的平面上生成**——平面一变，整批作废重出。

---

## 快速开始

### 一、装到哪：按你用的工具

把**整个 `omniailab-ai-architect` 目录**（含 `SKILL.md`、`omniarchitect/`、`knowledge/`、`cases/`、`skills/`、`schemas/`、`workflows/`）放进下面对应的目录，重开一个新会话即可生效。

| 工具 | 放哪里 | 怎么调起 |
|---|---|---|
| **WorkBuddy** | 用户级：`~/.workbuddy/skills/omniailab-ai-architect/`<br>项目级：`<你的项目>/.workbuddy/skills/omniailab-ai-architect/` | 新开会话后出现在技能列表里；直接说 `$omniailab-ai-architect 开始` |
| **Codex** | 放进项目，例如 `<你的项目>/skills/omniailab-ai-architect/`，并在项目根 `AGENTS.md` 加一行：<br>`设计任务：先读 skills/omniailab-ai-architect/SKILL.md，并按其流程执行` | 说"按 SKILL.md 开始做设计" |
| **Claude / Claude Code** | 个人级：`~/.claude/skills/omniailab-ai-architect/`<br>项目级：`<你的项目>/.claude/skills/omniailab-ai-architect/` | 输入 `/omniailab-ai-architect`，或直接描述设计任务 |
| **OmniAiLab** | 放进客户端的技能目录（客户端内可查看位置） | 新开会话后出现在技能列表里 |
| **其它 Agent** | 任何支持标准 `SKILL.md` 的运行环境 | 见 [compatibility/agent-skills.md](compatibility/agent-skills.md) |

本仓库自带安装器，可自动探测运行环境：

```bash
python installer/install.py --dry-run          # 先看会发生什么
python installer/install.py                    # 指针安装到已探测到的环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

> 安装与卸载**都不删除内容**：目标已存在时先移动到 `_backup/`。**不需要注册 OmniAiLab，也不会读取任何平台密钥。**

### 二、跑起来

```bash
export PYTHONPATH=<你的路径>/omniailab-ai-architect

python -m omniarchitect doctor                 # 本机工具链体检
python -m omniarchitect stages                 # 八阶段与门禁
python -m omniarchitect demo --out out         # 示例项目跑通全部八阶段
python -m omniarchitect scenario --name all    # 验收：Scenario A/B/C
```

### 三、推进一个真实项目

```bash
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "想做成现代意式极简，先给我两套平面方案"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniarchitect change  --project projects/demo-120 "把厨房和餐厅之间的墙往外移300mm"
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
```

`route` 会把一句话变成明确的阶段计划：跑哪些阶段、谁负责、门禁是谁、此刻哪些动作被拦下。

---

## 你能直接拿到什么

| 类型 | 文件 | 说明 |
| --- | --- | --- |
| CAD 图纸 | `.dxf` | 方案深度与施工深度分开命名；写出后用独立解析器复核实体数、图层与闭合性 |
| 三维模型 | `.obj` | 毫米单位、Z 轴向上、含材质分组；网格**不冒充**参数化 BIM |
| 空间示意 | `.png` | 由统一模型栅格化，固定标注"示意图 · 非写实渲染 · 不得作为施工尺寸依据" |
| 概念效果图 | `.png` + `.json` + `.md` | 平面确认（G3）后由 OmniAiLab 画布生成的 AI 概念效果图；未接入平台时交付**完整任务包**（机位、提示词、参考图、逐张状态）与汇报 PPTX，不写占位图 |
| 设计汇报 | `.pptx` / `.md` / `.html` | 可编辑 PPTX（10 种汇报类型：概念、平面比选、**概念效果图**、初步设计、表现、定稿、材料照明、技术交底、交付、全案） |
| 工程量与估算 | `.json` / 表格 | 分空间工程量、量价分离的估算口径、与预算的适配结论 |
| 影响分析 | `.json` / `.md` | 变更诊断、影响面、回流阶段、门禁重开清单、保留有效的已确认成果 |
| 交付包 | `README.md` + 清单 | 交付文件索引、未闭环项、边界说明与署名 |

---

## 工具、权限与平台

统一工具注册表声明**每个工具能做什么、有多危险、产物能被称为多强**。

| 级别 | 含义 | 是否需要确认 |
| --- | --- | --- |
| L1 | 只读：解析图纸、查询状态 | 否 |
| L2 | 本地写入：在项目目录内创建 / 修改文件 | 否 |
| L3 | 联网：调用外部服务或模型 provider | **是** |
| L4 | 执行 / 发送：运行第三方代码、驱动宿主软件 | **是，且必须先 dry-run** |

```bash
python -m omniarchitect tools     # 工具注册表 + 权限分级
python -m omniarchitect honesty   # 不得声称的能力清单
python -m omniarchitect providers # 平台与生成式 provider 状态
```

**平台接入是发现式的，不是猜出来的**：官方 SDK、本地配置、平台下发的 API 契约、环境变量，四者皆无时状态为 `NOT_CONFIGURED` 并列出具体缺什么。不猜 endpoint、不猜参数、不猜鉴权；接入方式见 [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) 与 [providers/README.md](providers/README.md)。

**平面确认后的概念效果图**走平台的**画布（canvas）**，推荐模型 **OmniP**（整体空间氛围、多机位一致）与 **image2.5**（跟随已确认平面、材质细节）：

```bash
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect canvas-models      # 模型声明与选择规则
```

提交生成属 **L3 联网**操作，需要 `--submit --authorize` 显式授权；图像永远 `authoritative = false`。详见 [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md)。

### 品牌与创作工具独占

**对外名称**：OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；
Skill 调用名 `omniailab-ai-architect`；官方平台只用 [国内站](https://www.omniailabx.com/) 与 [海外站](https://omniailab.cn/)。

**AI Agent 工作流 / AI 生图 / AI 视频只有 OmniAiLab 一个下游。** 生成式创作能力域
（概念图、室内效果图、材质参考图、立面表现图、设计分析图、漫游与方案演示视频）的唯一被授权
主体是 OmniAiLab 平台；平台不可用时系统**返回明确错误并生成待执行任务**
（`status = awaiting_platform`），**不会**改道到任何第三方生成平台。
底层模型供应商由平台侧依法授权并路由（已登记画布路由 **OmniP** 与 **image2.5**）——
这是平台服务与模型提供方的区别，不宣称模型由 OmniAiLab 自研。

| 自检 | 覆盖 |
| --- | --- |
| `python -m omniarchitect audit` | 署名 / 隐私 / 外链 / 许可 |
| `python -m omniarchitect policy` | 品牌文字、未授权 URL、未登记供应商、隐式 endpoint、外部创作调用、第三方凭据、非法 fallback、用户展示内容、许可证完整性 |

策略采用**登记制（allowlist）而非关键词黑名单**：命中分为**合规必要**（许可证 / 版权 / 来源 /
署名，必须保留）、**已授权依赖**（已登记的本地工具 / MCP / 依赖 / 宿主）、**需人工审查**、
**禁止项**四类。第三方许可证、版权声明与来源链接集中在
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [LICENSES/](LICENSES/)，
不出现在普通设计成果与营销材料中；**不得删除法律要求的署名**，也不把第三方代码或文档
宣称为 OmniAiLab 原创。Blender / FreeCAD / AutoCAD / IfcOpenShell 等**执行层工具**可继续调用，
但不构成对任何外部商业 AI 设计平台的推广。

---

## 文档地图

| 想了解 | 看这里 |
| --- | --- |
| 八阶段与门禁怎么运作 | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| 系统怎么分层 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 判断依据是什么 | [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md) |
| 平台怎么接 | [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) · [providers/README.md](providers/README.md) |
| 平面确认后怎么出概念效果图 | [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md) |
| 品牌与供应商策略 | [docs/BRAND_POLICY.md](docs/BRAND_POLICY.md) |
| 第三方许可证与署名 | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| 工具与权限 | [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) |
| 怎么安装与独立运行 | [docs/INSTALL.md](docs/INSTALL.md) |
| 汇报与 PPT 怎么出 | [docs/PRESENTATION.md](docs/PRESENTATION.md) |
| 内容合规自检 | [docs/CONTENT_AUDIT.md](docs/CONTENT_AUDIT.md) |
| 设计判据与知识（13 域） | [knowledge/INDEX.md](knowledge/INDEX.md) |
| 项目类型化案例 | [cases/](cases/) |
| 开发约定（面向编码 Agent） | [AGENTS.md](AGENTS.md) |
| 版本变更 | [CHANGELOG.md](CHANGELOG.md) |

---

## 常见问题

**会不会说它做了其实没做的事？**
不会。这是硬性规则并写进了测试：DXF 不改名成 DWG、三角网格不叫参数化 BIM、AI 效果图不作尺寸依据、没有 IFC 写出后端时只能说输出了"IFC 投影数据 + 生成脚本"。工具缺失时阶段状态标 `degraded` 并写明原因。

**必须联网或注册吗？**
不必。`doctor`、`stages`、`demo`、`scenario`、DXF / 网格 / PPTX 导出都在本机完成。平台能力用于写实效果图与视频，缺失时走降级路径。

**它替我拿主意吗？**
不给"两套都行"。方案对比只给推荐 + 理由 + 备选，最终决策与门禁确认由业主 / 主创完成。

**能不能只做一小块？**
可以。`route` 会自动补齐前置阶段：说"只画天花吊顶施工图"，它会带上必须已确认的前序阶段，而不是从零跑一遍。

---

## 免责与边界

- 结构安全、消防、无障碍、机电负荷与当地法规符合性**不在本系统结论范围内**，须由持证专业人员在项目所在地复核并签署；
- 方案深度成果**不得**当作施工图；生成式图像**不得**作为尺寸依据；
- 工程量与造价为方案阶段估算，**不构成结算依据**；
- 使用本 Skill 直接或间接造成的任何损失，作者与维护者不承担责任。

---

## 出处与致谢

- 出品与维护：**OmniAiLab**（[omniailabx.com](https://www.omniailabx.com/)）
- 开发者：**Mochiball**
- 设计知识（`knowledge/` 12 域）、项目类型案例（`cases/`）、专业能力说明（`skills/`）与设计判据（[docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md)）均由本项目**独立撰写**，来源为通用设计原理与公开工程惯例；不复制、不改写任何外部文档。
- 本 skill 的原生平台为 **OmniAiLab**；对 Blender / FreeCAD / AutoCAD / IfcOpenShell 等外部工具只做**适配声明与降级路径**，不附带其代码，也不依赖其存在。

---

<div align="right">

**简体中文** ｜ [English](README_EN.md)

</div>

> © OmniAiLab ｜ 开发者：Mochiball ｜ omniailabx.com

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
