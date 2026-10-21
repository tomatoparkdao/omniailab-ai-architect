---
name: omniailab-SECTOR_DESIGN
description: SECTOR_DESIGN —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: 1.15.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 行业设计层：从"知道是什么项目"到"按这个行业排"

分类解决的是"这是什么项目"。这一层解决另一半：**这类项目该怎么排、为什么这么排、
排到什么程度为止**。它不新增阶段、不新增门禁、不新建几何系统。

## 一、四个入口，各管一件事

| 入口 | 作用 | 不做什么 |
|---|---|---|
| `sector.brief.build(ctx)` | 从 S1 原话抽出可算的量，列出矛盾与缺口 | 不猜数、不替客户定 |
| `sector.moves.moves(brief)` | 由这些数推出 2–3 条组织方式，写明代价 | 不给固定套话 |
| `sector.program.build(brief)` | 折成房间清单，交给已有平面算法 | 不另写排布算法 |
| `sector.parti.resolve(handoff)` | 读 G2 选定概念声明的平面组织方式 | 概念没声明就不猜 |

S3 的调用顺序是 `brief → program → parti → plans → planner.PlanGenerator`。
住宅与办公**不进入**这条分支（`program.BUILDERS` 里没有 housing / office），
原有 `band_day_night` / `spine_centre` / `office_cluster` 一行未改。

## 二、先分清"主体"与"配套"

同一个词在两种语境里意思是相反的：

- 「新建学校，含**食堂**和**体育馆**」——食堂与体育馆是校园的配套房间；
- 「委托做一家**餐饮工装**」——那是一整套后厨、排烟、隔油与营业流程。

`taxonomy.FACILITY_TERMS` 记录了每个主体类型"可以有"的配套：
学校（A3）→ 学生食堂 / 校园体育馆 / 报告厅 / 宿舍；酒店（A6）→ 餐饮 / 会议 / SPA；
医院（A4）→ 院内食堂 / 药房；厂房（A12）→ 厂区办公 / 员工食堂……

判定规则（`classify`）：

1. 配套词只算"很弱的证据"（×0.25），不能把别的类型抬成主体
   ——「酒店的会议中心」不会把 A2 办公带进来；
2. 命中里**没有实质证据**的编码降级为 `ancillary`，不进 `codes`、不进委托范围；
3. 客户明确说"另建 / 独立 / 单独委托"（`SEPARATE`）时，配套升级回独立用途
   ——「新建学校，另建独立体育馆」→ A3 + A8；
4. 新建医院里的 B8 医疗工装算**同一栋楼的另一专业**（`sibling`），
   不是第二个用途：委托范围仍只看客户说没说明"做室内"。

## 三、推敲：数字说话，缺数就说缺

每条方向（`moves.Move`）必须写清三件事：

```python
Move(name="教学组团 · 共享中庭",
     parti="24 班拆成 3 个组团，每组约 8 班（520 m² 教室）…",   # 用了哪些数
     why="每班 45 人、共 1080 人，课间十分钟要完成的换场是…",     # 解决哪条矛盾
     costs=("中庭占 270 m² 但不排课…",),                      # 代价
     uses=("classes", "students"), answers=("容积率", "建筑密度"))
```

`brief` 里能算的都带算式（`facts`）：普通教室 = 班数 × 65 m²；
食堂 = 学生 × 60% ÷ 供餐批次 × 1.1 m²/座；容积率 = 建筑量 ÷ 用地……
只有客户原话里出现过的数才进 `inputs`，其余写进 `assumptions`（默认值）；
缺关键输入写进 `missing`，由 S2 明确告诉客户"缺什么会怎样"。

医院的"洁污分流"不是一句口号：`brief` 会算出床位、门诊量、手术间数与 ICU 床位数，
再据此把"医技居中"或"双廊模块"的取舍写出来；缺床位就明说"算不出住院部面积、
竖向分区与电梯数"。

## 四、S2 → S3：概念怎么落到平面上

选定概念写进交接文件的 `design.plan_layout`（旧项目按概念名回溯，并标明是推断）。
`sector.parti` 把它翻成一份可执行的剖面：**带序 + 每带进深 + 西端块 + 合成空间**
（走廊、中庭、诊疗街），以及这套概念"必须看得见的空间结构"（`DEVICES`）。

| 组织方式 | 落点 | 图上要找到的结构 |
|---|---|---|
| `cluster_atrium` | 学校 | 教室按组团分开、每团一处中庭/组团厅、专用教室贴中庭 |
| `linear_corridor` | 学校 | 通长连廊、两侧都挂房间、专用与办公集中成带 |
| `medical_street` | 医院 | 贯通全宽的诊疗街、候诊贴街、诊室分列两侧 |
| `tech_core` | 医院 | 医技居中、门诊绕医技一圈、候诊在端部 |
| `dual_corridor` | 医院 | 洁污两条廊、病房夹在中间、污物有后场出口 |
| `process_line` | 厂房 | 原料→生产→成品单向、装卸分两端 |
| `guest_wing` | 酒店 | 双面客房走廊、服务后场在尽端 |
| `water_loop` / `terrace` / `grove_edge` | 景观 | 环水游线 / 台地分层 / 林缘边界 |

四条硬规矩：

1. **A 方案就是选定概念**，不是"最像的那个"。B 方案取同一行业的**另一种组织逻辑**
   （`ALT`），不是把 A 镜像翻一下——面积表、流线、剖面构成都不同，业主才有得选。
2. **结构要在图上真的找得到**：`parti.inspect` 用几何关系逐条判定（房间是否共线贴边、
   走廊是否贯通、端部是否有后场），不是读名字对不对。判不出来就说"未找到"。
3. **不写死 `supported`**：`strategy_supported` 由实际排出的
   `scheme.metrics["parti"]` 与声明比对得出；声明了却没排出来就是 False。
4. **概念没声明就明说**：回落到通用带序，记录 `declared=False`、
   `implements_concept=False`，报告里写"本轮平面不是该概念的实现"——不许拿
   通用带状平面冒充概念落地。

## 五、几何依据分四档

`layout.geometry_basis` 只看可核对的来源字段，不做推测：

| 依据 | 判定 | 能否支撑正式确认 |
|---|---|---|
| `surveyed` | 来源含 survey / measured / 实测 | 可以（仍须现场核对） |
| `drawing` | 已有图纸导入，未标实测 | 可以，但签发后须核对 |
| `client` | 业主估算 | 不可以，只作探索 |
| `proposed` | 系统按任务书反算 | 不可以，须实测后重出 |

**已有真实几何时不能用自动矩形替代**：`has_envelope` 为真就不执行 `install_envelope`，
方案直接排在既有外墙里。反过来，只有建议轮廓时允许继续做方案探索与专业分析——
阻断的是"宣称已核实"，不是"继续想"。

总平面与景观按客户原话里的方位组织（`_orientation` 读"北侧临城市道路"这类描述）；
客户没说方位时按南侧入口假设，并在图上与报告里写明这是假设。

## 六、G3：三档结论，不是"过/不过"

`sector.check.assess` 挂在 `assess_plan_gate` 上，`formal_ready = 无 blockers 且无 critical`：

| 档 | 含义 | 典型 id |
|---|---|---|
| blockers | 连探索稿都不成立 | `G3-NO-DESIGN-DATA` |
| critical | 可作探索/讨论方案，不能声称已核实通过 | `G3-PROPOSED-ENVELOPE`、`G3-ESTIMATED-ENVELOPE`、`G3-MISSING-INPUT`、`G3-FUNCTION-INCOMPLETE`、`G3-CONCEPT-STRUCTURE`、`G3-CONCEPT-NOT-REALIZED` |
| conditions | 记录在案，不阻断本轮确认深度 | `G3-SPECIALIST-REVIEW`、`G3-SURVEYED-ENVELOPE`、`G3-DRAWING-ENVELOPE`、`G3-ASSUMPTION-USED`、`G3-STRUCTURE-CHECKED`、`G3-HUMAN-REVIEW` |

几条口径：

- **房间数达标 ≠ 功能对**：`REQUIRED_USES` 逐类核对（医院要有诊室/医技/候诊/卫生间，
  学校要有教室/专用/办公/卫生间），缺一项即 critical；
- **"缺什么"要分档**：会改变房间数量与面积的（床位数、日门诊量、工艺顺序、班数）
  算关键前提；"专项顾问复核""实测放线"算条件项，如实记录但不阻断讨论；
- **专项项目写清已验证/依赖顾问**：医疗工艺、厂房消防类别、厨房排烟隔油一律
  写明"须专业顾问确认"，不当作已验证；
- **旧项目兼容**：已签发的 G3 记录不重算、不追溯指责（旧记录没有 `categories`
  字段就不做功能完整性判定）。

## 七、参数来源四分档

经验值不能自动升级成"现行规范强制值"。`brief.param()` 登记每个关键参数，
报告里逐行给出依据：

| 档 | 含义 | 例子 |
|---|---|---|
| client | 客户明确数据 | 24 班、每班 45 人、1200 人次日门诊 |
| reference | 有来源的专业参考值 | 普通教室 65 m²/班（含讲台储藏，非强制指标） |
| assumption | 系统暂定探索假设 | 柱网 9×9 m、后场 15%、ICU 按 3% 床位 |
| consultant | 须专业顾问确认 | 手术间数与洁净等级、工艺设备基础 |

## 八、图纸：读得出组织，也读得出代价

`plandraw.plan_svg` 画的是方案平面：门画成门扇 + 开启弧，左侧标出剖面带名
（带名按该带的实际构成合成，不拿最大那间房代表整条带），中庭/诊疗街用与走廊
不同的底色，窗画在宿主墙上。`site.landscape_svg` 画园林总平面：水面成一块、
种植沿界、园路成环、节点与视线分层——**面积占比图与总平分布图分开表达**，
占比表说明任务书分区，总平面说明构图与游线，两者不能互相替代。

## 九、边界（不掩饰）

| 项 | 现在能做到 | 还不能 |
|---|---|---|
| 学校 | 校园总平面关系、教学楼标准层、教室/专用教室/办公/服务配比 | 办学标准符合性、疏散宽度校核 |
| 医院 | 门诊医技层、科室面积与洁污分区、手术与 ICU 的规模推算 | 医疗工艺、感控、机电专项 |
| 厂房 | 单层主厂房、工艺方向、仓储与厂前区、柱网反算 | 设备基础、结构、消防类别核定 |
| 酒店工装 | 客房标准层、后场比例、电梯与服务间位置 | 品牌标准、消防与隔声实测 |
| 景观 | 分区占比、游线关系、水面与绿化构成 | 竖向标高、放线、植物规格与苗木 |

**没有专属程序就明说**：`sector` 只覆盖 education / healthcare / industrial /
hospitality / landscape；其余类型不进入这条分支，也不套住宅模板冒充。

## 十、怎么复跑

```bash
# 五个行业案例 + 一个实测边界对照：S1 → G1 → S2 → G2 → S3 → G3，并出图
OMNIAILAB_NO_NETWORK=1 python scripts/design_sector_cases.py

# 单个案例（school_surveyed 用来对比"正式可确认"状态）
python scripts/design_sector_cases.py hospital
python scripts/design_sector_cases.py school school_surveyed

# 守卫测试
python scripts/run_tests.py --module test_sector
```

产物在 `out/sector-round/<case>/`：`scheme-comparison.md`（面积表、参数来源、矛盾、
概念→平面对照）、`plan-A/B.svg|png`（平面）、`site-plan.*`（总平面）、
`landscape-plan.*`、`index.html`（客户提案）、`summary.json`（门禁三态结论）。

---

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
