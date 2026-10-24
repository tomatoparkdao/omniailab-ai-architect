---
name: design-handoff
description: 设计交接层 —— CAD MCP / SketchUp MCP / 图像平台的真实连接状态、交接包内容与验收口径
version: 1.21.1
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 设计交接层

图纸（S3–S7）回答"设计是什么"。这一层回答另一组问题：

> 这张图该画成什么样的效果图？模型该怎么建？发出去的指令真的到达了吗？

三处最容易自欺的地方，在这里被钉死：**没连上却说连上了**、**提示词与平面无关**、
**模型与图纸各说各话**。

## 一、三条通道的真实状态（2026-10-24 实测）

| 通道 | 状态 | 依据 |
|---|---|---|
| CAD MCP | `not_configured` | 项目根无 `mcp.json`；`omniarchitect mcp` 如实输出 |
| SketchUp MCP | `not_configured` | 同上 |
| OmniAiLab 图像平台 | `not_configured` | provider 探测缺 SDK / 配置 / base_url / api_key / API 契约 |

这三条都不是"暂时没做"，而是**缺外部交付物**：MCP 服务器要你提供地址与工具名，
图像平台要你提供 API 契约（`providers/omniailab.api.json`）。

因此本轮的交付方式是：**连接层做成真的，缺口做成可执行的**。

- `tools/mcp_bridge.py` 是真实的 JSON-RPC 客户端（`initialize` → `tools/list` →
  `tools/call`）；握手成功、工具名对上，才记 `available`；只实现一半记 `partial`
  并点名缺哪个操作；连不上记 `not_configured` 并留下任务包。
- SketchUp 没有 MCP 时，输出 `build_model.rb`——在 SketchUp 里 `load` 一下就能建出
  墙与洞口标记的脚本，不是一段说明文字。
- 图像平台没有连接时，输出 `visual-brief.json` 里的专业提示词，**不生成任何替代图**。

## 二、交接包里有什么

`omniarchitect studio --project <dir>`（S4 也会自动生成到 `04-preliminary/handoff/`）：

| 文件 | 内容 | 谁用 |
|---|---|---|
| `visual-brief.json` / `.md` | 3 个镜头的提示词、禁止项、必查项，数字全部取自模型 | 出图的人 / 平台 |
| `linework.svg` | 墙填实、洞口挖白的几何控制图 | 图像模型的控制输入 |
| `sketchup/build_model.rb` | 可直接运行的建模脚本（长度带 `.mm`） | SketchUp |
| `sketchup/camera_jobs.json` | 固定机位，与效果图逐张可比 | 出图与截图 |
| `sketchup/sketchup-job.json` | 建模任务与连接状态 | 交接/复核 |
| `consistency.json` | 任务书是否过期、网格与模型是否同尺寸 | 校核 |
| `mcp-status.json` | 两条 MCP 的握手结论 | 验收 |
| `README.md` | 上面这些的状态、缺什么、下一步怎么做 | 客户/内部 |

## 三、提示词怎么来的

不是"现代简约、高级感"这种填空。每个镜头由五段拼成，数字全部来自统一空间模型：

1. **几何事实**：房间数与类型、最大空间及面积、层高、外轮廓尺寸；
2. **材料**：已确认方案里的主材，没有就写"按已确认方案的材料表"，不编；
3. **光线**：按专业分（建筑日光 35°／室内自然光 3500K／景观低角度长阴影）；
4. **重点**：该专业该看什么（入口识别性／家具与界面／园路与水景关系）；
5. **不可改变项**：房间数、门窗数、层高、外轮廓、内墙厚度——全部写成硬约束。

景观用"分区"，建筑与室内用"房间"。把种植带说成房间，提示词就会要一个室内空间，
这是专业口径错误，测试守着。

## 四、一致性核查能做什么、不能做什么

**能自动判**（`consistency.json`）：

- 任务书是否与模型脱节（模型改了房间数，任务书还写旧的 → `stale` 并列出差异）；
- 导出的 OBJ 与模型外轮廓是否同尺寸（米/毫米写错会被识别并换算，只说换算不报错）。

**不能自动判**：

- 效果图里的门窗位置、比例、家具尺度是否忠于平面。程序只能保证提示词与几何同源，
  图面是否照做，必须人看图。`consistency.json` 里这些永远记 `pending_human`，
  不会标成"通过"。

## 五、接上真 MCP 要做什么

1. 把 `mcp.json.example` 复制为项目根的 `mcp.json`；
2. 填 `command`/`args`（stdio）或 `url`（http，目前只登记不探测）；
3. 用 `toolAliases` 把契约操作名钉到服务器真实工具名——**不猜**；
4. 跑 `omniarchitect mcp --project <dir>` 看握手结论；
5. 再跑 S4，`sketchup-job.json` 里会出现真实的 `mcp_call` 结果。

契约（`CONTRACTS`）里规定的操作：

- CAD：`draw_plan`、`draw_elevation`、`draw_section`、`export_dxf`
- SketchUp：`create_walls`、`create_openings`、`capture_view`、`export_obj`

服务器提供不全时状态是 `partial`，缺的操作在报告里点名——不让"能画平面但画不出剖面"
被记成可用。

## 六、外部规范 Skill

入口由 `paths.EXTERNAL_STANDARDS_SKILL_URL` 提供（`omniarchitect standards` 可查）。

**只给链接，不下载**：规范正文体量以百 MB 计且持续更新，复制进本仓只会得到过期副本，
还把仓库撑大。按需读 raw 里的子 Skill，读完即用，结论记来源、标"待持证人员复核"。

## 七、边界

- 本层不产生尺寸依据：线稿与提示词都来自模型，但图片不是图纸；
- 洞口在 SketchUp 脚本里是**标记**，不是切割（Make 版无实体工具），须人工完成；
- 没有 MCP 时，`not_configured` 就是最终结论，不拿 OBJ 冒充"SketchUp 已建模"；
- 合规结论、结构安全、消防与无障碍仍须持证人员在项目所在地复核签署。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
