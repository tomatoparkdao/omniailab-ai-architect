---
name: omniailab-s1-intake
description: S1 智能项目启动 —— 三种启动情形、按项目类型的动态访谈、五态置信度、五类可行性、设计机会识别、八份成果包与 G1 基准
version: 1.20.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# S1 智能项目启动（Intelligent Intake & Discovery）

S1 原来只做一件事：把已有信息整理成任务书。问题是，大多数项目在 S1 开始时**信息根本不齐**
——业主只说了「150㎡ 大平层，想做现代意式极简」。旧实现要么让他先填完整套资料，要么
拿模板把空位填满，两种都不是设计。

这一轮把 S1 变成一个有判断力的启动过程：**先搞清楚知道什么、缺什么、缺的那部分能撑住到哪一步**，
再谈任务书。

## 一、三种启动情形

| 情形 | 判定依据 | S1 该做什么 |
|---|---|---|
| **只有一句话** | 无资料登记、信息槽覆盖 < 40% | 开启动态访谈，先问最关键的 3 个问题 |
| **已有图纸/照片/任务书** | 有 source 登记 或 program ≥ 3 项 | 先读资料再问，**只问资料里没有或相互矛盾的** |
| **资料基本完整** | 信息槽覆盖 ≥ 75% 且 program ≥ 3 项 | 直接形成初步诊断与任务书，只确认高风险项 |

判定在 `intake.detect_start_mode()`，写在 `project.meta.intake.start_mode`。
一句「资料完整」不等于「可以出图」——这两件事分开判断（见第四节）。

## 二、动态访谈

访谈不是一套固定问卷。六类项目各有自己的问题集与判断标准：

| 类型 | 专业重点 | 特征问题（举例） |
|---|---|---|
| 住宅 / 公寓 / 别墅 | 家庭结构、日常行为、收纳与隐私 | 常住几口人、作息冲突、厨房使用强度 |
| 办公 | 组织结构、会议频率、专注与协作比例 | 人数与增长、部门关系、访客动线 |
| 酒店 / 民宿 | 目标客群、客房结构、服务与后勤 | 卖給谁、房型配比、布草与垃圾通道 |
| 餐饮 / 商业 | 目标消费者、翻台、后场与设备 | 客单价与停留时长、峰值客流、菜单设备 |
| 展厅 / 文化 | 叙事顺序、人流组织、展品保护 | 观众按什么顺序看、展品敏感度 |
| 新建建筑 | 用地与规划条件、报批、专业协作 | 红线退界、容积率限高、地勘、报批状态 |

**机制（这些是代码行为，不是文档承诺）**：

1. 同一个信息槽只问一次。换个问法问同一个槽，会被跳过（`_covered_slots`）。
2. 依赖未满足的问题不问（`depends_on`）。
3. 每轮最多 3 个，按「后果严重度 → 影响的最深阶段」排序。
4. 「不知道」是合法答案：记为 `unknown`，转成假设与不确定项，**不阻塞整个流程**。
5. 已回答的内容不会被重复询问——首句里的面积、城市、人数、风格会自动提取
   （`seed_from_text`），并标注「从首句需求解析，请在 G1 前确认」。
6. 业主可以随时纠正答案。若任务书已确认，修改会返回 `requires_change_analysis = true`，
   提醒走变更影响分析，**不静默覆盖已确认版本**。
7. 访谈状态存在 `project.meta.intake.interview`，换会话、隔天继续都不丢。

## 三、使用行为矩阵

「需要一个大厅」不是需求，是没有约束的愿望。矩阵把愿望拆成可校核的行：

| 字段 | 问的是什么 | 为什么重要 |
|---|---|---|
| 活动 | 在这里做什么（不是房间叫什么） | 同样 30㎡，聚餐与写作业是两种房间 |
| 使用者 | 谁用、几个人 | 决定座位数、净宽与视线 |
| 频率与时段 | 多久一次、什么时间 | 决定位置、隔音与共享程度 |
| 空间与设备 | 需要什么尺寸与设备 | 是面积的真正来源 |
| 隐私 / 噪声 | 需要多安静、多私密 | 决定墙、门与分区 |
| 邻接 / 分隔 | 必须挨着谁、必须离开谁 | 决定平面骨架 |
| 优先级 | 必须 / 应该 / 可以 | 冲突时的取舍依据 |
| 来源与状态 | 谁说的、可信到什么程度 | 推断行不能当面积依据 |

每行带 `state`：`verified` / `documented` / `inferred` / `unknown` / `conflicting`。
由房间用途推出来的活动一律 `inferred`，不得直接当布置依据。

## 四、尽职调查：五态置信度

每条重要信息只允许落在五个状态之一，含义固定：

| 状态 | 含义 | 能否作为出图依据 |
|---|---|---|
| `verified` | 现场实测，或责任方书面确认 | 可以 |
| `documented` | 有来源文件支持，未现场核验 | 可以出方案图，须注明待核 |
| `inferred` | 由规则或 AI 推断 | 不可以 |
| `unknown` | 没有依据 | 不可以 |
| `conflicting` | 多个来源互相矛盾 | 不可以，且要先澄清 |

**阻断范围按影响面定，不是一刀切**（`diligence.BLOCKING_SCOPES`）：

| 主题 | 阻断到哪一步 | 为什么 |
|---|---|---|
| 结构（承重、梁柱） | S4 起，且不得批准任何拆改 | 方案可以谈，结构承诺不行 |
| 尺寸（缺少精确尺寸） | S3 起 | 平面要在真实尺寸上成立 |
| 法规 / 报批 | S7 | 报审图纸不能用未确认的条件 |
| 机电条件 | S4 | 净高、点位、容量都要它 |
| 预算口径 | 不阻断 | 造价结论改为给区间并注明假设 |
| 审美方向 | 不阻断 | S2 收敛即可 |

**`verified` 不是自己说了算**。登记一份 `measure` 资料时，系统要同时看到三样东西才认：
核验人（`verified_by`）、时间或版本、以及能找到的来源文件。缺一样就降级为 `documented`，
并把缺什么写进 note。只写一个文件名不会改变任何阶段准入——这条有测试守着。

**来源冲突比空白更危险**：空白可以补，冲突会让人照着错的那个干活。所以 `conflicting`
在自身阻断范围之外**额外阻断 S2**——先澄清，再谈概念。

**核实之后要主动关闭**：`--action verify --uid U-STRUCTURAL` 把该项标为 `verified`，
`blocks_stages` 清空、`open` 变 false，相关限制立刻解除。不关闭就会留下永久性阻断。

## 五、五类可行性

| 类别 | 检查什么 | 典型结论 |
|---|---|---|
| 功能与面积 | 需求面积 vs 可用面积（需求 ÷ 可用） | > 1.15 阻断；0.95–1.15 重要 |
| 行为与空间 | 聚餐人数、居家办公、照护、卫浴数量 | 需求与空间条件打架 |
| 预算与目标 | 预算 ÷ 面积 vs 参考区间 | 低于下沿 20% 阻断 |
| 周期与审批 | 交付深度 vs 周期；报批状态 | 含施工图但周期 < 8 周 |
| 建筑与专业 | 结构是否证实、机电、层高 | 层高 < 2600mm 影响吊顶策略 |

每条冲突必须给出：问题、事实依据、受影响需求、严重度、建议方向、可替代方案、
是否需要人工审核、是否阻断下一阶段。**依据里必须有具体数字**，不能写「感觉偏紧」。

造价与工期结论一律标为规划参考区间，不是报价与承诺。

## 六、设计机会

这是总设计师与表单系统的分界：听完、查完之后，指出这个项目**最值得花力气解决的 3–5 个问题**。

每项九个字段：`opportunity_id` / `problem` / `evidence` / `design_goal` /
`expected_value` / `constraints` / `priority` / `confidence` / `next_stage_recommendation`。

规则：

- 只输出有证据的项。**证据不足时少于 3 项是正确结果，不凑数**。
- 输出的是「要解决的设计问题与研究方向」，**不是概念方案或平面**。
- 每项的 `next_stage_recommendation` 指向 S2 或 S3 的具体动作。
- 结构、消防、无障碍、法规的结论不在其中，须持证人员复核。

## 七、统一执行入口

S1 只有**一个**任务书生成器。`run --stage S1` 与 `intake --action analyze` 都是它的适配层：

| 入口 | 实际做的事 | 差别 |
|---|---|---|
| `python -m omniarchitect run --stage S1` | `StageRunner.stage_S1` → `intake.generate_bundle` | 输出到 `out/<run>/01-*/` |
| `python -m omniarchitect intake --action analyze` | 直接调 `intake.generate_bundle` | 输出到 `--out` 指定目录 |

两者对同一项目产出的 8 份成果**逐字节一致**（除「生成时间」一行），
测试 `test_the_two_entry_points_produce_the_same_bundle` 守着这件事。

无几何资料也能跑：`envelope_polygon` 取不到轮廓时，条件报告会明确写「尚无几何数据，
本报告只汇总已知资料，不含任何尺寸结论」，而不是抛异常。

## 八、S1 成果包

| 文件 | 回答什么问题 |
|---|---|
| `design-brief.md` | 给谁做什么、做到什么深度 |
| `user-needs.json` | 空间到底怎么被使用 |
| `site-report.md` | 哪些物理条件可以依赖 |
| `source-register.json` | 每份资料从哪来、什么版本、可信度 |
| `uncertainty-register.json` | 什么没证实，各自阻断哪些阶段 |
| `feasibility-report.md` | 哪里对不上，依据是什么 |
| `design-opportunities.md` | 这个项目值不值得做、先解决什么 |
| `s1-approval-summary.md` | 业主要签的是什么 |

全部绑定 `project_id` + `revision`，并登记为 artifact；上游一变即可标 stale。
可编辑 PPTX 任务书汇报按需由 `design-presentation` 生成，不强制每次都出。

## 九、G1 门禁：四类后果，不是一个开关

G1 只回答一个问题：**能不能进 S2**。它不决定结构能不能拆——那是 S4/S7 的事。
把两件事混在一起，会得到一个永远开不了的门禁，和一堆看不见的限制。

所以判定拆成四类：

| 类别 | 含义 | 例子 |
|---|---|---|
| **阻断当前门禁** `blocks_gate` | 业主必须做取舍才能进 S2 | 需求 400 m² 装进 131 m²；完全没有需求 |
| **限制后续阶段** `limited_stages` | S2 照常，但 S3/S4/S7 带具体限制 | 结构未核验 → 不得拆改；尺寸未确认 → 不得出正式平面 |
| **要求专业复核** `needs_human` | 必须由持证人员签署才算数 | 结构、消防、报批条件 |
| **允许附条件推进** `conditions` | 可以进，但要把前提写在记录里 | 预算低于目标档次、需求全为推断 |

三种决策仍映射既有状态机：`approved → confirmed`、`revision_requested → rework`、
`blocked → blocked`。

**放行方式分两级**：

- `--acknowledge F-AREA-01`：业主逐项确认「我已理解并选择继续」，每项单独留痕；
- `--force`：等价的快捷方式，基准里记 `forced: true`。它**只对需求矛盾生效**，
  结构、消防、报批这类安全限制不归 G1 管，force 也解不开——它们由阶段守卫生效。

**签署来源分开记**：

| 来源 | 是否写基准 | 用途 |
|---|---|---|
| `owner`（`confirm` / 默认） | 写 `baseline` | 业主真实确认，后续阶段据此比对 |
| `demo`（`--assume-approval`） | 只写 `demo_approval` | 演示与测试，**不得被当作业主签署引用** |

`check_baseline()` 会明确回答「是否只有演示确认」，避免演示结果被拿来当签字。

## 十、基准与变更联动

基准摘要拆成两个，因为两种变化的性质不同：

| 摘要 | 覆盖 | 变化意味着 |
|---|---|---|
| `brief_digest` | program + constraints + answers + 来源 | 业主改了需求 → **必须走变更影响分析** |
| `baseline_digest` | 上面这些 + 每个不确定项的状态 | 只是限制变了（如已核验）→ 任务书没变 |

G1 确认后修改需求，系统**不只是返回一个标志位**：

1. `invalidate_from(project, "S1")` 把 S1 及下游已确认阶段置为返工；
2. 写一条 `change_log`（含被作废的阶段）；
3. `check_baseline()` 返回 `change_kind = "brief"` 与 `requires_change_analysis = true`。

原确认版保留在修订记录中，不会被覆盖；要继续就必须重新提交 G1。


## 十一、阶段守卫：限制按工作内容判，不按阶段一刀切

`intake.guard.check_stage(project, stage)` 回答「这个阶段能做哪些工作」：

| 阶段 | 结构未核实 | 尺寸未确认 | 报批未确认 |
|---|---|---|---|
| S2 | 可讨论非拆改方案 | 可讨论方向，不得给实际尺寸 | — |
| S3 | 平面不得以拆改为前提 | 可做比较与示意，不出正式平面 | — |
| S4 | 不得出拆改与加固图纸 | 不得出依赖精确尺寸的图纸 | — |
| S7 | **阻断**（施工图不得基于未证实结构） | **阻断** | **阻断** |
| S8 | — | 工程量不得作为结算依据 | — |

要点：

1. **限制不等于阻断**：S3/S4 仍可推进，只是具体工作被点名禁止，并且限制会写进阶段产出的
   `notes`，后续不会被误当成无限制成果；
2. **只对已登记的项生效**：模型自带的 `uncertain` 标记仍走原有校核逻辑，旧项目与 demo
   的行为完全不变；
3. **`documented` 不是通关证**：结构、法规类即使有图纸，仍保持限制——图画过不等于现场就是那样。

## 十二、S1 进入条件已放宽

旧条件写的是「需求、场地、原始图纸已收集」，这不符合真实业务——真实项目常常从一句话开始。

现在的条件：

1. 业主提出项目想法、初步需求或已上传资料**即可启动**；
2. **资料完整度决定精度**：缺尺寸不出依赖尺寸的权威成果，缺结构不批准结构改造。

精度分三级（`diligence.precision_level`）：

| 精度 | 判定 | 能做什么 |
|---|---|---|
| `diagnostic` | 无几何、无实测 | 需求诊断与概念方向，不出技术成果 |
| `schematic` | 有几何或图纸 | 方案图与示意，尺寸须核验，不出施工图 |
| `authoritative_capable` | 有现场实测 | 可出方案深度图纸（施工图仍须专业签署） |

`diagnostic` 的项目在 `can_start` 里会被直接拒绝进入 S4/S5/S7，理由写明「资料仅支持诊断级」。

## 十三、命令行

```bash
python -m omniarchitect intake --project P --action start --text "150㎡ 大平层，一家三口"
python -m omniarchitect intake --project P --action ask
python -m omniarchitect intake --project P --action answer --id base.budget --value "硬装 80 万"
python -m omniarchitect intake --project P --action answer --id res.future --state deferred
python -m omniarchitect intake --project P --action register --uncertainty --topic structural
python -m omniarchitect intake --project P --action status
python -m omniarchitect intake --project P --action analyze
python -m omniarchitect intake --project P --action verify --uid U-STRUCTURAL --note "现场探测已确认"
python -m omniarchitect intake --project P --action gate --decision approved --by 业主
python -m omniarchitect intake --project P --action gate --decision approved --acknowledge F-AREA-01
python -m omniarchitect intake --project P --action gate --decision approved --source demo

# 主流程入口（与上面同一个引擎）
python -m omniarchitect run     --project P --stage S1
python -m omniarchitect confirm --project P --stage S1 --by 业主 [--acknowledge ID] [--force]
```

`--json` 对所有命令可用，便于被 Agent 或脚本直接消费。

## 十四、边界

1. 不虚构面积、预算、结构条件与法规条款；没有依据的一律 `unknown`。
2. 不把推断当事实，不把「业主可能想要」写成需求。
3. 设计机会不是方案：不给平面、不给材料、不给造型。
4. 结构安全、消防、无障碍、机电负荷与法规符合性不在本能力结论范围内，须持证专业人员复核。
5. 平台未接入时不改道任何第三方；S1 主要用本地推理与文档解析，不需要联网。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
