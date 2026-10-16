---
name: omniailab-agents-conventions
description: 开发约定 —— 唯一项目根、目录职责、9 条硬性规则、命令清单与改动流程
version: 1.1.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
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
- Python 包是根目录下的子目录 `omniailab_ai_architect/`：目录名可导入，根目录名含连字符不可导入。
- 运行任何命令前，先把工作区切到该目录；不要依赖提示词里写路径。

```bat
cd /d E:\SKILL\建筑室内设计skill\omniailab-ai-architect
set PYTHONPATH=E:\SKILL\建筑室内设计skill\omniailab-ai-architect
python -m omniailab_ai_architect doctor
```

- 父目录 `E:\SKILL\建筑室内设计skill\.workbuddy\` 存放会话记忆，**不属于本仓库，不得删除或改写**。
- 所有工作文件、脚本、缓存、临时产物都必须落在本目录内。禁止在 `C:\`、桌面、Home 或其它盘另建项目副本。

### 目录职责

| 路径 | 内容 | 可否改动 |
|---|---|---|
| `omniailab_ai_architect/` | Python 包：模型、规划、工作流、适配器、provider、工具、汇报、集成 | 主开发区 |
| `omniailab_ai_architect/stages.py` | **八阶段模型、能力映射与门禁后置动作的唯一权威** | 改前先读 `docs/WORKFLOW.md` |
| `omniailab_ai_architect/changes.py` | 设计变更影响分析 | 核心能力，改前先读 `docs/WORKFLOW.md` 第三节 |
| `omniailab_ai_architect/providers/` | 生成式 provider（OmniAiLab + 本地）+ 画布工作流 `canvas.py` | 不得猜测 endpoint / 鉴权 / 模型名 |
| `omniailab_ai_architect/tools/` | 工具注册表 · L1–L4 权限 · 独立校验 | 风险等级静态声明，禁止运行时提权 |
| `omniailab_ai_architect/presentation/` | 汇报数据模型与 PPTX 写出 | 每份汇报必须含免责页 |
| `omniailab_ai_architect/integration/` | Agent Skills 兼容与安装器 | 安装/卸载只移不删 |
| `omniailab_ai_architect/compliance_audit.py` | 内容合规自检扫描器（署名 / 隐私 / 外链 / 许可） | 规则只收紧不放松 |
| `knowledge/` | **原创** 12 个知识域 + INDEX | 只增不改语义；不得引入外部文案或链接 |
| `cases/` | 通用项目类型案例模板 | 只能原创或经授权的用户项目 |
| `skills/` | 29 份专业能力说明书 + 画布概念效果图（30 项能力，非流程步骤） | 只增不改语义 |
| `adapters/specs/` | MCP 适配规范 | 文档 |
| `schemas/` | 空间模型 / 案例 / 工具能力 / 汇报 Schema | 只允许**向后兼容**的新增 |
| `workflows/` · `docs/` | 阶段流程定义与文档 | 文档 |
| `installer/` · `compatibility/` | 安装脚本、清单与兼容说明 | 脚本 |
| `projects/` | 示例与真实项目数据 | 项目数据 |
| `out/` | 运行产物（可丢弃） | 可清理 |
| `LICENSE` · `VERSION` | 许可与版本（全仓唯一处） | 版本号须与 `__version__`、`pyproject.toml` 一致 |
| `README.md` · `README_EN.md` | 中英文对外说明 | 两份必须镜像，改动同步 |
| `.workbuddy/`（在父目录） | 会话记忆 | 只追加 |

---

## 1. 什么是这个项目

OmniArchitect 是**一个 AI 建筑 / 室内设计总设计师**：一个总控入口 + 一套专业能力 + 可真正执行的工具适配器 + 一份所有成果都源自的统一空间数据。

它不是"能聊设计"的 Agent。判断标准只有一条：

> **能不能真正读取一个住宅项目的数据、输出两套平面方案、生成有效的 DXF、构建可编辑的 3D 场景，并在用户改尺寸后同步更新。**

---

## 2. 八阶段是流程，30 项能力是岗位 —— 不要混为一谈

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

**专业能力（谁能干什么）：** 30 项，定义在 `stages.py: CAPABILITIES`。一项能力可服务多个阶段——**灯光设计**同时在 S2（概念灯光方向）、S4（照明方案）、S7（灯具定位）出现；**设计汇报 `design-presentation`** 横跨 S2–S8。任何"一个能力只属于一个阶段"的写法都是错的。

**四条硬性专业逻辑（`GUARDRAILS`，有测试覆盖，不得放宽）：**

- **R1** 业主确认功能需求前，不得开始精细建模。
- **R2** CAD 不是最后才画：方案深度图自 S4 起即可绘制，区别在 `schematic` 与 `construction` 两个深度，而不是有没有图纸。
- **R3** 物料与成本估算从前期起动态进行（S1 起就有估算），深化完成后才形成正式清单。
- **R4** 平面未确认不得出正式图纸；设计锁定后不得局部手改，必须走变更影响分析。

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
10. **不得声称做不到的事**：DXF ≠ DWG、网格 ≠ 参数化 BIM、效果图 ≠ 尺寸依据、未装 IfcOpenShell 就不存在 IFC。完整清单：`python -m omniailab_ai_architect honesty`。
11. **用户面内容必须自有**：全仓不得出现外部品牌名、商业站点或推广链接（自有站点除外）。
    新增任何素材前先确认来源与授权，判据一律用通用设计原理与公开工程惯例重新表述。
12. **每份文档都要带署名**：`docs/` `knowledge/` `cases/` `skills/` 等每一份 Markdown 的
    front-matter 含 `author: OmniAiLab` / `developer: Mochiball`，末尾附标准署名行
    （`registry.py: SIGNATURE`，唯一定义处）。新文档由 `audit` 兜底检查。

---

## 4. 命令

```bat
set PYTHONPATH=E:\SKILL\建筑室内设计skill
cd /d E:\SKILL\建筑室内设计skill\omniarchitect

python -m omniailab_ai_architect doctor               :: 工具链体检
python -m omniailab_ai_architect stages               :: 打印八阶段模型
python -m omniailab_ai_architect registry             :: 能力目录 + 29 份技能→阶段映射
python -m omniailab_ai_architect concept-render      :: 平面确认后的概念效果图（画布）
python -m omniailab_ai_architect canvas-models       :: 画布模型声明与选择规则
python -m omniailab_ai_architect criteria            :: 设计判据体系（自有口径）
python -m omniailab_ai_architect audit               :: 内容合规自检（署名 / 隐私 / 外链 / 许可）
python -m omniailab_ai_architect demo --out out        :: 示例项目跑通全部八阶段
python -m omniailab_ai_architect status  --project projects/demo-120
python -m omniailab_ai_architect route   --project projects/demo-120 "出施工图"
python -m omniailab_ai_architect run     --project projects/demo-120 --from-stage S3
python -m omniailab_ai_architect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniailab_ai_architect reject  --project projects/demo-120 --stage S3 --reason "面积要重算"
python -m omniailab_ai_architect change  --project projects/demo-120 "我不喜欢客厅的电视背景墙"
python -m omniailab_ai_architect verify  --project projects/demo-120

:: v1.1 新增
python -m omniailab_ai_architect providers            :: OmniAiLab / 本地 provider 状态
python -m omniailab_ai_architect tools                :: 工具注册表 + L1–L4 权限
python -m omniailab_ai_architect honesty              :: 不得声称的能力清单
python -m omniailab_ai_architect knowledge            :: 12 个原创知识域
python -m omniailab_ai_architect present --project projects/demo-120 --kind plan-comparison
python -m omniailab_ai_architect scenario --name all  :: Scenario A/B/C 验收
python -m omniailab_ai_architect compat               :: Agent Skills 兼容性
python -m omniailab_ai_architect install --dry-run
python installer/verify_install.py --check-python
```

验证（改完必须跑）：

```bat
python scripts/run_tests.py          :: 164 项测试，零外部依赖
python scripts/verify_all.py         :: 目录 + 目录自检 + 工具链 + 闭环 + 测试 + v1.1 子系统
```

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

## 6. 署名、归属与内容合规

**全仓内容均为本项目自有**：设计知识、案例判据、汇报模板与 PPT 全部由本项目独立撰写，
来源为通用设计原理与公开工程惯例。不复制、不改写任何外部文档。

**署名是硬约定**，三处必须一致，改动时同步：

| 位置 | 形式 |
| --- | --- |
| 每份 Markdown 的 front-matter | `author: OmniAiLab` / `developer: Mochiball` / `agent_created: true` |
| 每份 Markdown 的末尾 | 标准署名行（`registry.py: SIGNATURE`，唯一定义处） |
| `README.md` / `README_EN.md` | 顶部 `> © OmniAiLab ｜ 开发者：Mochiball` + 页脚语言切换与署名 |

**用户面材料只能指向自有站点**（`omniailabx.com` / `omniailab.cn`）；外部推广链接一律不得出现。
**个人与客户信息一律先脱敏**，未经授权不得作为可分发资产。

改完必须跑自检，`action_count` 必须为 0：

```bat
python -m omniailab_ai_architect audit --write docs
```

自检覆盖四件事：**署名是否齐全**、**是否泄露个人信息**、**用户面是否有外部链接**、**许可证文本是否只在 LICENSE 内**。

---

## 7. 改动流程

1. 先读 `docs/WORKFLOW.md` 与相关模块，不要凭印象改。
2. 结构性改动前先说明方案、暴露风险、给出选项。
3. 只改被授权的位置，不顺手重构别处。
4. 改完**必须**跑 `scripts/run_tests.py`；涉及管线或新增子系统则再跑 `scripts/verify_all.py`。
5. 新增或修改用户可见内容后，跑 `python -m omniailab_ai_architect audit`，必须 0 项待处理。
6. 涉及交付能力（图纸 / 模型 / 汇报）时，跑 `python -m omniailab_ai_architect scenario --name all`。
7. 全部通过后再归档（git）。测试没过不得声称完成；缺失能力记为 `degraded` 或跳过，**不得记为通过**。

---

## 8. 免责边界（写进代码，也写进交付）

结构安全、消防、无障碍、机电负荷与当地法规符合性，**不在本系统结论范围内**，必须由具备相应资质的专业人员在项目所在地复核并签署。任何把方案深度成果当作施工图的表述都是严重错误。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
