# 第三方声明 · Third-Party Notices

本文件是 OmniArchitect（产品生态：OmniAiLab）**唯一集中**的第三方声明与许可归属文件。
所有许可证要求的署名、来源与许可标识都记录在这里；用户面材料（`SKILL.md`、`README.md`、
设计案例、模板与汇报文件）不包含任何第三方品牌广告或推广链接。

---

## 1. arch-skills（研究方法论来源）

| 项目 | 内容 |
| --- | --- |
| 上游项目 | **arch-skills** |
| 来源地址 | https://github.com/gujun1502/arch-skills |
| 作者 | **Gu Jun** |
| 代码许可 | **MIT License** |
| 文档许可 | **CC BY 4.0**（`SKILL.md`、`references/`、`templates/`） |
| 要求署名 | `Gu Jun / arch-skills` |
| 本地副本 | `third_party/arch-skills/` |

### 使用方式

上游材料**仅作为研究与方法论来源**，未在 OmniArchitect 的运行时代码路径中分发其任何源文件。
被吸收的是**判据与流程口径**，不是代码，融合明细记录在
`omniailab_ai_architect/registry.py: ARCH_FUSION` 与
[`docs/ARCH_SKILLS_INTEGRATION.md`](docs/ARCH_SKILLS_INTEGRATION.md)。

### 义务

1. `third_party/arch-skills/` **原样保留**，其自带 `LICENSE` 文件不得删除或修改。
2. 任何使用融合判据产生的交付物，需在文内标注 `Gu Jun / arch-skills（CC BY 4.0）`。
3. 本文件与 `docs/ARCH_SKILLS_INTEGRATION.md` 保留完整署名。

### 未采用的第三方内容

以下内容**未被引入**，且不得在任何时候重新混入本系统：

- 上游作者的商业推广站点与个人主页链接；
- 上游 `company-profile` 模板、业主档案与任何企业隐私信息；
- 上游示例项目的真实业主、项目名称、面积、年份与项目资料；
- 上游作者的个人审美宪章、设计偏好与专属口号（本系统使用自有
  `knowledge/` 知识体系，见第 2 节）；
- 上游的绘图库、PDF 处理脚本、Typst 样式文件与投标竞价引擎。

---

## 2. OmniArchitect 自有内容（无第三方许可义务）

| 目录 / 文件 | 来源 | 说明 |
| --- | --- | --- |
| `knowledge/` | **原创** | 12 个专业领域知识文档，从通用设计原理与公开工程惯例撰写 |
| `cases/` | **原创** | 按项目类型通用化的判据模板，不绑定任何真实外部项目 |
| `skills/` | **原创** | 28 项岗位能力与阶段归属说明 |
| `omniailab_ai_architect/` | **原创** | 全部运行时代码 |
| `schemas/` · `workflows/` · `templates/` · `docs/` | **原创** | 数据模型、流程定义、模板与文档 |

**用户项目数据**：只有在获得明确授权后才可加入案例库，并须保留项目来源与授权说明
（见 `schemas/case.schema.json` 的 `source` / `permission_note` / `media_redistributable` 字段）。
未获授权的第三方平面图、摄影图片与项目资料**不作为可再分发资产**随本系统分发。

---

## 3. 运行时依赖

OmniArchitect 核心路径**零硬依赖**。以下为可选依赖，仅在安装时提升产物质量，
不安装也不会阻断几何、图纸、模型、工程量与汇报成果：

| 依赖 | 用途 | 缺失时的降级 |
| --- | --- | --- |
| `ezdxf` | DXF R2010 后端 | 使用内置 DXF R12 写出器 |
| `shapely` | 精确多边形布尔运算 | 使用内置网格分解裁剪 |
| `jsonschema` | 严格 Schema 校验 | 使用内置子集校验器 |
| `PyYAML` | 读取工作流 YAML | 使用内置解析器或忽略 |
| `Pillow` | 本地示意图栅格化 | 跳过本地图像，保留矢量与 DXF |
| `python-pptx` | PPTX 高保真排版 | 使用内置原生 OOXML 写出器 |
| `pytest` | 测试运行器 | 使用内置零依赖测试运行器 |

这些库各自遵循其自身许可，均以「未修改的库引用」方式使用。

---

## 4. 工具与协议提及

`adapters/specs/` 与文档中提及的 Blender、FreeCAD、AutoCAD、IFC / IfcOpenShell、
SketchUp、Revit 等名称，均为其各自权利人的商标或产品名，此处仅用于说明**接口适配目标**，
不表示任何隶属、赞助或授权关系。OmniArchitect 不随附这些软件的安装包或代码。

---

## 5. 自动校验

第三方内容的合规状态由代码扫描，而非人工承诺：

```bash
python -m omniailab_ai_architect audit                 # 运行第三方内容审计
python -m omniailab_ai_architect notices              # 打印本声明
python -m omniailab_ai_architect audit --write docs   # 重写审计报告
```

扫描器位于 `omniailab_ai_architect/compliance_audit.py`，它对每个文本文件给出
来源判定与处置建议，报告输出到 `docs/THIRD_PARTY_AUDIT.md`。
扫描不通过即视为交付未完成。

---

*最后更新：见 `docs/THIRD_PARTY_AUDIT.md` 的扫描时间戳。*
