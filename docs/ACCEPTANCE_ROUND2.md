---
name: omniailab-acceptance-round2
description: 第二轮验收 —— 参考图真实进入请求、面积与容量可行性前置、办公平面策略落地；逐项标注 已验证 / 仅 Mock 验证 / 尚未连接 / 存在阻断
version: 1.13.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 执行闭环验收 · 第二轮

基准 `b64e08f`。本轮只做三件事：**把参考图真正送进请求**、**把可行性提到选方案之前**、
**给办公一个真能用的平面策略**；另外两件是证据分级与桌面端能力发现。

## 结论

| 项目 | 判定 | 依据 |
|---|---|---|
| 参考图进入 Provider 请求 | **仅 Mock 验证** | 契约不在本机；请求体已截获验证 |
| 面积口径不一致的主动诊断 | **已验证** | 150 vs 131.6 → G1 人话提示 + G2 条件 |
| 办公容量可行性 | **已验证** | 60 人/132㎡ → G1 阻断；改 25 人 → 通过 |
| 办公平面策略 | **已验证** | `office_cluster`，G3 可过也可拒 |
| 客户首次使用证据等级 | **已纠正** | 全部标 `scripted_e2e`，另加无图纸 C 案 |
| Desktop Agent 连接 | **尚未连接** | 客户端已装，无公开调用接口 |
| 真实画布生成 | **尚未连接** | 平台 `not_configured` |

## 一、参考图必须真的进请求

审计发现旧实现三处硬伤：`_params()` 不带 `references`、`workflow` 固定 `concept`、
`stage` 固定 `S2`。也就是说 `drawing-visuals.json` 里的 SVG/PNG 从未进入过模型请求。

现在的映射：

| 参数 | 来源 | 验证方式 |
|---|---|---|
| `references` | 任务的真实文件路径 | 请求体截获 |
| `stage` / `target` / `scope` | 任务自身（S3 / plan-color / reference_image_generation） | 断言相等 |
| `revision` | 当前模型修订 | 修订不符 → 拒发 |
| `reference_meta` | 文件名/格式/字节/sha256 | 与磁盘逐字节比对 |

传输方式由**契约**决定，不猜字段：`base64` / `url` / `asset_id` / `multipart` 四种；
契约没写 `references.mode` 或 `accepted_formats` 时**直接拒发**并说明缺什么。
DXF 明确归入 `not_accepted`；契约只接受 png 时，SVG 会被拒。

七项测试覆盖：字节一致、本地路径不外发、未知方式拒发、SVG 不被默认支持、
缺格式声明拒发、坏 PNG 拦截、multipart 走文件体。

**未验证的部分**：平台真实契约不存在，所以这是 Mock 验证；`base64` 之外的三种方式
只在假契约下跑通，没有对真实端点发过请求。**没有发起任何付费提交。**

## 二、面积口径：先把两个数字摆出来

`feasibility` 新增 `area_basis` 与 `F-AREA-BASIS`：

| 口径 | 数值 | 说明 |
|---|---|---|
| 客户说的 | 150.0㎡ | 一句话里的数字 |
| 模型实测套内 | 131.6㎡ | 不含墙体与公摊 |
| 外轮廓 | 131.6㎡ | 含墙体，不等于建筑面积 |
| 差异 | 12% | 触发条件项，须客户确认以哪个为准 |

G1 摘要新增「面积与容量」一节，用人话写：客户口径更大、差 18.4㎡、三个口径不可混用。
该结论同时进入 G2 的条件清单（`G2-COND-F-AREA-BASIS`），并在 G3 仍可追溯。

不把通用人均面积当法规：办公容量用的是**规划经验区间**，文中明确标注
「经验区间，不是法规指标」，法规符合性仍由持证专业人员复核。

## 三、办公容量：装不下就直说

60 人 / 132㎡ = 人均 2.2㎡ → `F-CAP-01`（blocker），G1 直接阻断，并给出三条出路：
减到约 22–25 人常驻、改轮用工位、换场地或把会议外移。

客户做出取舍后（改为 25 人常驻），系统**重新判定**而不是强行放行：

```
G1 blocked  | 60 个人放进 132㎡ 明显装不下（人均仅 2.2㎡）
客户决定     | 减少常驻人数至 25 人，其余轮用工位
G1 confirmed| 已形成任务书基准 r1
G2 confirmed| 概念基准 C-A
G3 confirmed| 一致性 pass
S4–S8       | ok（S6 degraded：1 阻断 19 提示）
```

## 四、办公平面策略：一套真算法，能过也能拒

新增 `office_cluster`（`PlanGenerator` 第三套策略，与住宅 band / spine 结构不同）：

* 前场带：接待 + 会议沿一条带布置，访客动线止于主通道；
* 开放办公是**一整块**连续空间（实测 72.7㎡），不切小间；
* 后场竖排专注间与服务，形成声环境硬边；
* 两套方案靠「会议带换边 + 通道 1200/1500」区分，不是随机数。

一致性校核新增 `H-CAPACITY`：按整套可用面积 ÷ 人数重算，人均 < 4㎡ 判失败。
所以 60 人那版平面即使 G1 被书面接受，G3 仍然拒绝；25 人那版正式通过。
`test_office_strategy.py` 4 项覆盖：布局不是住宅带、两套方案确实不同、可行通过、不可行失败。

**范围说明**：只实现了「活动带（图书馆式）」一个原型；其余 8 个办公原型仍是
`plan_strategy=""`，选到它们 G3 依然拒绝。这是刻意保留的边界，不是遗漏。

## 五、证据分级：脚本化 ≠ 真实客户

`acceptance_round1.py` 的 A/B 两个用例现在显式标注：

```json
"evidence_level": "scripted_e2e",
"evidence_note": "客户由脚本代理应答、几何来自 demo 壳体；只证明门禁与流程正确"
```

新增 **C 案**：只给一句话、**没有图纸、没有几何、没有方案**。

| 环节 | 结果 |
|---|---|
| S1 | ok，精度 `diagnostic`，问了 4 个问题（0 重复） |
| G1 | 通过，但明确标注只支撑诊断级 |
| S2 | ok，概念可作为探索稿 |
| S3 | **blocked**：「没有可用的平面几何……这不是系统故障」+ 补图清单 |
| 结论 | 概念与任务书有效，补图后无需重做 S1/S2 |

三者差异：

| 维度 | A/B（scripted_e2e） | C（真实首用形态） |
|---|---|---|
| 几何来源 | demo 壳体 | 无 |
| 能到哪一步 | S8 | S2 |
| 客户要做什么 | 只需确认 | 补图纸/实测 |
| 结论性质 | 方案可交付 | 探索稿 |

脚本签署只能证明门禁校验正确，**不代表获得实际业主授权**——报告与 JSON 都写了这句。

## 六、Desktop Agent：装是装了，但没有调用口

本机实测（证据 `out/acceptance-round2/desktop-evidence.json`）：

| 能力 | 状态 | 证据 |
|---|---|---|
| 客户端安装 | 已装 | `%APPDATA%/Omni AiLab Studio`，开始菜单快捷方式 |
| Skill 加载机制 | 字段存在、未加载 | `workbench/tasks-v3.json` 的任务含 `skillId`（当前空串） |
| 画布 | 字段存在 | 同一记录含 `canvas`（当前 null） |
| MCP | 未发现可用配置 | `connectors/<hash>/runtime` 为空，无 `mcp.json` |
| CLI | 未发现 | 安装目录无 CLI 可执行文件 |
| 素材回读 | 未知 | 记录含 `workspace.path`，未见回读接口 |

所以：**数据结构证明它有 Skill 与画布的概念，但没有公开的本地调用契约**。
要程序化驱动，需要客户端团队提供以下任一项：

1. 本地 CLI：`run-task --skill <path> --workspace <dir>`（最轻）；
2. 本地 MCP server：暴露 canvas / 文件读取 / 任务状态；
3. Electron 层的 IPC 白名单（需签名与授权文档）。

本轮**没有**尝试逆向或绕过登录态。

## 七、修改与测试

| 文件 | 改动 |
|---|---|
| `concept/visual.py` | `_params` 传参考图/阶段/目标/能力域/修订；修订不符或文件缺失即拒发；几何复核待办 |
| `providers/omniailab.py` | 契约化参考图装载（4 种方式）、multipart 提交、资产上传、格式与字节校验 |
| `intake/feasibility.py` | 面积口径 `area_basis`、`F-AREA-BASIS`、办公容量 `F-CAP-01..04` |
| `intake/gate.py` | 容量阻断与条件、面积口径进 G1 摘要、需求判定不再强依赖功能表 |
| `concept/gate.py` | G2 继承 S1 可行性；已接受项降为条件不再重复阻断 |
| `concept/handoff.py` | `H-CAPACITY` 一致性校核；原型不支持时不再误报 |
| `planner.py` | `office_cluster` 策略（前场带 / 开放办公 / 后场列）、面积差额告警 |
| `workflow.py` | 按项目类型选策略；S3 缺几何给人话阻断；G3 出图前置检查 |
| `concept/prototypes.py` | 活动带原型声明 `office_cluster` |
| `scripts/acceptance_round1.py` | 证据等级、无图纸 C 案、容量矛盾解决回环 |

测试日志：

```
run_tests.py            469 passed / 0 failed（33 模块）
  test_reference_transport     7 项（映射/拒发/多格式/坏文件）
  test_office_strategy         4 项（布局/差异/通过/拒绝）
  test_feasibility...          并入 client_first_use 4 项
verify_all.py           九段全通过
check_tables            94 文件 368 表 0 违规
normalize --check       235 文件 0 不一致
```

## 八、尚未完成与阻断

| 项目 | 原因 | 需要什么 |
|---|---|---|
| 真实参考图传输 | 无平台契约 | 契约声明 `references.mode` 与 `accepted_formats` |
| 画布真实生成 | 平台未配置 | API 契约 + 鉴权 + 计价 |
| Desktop Agent 集成 | 无本地调用接口 | CLI / MCP / IPC 三选一 |
| 其余 8 个办公原型 | 未实现策略 | 逐个验证后再放开，不一次性铺开 |
| 立面 / 剖面派生 | 无立面适配器 | 新增立面输出能力（下一轮） |

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
