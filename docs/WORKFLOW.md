---
name: omniailab-workflow
description: 八阶段专业工作流 —— 阶段推进项目进度，能力提供专业方法，门禁控制确认节奏
version: 1.13.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 八阶段专业工作流

> 本文是阶段模型的说明文档。**代码中的唯一权威是 `stages.py`**；两者不一致时以代码为准，并回来修文档。

---

## 为什么要重做流程

最初的设计把 18 个专业 Skill 顺序执行一遍。那是把两件不同的事混在一起了：

- **岗位能力** —— 设计事务所有哪些专业角色、各自能做什么。最初的 18 份说明书现拆解为 31 项能力（新增跨阶段的设计汇报、概念效果图与景观设计能力），一项能力经常横跨多个阶段。
- **业务阶段** —— 一个真实项目是怎么推进的。8 个阶段，每个阶段有自己的交付物、进入条件、退出条件和业主确认门禁。

一个项目不是"把 18 个能力跑一遍"，而是**按阶段推进，每个阶段调用该阶段需要的专业能力**。灯光设计就是一个例子：它在 S2 给概念灯光方向、在 S4 出照明方案、在 S7 出灯具定位图。把它钉死在某一个阶段，项目就没法做了。

---

## 阶段总表

| 代号 | 阶段 | 目的 | 交付物 | 门禁 |
|---|---|---|---|---|
| **S1** | 01 项目启动与设计任务书 | 把需求、场地、原始图纸与预算固化成可验收的任务书 | 设计任务书 · 原始条件报告 | G1 任务书确认 |
| **S2** | 02 概念方案设计 | 定方向：设计立场、空间原型、风格语言 | 概念方案 · 意向板 | G2 概念方案确认 |
| **S3** | 03 平面方案设计 | 把概念落到尺度：分区、功能、动线、家具、面积配比 | 两至三套平面方案 · 对比分析 | G3 平面方案确认 |
| **S3·后** | （门禁后置动作） | 让业主建立空间感受 | 概念效果图 · 画布任务包 · 汇报 PPTX | 附属于 G3 |
| **S4** | 04 初步设计与方案深化 | 把平面发展成可施工的做法 | 初步设计图纸（方案深度）· 材料及灯光方案 | G4 初步设计确认 |
| **S5** | 05 3D 建模与效果图表现 | 在已确认的几何上做真实表现 | 3D 模型 · 空间效果图 · 漫游 | G5 表现成果确认 |
| **S6** | 06 设计定稿与技术协调 | 审定、协调、预算适配，形成深化依据 | 确认版设计方案 · 深化依据 | G6 设计锁定 |
| **S7** | 07 CAD / BIM 施工图深化 | 出可施工的正式图纸与模型 | 施工图文件 · BIM 模型 · 审查记录 | G7 施工图审查 |
| **S8** | 08 物料清单与交付 | 变成可采购、可施工、可验收的交付包 | 材料表 · 工程量清单 · 全套交付文件 | G8 交付验收 |

**建筑设计项目**需在此基础上按规模与所在地要求增加报批、扩初设计、专业会审等阶段。当前版本实现的是室内设计项目主流程；`architectural-design` 能力已在 S1/S4 就位。

---

## 能力 → 阶段映射（多对多）

| 能力 | 阶段 | 能力 | 阶段 |
|---|---|---|---|
| design-brief | S1, S6 | 3d-modeling | S5 |
| site-analysis | S1 | scene-rendering | S5 |
| existing-drawing-analysis | S1 | ai-visualization | S5 |
| architectural-design | S1, S4 | walkthrough | S5 |
| concept-design | S2, S3 | design-review | S6, S7 |
| moodboard-aesthetic-iteration | S2, S5 | coordination-check | S6, S7 |
| create-draw | S2, S4, S7 | cost-check | S1–S6 |
| space-planning | S3 | bim-modeling | S5, S7 |
| layout-optimization | S3, S6 | construction-detailing | S7 |
| ergonomics | S3, S4 | quantity-takeoff | S1–S8 |
| interior-design | S4, S6 | material-schedule | S8 |
| material-design | S4, S5, S8 | documentation | S8 |
| lighting-design | S2, S4, S7 | delivery | S8 |
| building-services | S4, S6, S7 | cad-drafting | S4, S7 |

v1.0 的 18 份说明书已按能力域重组为 `skills/<能力名>.md`（共 30 份，文件名即能力名，可直接按名加载），每份的 front-matter 含 `capability` 与 `stages`；`design-presentation`（跨 S2–S8）与 `concept-visualization`（G3 门禁后置动作）为新增能力。`python -m omniarchitect registry` 可打印完整映射。

---

## 五条硬性专业逻辑（`GUARDRAILS`）

这几条专业逻辑最容易在实现时被做错，所以写成有测试守着的硬规则：

### R1 · 业主确认功能需求前不得开始精细建模
概念与平面可以交互迭代，但在任务书确认（G1）之前不能进入精细 3D。**代码强制**：`can_start(S5)` 在 S1 未确认时直接返回阻断。

### R2 · CAD 不是最后才画
真正的区别是**图纸深度**，不是有没有图纸：

| 深度 | 出现阶段 | 用途 |
|---|---|---|
| `schematic` | S3、S4 | 与业主沟通做法与造价 |
| `construction` | S7 | 施工 |

S4 起就可以画 CAD，也可以用简单 3D 辅佐设计。把 CAD 理解成"最后才用"是错的。

### R3 · 成本估算从前期就动态进行
`cost-check` 与 `quantity-takeoff` 覆盖 S1–S8。S1 就有估算（没有平面时按套内轮廓 + 任务书面积估，并声明基数），随深化逐步替换为实测值，S8 才形成正式清单。**在 S8 才第一次算预算，等于把造价风险全部推到最后。**

### R4 · 平面未确认不得出正式图纸；锁定后不得局部手改
G3 是整条链上最贵的一个门禁：跳过它，后面所有图纸都要重做。设计锁定（G6）之后，任何修改必须走变更影响分析，不允许在某张图上手工改动。

### R5 · 概念效果图只能在业主确认的平面上生成
平面一变，已出的概念效果图**整批失效**并重出。**代码强制**：概念效果图挂在 `POST_GATE_ACTIONS["G3"]` 上，是门禁的**后置动作**而不是独立阶段；平面未确认时它没有执行入口。每张图登记到产生它的模型修订与提示词指纹。

---

## 门禁后置动作（post-gate actions）

有些工作只有在门禁通过之后才**成立**。给业主看的概念效果图就是明确的例子：在平面被批准之前出图，画的是随时会变的空间——这正是 G3 这条规则要防的事。

```python
POST_GATE_ACTIONS = {"G3": ["concept-visualization"]}
```

后置动作与阶段的区别：

| | 阶段 | 门禁后置动作 |
|---|---|---|
| 有自己的门禁 | 有（G1–G8） | **没有**，附属于所在门禁 |
| 能单独确认 | 能 | 不能 |
| 触发时机 | `run_stage` | 门禁 `confirm` 那一刻 |
| 被打回的后果 | 置为返工 | 记录被清除，旧产物不再当作现行成果 |

**执行方式**：`confirm --stage S3` 通过的那一刻自动执行；
也可单独重出：`concept-render --project <dir> --scheme A --views 5`。

**不改动统一空间模型**：G3 确认的是方案，方案在 S4 才安装为深化依据。因此后置动作在
**fork** 上渲染——确认一个门禁不应该悄悄改写项目，修订号也不会因此跳动。

产出：画布任务包（`canvas-jobs.json`）、参考图（已确认平面的栅格化）、逐张状态
（`RUN-STATUS.md`）与可编辑汇报 PPTX。详见 `docs/CONCEPT_RENDER.md`。

---

## 阶段确认与变更回流

设计不能只从 S1 单向流到 S8。典型场景：S5 生成客厅效果图后，业主不满意电视背景墙。总设计师应该：

1. **判断**是材质问题、立面设计问题，还是平面尺寸问题；
2. **只回到受影响的设计任务**修改；
3. **保留**已确认的其他空间与方案；
4. **更新**关联的 3D、图纸与材料；
5. **重新提交**受影响成果确认。

这就是 `changes.py` 的设计变更影响分析。

### 诊断域

| 域 | 落点阶段 | 改变几何 | 典型处理 |
|---|---|---|---|
| scope_program 任务书与功能范围 | S1 | 是 | 修订任务书后重跑概念与平面 |
| plan_dimension 平面尺寸与墙体 | S3 | **是** | 改坐标 → 全局失效重算 |
| layout_zoning 分区与动线 | S3 | **是** | 重排分区与门位 |
| elevation 立面与造型 | S4 | 否 | 只改该立面分缝、比例与材料 |
| ceiling 顶面与吊顶 | S4 | 否 | 重做吊顶剖面与灯槽 |
| material 材料与色彩 | S4 | 否 | 换材料与色号 |
| lighting 灯光与照明 | S4 | 否 | 重排灯位与点位 |
| mep 机电与设备 | S4 | 否 | 调点位并重跑协调校核 |
| furniture_layout 家具与尺度 | S3 | 否 | 调家具选型与位置 |
| style_concept 概念与风格 | S2 | 否 | 重做意向板（标尺变了） |
| visual_only 表现与镜头 | S5 | 否 | 重出图，不动设计数据 |

### 两条不对称的规则

- **饰面级变更不碰几何**：换材料、换灯位、改立面做法，**不得**使平面或模型作废。
- **几何级变更一定连带全部下游**：动了坐标或尺寸，平面、立面、模型、图纸、工程量、效果图全部失效重算。

例外：**立面 / 天花变更仍然要使图纸与模型类成果失效**，因为立面图与吊顶图里画的就是这些东西——尽管平面坐标没变。

### 影响面收敛

只有真正引用了受影响对象的成果才会被卷入。定位时会把受影响空间的**边界构件**（墙、门窗、家具）一并作为种子，再按依赖图传递。已经确认、与本次变更无交集的其他空间成果保持锁定。

---

## 门禁与状态机

状态：`pending → in_progress → awaiting_confirmation → confirmed`，另有 `rework` 与 `blocked`。持久化在 `project.meta["stage_state"]`，因此一次运行可以在门禁处停下，几天后继续。

```bat
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
:: 跑到第一个未确认门禁即停
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniarchitect reject  --project projects/demo-120 --stage S3 --reason "面积要重算"
python -m omniarchitect status  --project projects/demo-120
```

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
