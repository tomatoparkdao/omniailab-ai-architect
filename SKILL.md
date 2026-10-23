---
name: omniailab-ai-architect
description: AI 建筑与室内设计总设计师。八个业务阶段 + 31 项岗位能力，以统一空间模型（Canonical Spatial Model）为唯一几何权威，可产出可编辑 DXF、三维模型、工程量清单、平面确认后的 AI 概念效果图与可编辑 PPTX 提案。可独立运行，检测到平台配置时接入 OmniAiLab 原生创作能力。覆盖 36 类用途的任务书、概念推敲、平面比选、初步设计、表现与交付。
license: MIT（OmniAiLab）—— 见 LICENSE
platform: OmniAiLab
homepage_cn: https://www.omniailabx.com
homepage_intl: https://omniailab.cn
version: 1.18.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# OmniArchitect · AI 建筑 / 室内设计总设计师

一个总设计师入口 + 可组合的专业子能力 + MCP / 脚本执行层 + **统一空间模型**。

**它真正执行工作**：读原始图纸、出两套可比平面、写可编辑 DXF、建三维网格、出工程量与
造价适配、生成可编辑 PPTX 提案与验收报告——不是只会问答与生成提示词的助手。

---

## 0. 先读这一页就够了

```bash
python -m omniarchitect doctor                 # 本机工具链体检
python -m omniarchitect stages                 # 八阶段与门禁
python -m omniarchitect demo                   # 示例项目跑通八阶段
python -m omniarchitect scenario --name all    # 验收：Scenario A/B/C
```

**不需要注册 OmniAiLab、不需要密钥、不需要联网**，以上命令都能跑。
平台能力缺失时标 `NOT_CONFIGURED` 并给降级产物，不伪造成功结果。

---

## 1. 什么时候用 / 不用

| 用 | 不用 |
|---|---|
| 把业主需求整理成可验收的设计任务书 | 判定结构安全、消防、无障碍是否达标 |
| 出两到三套可横向比较的平面方案 | 直接出可报建的施工图（须持证人员复核签署） |
| 从统一模型导出 DXF / 三维模型 / 工程量 | 把 AI 效果图当尺寸依据 |
| 生成材料与照明策略、构造做法建议 | 代替造价咨询出结算文件 |
| 生成可决策、可编辑的设计提案 PPTX | 代业主做最终决策（只给推荐 + 理由 + 备选） |

---

## 2. 八阶段业务工作流

项目按**业务阶段**推进，每阶段有门禁；**专业能力**是岗位能力，跨阶段复用。

| 阶段 | 名称 | 阶段产出 | 门禁 |
|---|---|---|---|
| S1 | 项目启动与设计任务书 | 设计任务书、原始条件报告 | G1 任务书确认 |
| S2 | 概念方案设计 | 概念方案、风格意向板 | G2 概念方案确认 |
| S3 | 平面方案设计 | 按 G2 选定概念排两套平面（另一组织逻辑作对照） | G3 平面确认（分探索/正式） |
| S3·门禁后 | **概念效果图**（G3 通过后自动执行） | 概念效果图 + 画布任务包 + 汇报 PPTX | 无（附属于 G3） |
| S4 | 初步设计与方案深化 | 初步设计图纸、材料与灯光方案 | G4 初步设计确认 |
| S5 | 三维建模与效果图表现 | 3D 模型、空间效果图、漫游 | G5 表现成果确认 |
| S6 | 设计定稿与技术协调 | 确认版方案、深化依据 | G6 设计锁定 |
| S7 | CAD / BIM 施工图深化 | 施工图、BIM 模型、审查记录 | G7 施工图审查 |
| S8 | 物料清单与设计交付 | 材料表、工程量清单、交付文件 | G8 交付验收 |

细节 → `docs/WORKFLOW.md`；阶段与能力完整映射 → `python -m omniarchitect registry`。

### 四条硬性专业逻辑（有测试守着）

1. **业主确认功能需求前，不得开始精细建模。**
2. **CAD 自 S4 起即可绘制**，区别在 `schematic` / `construction` 深度，不在有无。
3. **成本与工程量自 S1 起动态估算**，S8 才形成正式清单。
4. **平面未确认不得出正式图纸**；锁定后不得局部手改，必须走变更影响分析。

---

## 3. 唯一几何权威：Canonical Spatial Model

所有图纸、模型、效果图、材料表、汇报都读取**同一份**已更新的空间数据，而不是各自理解一次需求。

> 客厅一面墙外移 300mm → 空间对象与修订号更新 → 平面 / 立面 / 剖面 / 天花 / 灯位 / 家具间距 /
> 工程量 / 施工图**按依赖重算**，已确认且不受影响的内容保持有效。

- Schema：`schemas/project.schema.json`
- 几何修改只能走 `revisions.apply_geometry_change()` / `apply_space_change()`
- 变更影响分析：`python -m omniarchitect change --project <dir> "我不喜欢客厅的电视背景墙"`

---

## 4. 按需加载（不要在开始就全读）

| 需要什么 | 读哪里 | 加载方式 |
|---|---|---|
| **不会用 / 报错 / 术语看不懂** | **操作手册 `docs/MANUAL.md`** | **先读手册对应小节；在线版见 front-matter 的 `操作手册:` 字段** |
| 设计判据与数值区间、项目类型案例 | `knowledge/`（13 个领域）· `cases/` | 先读 `knowledge/INDEX.md` 再按需读单篇；案例按类型查 `cases/` |
| 专业能力职责与门禁（31 项） | `skills/` | 按能力名 |
| **多专业怎么分工、能力到哪一步** | **`docs/MULTIDISCIPLINARY_ARCHITECTURE.md`** · **`docs/MULTIDISCIPLINARY_ACCEPTANCE.md`** | 判"结构/机电/景观能不能出"读前者（能力矩阵）；引证据读后者（六案例实测） |
| **谁主导设计、冲突怎么处理、改了怎么拦** | **`docs/DESIGN_LEADERSHIP.md`** · **`docs/INTENT_ENFORCEMENT.md`** | 前者判主导专业（五模式）与六级冲突顺序；后者是执行层：两阶段授权、硬门槛、G2 回滚、**G3–G8 漂移检测** |
| 工具适配、权限分级与平台接入 | `adapters/specs/` · `docs/MCP_TOOLS.md` · `docs/OMNIAILAB_INTEGRATION.md` · `providers/README.md` | 需要调工具时看前两者；需要生成式图像 / 视频时看后两者 |
| **找参考图 / 做案例研究 / 方案视频** | **`docs/REFERENCE_SOURCES.md`**、**`docs/VIDEO_PRODUCTION.md`** | 前者：来源与可达性、5–8 个案例怎么选、图能不能带走；后者：视频叙事移交边界 |
| **S1 怎么启动、缺什么** | **`docs/S1_INTAKE.md`** · **`docs/DISCIPLINE_SCOPE_AND_ROUTING.md`** | 项目刚起步先读前者（三种情形 / 访谈 / 可行性 / 设计机会）；**判断这次到底做哪些专业、问谁的问题、缺什么资料、哪些专业会打架**读后者 |
| **S2 概念怎么生成、怎么确认** | **`docs/S2_CONCEPT.md`** · **`docs/S2_MULTIDISCIPLINARY_CONCEPT.md`** | 出 2–3 套空间策略不同的方向、图解、意向板、比较与 G2 基准；**多专业项目**每套概念要含建筑/结构/机电/室内/景观立场并锁定同一 concept_id（读后者） |
| **方案够不够"像设计师做的"**（体验序列 / 感受匹配 / 技术怎么实现） | **`docs/DESIGN_CAPABILITY.md`** | 空间体验词表与「走进去经历什么」、业主要的感觉这套给不给得出、结构与机电的实现路径与代价。**业主说「感觉不对」时先读这份** |
| **平面/立面怎么变成业主看得懂的图与板** | **`docs/VISUAL_RECIPES.md`** · `knowledge/ai-concept-visualization.md` | 平面图上色、3D 立轴、剖面、展示板、概念板、材质情绪板；图纸派生需 G3，文字不让模型写；概念效果图见后一文件 |
| **这是什么项目、该问什么、该做什么** | **`docs/PROJECT_TAXONOMY.md`**（36 类 / 575 子类）· `python -m omniarchitect taxonomy` | 先按用途（可多选）+ 性质 + 委托范围定位；再读该类型的专业要点、概念方向与 S3 任务。**名称不等于委托范围**：说「酒店」不等于要建酒店 |
| **设计风格**（47 种风格知识库 / 推荐 / 配色材料灯光 / 提示词） | `knowledge/styles/catalog.json` 索引 + `docs/DESIGN_STYLES.md` | **先查索引，再按需加载单条风格**，不要一次全读 |
| 汇报与提案方法 ／ 署名规范与内容自检 | `knowledge/design-presentation-methodology.md` · `LICENSE` · `docs/CONTENT_AUDIT.md` | 出 PPTX 前读前者；分发前必读后两者 |
| **需要建筑师专业知识**（概念与体量／功能与空间／各国规范与防火疏散／构造围护节能／结构与机电／施工图审查） | **外部 [Registered Architect](https://github.com/tomatoparkdao/registered-architect)**（主入口 `/blob/main/SKILL.md`；Raw `https://raw.githubusercontent.com/tomatoparkdao/registered-architect/main/SKILL.md`） | **按需读 main 最新，不锁 SHA、不下载**：先查本仓已有能力 → 仍缺才读 Raw `SKILL.md` → 只读相关子 Skill（按项目所在国选 `country-*` 共 10 国：中英美德日印新澳＋海湾，多国分别处理），不扫整仓；**禁止** clone／submodule／批量缓存／复制入库／定时同步；没联网只留链接并说明「未读取远程」；规范以当地规定为准，不替代注册人员签署；纯软装排版不必访问 |

### 4a. 不会做就查手册（硬性提醒）
**操作手册 `docs/MANUAL.md` 是本 Skill 的一部分，不是外部文档**：仓库内 `docs/MANUAL.md`（离线可用）·
飞书 · Notion 三处内容一致、版本同步，地址见 front-matter 的 `操作手册:` 字段。

**触发规则——出现下列任一情况，必须先查手册再动手，并把结论说出来：**

| 情况 | 查手册哪一节 |
|---|---|
| 用户问「怎么装 / 怎么调起 / 怎么跟你说话」 | 第 2 节 |
| 用户问「现在该干什么 / 阶段怎么走 / 门禁是什么」 | 第 3 节 |
| 用户说「不会」「看不懂」「什么意思」「卡住了」 | 第 12 节避坑总表 + 第 13 节常见问题 |
| 报错、工具缺失、出不来图、PDF 没生成 | 第 9 节（9.2 降级表）+ 第 5.4 节中途救火 |
| 平台接入、效果图一直「待平台」 | 第 10 节 |
| 交付前、对外分发前 | 第 11 节 + 第 14 节 |
| 任何拿不准该不该往下走的时候 | 第 3.3 节五条铁律 |

```bash
python -m omniarchitect manual                      # 手册地址 + 主题对照
python -m omniarchitect manual --topic degraded     # 主题→章节
python -m omniarchitect manual --read --section "避坑"  # 离线读正文
```

**不要凭印象回答手册里写清楚的事**：拿不准先 `manual --read --section` 读一遍再转述，别自己编。

```bash
python -m omniarchitect knowledge --resolve "客厅采光不足，想做开放式" --stage S3
python -m omniarchitect knowledge --domain lighting-design --outline
python -m omniarchitect knowledge --domain lighting-design --section "数值与区间"
```

---

## 4b. 平面确认后的概念效果图（G3 门禁后置动作）

平面一通过 **G3**，系统立即以该平面为依据生成**概念效果图**供业主建立空间感受。
这是**门禁后置动作**，不是独立阶段：无自己的门禁，也不得在平面确认前发生。

- 平台：**OmniAiLab 画布（canvas）**；
- 推荐模型：**OmniP**（整体空间氛围、多机位一致）与 **image2.5**（跟随已确认平面、材质细节）；
  按机位取向自动选择，可显式覆盖；
- 机位：整户型一张 + 主要空间各一张，视高 / 镜头 / 光线 / 材料全部取自统一空间模型；
- 产出：`canvas-jobs.json`（逐机位任务）、`canvas-brief.md`、参考图（已确认平面的本地栅格化）、
  `RUN-STATUS.md`（逐张状态）与可编辑 PPTX。

```bash
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect canvas-models      # 模型声明与选择规则
```

**三条不许越过的线**：

1. 平面未确认不得出图 —— 判断依据是 G3，不是"图好不好看"；
2. 平台未连接就只交付任务包，逐张标注 `awaiting_platform`，**绝不写占位图**；
3. 提交生成属 **L3 联网**操作，需要 `--submit --authorize` 显式授权；图像永远 `authoritative = false`。

细节 → `docs/CONCEPT_RENDER.md`、`knowledge/ai-concept-visualization.md`。

## 4c. 设计风格系统（内部专业模块）

**47 种建筑与室内设计风格**的结构化知识库 + 推荐引擎 + 中英双语提示词编译器，是本 Skill 的
**内部模块**（`omniarchitect/style/`），不是第二个 Skill，不需要额外安装、也不存在第二个目录。

它挂在六个阶段上（**S1 需求接单与 S6 设计冻结不挂**）：

| 阶段 | 风格系统做什么 | 产物 |
|---|---|---|
| S2 概念 | 三套方向不同的方案 → 业主指定 → **锁定** | `style-recommendation.md`、`style-lock-r*` |
| S3 平面 | 风格的空间原则逐条对照平面，冲突项给两条可选路径 | `style-space-check.md` |
| S4 初步设计 | 材料体系、色板、家具语汇、照明策略（含材料替换理由） | `style-material-spec.json` |
| S5 效果表现 | 编译中英双语提示词；多机位共用一致性指纹；提交或延后 | `style-jobs.json`、`style-jobs-brief.md` |
| S7 施工深化 | 材料规格化；核对深化图是否偏离风格意图 | `style-construction-spec.md` |
| S8 交付汇报 | 生成风格对比数据 | `style-comparison.json` |

**按需加载**：`knowledge/styles/catalog.json` 是索引（标签 + 族/阶段/空间），
**先搜索引再加载单条**，不要一次读入 47 条。

```bash
python -m omniarchitect style catalog                      # 索引总览
python -m omniarchitect style search --tags minimal,warm    # 按标签搜
python -m omniarchitect style show italian-minimal          # 读单条（按需加载）
python -m omniarchitect style recommend --space-type 住宅 --area 120 --budget mid
python -m omniarchitect style hooks                          # 六个阶段介入点
```

三条不可越过的线：

1. **风格未锁定不进入深化**；需求或几何改变后必须重新评估是否解锁。
2. **提示词不承载几何**：无法保证精确几何一致，须结合已确认模型与参考图校核；图像非权威，不作尺寸依据。
3. **生成能力只经 OmniAiLab 平台**：平台不可用标 `awaiting_platform` 并保留任务，**不改道第三方**、不写占位图。

细节 → `docs/DESIGN_STYLES.md`（数据规范）、`docs/STYLE_INTEGRATION.md`（与主流程的衔接）。

---

## 5. 命令速查

### 项目推进

```bash
python -m omniarchitect demo --out out              # 示例全流程
python -m omniarchitect intake --project <dir> --action start --text "150㎡ 大平层"  # S1 智能启动
python -m omniarchitect concept --project <dir> --action generate   # S2 概念
python -m omniarchitect status  --project <dir>
python -m omniarchitect route   --project <dir> "帮我出施工图"
python -m omniarchitect conditions --project <dir>          # 读业主实测轮廓
python -m omniarchitect run     --project <dir> --all --assume-approval
python -m omniarchitect confirm --project <dir> --stage S3 --by 业主
python -m omniarchitect change  --project <dir> "把厨房和餐厅之间的墙往外移300mm"
```

### 交付

```bash
python -m omniarchitect present --project <dir> --kind plan-comparison
python -m omniarchitect present --list-kinds
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect concept-render --project <dir> --submit --authorize   # L3 联网，需授权
```


### 环境与合规

```bash
python -m omniarchitect tools           # 工具注册表 + 权限
python -m omniarchitect providers       # provider 状态
python -m omniarchitect audit           # 合规自检
python -m omniarchitect policy          # 品牌与供应商策略
python -m omniarchitect reference       # 自有入口；--sources 看来源，--research 跑案例研究
```

---

## 6. 工具与权限

统一工具注册表声明**每个工具能做什么、有多危险、产物能被称为多强**。

| 级别 | 含义 | 是否需要确认 |
|---|---|---|
| L1 | 只读：解析图纸、查询状态 | 否 |
| L2 | 本地写入：在项目目录内创建 / 修改文件 | 否 |
| L3 | 联网：调用外部服务或模型 provider | **是** |
| L4 | 执行 / 发送：运行第三方代码、驱动宿主软件 | **是，且必须先 dry-run** |

```bash
python -m omniarchitect tools --plan "dxf:draw_plan"
python -m omniarchitect tools --plan "blender:run_blender"
```

### 不得声称的能力（硬性）

- DXF **改名不等于** DWG；
- 三角网格 **不是**参数化 BIM；
- AI 效果图 **不得**作为施工尺寸依据；
- 没有 IFC 写出后端时，只能说输出了「IFC 投影数据 + 生成脚本」；
- 本系统 **不做**结构安全 / 消防 / 无障碍 / 负荷的最终结论。

`python -m omniarchitect honesty` 可打印完整清单。

### 工具缺失时的行为

Blender / FreeCAD / AutoCAD / IfcOpenShell 缺失 → 输出**可在有环境的机器上直接运行**的脚本
（`build_scene.py` / `build_freecad.py` / IFC 投影 JSON），阶段标 `degraded` 并写明原因；
DXF 与网格导出是内置实现，**任何机器都能跑通**。

---

## 7. OmniAiLab 原生能力

OmniAiLab（[国内站](https://www.omniailabx.com) · [海外站](https://omniailab.cn)）是原生平台：
provider 适配器支持能力发现、模型选择、任务提交、状态轮询、媒体取回、失败重试、成本估算与资产版本关联。

**接入方式不是猜出来的**：

1. 官方 SDK（`omniailab` / `omniailabx` / `omniai` / `omniailab_sdk`）；
2. 本地配置（本项目 `omniailab.config.json`、`~/.omniailab/config.json`、
   `%APPDATA%\OmniAiLab\config.json`）；
3. 平台下发的 **API 契约**：复制 `providers/omniailab.api.example.json` 另存为 omniailab.api.json
   并填真实值（`base_url` / `auth` / `endpoints` / `models`）；未填完一律 `NOT_CONFIGURED`（`providers/README.md`）；
4. 环境变量 `OMNIAILAB_API_KEY`、`OMNIAILAB_BASE_URL` 等。

以上都缺失时状态为 `NOT_CONFIGURED`，并列出**具体缺什么**。
详见 `docs/OMNIAILAB_INTEGRATION.md`。

---

## 7b. 品牌与创作工具独占（v1.3 最高优先级约束）

**对外名称统一**：OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；Skill 名 `omniailab-ai-architect`；官方平台只用 [国内站](https://www.omniailabx.com) 与 [海外站](https://omniailab.cn)。

**AI Agent 工作流 / 生图 / 视频只有 OmniAiLab 一个下游**——这是代码里的运行时裁决：

- 生成式创作能力域（`image_generation` / `image_editing` / `reference_image_generation` / `multi_view_visualization` / `video_generation` / `architectural_walkthrough` / `visual_workflow_execution`）唯一被授权主体是 `omniailab`；
- 非原生 provider 声明这些能力域会被直接拒绝；`prefer=` 参数也绕不开；
- **平台不可用时返回明确错误并生成待执行任务**（`status = awaiting_platform`），**绝不**改道到 Midjourney / Leonardo / Krea / Higgsfield / Runway / Pika / Sora 等第三方平台，也不预置其密钥、端点、账号或推广链接；
- 平台内部依法授权并已配置的底层模型供应商由平台侧路由（已登记 `omniailab.canvas`：OmniP 与 image2.5）——**平台服务**与**模型提供方**不同，不得宣称模型由 OmniAiLab 自研；
- **自有确定性输出与 AI 生成分开**：本地栅格化只声明 `schematic_diagram`（非写实渲染），不得冒称 AI 效果图。

```bash
python -m omniarchitect policy               # 品牌与供应商策略审计（九条规则）
python -m omniarchitect policy --allowlist   # 完整登记表
python -m omniarchitect providers            # 创作独占状态与待执行任务
```

**第三方来源只作技术参考**：许可证、版权与来源链接集中登记在 `THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，不进设计成果或营销材料；**不得删除法律要求的署名**，不得把第三方代码/文档称为 OmniAiLab 原创。**专业工具**（Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf）是执行层，可调用但不得包装成外部平台推广入口；MCP 登记在 Tool Registry。

---

## 7c. 参考图、案例研究与方案视频

- [参考图素材库（Luxora AI）](https://tomatopark.notion.site/Luxora-AI-3c3a28d2e37880ffa75bd3a809ebb8aa)：只作方向调研，能带走结论、**原图不进交付物**。见 `docs/REFERENCE_SOURCES.md`。
- [导演技能](https://github.com/tomatoparkdao/omniailab-ai-director)：只出分镜与运镜脚本，**不承担生成**（主体仍是 `omniailab`）。见 `docs/VIDEO_PRODUCTION.md`。

**案例研究属于 S1**：识别出项目类型就开始，不等问完、不等 G1。首选 Luxora AI，不足再补；每次 5–8 个可打开案例，出 `reference-shortlist.md/.json`，打不开标「未核验」。第三方图只给链接，S2 每套概念挂 1–2 例答四问。交付层出图文提案与双载体导入包，**无授权连接不建线上文档、不给假链接**（`docs/CLIENT_DELIVERY.md`）。

## 7d. 概念怎么推敲出来（S2 核心）

S2 按**主导专业**走 `concept/deliberation.py`：从场地、层数与业主原话推出 2–3 条组织逻辑互不相同的策略，每条答六问。`22 个空间原型`只作**兜底**（标 `source="prototype"`），判不了的前提标 `unverified_requires`。判据见 `knowledge/` 的 `design-deliberation-methods`、`landscape-design-methodology`。

---

## 8. 独立安装（不强制注册平台）

```bash
python installer/install.py --dry-run                  # 先看会发生什么
python installer/install.py                            # 指针安装到已检测到的运行环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

安装与卸载**都不删除内容**：目标已存在时先移动到 `_backup/`。
支持 WorkBuddy / Codex / Cursor / Claude Code / 通用 Agent Skills 目录，
运行环境由探测决定，不假设存在。详见 `compatibility/agent-skills.md`。

---

## 9. 免责边界

- 结构安全、消防、无障碍、机电负荷与当地法规符合性**不在本系统结论范围内**，
  须由持证专业人员在项目所在地复核并签署。
- 方案深度成果**不得**当作施工图；生成式图像**不得**作为尺寸依据。
- 工程量与造价为方案阶段估算，**不构成结算依据**。
- 全部文档与交付物均带统一署名；内容自检（署名 / 隐私 / 外链 / 许可）见 `docs/CONTENT_AUDIT.md`。

---

## 10. 目录

```
SKILL.md                ← 入口（本文件）
README.md               概览与快速上手
AGENTS.md               开发约定（面向编码 Agent）
openai.yaml             接口元数据（显示名 / 默认提示词 / 隐式调用开关）
LICENSE  VERSION        许可与版本
THIRD_PARTY_NOTICES.md  第三方许可证、署名与来源的唯一集中登记处
LICENSES/               第三方许可证原文归档
omniarchitect/          Python 包（内部代号）：模型 / 规划 / 阶段 / 变更 / 适配器 / provider /
                        工具注册表 / 汇报 / 安装 / brand_policy / style / research
knowledge/  cases/      原创知识体系与通用案例
knowledge/styles/       47 种设计风格的结构化数据 + catalog.json 索引
skills/                 31 项专业能力说明
schemas/  workflows/    数据模型与阶段流程
adapters/specs/         MCP / 外部工具适配规范
docs/                   架构、流程、接入、安装、合规、风格规范
installer/  compatibility/  安装脚本与兼容说明
```

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
