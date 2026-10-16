# AGENTS.md — OmniArchitect 开发约定

> **本文件约束所有在本仓库中工作的 AI 智能体与开发者。**
> 它说明项目在哪、怎么跑、什么不能改、以及什么绝对不能假装做到。

---

## 0. 项目根目录（唯一）

```
E:\SKILL\建筑室内设计skill\omniarchitect
```

- 这是**唯一**的正式开发根目录。Python 包名即 `omniarchitect`，包目录就是本目录本身。
- 运行任何命令前，先把工作区切到该目录；不要依赖提示词里写路径。
- 从**父目录**导入本包（`E:\SKILL\建筑室内设计skill` 需在 `sys.path` 上）：

```bat
cd /d E:\SKILL\建筑室内设计skill\omniarchitect
set PYTHONPATH=E:\SKILL\建筑室内设计skill
python -m omniarchitect doctor
```

- 父目录 `E:\SKILL\建筑室内设计skill\.workbuddy\` 存放会话记忆，**不属于本仓库，不得删除或改写**。
- 所有工作文件、脚本、缓存、临时产物都必须落在本目录内。禁止在 `C:\`、桌面、Home 或其它盘另建项目副本。

### 目录职责

| 路径 | 内容 | 可否改动 |
|---|---|---|
| `omniarchitect/`（即本目录） | Python 包：模型、规划、工作流、适配器、CLI | 主开发区 |
| `stages.py` | **八阶段模型与能力映射的唯一权威** | 改前先读 `docs/WORKFLOW.md` |
| `changes.py` | 设计变更影响分析 | 核心能力，改前先读 `docs/WORKFLOW.md` 第三节 |
| `skills/` | 18 份专业能力说明书（岗位能力，非流程步骤） | 只增不改语义 |
| `adapters/specs/` | 4 份 MCP 适配规范 | 文档 |
| `schemas/project.schema.json` | 统一空间模型 Schema | 只允许**向后兼容**的新增 |
| `workflows/interior-full.yaml` | 阶段流程定义 | 文档 |
| `projects/` | 示例与真实项目数据 | 项目数据 |
| `out/` | 运行产物（可丢弃） | 可清理 |
| `third_party/arch-skills/` | 上游参考仓库，**原样保留** | **禁止修改** |
| `.workbuddy/`（在父目录） | 会话记忆 | 只追加 |

---

## 1. 什么是这个项目

OmniArchitect 是**一个 AI 建筑 / 室内设计总设计师**：一个总控入口 + 一套专业能力 + 可真正执行的工具适配器 + 一份所有成果都源自的统一空间数据。

它不是"能聊设计"的 Agent。判断标准只有一条：

> **能不能真正读取一个住宅项目的数据、输出两套平面方案、生成有效的 DXF、构建可编辑的 3D 场景，并在用户改尺寸后同步更新。**

---

## 2. 八阶段是流程，18 项能力是岗位 —— 不要混为一谈

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

**专业能力（谁能干什么）：** 27 项，定义在 `stages.py: CAPABILITIES`。一项能力可服务多个阶段——**灯光设计**同时在 S2（概念灯光方向）、S4（照明方案）、S7（灯具定位）出现。任何"一个能力只属于一个阶段"的写法都是错的。

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
5. **写出的文件必须能读回**：DXF 写完必须用独立解析器复核；OBJ 写完必须复解；不通过即视为失败。
6. **失败要显形**：能放不下的房间、达不到的最小净宽、被裁剪的分区，都要写进 `warnings`，而不是悄悄压缩。
7. **变更不可局部手改**：任何修改都要经过 `changes.analyse()`，产出诊断、影响面、回流计划与门禁重开清单。
8. **不代业主决策**：方案对比只给推荐 + 理由 + 备选，不给"两套都行"的话术。

---

## 4. 命令

```bat
set PYTHONPATH=E:\SKILL\建筑室内设计skill
cd /d E:\SKILL\建筑室内设计skill\omniarchitect

python -m omniarchitect doctor                      :: 工具链体检
python -m omniarchitect stages                      :: 打印八阶段模型
python -m omniarchitect registry                    :: 能力目录 + 18 份技能→阶段映射
python -m omniarchitect fusion                      :: arch-skills 融合与归属
python -m omniarchitect demo --out out              :: 示例项目跑通全部八阶段
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "出施工图"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by 业主
python -m omniarchitect reject  --project projects/demo-120 --stage S3 --reason "面积要重算"
python -m omniarchitect change  --project projects/demo-120 "我不喜欢客厅的电视背景墙"
python -m omniarchitect verify  --project projects/demo-120
```

验证（改完必须跑）：

```bat
python scripts/run_tests.py          :: 65 项测试，零第三方依赖
python scripts/verify_all.py         :: 测试 + 目录自检 + 全流程冒烟
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

新增依赖前先问：能不能降级？不能降级的部分必须有明确的"能力缺失"报告路径。

---

## 6. 第三方归属

`third_party/arch-skills/` 是上游参考仓库（作者 **Gu Jun**，https://arch-skills.com ，代码 MIT / 文档 CC BY 4.0），**原样保留、不得修改**。

吸收进本系统的是**方法论与判据**，不是代码：融合记录在 `registry.py: ARCH_FUSION`，说明见 `docs/ARCH_SKILLS_INTEGRATION.md`。任何使用这些判据的交付物都要在内联标注归属。

---

## 7. 改动流程

1. 先读 `docs/WORKFLOW.md` 与相关模块，不要凭印象改。
2. 结构性改动前先说明方案、暴露风险、给出选项。
3. 只改被授权的位置，不顺手重构别处。
4. 改完**必须**跑 `scripts/run_tests.py`；涉及管线则再跑 `scripts/verify_all.py`。
5. 全部通过后再归档（git）。测试没过不得声称完成。

---

## 8. 免责边界（写进代码，也写进交付）

结构安全、消防、无障碍、机电负荷与当地法规符合性，**不在本系统结论范围内**，必须由具备相应资质的专业人员在项目所在地复核并签署。任何把方案深度成果当作施工图的表述都是严重错误。
