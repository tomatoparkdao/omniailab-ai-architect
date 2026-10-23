---
name: 多专业总设计师架构
description: OmniAiLab AI Architect 的多专业组织方式——一个总设计师、一个项目主模型、一条阶段工作流、一套可追溯成果，以及每项能力到底真到哪一步
version: 1.17.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 多专业总设计师架构

## 一、一句话

**不是五个 AI 各做五份文档，是一个总设计师带着五个专业做同一套设计。**

落到代码上就是四条唯一：

| 唯一 | 落在哪 | 破了会怎样 |
|---|---|---|
| 一个总设计师 | `SKILL.md` 是唯一调度入口 | 出现第二个主 Skill，判断标准分裂 |
| 一个项目主模型 | `schemas/project.schema.json` + `revisions.py` | 各专业各存一份几何，互相矛盾 |
| 一条阶段工作流 | `stages.py` 的 S1–S8 / G1–G8 | 出现竞争性工作流，门禁失效 |
| 一套可追溯成果 | `register_artifact` + 修订号 | 成果与版本脱钩，无法回溯 |

新增的专业能力全部挂在这四条上，不另建架构。

## 二、总设计师负责什么

项目理解、委托范围识别、专业分工、设计计划、概念统筹、跨专业冲突检查、成本协调、成果合并、业主沟通、门禁审批、版本与交付。

专业只负责"我这块怎么做"，不负责"这次到底要做哪些专业"——后者是总设计师的判断，落在 `disciplines.py`。

## 三、五个专业域

| 域 | 管什么 | 系统能出到什么 | 必须人工 |
|---|---|---|---|
| 建筑 Architecture | 总图、体量、平面、立面、剖面、竖向交通 | 方案深度；房型组合与体量关系 | 报批符合性、结构可行性 |
| 结构 Structure | 体系选择、柱网、跨度、荷载路径、加固 | 条件与待核实清单；**不出计算** | 鉴定、计算、配筋、签署 |
| 机电 MEP | 暖通、给排水、电气、弱电、消防、机房管井 | 条件与接口；**不出负荷** | 负荷计算、消防合规、系统选型 |
| 室内 Interior | 功能布局、顶墙地、固定家具、材料、灯光 | 方案深度；做法与材料表 | 现场条件、收口可行性 |
| 景观 Landscape | 室外与室内景观、竖向、铺装、种植、水景、照明 | 分区与竖向原则；**无独立平面生成器** | 防水排水、植物适应性、维护 |
| 规划 Planning | 用地指标、退线、限高、日照、报批路径 | 口径核对与缺口清单；**不出法定结论** | 当地规范符合性 |

结构与机电的边界是刻意的：**能说清要算什么，不等于算过。** 系统输出的是"待核实项 + 谁签"，不是"已验算"。

## 四、两轴识别委托

**第一轴：项目是什么** —— 住宅、公寓、别墅、商业、办公、酒店、民宿、园区、公共建筑、庭院、花园、室内中庭。

**第二轴：客户要设计什么** —— 总体规划、建筑、结构、机电、室内、室外景观、室内景观、全专业。

两轴独立。所以"别墅"这个类型既可能是全专业委托，也可能只是室内装修；"酒店"同样不能因为类型是酒店就自动认定只做室内。

## 五、真实能力矩阵

`implemented` 真实实现 · `partial` 部分实现 · `documented_only` 只有说明 · `adapter_required` 需专业软件 · `blocked` 当前无法执行

| 专业 | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 |
|---|---|---|---|---|---|---|---|---|
| 室内 | implemented | implemented | implemented | implemented | partial | partial | partial | implemented |
| 建筑 | partial | partial | partial | partial | partial | partial | blocked | partial |
| 结构 | partial | partial | blocked | blocked | not_applicable | blocked | blocked | partial |
| 机电 | partial | partial | blocked | partial | not_applicable | partial | blocked | partial |
| 景观 | partial | partial | blocked | blocked | not_applicable | blocked | blocked | blocked |
| 规划 | partial | partial | blocked | not_applicable | not_applicable | blocked | blocked | blocked |

读法说明（这张表比看上去保守，原因是刻意的）：

- **室内**是唯一走完整条链的专业：S3 有平面策略、S4 有顶墙地、S7 有 DXF、S8 有材料表。
- **建筑**的"partial"指能出体量与平面关系，但没有独立的建筑平面生成器与立面适配器；S7 无建筑图纸适配器。
- **结构/机电/景观**的 S3 `blocked` 不是"做不了"，是**不许假装**：没有对应执行器时明确阻断并给补资料清单，而不是拿房间算法顶上。
- 结构 S2 的 `partial` 指能给出"这套概念要求结构回答什么"，不是给出结构方案。
- 规划全链 `blocked` 是因为法定指标须当地规范复核，系统只做口径与缺口。

## 六、跨专业接口

十二组物理约束（详见 `docs/DISCIPLINE_SCOPE_AND_ROUTING.md`），只在双方都在范围内时进矩阵。每条含"什么情况下算没解决"——这是可判定的失败条件，不是"建议加强沟通"。

## 七、变更回流

跨专业变更走 `changes.py` 的两层判断：

1. **领域判定**回答"主要落在哪个阶段"（原有 11 条 + 新增屋面/景观/用地/结构 4 条）；
2. **跨专业规则**回答"还动了谁"（6 条：屋顶花园、水体、建筑移位、加层、立面开洞、结构加固）。

命中的规则展开成逐专业影响项，每项带"需要什么才能定"和影响阶段。跨专业改动的落点取**最早**受影响阶段——晚定等于返工。

反例同样重要：**换墙面颜色不该让结构与景观全部返工**，它有测试守着。

## 八、还没做到的

| 缺口 | 影响 | 为什么不现在做 |
|---|---|---|
| 无建筑平面生成器 | 建筑项目 S3 只能出体量关系 | 需要柱网与开间体系，不能拿房间组合代替 |
| 无立面/剖面适配器 | 建筑 S7 无正式图纸 | 需要专业制图适配器，属平台/工具侧 |
| 无结构计算 | 结构只能给条件 | 需经验证的计算工具与注册工程师 |
| 无景观平面生成器 | 纯景观委托 S3 阻断 | 竖向与排水是几何问题，不能简化成铺装图案 |
| 无机电负荷计算 | 机电只能给接口 | 同上 |
| 无地勘接入 | 结构条件无法证实 → S7 阻断 | 需外部资料，不是软件问题 |

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
