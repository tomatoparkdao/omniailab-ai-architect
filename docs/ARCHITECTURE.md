---
name: omniailab-architecture
description: 系统架构 —— 阶段负责推进节奏，能力负责专业方法，适配器负责操作软件，模型负责记住一切
version: 1.3.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 系统架构

```
入口层      Chief Designer（CLI / 智能体）  理解项目 · 规划阶段 · 分配能力 · 检查成果 · 协调修改
            ────────────────────────────────────────────────────────────────
阶段层      八阶段状态机（workflow.py + stage_state.py）  门禁 · 确认 · 返工 · 变更回流
            ────────────────────────────────────────────────────────────────
能力层      30 项专业能力（stages.py + skills/）  判断与做法，不做工具调用
            ────────────────────────────────────────────────────────────────
数据层      Canonical Spatial Model（model.py + schemas/）  唯一权威几何与编号
            ────────────────────────────────────────────────────────────────
执行层      适配器（adapters/）  DXF · MESH · Blender · FreeCAD · IFC · Render
            ────────────────────────────────────────────────────────────────
交付层      PDF/DXF/OBJ/IFC/JSON/图片  版本化清单 · 校核报告 · 未闭环项
```

核心分工：**阶段负责推进节奏，能力负责专业方法，适配器负责操作软件，模型负责记住一切。**

---

## 模块职责

| 模块 | 职责 | 关键约束 |
|---|---|---|
| `model.py` | Canonical Spatial Model：Level / Space / Element / Artifact / ChangeEntry | 单位恒为 mm；每个对象有稳定 `id`、`source`、`revision` |
| `geometry.py` | 多边形运算、墙体轮廓、净距检查 | 有 shapely 用 shapely，无则用内置矩形布尔裁剪 |
| `planner.py` | 由任务书 + 外壳生成两套平面方案 | 房间必须全部放得下；放不下要报警而不是静默丢弃 |
| `revisions.py` | 版本与依赖失效 | 唯一允许的几何修改入口；失效沿依赖图传递 |
| `changes.py` | 变更影响分析 | 饰面变更不碰几何；几何变更连带全部下游 |
| `stages.py` | 八阶段模型 + 能力映射 | 阶段与能力多对多；四条硬逻辑有测试 |
| `stage_state.py` | 阶段状态机 | 状态持久化，可跨会话恢复 |
| `routing.py` | 请求 → 阶段计划 | 规则化、可测试，不用模型黑箱决策 |
| `workflow.py` | 阶段执行器 | 每个阶段先检门禁；产物进各自目录 |
| `quantities.py` | 工程量 / 材料表 / 估算 | 无平面时按轮廓+任务书估，并声明基数 |
| `compliance.py` | 几何与规范初审 | 只做可量化项；明确声明不是审批 |
| `registry.py` | 能力目录 + 第三方融合与归属 | 上游仓库只读 |
| `adapters/` | 工具执行 | 先 `preflight()`；写出的文件必须能读回 |

---

## 为什么所有成果必须来自同一套数据

假设设计师在方案阶段把客厅一面墙向外移动 300mm：

```
客厅墙体 +300mm
   ├── 更新空间对象 ID、几何尺寸与项目修订版本
   ├── 平面布置图更新
   ├── BIM / 3D 模型更新
   ├── 立面与剖面更新
   ├── 吊顶与灯位复核
   ├── 家具尺寸与间距复核
   ├── 材料工程量重算
   ├── 效果图重新生成
   └── 施工图更新与校核
```

不是让九个能力各自重新理解一次用户的要求，而是**九个能力读取同一份已经更新的空间数据，各自重新执行一次**。这就是 `revisions.invalidate()` 与 `changes.analyse()` 存在的理由。

**推论：AI 效果图不能天然保证精确尺寸。** 因此施工图从经校核的几何 / BIM 模型生成，绝不从一张漂亮的效果图反推。

---

## 适配器契约

```python
class Adapter:
    def preflight(self) -> Capability: ...   # 这个宿主上，我现在到底能不能干活？
```

`Capability` 必须回答：是否存在、版本、可执行文件、支持哪些操作、缺什么、降级成什么。

| 适配器 | 有工具时 | 无工具时（降级） |
|---|---|---|
| `dxf` | ezdxf → R2010 | **内置 R12 写出器**（始终可用） |
| `mesh` | —— | 始终可用：纯 Python OBJ/MTL |
| `blender` | `blender -b -P` 建场景 + 渲染 | `snapshot.json` + 可执行的 `build_scene.py` |
| `freecad` | `FreeCADCmd` 参数化重建 | `build_freecad.py` |
| `ifc` | IfcOpenShell → IFC4 | IFC 投影 JSON + 生成脚本 |
| `render` | 图片模型后端 | 完整的机位/材质/光线/提示词任务包 |

**降级不是失败，是如实交付。** 但"伪造成功"是绝对禁止的：工具不存在却报告渲染完成，属于严重缺陷。

---

## 写-读回原则

所有写文件的适配器都必须能把自己写的东西读回来：

- DXF：`read_r12()` 独立解析（或 `ezdxf.recover`），检查 ENTITIES 段、实体数、A-WALL 图层
- OBJ：解析顶点/面、包围盒、单位尺度
- IFC：重新打开并统计 `IfcWallStandardCase`

**读不回来 = 交付失败**，不是"导出完成"。

---

## 依赖策略

核心路径零硬依赖，因为宿主可能没有网络，也可能装不上包。

| 能力 | 有包 | 无包 |
|---|---|---|
| 几何布尔 | shapely | 网格分解 + 边界追踪（矩形-多边形精确） |
| Schema 校验 | jsonschema | 内置子集校验器 |
| DXF | ezdxf | 内置 R12 |
| 测试 | pytest | `scripts/run_tests.py` |

新增依赖前先问：能不能降级？不能降级的部分必须有明确的能力缺失报告路径。

---

## 已知边界（不做的事）

1. 不做法规判定。结构、消防、无障碍、机电负荷与当地法规符合性由持证专业人员复核签署。
2. 不做自动出图审批。系统给初审清单与待办，不给结论。
3. 不用生成式图像反推几何。
4. 不代业主决策：方案对比给推荐 + 理由 + 备选，不给"两套都行"。
5. 不自动连接互联网或上传项目数据。

## v1.1 增量（本次新增的子系统）

| 子系统 | 模块 | 职责 |
|---|---|---|
| 内容合规 | `compliance_audit.py` | 逐文件检查署名 / 隐私 / 外链 / 许可；用户面材料只能指向自有站点；署名行由 `registry.py: SIGNATURE` 统一定义 |
| 原创知识库 | `knowledge/` + `knowledge/loader.py` | 13 个知识域，索引 → 领域 → 单节的渐进式加载，带加载成本上限 |
| 平台 provider | `providers/` | OmniAiLab 发现式接入（SDK / 配置 / API 契约）+ 内置本地确定性 provider；未验证一律 `NOT_CONFIGURED` |
| 概念效果图 | `providers/canvas.py` | **门禁 G3 后置动作**：以已确认平面为据，走 OmniAiLab 画布（推荐 OmniP / image2.5）出概念效果图；平台未连接时只交付任务包 |
| 工具执行 | `tools/` | 统一工具注册表、L1–L4 权限分级、产物独立校验、能力真实性规则 |
| 设计汇报 | `presentation/` | 汇报数据模型 → PPTX / Markdown / HTML / PDF；两个写出后端，写出后独立复核 |
| 独立运行 | `integration/` | Agent Skills 契约校验、运行环境探测、只移不删的安装器 |
| 验收 | `scenarios.py` | Scenario A/B/C 端到端验收，含"文件真实存在 / 格式有效 / 与项目关联 / 可追溯 / 可重复 / 未伪造"六项口径 |

### v1.2 增量（概念效果图）

| 位置 | 内容 |
|---|---|
| `providers/canvas.py` | 画布工作流：机位规划、提示词组装、参考图栅格化、逐机位提交与状态登记、汇报落盘 |
| `providers/omniailab.models.json` | 画布模型声明：OmniP / image2.5 的取向与选择规则；与平台契约交叉校验，冲突时以契约为准 |
| `stages.py` | `POST_GATE_ACTIONS = {"G3": ["concept-visualization"]}` + 能力 `concept-visualization` + 铁律 R5 |
| `workflow.py` | 门禁后置动作分发（`run_post_gate`）；在 fork 上渲染，不改动统一空间模型与修订号 |
| `schemas/concept-render.schema.json` | 画布任务包结构；状态三态（generated / awaiting_platform / failed） |
| `presentation/` | 新增汇报类型 `concept-rendering`：逐机位一页，含模型、状态与提示词指纹 |

**为什么不是第九个阶段**：概念效果图没有自己的门禁，也不该有——它的成立条件完全由 G3 决定。
把门禁后置动作建成独立阶段，会诱导使用者"单独确认"这一步，从而绕过平面确认。

### 三条新铁律

1. **外部接口只读已声明的配置与契约**，不猜测 endpoint、参数与鉴权。
2. **产物只能按能力上限命名**：DXF ≠ DWG，网格 ≠ 参数化 BIM，效果图 ≠ 尺寸依据。
3. **缺失能力记为 `degraded` 或跳过**，绝不以 Mock 通过宣称生产功能可用。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
