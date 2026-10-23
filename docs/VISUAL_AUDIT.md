---
name: omniailab-visual-audit
description: 视觉能力盘点与复用清单 —— 记录总设计师原有的审美、图解与排版能力各自被谁调用、本轮哪些是重新接上的、哪些是新增的，以及为什么新增是最小必要
version: 1.18.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 视觉能力盘点与复用清单

这份文档回答一个问题：**总设计师本来就有的审美能力，是不是真的被用上了。**

答案是"有一部分没有"。v1.7.0 的客户提案之所以像工程文档，不是因为系统没有风格库或表现技法，而是因为最终出图的那一层只用了 `rect`、`line`、`circle` 三个图元，并且把确定性 SVG 当成了唯一的图像来源。能力在库里，链路没接上。

## 一、盘点方法与判据

对每个视觉模块问三个问题：

1. **它能做什么**（读代码与文档，不看宣称）；
2. **谁在调用它**（`grep` 真实调用点，`__all__` 与测试不算调用）；
3. **产物出现在谁面前**（客户交付目录里能不能找到它）。

第三条是硬判据：**只在测试里跑通的能力，等于没有交付。**

## 二、原有能力：调用状态

| 模块 | 能做什么 | v1.7.0 前是否被调用 | 本轮处置 |
|---|---|---|---|
| `knowledge/styles/`（47 份） | 风格记录：色彩、材料、光、家具语汇、提示词组件 | 是（`style_ids` → 意向板与提示词） | 保留，未改记录 |
| `style/recipes.py`（6 条） | 表现技法配方：投影、约束、文字策略、核对项 | 部分（S2 用 4 条，图纸派生 3 条等 G3） | 保留，未新增配方 |
| `style/compiler.py` | 9 类目标画像 → 结构化双语提示词 | 是 | 保留 |
| `compile_view_set()` | 多机位同一身份编译 | **否**（仅 CLI 与测试） | 保留给 S3+，本轮不动 |
| `concept/moodboard.py` | 六格意向板 + 真实色板与材料 | 是 | 保留；整栏嵌入改为满宽 |
| `concept/diagrams.py` | 8 种概念图解 | 是，但图元只有矩形/线/圆 | **重做 4 种 + 新增 1 种** |
| `concept/visual.py` | 平台视觉任务、双开关、幂等台账 | 是（平台未配置 → 如实延后） | 保留 |
| `research/preview.py` | 案例手法示意、授权图判定 | 是 | 保留（案例卡专用） |
| `presentation/html.py` | 客户提案单页 | 是 | **版式重写** |
| `presentation/deck.py` + `pptx_writer.py` | 可编辑 PPTX / MD / HTML | 是 | 保留 |
| `presentation/online_doc.py` | 飞书 / Notion 双载体文档包 | 是 | 保留；加带图开关 |

## 三、被漏掉的四件事（本轮真正的问题）

### 1. `Svg` 只有三个图元，画不出体块

`Svg` 类原来只有 `rect` / `line` / `circle` / `polyline` / `path` / `text`。**没有 `polygon`、没有 `ellipse`、没有渐变。** 等距轴测的每一个可见面都是一个填充多边形——没有 `polygon` 就只能用矩形拼，于是"体量图"必然是几个方块。这不是设计选择，是能力缺失。

处置：`diagrams.Svg` 补 `polygon` / `ellipse` / `gradient` / `clip_rect` 四个原语。

### 2. 没有等距投影，体量就没有第三维

体量推敲的信息全在立面与遮挡关系里：哪一面朝街、哪一层退进去、院是切出来的还是围出来的。俯视矩形一条都表达不了。

处置：新增 `concept/iso.py`（等距投影 + 三面明暗 + 画家算法 + 阴影 + 水面 + 树冠）。`massing()` 改为四联轴测：**做满 → 减去 → 加入场地 → 结果**。

### 3. 素材库图片从未进入交付物

`paths.REFERENCE_LIBRARY_URL` 登记了自有素材库，`docs/REFERENCE_SOURCES.md` 也写了"只给链接、图不可嵌入"。结果是：提案里的"图"只剩确定性 SVG，客户看到的是线框。

处置：新增 `research/library.py` 与 `knowledge/library/catalog.json`（素材库条目的文本索引）。运行时按专业与风格匹配、下载、按版面比例裁剪、登记来源。图本体不入库，仍受 `scripts/check_assets.py` 约束。

口径变化见 `docs/REFERENCE_SOURCES.md`：自有素材库与第三方案例分开对待。

### 4. 图被平均对待，于是每张都不够大

旧版把 1200×900 的意向板塞进 300px 侧栏、把 540×372 的案例示意当 hero、把 1440×860 的图解缩进半栏。字号 14 缩到 7，图有内容但没传达。

处置：`presentation/html.py` 重写版式——满幅封面、每方案一张 hero、图解按重要度分满宽 / 双联、图注统一编号（`FIG.01`）。素材图与图解在图例上分开标注。

## 四、本轮新增（最小必要）

| 新增 | 为什么必须新增 | 复用了什么 |
|---|---|---|
| `concept/iso.py` | 等距投影是几何算法，原有模块没有 | `Svg`、`diagrams` 的语义色 |
| `research/library.py` | 素材库取图与裁剪，原有模块只判权不取图 | `Svg` 无关；色板与标题来自 catalog |
| `knowledge/library/catalog.json` | 素材条目的文本索引（不含图片） | 素材库页面本身 |
| `concept/diagrams.axon()` | 室内不能套建筑体块图 | `iso`、`Svg`、概念的真实字段 |

没有新增：风格系统、视觉引擎、设计语言系统、第二个 Skill、第二套排版框架。

## 五、仍然缺的（不掩饰）

| 缺什么 | 影响 | 什么时候会有 |
|---|---|---|
| 平台生成的概念意象图 | 只有素材库参考与确定性图解 | OmniAiLab 画布配置授权后 |
| 真实几何（平面/体量尺寸） | 图解只能表达关系，不能放线 | S3 平面确认后 |
| 授权案例照片 | 案例卡只有手法示意 | 项目登记 `references/credits.json` 后 |
| 材料实物照片 | 材料带目前用素材库材质图 | 选材阶段有样板后 |

## 六、怎么复核这份清单

```bash
# 谁在调用图解
grep -rn "dia.build\|diagrams import" omniarchitect --include=*.py
# 素材库有没有真的进产物
ls out/*/assets/*.jpg
# 图元是否够用（应该看到 polygon/ellipse/gradient）
grep -n "def polygon\|def ellipse\|def gradient" omniarchitect/concept/diagrams.py
```

判据只有一条：**客户打开的页面里，能不能看到一张不是线的东西。** 看不到，就说明链路又断了。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
