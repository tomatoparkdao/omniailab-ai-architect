<h1 align="center">OmniAiLab AI 建筑与室内设计总设计师</h1>

<p align="center">
  <b>建筑 / 室内 / 景观全流程 AI 总设计师 Skill —— 先问清楚、再推敲、该说不就说不</b><br>
  三大专业并列主导　｜　36 类项目 / 575 个子类，先分类再设计　｜　8 阶段 × 31 项能力 × 47 种风格<br>
  任务书 → 概念推敲与专业图解 → 平面比选 → 初步设计 → 施工图深度 DXF → 物料清单与交付<br>
  概念效果图须 G3 确认后才出，且只走 OmniAiLab　｜　零硬依赖可离线　｜　结构 / 消防 / 无障碍不作结论
</p>

<p align="center">
  <a href="https://github.com/tomatoparkdao/omniailab-ai-architect"><img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-1.15.0-1f6feb?style=flat-square" alt="版本 1.15.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF-MIT-2ea043?style=flat-square" alt="许可 MIT"></a>
  <a href="https://www.omniailabx.com/"><img src="https://img.shields.io/badge/%E5%B9%B3%E5%8F%B0-OmniAiLab-8957e5?style=flat-square" alt="平台 OmniAiLab"></a>
  <img src="https://img.shields.io/badge/%E9%A2%86%E5%9F%9F-%E5%BB%BA%E7%AD%91_%7C_%E5%AE%A4%E5%86%85_%7C_%E6%99%AF%E8%A7%82-0e8a16?style=flat-square" alt="领域 建筑 | 室内 | 景观">
  <img src="https://img.shields.io/badge/%E6%B5%81%E7%A8%8B-8_%E9%98%B6%E6%AE%B5_%C3%97_31_%E8%83%BD%E5%8A%9B-0969da?style=flat-square" alt="8 阶段 × 31 能力">
  <img src="https://img.shields.io/badge/%E4%BA%A4%E4%BB%98-%E6%96%B9%E6%A1%88_%7C_%E6%96%BD%E5%B7%A5%E5%9B%BE-1d76db?style=flat-square" alt="交付 方案 | 施工图">
  <img src="https://img.shields.io/badge/%E5%85%BC%E5%AE%B9-Codex_%7C_Claude_%7C_Cursor_%7C_WorkBuddy-6f42c1?style=flat-square" alt="兼容 Codex / Claude / Cursor / WorkBuddy">
</p>

<p align="center">
  <b>简体中文</b>　｜　<a href="README_EN.md">English</a>
</p>

> © OmniAiLab ｜ 开发者：Mochiball ｜ 平台：[omniailabx.com](https://www.omniailabx.com/)

不止于生成效果图，而是让 AI 真正参与建筑与室内设计的全过程。**它不只执行流程——开工第一件事是问清功能、场地与预算**，再按主导专业决定推敲顺序：建筑先定体量与剖面，室内先定空间重组与界面，景观先定分区与游线；然后按阶段推进到可交付的图纸、模型与物料清单，你在每个阶段末尾只需回答"确认"或"要改哪里"。一个 Skill 覆盖 8 大设计阶段、31 项专业能力与 47 种设计风格，并通过 OmniAiLab AI 创作平台与专业 MCP 工具协同，让 AI 从设计建议走向真实的设计执行。

| 项目 | 值 | 说明 |
|---|---|---|
| 项目分类 | 36 类 / 575 子类 | 建筑 15 类、室内 12 类、景观 9 类；用途可多选，另有项目性质与委托范围两个独立维度（`docs/PROJECT_TAXONOMY.md`） |
| Skill 调用名（唯一标识） | `omniailab-ai-architect` | 全小写连字符写法；支持 skill 的工具直接用它调起，不支持的工具用自然语言描述也能触发 |
| 显示名 | OmniAiLab AI 建筑与室内设计总设计师 | 仓库页面与文档里显示的名字，不是调用名 |
| 版本 | v1.15.0 | 与 `VERSION`、`pyproject.toml`、`SKILL.md`、`installer/manifest.json`、`openai.yaml` 及两份 README 保持一致 |
| 出品 / 开发者 | OmniAiLab ／ Mochiball | — |
| 许可 | MIT（见 [LICENSE](LICENSE)） | 使用与二次分发以该文件为准 |
| 配套操作手册 | [飞书](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) ／ [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) ／ `docs/MANUAL.md` | 如何调用、三步启动、逐阶段操作细则、能力速查、避坑总表、常见问题、交付物清单 |
| 仓库 | [tomatoparkdao/omniailab-ai-architect](https://github.com/tomatoparkdao/omniailab-ai-architect) | 全部源码、文档与验收脚本；**当前为私有仓库**，公开后可直接 `git clone` 与提 issue |
| 运行要求 | Python 3.10+ | 零硬依赖：DXF、网格、PPTX 都有内置写出器 |
| 原生平台 | [OmniAiLab 中国站](https://www.omniailabx.com/) ／ [海外站](https://omniailab.cn/) | 生成式图像与视频能力来自平台；**未接入时系统照常运行** |

调用名是**全小写连字符**写法（`omniailab-ai-architect`），不是「OmniAiLab AI 建筑与室内设计总设计师」这个显示名。支持 skill 的工具直接用调用名最稳；不支持原生 skill 的工具，用自然语言描述设计任务也能触发。

> **名字里的一个坑**：仓库根目录叫 `omniailab-ai-architect`（含连字符，这是 Skill 名），
> 里面的 Python 包叫 `omniarchitect`（内部引擎代号，可导入）。**两者不是重复目录**——
> 根目录是 Skill 载荷（`SKILL.md` / `knowledge/` / `skills/` / `docs/`），包目录是全部可执行代码。


---

## 先判断"这是什么项目"，再谈怎么设计

同一句"做个酒店"，可以是新建一栋酒店，也可以只是既有酒店的室内精装——两者的专业、
流程与成果完全不同。所以 S1 不再只问面积与房间数，而是先落三件事：

- **用途**（可多选）：A 建筑 15 类 / B 室内 12 类 / C 景观 9 类，共 575 个子类；
- **项目性质**：新建、改扩建、既有室内装修、独立景观、功能转换、历史保护；
- **委托范围**：建筑、室内、景观里到底委托了哪几块——**名称不等于委托**。

分类决定后面两件事：S2 用哪套设计方法推敲（医院按医疗工艺与洁污分流、学校按分龄与
教学组团、厂房按工艺流线），S3 列哪些专业任务（科室面积表、客房模数、汇水分区……）。
能力边界随类型写明：住宅能算到房间级，医院只能给概念与任务梳理，厂房必须由工艺专业给条件。

```bash
python -m omniarchitect taxonomy                      # 36 类索引
python -m omniarchitect taxonomy --show A4            # 医院：要点 / 方向 / S3 任务
python -m omniarchitect taxonomy --detect "既有酒店室内精装修"
```


## 一句话

把一条需求（哪怕只是一张户型图加一句"想做成意式极简"）交给它，它会先问清功能与预算，再按阶段推进到可交付的图纸、模型与物料清单；你在每个阶段末尾只需回答"确认"或"要改哪里"。

**它不说"这套方案更现代"，它说"从这里进门你会先看到一堵墙，向左三步才亮起来"**——S2 给出的每一套方向，都带一段可核验的空间经历，以及对你那句话的正面回应。

| 适用范围 | 具体是什么 |
|---|---|
| **适用 · 项目类型不限** | 住宅公寓、大平层、别墅，办公、商业、餐饮、酒店、展厅；方案阶段与深化阶段都在范围内。**建筑、室内、景观三类都可以做主专业**：新建项目由建筑统筹、既有空间只做室内、独立庭院只做景观，主导专业决定推敲顺序；不属于主导的专业只做**界面协调**（设备位置、照明接线、退界与接口材质） |
| **适用 · 深度可控** | 只要"两套平面比一比"，或要"平面 + 三维 + 效果图任务包 + 施工图深度 DXF + 物料清单 + 汇报 PPT"，用同一条管线按需取用 |
| **不适用（明确说不）** | 结构安全、消防、无障碍、机电负荷与当地法规符合性的**最终结论**不在本系统结论范围内；本系统只标注问题、给出待复核清单，须由持证专业人员在项目所在地复核签署 |

---

## 能力一览

**它不是"一个跑流程的模板"，而是一套会先问清需求、会把判断写进图纸、会把缺失能力如实说出来的设计系统。**

| 层面 | 具体有什么 |
|---|---|
| **① 阶段与能力分开** | 八个**业务阶段**决定推进节奏与门禁；31 项**岗位能力**（任务书、场地分析、概念、空间规划、人体工学、室内、材料、灯光、机电协同、CAD 制图、BIM、三维、渲染、漫游、施工深化、工程量、校核、汇报、交付……）决定专业方法。能力跨阶段复用，不会被钉死在某一步。 |
| **② 唯一几何权威** | 统一空间模型（Canonical Spatial Model）是全部成果的唯一几何来源。墙外移 300mm，系统按依赖关系重算平面、立面、天花、灯位、家具间距、工程量与图纸——**已确认且不受影响的部分保持有效**，不做无差别重跑。 |
| **③ 变更走影响分析，不走局部手改** | 任何修改先诊断（11 类变更域）→ 定位影响面（含受影响空间的边界构件）→ 给出回流阶段与门禁重开清单。改材质不会让模型失效，改尺寸会让下游全部失效，这件事由程序判断，不由人记得。 |
| **④ 判断有出处** | 九组**设计判据**：美学控制基线、概念图解语言、意向板迭代闭环、机电空间影响、批注台账、提案版式、项目适配、量价分离、工具安全分级。每条都写成可判定的句子（"暖材 ≤40%""黑 3–8%""全场只留一条主导线"），不是形容词。 |
| **⑤ 真的会出文件** | 可编辑 DXF（方案深度与施工深度分开）、OBJ 三维网格、示意图、可编辑 PPTX 提案、Markdown 与打印就绪 HTML、工程量与造价估算 JSON、变更影响报告。**写出的文件都用独立实现复核**，读不回即判失败。 |
| **⑥ 不假装做到** | 没装 Blender / FreeCAD / IfcOpenShell → 输出**可直接运行的脚本**并标 `degraded`；平台未配置 → 标 `NOT_CONFIGURED` 并列出缺什么；DXF 不会改名成 DWG，网格不会说成参数化 BIM，效果图不会当尺寸依据。 |
| **⑦ 设计风格系统** | **47 种建筑与室内设计风格**的结构化知识库（八族：现代 / 东方 / 经典 / 装饰复古 / 工业 / 自然有机 / 地域性 / 实验性），每种含 20 个专业字段（历史脉络、空间原则、比例几何、色板、材料、家具语汇、照明策略、适用空间、造价与施工注意、相容与冲突、正向提示词组、几何保持规则、负向约束、质检清单）。**索引与数据分离**：先查 `catalog.json`（179 个标签），再按需加载单条，不会把 47 条全读进上下文。附三方案推荐引擎与中英双语提示词编译器（14 种目标：8 种空间表现 + 6 种图纸派生与版面——平面图上色 / 3D 立轴 / 正投影剖面 / 三视图展示板 / 概念设计板 / 实体材质情绪板，图纸派生需 G3 且文字由排版层叠加）。 |
| **⑧ 设计能力：空间体验** | 原型说房间怎么排，风格说看起来像什么——中间那段「**人走进去经历什么**」不再空着。**11 条空间体验手法**（压缩与释放、前景与庇护、门槛与过渡、套间序列、框景、借景、节奏与重复、光的层次、材料的真实与触感、比例与层高推导、到达序列），每条都写清机制、做法、**在图上怎么核验**、以及用错了会怎样。**22 套原型各有不同的空间家族**，天然擅长的不是同一套手法，所以三套方向不会说同一句话。业主说「要敞亮、进门别一眼看穿」，S1 直接记下、S2 逐条回应：能给（`met`）、勉强（`at_risk`）、还是没提（`not_stated`）——**业主没说就不替他决定**。 |
| **⑨ 技术为实现让路** | 结构机电是**辅助专业，不是审批口**。概念提到「挑空」，它不判「不可行」，而是给 3 条实现路径：边梁抬 / 钢梁框架 / 局部悬挑——每条写清**换来什么、拿什么换、必须由谁签字核算**。8 个技术目标、24 条路径（结构：通高开洞 / 拆改承重墙 / 新增荷载 / 大跨度；机电：不吊顶的净高 / 湿区移位 / 无窗空间 / 开放厨房）。**物理上做不到的直接说做不到**（中间层开天窗、地下层要自然光），并给替代做法，不列假路径。 |

### 能力清单（31 项，按服务阶段）

| 能力 | 名称 | 服务阶段 | 说明 |
|---|---|---|---|
| `design-brief` | 设计任务书 | S1 · S6 | 把需求、预算与验收标准翻成可勾选的功能任务书与面积指标 |
| `site-analysis` | 场地与建筑条件分析 | S1 | 把建筑条件、朝向采光、动线与限制读成可核对的约束清单 |
| `existing-drawing-analysis` | 原始图纸解析 | S1 | 识别图层、墙体、尺寸与门窗，区分可置信的事实与推断，并逐条标注待现场核对项 |
| `architectural-design` | 建筑设计 | S1 · S4 | 把功能、场地与朝向组织成自洽的体量、立面和楼层策略 |
| `landscape-design` | 景观设计 | S1–S4 | 用竖向、分区、游线、水景与植物把室外空间组织成可使用的场所 |
| `concept-design` | 概念方案设计 | S2 · S3 | 把任务书翻成一句可验证的设计主张、空间原型与风格语言 |
| `moodboard-aesthetic-iteration` | 意向板与审美迭代 | S2 · S5 | 用关键词锚定审美目标，按固定框架量化打分，并跨轮追踪整改闭环；参考图分调研级与交付级 |
| `create-draw` | 概念图解与评图 | S2 · S4 · S7 | 用约定图形语义把设计判断画成一张可读的图，评图意见跨轮可核销 |
| `lighting-design` | 灯光设计 | S2 · S4 · S7 | 把自然光与人工光统一成一套策略，输出照度、色温与灯位判据 |
| `space-planning` | 空间规划 | S3 | 把任务书与概念方向翻成房间划分、面积配比与流线 |
| `layout-optimization` | 布局优化 | S3 · S6 | 对比例、进深与开放度做多方案量化比较，并说清每一种代价 |
| `ergonomics` | 人体工学与尺度 | S3 · S4 | 把「够不够、顺不顺」翻成可校核的净宽、间距与操作高度 |
| `concept-visualization` | 概念效果图 | S3 · S4（G3 门禁后置动作） | 平面确认后由 OmniAiLab 画布按机位生成，供业主对齐空间感受 |
| `interior-design` | 室内设计 | S4 · S6 | 把平面发展成顶墙地界面、天花与软硬装做法，形成可施工方案 |
| `material-design` | 材料与色彩设计 | S4 · S5 · S8 | 翻成可采购、可施工、可维护的主材表、样板与排版 |
| `building-services` | 机电与设备协同 | S4 · S6 · S7 | 把电气、给排水、暖通、消防的空间与净高需求翻成点位清单 |
| `cad-drafting` | CAD 制图 | S4 · S7 | 翻成统一制图标准的成套图纸，分方案与施工两个深度 |
| `3d-modeling` | 3D 空间建模 | S5 | 把已确认的统一空间模型翻成可编辑的三维场景与构件 |
| `scene-rendering` | 场景渲染 | S5 | 按机位、材质与光影批量出图，多视角一致，图像一律非权威 |
| `ai-visualization` | AI 视觉表现 | S5 | 经 OmniAiLab 平台生成辅助表现材料，输出一律标注非权威 |
| `walkthrough` | 漫游与多视角表现 | S5 | 把空间序列翻成全景与漫游，验证动线与观感，标注非权威；需要叙事时移交导演技能 |
| `bim-modeling` | BIM 建模 | S5 · S7 | 翻成带参数的构件与信息模型，支撑出图、算量与专业协同 |
| `design-review` | 设计审核 | S6 · S7 | 按可判定的清单逐项初筛，输出通过 / 有条件通过 / 退回 |
| `coordination-check` | 专业协调校核 | S6 · S7 | 查结构、机电、吊顶净高、点位与做法的冲突，出碰撞记录 |
| `construction-detailing` | 施工深化与节点 | S7 | 把设计意图深化到可施工的构造层次、收口与节点大样 |
| `cost-check` | 造价适配 | S1–S6 | 自 S1 起随深化动态估算，用区间口径判断是否落在预算内 |
| `quantity-takeoff` | 工程量计算 | S1–S8 | 逐阶段从统一模型滚动计量，S8 才形成与图纸一致的正式工程量清单 |
| `material-schedule` | 材料与物料表 | S8 | 出规格、用量、损耗与替代，数量与单价分列，可直接采购 |
| `documentation` | 交付文档 | S8 | 组织成带索引、边界说明与署名的归档文本，供审查与交底 |
| `delivery` | 版本管理与交付 | S8 | 用修订号追踪变更、失效重算与交付索引，完成版本冻结 |
| `design-presentation` | 设计汇报与提案 | S2–S8 | 把阶段成果转译为可决策的提案与可编辑 PPTX，每份都含免责与边界页 |

```bash
python -m omniarchitect registry     # 打印能力目录与技能→阶段完整映射
python -m omniarchitect criteria     # 设计判据体系（自有口径）
```

---

## 快速开始

> **第一次用？照这五步走就够了。** 它不会一上来就问"你的设计需求是什么"，而是按下面顺序把你需要的东西收齐。

### 一、装到哪：按你用的工具

把**整个 `omniailab-ai-architect` 文件夹**（含 `SKILL.md`、`omniarchitect/`、`knowledge/`、`cases/`、`skills/`、`schemas/`、`workflows/`、`docs/`）放进下面对应的目录，重开一个新会话即可生效。

| 工具 | 放哪里 | 怎么调起 |
|---|---|---|
| **Codex**（推荐主用） | 没有原生 skill 目录：把文件夹放进项目，例如 `<你的项目>/skills/omniailab-ai-architect/`，再在项目根目录的 `AGENTS.md` 里加一行：<br>`设计任务：先读 skills/omniailab-ai-architect/SKILL.md，并按其流程执行。` | 说"按 SKILL.md 开始做设计"。它读 `AGENTS.md` 后会加载这个 skill。 |
| **Claude / Claude Code** | 个人级：`~/.claude/skills/omniailab-ai-architect/`<br><br>项目级：`<你的项目>/.claude/skills/omniailab-ai-architect/` | 输入 **`/omniailab-ai-architect`**；或直接描述任务（如"照这份户型图走完整设计流程"），它会按描述命中并加载。 |
| **WorkBuddy** | 用户级（全局可用）：`~/.workbuddy/skills/omniailab-ai-architect/`<br><br>项目级（只在该项目可用）：`<你的项目>/.workbuddy/skills/omniailab-ai-architect/` | 新开会话后它出现在技能列表里；直接说 **`$omniailab-ai-architect 开始`**。 |
| **OmniAiLab**（omniailabx） | [官网下载](https://www.omniailabx.com/)（版本以官网为准）；安装后把整个文件夹放进它的 **技能目录**（客户端内可查看技能目录位置） | 新开会话后它出现在技能列表里；直接说 **`$omniailab-ai-architect 开始`**。 |
| **其他 Agent Skills 宿主** | 按宿主约定，例如 `<你的项目>/.agent/skills/omniailab-ai-architect/`；Cursor 用 `~/.cursor/skills-cursor/omniailab-ai-architect/` | 在对话里描述设计任务；详见 [compatibility/agent-skills.md](compatibility/agent-skills.md)。 |

> **必须整个文件夹一起复制，不能只拷 SKILL.md。** 31 项能力说明在 `skills/`、15 个知识域在 `knowledge/`、判据在 [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md)、操作手册在 [docs/MANUAL.md](docs/MANUAL.md)、模板在 `schemas/` 与 `workflows/`、可执行代码在 `omniarchitect/`；少拷一个目录，运行时就会断链。

**克隆安装（推荐）**

```bash
git clone https://github.com/tomatoparkdao/omniailab-ai-architect.git \
  ~/.workbuddy/skills/omniailab-ai-architect
```

> 本仓库是**私密仓库**：克隆时需要 GitHub 授权（HTTPS 用访问令牌，或改用 SSH）。以后更新只需在该目录执行 `git pull`。发现问题也可以在仓库里提 issue。

本仓库自带安装器，可自动探测运行环境（**不需要注册 OmniAiLab，也不会读取任何平台密钥**）：

```bash
python installer/install.py --dry-run          # 先看会发生什么
python installer/install.py                    # 指针安装到已探测到的环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

> 安装与卸载**都不删除内容**：目标已存在时先移动到 `_backup/`。

### 二、资料从哪来（三选一）

1. **你直接上传原始图纸 / 设计任务书** —— 它读取后按 `existing-drawing-analysis` 解析，直接进入 S1。
2. **什么都不给，直接说"开始"** —— 它会先问四件事（项目类型 / 功能需求 / 预算口径与交付深度 / 手上有哪些资料），**不会自动编一套需求**；只有你明确说"跑示例项目"时，才用内置的 120㎡ 住宅示例。
3. **只给一句话需求**（例如"120㎡ 三居，想要现代意式极简，预算 30 万"）—— 它先整理成一版可确认的设计任务书给你确认，确认后才进 S1。

> **还有一句话，值得你认真答**：它一定会问「如果用一句话形容推开门那一刻想要的感受，你会怎么说？」。
> 这道题**故意不给选项**——选项会把你的答案框成它预设的几种。这一句换来的，是 S2 全部审美方向的依据：
> 说「敞亮、要显大」，它就往借景与光的层次上做；说「进门别一眼看穿」，它就往门槛与过渡上做。
> **你第一句话里已经说了，它就直接记下，不再问第二遍。**

### 三、启动指令

```text
$omniailab-ai-architect 开始
```

直接说"开始"即可，它**不会**反问"请问你的需求是什么"，而是直接问：项目类型、功能需求、预算口径、手上有哪些资料。

用命令行方式也可以（全在本机跑，不需要平台、不需要密钥）：

```bash
export PYTHONPATH=<你的路径>/omniailab-ai-architect
python -m omniarchitect doctor                 # 本机工具链体检
python -m omniarchitect stages                 # 八阶段与门禁
python -m omniarchitect demo --out out         # 示例项目跑通全部八阶段
python -m omniarchitect scenario --name all    # 验收：Scenario A/B/C
```

推进一个真实项目：

```bash
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "想做成现代意式极简，先给我两套平面方案"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniarchitect change  --project projects/demo-120 "把厨房和餐厅之间的墙往外移300mm"
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
```

`route` 会把一句话变成明确的阶段计划：跑哪些阶段、谁负责、门禁是谁、此刻哪些动作被拦下。

### 四、启动前必须想清楚的两件事

- **功能需求必须由业主确认。** R1：业主确认功能需求之前，不得开始精细建模——需求没定就建模＝白建。中途大改功能（尤其涉及房间增删）会让前面已确认的平面与下游成果全部作废。
- **目标交付深度先定好。** 只要"两套平面比一比"，还是要"平面 + 三维 + 效果图任务包 + 施工图深度 DXF + 物料清单 + 汇报 PPT"？用同一条管线按需取用，但深度要在 S1 说清——中途加深会让返工面扩大。

### 五、全程你只需要回答两种话

1. **放行到下一阶段** —— 必须是这四个词之一，其它说法它不开门：

```text
确认 / 通过 / 定稿 / 继续
```

2. **要改就指出位置** —— 它停在当前阶段就地重做，不会往下走：

```text
第 3 套平面的客厅采光面被独占了，重排一下
把主卧衣柜从 600 深改成 550 深
```

**只想用其中一项能力时**，直接点名即可，不必走全流程：

| 你想要什么 | 复制这句话直接说 | 它会给你什么 |
|---|---|---|
| 设计任务书 | `只做任务书，帮我把需求整理成可验收的任务书` | 功能任务书 + 面积指标 + 预算口径 + 验收标准 |
| 平面方案比选 | `只做平面，给我两到三套可比较的方案` | 多套平面 + 可比指标 + 面积配比 + 造价影响 |
| 人体尺度校核 | `只做尺度，帮我核一下通道和家具间距够不够` | 通道净宽 / 家具间距 / 洁具间距的数值校核清单 |
| 材料与饰面 | `只做材料，给我一套可采购可施工的材料体系` | 材料选型 + 规格排版 + 样板清单 |
| 灯光 | `只做灯光，给我照度、色温与灯位方案` | 照度标准 / 色温 / 显色 / 灯位与回路建议 |
| 概念效果图 | `只做概念效果图，平面我确认了` | 画布任务包（机位 + 提示词 + 参考图 + 回填位置）+ 逐张状态；未接平台时逐张标 `awaiting_platform` |
| CAD 图纸 | `只做图纸，出方案深度的 DXF` | 可编辑 DXF（方案深度 `schematic`）+ 独立解析复核实体数与图层 |
| 工程量与造价 | `只做工程量，算一下这套方案的量和估算` | 分空间工程量 + 量价分离估算 + 与预算的适配结论 |
| 设计汇报 | `只做汇报，把这个阶段的成果做成提案` | 可编辑 PPTX（含免责与边界页）+ Markdown + HTML |

> **给的信息越具体，返工越少。** 最有效的三样：① 原始图纸或现场实测尺寸；② 功能需求与使用人数；③ 预算口径与硬性限制（不能出现什么、必须出现什么）。这三样在第一步就给它，比后面补要省得多。

---

## 全流程总览

| 阶段 | 名称 | 阶段产出 | 门禁 |
|---|---|---|---|
| S1 | 项目启动与设计任务书 | 功能任务书（可勾选）、原始条件报告、面积指标与预算口径 | G1 任务书确认（业主 / 主创） |
| S2 | 概念方案设计 | 概念方案（设计主张与空间原型）、风格意向板（含材料与色调倾向） | G2 概念方案确认（业主 / 主创） |
| S3 | 平面方案设计 | 两至三套平面方案、方案对比分析（面积 / 动线 / 造价影响） | G3 平面方案确认（业主 / 主创） |
| S3·后 | **概念效果图**（G3 门禁后置动作） | AI 概念效果图、画布任务包、逐机位状态、概念效果图汇报 | 附属于 G3（无独立门禁） |
| S4 | 初步设计与方案深化 | 初步设计图纸（方案深度 CAD）、材料与灯光方案、机电协调结论 | G4 初步设计确认（业主 / 主创） |
| S5 | 三维建模与效果图表现 | 可编辑 3D 模型、多视角一致的空间效果图、漫游与全景 | G5 表现成果确认（业主 / 主创） |
| S6 | 设计定稿与技术协调 | 确认版设计方案、锁定版本与待办清单、变更影响规则 | G6 设计锁定（业主 / 主创） |
| S7 | CAD / BIM 施工图深化 | 正式深度施工图（平立剖 / 吊顶 / 铺装 / 节点大样）、BIM 模型或 IFC 投影、审查记录 | G7 施工图审查（持证专业负责人） |
| S8 | 物料清单与设计交付 | 材料表与物料清单、工程量清单与成本、全套交付文件与技术交底 | G8 交付验收（业主 / 主创） |

**八阶段是流程，31 项能力是岗位——不要混为一谈。** 一项能力可以服务多个阶段：灯光设计同时在
S2（概念灯光方向）、S4（照明方案）、S7（灯具定位）出现；设计汇报横跨 S2–S8。

### 五条不可协商的专业逻辑

| 编号 | 规则 | 为什么 |
|---|---|---|
| **R1** | 业主确认功能需求前，不得开始精细建模 | 需求没定就建模等于把返工写进预算；G1 通过前的一切模型都只是推演，不算交付成果 |
| **R2** | CAD 不是最后才画：方案深度图自 S4 起即可绘制 | 区别在 `schematic` 与 `construction` 两个深度，不在「有没有 CAD」——从 S4 起就能出图 |
| **R3** | 成本与工程量自 S1 起动态估算，S8 才形成正式清单 | 估算随阶段收敛：S1 给区间、S6 收紧、S8 才定稿，不是最后一次性拍脑袋 |
| **R4** | 平面未确认不得出正式图纸；锁定后不得局部手改，必须走 `change` | 未确认就出图是把钱画在流沙上；锁定后局部手改会让图纸、模型与工程量三份成果互相矛盾 |
| **R5** | 概念效果图只在业主确认的平面上生成 | 平面一变，已生成的整批效果图即时作废重出，绝不把旧图混进新方案 |
| **R6** | 技术可行性不是设计的前提，而是设计的结果 | 先明确要做成什么，再选实现路径。提到「挑空」不是否掉设计，而是给出三条做法与各自代价；**物理上做不到的才叫做不到**，并给替代做法 |
| **R7** | 业主没说想要什么感受，不替他决定 | `not_stated` 就是 `not_stated`。凭空推荐「温馨」是把我们的偏好伪装成他的需求 |

---

## 逐阶段操作细则

| 阶段 | 你要做的判断 | 常用能力 | 注意 |
|---|---|---|---|
| **S1** 启动与任务书 | 功能需求、面积指标、预算口径对不对得上 | 设计任务书、场地分析、图纸解析、造价适配 | 从图纸推断而非实测的数据会带 `uncertain = true`，须现场核实。**「想要什么感受」这道题值得认真答**，它是 S2 全部审美判断的输入 |
| **S2** 概念方案 | 概念方向与意向板认不认；**走进去的经历对不对** | 概念方案、意向板迭代、概念灯光方向、汇报 | 评分口径在同一项目内不会中途更换。每套方向都带「第一眼 / 转折 / 主空间 / 记住的是」四段经历与手法依据；**三套方向说的是不同的空间，不只是不同的颜色** |
| **S3** 平面方案 | **最重要的一次拍板**：选哪套平面 | 空间规划、人体工学、布局优化 | 平面四问：采光面是否被独占、流线是否穿私密区、有无真实主导线、是否留出"空的地方" |
| **S3·后** 概念效果图 | 空间感受对不对 | 概念效果图（G3 通过后自动执行） | 只能在已确认平面上生成；改平面＝整批作废 |
| **S4** 初步设计 | 做法、材料与机电协调 | 室内、建筑、材料与色彩、灯光、机电协同、CAD 制图 | R2：从这一步起就能出 CAD，是 `schematic` 深度 |
| **S5** 三维与表现 | 效果图与漫游认不认 | 3D 建模、场景渲染、AI 视觉表现、漫游、BIM | 跨视角一致靠同一份模型：机位、材质、光线全部取自统一空间模型 |
| **S6** 设计定稿 | **设计锁定**（之后不许局部手改） | 设计审核、专业协调校核、布局优化 | 任何修改都走 `change`，产出诊断、影响面与门禁重开清单 |
| **S7** 施工图深化 | 结构、消防、机电与法规由**持证人员**复核 | 施工深化与节点、CAD 制图、BIM、审核 | 本系统只做规则初筛与提示，**不出合规结论** |
| **S8** 物料与交付 | 交付内容与版本核对 | 材料与物料表、工程量、交付文档、版本管理、汇报 | 量价分离；方案估算**不构成结算依据** |

细节见操作手册与 [docs/WORKFLOW.md](docs/WORKFLOW.md)。

---

## 门禁后置动作：平面确认后的概念效果图

**它是门禁后置动作，不是独立阶段**：没有自己的门禁、不能单独确认，只在 **G3 通过的那一刻**执行；
门禁被打回时记录会被清除。

| 环节 | 说明 | 落点与依据 |
|---|---|---|
| 平台 | OmniAiLab 画布（canvas） | 凭据只存本机 `omniailab.config.json`；端点与鉴权只来自 `providers/omniailab.api.json` |
| 推荐模型 | **OmniP**（整体空间氛围、多机位一致）· **image2.5**（跟随已确认平面、材质细节） | 声明在 `omniarchitect/providers/omniailab.models.json`，与平台契约交叉校验，冲突以契约为准 |
| 机位 | 整户型 1 张 + 主要空间各 1 张；视高 / 镜头 / 光线 / 材料全部取自统一空间模型 | 机位规划由 `providers/canvas.py` 生成，不手写镜头参数 |
| 参考图 | 由本系统**自有确定性栅格化**产出（已确认平面的示意图，不是 AI 图） | 走 `schematic_diagram` 能力，标注「非写实渲染」，可离线复现 |
| 产出 | `canvas-jobs.json`、`canvas-brief.md`、`RUN-STATUS.md`、参考图、可编辑汇报 PPTX | 逐机位标 `awaiting_platform` 或生成状态；**绝不写占位图、绝不改道第三方** |

```bash
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect concept-render --project <dir> --submit --authorize   # L3 联网，需授权
python -m omniarchitect canvas-models                                         # 模型声明与选择规则
```

**三条不许越过的线**：平面未确认不得出图（依据是 G3）；平台未连接就只交付任务包，
逐张标 `awaiting_platform`，**绝不写占位图、绝不改道第三方**；提交生成属 **L3 联网**，
需要 `--submit --authorize` 显式授权，图像永远 `authoritative = false`。详见 [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md)。

---

## 模型口径速查

| 用途 | 模型 / 后端 | 说明 |
|---|---|---|
| 概念效果图 · 整体空间氛围与多机位一致 | **OmniP**（OmniAiLab 画布） | 整户型机位、公区需要读空间关系时 |
| 概念效果图 · 跟随已确认平面与材质细节 | **image2.5**（OmniAiLab 画布） | 房间机位；要求画面与已确认平面严格对齐时 |
| 平面示意图（参考图） | 自有确定性栅格化（`schematic_diagram`） | 与 DXF 共用绘图基元，图与图纸不会互相矛盾；标「非写实渲染」，不得作为施工尺寸依据 |
| 施工尺寸依据 | **不存在生成式选项** | 施工图必须由经过校核的几何 / BIM 模型生成 |

**一句话口径**：概念效果图与材质参考图只能经 OmniAiLab 平台；底层模型供应商由平台侧依法授权并路由
（已登记画布路由 `omniailab.canvas`），这是**平台服务**与**模型提供方**的区别，**不宣称模型由 OmniAiLab 自研**。

---

## 避坑总表

踩中任意一条，轻则返工一段，重则整套成果作废。

| # | 坑 | 后果 | 怎么避 |
|---|---|---|---|
| 1 | 平面没确认就往下做 | 整批概念效果图与下游全部作废 | G3 必须显式 `confirm`，判断依据是门禁不是感觉 |
| 2 | 锁定后局部手改下游文件 | 改一处坏三处，模型与图纸不一致 | 一律走 `change` 命令，让它算影响面 |
| 3 | 把 DXF 改名成 DWG | AutoCAD 拒绝打开或损坏 | DXF ≠ DWG；要 DWG 必须由具备许可的后端另存 |
| 4 | 把 AI 效果图当尺寸依据 | 施工尺寸错，现场返工 | 效果图永远只用于表现，`authoritative = false` |
| 5 | 没装 IfcOpenShell 却说出了 IFC | 交付物无法被 BIM 软件读入 | 只能说「IFC 投影数据 + 生成脚本」 |
| 6 | 把三角网格当参数化 BIM | 无构件语义，无法承载 IFC 信息 | 网格就是网格，参数化 BIM 需 IFC / 原生 BIM 后端 |
| 7 | 跳过 G7 让系统给法规结论 | 结论无效，风险落在业主 | 结构 / 消防 / 无障碍 / 负荷必须持证专业人员复核签署 |
| 8 | 从图纸推断的尺寸当实测 | 隐蔽误差带到施工 | 推断值带 `uncertain = true`，校核中作为阻断项 |
| 9 | 平面改了但概念效果图没重出 | 业主按旧图想象空间 | R5：平面一变，整批概念图作废重出 |
| 10 | 门禁打回后仍用旧的下游产物 | 新旧混用 | 门禁打回会清除后置动作记录，下游失效重算 |
| 11 | 未授权就提交平台生成 | 产生计费调用 | L3 操作必须 `--submit --authorize` |
| 12 | 平台没连上就等着出图 | 空等 | 平台缺席是**正常降级**：只交付任务包，逐张标 `awaiting_platform` |
| 13 | 让系统改道第三方生成平台 | 违反品牌与供应商策略 | 创作能力域只有 OmniAiLab；不可用时延后，不改道 |
| 14 | 说模型是 OmniAiLab 自研 | 虚假陈述 | OmniP / image2.5 是平台内已授权路由，不是自研模型 |
| 15 | 把自有示意图当 AI 效果图 | 误导业主 | 本地栅格化只声明 `schematic_diagram`，标「非写实渲染」 |
| 16 | 期望本机直接生成 PDF | 拿不到 PDF | 无 LibreOffice / soffice 时不伪造 PDF，走 HTML 打印路径 |
| 17 | 用裸 `python` 跑验证 | 缺 Pillow 导致示意图用例走降级分支而失败 | 用装了依赖的解释器：`…\python\envs\default\Scripts\python.exe` |
| 18 | 忘记跑自检就交付 | 署名 / 外链 / 隐私问题带出去 | 交付前跑 `audit` 与 `policy`，两者都必须 0 |
| 19 | 为了报告归零删掉许可证信息 | 违反许可证，法律风险 | `compliance-required` 不计入待处理，**不要删** |
| 20 | 推 GitHub 未指定代理 | git 协议被拦，`read operation timed out` | `HTTPS_PROXY=http://127.0.0.1:7890 … sync`；沙箱默认代理只放行 API |
| 21 | 令牌过期后以为是代码坏了 | 白排查 | PAT 有有效期，到期重新授权一次即可 |
| 22 | 改了版本号但没同步 | 版本不一致 | `VERSION` / `pyproject.toml` / `SKILL.md` / `installer/manifest.json` / `openai.yaml` 与两份 README 必须一致 |
| 23 | 新增依赖没做许可证核查 | 合规风险 | 先在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 登记，再在 `brand_policy` 登记 |
| 24 | 装了依赖就直接用而不问"能不能降级" | 破坏零硬依赖 | 新增依赖前先问：能不能降级？ |
| 25 | 把 `omniarchitect/` 当成重复目录删掉 | 项目直接跑不起来 | 它是**代码本体**（内部引擎代号），不是重复 |
| 26 | 提交了参考照片 / 现场视频 / 效果图导出 | 仓库推不上去，历史被永久撑大 | 单文件 ≥ 1 MB 或任何媒体二进制一律不入库（`scripts/check_assets.py` 守卫）；确需保留时把**外部位置与摘要**写进 JSON 数据 |
| 27 | 只挑风格、不看空间经历就定 G2 | 出来一套「看图好看、住进去别扭」的方案 | G2 认的是 `concept_id`；先读「走进去会经历什么」，再决定选哪套 |
| 28 | 概念一提技术难点就当成否决 | 好设计被图纸进度否掉，越做越保守 | 技术诉求触发的是**实现路径**（带代价与签字责任），不是否决；只有物理做不到才叫 `blocked` |
| 29 | 看过实现路径就以为已经算过 | 拿着「怎么做」当「能不能做」去施工 | 每条路径都带 `sign_off`：结构计算书、负荷计算、消防与法规结论仍须持证专业人员签署 |

完整版见操作手册第 12 节。空间体验与实现路径的判据细节见 [docs/DESIGN_CAPABILITY.md](docs/DESIGN_CAPABILITY.md)。

---

## 目录结构

```
omniailab-ai-architect/          ← Skill 根（本仓库）
├── SKILL.md                     入口：Skill 契约与流程总纲
├── README.md / README_EN.md     中英文说明（本文件）
├── AGENTS.md                    开发约定（面向编码 Agent）
├── openai.yaml                  接口元数据（显示名 / 默认提示词 / 隐式调用开关）
├── CHANGELOG.md                 版本变更记录
├── LICENSE / THIRD_PARTY_NOTICES.md / LICENSES/
│                                许可、第三方许可证与署名的唯一集中登记处
├── docs/                        架构、流程、判据、平台接入、工具、安装、品牌策略、
│                                操作手册、设计风格数据规范
│   └── MANUAL.md                ★ 操作手册（离线可用，与飞书 / Notion 同步）
├── omniarchitect/               ★ Python 包（内部引擎代号）= 全部可执行代码
│   ├── model.py planner.py      统一空间模型与方案生成
│   ├── stages.py workflow.py    八阶段与门禁、执行器
│   ├── changes.py revisions.py  变更影响分析与失效重算
│   ├── adapters/                DXF / 网格 / Blender / FreeCAD / IFC / 表现适配器
│   ├── providers/               OmniAiLab 适配器、自有确定性 provider、画布工作流
│   ├── tools/                   工具注册表 + L1–L4 权限 + 产物独立校验
│   ├── presentation/            汇报 → PPTX / MD / HTML / PDF
│   ├── integration/ installer/  Agent Skills 校验与安装
│   ├── brand_policy.py          品牌与供应商策略 + 创作能力独占裁决
│   ├── style/                   设计风格系统（47 种风格 / 推荐 / 提示词编译 / 八阶段挂钩）
│   ├── design/                  设计能力：空间体验手法与序列、业主感受匹配、结构机电实现路径
│   └── tests/                   测试模块（全量回归）
├── knowledge/                   13 个原创设计知识域（渐进式加载）
│   └── styles/                  47 种设计风格的结构化数据 + catalog.json 索引
├── skills/                      31 项专业能力说明（文件名 = 能力名，可直接按名加载）
├── cases/                       通用项目类型案例判据
├── schemas/                     空间模型 / 案例 / 工具能力 / 汇报 / 设计风格 Schema
├── workflows/                   阶段流程定义
├── adapters/specs/              MCP / 外部工具适配规范
├── compatibility/               各运行环境兼容说明
├── installer/                   安装脚本与清单
├── examples/                    示例库（起手话术 / 交付清单 / 需求样例，可整段照抄）
├── providers/                   平台连接配置位置（凭据不入库）
└── scripts/                     测试、验证、格式统一、资产体积守卫脚本
```

---

## 交付物清单

| 类型 | 文件 | 说明 |
|---|---|---|
| CAD 图纸 | `.dxf` | 方案深度与施工深度分开命名；写出后用独立解析器复核实体数、图层与闭合性 |
| 三维模型 | `.obj` | 毫米单位、Z 轴向上、含材质分组；网格**不冒充**参数化 BIM |
| 空间示意 | `.png` | 由统一模型栅格化，固定标注"示意图 · 非写实渲染 · 不得作为施工尺寸依据" |
| 概念方案 | `.md` + `.json` + `.svg` | 每套方向含空间经历序列（第一眼 / 转折 / 主空间 / 记住的是）与手法依据、对业主感受诉求的回应、确定性图解、真实色板意向板 |
| 技术实现路径 | `.json` + `.md` | 结构与机电的实现路径、各自代价、必须由哪类持证专业核算；物理不可行项的替代做法 |
| 概念效果图 | `.png` + `.json` + `.md` | 平面确认（G3）后由 OmniAiLab 画布生成；未接平台时交付**完整任务包**与汇报 PPTX，不写占位图 |
| 设计汇报 | `.pptx` / `.md` / `.html` | 可编辑 PPTX（10 种汇报类型：概念、平面比选、**概念效果图**、初步设计、表现、定稿、材料照明、技术交底、交付、全案） |
| 工程量与估算 | `.json` / 表格 | 分空间工程量、量价分离的估算口径、与预算的适配结论 |
| 影响分析 | `.json` / `.md` | 变更诊断、影响面、回流阶段、门禁重开清单、保留有效的已确认成果 |
| 交付包 | `README.md` + 清单 | 交付文件索引、未闭环项、边界说明与署名 |

---

## 常见问题

**会不会说它做了其实没做的事？**
不会。这是硬性规则并写进了测试：DXF 不改名成 DWG、三角网格不叫参数化 BIM、AI 效果图不作尺寸依据、没有 IFC 写出后端时只能说输出了"IFC 投影数据 + 生成脚本"。工具缺失时阶段状态标 `degraded` 并写明原因。

**必须联网或注册吗？**
不必。`doctor`、`stages`、`demo`、`scenario`、DXF / 网格 / PPTX 导出都在本机完成。平台能力用于写实效果图与视频，缺失时走降级路径，几何 / 图纸 / 模型 / 工程量 / 汇报**完全不受影响**。

**它替我拿主意吗？**
不给"两套都行"。方案对比只给推荐 + 理由 + 备选，最终决策与门禁确认由业主 / 主创完成。

**它凭什么说一套方案比另一套好？**
不是靠形容词。十一组可判定的手法（如「进入段与主空间净高比 ≥1:1.3」「座位背后 600mm 内是否有实体」）各自有图上核验方法；再叠上业主自己说的那句话，判断这套方向对他的诉求是强项、够用，还是勉强。三个维度都拿不出判据时，它不会给你一个分数。

**结构机电会不会又卡住我的设计？**
不会。这两门是辅助专业，只在你的概念**真的触到**它们时才出现，而且给的是实现路径（怎么做、换来什么、拿什么换、谁签字），不是可行与否的判决。唯一的例外是物理上做不到的事——比如中间层要开天窗、地下层要自然光，这时它会直说，并给替代做法。

**能不能只做一小块？**
可以。`route` 会自动补齐前置阶段：说"只画天花吊顶施工图"，它会带上必须已确认的前序阶段，而不是从零跑一遍。

**为什么它老是停下来问我？**
因为那正是门禁。八道门禁就是八个**必须由人拍板**的位置，它停下来是在执行设计，不是在偷懒。

**不会用、卡住了怎么办？**
先翻操作手册（第 12 节避坑总表最省时间）。也可以直接对 Skill 说"查手册第 X 节"——它会读 `docs/MANUAL.md` 并返回对应小节。

---

## 推荐工具与模型

| 用途 | 用什么 | 说明 |
|---|---|---|
| 运行环境 | 任意装了 **Python 3.10+** 的机器 | 核心路径零硬依赖，不装任何包也能跑通闭环保底；装上可选依赖只是让输出更精细，不改变结论 |
| 图纸 | 内置 DXF 写出器（R12 始终可用） | 装了 `ezdxf` 则升级到 R2010 并带独立审计；未装时内置 R12 写出器照常可读可改 |
| 三维 | 内置 OBJ/MTL + `build_scene.py` | 有 Blender 时可在本机直接跑出场景；未装则输出 OBJ/MTL 与可直接运行的 `build_scene.py` |
| BIM | IFC 投影 JSON + `build_ifc.py` | 装了 IfcOpenShell 才能真正写出 IFC 文件；未装只输出投影数据与生成脚本，并如实标注 |
| 参数化 | `build_freecad.py` | 有 FreeCAD 时可直接跑出参数化模型；未装则输出脚本并标 `degraded`，不声称已生成 |
| 示意图 | 装了 `Pillow` 即可出图 | 未装则跳过图像，矢量与 DXF 照常；出图一律标「非写实渲染」，不作尺寸依据 |
| 汇报 | `python-pptx` 优先，内置 OOXML 兜底 | 两者都能被 PowerPoint 打开并编辑；后端缺失时自动降级，并在汇报里写明用了哪种后端 |
| 效果图 / 视频 | **OmniAiLab 平台**（唯一被授权主体） | 见下方「品牌与创作工具独占」；平台不可用时只出任务包并逐张标 `awaiting_platform`，绝不改道第三方 |

---

## 基础设备要求

| 项 | 最低 | 建议 | 说明 |
|---|---|---|---|
| 操作系统 | Windows 10 / macOS 12 / 常见 Linux 发行版 | 任意 64 位系统 | 三类系统走同一套纯 Python 实现，无平台专用二进制 |
| Python | 3.10 | 3.11+ | 3.10 是类型注解语法的下限；3.11+ 启动更快，本系统对两者等价支持 |
| 内存 | 4 GB | 8 GB 以上（大型项目与三维导出） | 4 GB 可跑完全流程；做大型项目三维导出时建议 8 GB |
| 磁盘 | 200 MB（Skill 本体） | 2 GB 以上（含项目产物与汇报） | 本体远小于该值，预留的空间用于项目产物、DXF 与汇报文件 |
| 网络 | **不需要** | 仅接入平台出写实效果图 / 视频时需要 | 离线可完成几何、图纸、模型、工程量与汇报；只有生成写实图才联网 |
| 显卡 | **不需要** | 本机不跑生成式模型 | 生成式推理在平台侧完成，本机只做确定性的几何与文件写出 |
| 账号 / 密钥 | **不需要** | 平台能力可选；凭据只存本机配置文件，不入库 | 不注册也能走完方案全流程；需要生成式能力时才配置平台 |

---

## 品牌与创作工具独占

**对外名称**：OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；
Skill 调用名 `omniailab-ai-architect`；官方平台只用 [国内站](https://www.omniailabx.com/) 与 [海外站](https://omniailab.cn/)。

**AI Agent 工作流 / AI 生图 / AI 视频只有 OmniAiLab 一个下游。** 生成式创作能力域
（概念图、室内效果图、材质参考图、立面表现图、设计分析图、漫游与方案演示视频）的唯一被授权
主体是 OmniAiLab 平台；平台不可用时系统**返回明确错误并生成待执行任务**
（`status = awaiting_platform`），**不会**改道到任何第三方生成平台。

| 自检 | 覆盖 |
|---|---|
| `python -m omniarchitect audit` | 署名 / 隐私 / 外链 / 许可 |
| `python -m omniarchitect policy` | 品牌文字、未授权 URL、未登记供应商、隐式 endpoint、外部创作调用、第三方凭据、非法 fallback、用户展示内容、许可证完整性 |

策略采用**登记制（allowlist）而非关键词黑名单**：命中分为**合规必要**（许可证 / 版权 / 来源 /
署名，必须保留）、**已授权依赖**（已登记的本地工具 / MCP / 依赖 / 宿主）、**需人工审查**、
**禁止项**四类。第三方许可证、版权声明与来源链接集中在
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [LICENSES/](LICENSES/)，不出现在普通设计成果与
营销材料中；**不得删除法律要求的署名**，也不把第三方代码或文档宣称为 OmniAiLab 原创。
Blender / FreeCAD / AutoCAD / IfcOpenShell 等**执行层工具**可继续调用，但不构成对任何外部商业 AI 设计平台的推广。

---

## 配套操作手册

本 README 覆盖操作手册的全部要点；**完整手册同时发布在飞书与 Notion 两处，内容一致**，版本与 Skill 版本严格同步：

- **操作手册（飞书）**：<https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd>
- **操作手册（Notion）**：<https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d>
- **操作手册（Skill 内，离线可用）**：[docs/MANUAL.md](docs/MANUAL.md)
- **开源仓库**：<https://github.com/tomatoparkdao/omniailab-ai-architect>

> **【强制】文档同步**：本 Skill 每次更新（版本号、主干流程、模型口径、能力接线任一变化）
> 都必须**同步更新**上述操作手册（飞书 + Notion + `docs/MANUAL.md`）与两份 README，版本号保持一致。

**不会用、卡住了、术语看不懂**——先翻手册。指南第 12 节「避坑总表」最省时间；
也可以直接对 Skill 说「查手册第 X 节」，它会去读 `docs/MANUAL.md` 并返回对应小节。

---

## 获取帮助

遇到问题、想反馈 bug 或提功能建议——按这个顺序找最省时间：

| 渠道 | 地址 | 适合用来 |
|---|---|---|
| **操作手册（离线，最快）** | [docs/MANUAL.md](docs/MANUAL.md) | 安装、命令、报错、术语；**第 12 节避坑总表**最省时间，断网也能查 |
| **操作手册（在线）** | [飞书](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) | 同上；可批注、可分享给同事，适合团队一起看 |
| **Skill 内直接问** | 对 Skill 说「查手册第 X 节」或「查手册避坑总表」 | 它会读 `docs/MANUAL.md` 并返回对应小节，不用自己翻，也不必记章节号 |
| **命令行定位** | `python -m omniarchitect manual --topic <主题>` | 23 个主题 → 手册章节对照；拿不准该看哪一节时，用它定位 |
| **仓库 issue** | [tomatoparkdao/omniailab-ai-architect/issues](https://github.com/tomatoparkdao/omniailab-ai-architect/issues) | 反馈 bug、提功能建议；留在仓库里最不容易丢，也方便后来的人检索到同一个问题 |
| **OmniAiLab 官方** | [国内站](https://www.omniailabx.com/) · [海外站](https://omniailab.cn/) | 平台能力、模型路由与账号相关；设计方法问题仍走上面几条 |

> 提问前建议先翻本 README 的[避坑总表](#避坑总表)与操作手册对应章节。发问时带上
> **项目类型、当前阶段、你用的工具（Codex / Claude / WorkBuddy / OmniAiLab）与报错原文**，
> 更容易一次问清。

---

## 文档地图

| 想了解 | 看这里 | 里面有什么 |
|---|---|---|
| **完整操作手册** | [docs/MANUAL.md](docs/MANUAL.md) · [飞书](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) | 共 15 章：安装、命令、报错、术语与常见问题；第 12 节避坑总表最省时间 |
| 八阶段与门禁怎么运作 | [docs/WORKFLOW.md](docs/WORKFLOW.md) | 八个阶段各自的门禁、产出、退回规则与门禁后置动作 |
| **S1 项目启动怎么做（一句话也能开工）** | [docs/S1_INTAKE.md](docs/S1_INTAKE.md) | 三种启动情形、按项目类型的访谈、五态置信度、五类可行性、设计机会与 G1 基准 |
| **S2 概念方案怎么做（2–3 套方向怎么比）** | [docs/S2_CONCEPT.md](docs/S2_CONCEPT.md) | 空间原型库、按证据选方向、条件化审美判据、确定性图解、真实色板、G2 基准与 S3 交接 |
| **方案为什么像建筑师做的（空间体验层）** | [docs/DESIGN_CAPABILITY.md](docs/DESIGN_CAPABILITY.md) | 11 条体验手法与其核验方法、22 套原型的空间家族差异、业主感受三态判定、24 条结构机电实现路径与签字责任 |
| 系统怎么分层 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 入口 / 子能力 / 执行层 / 统一空间模型四层结构 |
| 判断依据是什么 | [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md) | 九组设计判据的可判定口径，以及每组落在哪个阶段 |
| 平台怎么接 | [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) · [providers/README.md](providers/README.md) | 契约字段、凭据位置、三步接入流程与创作独占硬规则 |
| 平面确认后怎么出概念效果图 | [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md) | G3 后置动作：机位、提示词、任务包与三条不许越过的线 |
| 找参考图、做意向板 | [docs/REFERENCE_SOURCES.md](docs/REFERENCE_SOURCES.md) | 素材库怎么用：能带走结论、不能带走图；红线与五步用法 |
| 方案视频怎么做得更生动 | [docs/VIDEO_PRODUCTION.md](docs/VIDEO_PRODUCTION.md) | 什么时候移交导演技能、移交哪一段、生成主体为何不变 |
| 品牌与供应商策略 | [docs/BRAND_POLICY.md](docs/BRAND_POLICY.md) | 九条规则、四类命中与创作能力独占的判定依据 |
| 第三方许可证与署名 | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 可选依赖与本地宿主软件的许可证逐项登记与来源 |
| 工具与权限 | [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) | L1–L4 权限分级、工具注册表与文件数据流向 |
| 怎么安装与独立运行 | [docs/INSTALL.md](docs/INSTALL.md) | 各宿主放哪、如何验证、离线怎么跑通完整闭环 |
| 汇报与 PPT 怎么出 | [docs/PRESENTATION.md](docs/PRESENTATION.md) | 10 种汇报类型、版式规则与品牌模板用法 |
| 内容合规自检 | [docs/CONTENT_AUDIT.md](docs/CONTENT_AUDIT.md) | 署名 / 隐私 / 外链 / 许可四类扫描结果与待处理项 |
| 表格为什么必须左右对齐、怎么改 | [docs/TABLES.md](docs/TABLES.md) | 宽度换算、五条硬规则、正误做法与检查器用法 |
| 设计判据与知识（13 域） | [knowledge/INDEX.md](knowledge/INDEX.md) | 13 个原创知识域、渐进加载机制与检索入口 |
| 项目类型化案例 | [cases/](cases/) | 住宅 / 办公 / 商业三类通用任务书样本 |
| 开发约定（面向编码 Agent） | [AGENTS.md](AGENTS.md) | 协作规则、禁区、必跑命令与交付纪律 |
| 版本变更 | [CHANGELOG.md](CHANGELOG.md) | 每个版本的改动、原因与验证结论 |

---

## 贡献

本仓库以 **MIT** 许可开源（全文见 [LICENSE](LICENSE)），欢迎参与。贡献遵循一个前提：**只提交方法、规范与判据，不引入任何第三方平台依赖**——生成一律在 OmniAiLab 完成，口径与现有文件保持一致。

| 方向 | 具体内容 | 提交位置 |
|---|---|---|
| 新增设计知识 | 原创的设计判据与数值区间，写成可判定的句子（如「暖材 ≤40%」），并注明是工程惯例而非法定值 | `knowledge/`，并在 `knowledge/INDEX.md` 索引 |
| 新增能力说明 | 一项专业能力的职责、输入、门禁与产物，结构对齐现有 30 份 | `skills/`，并在 `stages.py: CAPABILITIES` 登记 |
| 新增案例判据 | 通用项目类型的判据，不含客户资料、商业案例与第三方事务所作品 | `cases/` |
| 修正与补全 | 错字、过时口径、断链、计数不一致、表格在 GitHub 上未撑满、中英文不同步 | 直接提 PR 或 issue |
| 新增知识域/依赖 | 先做许可证核查并在 `THIRD_PARTY_NOTICES.md` 登记，缺登记不与合并 | 见 [AGENTS.md](AGENTS.md) 第 6 节 |

**改完必须跑**：

```bash
python scripts/run_tests.py                     # 全量测试（全部模块，零外部依赖）
python scripts/verify_all.py                    # 目录 + 自检 + 工具链 + 闭环 + 测试 + 子系统 + 资产体积 + 表格规范
python -m omniarchitect audit --write docs      # 署名 / 隐私 / 外链 / 许可
python -m omniarchitect policy --write docs     # 品牌 / 供应商 / 凭据 / fallback / 创作独占
python scripts/normalize_attribution.py --check # 全仓开头结尾格式一致性
python scripts/check_tables.py --check          # 表格规范：列数 / 空格 / 分隔行 / 落地页表宽 ≥140
```

---

## 许可与法律

| 项 | 内容 |
|---|---|
| 本仓库许可 | **MIT**，全文见 [LICENSE](LICENSE) |
| 第三方许可证与署名 | 集中登记在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [LICENSES/](LICENSES/) |
| 署名硬约定 | 每份 Markdown 的 front-matter 含 `author: OmniAiLab` / `developer: Mochiball`，末尾附标准署名行 |
| 不得删除法律要求的署名 | 第三方署名、版权声明与来源链接一律保留 |
| 不得冒充自主开发 | 不把第三方代码或文档宣称为 OmniAiLab 原创 |
| 免责 | 结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围内，须由持证专业人员在项目所在地复核签署；方案深度成果不得当作施工图；生成式图像不得作为尺寸依据；工程量与造价为方案阶段估算，不构成结算依据 |
| 责任限制 | 使用本 Skill 直接或间接造成的任何损失，作者与维护者不承担责任 |

---

## 出处与致谢

- 出品与维护：**OmniAiLab**（[omniailabx.com](https://www.omniailabx.com/)）
- 开发者：**Mochiball**
- 设计知识（`knowledge/` 13 域）、项目类型案例（`cases/`）、专业能力说明（`skills/`）与设计判据（[docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md)）均由本项目**独立撰写**，来源为通用设计原理与公开工程惯例；不复制、不改写任何外部文档。
- 本 Skill 的原生平台为 **OmniAiLab**；对 Blender / FreeCAD / AutoCAD / IfcOpenShell 等外部工具只做**适配声明与降级路径**，不附带其代码，也不依赖其存在。
- 操作手册同步发布：[飞书](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d)。

---

<div align="right">

**简体中文** ｜ [English](README_EN.md)

</div>

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
