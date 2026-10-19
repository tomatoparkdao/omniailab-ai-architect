---
name: omniailab-acceptance-round1
description: 执行闭环验收第一轮 —— 图纸派生参考图、任务生命周期与恢复、两个真实项目的客户首用测试；逐项标注 已验证 / 仅 Mock 验证 / 尚未连接 / 存在阻断
version: 1.11.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 执行闭环验收 · 第一轮

基准 `e682cbf` → 本轮提交记录见 CHANGELOG「后续补充八」。证据目录 `out/acceptance-round1/`
（`session.json` / `summary.json` / 各阶段真实成果），本文只做结论与判据。

## 结论速览

| 项目 | 结论 | 判据 |
|---|---|---|
| L1 Skill 内部流程闭环 | **住宅已验证；办公存在阻断** | A 项目 G1–G8 全签、20 项成果登记；B 项目 G3 拒绝签发 |
| L2 Desktop Agent + Skill + MCP | **尚未连接** | 桌面端无公开调用接口；本仓库无 MCP 客户端 |
| L3 Agent + 画布 + 真实生成 | **尚未连接** | 平台 `NOT_CONFIGURED`，任务停在任务包 |
| 图纸派生参考图 | **已验证**（本地） | SVG+PNG 同源输出，尺寸为矢量文字 |
| 任务生命周期与恢复 | **仅 Mock 验证** | 6 态状态机 + 恢复路径，用 stub 平台跑通 |
| 视觉与 CAD 几何一致性 | **部分验证** | 参考图与 DXF 同源；AI 产出未验证（无平台） |

## 一、图纸派生任务的实际可用性

上一轮 `references` 里写的是 `.dxf` 路径——那只是把字符串塞进 JSON，既不能证明模型收到了
什么，也不能证明它看到的是哪一版几何。本轮改为**由本项目矢量图元输出 SVG + PNG**：

| 检查 | 结果 |
|---|---|
| 参考文件是否存在 | SVG 35,223 B、PNG 33,765 B，均存在且可解析 |
| 是否可作图像模型输入 | SVG/PNG 是；DXF/DWG 明确列在 `not_accepted` |
| 与 DXF 是否同源 | 同一份 `build_primitives()`，房间 12 / 墙 27 / 门 12 / 窗 9 |
| 尺寸与房间名 | 2 条总尺寸（13200 / 10400 mm）、24 条房间名，均为矢量文字 |
| 图像模型能否改写几何 | 提示词与负向约束写死"不得改写墙、门窗、房间位置" |

三条配方所需数据的完整性（`REQUIRED_DATA` 判定）：

| 配方 | 需要 | 结论 |
|---|---|---|
| `plan-color` | 平面几何 + 门窗 + 尺寸 | 齐全 → `awaiting_authorization` |
| `plan-axon` | 平面几何 + 门窗 + 层高 | 齐全 → `awaiting_authorization` |
| `presentation-board` | 平面 + 立面 + 透视 | 缺立面与透视 → `blocked_missing` |

展示板不冒充已完成：`drawing-visuals.md` 里单列"待补充：立面图、三维透视"。
**P0 缺口**：本仓库没有立面适配器，也没有可用的透视生成（平台未连接），
所以三视图展示板目前只能出两块。

## 二、任务执行与资产回流

状态机 `awaiting_authorization → submitted → running → succeeded → asset_validated →
project_linked` 已落进台账（`concept-visual-ledger.json` 的 `state` + `history`）。

| 场景 | 结果 | 判定 |
|---|---|---|
| 正常完成 | 6 态齐全，资产写入 `project.artifacts` | 仅 Mock 验证 |
| 轮询超时 | `poll_exhausted`，任务仍算已受理，不重提 | 仅 Mock 验证 |
| 提交后断线 | `submitted_unknown`，不当成"没发生" | 仅 Mock 验证 |
| 恢复 | `unknown → running → project_linked`，全程提交次数恒为 1 | 仅 Mock 验证 |
| 平台不可用时恢复 | 明确说明"无法核实"，不提交 | 仅 Mock 验证 |

真实平台链路（`submitted` 之后的真实轮询与下载）**尚未连接**：本机 `omniailab` 状态为
`not_configured`，缺 API 契约、`base_url`、`api_key`。没有发起过任何付费请求。

## 三、普通客户首次使用

两个项目都从一句话开始，客户由脚本代理应答、逐条记录，门禁全部走真实判定
（`decide_g1` / G2 `decide_gate` / G3 `approve`），未使用 `--assume-approval`。

| 观察点 | A 住宅 | B 办公 |
|---|---|---|
| 主动了解需求 | 5 个问题，分 5 轮 | 6 个问题，分 6 轮 |
| 是否重复询问 | 0 次 | 0 次 |
| 每轮问题数 | ≤3（系统上限内） | ≤3 |
| 是否展示真实成果 | 20 项成果登记 | 11 项（止于 S3） |
| 是否提示下一步 | 每阶段有 `next_action` | 同 |
| 错误引导 | S6 `degraded`，列出 1 阻断 19 提示 | G3 拒绝并给出两条出路 |
| 保存与继续 | 关掉重载后 S1–S3 仍 confirmed，从 S4 续跑 | 同 |
| 客户改方案 | 局部改动 → 5 项返工 + G4–G8 需重开，未自动应用 | 同（S5/S8） |

A 项目壳体净面积 131㎡、任务书写 150㎡——这条差异在报告里标明，不当作 150㎡ 已实现。
B 项目 = 既有 131㎡ 楼层改办公，60 人；风格未声明时系统不再默认意式极简。

**B 为什么停在 S3**：办公方向的空间原型没有对应平面策略，`verify_scheme` 判
`H-STRATEGY-UNSUPPORTED` → G3 拒绝签发（`G3-CONCEPT-CONFLICT` +
`G3-PROTOTYPE-UNSUPPORTED`），S4 因上游未确认而无法启动。这是**设计能力缺口**，不是门禁 bug：
`PlanGenerator` 目前只支持 `band_day_night` 与 `spine_centre`。

## 四、逐项验收

| # | 项目 | 判定 | 依据 |
|---|---|---|---|
| 1 | Skill 内部流程完成度 | 住宅已验证 / 办公存在阻断 | A 8/8 阶段、8/8 门禁；B 3/8 阶段 |
| 2 | Desktop Agent 可用度 | 尚未连接 | 下载入口存在，无公开接口 |
| 3 | 网站画布是否真正完成任务 | 尚未连接 | 状态 `not_configured`，任务包就绪 |
| 4 | 视觉与 CAD 几何一致性 | 参考图已验证，AI 产出未验证 | 同源图元计数一致 |
| 5 | 客户体验问题 | 见下 | 5 项待改进 |
| 6 | P0 阻断 | 4 项 | 见下 |
| 7 | 本轮修复与测试日志 | 已验证 | 458 passed |
| 8 | 平台端需提供 | 清单 | 见下 |

## 五、客户体验问题清单

1. **单一维度验收会让"能跑"掩盖"跑得对"**：S6 的 `degraded` 只体现在状态位，
   客户看不到"哪一条被阻断"，需要在对话层翻译成一句人话。
2. **专业限制仍然靠读者自己发现**：G3 的"待人工复核 2 项"写在 notes 里，
   建议在成果封面就标出来，而不是等客户翻 JSON。
3. **非住宅方向选择缺少预先说明**：客户选到"无平面策略"的方向时，只在 G3 才知道；
   应在 G2 对比表里就标"此方向需专用深化"。
4. **进度可见性依赖 CLI 输出**：没有面向客户的一页式进度（阶段 / 门禁 / 下一步）。
5. **修改影响只给清单不给排期**：返工 5 项与重开门禁是准确的，但没有"预计影响范围"
   的量化（哪些成果会作废、哪些可保留）。

## 六、P0 阻断

| 阻断 | 性质 | 影响 |
|---|---|---|
| 非住宅原型无平面策略 | 本地能力缺口 | 办公/酒店/商业 G3 无法签发，S4–S8 全停 |
| 平台未配置（API 契约/鉴权/计价） | 平台侧 | 画布调用、真实生成、资产回流全链路不可用 |
| Desktop Agent 无公开接口 | 平台侧 | 无法验证加载 Skill、调度 MCP、操作画布、回写资产 |
| 无立面适配器 | 本地能力缺口 | 三视图展示板只能出两块，立面标待补充 |

本轮**未**为了"看起来完成"而给办公项目放行 G3。

## 七、本轮修复内容

| 修复 | 说明 |
|---|---|
| `reference_plan.py` | 平面参考图由矢量图元输出 SVG/PNG，含尺寸与房间名，清单自述缺什么 |
| `build_plan_visuals` | 参考图真实生成 + 逐配方数据完整性判定；缺项 `blocked_missing` |
| 任务状态机 | 6 态 + `history`；成功路径登记项目资产；未知状态不记 failed |
| `resume_pending` | 有 job_id 只核实；恢复过程提交次数恒为 1；平台不可用就停 |
| G3 接线 | 用"装好方案的模型副本"出参考图，不改 canonical 修订号 |
| 验收脚本 | `scripts/acceptance_round1.py`，两项目全流程留档 |

测试日志：

```
run_tests.py            458 passed / 0 failed（31 模块）
  test_reference_plan          3 项（参考图真实性/同源计数/缺项声明）
  test_client_first_use        4 项（不重复问/一句话到 G1/住宅到 S8/办公 G3 拦截）
  test_billing_safety         11 项（含生命周期 6 态与恢复）
verify_all.py           九段全通过
check_tables            93 文件 359 表 0 违规
normalize --check       230 文件 0 不一致
```

## 八、仍需 OmniAiLab 平台端提供

| 需求 | 用途 | 缺了会怎样 |
|---|---|---|
| API 契约（submit / poll / fetch 端点） | 创建任务、查状态、取结果 | 只能停在任务包 |
| 鉴权方式与 key 下发 | 调用前提 | `NOT_CONFIGURED` |
| 计价声明（单价 + 计量单位） | 费用受控 | 不提交（无法证明不超支） |
| 幂等键支持 | 重试不重复计费 | 只能靠本地台账兜底 |
| 按 job_id 查询 | 断线后核实 | 只能人工到后台查 |
| 结果直链与下载权限 | 取回资产 | 无法回写项目 |
| 资产回写接口（图 + 修订号） | 成果入库 | 只能本地登记 |
| Desktop Agent 本地桥（CLI 或 MCP） | 让 Skill 驱动客户端 | 只能人工在界面里操作 |

桌面端情况：下载页提供 Windows 安装版 0.8.27（含 SHA-256），并写明"本地版使用本站账号登录，
不需要开放 API"。也就是说入口存在、运行时能力**没有可调用的接口**——这一点不是本仓库能补的。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
