---
name: omniailab-changelog
description: 变更记录 —— 自 v1.0.0（八阶段工作流）增量开发，未重建项目、未覆盖既有成果、既有测试全部保留并通过。
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 变更记录

## v1.4.0 · 后续补充四 — S2 概念方案设计专业化升级

S2 原来的实现写死了两个住宅策略（「中部服务脊」「南北动静横分」）再加一句风格名。
办公项目拿到同样两句，酒店也是。业主说一句「现代意式极简」，系统就当成概念做完了。

本轮把 S2 做成真正的概念设计过程，核心是拆开一件常被混为一谈的事：
**概念方向 ≠ 设计风格**。空间原型决定房间怎么组织、人怎么走、光怎么进来；
风格决定它看起来像什么。同一原型可配不同风格，同一风格也能落成不同空间策略。

### 新增子系统 `omniarchitect/concept/`（12 模块）

| 模块 | 职责 |
|---|---|
| `context.py` | 读 S1 与 G1 基准为可推理结构（每项带出处），算信号 |
| `prototypes.py` | 22 个空间原型 × 6 类项目（住宅/办公/酒店/餐饮/展厅/建筑） |
| `directions.py` | 按证据选原型、凑三套不同家族、配视觉语言 |
| `palette.py` | 审美判据条件化（见下） |
| `diagrams.py` | 确定性 SVG：功能关系 / 分区 / 动线 / 采光 / 序列 / 体量 |
| `moodboard.py` | 六格意向板 + 真实色板与材料板（色值取自风格库） |
| `visual.py` | OmniAiLab 概念视觉（复用 providers 注册表） |
| `compare.py` | 八维比较 + 总设计师推荐（未评估项不折算） |
| `gate.py` | G2 判定、概念基准、风格锁定绑定 |
| `handoff.py` | `concept-handoff.json` 与 S3 一致性校核 |
| `deck.py` | 可编辑概念提案（23 页，`concept-options` 版式） |
| `cli.py` | `concept` 子命令（generate/status/select/gate/handoff/deck） |

### 一个引擎，两个入口

`run --stage S2` 与 `concept --action generate` 都调 `generate_bundle()`，同一项目产物一致。
与 S1 同一条纪律：不允许第二套实现。

### 审美判据不再全项目通用

冷调打底、暖材 ≤40%、黑 3–8%、60-30-10 是住宅极简的经验，不是普适规律。
现在每条判据带适用条件（风格标签 + 项目类型），逐条给出「不适用 + 为什么」：

* 「暖材」按材料词判断（木/皮革/藤/织物/黄铜），不按色相——意式极简的暖白墙面是打底，
  按色相算会得出 100% 并误判不合格（第一版真实踩到）；
* 风格自己声明了色量分配时以声明为准，不硬套 60-30-10；
* 酒店/餐饮不设暖材上限（暖色是产品的一部分）。

### S2 视觉与 G3 后效果图严格区分

S2 概念视觉依据概念主张与风格库，不含真实几何；G3 后依据已确认平面。
两者产物命名、状态与说明全部不同，混用会让业主以为看到的是自己家。

### 开发中修掉的 6 个真实缺陷

1. G1 确认时未先落定访谈状态 → `brief_digest` 随后变化，误报「业主改了需求」；
2. 交接文件是生成时的快照，选概念后不刷新 → S3 读到 `not_selected`；
3. `verify_scheme` 把 `daylight_rooms_served="4/6"` 当整数解析 → S3 崩；
4. 隔离类要求被记成「通过」→ 假通过，改为待人工复核；
5. 功能覆盖检查拿需求描述硬套房间名 → 必然误报，改为只核对任务书真有的房间；
6. 「不支持的平面策略」条件从推荐方向继承到选定方向 → 无关条件误挂。

### 验证

`run_tests.py` 全绿；`verify_all.py` 九段全通过；`audit`/`policy` 0；表格 0 违规；
新增 `test_concept.py` 18 项（对应验收 A–L）。

---

## v1.4.0 — 单 Skill 架构纠正：设计风格系统并入主 Skill

本轮是一次**架构纠正**，不是功能增量。此前把「设计风格系统」建成了一个独立工程
（Design Style Intelligence），这是架构偏差：`OmniAiLab AI Architect` 只能有一个主 Skill。
本轮把它**整体并入**主工程，并删除合并过程中暴露出的**五处重复实现**。

### 并入的能力（全部可由主 Skill 直接发现与调用）

| 能力 | 落点 |
|---|---|
| 47 种建筑与室内设计风格结构化知识库（八族 × 20 字段） | `knowledge/styles/*.json` |
| 风格索引与按需加载（179 个标签，不整体读入上下文） | `knowledge/styles/catalog.json` |
| 风格分类与检索 | `omniarchitect/style/catalog.py` |
| 三方案风格推荐（稳妥 / 个性 / 混搭，逐条可归因） | `omniarchitect/style/recommender.py` |
| 中英双语结构化提示词编译（8 种目标） | `omniarchitect/style/compiler.py` |
| 跨机位一致性指纹与几何保持规则 | 同上 |
| 风格与空间关系检查、材料与灯光体系、设计意图核对 | `omniarchitect/style/hooks.py` |
| 唯一生成出口（委托 provider 层，平台不可用则延后） | `omniarchitect/style/provider_bridge.py` |
| 零依赖 Schema 校验器 | `omniarchitect/style/validation.py` |
| Schema：设计风格、编译提示词 | `schemas/design-style.schema.json`、`schemas/compiled-prompt.schema.json` |
| CLI | `python -m omniarchitect style <子命令>`（16 个） |
| 测试 | `omniarchitect/tests/test_style_*.py`（5 个模块） |
| 内容来源声明与第三方依赖登记 | `THIRD_PARTY_NOTICES.md`（设计风格内容**全部自有**，无第三方许可证留档） |

### 删除的五处重复实现（"同一规则两份实现"的来源）

| 原先自己实现 | 现在来自 |
|---|---|
| 项目根与目录常量（`paths.py` 自己推算 `parents[1]`） | `omniarchitect.paths` |
| 署名与 front-matter（自带 `attribution.py`） | `omniarchitect.registry` |
| 平台探测（自己读契约、自己判 `FILL_ME`、自己拼 missing） | `omniarchitect.providers` |
| 八阶段与门禁（导出快照再读） | `omniarchitect.stages`（同包直接引用，**快照文件已删除**） |
| 独立 CLI（`build_parser()` / `main()`） | 主 CLI 的 `style` 子命令 |

**这不是形式统一，而是修掉一个真实故障源。** 分开时手写的门禁措辞与阶段模型存在
**4 处不一致**（G2「概念确认」/ G3「平面确认」/ G5「表现确认」/ G8「交付确认」，
而权威定义是「概念方案确认」「平面方案确认」「表现成果确认」「交付验收」）。
这种漂移不抛异常，会一路飘到给业主的汇报里。合并后比对变成同进程内的对象引用。

### 顺带修掉的两处文档缺陷

1. **`SKILL.md` 与 `README` 的阶段表门禁名**：与阶段模型不一致（同样是那 4 处），
   而 `SKILL.md` 正是 Agent 读的入口 —— 等于在教错名字。已改为权威全称，
   `README_EN.md` 同步译为对应英文。
2. **`catalog.json` 被当作风格记录校验**：它在独立工程里位于根目录，并进
   `knowledge/styles/` 后与数据同目录，导致 47 条风格全部校验失败。
   已抽出 `style_files()` 作为"哪些是风格记录"的唯一定义。

### 单 Skill 架构保证（有测试守着）

- **一个 Skill**：仓库内 `SKILL.md` 恰好一份。
- **一个安装过程**：`installer/` 单一入口，无需第二个安装器。
- **一个仓库**：远程 `origin` 一个，不再建第二个。
- **零外部路径依赖**：全仓对独立工程目录的引用为 **0 处**。
- **框架快照已删除**：`test_style_frame.py` 断言 `FRAME_FILE` 不存在、
  `hooks._CORE_STAGES is stages.STAGES`（同一对象，不是副本）。

### 版本

- `1.3.0` → **`1.4.0`**，七处一致：`VERSION` / `pyproject.toml` / `SKILL.md` /
  `installer/manifest.json` / `openai.yaml` / `README.md` / `README_EN.md`。
- 已发布的 `v1.3.0` tag **未改动**。

### 原独立工程的处置

- 其仓库标记为**已合并归档**（新增 `MERGED.md` + README/SKILL.md 顶部横幅），
  **保留为本地备份，未删除**。
- 合并前的完整状态（两个工程的 git 历史与工作树）备份在
  `E://OmniAiLab-Backup-2026-10-17//`。

### 验证

- `run_tests.py`：**350 passed / 0 failed**（22 模块）
- 用户要求的十三项验证全部通过（单 Skill 可用、无第二目录 / 安装 / 仓库等）

### 后续清理 — 第三方 Skill 内容、外链与品牌宣传

按「全仓内容必须自有、用户面不出现外部内容」的要求复查，清掉残留在设计风格系统
立项记录里的**第三方 Skill 内容**：

| 清除项 | 原因 |
|---|---|
| `docs/STYLE_REFERENCE_AUDIT.md` | 五个第三方仓库（其中两个是第三方 Skill）的参考审计全文，含项目名与仓库标识 |
| `LICENSES/LICENSE-jac2020-2020_architectural-visualization-prompt-library.txt` | 第三方许可证原文；本仓未复用、不分发其任何内容，非法律必需 |
| `LICENSES/LICENSE-ur-grue_autopunk-media-skills.txt` | 同上 |
| `LICENSES/LICENSE-chrzamz_ui-styles-skill.txt` | 同上；且其附注含一条指向 `TonnyWong1052/UI-Prompt`（Web 前端 UI 风格提示词库）的外链，与建筑室内设计毫无关系 |
| `THIRD_PARTY_NOTICES.md`「设计风格系统的参考项目审计」一节 | 改写为「内容来源（全部自有）」声明，不再出现任何第三方项目名与仓库标识 |
| `installer/manifest.json` 4 条失效记录 | 随上述文件重新生成 |

**并修掉一个真实缺陷**：`normalize_attribution.py` 会往 `LICENSES/LICENSE-*.txt` 上盖本仓署名——
这会把别人的许可证读成「本仓出具的许可证」，属冒充自研/混淆归属。已加
`NO_ATTRIBUTION_PREFIXES` 守卫，这类文件一律不加本仓署名。

**修完这一轮后 `LICENSES/` 只剩 `README.md`**——本仓不含任何第三方作品内容，
也就没有任何需要留档的许可证原文。目录本身保留（策略规则 `licence-completeness`
要求它存在，用于承接将来真正需要随附的许可证）。

**本机另清掉一份参考 Skill 副本**：`out/ref-director/`（`omniailab-ai-director` 的只读副本，
7 个文件 314 KB）。删除前已逐字节核对：`SKILL.md` / `README.md` / `README_EN.md` /
`openai.yaml` / `VERSION` 与上游 `main` 完全一致，`ref-camera.md` 与
`ref-onboarding.md` 分别是上游 `references/CAMERA-LIGHT SKILL.md` 与
`references/ONBOARDING SKILL.md` 的原样改名。**无任何本地独有内容**；
该目录位于 gitignore 的 `out/` 内，从未进入仓库历史，需要时从上游仓库重拉即可。
链路核查：全仓 0 处引用、installer 打包 259 个文件不含它、`out/` 完全未被 git 跟踪。

**保留项**（真实依赖，不属于「不必要的第三方内容」）：可选 Python 库
（ezdxf / Pillow / python-pptx / jsonschema / shapely / pytest）与用户自备的本地专业工具
（Blender / FreeCAD / IfcOpenShell / AutoCAD）继续在 `THIRD_PARTY_NOTICES.md` 逐项登记——
许可证完整性检查要求其必须存在，缺项会被判 `forbidden`。

**商业案例与品牌宣传**：复查无残留（`cases/` 三份是自创通用任务书，不含第三方事务所 /
项目 / 作品名；九条策略规则 `action_count = 0`）。
**AI 生图与视频生成**：唯一被授权主体 `omniailab`，第三方回退 `forbidden`——
能力域在平台未连接时一律标记 `awaiting_platform`，不改道（见 `python -m omniarchitect providers`）。

### 表格规范：README 中英文版左右对齐（形成规范 + 检查器 + 测试守卫）

**问题**：GitHub 渲染 Markdown 表格用的是 `width: max-content; max-width: 100%` ——
**宽度由内容撑开，源码无法指定**。内容少的表就撑不满正文区，右边界缩进一截，
于是同一页里表格左右不齐。截图里的「能力清单（30 项）」只有 75 个显示宽度单位
（正文区约 119），短了将近一半。

**诊断**（显示宽度单位：中日韩字符记 2、其余记 1；正文区 ≈ 950px ÷ 8px ≈ 119）：

| 文件 | 不达标的表 |
|---|---|
| `README.md` | 能力清单 75、八阶段 94、五条规则 107、概念效果图环节 87、画布模型 133、推荐工具 113、设备要求 94、贡献方向 117、单能力速查 136（共 9 张） |
| `README_EN.md` | Capability list 103（共 1 张） |

**处置：补真实内容把表撑到正文区之上**（表宽一旦超过正文区，浏览器压到 100%，所有表边界自然一致）：

| 表 | 做法 | 内容来源 |
|---|---|---|
| 能力清单（中英） | 新增「说明 / What it does」列 | `skills/<能力>.md` 的 `description`，压缩成一句 |
| 八阶段 | 阶段产出写全，门禁补审批人 | `stages.py` 的 `deliverables` / `gate.approver` |
| 五条规则 | 「为什么」写清后果 | 既有 `AGENTS.md` 第 2 节口径 |
| 概念效果图环节 | 新增「落点与依据」列 | `providers/canvas.py`、`omniailab.models.json` |
| 设备要求 | 新增「说明」列 | 既有降级路径口径 |
| 其余 4 张 | 把现有列写足（不新增列） | 原文事实 |

**禁止的做法**（写进规范，避免后人用错手）：

- 用空格或 `&nbsp;` 填充 —— Markdown 折叠空白，`&nbsp;` 污染正文且不解决「内容真的不够」；
- 编造内容凑宽度 —— 写不出第五列，说明这张表本该改写成列表；
- 改写成 HTML `<table width="100%">` —— 失去 Markdown 可编辑性，diff 不可读；
- 加对齐冒号 `:---:` 来「凑齐」—— 那是列内文字对齐，与表宽无关。

**规范沉淀（三处，缺一不可）**：

| 落点 | 内容 |
|---|---|
| `docs/TABLES.md`（新增） | 问题成因、宽度换算与 140 阈值推导、五条硬规则 T1–T5、补内容正误对照、常见错误表 |
| `scripts/check_tables.py`（新增） | T1 列数一致 / T2 无空单元格 / T3 分隔行紧凑 / T4 落地页表宽 ≥140 / T5 列数 ≤6；`--check` 供守卫，`--all` 可对全仓施加表宽检查 |
| 测试与验收 | `test_integration.py` 新增 2 项（全仓 0 违规 + 中英文 README 逐表 ≥140）；`verify_all.py` 新增第 9 段 |

**结果**：中英文 README 共 40 张表全部 ≥ 140（最小 140，最大 894），全仓 88 个文件
304 张表零违规。检查器跳过 `out/`（运行时产物）与 `projects/`（用户项目数据）。

#### 补漏：量宽口径修正（测错了，所以漏了）

上一版的 `check_tables.py` **按原始 Markdown 量宽**，把 `[操作手册](https://example.org/very/long/path)` 的
URL 也算了进去。GitHub 只渲染链接文字、URL 藏在 `href` 里一个字符都不占——于是窄表被
误判为达标。用户指出「文档地图」仍然没对齐，正是这个漏检。

修正后按**渲染后可见文字**量：

| 写法 | 计入宽度 |
|---|---|
| `[文字](https://example.org/x)` | 只算「文字」 |
| `**粗体**` / `` `代码` `` | 去掉标记符号 |
| `甲<br>乙` | 取较宽的一行，不相加 |
| HTML 标签 / 图片 | 不计 |

修正后重新体检，中英文 README 共 5 张表其实不达标（此前全被判为达标）：

| 表 | 原测（错） | 实宽 | 补法 |
|---|---|---|---|
| README · 文档地图 | 213 | **81** | 新增「里面有什么」列，逐份文档写一句内容提要 |
| README_EN · Documentation map | 252 | **114** | 同上（What's inside），并补上漏掉的 `docs/TABLES.md` 行 |
| README · 联系与支持渠道 | 241 | **118** | 「适合用来」列写足 |
| README · 单能力速查 | 140 | **136** | 「它会给你什么」补「+ 回填位置」 |
| README · 能力清单 | 141 | **139** | 两条「说明」补足 |

修正后：`README.md` 20 张表最小 140、`README_EN.md` 20 张表最小 152，全部达标。

`docs/TABLES.md` 同步补了「量的是渲染后可见文字」一节与对照表，
`test_integration.py` 的表宽断言也改用 `cell_width()`——同一处口径不再有两份实现。

### 手册载体称谓定稿：只写「飞书」与「Notion」

这条涉及措辞的规则改过两轮仍未收口：第一轮去掉了「主」和「镜像」，但改后仍多带了一个限定词，
仍然带了多余的限定词。本轮按用户要求**全文搜索、一次收口**：手册载体**只写载体名本身**。

| 位置 | 处理 |
|---|---|
| 两份 README 的徽章（URL 编码形式） | 手册徽章的文案不再带限定词 |
| 两份 README 的链接文字与手册列表 | 统一为「飞书」「Notion」，去掉「主」「镜像」「同内容」这类限定 |
| `SKILL.md` 手册入口描述 | 同上 |
| `omniarchitect/manual.py` / `cli.py` | 模块 docstring、「手册」子命令输出与 `--help` 尾注同步 |
| `omniarchitect/brand_policy.py` | 自有 URL 登记处的注释同步 |
| `docs/MANUAL.md` 载体表 | 两行只写载体名 |

**关键坑：徽章文案是 URL 编码的。** 上一轮按原文 grep 抓不到它，所以漏了一处——
本轮改为「原文 + URL 解码后」双通道扫描，才发现徽章里还写着旧措辞。

**顺带消歧**：交付判据里有一处同形词，指代的是**被批注的那份成果文件**，
与手册载体无关，但容易被误读，已改为「成果主文件 + 意见 → 批注版交付物」
（`registry.py` 与 `docs/DESIGN_CRITERIA.md` 同步）。

**保留**：`镜像` 一词在别处仍有正当用法——构件的镜像对称（`knowledge/styles/*.json`）、
两份 README 互为镜像、打包与镜像分发。这些与手册载体无关，不改。

**守卫**：`test_integration.py` 新增
`test_the_manual_carrier_is_named_feishu_and_notion_only`，
对全仓执行「原文 + URL 解码」双通道扫描，出现限定写法即失败。

### README 开头改版：文案重写、整块左对齐

原来的开头是「居中标题 + 居中一句介绍」，定位说得含糊（只讲"全流程 AI 总设计师"，
没讲清与"只会出效果图"的工具差别）。本轮按新的定位文案重写，并把**开头整块改为左对齐**。

| 项 | 原来 | 现在 |
|---|---|---|
| 标题 | `<h1 align="center">` HTML 居中 | Markdown `#` 标题，左对齐 |
| 简介 | 居中两行（业务阶段 / 产出清单） | 四段左对齐：定位 → 覆盖环节 → 规格一行 → 执行方式 |
| 徽章 | 居中 | 左对齐（`<p>` 不加 `align`） |
| 语言切换 | 居中 | 左对齐 |

四段文案的顺序与作用：**① 定位**（不止于出效果图，而是参与全过程）→ **② 覆盖环节**
（设计需求到专业交付，一口气说清起点与终点）→ **③ 规格**（一个 Skill · 8 大设计阶段 ·
30 项专业能力 · 47 种设计风格）→ **④ 执行方式**（OmniAiLab 创作平台 + MCP 工具协同）。

`README_EN.md` 同步译为英文并同样左对齐。文案里的数字与实现一致（8 阶段 / 30 能力 / 47 风格），
没有夸大。

顺带修掉 `normalize_attribution.py` 里一句会过期的注释（原写「直接以居中的 HTML 标题开始」）。

### 手册地址换新：Notion 换到公开站点，两个载体统一为干净地址

| 载体 | 旧 | 新 |
|---|---|---|
| 飞书 | 同一 wiki 页 | 同一 wiki 页，**不带任何来源追踪参数** |
| Notion | `app.notion.com/p/tomatopark/3fba28d2e37880ac9be5dd199c99677d` | `tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d` |

**关于查询参数**：两个载体在「复制链接」时都会附带来源标记（飞书是 `from`、Notion 是 `pvs`）。
实测确认那些参数只是**来源标记，不改变文档权限**——匿名访问时带不带都一样。
既然对可达性没有帮助，只会让同一份地址在仓库里出现两种写法，已统一为
**不含任何查询参数的干净地址**，并加守卫测试防止再引入变体。

**可达性实测（两个地址都验过，结论不同）**：

| 地址 | 匿名访问结果 |
|---|---|
| 飞书 wiki 页 | 15 次跳转到 `accounts.feishu.cn` 登录页 → **外部用户打不开**，需在飞书侧把分享设为「互联网上获得链接的人可阅读」 |
| Notion 公开页 | `200`、零跳转，抓到真实标题「建筑与室内设计 Skill 操作手册」→ **外部可读** |

**改动源头只有一处**：`omniarchitect/paths.py` 的 `MANUAL_CN_URL` / `MANUAL_NOTION_URL`。
front-matter 的「操作手册」字段由 `normalize_attribution.py` 从这两个常量取，
`python -m omniarchitect manual` 与生成器报告头也读这里——所以改常量 + 跑一次统一化即可。

实际改动：**91 个文件、飞书 103 处、Notion 13 处**（含 90 处 front-matter 与 README/文档正文链接、
徽章 href、`brand_policy.OWN_URLS` 登记）。

`OWN_URLS` 同步为新的 Notion 页与站点前缀；旧的 `app.notion.com` 条目随之替换，不再保留。

**可达性实测**（改完即验证，避免换成一个更糟的死链）：
- 飞书 → `200`，跳转 `accounts.feishu.cn` 登录页（私有 wiki 的正常行为，wiki ID 保留在 redirect 里）
- Notion → `200`，最终 URL 与所给完全一致

### 两个自有入口：参考图素材库与导演技能

两件事：素材库（Luxora AI）作为找参考图的入口；方案视频需要更生动时，可调用另一条自有技能
（`omniailab-ai-director`）。两者都是本项目自有，所以可以挂在用户面材料里。

**参考图素材库** —— 这里有一个不能含糊的边界：库里汇总的是各设计平台公开发布的作品，
**权利属于各自的创作者**，"公开发布"不等于"授权复制"。所以定为两层：

| 层级 | 能做什么 | 产出 | 进交付物 |
|---|---|---|---|
| 调研级 | 看构图 / 材质 / 色调，提取可验证特征 | `reference-log.md`、`keywords.json` | 只有**结论**能进 |
| 交付级 | 用自有、已授权或本系统产出的图 | 意向板、汇报 PPTX | 图本身能进 |

新增 `docs/REFERENCE_SOURCES.md`：两类来源、两层判据、五步用法（先有词再看 → 只看关系 →
提取可验证特征 → 落成词与比例 → 记来源）与六条红线。

**导演技能** —— 移交的是**分镜与运镜脚本**，不是生成任务。它解决"怎么讲"，
不解决"讲的是什么"（空间事实只认已确认模型），也不负责出片；`video_generation` 与
`architectural_walkthrough` 的唯一被授权主体仍是 `omniailab`。新增 `docs/VIDEO_PRODUCTION.md`：
三种形态的区分、五个移交信号、四段分工、六条硬性边界与六项移交清单。

**代码**：新增 `omniarchitect/reference.py` 与 CLI `reference`（打印两个入口与各自边界，
`--json` 可机读）。两个地址登记进 `brand_policy.OWN_URLS`，合规审计不再视为外部推广链接。

**守卫**：`test_reference_and_director_entries_are_first_party` 要求两个地址只有一种写法
（不允许重新带上来源参数）、且必须被 `OWN_URLS` 覆盖；`test_reference_command_lists_both_entries`
要求每个入口都带边界说明，且它指向的细则文档真实存在。

**顺带修掉两个真实缺陷**：

1. `SKILL.md` 加完 7c 节后涨到 416 行，超过渐进式加载上限（400 行）——已把细节下沉到两份 docs，
   入口只留一行指针，现为 398 行；
2. `test_every_document_carries_the_omniailab_signature` 与 front-matter 一致性测试不跳过
   `.pytest_cache/`——**跑过一次 pytest 就必然失败**（pytest 会在里面写一个没有本仓署名的
   `README.md`）。已抽出统一的 `SCAN_SKIP_PREFIXES` 供多处复用。

### S1 专业智能化升级：从被动生成任务书到主动项目启动

**升级前**：S1 只做一件半事——把已有的 `program` 与 `constraints` 拼成 `design-brief.md` 与
`site-report.md`。进入条件写的是「需求、场地、原始图纸已收集」，真实项目根本满足不了；
整个阶段没有提问机制，也不记录「哪条是推断、哪条没核实」。业主只给一句话时，系统只能干等
或拿模板填满。

**升级后**：S1 成为真正的启动过程。代码在 `omniarchitect/intake/`（9 个模块），
全部规则驱动、可测、可复现，不依赖任何模型调用。

| 能力 | 落点 | 关键行为 |
|---|---|---|
| 三种启动情形 | `interview.detect_start_mode` | 一句话 / 有资料 / 资料齐，决定先问还是先读 |
| 按类型的动态访谈 | `profiles.py` + `interview.py` | 6 类项目 11–19 问；同槽不重问、依赖门控、每轮 ≤3 问 |
| 首句信息提取 | `interview.seed_from_text` | 面积 / 城市 / 人数 / 风格自动记下，标注「待 G1 确认」 |
| 使用行为矩阵 | `needs.py` | 记活动而非房间；11 条活动线索；每行带来源与状态 |
| 资料尽职调查 | `diligence.py` | 五态置信度 + 按影响面阻断，不是一律阻断 |
| 五类可行性 | `feasibility.py` | 面积 / 行为 / 预算 / 周期 / 技术，逐条带证据与备选 |
| 设计机会 | `opportunities.py` | 9 字段；只输出有证据的项，不足 3 项就少于 3 项 |
| S1 成果包 | `report.py` | 8 份，绑定 id + revision 并登记 artifact |
| G1 基准 | `gate.py` | 三决策映射既有状态机 + 基准摘要比对 |

**S1 进入条件已改（代码 + 文档 + 门禁 + 测试同步）**：

- 旧：`需求、场地、原始图纸已收集` / `预算区间与目标入住时间已知`
- 新：`业主提出项目想法、初步需求或已上传资料即可启动（不必先集齐全部资料）` +
  `资料完整度决定本轮可产出的精度：缺尺寸不出依赖尺寸的权威成果，缺结构不批准结构改造`
- 新增精度三级 `diagnostic / schematic / authoritative_capable`，`diagnostic` 的项目在
  `stage_state.can_start` 里被拒绝进入 S4/S5/S7，理由写明「资料仅支持诊断级」

**阻断范围按影响面定**（这是本轮最重要的判断）：结构未证实 → 挡 S4 且不批准拆改；
尺寸未证实 → 挡 S3（平面要在真实尺寸上成立）；报批未确认 → 挡 S7；
预算与审美 → 不阻断，只降级为区间与假设。`conflicting` 比空白更危险，额外挡 S2 要求先澄清。

**G1 不再是一个按钮**：`approved / revision_requested / blocked` 映射到既有的
`confirmed / rework / blocked`，不另造状态机。存在阻断级可行性问题时 `approved` 会被
自动降级为 `blocked`，确实要过必须显式 `force` 并在基准里记 `forced: true`。
确认时记录 `baseline_digest`（program + constraints + answers + 假设 + 不确定项 id），
之后任何改动都会让摘要不一致，`check_baseline()` 返回 `requires_change_analysis = true`，
**原确认版保留，不静默覆盖**。

**新增数据模型**：`schemas/intake.schema.json`（`project.meta.intake`，含 profile / start_mode /
precision / interview.answers / sources / uncertainty / baseline）。已用 jsonschema 实测校验通过。

**新增 CLI**：`python -m omniarchitect intake --action start|ask|answer|register|status|analyze|gate`，
`--json` 全可用，逻辑全在包内，CLI 只做加载—调用—保存。

**开发中修掉的三个真实问题**（都不是「跑通就行」）：

1. 首句说了「150㎡ 在杭州，一家三口」，系统仍重复问面积与人数——补了 `seed_from_text`
   与中文数字解析（`三` → 3），完整度从 4% 直接到 46%；
2. 业主答「结构不清楚」没有进入不确定登记，尽职调查形同空转——补了问答→登记联动
   （`_UNCERTAINTY_FROM_ANSWER` 与 `_evidence_state`），五态映射刻意悲观：
   「有图纸」记 documented、「只有拍照」记 inferred；
3. 预算答案写「硬装 80 万」却没被解析，可行性一直报「预算未定」——补了 `_budget_from_text`，
   现在能算出 `5,333 元/m²` 并落在参考区间内。

**限制（如实列出，未做的不假装做了）**：

- 访谈是规则驱动，不理解语义歧义；业主表述绕时需要人工介入改写答案；
- 使用行为矩阵的活动识别基于关键词，未命中时保留原句并标 `inferred`；
- 五类可行性只看已有数据，几何为空时只报「需核实」不给结论；
- 造价参考区间是规划口径，不是当地报价，也不替代造价咨询；
- 结构、消防、无障碍、法规符合性仍须持证专业人员复核签署。

**验证**：

- `run_tests.py` 377 passed / 0 failed（23 模块，新增 `test_intake.py` 21 项）
- `verify_all.py` 九段全通过
- `schemas/intake.schema.json` 用 jsonschema 对实际 `project.meta.intake` 校验通过
- `audit` 内容 0 / 策略 0；`policy` 待处理 0；`check_tables` 91 文件 0 违规
- 端到端实测：一句话需求 → 访谈 6 轮 → 成果包 8 份 → G1 自动因结构未证实降级为 `blocked`

### S1 正式验收前的集成修复：让智能 S1 真正接管主工作流

上一轮把 S1 引擎建起来了，但它和主流程是**两套并行实现**：`workflow.stage_S1()` 仍是旧版
只出两份文件；G1 有五个确认入口，其中四个绕过审查；`--assume-approval` 直接把人写成
「业主/主创（假设）」。本轮不增功能，只把这几处接好。

**一、一个 S1 引擎，两个适配层**

`workflow.stage_S1()` 不再自己拼任务书，改为调用 `intake.generate_bundle()`；
成本估算也下沉进 bundle（原先只有 `run` 算，CLI 不算，导致同一项目两份 brief 不一致）。
实测同一项目：`run --stage S1` 与 `intake --action analyze` 的 8 份成果**除「生成时间」一行外
逐字节一致**，测试 `test_the_two_entry_points_produce_the_same_bundle` 守着。

无几何资料不再有崩溃风险：`envelope_polygon` 取不到轮廓时条件报告写明「尚无几何数据，
本报告只汇总已知资料，不含任何尺寸结论」，S1 正常产出 8 份（精度 `diagnostic`）。

**二、G1 只剩一个入口**

新增 `StageRunner.approve()` 作为唯一审批通道。`confirm` 命令、`run_stage(confirm=True)`、
`--assume-approval`、`intake --action gate` 全部经过它，S1 一律走 `intake.decide_gate`。
`--assume-approval` 现在带 `source="demo"`：**确认阶段状态照旧，但不写 `baseline`**，
只写 `demo_approval`，`check_baseline()` 会明确回「仅有演示确认，未形成可引用基准」。

**三、G1 判定改成四类后果**

旧逻辑是「有 blocker 就挡住」，结果是结构一根墙没核实，S2 都进不去。
现在拆成：**阻断当前门禁**（需求矛盾、无需求）/ **限制后续阶段**（结构、尺寸、报批）/
**要求专业复核** / **允许附条件推进**（预算、推断需求）。

| 情况 | 旧行为 | 新行为 |
|---|---|---|
| 结构未核验 | G1 全挡 | G1 可过，S4/S7 受限，须专业复核 |
| 尺寸未确认 | G1 全挡 | G1 可过，S3 不得出正式平面 |
| 需求 400m² 装 131m² | 自动挡 | 挡，且逐项 `--acknowledge` 才放行 |
| `--force` | 什么都能过 | 只解需求矛盾；安全类限制不归 G1 管，解不开 |

**四、阶段守卫把限制落到工作内容上**

新增 `intake/guard.py`：`check_stage()` 按「哪个阶段做哪类工作」给结论。
S3/S4 是**限制**（可推进，但点名禁止拆改图、禁止精确尺寸图），S7 是**阻断**
（施工图不得基于未证实条件）。限制会写进阶段产出的 `notes`，后续不会被误当成无限制成果。

只对**已登记**的项生效——模型自带的 `uncertain` 仍走原有校核，旧项目与 demo 行为不变。

**五、可信度不能靠文件名升级**

`verified` 现在要求三样齐：核验人、时间或版本、能找到的来源文件。缺一样降级 `documented`
并写明缺什么。`documented` 的结构仍**不许拆改**——图画过不等于现场就是那样。
判据细化到主题：`documented_blocks` 让尺寸类（有 CAD）可以出方案图，但结构类仍受限。

核实后可用 `--action verify --uid U-STRUCTURAL` 关闭该项，限制立刻解除；不关闭就会留下
永久性阻断。

**六、基准与变更真正联动**

`baseline_digest` 拆成两个：`brief_digest`（需求/约束/来源）与完整摘要（再加不确定项状态）。
前者变 = 业主改了需求，必须走变更分析；只有后者变 = 条件核实了，任务书没变。

确认后修改需求不再只是"返回一个标志位"：`invalidate_from("S1")` 把 S1 及下游置为返工、
写 `change_log`、`check_baseline()` 返回 `change_kind="brief"`。原确认版保留，不会被覆盖。

**七、测试**

新增 `test_s1_integration.py` 13 项，对应验收 A–I：

| 场景 | 断言 |
|---|---|
| A 一句话 → 访谈 → 成果包 → G1 | 无几何也出 8 份，精度诊断级，业主确认成基准 |
| B G1 后进 S2 | S2 可运行且无阻断 |
| C 结构未核验限制 S4 | S4 不阻断但带限制，S7 整体受阻 |
| D 尺寸未确认限制 S3 | S3 可示意、不可出正式平面 |
| E 旧 confirm 不能绕 | 需求矛盾时 `runner.confirm` 也返回非 confirmed |
| F 演示不冒充业主 | `baseline` 为空、`demo_approval` 标注 demo |
| G 核实解除限制 | S7 由阻断转为放行，基准记为「限制变化」 |
| H 确认后改需求 | S1 回 pending、change_log 有记录、`change_kind=brief` |
| I 全流程回归 | 八阶段 `run_all` 无失败阶段 |

全量 `run_tests.py` **390 passed / 0 failed**（24 模块）。

---

## v1.3.0 · 后续补充三 — 全盘检查：能力说明补齐、安装引导对齐参考、示例库扩充

版本号仍为 **1.3.0**（全仓统一，不新开小版本）。本轮是一次**全盘审计**：把「文档承诺」与
「仓库实际」对齐，补掉所有缺口。

### 补掉的最大缺口：`skills/` 能力说明缺 11 项、命名无法定位

**问题**：文档一直承诺「30 项专业能力说明在 `skills/`」，实际只有 19 份——18 份编号文件
（`01-brief.md`…`18-revisions.md`）+ `design-presentation.md`，且**编号与能力名不可互推**：
Agent 拿到 `ergonomics` 这个能力名时无处定位。18 份编号文件还是 42 行的通用英文模板。

**处理**：
- 全部改为 **`skills/<能力名>.md`**（30 份），**文件名即能力名**，可按名直接加载；
  旧编号文件删除（其能力已被全部覆盖，逐个核对过 `capability` 字段）。
- 30 份全部重写为实用内容（**70–110 行**，中位 88 行）：六节结构 —— 做什么 / 什么时候用·不用 /
  输入→输出 / 操作步骤 / **判断清单（可判定的判据，含数值区间）** / 硬性规则 / 常见坑 / 与阶段的关系。
- `registry.load_registry()` 新增 **`brief_file`** 字段指向 `skills/<slug>.md`，`version` 从该文件读；
  `legacy` 降级为纯历史记录（v1.0 编号）。`registry` 命令现在逐项打印 ✓/✗，缺文件会显式告警。

### 新增 `openai.yaml`（接口元数据，参考仓库有而本仓缺）

`interface.display_name` / `short_description` / `author` / `developer` / `default_prompt` /
`policy.allow_implicit_invocation`，与 `SKILL.md` 同版本。是「隐式调用」与「默认提示词」的落点。

### README 安装引导对齐参考仓库 `omniailab-ai-director`

- **安装表工具与排序完全对齐**：**Codex（推荐主用）→ Claude / Claude Code → WorkBuddy →
  OmniAiLab（omniailabx）→ 其他宿主**，其后接 **「克隆安装（推荐）」**。
- 快速开始重排为**五步小白引导**：一、装到哪 → 二、资料从哪来（三选一）→ 三、启动指令 →
  四、启动前必须想清楚的两件事 → 五、全程你只需要回答两种话（+ **「只想用其中一项能力时」
  9 行点名表**）。
- 章节顺序对齐参考：`快速开始` 提到 `全流程总览`（原「八阶段工作流」）之前。
- 新增 **「获取帮助」** 章节（手册 / Skill 内直接问 / `manual --topic` / 仓库 issue / 官方站）。
- 删掉过期数字：`15 个模块、238 项测试` → `16 个测试模块`（不再写死条数，避免每次加测试都要改 README）。
- 同步改了 `README_EN.md`（20 节 / 20 表逐项一致），页脚改为只留英文署名。

### 表格样式全仓统一（此前遗漏的第三条格式规则）

同一份 Markdown 里 `|---|---|` 与 `| --- | --- |` 混用（此前 85 : 66）。参考仓库一律用紧凑写法，
故全仓统一到 `|---|---|`：**146 行表格、30 个文件**被改写。
规则写进 `scripts/normalize_attribution.py` 的 `normalize_tables()`——**跳过代码块**，
`--check` 继续作为测试守卫。生成器（`brand_policy` / `compliance_audit`）的表格字面量同步改成紧凑写法。

### 示例库扩充（`examples/` 从 1 → 4）

新增 `examples/README.md`（索引）、`examples/cold-start-prompts.md`（**4 种起手式 + 30 项能力
一句话点名表 + 卡住时的三句话**）、`examples/deliverable-checklist.md`（逐阶段产物清单 +
五件必须存在的东西 + 四条不许出现的说法）。`demo-brief.md` 改为中英对照并加「示范了什么」。

### 其它一致性修正

- `knowledge/INDEX.md` 版本小节 `1.1.0` → `1.3.0`，并加「须与 `VERSION` 同步」的约束。
- `AGENTS.md` 文件表：知识域 `12 个` → `13 个`；skills `29 份` → `30 份（文件名 = 能力名）`；
  新增 `openai.yaml` 行。
- `docs/WORKFLOW.md` 里「原始的 18 份说明书全部保留…新增 `19-design-presentation` 系列能力」
  的过期表述已重写。
- `compatibility/agent-skills.md` 的「29 项专业能力说明」→「30 项（文件名 = 能力名）」。
- `SKILL.md` / `README` 目录树补 `openai.yaml`、`CHANGELOG.md`、`examples/` 实际说明。
- `docs/MANUAL.md` §2.2 安装表同步为参考排序 + 补「克隆安装（推荐）」（飞书 / Notion 待同步）。

### 新增防漂移测试（+4）

- `test_every_capability_has_a_specialist_brief`：30 项能力必须各有 `skills/<slug>.md`，
  且不许有多余文件。
- `test_specialist_briefs_declare_matching_capability_and_stages`：每份说明的 `capability`
  必须等于文件名、`stages` 必须等于 `CAPABILITIES` 的定义。
- `test_readme_install_table_lists_tools_in_the_reference_order`：安装表工具顺序锁定。
- `test_readme_guides_the_first_time_user_through_five_steps`：五步引导小节必须齐全。

**验证**：`run_tests` **252 passed / 0 failed**（16 模块）；`normalize --check` 160 文件
**0 处不一致**；`verify_all` 六段全通过；`scenario --name all` 3/3；`audit` 0；`policy` 0 禁止项。

---

## v1.3.0 · 后续补充二 — 操作手册、README 对齐参考仓库、仓库与手册地址入册

版本号仍为 **1.3.0**（全仓统一，不新开小版本）。

### 新增操作手册（可被技能调用）

- **`docs/MANUAL.md`**：完整操作手册，15 章 —— 这份手册怎么用 / 如何调用 / 八阶段与八道门禁 /
  三步启动 / 示例对话 / 逐阶段操作细则 S1–S8 / 门禁后置动作（概念效果图）/ 能力速查 30 项 /
  工具与权限 / 平台接入与创作能力独占 / 品牌署名合规 / **避坑总表 25 条** / 常见问题 /
  交付物清单 / 版本同步。
- **手册同时发布三处，内容一致、版本同步**：飞书（可批注）· Notion · 仓库内
  `docs/MANUAL.md`（**离线可用**）。
- **新增 `omniarchitect/manual.py`**：手册指针模块。把「去查手册」做成**可在代码里查表定位**的东西，
  而不是文档里的一句建议：
  - `SECTIONS` 把 23 个主题映射到手册章节（`degraded` → 9.2、`platform` → 10、`pitfalls` → 12 …）；
  - `hint(topic)` 给一行提示，`pointer(topic)` 给三处地址，未登记主题兜底到避坑总表。
- **新增 CLI `manual`**：`manual` 列三处地址与主题表；`manual --topic <主题>` 定向；
  `manual --read [--section "避坑"]` **离线读手册正文指定章节**；`--json` 机器可读。
  `--help` 的 epilog 也印出手册与仓库地址。
- **把提醒接到实际会卡住的地方**：`doctor` 有工具缺失时、`providers` 平台未配置时、
  `concept-render` 状态非 ok 时、`present` 的 PDF 未生成时——都会打印「不会处理？看操作手册「X 节」」。
- 新增 `omniarchitect/tests/test_manual.py`（10 项）：手册存在且可离线读、自身带八项 front-matter、
  三处地址互指、**主题表不允许指向不存在的章节**、hint/pointer 兜底、CLI 三种模式接线、`--help` 能看见手册。
- **`SKILL.md` 新增「4a. 不会做就查手册（硬性提醒）」**：给出「什么情况 → 查哪一节」的对照表，
  并写明**不要凭印象回答手册里写清楚的事**（4a 节 342 行 / 17.8 KB，仍在 400 行上限内）。

### 仓库与手册地址写入全仓 front-matter

- front-matter 的标准尾部两项改为**真实地址**（原为「待发布」）：
  `开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect` ·
  `操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd`。
  **这就是「手册能被技能调用」的机制**：读到本仓任一 `.md` 的 front-matter 即可拿到仓库与手册地址。
- 地址**唯一来源**收敛到 `paths.py`（`REPO_URL` / `MANUAL_CN_URL` / `MANUAL_NOTION_URL`），
  `registry.FRONTMATTER_TAIL`、`manual.py`、`scripts/normalize_attribution.py` 全部从那里读。
- 全部 .md 同步（61 个文件尾部字段归位）。

### README 对齐参考仓库 `omniailab-ai-director`

- **README 不再带 front-matter**（与参考仓库一致：GitHub 首页直接以居中 HTML 头开始，
  避免首页顶部被渲染成元数据表）。`scripts/normalize_attribution.py` 新增 `NO_FRONTMATTER`
  规则并把 README 纳入，`--check` 守护。
- **章节结构按参考仓库重排**为 19 节：一句话 / 能力一览（含 30 项能力表）/ 八阶段工作流 /
  快速开始 / 逐阶段操作细则 / 门禁后置动作 / 模型口径速查 / **避坑总表 25 条** / 目录结构 /
  交付物清单 / 常见问题 / 推荐工具与模型 / 基础设备要求 / 品牌与创作工具独占 /
  **配套操作手册** / 文档地图 / 贡献 / 许可与法律 / 出处与致谢。
- **表格统一为参考仓库写法**：分隔行一律 `|---|---|`（不补空格），内容加长以保证在 GitHub 上
  撑满宽度；中英两份 19 节标题、18 张表、列数与代码块**逐项对齐**。
- 徽章链接到本仓库；新增"操作手册（飞书）"徽章；表格里的"开源仓库"改为真实链接。
- `README_EN.md` 结尾署名改为英文形式（与参考仓库的英文 README 一致）。

### 新增登记：自有 URL

- `brand_policy.OWN_URLS` + `compliance_audit.OWN_URL_PREFIXES`（单一来源）登记本产品自有的
  仓库与手册地址；它们与自有站点同等对待，**不再被当成"外部推广链接"**
  （涉及 `external-url` 与 `implicit-endpoint` 两条规则）。
- `brand_policy.HOST_ALLOWED_FILES` 纳入 `docs/MANUAL.md`（手册本来就登记运行环境宿主）。

### 修掉的两处测试自伤

1. `test_user_facing_files_carry_no_external_promotion` 与
   `test_knowledge_is_self_contained_and_carries_the_signature` 会因 front-matter 里
   强制要求的自有地址而失败 → 前者放行已登记的 `OWN_URL_PREFIXES`，
   后者**改判正文**（front-matter 尾部是仓库统一格式要求，不属于"引用外部资料"），原意不变。

### 验证

- `run_tests.py`：**249 passed / 0 failed**（16 个模块，238 → 249）
- `verify_all.py`：六段全通过（内容自检 **0**；策略 **0** 禁止项 / **0** 待审）
- `normalize_attribution.py --check`：145 个文件 **0** 处不一致
- 飞书手册：15 章 / 避坑 25 条 / 能力 30 行 / 全部表格与署名写入成功
- Notion 手册：15 章 / 29 张表 / 同上

## v1.3.0 · 后续补充 — 文件格式统一、包名与结构整理

版本号仍为 **1.3.0**（全仓统一，不新开小版本）。

### 统一开头与结尾格式

- 新增 **`scripts/normalize_attribution.py`**：幂等统一化工具（`--check` / `--json`）。
  - **Markdown**：YAML front-matter = **文件类型专属字段在前 + 标准尾部在后**
    （`version` / `author` / `developer` / `agent_created` / `开源仓库` / `操作手册`），
    结尾为标准署名行；**保留 CRLF**，不重排或删除类型专属字段
    （`cases/*.md` 的 YAML 列表、`skills/*.md` 的 `capability`/`stages` 原样保留）。
  - **Python**：署名收进模块 docstring 末尾（**shebang 必须留在第 1 行**）。
  - **YAML / CMD / TXT**：头部注释 + 结尾注释。
  - **JSON**：用标准 `$comment` 字段（JSON 无注释语法）。
- 补齐 5 个缺 front-matter 的文件（`README.md` / `README_EN.md` / `providers/README.md`
  及两份自动生成的报告）与 2 个缺尾部字段的许可证登记文件。
- **版本号统一为 1.3.0**：原先 `1.0.0 / 1.1.0 / 1.2.0 / 1.3.0` 混用，现统一，
  并由 `paths.project_version()` 从 `VERSION` 读取，不再两处手写。
- **生成器同步**：`registry.frontmatter_block()` 统一构造；`compliance_audit` /
  `brand_policy` 的报告头部由生成器产出，`installer/manifest.json` 也带署名，
  格式不会再漂移。
- 新增 **6 项守卫测试**：格式一致性、幂等性、尾部字段统一、生成报告头尾、
  Python 署名齐全、shebang 仍在第 1 行。
- `projects/` 不参与统一：统一空间模型 schema 不接受多余字段，且那是用户项目数据。

### 包名与结构整理

- **Python 包 `omniailab_ai_architect/` → `omniarchitect/`**。
  原因：原包名与项目根目录 `omniailab-ai-architect` 仅差一个连字符，看起来像重复目录。
  现在二者刻意区分：**对外用产品名 `omniailab-ai-architect`（Skill 调用名，含连字符）**，
  **代码用内部引擎代号 `omniarchitect`（合法可导入标识符）**。
  427 处引用全部同步（导入、脚本、测试、打包、文档、清单）。
- **删除 `projects/_pre-rename-copy/`**：与 `projects/demo-120/` 是同一个项目
  （`project_id` 相同、README 逐字节相同），是 v1.1 改名时留下的 **revision 1 旧快照**
  （10 KB，现行 r2 为 73 KB）。除生成的清单外无人引用；删除前已在 git 中留档
  （blob `0ae0d3c9…` / `ca0e864c…`），可随时取回，也能用 `demo` 重新生成。

### 修掉的两个真实误报

1. **sha256 摘要被当成手机号**：`installer/manifest.json` 里的
   `797f14446326125d` 命中 `cn_phone` 规则。手机号 / 身份证号正则改为要求两端为
   **非十六进制字符**，并能继续识别真实号码。
2. **扫描器自我循环**：`docs/content-audit.json` 记录过一次命中，
   下一轮扫描又把它当新命中写回去，永远归零不了。新增 `SELF_OUTPUT` 豁免：
   扫描器自身的机器可读产出归入 `generated-ok`，不参与内容规则。
   两项都有回归测试。

### 验证

- `run_tests.py`：**238 passed / 0 failed**（15 模块，235 → 238）
- `verify_all.py`：六段全通过（内容自检 **0** 待处理；策略 **0** 禁止项）
- `scenario --name all`：**3/3 通过**；`policy`：**0** 禁止项

## v1.3.0 — 品牌统一、第三方来源合规隔离、OmniAiLab 创作工具独占

**本轮最高优先级约束：对外品牌统一为 OmniAiLab；第三方内容只作技术参考并集中登记许可证；
AI Agent 工作流 / AI 生图 / AI 视频只能经 OmniAiLab，不可用时明确失败 + 生成待执行任务，
不得出现任何未授权第三方商业创作平台的隐藏调用、默认回退、推广链接或广告。**

这一轮不只是写规范文件，规则落到了**代码与测试**里：独占规则由 provider 层的运行时裁决执行，
任何"改道"都会在调用点抛异常而不是悄悄发生。

### 新增

- **策略模块 `omniarchitect/brand_policy.py`**：`brand-and-provider-policy`。
  **登记制（allowlist）而非关键词黑名单**，九条检测规则与用户要求逐条对应：
  1. `brand-text` 品牌文字扫描；2. `external-url` 未授权外部 URL 检测；
  3. `unregistered-vendor` 未登记模型供应商检测；4. `implicit-endpoint` 隐式 API endpoint 检测；
  5. `external-creative-call` 图片 / 视频外部调用检测；6. `third-party-credential` 第三方凭据检测；
  7. `illegal-fallback` 非法默认 fallback 检测；8. `user-facing-content` PPT / README / SKILL
  用户展示内容扫描（含宿主语境检查）；9. `licence-completeness` 第三方许可证完整性检查。
  命中分为四类：**合规必要**（许可证 / 版权 / 来源 / 署名，**必须保留**）、
  **已授权依赖**（已登记的本地工具 / MCP / 依赖 / 宿主）、**需人工审查**、**禁止项**。
  报告只把后两类计入待处理——**不会把许可证信息误删**。
- **登记表**：自有站点与规范命名空间主机表、许可证登记专用主机表、已核实的内部模型路由
  （`omniailab.canvas`：OmniP / image2.5，明确"不宣称模型由 OmniAiLab 自研"）、
  本地专业工具（dxf / mesh / blender / freecad / ifc / render）、本地 MCP
  （blender / freecad / autocad / ifcopenshell，登记用途与数据流向）、
  运行环境宿主（Codex / Claude / Cursor / WorkBuddy，仅在宿主语境中出现）、
  经批准的依赖（含 SPDX 标识、版权持有方、官方来源、用途与降级路径）。
- **创作能力域独占（执行侧）**：
  - 能力域一分为二：**生成式创作域**（`image_generation` / `image_editing` /
    `reference_image_generation` / `multi_view_visualization` / `video_generation` /
    `architectural_walkthrough` / `visual_workflow_execution`）与
    **自有确定性域**（`schematic_diagram` / `media_asset_management`）。
  - 生成式创作域**只有 OmniAiLab** 可以承担，三处强制：
    `ProviderCapability.__post_init__`（声明层）、`MediaProvider.__init_subclass__`（类定义层）、
    `ProviderRegistry.add / select / generate` 与 `MediaProvider.run`（调用层）。
  - `ProviderRegistry.generate()` 在创作能力域不可用时**抛明确错误并生成待执行任务**
    （`status = awaiting_platform`、`owner_required = omniailab`），报告里写明
    `third_party_fallback = forbidden`；**不静默改道**。
  - `prefer=` 参数不能绕开独占规则（`select(scope, prefer='其他')` 直接抛 `PolicyViolation`）。
- **自有栅格化与 AI 生图彻底分开**：本地确定性 provider 改为只声明
  `schematic_diagram` / `media_asset_management`，不再声明 `image_generation`——
  自有矢量栅格化不得冒称 AI 效果图，也不得成为生成式能力的隐式替代。
- **`THIRD_PARTY_NOTICES.md` + `LICENSES/`**：第三方许可证、版权声明、来源链接与署名的
  **唯一**集中落点；明确本仓不打包、不分发任何第三方源码或二进制，未随本仓分发的宿主软件
  单独列表，并写明"禁止删除法律要求的署名，禁止冒充自主开发"。
- **CLI `policy`**：打印九条规则的命中、四类分类、已登记清单（`--allowlist`）、
  生成 `docs/BRAND_POLICY.md` 与 `docs/brand-policy.json`。
  `audit` 命令现在同时输出内容合规与品牌策略两份结论。
- **测试 `test_brand_policy.py`（41 项）**：九条规则各自的正反例；
  **模拟 OmniAiLab 不可用**验证创作能力域无人可做、必须抛错、留下待执行任务、
  且不存在第三个可选 provider；并验证 allowlist 的形状、许可证登记完整性、
  以及"合规必要项不计入待处理"。

### 变更

- `providers/base.py`：新增 `schematic_diagram` 能力域、`GENERATIVE_SCOPES`、`PROVIDER_KINDS`；
  `ProviderCapability` 增 `provider_kind` / `generative`，并在构造时拒绝非原生平台声明创作能力域。
- `providers/omniailab.py`：声明 `generative = True`；`submit()` 前执行
  `assert_scope_route()`；未配置时的提示改为"只生成待执行任务包，不改道第三方"。
- `providers/__init__.py`：`add()` 拒绝未登记 provider；`for_scope()` / `select()` 按策略过滤；
  新增 `creative_backends()` / `diagram_backends()` / `defer_creative_task()`；
  报告新增 `creative_policy` 与 `deferred_tasks`。
- `adapters/render.py`：创作后端改问 `creative_backends()`（只可能是 omniailab）；
  离线时明确"任务被延后而非改道"；新增 `_diagram_backends()` 暴露自有示意图后端。
- `tools/registry.py`：`render_ai` 描述改为"调用 OmniAiLab 生成式能力（唯一被授权主体）"；
  `render_local` 改为"自有确定性栅格化示意图"；限制条目写明禁止改道第三方平台。
- `compliance_audit.py`：许可证白名单加入 `THIRD_PARTY_NOTICES.md` / `LICENSES/` /
  `docs/BRAND_POLICY.md` / `docs/brand-policy.json`；`brand_policy.py` 列为内容规则豁免（扫描器自身）。
- 版本 1.2.0 → **1.3.0**；`verify_all.py` 必需文件清单与第六段新增品牌策略与独占性检查。

### 验证

- `scripts/run_tests.py`：**226 passed / 0 failed**（15 个模块，含新增 41 项策略测试与扩展后的 provider 测试）。
- `scripts/verify_all.py`：目录完整、目录自检、工具链、八阶段闭环、测试全绿、
  v1.1+ 子系统（内容自检 **0** 待处理；策略审计 **0** 禁止项 / **0** 待审；创作独占离线不外溢）。
- `python -m omniarchitect scenario --name all`：**3/3 通过**（降级与跳过项按规则如实记录）。
- `python -m omniarchitect audit`：**0** 项待处理；
  `python -m omniarchitect policy`：**0** 禁止项。

## v1.2.0 — 平面确认后的概念效果图（OmniAiLab 画布）

**新增能力：平面方案通过门禁 G3 之后，立即以该平面为依据生成概念效果图，交给业主建立空间感受。**

### 新增

- **能力 `concept-visualization`（概念效果图）**：参与 S3 / S4，能力总数 29 → **30**。
- **门禁后置动作机制**：`stages.py: POST_GATE_ACTIONS = {"G3": ["concept-visualization"]}`。
  后置动作没有自己的门禁、不能单独确认，只在所在门禁通过的那一刻执行；
  门禁被打回时，其记录会被清除。新增铁律 **R5**：概念效果图只能在业主确认的平面上生成。
- **画布工作流** `providers/canvas.py`：
  - 机位规划取自统一空间模型（整户型 1 张 + 主要空间各 1 张，视高 / 镜头 / 光线 / 材料均来自模型）；
  - 提示词由模型数据组装，携带项目标识、修订号与方案号，并计算**提示词指纹**用于跨轮追踪；
  - 参考图为**已确认平面**的本地栅格化输出（与 DXF 共用绘图基元，图与图纸不会互相矛盾）；
  - 提交走 provider 编排：提交 → 轮询 → 取回，带**有界重试**；属 **L3 联网**操作，未授权时停在授权点；
  - 产出 `canvas-jobs.json` / `canvas-payload.json` / `canvas-brief.md` / `RUN-STATUS.md` / `models.json`
    / `reference/*.png`，平台已连接时另有 `renders/*.png` 与逐机位资产版本关联。
- **模型声明** `providers/omniailab.models.json`：推荐 **OmniP**（整体空间氛围、多机位一致）与
  **image2.5**（跟随已确认平面、材质细节），含取向规则与优先级；
  与平台契约的 `models` 交叉校验，冲突时**以契约为准**并记录偏差，不硬套平台不提供的模型。
- **契约模板** `providers/omniailab.api.example.json` + `providers/README.md`：
  含 `FILL_ME` 占位符的模板会被识别并**拒绝**——模板不等于可用契约。
- **汇报类型 `concept-rendering`**：逐机位一页（图 / 模型 / 状态 / 提示词指纹），
  页面内容读自 `canvas-jobs.json`，因此幻灯片不会描述一个从未被规划的机位；
  未生成的机位展示参考图并写明状态，**不用替代图充数**。
- **知识域** `ai-concept-visualization`（AI 概念表现方法论）：知识库 12 → **13** 个领域。
- **Schema** `schemas/concept-render.schema.json`。
- **CLI**：`concept-render`、`canvas-models` 两个命令。
- **文档** `docs/CONCEPT_RENDER.md`；README 中英双版、SKILL.md、AGENTS.md、WORKFLOW、ARCHITECTURE、
  OMNIAILAB_INTEGRATION、PRESENTATION 同步更新。
- **运行报告**新增「门禁后置动作」小节：门禁通过后做了什么、产在哪，直接出现在 `run-report.md`。
- **验收**：Scenario A 增加 6 项概念效果图检查（任务包存在 / 可解析 / 机位指向已确认平面 /
  逐张可追溯 / 模型按声明选择 / 状态口径未混淆且未伪造图像 + 汇报 PPTX 独立复核）。
- **测试** 164 → **181** 项（新增 `test_concept_render.py`，14 个模块）。

### 设计取舍

- **不做成第九个阶段**：概念效果图的成立条件完全由 G3 决定。做成独立阶段会诱导使用者
  "单独确认"这一步，从而绕过平面确认——那正是最贵的错误。
- **在 fork 上渲染**：G3 确认的是方案，方案在 S4 才安装为深化依据。因此门禁后置动作
  不改写统一空间模型，项目修订号也不会因为"确认了一下"而跳动。
- **不写占位图**：平台未连接时逐张标 `awaiting_platform`，状态与产出严格对应
  （有 `generated` 才有图），由验收脚本当作硬口径检查。


## v1.1.0 修订 — 内容自有化与署名规范

**全仓完成内容自有化**：移除全部外部项目痕迹，全部文档与交付物统一 OmniAiLab 署名格式。

### 移除

- 删除上游参考仓库的本地副本（可再生、未纳入本仓库历史）与全部相关声明文件；
  本仓库不再保留、不再分发任何外部项目内容。
- 代码与文档中的外部项目名、作者名、仓库地址、商业推广链接**全部清除**：
  `registry.py`、`workflow.py`、`stages.py`、`paths.py`、`changes.py`、`cli.py`、`docs/`、`AGENTS.md`、`.gitignore`、`pyproject.toml`。
- `python -m omniarchitect fusion` / `notices` 两个命令移除，改为 `criteria`（设计判据体系）。

### 新增

- **统一署名**：`registry.py: SIGNATURE`（长）/ `SIGNATURE_SHORT` / `SIGNATURE_SHORT_EN` 三个常量，
  51 份 Markdown 全部加上标准 front-matter（`author: OmniAiLab` / `developer: Mochiball` / `agent_created: true`）与末尾署名行；
  自动生成的阶段文档、汇报 Markdown 与交付包 README 同样带署名。
- **中英双语 README**：`README.md`（简体中文，主推中国站）+ `README_EN.md`（English，主推海外站），
  排版与格式对齐 OmniAiLab 产品线：居中标题 / 徽章 / 语言切换 / 一句话 / 能力一览 / 快速开始 / 文档地图 / 出处与致谢 / 页脚署名。
- `LICENSE`（MIT，© OmniAiLab / Mochiball）与 `VERSION`（1.1.0）。
- `docs/DESIGN_CRITERIA.md`：九组设计判据的正式说明（自有口径，源自通用设计原理与公开工程惯例）。

### 变更

- `ARCH_ATTRIBUTION` / `ARCH_FUSION` → `PROJECT_ATTRIBUTION` / `DESIGN_CRITERIA`（键名与内容全部自有化）。
- `compliance_audit.py` 从"第三方内容审计"改为**内容合规自检**：署名是否齐全 / 是否泄露个人信息 /
  用户面是否有外部链接 / 许可证文本是否只在 `LICENSE` 内；报告改为 `docs/CONTENT_AUDIT.md`。
- 新增源码级守卫测试：`test_every_document_carries_the_omniailab_signature`、
  `test_no_borrowed_branding_anywhere_in_the_tree`（全仓扫描，命中即失败）。
- 既有的 65 项与新增的 99 项测试**全部保留并通过**（164 项 / 13 个模块，零失败）。

## v1.1.0 — OmniAiLab 集成、原创化与交付能力

自 v1.0.0（八阶段工作流）增量开发，**未重建项目、未覆盖既有成果、既有测试全部保留并通过**。

### 目录与命名

- 项目根目录 `omniarchitect/` → **`omniailab-ai-architect/`**（同时是 Agent Skill 根）。
- Python 包改为根目录下的子目录 `omniarchitect/`（根目录名含连字符，不可直接导入）。
- 父目录遗留的 `out/`、`projects/` 已安全归并进项目，**未删除任何内容**。

### 新增

| 子系统 | 内容 |
|---|---|
| 内容合规 | `compliance_audit.py` 可执行扫描器（署名 / 隐私 / 外链 / 许可四类判定）、`docs/CONTENT_AUDIT.md` |
| 原创知识库 | `knowledge/` 12 个领域（约 2 480 行，全部原创）+ `INDEX.md` + 渐进式加载器；`cases/` 3 个通用案例模板；`schemas/case.schema.json` |
| 平台 provider | `providers/`：OmniAiLab 发现式适配器（SDK / 配置 / API 契约）+ 本地确定性 provider；能力发现、模型选择、任务提交、状态轮询、媒体取回、失败重试、成本估算、资产版本关联 |
| 工具执行 | `tools/`：统一工具注册表、L1–L4 权限分级、危险操作确认、产物独立校验、能力真实性规则；`schemas/tool-capability.schema.json` |
| 设计汇报 | `presentation/` + `skills/design-presentation.md` + `schemas/presentation.schema.json`：9 种汇报类型 → 可编辑 PPTX / Markdown / HTML / PDF |
| 独立运行 | `integration/`：Agent Skills 契约校验、运行环境探测、只移不删的安装器；`installer/`、`compatibility/` |
| 验收 | `scenarios.py`：Scenario A/B/C 端到端验收 + 验收报告；`scripts/verify_all.py` 增加 v1.1 子系统检查 |
| 命令 | `audit` `notices` `providers` `tools` `honesty` `knowledge` `present` `scenario` `compat` `install` `uninstall` `manifest` |

### 变更

- `SKILL.md` 重写为渐进式加载入口（241 行 / 11.4 KB，细节下沉到 `knowledge/`、`docs/`）。
- 能力目录 28 → **29 项**：新增跨阶段能力 `design-presentation`（S2–S8）。
- 用户面材料（`SKILL.md`、`README.md`、`skills/`、`knowledge/`、`cases/`、汇报模板）**不再出现第三方品牌名与推广链接**；
  全部文档与交付物统一署名（`registry.py: SIGNATURE`）。
- `render` 适配器改为向 provider 注册表查询可用后端，不再硬编码空列表。
- stage S2 的概念文档与意向板增加「项目 + 模型修订 + 生成时间」页脚，使汇报可追溯到同一修订。
- 工作流阶段 B 的验收不再跳过 S6 门禁（S7 必须在其确认后进行）。

### 修正

- `ezdxf.recover` 子模块需显式导入（此前在装了 ezdxf 的机器上会失败）。
- DXF 校验器现在同时支持 R12 与 R2007+ 方言，并按内容判定 `.dwg`（改名不等于 DWG）。
- DXF 读取容忍 UTF-8 方言，中文标注不再被解成 `?`。
- 知识库 front-matter 解析支持块状列表（此前 `review_results` 等字段会被读成空）。
- `knowledge.resolve()` 的阶段加权只放大已有命中，不再制造命中（原先回退逻辑永不触发）。
- 安装器 `--target` 语义明确为「运行时技能根」，避免误把技能根当作技能目录覆盖。
- 审计器区分「署名义务」「商业推广」「个人/客户信息」「测试夹具」，不再互相污染。

### 测试

`65 → 164` 项，13 个测试模块。新增：provider、tools、presentation、knowledge、integration（含审计与安装）、scenarios。

```bash
python scripts/run_tests.py        # 164 passed
python scripts/verify_all.py       # 目录 + 目录自检 + 工具链 + 闭环 + 测试 + v1.1 子系统
```

### 已知未完成

- **OmniAiLab provider 未连接**：本机未检测到官方 SDK、本地配置或平台下发的 API 契约，状态为
  `NOT_CONFIGURED`。接入方式与所需字段见 `docs/OMNIAILAB_INTEGRATION.md`。
- **Blender / FreeCAD / IfcOpenShell 未安装**：输出可执行的生成脚本与投影数据，阶段标 `degraded`。
- **写实效果图不可用**：表现任务包已生成；图像生成待平台接入，验收中记为**跳过**而非通过。
- **PDF 导出**需本机有 LibreOffice；否则降级为打印就绪 HTML，**不伪造 PDF**。

## v1.0.0 — 八阶段专业工作流

- 八阶段业务模型（S1–S8）+ 人工确认门禁 G1–G8。
- 28 项岗位能力，与阶段多对多映射；原 18 份说明书全部保留并注入阶段字段。
- Canonical Spatial Model 作为唯一几何权威；几何变更触发下游失效重算。
- 设计变更影响分析（诊断 → 影响面 → 回流 → 门禁重开）。
- 真实执行层：内置 DXF R12 写出器 + ezdxf R2010、OBJ/MTL 网格、Blender/FreeCAD 脚本、IFC 投影。
- 四条硬性专业逻辑（R1–R4）落为带测试的约束。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
