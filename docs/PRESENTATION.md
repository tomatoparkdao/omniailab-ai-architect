---
name: omniailab-presentation
description: 设计汇报与 PPT 交付 —— 汇报能力是跨阶段通用能力（design-presentation，参与 S2–S8），不是流程末尾的一次动作。
version: 1.7.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 设计汇报与 PPT 交付

汇报能力是**跨阶段通用能力**（`design-presentation`，参与 S2–S8），不是流程末尾的一次动作。
每个阶段都能产出对应深度的提案文件。

---

## 1. 汇报类型

> `concept-rendering` 由概念效果图流程（G3 后置动作）自动生成，见 `docs/CONCEPT_RENDER.md`。
> 逐机位页面来自 `canvas-jobs.json`——**幻灯片不会描述一个从未被规划的机位**；
> 尚未生成的机位展示参考图并写明状态，而不是拿一张替代图充数。


```bash
python -m omniarchitect present --list-kinds
```

| kind | 阶段 | 用途 | 默认页结构 |
|---|---|---|---|
| `concept` | S2 | 概念设计提案 | 封面 / 结构 / 摘要 / 概念 / 关键词 / 意向板 / 平面 / 照明 / 材料 / 预算 / 待确认 / 免责 |
| `plan-comparison` | S3 | 平面方案比选 | 封面 / 结构 / 摘要 / 平面 / 比选 / 分析 / 预算 / 决策 / 待确认 / 免责 |
| `concept-rendering` | S3 | **平面确认后 · 概念效果图汇报** | 基础页 + **逐机位一页**（图 / 模型 / 状态 / 提示词指纹） |
| `preliminary` | S4 | 初步设计汇报 | 含材料、照明、机电协调 |
| `visual` | S5 | 视觉表现汇报 | 含机位说明与非权威声明 |
| `materials-lighting` | S4 | 材料与照明专项 | — |
| `final` | S6 | 设计定稿确认 | 含决策台账与下一步 |
| `technical-briefing` | S7 | 施工图技术交底 | 含图纸清单与专业接口 |
| `delivery` | S8 | 交付与物料清单 | — |
| `full` | — | 全过程汇报 | 上述页面组合 |

```bash
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
python -m omniarchitect present --project projects/demo-120 --kind full --brand "某事务所"
```

## 2. 产出物

| 文件 | 说明 |
|---|---|
| `presentation-<kind>-r<rev>.pptx` | **可编辑** PPTX（表格、图片、讲稿备注） |
| `presentation-<kind>-r<rev>.md` | 文字版，便于评审、检索与 diff |
| `presentation-<kind>-r<rev>.html` | 打印就绪版式，浏览器可另存为 PDF |
| `presentation-<kind>-r<rev>.pdf` | 仅当本机存在真实渲染器（LibreOffice）时生成 |
| `presentation-<kind>-r<rev>.deck.json` | 汇报数据模型 + 产出清单 + 内容来源 |

PDF 缺失时**不会伪造**：报告写明原因，并给出 HTML 打印作为降级路径。

## 3. 两个写出后端

| 后端 | 何时使用 | 特点 |
|---|---|---|
| `python-pptx` | 已安装（主后端） | 富排版：表格、图片、备注页、品牌样式 |
| `native-ooxml` | 未安装（内置兜底） | 零第三方依赖，直写 Open XML 容器，文本层完整，同样可被 PowerPoint 打开编辑 |

用 `--json` 或直接读取 `.deck.json` 可看到实际使用的后端。
写出后必须由**独立实现**重新打开校验（OOXML part 完整性、slide 数量、文本可读）。

## 4. 版式与品牌

`Brand` 可自定义：名称、标语、平台署名、主色 / 纸色 / 弱色 / 强调色 / 分隔线、
中西文字体、Logo、页脚。

默认是 OmniArchitect 自身的中性原则（浅纸色 + 单一强调色 + 大留白），
**不模仿任何第三方事务所模板**。

## 5. 内容与页结构

每份提案按需组织以下内容，**每一页的数据都必须来自模型 / 工程量 / 校核结果**：

设计任务与项目摘要 · 概念关键词 · 概念草图与图解 · Moodboard · 平面方案 ·
平面分析图（面积配比 / 采光 / 动线） · 空间透视效果图 · 材料与色彩 ·
照明逻辑 · 设计决策（决定—理由—代价） · 预算与材料概算 ·
方案对比 · 待确认事项 · 下一步 · **免责与边界**

### 内容自检（不通过即不得提交）

- 页数下限；
- 首页必须是 `cover`；
- **必须包含 `disclaimer` 免责与边界页**；
- 不得有空页；
- 表格列数必须与表头一致。

```python
from omniarchitect import presentation
rep = presentation.render(project, "final", out_dir="out")
print(rep["issues"])        # [] 表示通过
```

## 6. 硬性规则

1. **必须含免责与边界页**：结构安全、消防、无障碍、机电负荷与法规符合性不在系统结论范围内。
2. **效果图不得作为施工尺寸依据**；表现页必须声明该图非权威成果。
3. **不得引用第三方事务所自有作品**作为默认汇报案例。
4. **不得凭空声称具备 PowerPoint MCP**；PPTX 只由已验证的写出后端产生，并回报所用后端。
5. **不代业主决策**：给推荐 + 理由 + 备选。
6. 预算与工程量标注为方案阶段估算，**不构成结算依据**。

## 7. 可追溯性

`.deck.json` 里的 `provenance` 记录本次汇报用到了哪些知识域，
`project_id` / `revision` / `generated_at` 把文件钉在模型的具体修订上。
模型改了修订，旧汇报不会假装还成立。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
