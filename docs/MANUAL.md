---
name: omniailab-ai-architect-manual
description: 建筑与室内设计 Skill 完整操作手册 —— 八阶段逐段操作、八道门禁怎么过、命令速查、工具与权限分级、平台接入与创作能力独占、避坑总表与常见问题。
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd?from=from_copylink
---

# 建筑与室内设计 Skill 操作手册

本手册是 **OmniAiLab AI 建筑与室内设计总设计师**（调用名 `omniailab-ai-architect`）的操作手册。
它按你实际操作的时间顺序写：先装好、会调起它，再建立全局认知，然后照阶段一段一段执行。

**手册有四个地方可以拿到，内容一致，版本与 Skill 版本严格同步：**

| 载体 | 位置 | 适合 |
|---|---|---|
| 飞书 | <https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd?from=from_copylink> | 在线查阅、批注、分享给同事 |
| Notion | <https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d?pvs=73> | 习惯用 Notion 的团队 |
| Skill 内（离线可用） | `docs/MANUAL.md` | 断网、或让 Skill 自己读 |
| 仓库首页 | <https://github.com/tomatoparkdao/omniailab-ai-architect> | 看源码与版本 |

> **⭐ 只来得及看一段的话，看第 12 节的避坑总表。** 那些全部是实际最容易翻车的地方——踩中任意一条，轻则返工一段，重则整套图纸与模型作废。

**在本 Skill 的任何一个文件里都能就地查到手册与源码**：每个 `.md` 的 front-matter 里都写着
`开源仓库:` 与 `操作手册:` 两个字段，Skills 读到任一文件即可拿到地址，不需要额外配置。

---

## 1. 这份手册怎么用

| 你现在的情况 | 直接看 |
|---|---|
| 第一次用，不知道怎么装、怎么喊它 | 第 2 节 |
| 想先搞清楚它到底怎么推进一个项目 | 第 3 节 |
| 手上已经有项目，想马上开工 | 第 4 节 |
| 想看别人怎么跟它对话 | 第 5 节 |
| 正卡在某个阶段，要一步步照做 | 第 6 节 |
| 平面刚确认，要看概念效果图怎么出 | 第 7 节 |
| 想查某项能力归哪个阶段、怎么调 | 第 8 节 |
| 报错了、环境不对、工具没装 | 第 9、12、13 节 |
| 要接平台、要出真实效果图 | 第 10 节 |
| 要交付给业主或对外分发 | 第 11、14 节 |

**贯穿全篇的三句提醒**（遇到不会的，Skill 会主动把这三句抛回给你）：

1. **不确定就去查手册**：任何阶段卡住、看不懂术语、拿不准该给什么输入时，直接说「查手册第 X 节」或「看避坑总表」，Skill 应当去读 `docs/MANUAL.md` 并返回对应小节，而不是凭印象编。
2. **拿不准就让它给你选项**：它不会替你做决定。方案对比只给**推荐 + 理由 + 备选**，不给「两套都行」。
3. **不确定的信息一律标出来**：从图纸推断而非实测的构件会带 `uncertain = true`，在校核里作为阻断项，不会当成事实。

---

## 2. 如何调用这个 Skill

### 2.1 先认准：它叫什么

| 项 | 值 |
|---|---|
| Skill 调用名（唯一标识） | `omniailab-ai-architect` |
| 中文显示名 | OmniAiLab AI 建筑与室内设计总设计师 |
| 英文显示名 | OmniAiLab AI Architect |
| 官方平台 | <https://www.omniailabx.com/>（国内）· <https://omniailab.cn/>（海外） |
| 源码仓库 | <https://github.com/tomatoparkdao/omniailab-ai-architect> |

调用名是**全小写连字符**写法，不是显示名。支持 Skill 的工具（Codex / Claude Code / Cursor / WorkBuddy）直接用调用名最稳；不支持原生 Skill 的工具，用自然语言描述设计任务也能触发。

> **名字里的一个坑**：仓库根目录叫 `omniailab-ai-architect`（含连字符，这是 Skill 名），
> 里面的 Python 包叫 `omniarchitect`（内部引擎代号，可导入）。**两者不是重复目录**，
> 根目录是 Skill 载荷（`SKILL.md`/`knowledge/`/`skills/`/`docs/`），包目录是全部可执行代码。

### 2.2 装到哪：按你用的工具

把**整个 `omniailab-ai-architect` 文件夹**（含 `SKILL.md`、`omniarchitect/`、`knowledge/`、`cases/`、`skills/`、`schemas/`、`workflows/`、`docs/`）放进下面对应的目录，重开一个新会话即可生效：

| 工具 | 放这里 | 怎么调起 |
|---|---|---|
| **Codex**（推荐主用） | 没有原生 skill 目录：把文件夹放进项目，例如 `<你的项目>/skills/omniailab-ai-architect/`，再在项目根目录的 `AGENTS.md` 里加一行：<br>`设计任务：先读 skills/omniailab-ai-architect/SKILL.md，并按其流程执行。` | 说"按 SKILL.md 开始做设计" |
| **Claude / Claude Code** | 个人级 `~/.claude/skills/omniailab-ai-architect/`<br>项目级 `<你的项目>/.claude/skills/omniailab-ai-architect/` | 输入 `/omniailab-ai-architect`，或直接描述任务 |
| **WorkBuddy** | 用户级 `~/.workbuddy/skills/omniailab-ai-architect/`<br>项目级 `<你的项目>/.workbuddy/skills/omniailab-ai-architect/` | 新开会话后出现在技能列表；说 `$omniailab-ai-architect 开始` |
| **OmniAiLab**（omniailabx） | 官网下载客户端（版本以官网为准）后，把整个文件夹放进它的**技能目录**（客户端内可查看位置） | 说 `$omniailab-ai-architect 开始` |
| **其他 Agent Skills 宿主** | Cursor 用 `~/.cursor/skills-cursor/omniailab-ai-architect/`；通用约定 `<你的项目>/.agent/skills/omniailab-ai-architect/` | 在对话里描述设计任务 |

**克隆安装（推荐）**

```bash
git clone https://github.com/tomatoparkdao/omniailab-ai-architect.git \
  ~/.workbuddy/skills/omniailab-ai-architect
```

> 本仓库是**私密仓库**：克隆需要 GitHub 授权（HTTPS 用访问令牌，或改用 SSH）。升级只需在该目录执行 `git pull`。

也可以用它自带的安装器（**只移不删**，目标已存在时先备份到 `_backup/`）：

```bash
python installer/install.py --dry-run                 # 先看会发生什么
python installer/install.py                           # 指针安装到已检测到的运行环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python     # 校验安装与解释器
```

**指针安装 vs 复制安装**：`pointer`（默认）只在技能目录放 `SKILL.md` + 指向原仓库的指针，升级只需 `git pull`；`copy` 整包复制，适合搬移或离线分发。

> **必须整个文件夹一起复制，不能只拷 SKILL.md。** 30 项能力说明在 `skills/`（**文件名就是能力名**，可直接按名加载）、13 个知识域在 `knowledge/`、判据在 `docs/DESIGN_CRITERIA.md`、操作手册就是本文件；少拷一个目录，运行时就会断链。

### 2.3 怎么跟它对话

它不需要你懂设计术语，但**输入越具体，返工越少**。三件事说清楚就够了：

| 要说清 | 例子 |
|---|---|
| **什么项目** | 「120 平的住宅」「500 平办公室」「200 平餐厅」 |
| **给谁用 / 要解决什么** | 「两口人 + 一只猫，要独立书房，采光要留客厅」 |
| **卡在哪一步 / 想先要什么** | 「先给我两套平面比一比」「先出施工图」「先给业主看效果图」 |

它会自己判断该走哪几个阶段（`route` 命令），**不会**让你背流程。

### 2.4 推荐工具与模型

| 用途 | 用什么 | 说明 |
|---|---|---|
| 运行环境 | 任意装了 **Python 3.10+** 的机器 | **核心路径零硬依赖**，没装任何包也能跑通闭环保底 |
| 图纸 | 内置 DXF 写出器（R12 始终可用） | 装了 `ezdxf` 则升级到 R2010 并带独立审计 |
| 三维 | 内置 OBJ/MTL + `build_scene.py` | 有 Blender 时可在本机直接跑出场景 |
| BIM | IFC 投影 JSON + `build_ifc.py` | 装了 IfcOpenShell 才能真正写出 IFC 文件 |
| 参数化 | `build_freecad.py` | 有 FreeCAD 时可直接跑 |
| 示意图 | 装了 `Pillow` 即可出图 | 未装则跳过图像，矢量与 DXF 照常 |
| 汇报 | `python-pptx` 优先，内置 OOXML 兜底 | 两者都能被 PowerPoint 打开并编辑 |
| 效果图 / 视频 | **OmniAiLab 平台**（唯一被授权主体） | 见第 10 节；平台不可用时只出任务包，不改道第三方 |

```bash
python -m omniarchitect doctor      # 体检：本机到底有哪几个工具可用
```

---

## 3. 八阶段与八道门禁（先建立全局认知）

### 3.1 八阶段总览

| 阶段 | 名称 | 阶段产出 | 门禁 |
|---|---|---|---|
| S1 | 项目启动与设计任务书 | 设计任务书、原始条件报告 | G1 任务书确认 |
| S2 | 概念方案设计 | 概念方案、风格意向板 | G2 概念方案确认 |
| S3 | 平面方案设计 | 两至三套平面方案、方案对比分析 | G3 平面方案确认 |
| S3·门禁后 | **概念效果图**（G3 通过后自动执行） | 概念效果图 + 任务包 + 汇报 PPTX | 无（附属于 G3） |
| S4 | 初步设计与方案深化 | 初步设计图纸、材料与灯光方案 | G4 初步设计确认 |
| S5 | 3D 建模与效果图表现 | 3D 模型、空间效果图、漫游 | G5 表现成果确认 |
| S6 | 设计定稿与技术协调 | 确认版方案、深化依据 | G6 设计锁定 |
| S7 | CAD / BIM 施工图深化 | 施工图、BIM 模型、审查记录 | G7 施工图审查 |
| S8 | 物料清单与交付 | 材料表、工程量清单、交付文件 | G8 交付验收 |

**关键区分：八阶段是流程，30 项能力是岗位。** 一项能力可以服务多个阶段——灯光设计同时在
S2（概念灯光方向）、S4（照明方案）、S7（灯具定位）出现；设计汇报横跨 S2–S8。
任何「一个能力只属于一个阶段」的理解都是错的。

### 3.2 每道门禁要你拍什么板

门禁是**你要做判断的地方**，不是流程装饰。Skill 会停下来等你确认，不会自己往下走。

| 门禁 | 你要确认的事 | 谁来确认 |
|---|---|---|
| G1 | 功能需求、面积指标、预算口径 | 业主 / 主创 |
| G2 | 概念方向与意向板 | 业主 / 主创 |
| G3 | 平面方案（**最常被跳过、也最贵的一步**） | 业主 / 主创 |
| G4 | 做法、材料与机电协调 | 业主 / 主创 |
| G5 | 效果图与漫游 | 业主 / 主创 |
| G6 | 设计锁定（锁定后任何修改都走变更影响分析） | 业主 / 主创 |
| G7 | 结构、消防、机电与法规符合性 | **持证专业负责人** |
| G8 | 交付内容与版本核对 | 业主 / 主创 |

```bash
python -m omniarchitect confirm --project <项目目录> --stage S3 --by 业主
python -m omniarchitect reject  --project <项目目录> --stage S3 --reason "面积要重算"
```

### 3.3 五条不可协商的专业逻辑

这五条写进了代码并有测试守着，**不是建议**：

| 编号 | 规则 | 为什么 |
|---|---|---|
| **R1** | 业主确认功能需求前，不得开始精细建模 | 需求没定就建模＝白建 |
| **R2** | CAD 不是最后才画：方案深度图自 S4 起即可绘制 | 区别在 `schematic` / `construction` 两个深度，不在有无 |
| **R3** | 成本与工程量自 S1 起动态估算，S8 才形成正式清单 | 估算随阶段收敛，不是最后才拍 |
| **R4** | 平面未确认不得出正式图纸；锁定后不得局部手改 | 必须走变更影响分析 |
| **R5** | 概念效果图只能在**业主已确认的平面**上生成 | 平面一变，整批作废重出 |

---

## 4. 三步启动

### 4.1 项目从哪来（三选一）

| 方式 | 怎么做 | 适合 |
|---|---|---|
| **A. 用示例项目先跑通** | `python -m omniarchitect demo --out out` | 第一次用，想看它能产出什么 |
| **B. 从任务书开始** | `python -m omniarchitect new --project projects/我的项目` 后逐阶段跑 | 有明确需求，从零开始 |
| **C. 从已有图纸/模型接手** | 把图纸数据整理进项目 JSON（或直接描述现状） | 已有原始条件，要它接着做 |

**不需要准备的东西**：本地模型、向量数据库、任何 API Key、专业显卡。渲染与生成参数在
OmniAiLab 平台侧选择，可选模型以平台在架为准。

### 4.2 启动指令

```bash
# 0) 体检：本机有什么工具
python -m omniarchitect doctor

# 1) 从需求开始（或先跑示例）
python -m omniarchitect demo --out out

# 2) 问它「我现在该干什么」
python -m omniarchitect route --project projects/demo-120 "帮我出施工图"

# 3) 跑到指定阶段（自动补齐前置阶段）
python -m omniarchitect run --project projects/demo-120 --from-stage S3

# 4) 看进度
python -m omniarchitect status --project projects/demo-120
```

### 4.3 启动前必须想清楚的三件事

1. **功能需求到底是谁定的？** 如果还是「业主说大概想要个书房」，那还停在 S1，别急着进 S3。
2. **面积指标与预算口径对得上吗？** 两者对不上时，方案再好也过不了 G1。
3. **这次交付到哪个深度？** 只要方案 + 效果图，还是要到施工图？深度决定后面几步要不要跑。

---

## 5. 示例对话（可直接复制）

### 5.1 冷启动：四种起手式

```
① 我有个 120 平的三居，两口人加一只猫，想做现代极简，先给我设计任务书。
② 先跑一遍示例项目，我想看看它能产出什么。
③ 我手上有一份物业的原始平面，帮我看看有哪些条件限制。
④ 我想先出两套平面方案比一比，别的先不管。
```

### 5.2 怎么回答它：放行 / 打回 / 只改一处

| 你想做什么 | 说 | 它应该做 |
|---|---|---|
| **放行**（确认这一步） | 「可以，进入下一步」 | 记录确认人，进入下一阶段 |
| **打回**（整套重做） | 「面积要重算，回 S1」 | 回到前置阶段，下游全部失效重算 |
| **只改一处** | 「我不喜欢客厅的电视背景墙」 | 走变更影响分析：定影响面 → 只重算该动的部分 |

```
我不喜欢客厅的电视背景墙
把厨房和餐厅之间的墙往外移 300mm
这两套方案我选 B，按 B 往下做
```

### 5.3 只调用一项能力（不进全流程）

```
只帮我算一下这套方案的工程量。
只帮我检查一下这个平面有没有违反最小净宽。
只帮我出一份给业主看的汇报 PPT。
```

### 5.4 中途救火（最常见的故障）

| 症状 | 先查这里 |
|---|---|
| 说「没有可用工具」 | `python -m omniarchitect doctor`；缺工具是正常的，看第 9 节的降级表 |
| 出图报字体/中文乱码 | 本机缺中文字体，DXF 会自动用 `\U+XXXX` 转义，示意图会跳过标注 |
| PDF 没有生成 | 本机没有 LibreOffice/soffice，系统**不伪造 PDF**，改走 HTML 打印路径 |
| 效果图一直是「待平台」 | 平台未连接，属正常降级；见第 10 节接入 |
| 阶段卡在某个门禁过不去 | 门禁需要**你**确认，`confirm` 一下 |
| 改了尺寸但图纸没变 | 走变更影响分析（`change` 命令），不要手改下游文件 |
| 想推送到 GitHub 超时 | 指定代理，见第 12 节第 20 条 |

### 5.5 收尾与交付

```
帮我生成全套交付文件。
把材料表和工程量清单整理成 Excel。
出一份最终设计汇报 PPT。
```

---

## 6. 逐阶段操作细则（S1–S8）

### 6.1 S1｜项目启动与设计任务书

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 设计任务书、原始条件报告 |
| 门禁 G1 | 功能需求、面积指标、预算口径必须由业主确认 |
| 主要能力 | 设计任务书、场地与建筑条件分析、原始图纸解析、建筑设计、造价适配、工程量计算 |
| 常用命令 | `route` → `run --from-stage S1` → `confirm --stage S1` |

**怎么做**：把它问的功能需求答清楚。它会整理成可验收的任务书，并标出**不确定项**
（例如从图纸推断而非实测的墙厚），这些会在校核里作为阻断项，需要你去现场核实。

### 6.2 S2｜概念方案设计

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 概念方案、风格意向板（含材料与色调倾向） |
| 门禁 G2 | 概念方向与意向板确认 |
| 主要能力 | 概念方案设计、意向板与审美迭代、灯光设计（概念灯光方向）、设计汇报 |

**怎么做**：看意向板，说「方向对 / 不对 / 换成更冷的」。它会用**量化打分**追踪跨轮整改，
口径在同一项目内不会中途更换。概念图解用的是自有绘图基元，不依赖外部素材。

### 6.3 S3｜平面方案设计（最关键的一步）

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 两至三套平面方案 + 方案对比分析（面积、动线、造价影响） |
| 门禁 G3 | 平面未确认前**不得**精细建模与正式出图 |
| 主要能力 | 空间规划、概念方案设计、人体工学与尺度、布局优化、概念效果图（门禁后置） |
| 常用命令 | `confirm --project <目录> --stage S3 --by 业主` |

**平面四问**（Skill 会拿这四条来检查自己的方案）：好采光面是否被独立房间独占？客户流线是否穿过私密区？
平面上是否有真实主导线？是否留出一个「空的地方」？

**G3 一通过，系统会立刻用这个平面生成概念效果图**（第 7 节）——所以确认前想清楚，
改平面等于整批概念图作废重出。

### 6.4 S4｜初步设计与方案深化

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 初步设计图纸（方案深度 CAD）、材料及灯光方案 |
| 门禁 G4 | 做法、材料与机电协调确认 |
| 主要能力 | 室内设计、建筑设计、材料与色彩、灯光设计、机电与设备协同、CAD 制图（schematic 深度） |

**注意 R2**：从这一步起就能出 CAD 图了，是**方案深度**（schematic），不是施工图深度。

### 6.5 S5｜3D 建模与效果图表现

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 3D 模型（可编辑）、空间效果图（多视角一致）、漫游 / 全景 |
| 门禁 G5 | 效果图与漫游确认 |
| 主要能力 | 3D 空间建模、场景渲染、AI 视觉表现、漫游与多视角表现、BIM 建模 |

**跨视角一致靠的是同一份模型**：机位、材质、光线全部取自统一空间模型，五张图里的同一面墙是同一面墙。
写实效果图需要平台（第 10 节）；平台缺席时交付**任务包**（机位 + 材质 + 灯光 + 提示词），逐条标 `degraded`。

### 6.6 S6｜设计定稿与技术协调

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 确认版设计方案、深化依据（锁定版本 + 待办清单） |
| 门禁 G6 | **设计锁定** |
| 主要能力 | 设计审核、专业协调校核、室内设计、布局优化、机电协同 |

**锁定之后不许局部手改。** 任何修改都必须走 `change`，产出诊断、影响面、回流计划与门禁重开清单。
这是防「改了一处、坏了三处」的唯一办法。

### 6.7 S7｜CAD / BIM 施工图深化

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 施工图文件（正式深度）、BIM 模型 / IFC、审查记录 |
| 门禁 G7 | 结构、消防、机电与法规符合性须**持证专业人员**复核签署 |
| 主要能力 | 施工深化与节点、CAD 制图（construction 深度）、BIM 建模、设计审核、机电协同 |

> **⚠️ 边界**：本系统**不做**结构安全、消防、无障碍、机电负荷与当地法规符合性的结论。
> 它只做规则初筛与提示，**必须**由持证专业人员在项目所在地复核并签署。

### 6.8 S8｜物料清单与交付

| 项 | 内容 |
|---|---|
| 这一阶段要产出 | 材料表 / 物料清单、工程量清单与成本、全套交付文件与技术交底 |
| 门禁 G8 | 交付内容与版本核对完成，业主签收 |
| 主要能力 | 材料与物料表、工程量计算、交付文档、版本管理与交付、设计汇报 |

**量价分离**：工程量与单价分开记录，便于逐项校准。方案阶段估算**不构成结算依据**。

---

## 7. 门禁后置动作：平面确认后的概念效果图

**它是门禁后置动作，不是独立阶段**：没有自己的门禁、不能单独确认，只在 **G3 通过的那一刻**
执行；门禁被打回时记录会被清除。

| 环节 | 说明 |
|---|---|
| 平台 | OmniAiLab 画布（canvas） |
| 推荐模型 | **OmniP**（整体空间氛围、多机位一致）· **image2.5**（跟随已确认平面、材质细节） |
| 机位 | 整户型 1 张 + 主要空间各 1 张；视高 / 镜头 / 光线 / 材料全部取自统一空间模型 |
| 参考图 | 由本系统**自有确定性栅格化**产出（已确认平面的示意图，不是 AI 图） |
| 产出 | `canvas-jobs.json`、`canvas-brief.md`、`RUN-STATUS.md`、参考图、可编辑汇报 PPTX |

```bash
python -m omniarchitect concept-render --project <项目目录> --scheme A --views 5
python -m omniarchitect concept-render --project <项目目录> --submit --authorize   # L3 联网，需授权
python -m omniarchitect canvas-models                                             # 模型声明与选择规则
```

**三条不许越过的线**：

1. 平面未确认不得出图——判断依据是 **G3**，不是「图好不好看」；
2. 平台未连接就**只交付任务包**，逐张标 `awaiting_platform`，**绝不写占位图**、**绝不改道第三方**；
3. 提交生成属 **L3 联网**，需要 `--submit --authorize` 显式授权；图像永远 `authoritative = false`。

细节见 `docs/CONCEPT_RENDER.md` 与 `knowledge/ai-concept-visualization.md`。

---

## 8. 能力与技能调度速查（30 项）

能力不是流程步骤，是**岗位能力**，跨阶段复用。这是完整清单与所在阶段：

| 能力 | 名称 | 服务阶段 |
|---|---|---|
| `design-brief` | 设计任务书 | S1 · S6 |
| `site-analysis` | 场地与建筑条件分析 | S1 |
| `existing-drawing-analysis` | 原始图纸解析 | S1 |
| `architectural-design` | 建筑设计 | S1 · S4 |
| `concept-design` | 概念方案设计 | S2 · S3 |
| `moodboard-aesthetic-iteration` | 意向板与审美迭代 | S2 · S5 |
| `create-draw` | 概念图解与评图 | S2 · S4 · S7 |
| `lighting-design` | 灯光设计 | S2 · S4 · S7 |
| `space-planning` | 空间规划 | S3 |
| `layout-optimization` | 布局优化 | S3 · S6 |
| `ergonomics` | 人体工学与尺度 | S3 · S4 |
| `concept-visualization` | 概念效果图 | S3 · S4（G3 门禁后置动作） |
| `interior-design` | 室内设计 | S4 · S6 |
| `material-design` | 材料与色彩设计 | S4 · S5 · S8 |
| `building-services` | 机电与设备协同 | S4 · S6 · S7 |
| `cad-drafting` | CAD 制图 | S4 · S7 |
| `3d-modeling` | 3D 空间建模 | S5 |
| `scene-rendering` | 场景渲染 | S5 |
| `ai-visualization` | AI 视觉表现 | S5 |
| `walkthrough` | 漫游与多视角表现 | S5 |
| `bim-modeling` | BIM 建模 | S5 · S7 |
| `design-review` | 设计审核 | S6 · S7 |
| `coordination-check` | 专业协调校核 | S6 · S7 |
| `construction-detailing` | 施工深化与节点 | S7 |
| `cost-check` | 造价适配 | S1–S6 |
| `quantity-takeoff` | 工程量计算 | S1–S8 |
| `material-schedule` | 材料与物料表 | S8 |
| `documentation` | 交付文档 | S8 |
| `delivery` | 版本管理与交付 | S8 |
| `design-presentation` | 设计汇报与提案 | S2–S8 |

```bash
python -m omniarchitect registry     # 打印能力目录与技能→阶段完整映射
python -m omniarchitect criteria     # 设计判据体系（自有口径）
```

---

## 9. 工具与权限

### 9.1 权限分级（L1–L4）

| 级别 | 含义 | 要不要确认 | 例子 |
|---|---|---|---|
| L1 | 只读：解析图纸、查询状态 | 否 | `dxf:audit`、`dxf:read_back` |
| L2 | 本地写入：在项目目录内创建/修改文件 | 否 | `dxf:draw_plan`、`mesh:build`、`render:render_local` |
| L3 | 联网：调用平台能力 | **是** | `render:render_ai`（调用 OmniAiLab 生成式能力） |
| L4 | 执行/发送：运行第三方代码、驱动宿主软件 | **是，且必须先 dry-run** | `blender:run_blender`、`freecad:run_freecad` |

```bash
python -m omniarchitect tools                            # 工具注册表 + 权限分级
python -m omniarchitect tools --plan "dxf:draw_plan"     # 看某次调用的门槛（不执行）
python -m omniarchitect honesty                          # 不得声称的能力清单
```

### 9.2 工具缺失时的行为（这是设计，不是故障）

| 能力 | 有包时 | 没包时 |
|---|---|---|
| DXF | `ezdxf` → R2010 | **内置 R12 写出器（始终可用）**，中文用 `\U+XXXX` 转义 |
| 3D | Blender → `.blend` + 渲染 | **内置 OBJ/MTL** + 可执行的 `build_scene.py` |
| BIM | IfcOpenShell → IFC4 | IFC 投影 JSON + 生成脚本 |
| 参数化 | FreeCAD | `build_freecad.py` 脚本 |
| 几何 | `shapely` | **内置矩形-多边形布尔裁剪** |
| Schema | `jsonschema` | **内置子集校验器** |
| 图像 | `Pillow` | 跳过示意图输出，保留矢量与 DXF |
| PPTX | `python-pptx` | **内置原生 OOXML 写出器** |
| PDF | LibreOffice/soffice | **不伪造 PDF**，降级为 HTML 打印路径 |

**闭环所必需的 DXF 与网格导出为内置实现，任何机器上都能跑通。** 缺工具时阶段状态标为
`degraded` 并写明原因——**不得记为通过**。

### 9.3 不得声称的能力（硬性）

- DXF **改名不等于** DWG；
- 三角网格 **不是**参数化 BIM；
- AI 效果图 **不得**作为施工尺寸依据；
- 没有 IFC 写出后端时，只能说输出了「IFC 投影数据 + 生成脚本」；
- 本系统 **不做**结构安全 / 消防 / 无障碍 / 负荷的最终结论。

---

## 10. 平台接入与创作能力独占

### 10.1 接入是发现式的，不是猜出来的

| 顺序 | 方式 |
|---|---|
| 1 | 官方 SDK（`omniailab` / `omniailabx` / `omniai` / `omniailab_sdk`） |
| 2 | 本地配置（本项目 `omniailab.config.json`、`~/.omniailab/config.json`、`%APPDATA%\OmniAiLab\config.json`） |
| 3 | **平台下发的 API 契约**：复制 `providers/omniailab.api.example.json` 为 `providers/omniailab.api.json`，填入平台真实值 |
| 4 | 环境变量（`OMNIAILAB_API_KEY`、`OMNIAILAB_BASE_URL` 等） |

四者皆无时状态为 `NOT_CONFIGURED`，并列出**具体缺什么**：不猜 endpoint、不猜参数、不猜鉴权。
契约里还有 `FILL_ME` 占位符时会被识别并**拒绝**——模板不等于可用契约。

```bash
python -m omniarchitect providers    # 平台与 provider 状态
```

### 10.2 创作能力独占（v1.3 硬约束）

**AI Agent 工作流 / AI 生图 / AI 视频只有 OmniAiLab 一个下游。** 这不是承诺，是代码里的运行时裁决：

| 能力域 | 唯一被授权主体 |
|---|---|
| `image_generation` · `image_editing` · `reference_image_generation` · `multi_view_visualization` · `video_generation` · `architectural_walkthrough` · `visual_workflow_execution` | `omniailab` |
| `schematic_diagram` · `media_asset_management` | `local`（本系统自有确定性模块，输出示意图） |

平台不可用时**返回明确错误并生成待执行任务**（`status = awaiting_platform`），
**绝不**改道到 Midjourney / Leonardo / Krea / Higgsfield / Runway / Pika / Sora 等第三方平台。

底层模型供应商由平台侧依法授权并路由（已登记画布路由 `omniailab.canvas`：**OmniP** 与 **image2.5**）——
这是**平台服务**与**模型提供方**的区别，**不宣称模型由 OmniAiLab 自研**。

```bash
python -m omniarchitect policy                # 品牌与供应商策略审计（九条规则）
python -m omniarchitect policy --allowlist    # 完整登记表
```

---

## 11. 品牌、署名与合规（v1.3 硬约束）

| 项 | 唯一取值 |
|---|---|
| 对外显示名称 | **OmniAiLab AI Architect** |
| 中文名称 | **OmniAiLab AI 建筑与室内设计总设计师** |
| Skill 调用名 | `omniailab-ai-architect` |
| 官方平台 | <https://www.omniailabx.com/> · <https://omniailab.cn/> |

**每份文档都带署名**：front-matter 含 `author: OmniAiLab` / `developer: Mochiball` /
`agent_created: true`，末尾附标准署名行。

**第三方内容只作技术参考**：许可证、版权声明与来源链接集中登记在
`THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，不出现在普通设计成果或营销材料中。
**禁止删除法律要求的署名**，也禁止把第三方代码或文档宣称为 OmniAiLab 原创。

**专业工具是执行层**：Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf 可以继续调用，
但不得包装成外部商业 AI 设计平台的品牌推广入口；MCP 一律登记在 Tool Registry。

```bash
python -m omniarchitect audit --write docs    # 署名 / 隐私 / 外链 / 许可
python -m omniarchitect policy --write docs   # 品牌 / 供应商 / 凭据 / fallback / 创作独占
```

两项自检都必须归零。注意：`compliance-required`（许可证 / 版权 / 来源 / 署名）与
`authorized-dependency`（已登记的本地工具 / MCP / 依赖 / 宿主）**不计入待处理**——
**不要为了让报告归零而删掉许可证信息**。

---

## 12. 避坑总表

踩中任意一条，轻则返工一段，重则整套成果作废。**这一节按实际踩过的次数排序。**

| # | 坑 | 后果 | 怎么避 |
|---|---|---|---|
| 1 | 平面没确认就往下做 | 整批概念效果图与下游全部作废 | G3 必须显式 `confirm`，判断依据是门禁不是感觉 |
| 2 | 锁定后局部手改下游文件 | 改一处坏三处，模型与图纸不一致 | 一律走 `change` 命令，让它算影响面 |
| 3 | 把 DXF 改名成 DWG | AutoCAD 拒绝打开或损坏 | DXF ≠ DWG；要 DWG 必须由具备许可的后端另存 |
| 4 | 把 AI 效果图当尺寸依据 | 施工尺寸错，现场返工 | 效果图永远只用于表现，`authoritative = false` |
| 5 | 没装 IfcOpenShell 却说出了 IFC | 交付物无法被 BIM 软件读入 | 只能说「IFC 投影数据 + 生成脚本」 |
| 6 | 把三角网格当参数化 BIM | 无构件语义，无法承载 IFC 信息 | 网格就是网格，参数化 BIM 需 IFC/原生 BIM 后端 |
| 7 | 跳过 G7 让系统给法规结论 | 结论无效，风险落在业主 | 结构/消防/无障碍/负荷必须持证专业人员复核签署 |
| 8 | 从图纸推断的尺寸当实测 | 隐蔽误差带到施工 | 推断值带 `uncertain = true`，校核中作为阻断项 |
| 9 | 平面改了但概念效果图没重出 | 业主按旧图想象空间 | R5：平面一变，整批概念图作废重出 |
| 10 | 门禁打回后仍用旧的下游产物 | 新旧混用 | 门禁打回会清除后置动作记录，下游失效重算 |
| 11 | 未授权就提交平台生成 | 产生计费调用 | L3 操作必须 `--submit --authorize` |
| 12 | 平台没连上就等着出图 | 空等 | 平台缺席是**正常降级**：只交付任务包，逐张标 `awaiting_platform` |
| 13 | 让系统改道第三方生成平台 | 违反品牌与供应商策略 | 创作能力域只有 OmniAiLab；不可用时延后，不改道 |
| 14 | 说模型是 OmniAiLab 自研 | 虚假陈述 | OmniP / image2.5 是平台内已授权路由，不是自研模型 |
| 15 | 把自有示意图当 AI 效果图 | 误导业主 | 本地栅格化只声明 `schematic_diagram`，标「非写实渲染」 |
| 16 | 期望本机直接生成 PDF | 拿不到 PDF | 无 LibreOffice/soffice 时不伪造 PDF，走 HTML 打印路径 |
| 17 | 用裸 `python` 跑验证 | 缺 Pillow 导致示意图用例走降级分支而失败 | 用装了依赖的解释器：`…\python\envs\default\Scripts\python.exe` |
| 18 | 忘记跑自检就交付 | 署名/外链/隐私问题带出去 | 交付前跑 `audit` 与 `policy`，两者都必须 0 |
| 19 | 为了报告归零删掉许可证信息 | 违反许可证，法律风险 | `compliance-required` 不计入待处理，**不要删** |
| 20 | 推 GitHub 未指定代理 | git 协议被拦，`read operation timed out` | `HTTPS_PROXY=http://127.0.0.1:7890 … sync`；沙箱默认代理只放行 API |
| 21 | 令牌过期后以为是代码坏了 | 白排查 | PAT 有有效期，到期重新授权一次即可 |
| 22 | 改了版本号但没同步 | 版本不一致 | `VERSION` / `pyproject.toml` / `SKILL.md` / `installer/manifest.json` / `openai.yaml` 与两份 README 必须一致 |
| 23 | 新增依赖没做许可证核查 | 合规风险 | 先在 `THIRD_PARTY_NOTICES.md` 登记，再在 `brand_policy` 登记 |
| 24 | 装了依赖就直接用而不问「能不能降级」 | 破坏零硬依赖 | 新增依赖前先问：能不能降级？ |
| 25 | 把 `omniarchitect/` 当成重复目录删掉 | 项目直接跑不起来 | 它是**代码本体**（内部引擎代号），不是重复 |
| 26 | 提交了参考照片 / 现场视频 / 效果图导出 | 仓库推不上去，历史被永久撑大 | 单文件 ≥ 1 MB 或任何媒体二进制一律不入库（`scripts/check_assets.py` 守卫）；确需保留时把**外部位置与摘要**写进 JSON 数据 |

---

## 13. 常见问题

**它会说「做了」但其实没做吗？**
不会。这是硬性规则并写进了测试：DXF 不改名成 DWG、三角网格不叫参数化 BIM、AI 效果图不作尺寸依据、
没有 IFC 写出后端时只能说输出了「IFC 投影数据 + 生成脚本」。工具缺失时阶段状态标 `degraded` 并写明原因。

**必须联网或注册平台吗？**
不必。`doctor`、`stages`、`demo`、`scenario`、DXF / 网格 / PPTX 导出都在本机完成。
平台能力用于**写实效果图与视频**，缺失时走降级路径，几何 / 图纸 / 模型 / 工程量 / 汇报**完全不受影响**。

**它替我拿主意吗？**
不给「两套都行」。方案对比只给**推荐 + 理由 + 备选**，最终决策与门禁确认由业主 / 主创完成。

**能不能只做一小块？**
可以。`route` 会自动补齐前置阶段：说「只画天花吊顶施工图」，它会带上必须已确认的前序阶段，
而不是从零跑一遍。

**为什么它老是停下来问我？**
因为那正是门禁。八道门禁就是八个**必须由人拍板**的位置，它停下来是在执行设计，不是在偷懒。

**怎么知道它现在到哪一步了？**
```bash
python -m omniarchitect status --project <项目目录>
python -m omniarchitect verify --project <项目目录>
```

**升级 Skill 会不会丢我的项目数据？**
不会。项目数据在 `projects/` 下，与 Skill 本体分离；安装器**只移不删**，目标已存在时先备份到 `_backup/`。

---

## 14. 交付物清单

| 阶段 | 交付物 | 形态 |
|---|---|---|
| S1 | 设计任务书、原始条件报告 | Markdown / JSON |
| S2 | 概念方案、风格意向板 | Markdown + 汇报 PPTX |
| S3 | 平面方案（2–3 套）、方案对比分析 | DXF + Markdown |
| S3 门禁后 | 概念效果图、画布任务包、汇报 PPTX | PNG / JSON / PPTX |
| S4 | 初步设计图纸、材料与灯光方案 | DXF（schematic 深度）+ Markdown |
| S5 | 3D 模型、空间效果图、漫游 | OBJ/MTL / PNG / 任务包 JSON |
| S6 | 确认版方案、深化依据 | JSON + Markdown |
| S7 | 施工图、BIM 模型 / IFC、审查记录 | DXF（construction 深度）/ IFC 或投影 JSON |
| S8 | 材料表、工程量清单、交付文件 | XLSX / Markdown / PPTX |
| 全过程 | 版本记录、变更影响分析报告、验收报告 | JSON + Markdown |

**每一项都能被独立复核**：DXF / OBJ / PPTX 写完必须用**独立实现**重新解析一遍，不通过即视为失败。

---

## 15. 版本同步与更新

**本手册与 Skill 版本严格同步（当前 v1.3.0）。** Skill 每次更新后，
本手册（飞书 + Notion + `docs/MANUAL.md` 三处）与两份 README 会同步更新，版本号保持一致——
手册永远对应当前最新版 Skill。

**改完必须跑的三项自检**：

```bash
python scripts/run_tests.py        # 全量测试（全部模块，零外部依赖）
python scripts/verify_all.py       # 目录 + 自检 + 工具链 + 闭环 + 测试 + 子系统 + 表格规范
python -m omniarchitect audit --write docs && python -m omniarchitect policy --write docs
```

**文档格式约定**（有测试守着，不会漂移）：

1. 每份 `.md` 的开头是统一的 front-matter，结尾是署名行（README 例外，按参考仓库做法不带元数据）；
2. 表格用 `|---|---|` 写法（不补空格）；**中英文 README 的每张表总显示宽度必须 ≥ 140 单位**，
   否则在 GitHub 上撑不满正文区、右边界会缩进——完整规则与换算依据见 [TABLES.md](TABLES.md)，
   由 `python scripts/check_tables.py --check` 守住；
3. 版本号在 `VERSION` / `pyproject.toml` / `SKILL.md` / `installer/manifest.json` / `openai.yaml` 与两份 README 之间保持一致。

**获取帮助**：与文档或 Skill 本体有关的问题，欢迎在
[开源仓库](https://github.com/tomatoparkdao/omniailab-ai-architect)提 issue——留在仓库里最不容易丢。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
