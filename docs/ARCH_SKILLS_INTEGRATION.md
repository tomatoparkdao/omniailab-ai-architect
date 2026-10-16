# arch-skills 融合说明与归属

## 来源与许可

| | |
|---|---|
| 上游项目 | **arch-skills** — https://github.com/gujun1502/arch-skills |
| 作者 | **Gu Jun**（https://www.chodo.ai · https://arch-skills.com ） |
| 许可 | 代码 **MIT**；文档（`SKILL.md` / `references/` / `templates/`）**CC BY 4.0** |
| 要求署名 | `Gu Jun / arch-skills.com` |
| 本地副本 | `third_party/arch-skills/`（`git clone` 原样保留，含其自带 LICENSE） |

**已做的事**：把上游的**方法论与判据**吸收进 OmniArchitect 对应的阶段与能力。
**未做的事**：没有在上游仓库中修改任何文件；没有在运行时代码路径中分发上游源文件；没有搬运上游的脚本（如 `drawkit.py`、`annotate.py`、`md_to_pdf.py`）。

融合明细的机器可读版本在 `registry.py: ARCH_FUSION`，可用 `python -m omniarchitect fusion` 打印。任何使用了这些判据的交付物都在文内带了归属行。

---

## 融合明细

### 1. asset-management-interior → S2 概念 / S3 平面 / S4 材料

吸收内容：

- **克制美学宪章**：冷底暖眼 / 一条主导线定全场 / 天花是第一叙事面 / 黑是重音不是块面 / 一个纹理三种密度 / 每层至少有一个发光的面
- **概念四步引擎**：锚 → 象 → 法 → 形
- **平面判据**：好采光面是否被独立房间独占、客户流线是否穿过私密区、平面上是否存在真实成立的主导线、是否留出一个"空的地方"
- **Moodboard 六格意象结构**与暖材 ≤40%、黑 3–8% 的配比规则

落地位置：S2 的概念方案与意向板骨架、S3 的评审判据、S4 的材料色彩体系（含占比表）。
未吸收：具体业主信息、案例实拍图、品牌报价表。

### 2. create-draw → S2 概念图解 / S4 立面批注 / S7 图纸会审

吸收内容：

- **红蓝笔图形语义**：红=问题/张力、蓝=方向/动线/视线、橙=光的动作、绿=亮点、灰=参考
- 概念图解的表达方式：概念主张 + 空间原型 + 光 / 材质 / 动线三策略
- **图主文辅纪律**：图上标签 ≤12 字，说明栏每条 ≤30 字

落地位置：概念图解与图纸批注的图形语言规范。
未吸收：`drawkit.py` 绘图库与其 SVG 坐标脚本。

### 3. moodboard-aesthetic-iteration → S2 意向板 / S5 效果图质量门

吸收内容：

- 意向板 → 关键词三组 → 量化打分 → 跨轮整改追踪的迭代闭环
- 200ms 第一印象 + Design Critic 六维 + Color Harmony 60-30-10 诊断框架
- **口径固定原则**：同一项目内评分体系不可中途更换

落地位置：S2 写入意向板骨架与固定的评分口径，S5 作为效果图质量门。
未吸收：`md_to_pdf.py` 渲染脚本与其 PDF 模板。

### 4. building-services-electrical → S4 机电初步 / S6 协调 / S7 点位

吸收内容：HVAC / 给排水 / 电气 / 竖向交通 / 消防对空间的影响速查；机房、管井、净高与吊顶空间占用的判断口径。

落地位置：S4 的机电初步协调表、S6 的专业协调清单、S7 的点位图待办。
未吸收：具体地区规范条文——这些必须由持证专业人员在项目所在地复核，不能由文档替代。

### 5. red-blue-pen-annotation → S6 / S7 / S8 的变更台账

吸收内容：

- **逐条核销的批注台账机制**（跨轮 ledger、问题闭环）
- 主文档 + 意见 → 批注版交付物的流程约定

落地位置：变更影响分析的数据结构（`ChangeEntry` + 依赖图失效重算 + 跨轮追踪），以及 `out/<run>/changes/` 下的变更台账。
未吸收：`annotate.py` / `extract_pdf.py` / `ledger.py` 等 PDF 处理脚本。

### 6. design-text-typst → S8 交付文档

吸收内容：A3 横版设计提案的网格版式与交付文本规范。
落地位置：交付文档的版式约定。
未吸收：Typst 样式文件与样张。

### 7. tender-bid-review → S1 可行性判断

吸收内容：全生命周期复盘与评分反算思路；能力边界与造价档位匹配的判据。
落地位置：S1 任务书阶段的"这个项目该不该接 / 能不能做"判断。**不参与设计生成。**
未吸收：`company-profile` 模板与业主档案（含企业隐私）。

### 8. bid-pricing-engine → S1 / S8 估算口径

吸收内容：量价分离的估算口径。
落地位置：S1 前期估算与 S8 正式清单使用同一套口径，避免前后对不上。
未吸收：蒙特卡洛投标竞价引擎（`bid-pricing-engine.jsx`）与其博弈模型——与本系统的设计生产链无关。

### 9. skill-safety-audit → 适配器定级

吸收内容：**L1–L4 安全等级分类法**（只读 / 本地写 / 联网 / 执行发送）。
落地位置：适配器能力声明与人工审核门槛的定级依据——`adapters/base.py: Capability` 的 `operations` 与 `notes`。
未吸收：`audit.py` 扫描器。

### 10. article-academic → 未纳入

学术深度文章写作属内容创作能力，与设计生产链无关，**全部未吸收**。

---

## 结构性差异（有意不照搬）

上游按**业务链**组织：商机 → 投标 → 设计 → 审核 → 交付。OmniArchitect 的目标是"能真正完成一个设计项目的 AI 总设计师"，因此：

- **保留**其组织思想：Stage（业务阶段）+ Skill（专业能力）+ Role（执行角色）+ Level（成熟度）分层。
- **不照搬**其业务链：商机与投标不在本系统范围内，只把其中"能力边界与造价档位匹配"的判据借到 S1。
- **重构**设计段：上游把设计段作为一个整体（asset-management-interior / create-draw / moodboard），本系统拆成 S2 概念 / S3 平面 / S4 初步设计 / S5 表现 / S6 定稿 / S7 施工图，每段有独立门禁。

---

## 署名要求（再强调）

> 设计判据、评审方法与文档规范来自 **arch-skills**，作者 **Gu Jun**（https://arch-skills.com ），
> 代码 MIT / 文档 CC BY 4.0。

任何对外交付物若使用了这些判据，需保留上句归属。代码中的归属常量：

```python
from omniarchitect import ARCH_ATTRIBUTION
print(ARCH_ATTRIBUTION["attribution_line"])   # Gu Jun / arch-skills.com
```
