# OmniArchitect

**AI 建筑 / 室内设计总设计师** — 八阶段专业工作流 · 29 项专业能力 · 可真正执行的工具适配器 · 一份统一空间数据 · 可编辑 PPTX 交付

产品生态：**OmniAiLab**（[国内站](https://www.omniailabx.com) · [海外站](https://omniailab.cn)）

> 判断这个项目是否成立的唯一标准：
> 能不能真正读取一个住宅项目的数据、输出两套平面方案、生成**有效的 DXF**、构建**可编辑的 3D 场景**，
> 并在用户改尺寸后**同步更新**，最后产出**可编辑的设计提案 PPTX**。
> 不是"能聊设计"。

---

## 它做什么

| | |
|---|---|
| **业务阶段** | 八阶段：任务书 → 概念 → 平面 → 初步设计 → 表现 → 定稿 → 施工图 → 交付，每阶段带人工确认门禁 |
| **专业能力** | 29 项，可跨阶段调用（灯光设计同时服务概念、初步设计与灯具定位；设计汇报横跨 S2–S8） |
| **工具执行** | DXF（内置 R12 写出器 + ezdxf）、OBJ/MTL、Blender 脚本、IFC、FreeCAD 脚本 |
| **变更管理** | 诊断 → 影响面 → 回流计划 → 门禁重开；几何变更全局失效重算，饰面变更不动几何 |
| **质量门** | 几何、人体工学、采光、规范初审；不确定构件一律阻断 |
| **设计汇报** | 9 种汇报类型，输出可编辑 PPTX / Markdown / 打印就绪 HTML / PDF（有渲染器时） |
| **平台能力** | OmniAiLab 原生 provider（发现式接入）+ 内置本地确定性 provider；不联网也能出图 |
| **合规** | 可执行的第三方内容审计；署名义务集中在 `THIRD_PARTY_NOTICES.md` |

## 快速开始

```bash
cd "E:\SKILL\建筑室内设计skill\omniailab-ai-architect"

python -m omniailab_ai_architect doctor                 # 本机工具链体检
python -m omniailab_ai_architect demo --out out         # 生成示例项目并跑通全部八阶段
python -m omniailab_ai_architect scenario --name all    # 验收：Scenario A/B/C
python scripts/verify_all.py                            # 目录 + 闭环 + 测试 + v1.1 子系统
```

**不需要安装任何包，不需要联网，不需要注册平台账号。**
`doctor` 会告诉你哪些工具缺失，以及每一项的降级方案。

## 一次真实运行的样子

```
[ok] 01 项目启动与设计任务书   任务书 11 项功能，合计 103.0 m²
                            3 个构件标记为须现场核对
                            前期估算 179,984–546,356 CNY（R3：前期就开始算）
[ok] 02 概念方案设计          2 个概念方向 + 意向板骨架 + 概念层照明方向
[ok] 03 平面方案设计          2 套平面方案 + 对比分析 + 造价影响
                            方案深度 DXF 已生成并审计通过
[ok] 04 初步设计与方案深化     顶墙地做法 + 材料色彩体系 + 灯光 + 机电初步
                            方案深度图纸（R2：CAD 不是最后才画）
[ok] 05 3D 建模与效果图表现    可编辑 3D 模型（mm，Z 向上）
                            5 个机位任务（同一几何、同一材质、同一光线）
[degraded] 06 设计定稿与技术协调  校核阻断/提示数 + 设计基线锁定
                            （有构件为图纸推断，须现场核对——系统在正确工作）
[ok] 07 CAD / BIM 施工图深化   三张施工图深度 DXF，逐张审计通过
[ok] 08 物料清单与交付        工程量 + 材料表 + 全套交付文件
```

## 变更影响分析（核心能力）

```
输入：我不喜欢客厅的电视背景墙

一、诊断
  判定领域：立面与造型（置信度 95%）
  落点阶段：04 初步设计与方案深化
  是否改变几何：否
  处理原则：只改该立面的分缝、比例与材料，平面与结构不动

二、影响范围   空间 SA-LIVING，构件 2 个，成果 6 项
三、保持不变   art-delivery / art-materials / art-freeze …
四、回流计划   S4 做法 → S5 重出图 → S6 重审定 → S7 重出图 → S8 重算量
五、需重新确认 初步设计确认 / 表现成果确认 / 设计锁定 / 施工图审查 / 交付验收
```

对比一下几何变更：

```
输入：把厨房和餐厅之间的墙往外移 300mm
  判定领域：平面尺寸与墙体　落点 S3　改变几何：是
  回流：S3 → S8（平面的一切推论全部重来）
```

**饰面变更不碰几何，几何变更一定连带全部下游。** 这条规则有测试守着。

## 三条最容易被搞错的专业逻辑

1. **概念与平面可交互迭代，但业主确认功能需求前不得开始精细建模。**
2. **CAD 不是最后才画**——方案深度图自初步设计（S4）起就画，区别在 `schematic` 与 `construction` 两个深度，不是有没有图纸。
3. **成本估算从前期就动态进行**（S1 起就有估算），深化完成后才形成正式清单。

## 设计汇报与 PPT

```bash
python -m omniailab_ai_architect present --list-kinds
python -m omniailab_ai_architect present --project projects/demo-120 --kind plan-comparison
```

| kind | 阶段 | 用途 |
| --- | --- | --- |
| `concept` | S2 | 概念设计提案 |
| `plan-comparison` | S3 | 平面方案比选 |
| `preliminary` / `materials-lighting` | S4 | 初步设计 / 材料与照明专项 |
| `visual` | S5 | 视觉表现汇报 |
| `final` | S6 | 设计定稿确认 |
| `technical-briefing` | S7 | 施工图技术交底 |
| `delivery` | S8 | 交付与物料清单 |
| `full` | — | 全过程汇报 |

两个写出后端：`python-pptx`（主）与内置 **原生 OOXML** 写出器（零依赖兜底），
写出后必定用独立实现重新打开校验。PDF 只在检测到真实渲染器时生成，**从不伪造**。
每份汇报**必须**含免责与边界页，否则不允许提交。

## 平台与工具状态（如实报告）

| 能力 | 当前状态 | 缺失时的行为 |
| --- | --- | --- |
| DXF / 网格 | ✅ 可用（内置 + ezdxf） | — |
| 本地示意图 | ✅ 可用（Pillow） | 标注"非写实渲染，不得作为尺寸依据" |
| Blender / FreeCAD / IfcOpenShell | ⚠️ 本机未安装 | 输出可在有环境的机器上直接运行的脚本，阶段标 `degraded` |
| OmniAiLab provider | ⚠️ `NOT_CONFIGURED` | 列出**具体缺什么**；表现图任务包照常生成 |
| 写实效果图 | ⚠️ 待平台接入 | Scenario B 记为**跳过**，不记为通过 |

接入方式见 [`docs/OMNIAILAB_INTEGRATION.md`](docs/OMNIAILAB_INTEGRATION.md)。

## 独立安装

```bash
python installer/install.py --dry-run
python installer/install.py                                    # 自动选择已检测到的运行环境
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

安装与卸载**都不删除内容**：目标已存在时先移入 `_backup/`。
支持 WorkBuddy / Codex / Cursor / Claude Code / 通用 Agent Skills 目录（探测决定，不假设）。
详见 [`docs/INSTALL.md`](docs/INSTALL.md)。

## 目录

```
SKILL.md                Agent Skills 入口（渐进式加载）
README.md               本文件
AGENTS.md               开发约定（AI 智能体必读）
THIRD_PARTY_NOTICES.md  第三方声明与许可义务（唯一集中处）
CHANGELOG.md            版本记录

omniailab_ai_architect/ Python 包
  stages.py             八阶段模型 + 能力映射（唯一权威）
  changes.py            设计变更影响分析
  model.py              Canonical Spatial Model
  planner.py            平面方案生成（两种分区策略）
  workflow.py           阶段状态机
  quantities.py / compliance.py / revisions.py / routing.py
  adapters/             DXF · MESH · Blender · FreeCAD · IFC · Render
  providers/            OmniAiLab provider + 本地确定性 provider
  tools/                统一工具注册表 · L1–L4 权限 · 产物独立校验
  presentation/         汇报数据模型 · PPTX/HTML/MD 写出
  knowledge/            知识库渐进式加载器
  integration/          Agent Skills 兼容 · 安装器
  scenarios.py          Scenario A/B/C 验收
  tests/                164 项测试

knowledge/              12 个原创知识域 + INDEX（约 2 480 行）
cases/                  3 个通用项目类型案例模板
skills/                 29 份专业能力说明书
schemas/                空间模型 / 案例 / 工具能力 / 汇报
workflows/              阶段流程定义
adapters/specs/         MCP 与外部工具适配规范
docs/                   ARCHITECTURE · WORKFLOW · OMNIAILAB_INTEGRATION ·
                        MCP_TOOLS · PRESENTATION · INSTALL ·
                        ARCH_SKILLS_INTEGRATION · THIRD_PARTY_AUDIT
installer/              install.py · verify_install.py · manifest.json
compatibility/          agent-skills · codex · mcp 示例
projects/demo-120/      示例项目（131.6 m² 三居，含 3 处待现场核对）
out/                    运行产物（不入库）
third_party/            上游研究方法副本（原样保留）

scripts/run_tests.py    零依赖测试运行器
scripts/verify_all.py   目录 + 目录自检 + 工具链 + 闭环 + 测试 + v1.1 子系统
```

## 归属

第三方声明与全部署名义务集中在 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
上游研究方法副本原样保留在 `third_party/` 下（不修改、不并入本仓库历史）；
被吸收的是设计判据与流程口径，融合明细见 [`docs/ARCH_SKILLS_INTEGRATION.md`](docs/ARCH_SKILLS_INTEGRATION.md)。
面向用户的设计知识体系（`knowledge/`）与案例体系（`cases/`）为**完全原创**，不依赖任何第三方文档。

合规状态由代码扫描而非人工承诺：

```bash
python -m omniailab_ai_architect audit      # 扫描通过即视为交付前提
python -m omniailab_ai_architect notices
```

## 边界

结构安全、消防、无障碍、机电负荷与当地法规符合性**不在本系统结论范围内**，须由持证专业人员在项目所在地复核签署。
方案深度成果不得当作施工图使用；生成式图像不得作为尺寸依据；工程量与造价为方案阶段估算，不构成结算依据。
