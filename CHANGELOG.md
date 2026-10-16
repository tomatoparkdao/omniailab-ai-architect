# 变更记录

## v1.1.0 — OmniAiLab 集成、原创化与交付能力

自 v1.0.0（八阶段工作流）增量开发，**未重建项目、未覆盖既有成果、既有测试全部保留并通过**。

### 目录与命名

- 项目根目录 `omniarchitect/` → **`omniailab-ai-architect/`**（同时是 Agent Skill 根）。
- Python 包改为根目录下的子目录 `omniailab_ai_architect/`（根目录名含连字符，不可直接导入）。
- 父目录遗留的 `out/`、`projects/` 已安全归并进项目，**未删除任何内容**。

### 新增

| 子系统 | 内容 |
| --- | --- |
| 第三方合规 | `compliance_audit.py` 可执行扫描器（文件级来源判定 + 处置建议）、`THIRD_PARTY_NOTICES.md`、`docs/THIRD_PARTY_AUDIT.md` |
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
  许可证要求的署名全部集中到 `THIRD_PARTY_NOTICES.md`。
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
