---
name: omniailab-SECTOR_DESIGN
description: SECTOR_DESIGN —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: 1.12.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 行业设计层：从"知道是什么项目"到"按这个行业排"

分类解决的是"这是什么项目"。这一层解决另一半：**这类项目该怎么排、为什么这么排、
排到什么程度为止**。它不新增阶段、不新增门禁、不新建几何系统。

## 一、三个入口，各管一件事

| 入口 | 作用 | 不做什么 |
|---|---|---|
| `sector.brief.build(ctx)` | 从 S1 原话抽出可算的量，列出矛盾与缺口 | 不猜数、不替客户定 |
| `sector.moves.moves(brief)` | 由这些数推出 2–3 条组织方式，写明代价 | 不给固定套话 |
| `sector.program.build(brief)` | 折成房间清单，交给已有平面算法 | 不另写排布算法 |

S3 的调用顺序是 `brief → program → planner.PlanGenerator(zone_bands)`。
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
   不是第二个用途：委托范围仍只看客户说没说"做室内"。

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

## 四、排布：一种通用算法 + 各行业的带序

`planner.zone_bands` 是这一轮唯一新增的排布算法：把房间按"带"铺开，
走廊插在指定位置。行业差异体现在三件数据上，而不是三套代码：

| 行业 | 带序 | 设计进深（mm） | 走廊 |
|---|---|---|---|
| 学校 | 教学带 / 后场带 | 教室 7500 | 3000 |
| 医院 | 候诊 / 诊室 / 医技后勤 | 诊室 4500、医技 12000 | 2400 |
| 酒店 | 客房 / 客房 + 后场 | 客房 8000 | 1800 |
| 厂房 | 生产 / 仓储办公 | 生产 60000、仓储 30000 | 无 |

三个细节是踩出来的：

1. **带宽反算轮廓**：轮廓宽度取"最宽那条带按设计进深排开的宽度"，
   再按此反算各带深度。只按面积比分配会把诊室压成 2 m 宽的窄条。
2. **余量要画成"预留"**：一条带末端剩几米，图上不能留白——留白会被读成"漏排了"。
   余量 ≤18% 时按带宽补齐（并在 deviations 里写"放大了多少"），超过就画"预留（交通/辅助）"。
3. **通长外墙要按重叠判断**：外墙是一条长线时，"墙中点靠近房间"会判错，
   一扇窗都生不出来；改成判断墙段与房间贴边是否共线且有重叠。

## 五、G3：有数据才算方案

`sector.check.assess` 挂在 `assess_plan_gate` 上，只加核验、不改判据：

- **没数据不算完成**：教育/医疗/酒店 ≥6 个房间、厂房 ≥3、景观 ≥3 个分区，
  否则 `G3-NO-DESIGN-DATA` 阻断——任务清单不是专业方案；
- **建议轮廓要复检**：按任务书反算的轮廓（`proposed`）只作讨论起点，
  签发前须实测复核（`G3-PROPOSED-ENVELOPE`，条件项而非阻断）；
- **类型限制进条件**：医疗属 `specialist`，写明"医疗工艺与感控须专项顾问"；
- **缺输入如实写**：`G3-MISSING-INPUT` 列出本轮按假设推进的项。

## 六、边界（不掩饰）

| 项 | 现在能做到 | 还不能 |
|---|---|---|
| 学校 | 校园总平面关系、教学楼标准层、教室/专用教室/办公/服务配比 | 办学标准符合性、疏散宽度校核 |
| 医院 | 门诊医技层、科室面积与洁污分区、手术与 ICU 的规模推算 | 医疗工艺、感控、机电专项 |
| 厂房 | 单层主厂房、工艺方向、仓储与厂前区、柱网反算 | 设备基础、结构、消防类别核定 |
| 酒店工装 | 客房标准层、后场比例、电梯与服务间位置 | 品牌标准、消防与隔声实测 |
| 景观 | 分区占比、游线关系、水面与绿化构成 | 竖向标高、放线、植物规格与苗木 |

**没有专属程序就明说**：`sector` 只覆盖 education / healthcare / industrial /
hospitality / landscape；其余类型不进入这条分支，也不套住宅模板冒充。

## 七、怎么复跑

```bash
# 五个行业案例：S1 → G1 → S2 → G2 → S3 → G3，并出图
OMNIAILAB_NO_NETWORK=1 python scripts/design_sector_cases.py

# 单个案例
python scripts/design_sector_cases.py hospital

# 守卫测试
python scripts/run_tests.py --module test_sector
```

产物在 `out/sector-round/<case>/`：`scheme-comparison.md`（面积表与矛盾）、
`plan-A/B.svg|png`（平面）、`site-plan.*`（总平面）、`landscape-plan.*`、
`index.html`（客户提案）、`summary.json`（门禁结论）。

---
© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
