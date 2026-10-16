---
name: omniailab-ai-architect-design-presentation
version: 1.0.0
capability: design-presentation
stages: [S2, S3, S4, S5, S6, S7, S8]
---
# Design Presentation

## Responsibility
把专业设计成果转译为**可决策**的提案：让业主在有限时间内看清方向、看懂取舍、做出确认。
汇报能力是跨阶段通用能力——每个阶段都产出对应深度的汇报文件，而不是只在最后做一次。

## Inputs
- 统一空间模型（Canonical Spatial Model）当前修订；
- 该阶段已产出的成果：概念方案 / 平面方案与指标 / 材料与照明方案 / 图纸清单 / 工程量与估算；
- 评审与校核结果（含待确认项与阻断项）；
- 可用媒体资产（示意图、效果图、意向图），以及它们的 provider 与任务 ID；
- 品牌样式（可自定义 `Brand`：名称、主色、纸色、字体、页脚）。

## Outputs
- `presentation-<kind>-r<revision>.pptx` — 可编辑 PPTX；
- `presentation-<kind>-r<revision>.md` — 文字版，便于评审与检索；
- `presentation-<kind>-r<revision>.html` — 打印就绪版式（浏览器可另存为 PDF）；
- `presentation-<kind>-r<revision>.pdf` — 仅当本机存在真实渲染器时生成；
- `presentation-<kind>-r<revision>.deck.json` — 汇报数据模型 + 产出清单 + 内容来源。

## Deck kinds（按阶段）
| kind | 阶段 | 用途 |
| --- | --- | --- |
| `concept` | S2 | 概念设计提案：立场、原型、关键词、意向板 |
| `plan-comparison` | S3 | 平面方案比选：可比指标 + 面积配比 + 造价影响 |
| `preliminary` | S4 | 初步设计汇报：材料、照明、机电协调 |
| `visual` | S5 | 视觉表现汇报：表现图与机位说明 |
| `final` | S6 | 设计定稿确认：决策台账 + 待确认项 |
| `materials-lighting` | S4 | 材料与照明专项 |
| `technical-briefing` | S7 | 施工图技术交底：图纸清单 + 协调接口 |
| `delivery` | S8 | 交付与物料清单 |
| `full` | — | 全过程汇报（各阶段页组合） |

## Procedure
1. 读取模型当前修订，确定汇报深度与目标读者。
2. 按 `DeckBuilder` 组织页面：封面 → 结构 → 项目摘要 → 概念/平面/材料/照明/表现 → 决策 → 预算 → 协调 → 图纸 → 待确认 → 下一步 → **免责与边界**。
3. 每一页的数据都必须来自模型、工程量或校核结果；缺失时写明"尚未生成"，**不得用占位数据冒充结果**。
4. 生成页面的同时记录 `provenance`（本次用到哪些知识域与数据源）。
5. 写出 PPTX / Markdown / HTML；PDF 仅在检测到真实渲染器时生成。
6. 自检：页数下限、封面、免责页、空页、表格列数一致性。

## 硬性规则（门禁）
1. **必须包含免责与边界页**。结构安全、消防、无障碍、机电负荷与法规符合性不在系统结论范围内，须由持证专业人员复核签署。
2. **效果图不得作为施工尺寸依据**；表现页必须声明该图非权威成果。
3. **不得引用第三方事务所的自有作品**作为默认汇报案例；案例只能来自原创知识库与用户授权内容。
4. **不得凭空声称具备 PowerPoint MCP**；PPTX 只能由已验证的写出后端产生，并回报所用后端。
5. **不代业主决策**：给推荐 + 理由 + 备选，不写"两套都行"。
6. 预算与工程量标注为方案阶段估算，**不构成结算依据**。

## Toolchain
- 主后端：`python-pptx`（真实可编辑 PPTX，含表格、图片、讲稿备注）。
- 备用后端：内置原生 OOXML 写出器（零第三方依赖，输出同样可被 PowerPoint 打开与编辑）。
- 写出后必须用**独立实现**重新打开校验（part 完整性、slide 数量、文本可读）。

## Gate
汇报文件不通过内容自检（缺免责页、空页、表格列数不一致）时，**不得作为交付件提交**。
