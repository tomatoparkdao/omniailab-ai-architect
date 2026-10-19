---
name: omniailab-agents-conventions
description: 开发约定 —— 唯一项目根、目录职责、9 条硬性规则、命令清单与改动流程
version: 1.8.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# AGENTS.md — OmniArchitect 开发约定

> **本文件约束所有在本仓库中工作的 AI 智能体与开发者。**
> 它说明项目在哪、怎么跑、什么不能改、以及什么绝对不能假装做到。

---

## 0. 项目根目录（唯一）

```
E:\SKILL\建筑室内设计skill\omniailab-ai-architect
```

- 这是**唯一**的正式开发根目录，同时也是 Agent Skill 根（`SKILL.md` 在此）。
- **Python 包目录是 `omniarchitect/`**（内部引擎代号），它是全部可执行代码所在处：
  模型 / 规划 / 八阶段 / 变更分析 / 适配器 / provider / 工具注册表 / 汇报 / 集成 / 测试。
  它与根目录**不是重复**：根目录是 Agent Skill 根（`SKILL.md`、`knowledge/`、`skills/`、
  `docs/`、`schemas/`、`LICENSE`），包目录是代码本体。
  两者命名不同是刻意的：**对外用产品名 `omniailab-ai-architect`（连字符，Skill 调用名），
  代码用内部代号 `omniarchitect`（可导入的合法标识符）**，避免根目录出现近似重名的顶层目录。
- 运行任何命令前，先把工作区切到该目录；不要依赖提示词里写路径。

```bat
cd /d E:\SKILL\建筑室内设计skill\omniailab-ai-architect
set PYTHONPATH=E:\SKILL\建筑室内设计skill\omniailab-ai-architect
python -m omniarchitect doctor
```

- 父目录 `E:\SKILL\建筑室内设计skill\.workbuddy\` 存放会话记忆，**不属于本仓库，不得删除或改写**。
- 所有工作文件、脚本、缓存、临时产物都必须落在本目录内。禁止在 `C:\`、桌面、Home 或其它盘另建项目副本。

### 目录职责

| 路径 | 内容 | 可否改动 |
|---|---|---|
| `omniarchitect/` | Python 包：模型、规划、工作流、适配器、provider、工具、汇报、集成 | 主开发区 |
| `omniarchitect/stages.py` | **八阶段模型、能力映射与门禁后置动作的唯一权威** | 改前先读 `docs/WORKFLOW.md` |
| `omniarchitect/changes.py` | 设计变更影响分析 | 核心能力，改前先读 `docs/WORKFLOW.md` 第三节 |
| `omniarchitect/providers/` | 生成式 provider（OmniAiLab + 本地）+ 画布工作流 `canvas.py` | 不得猜测 endpoint / 鉴权 / 模型名 |
| `omniarchitect/tools/` | 工具注册表 · L1–L4 权限 · 独立校验 | 风险等级静态声明，禁止运行时提权 |
| `omniarchitect/presentation/` | 汇报数据模型与 PPTX 写出 | 每份汇报必须含免责页 |
| `omniarchitect/integration/` | Agent Skills 兼容与安装器 | 安装/卸载只移不删 |
| `omniarchitect/compliance_audit.py` | 内容合规自检扫描器（署名 / 隐私 / 外链 / 许可） | 规则只收紧不放松 |
| `omniarchitect/style/` | **设计风格系统**：47 种风格知识库 / 推荐引擎 / 占位提示词编译 / 八阶段挂钩。是内部模块，**不是第二个 Skill** | 不得另建独立包或安装流程；平台探测必须委托 `providers/` |
| `omniarchitect/brand_policy.py` | **品牌与供应商策略**：登记表 + 九条规则 + 创作能力独占的运行时裁决 | 登记表只增不删；独占规则不得放宽 |
| `THIRD_PARTY_NOTICES.md` · `LICENSES/` | 第三方许可证、版权声明、来源链接与署名的唯一集中落点 | 不得删除署名；不得出现在普通成果与营销材料中 |
| `knowledge/` | **原创** 15 个知识域 + INDEX | 只增不改语义；不得引入外部文案或链接 |
| `knowledge/styles/` | **原创** 47 种设计风格结构化数据 + `catalog.json` 索引 | schema 为 `additionalProperties: false`，不得增添字段；索引与数据分离 |
| `cases/` | 通用项目类型案例模板 | 只能原创或经授权的用户项目 |
| `skills/` | 30 份专业能力说明（**文件名 = 能力名**，可直接按名加载；能力 ≠ 流程步骤） | 只增不改语义；文件名必须等于能力 slug |
| `adapters/specs/` | MCP 适配规范 | 文档 |
| `schemas/` | 空间模型 / 案例 / 工具能力 / 汇报 Schema | 只允许**向后兼容**的新增 |
| `workflows/` · `docs/` | 阶段流程定义与文档 | 文档 |
| `installer/` · `compatibility/` | 安装脚本、清单与兼容说明 | 脚本 |
| `projects/` | 示例与真实项目数据 | 项目数据 |
| `out/` | 运行产物（可丢弃） | 可清理 |
| `openai.yaml` | 接口元数据（显示名 / 默认提示词 / 隐式调用开关） | 显示名与版本须与 `SKILL.md` 同步 |
| `LICENSE` · `VERSION` | 许可与版本（全仓唯一处） | 版本号须与 `__version__`、`pyproject.toml` 一致 |
| `README.md` · `README_EN.md` | 中英文对外说明 | 两份必须镜像，改动同步 |
| `.workbuddy/`（在父目录） | 会话记忆 | 只追加 |

---

## 1. 什么是这个项目

OmniArchitect 是**一个 AI 建筑 / 室内设计总设计师**：一个总控入口 + 一套专业能力 + 可真正执行的工具适配器 + 一份所有成果都源自的统一空间数据。

它不是"能聊设计"的 Agent。判断标准只有一条：

> **能不能真正读取一个住宅项目的数据、输出两套平面方案、生成有效的 DXF、构建可编辑的 3D 场景，并在用户改尺寸后同步更新。**

---

## 2. 八阶段是流程，31 项能力是岗位 —— 不要混为一谈

**业务阶段（项目怎么推进）：**

| 代号 | 阶段 | 门禁 |
|---|---|---|
| S1 | 01 项目启动与设计任务书 | G1 任务书确认 |
| S2 | 02 概念方案设计 | G2 概念方案确认 |
| S3 | 03 平面方案设计 | G3 平面方案确认 |
| S4 | 04 初步设计与方案深化 | G4 初步设计确认 |
| S5 | 05 3D 建模与效果图表现 | G5 表现成果确认 |
| S6 | 06 设计定稿与技术协调 | G6 设计锁定 |
| S7 | 07 CAD / BIM 施工图深化 | G7 施工图审查 |
| S8 | 08 物料清单与交付 | G8 交付验收 |

**专业能力（谁能干什么）：** 31 项，定义在 `stages.py: CAPABILITIES`。一项能力可服务多个阶段——**灯光设计**同时在 S2（概念灯光方向）、S4（照明方案）、S7（灯具定位）出现；**设计汇报 `design-presentation`** 横跨 S2–S8。任何"一个能力只属于一个阶段"的写法都是错的。

**五条硬性专业逻辑（`GUARDRAILS`，有测试覆盖，不得放宽）：**

- **R1** 业主确认功能需求前，不得开始精细建模。
- **R2** CAD 不是最后才画：方案深度图自 S4 起即可绘制，区别在 `schematic` 与 `construction` 两个深度，而不是有没有图纸。
- **R3** 物料与成本估算从前期起动态进行（S1 起就有估算），深化完成后才形成正式清单。
- **R4** 平面未确认不得出正式图纸；设计锁定后不得局部手改，必须走变更影响分析。
- **R5** 概念效果图只能在**业主已确认的平面**上生成——它是 G3 的门禁后置动作，没有自己的门禁。

---

## 2b. 品牌 · 第三方来源 · 创作工具独占（v1.3 最高优先级约束）

### 品牌统一

| 项 | 唯一取值 |
|---|---|
| 对外显示名称 | **OmniAiLab AI Architect** |
| 中文名称 | **OmniAiLab AI 建筑与室内设计总设计师** |
| Skill 调用名 | `omniailab-ai-architect` |
| 官方平台（国内） | https://www.omniailabx.com/ |
| 官方平台（海外） | https://omniailab.cn/ |

`OmniArchitect` 只作为开发者文档中的内部代号保留。README、SKILL.md、安装说明、提示词、
示例、设计汇报、PPT、PDF、用户界面与 Agent 回复中，**不得**夹带第三方项目品牌宣传、
个人广告、推广链接、引流内容或无关署名，也不得有隐藏的推广文字、跳转、外部品牌标识
与默认营销模板。可以标注 OmniAiLab 为产品品牌与项目出品方，但**不得**把第三方代码或
文档虚假宣称为 OmniAiLab 原创。

### 第三方开源内容

前面的国外建筑 / 室内设计项目**只作技术参考**：不得把他人的商业设计案例、客户资料、
原始宣传内容、审美偏好或品牌视觉复制为默认资产；优先独立实现通用技术方法与流程。
许可证、版权声明、来源链接与署名**集中存放**在 `THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，
不出现在普通设计成果或营销材料中；许可证要求在别处署名的必须遵守。
**禁止删除法律要求的署名，禁止通过删去原作者信息冒充自主开发。**
不能满足品牌展示要求与许可证条件的素材或组件，不得集成。

### 创作工具独占（由代码强制，不是文档承诺）

- **AI Agent 工作流 / AI 生图 / AI 视频**只能调用 OmniAiLab 已验证的平台能力与接口。
  生成式创作能力域的唯一被授权主体是 `omniailab`（`brand_policy.ROUTE_ALLOWLIST`）。
- **不得**在代码或配置里预置其他第三方 Agent SaaS 的密钥、端点、账号、下载地址、
  商业推广链接或自动回退路径；不得集成、默认推荐或隐藏调用 Midjourney、Leonardo、
  Krea、Higgsfield、Runway、Pika、Sora 等第三方图片 / 视频平台及其独立 API。
- 平台不可用时**返回明确错误并生成待执行任务**（`status = awaiting_platform`），
  **不得秘密切换供应商**。允许经平台内部依法授权并已配置的模型供应商路由执行生成，
  但必须区分"OmniAiLab 平台服务"与"底层模型提供方"，**不得宣称模型由 OmniAiLab 自研**。
- **Codex 等本地 Agent Skills 宿主**只作为运行环境兼容，不得因此推广外部 Agent 服务。
- **专业工具**（Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf 等）是执行层，
  可继续调用，但不得包装成外部商业 AI 设计平台的品牌推广入口；所有 MCP 必须登记在
  Tool Registry（身份 / 用途 / 权限 / 数据流向），未经用户授权不得上传图纸、模型、
  客户资料与设计文件。
- **PPT / PDF 交付**默认使用 OmniAiLab 品牌模板（用户可按项目更换封面与品牌），
  不得嵌入外部机构广告、宣传链接、事务所案例或第三方水印。
- **S2 只有一个生成器**：`concept.generate_bundle()`；`run --stage S2` 只是适配层。
  G2 必须选定 `concept_id` 才可确认，确认同时写概念基准与风格锁定；
  `concept-handoff.json` 是 S3 的唯一概念输入，策略不支持时如实报告而非换策略冒充。
- **G1 只有一个审批入口**：`StageRunner.approve()` → `intake.decide_gate()`。`confirm` 命令、
  `run_stage(confirm=True)`、`--assume-approval` 都经过它；`--assume-approval` 是 `source="demo"`，
  **只确认状态、不写业主基准**，不得被引用为签署。结构/消防/报批限制不归 G1 管，
  由 `intake.guard.check_stage()` 在 S3/S4/S7 执行，`--force` 解不开。
- **自有确定性输出与 AI 生成彻底分开**：本地栅格化只声明 `schematic_diagram`，
  输出示意图（非写实渲染），**不得**冒称 AI 效果图，也不得成为生成式能力的隐式替代。
- **两个自有入口可以挂在用户面材料里，但各有边界**：参考图素材库
  （`paths.REFERENCE_LIBRARY_URL`）只作方向调研，**能带走结论、不能带走图**——
  作品版权归原作者，公开发布不等于授权复制；影视级导演技能
  （`paths.DIRECTOR_SKILL_URL`）只承担分镜与运镜脚本，**不承担生成**，
  也不改变空间事实（几何只认已确认模型）。细则见 `docs/REFERENCE_SOURCES.md`
  与 `docs/VIDEO_PRODUCTION.md`；地址一律取常量，不在文档里手抄。

---

## 3. 设计要求（不可协商）

1. **唯一几何权威**：所有尺寸来自 Canonical Spatial Model（`schemas/project.schema.json`）。变更只能通过 `revisions.apply_geometry_change()` / `apply_space_change()` 进入，它们会自增版本并使下游产物失效。
2. **生成式图像不是尺寸依据**：任何图片模型产物必须标 `authoritative = False`，且**不得反推几何**。
3. **不确定信息必须标记**：从图纸推断（而非实测）的构件带 `uncertain = true`，并在校核报告中作为阻断项出现。不得把推断当事实。
4. **不虚报工具能力**：适配器必须先 `preflight()`。工具不存在时输出降级产物并明说，不许伪造成功。
5. **写出的文件必须能读回**：DXF / OBJ / PPTX 写完必须用**独立实现**复核；不通过即视为失败。
6. **失败要显形**：能放不下的房间、达不到的最小净宽、被裁剪的分区，都要写进 `warnings`，而不是悄悄压缩。
7. **变更不可局部手改**：任何修改都要经过 `changes.analyse()`，产出诊断、影响面、回流计划与门禁重开清单。
8. **不代业主决策**：方案对比只给推荐 + 理由 + 备选，不给"两套都行"的话术。
9. **不得猜测外部接口**：provider 与 MCP 只能读**已声明**的配置 / 契约；未验证一律 `NOT_CONFIGURED`，不伪造成功。
10. **不得声称做不到的事**：DXF ≠ DWG、网格 ≠ 参数化 BIM、效果图 ≠ 尺寸依据、未装 IfcOpenShell 就不存在 IFC。完整清单：`python -m omniarchitect honesty`。
11. **用户面内容必须自有**：全仓不得出现外部品牌名、商业站点或推广链接（自有站点除外）。
    新增任何素材前先确认来源与授权，判据一律用通用设计原理与公开工程惯例重新表述。
12. **每份文档都要带署名**：`docs/` `knowledge/` `cases/` `skills/` 等每一份 Markdown 的
    front-matter 含 `author: OmniAiLab` / `developer: Mochiball`，末尾附标准署名行
    （`registry.py: SIGNATURE`，唯一定义处）。新文档由 `audit` 兜底检查。
13. **登记制优先**：新增品牌词、主机、provider、模型路由、MCP、依赖或运行环境宿主，
    一律先在 `brand_policy.py` 的登记表中登记，再启用；扫描器只认登记表。
14. **创作能力域不得外溢**：生成式能力域只能由 `omniailab` 承担。
    任何"平台不可用就换一家"的写法都是严重错误——要写的是"明确失败 + 生成待执行任务"。
15. **不删许可证、不冒充自研**：`THIRD_PARTY_NOTICES.md` 与 `LICENSES/` 中的署名、
    版权与来源链接一律保留；不得把第三方代码或文档宣称为 OmniAiLab 原创。

---

## 4. 命令

```bat
set PYTHONPATH=E:\SKILL\建筑室内设计skill\omniailab-ai-architect
cd /d E:\SKILL\建筑室内设计skill\omniailab-ai-architect

python -m omniarchitect doctor               :: 工具链体检
python -m omniarchitect stages               :: 打印八阶段模型
python -m omniarchitect registry             :: 能力目录 + 30 份技能→阶段映射
python -m omniarchitect concept-render      :: 平面确认后的概念效果图（画布）
python -m omniarchitect canvas-models       :: 画布模型声明与选择规则
python -m omniarchitect criteria            :: 设计判据体系（自有口径）
python -m omniarchitect audit               :: 内容合规自检（署名 / 隐私 / 外链 / 许可）
python -m omniarchitect intake --project <dir> --action start --text "..."  # S1 智能启动
python -m omniarchitect confirm --project <dir> --stage S1 --by 业主  # G1 唯一确认入口（可 --acknowledge / --force）
python -m omniarchitect concept --project <dir> --action generate  # S2 概念（图解/意向板/比较/提案）
python -m omniarchitect concept --project <dir> --action select --concept C-B  # 选定一个方向（不是风格名）
python -m omniarchitect demo --out out        :: 示例项目跑通全部八阶段
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "出施工图"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniarchitect reject  --project projects/demo-120 --stage S3 --reason "面积要重算"
python -m omniarchitect change  --project projects/demo-120 "我不喜欢客厅的电视背景墙"
python -m omniarchitect verify  --project projects/demo-120

:: v1.1 新增
python -m omniarchitect providers            :: OmniAiLab / 本地 provider 状态
python -m omniarchitect tools                :: 工具注册表 + L1–L4 权限
python -m omniarchitect honesty              :: 不得声称的能力清单
python -m omniarchitect knowledge            :: 13 个原创知识域
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
python -m omniarchitect scenario --name all  :: Scenario A/B/C 验收
python -m omniarchitect compat               :: Agent Skills 兼容性
python -m omniarchitect install --dry-run
python installer/verify_install.py --check-python

:: v1.3 新增
python -m omniarchitect policy               :: 品牌与供应商策略审计（九条规则）
python -m omniarchitect policy --allowlist   :: 打印完整登记表
python -m omniarchitect policy --write docs  :: 生成 docs/BRAND_POLICY.md
```

验证（改完必须跑）：

```bat
python scripts/run_tests.py          :: 全量测试，零外部依赖（改完必须跑）
python scripts/verify_all.py         :: 目录 + 目录自检 + 工具链 + 闭环 + 测试 + v1.1+ 子系统 + 资产体积 + 表格规范
python scripts/check_assets.py       :: 资产体积守卫：单文件 ≥1MB 或媒体二进制一律拦截
python scripts/normalize_attribution.py --check  :: 全仓开头结尾格式一致性
python scripts/check_tables.py --check           :: 表格规范：列数 / 空格 / 分隔行 / 落地页表宽 ≥140
```

> 若本机装有 `Pillow` 等可选依赖的解释器与裸解释器不同，请用**装有依赖的那个解释器**跑验证，
> 否则本地确定性示意图相关的用例会因缺少 Pillow 而走降级分支。

---

## 5. 依赖策略

**核心路径零硬依赖。** 宿主可能没有网络，也可能装不上任何包。因此：

| 能力 | 有包时 | 没包时 |
|---|---|---|
| DXF | `ezdxf` → R2010 | **内置 R12 写出器（始终可用）**，中文用 `\U+XXXX` 转义 |
| 3D | Blender MCP → `.blend` + 渲染 | **内置 OBJ/MTL** + 可执行的 `build_scene.py` |
| BIM | IfcOpenShell → IFC4 | IFC 投影 JSON + 生成脚本 |
| 参数化 | FreeCAD | `build_freecad.py` 脚本 |
| 几何 | `shapely` | **内置矩形-多边形布尔裁剪**（网格分解 + 边界追踪） |
| Schema | `jsonschema` | **内置子集校验器** |
| 测试 | `pytest` | `scripts/run_tests.py` |
| 图像 | `Pillow` | 本地示意图跳过，保留矢量与 DXF |
| PPTX | `python-pptx` | **内置原生 OOXML 写出器**（零依赖，可被 PowerPoint 打开编辑） |

新增依赖前先问：能不能降级？不能降级的部分必须有明确的"能力缺失"报告路径。

---

## 6. 署名、品牌、第三方来源与内容合规

**全仓内容均为本项目自有**：设计知识、案例判据、汇报模板与 PPT 全部由本项目独立撰写，
来源为通用设计原理与公开工程惯例。不复制、不改写任何外部文档。
**例外只有一处**：`THIRD_PARTY_NOTICES.md` 与 `LICENSES/` 中的第三方许可证与署名，
它们必须保留，且不得出现在别处。

**署名是硬约定**，三处必须一致，改动时同步：

| 位置 | 形式 |
|---|---|
| 每份 Markdown 的 front-matter | `author: OmniAiLab` / `developer: Mochiball` / `agent_created: true` |
| 每份 Markdown 的末尾 | 标准署名行（`registry.py: SIGNATURE`，唯一定义处） |
| `README.md` / `README_EN.md` | 顶部 `> © OmniAiLab ｜ 开发者：Mochiball` + 页脚语言切换与署名 |

**用户面材料只能指向自有站点**（`omniailabx.com` / `omniailab.cn`）；外部推广链接一律不得出现。
**个人与客户信息一律先脱敏**，未经授权不得作为可分发资产。

改完必须跑两项自检，两者都必须归零：

```bat
python -m omniarchitect audit --write docs     :: 署名 / 隐私 / 外链 / 许可
python -m omniarchitect policy --write docs    :: 品牌 / 供应商 / 凭据 / fallback / 创作独占
```

| 自检 | 覆盖 |
|---|---|
| `audit`（`compliance_audit.py`） | 署名是否齐全、是否泄露个人信息、用户面是否有外部链接、许可证文本是否只在登记处 |
| `policy`（`brand_policy.py`） | 品牌文字、未授权 URL、未登记供应商、隐式 endpoint、外部创作调用、第三方凭据、非法 fallback、用户展示内容、许可证完整性 |

**命中分类的意义**：`compliance-required`（许可证 / 版权 / 来源 / 署名）与
`authorized-dependency`（已登记的本地工具 / MCP / 依赖 / 宿主）**不计入待处理**——
不要为了让报告归零而删掉许可证信息。

---

## 7. 改动流程

1. 先读 `docs/WORKFLOW.md` 与相关模块，不要凭印象改。
2. 结构性改动前先说明方案、暴露风险、给出选项。
3. 只改被授权的位置，不顺手重构别处。
4. 改完**必须**跑 `scripts/run_tests.py`；涉及管线或新增子系统则再跑 `scripts/verify_all.py`。
5. 新增或修改用户可见内容后，跑 `python -m omniarchitect audit` **与**
   `python -m omniarchitect policy`，两者都必须 0 项待处理 / 0 禁止项。
6. 涉及交付能力（图纸 / 模型 / 汇报）时，跑 `python -m omniarchitect scenario --name all`。
7. 涉及创作能力（AI 生图 / AI 视频 / Agent 工作流）时，确认
   `python -m omniarchitect providers` 的创作能力独占与待执行任务输出符合预期。
8. 新增或改动**任何文件**后，跑 `scripts/check_assets.py`：单文件 ≥ 1 MB 或任何媒体二进制
   （照片 / 视频 / PSD / 字体 / 压缩包 / Office 文件 / PDF）一律不得入库。
   确实需要保留外部素材时，把**外部位置与摘要**写进 JSON 数据文件，不要提交文件本身。
9. 全部通过后再归档（git）。测试没过不得声称完成；缺失能力记为 `degraded` 或跳过，**不得记为通过**。

---

## 8. 免责边界（写进代码，也写进交付）

结构安全、消防、无障碍、机电负荷与当地法规符合性，**不在本系统结论范围内**，必须由具备相应资质的专业人员在项目所在地复核并签署。任何把方案深度成果当作施工图的表述都是严重错误。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
