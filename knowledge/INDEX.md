---
name: omniailab-index
description: 知识库索引（INDEX） —— 本索引供程序做渐进式加载：先读本文件确定需要哪个领域，再按需加载对应知识文档，避免一次性加载全部内容。索引本身只做路由，不承载领域判据。
version: 1.13.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 知识库索引（INDEX）

本索引供程序做**渐进式加载**：先读本文件确定需要哪个领域，再按需加载对应知识文档，避免一次性加载全部内容。索引本身只做路由，不承载领域判据。

## 使用方式

1. 解析当前任务所在阶段（S1–S8）与涉及的判断问题。
2. 在下表的 `加载时机` 列匹配命中的领域。
3. 按 `成本` 列评估加载成本，优先加载轻量领域。
4. 用 `阶段` 列复核该领域是否适用于当前阶段。
5. 仅加载命中的文档，不加载全集。
6. 当多个领域命中时，按依赖顺序加载（上游在前）。
7. 加载后应回到索引确认是否有遗漏领域。
8. 涉及安全与合规时，输出中必须保留免责声明。

## 八阶段速查

| 阶段 | 名称 |
|---|---|
| S1 | 项目启动与设计任务书 |
| S2 | 概念方案设计 |
| S3 | 平面方案设计 |
| S4 | 初步设计与方案深化 |
| S5 | 三维建模与效果图表现 |
| S6 | 设计定稿与技术协调 |
| S7 | CAD/BIM 施工图深化 |
| S8 | 物料清单与设计交付 |

## 领域清单

| # | domain | 中文名 | 一句话用途 | 加载时机 | 阶段 | 成本 |
|---|---|---|---|---|---|---|
| 1 | architectural-design-principles | 建筑设计原理 | 判断总图、功能分区、流线、体量与场地关系的自洽性 | 涉及总体布局、体型生成、功能分区、流线与场地关系时 | S1,S2,S3,S4 | medium |
| 2 | interior-design-methodology | 室内设计方法论 | 把建筑壳体翻译为可施工的室内功能、界面与氛围方案 | 涉及室内功能重塑、界面、风格落地与软装策略时 | S1,S2,S3,S4,S6 | medium |
| 3 | spatial-planning | 空间规划 | 把功能意向落成房间、面积与动线的可校核平面 | 涉及房间划分、面积指标、动线组织与平面优化时 | S3,S4,S5 | heavy |
| 4 | human-ergonomics | 人体工学与尺度 | 提供通道、家具、洁具、操作台等人体活动尺度判据 | 涉及家具尺寸、通行宽度、洁具间距或任何尺度校核时 | S3,S4,S7 | medium |
| 5 | material-and-finish-selection | 材料与饰面选择 | 把设计意图翻译为可采购、可施工、可维护的材料体系 | 涉及材质选型、饰面构造、规格排版、样板或物料清单时 | S4,S6,S8 | heavy |
| 6 | lighting-design | 照明设计 | 统一自然光与人工光的照度、色温、显色与灯具布置策略 | 涉及照度标准、色温、灯具布置、自然光或照明场景时 | S4,S5,S6 | medium |
| 7 | building-systems-coordination | 机电与设备协同 | 协调暖通、给排水、电气、消防、智能化的空间与接口 | 涉及净高协调、管井、机房、管线走向或末端综合时 | S4,S6,S7 | heavy |
| 8 | construction-detailing | 构造与施工深化 | 把设计意图落到可施工的节点、层次、收口与防水做法 | 涉及节点大样、收口、基层、防水防潮或材料交接时 | S6,S7 | heavy |
| 9 | cad-drawing-standards | CAD 制图标准 | 统一图层、线型、标注、图框、编号与打印规则 | 涉及图层命名、线型线宽、尺寸标注、图框或图纸编号时 | S7 | medium |
| 10 | bim-modeling-principles | BIM 建模原理 | 定义模型精度、命名、属性、协同、碰撞与交付规则 | 涉及三维建模、模型精度、构件参数、碰撞或交付时 | S5,S7 | medium |
| 11 | design-review-checklists | 设计评审清单 | 以可判定的清单在提交与交付前把关质量 | 涉及方案自检、阶段评审、提交前检查或交付验收时 | S1,S4,S6,S8 | heavy |
| 12 | design-presentation-methodology | 设计汇报方法论 | 把专业成果转译为可决策的叙事与图册结构 | 涉及方案表达、图册组织、汇报结构或向业主沟通时 | S2,S4,S6,S8 | light |
| 13 | ai-concept-visualization | AI 概念表现方法论 | 平面确认后用 AI 出概念效果图：机位、提示词、参考图与迭代纪律 | 涉及概念效果图、出图提示词、机位安排或表现成果验收时 | S3,S4,S5 | medium |
| 14 | design-deliberation-methods | 设计推敲方法 | 从场地与诉求推出组织逻辑：parti、体量、剖面、虚实与采光路径 | 涉及概念推敲、方案比较或判断是否只换了风格时 | S1,S2 | medium |
| 15 | landscape-design-methodology | 景观设计方法论 | 庭院与室外专项：竖向、分区、游线、水景、植物、铺装与维护 | 委托涉及庭院、花园、屋顶花园或景观主导项目时 | S1,S2,S3,S4 | medium |

## 文件对应关系

| domain | 文件路径 |
|---|---|
| architectural-design-principles | knowledge/architectural-design-principles.md |
| interior-design-methodology | knowledge/interior-design-methodology.md |
| spatial-planning | knowledge/spatial-planning.md |
| human-ergonomics | knowledge/human-ergonomics.md |
| material-and-finish-selection | knowledge/material-and-finish-selection.md |
| lighting-design | knowledge/lighting-design.md |
| building-systems-coordination | knowledge/building-systems-coordination.md |
| construction-detailing | knowledge/construction-detailing.md |
| cad-drawing-standards | knowledge/cad-drawing-standards.md |
| bim-modeling-principles | knowledge/bim-modeling-principles.md |
| design-review-checklists | knowledge/design-review-checklists.md |
| design-presentation-methodology | knowledge/design-presentation-methodology.md |
| ai-concept-visualization | knowledge/ai-concept-visualization.md |
| design-deliberation-methods | knowledge/design-deliberation-methods.md |
| landscape-design-methodology | knowledge/landscape-design-methodology.md |

## 加载组合建议

- 方案阶段（S2–S3）：先 `architectural-design-principles`，再 `spatial-planning` 与 `human-ergonomics`。
- 深化阶段（S4–S6）：`interior-design-methodology` + `material-and-finish-selection` + `lighting-design` + `building-systems-coordination`。
- 出图阶段（S7）：`construction-detailing` + `cad-drawing-standards` + `bim-modeling-principles`。
- 评审与交付（S8）：`design-review-checklists` + `design-presentation-methodology`。
- 概念与汇报（S2）：`architectural-design-principles` + `design-presentation-methodology`。
- 模型表现（S5）：`bim-modeling-principles` + `lighting-design` + `spatial-planning`。
- 概念效果图（S3 门禁后 / S4）：`ai-concept-visualization` + `lighting-design` + `material-and-finish-selection`。

## 按阶段加载矩阵

| 阶段 | 主加载领域 | 次加载领域 |
|---|---|---|
| S1 | architectural-design-principles | design-review-checklists、interior-design-methodology |
| S2 | architectural-design-principles | design-presentation-methodology、interior-design-methodology |
| S3 | spatial-planning | human-ergonomics、architectural-design-principles、ai-concept-visualization |
| S4 | spatial-planning | material-and-finish-selection、lighting-design、building-systems-coordination、ai-concept-visualization |
| S5 | bim-modeling-principles | lighting-design、spatial-planning、ai-concept-visualization |
| S6 | building-systems-coordination | material-and-finish-selection、construction-detailing、lighting-design |
| S7 | construction-detailing | cad-drawing-standards、bim-modeling-principles、building-systems-coordination |
| S8 | material-and-finish-selection | design-review-checklists、design-presentation-methodology |

## 按问题类型加载路由

| 问题类型 | 应加载领域 |
|---|---|
| 功能分区与流线 | architectural-design-principles、spatial-planning |
| 房间面积与布置 | spatial-planning、human-ergonomics |
| 人体尺度与通行 | human-ergonomics |
| 材质与样板 | material-and-finish-selection |
| 照度与灯位 | lighting-design |
| 净高与管线 | building-systems-coordination |
| 节点与收口 | construction-detailing |
| 图层与出图 | cad-drawing-standards |
| 模型与碰撞 | bim-modeling-principles |
| 提交前把关 | design-review-checklists |
| 汇报与表达 | design-presentation-methodology |
| 概念效果图与出图提示词 | ai-concept-visualization、lighting-design、material-and-finish-selection |

## 成本等级说明

- light：结构简单，页面少，可频繁加载。
- medium：结构标准，含表格与清单，按需加载。
- heavy：内容密集，含大量数值与条目，仅在必要时加载。
- 加载成本不改变判据质量，只影响读取开销。

## 依赖顺序说明

- 上游领域先于下游领域加载，避免判据悬空。
- 典型上游：architectural-design-principles、spatial-planning。
- 典型下游：cad-drawing-standards、bim-modeling-principles。
- 评审与汇报领域通常在所有专业领域之后加载。

## 输出约束

- 任何输出若引用规范，须表述为"项目所在地现行规范"。
- 任何数值须注明为**常见工程惯例区间**。
- 涉及结构安全、消防、无障碍、机电负荷的结论，须注明"由持证专业人员在项目所在地复核签署"。
- 不得输出绝对化承诺或无法验证的形容词。

## 通用免责

本知识库所有数值均为**常见工程惯例区间**，非当地法定强制值。涉及结构安全、消防、无障碍、机电负荷的判定，须由持证专业人员在项目所在地复核签署。

## 领域摘要（逐条）

- **architectural-design-principles**：面向方案全局，回答功能、场地、法规、造价、可实施性是否自洽。
- **interior-design-methodology**：面向内部空间，回答界面、动线、氛围与功能如何统一。
- **spatial-planning**：面向平面，回答房间、面积与流线如何被校核。
- **human-ergonomics**：面向尺度，回答"够不够、顺不顺"的数值判据。
- **material-and-finish-selection**：面向材料，回答选型、规格、样板与清单如何一致。
- **lighting-design**：面向光环境，回答照度、色温、显色与灯位如何协调。
- **building-systems-coordination**：面向机电，回答净高、管井、机房与末端如何协同。
- **construction-detailing**：面向构造，回答节点、层次、收口与防水如何落地。
- **cad-drawing-standards**：面向出图，回答图层、标注、图框与编号如何统一。
- **bim-modeling-principles**：面向模型，回答精度、属性、协同与交付如何规范。
- **design-review-checklists**：面向质量，回答提交与交付前如何把关。
- **design-presentation-methodology**：面向沟通，回答成果如何被理解与决策。
- **ai-concept-visualization**：面向表现，回答平面确认后概念效果图怎么出、怎么迭代、怎么标注边界。

## 术语总表

- **阶段（S1–S8）**：设计流程的八个阶段，用于路由。
- **domain**：知识领域的 slug，与文件名一致。
- **stage_affinity**：领域适用的阶段集合。
- **loads_when**：触发加载的条件描述。
- **load_cost**：内容体量等级。
- **判据**：可判定的判断条目。
- **惯例区间**：常见工程取值，非法定强制值。
- **复核签署**：由持证专业人员在项目所在地确认。
- 术语在本知识库内统一，不得跨文档改变含义。

## 索引维护规则

- 新增领域须同步更新领域清单、文件对应关系与加载矩阵。
- 领域 slug 不得与文件名不一致。
- 阶段取值只能来自 S1–S8，不得自造。
- 删除领域须同时删除对应文件并更新引用。
- 索引版本变更须记录在版本小节。
- 索引本身不写判据，判据一律放在领域文档中。
- 索引与领域文档不一致时，以领域文档为准并回修索引。

## 常见问答

- 问：一次要加载几个领域？答：按命中数量，通常 1–3 个。
- 问：阶段不匹配还能加载吗？答：可以，但须说明必要性。
- 问：索引能替代领域文档吗？答：不能，索引只做路由。
- 问：数值能以索引为准吗？答：不能，须以领域文档为准。
- 问：合规结论能从知识库直接给出吗？答：不能，须专业复核。
- 以上问答用于保证索引被正确使用。

## 领域—阶段覆盖核对

| 阶段 | 覆盖领域数 | 是否含 heavy 领域 |
|---|---|---|
| S1 | 3 | 否 |
| S2 | 3 | 否 |
| S3 | 4 | 是 |
| S4 | 7 | 是 |
| S5 | 3 | 否 |
| S6 | 5 | 是 |
| S7 | 4 | 是 |
| S8 | 3 | 是 |

说明：覆盖数为常见组合，非强制；heavy 领域应尽量延后加载。

## 加载示例

- 示例一：任务为"住宅户型平面优化"，命中介于 S3，加载 `spatial-planning` 与 `human-ergonomics`。
- 示例二：任务为"办公室净高冲突"，命中介于 S6，加载 `building-systems-coordination`。
- 示例三：任务为"提交前检查"，命中介于 S8，加载 `design-review-checklists`。
- 示例四：任务为"节点做法"，命中介于 S7，加载 `construction-detailing`。
- 示例五：任务为"向业主汇报方案"，命中介于 S4，加载 `design-presentation-methodology`。
- 示例六：任务为"平面确认后给业主看几张概念效果图"，命中介于 S3，加载 `ai-concept-visualization`。
- 每次加载后应回读索引确认未遗漏依赖领域。

## 质量自检

- [ ] 索引中 13 个领域与 knowledge/ 下 13 个文件一一对应。
- [ ] 每个领域的 slug 与文件名一致。
- [ ] 每个领域的阶段取值来自 S1–S8。
- [ ] 每个领域标注了加载时机与成本。
- [ ] 加载矩阵与领域清单一致。
- [ ] 术语总表与实际文档口径一致。
- [ ] 免责声明已包含。

## 版本

- 索引版本：1.3.0（与 Skill 版本同步）
- 覆盖领域：13 个
- 覆盖阶段：S1–S8
- 对应文件：knowledge/ 下 13 个文档
- 版本一致性：本索引版本须与 `VERSION` 及 `SKILL.md` 的 `version` 保持一致

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
