---
name: omniailab-style-data-spec
description: 风格数据规范 —— 二十个必需字段的写法与内容纪律，供新增或修改 knowledge/styles/ 下的风格记录时遵循。
version: 1.17.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 风格数据规范（Style Data Spec）

> 本文件是 `knowledge/styles/*.json` 的写作与校验规范。Schema 权威定义在
> `schemas/design-style.schema.json`；校验器在 `omniarchitect/style/validation.py`。

## 一、文件与命名

- 一个风格 = 一个文件：`knowledge/styles/<style_id>.json`
- `style_id` 为 **kebab-case**，与文件名逐字符一致
- `source` 固定为 `OmniAiLab` —— 表示本条目由本项目独立撰写

## 二、二十个必需字段（第一版硬约束）

| # | 字段 | 类型 | 要点 |
|---|---|---|---|
| 1 | `style_id` | string | kebab-case，等于文件名 |
| 2 | `display_name_zh` | string | 中文名，2–24 字 |
| 3 | `display_name_en` | string | 英文名 |
| 4 | `history_and_context` | object | `period` / `origin` / `summary`（≥40 字）/ 可选 `key_movements` |
| 5 | `spatial_principles` | string[] | ≥3 条，每条可判定 |
| 6 | `proportion_and_geometry` | object | `rules`（≥3）/ `ratios` / `ceiling_height_mm` |
| 7 | `color_palette` | object[] | ≥3 组，各含 `name_zh` / `name_en` / `hex` / `usage` / `role` |
| 8 | `materials` | object[] | ≥3 项，各含 `name_zh` / `name_en` / `application` / `finish` |
| 9 | `furniture_language` | string[] | ≥3 条：线条、体量、尺度、落地与拉手形式 |
| 10 | `lighting_strategy` | object | `principles`（≥2）/ `fixtures` / `color_temperature_k`（两元素）/ `illuminance_lux` / `layering` |
| 11 | `architectural_elements` | string[] | ≥3 条标志性构造元素 |
| 12 | `applicable_spaces` | string[] | ≥3 类空间 |
| 13 | `budget_considerations` | object | `tier` / `drivers`（≥2）/ `saving_moves` / `notes` |
| 14 | `construction_considerations` | string[] | ≥3 条工艺重点与易错环节 |
| 15 | `compatible_styles` | string[] | 可混搭的 style_id（必须真实存在于目录中） |
| 16 | `incompatible_elements` | string[] | ≥3 条会立刻破坏风格的元素 |
| 17 | `positive_prompt_components` | object | `zh` / `en` 两块，各含 `space` / `material` / `lighting` / `furniture` / `camera` / `atmosphere` / 可选 `keywords` |
| 18 | `geometry_preservation_rules` | string[] | ≥2 条几何保持约束 |
| 19 | `negative_constraints` | object | `zh` / `en` 各 ≥3 条 |
| 20 | `quality_checklist` | object[] | ≥3 项，各含 `check` / `criteria` / 可选 `stage` |

**可选元数据**（Schema 允许）：`family` / `tags` / `stages` / `version` / `source`。

Schema 是 `additionalProperties: false` —— **不许自造字段**，多一个键就校验失败。

## 三、内容纪律（违反即返工）

1. **不得堆砌同义词当不同风格。** 每种风格必须在**空间组织、比例、材料逻辑或构造做法**上
   与同族其他风格有可指认的差异。写不出差异，说明这个风格本来就不该单列。
2. **判据要可判定。** 写「暖材占比 ≤40%」而不是「温馨舒适」；写「主通道净宽 ≥900mm」
   而不是「动线顺畅」。数值一律标注为**常见工程惯例区间**，不得写成法定强制值。
3. **不得虚构材料或工艺。** 只用真实存在、可采购、可施工的材料与做法。
4. **不得复制任何第三方内容。** 风格知识必须独立撰写；不得搬运任何项目的提示词文本、
   案例描述、品牌名或宣传语。可在 `history_and_context.key_movements` 里写**公认的设计运动/流派名**
   （这是公共知识），但不写具体事务所、项目名或作品名。
5. **不写外部链接、不写第三方品牌名**（涂料/家具品牌名一律不出现，只用材料品类）。
6. **提示词组件里不许出现模型平台名**：生成式能力只能经 OmniAiLab 平台，
   提示词里不点名任何底层模型或第三方平台。
7. **`compatible_styles` 只能引用真实存在的 style_id**，且不做互相矛盾的双向声明
   （A 说兼容 B，B 也应说兼容 A 或至少在语义上不冲突）。
8. **免责边界**：结构安全、消防、无障碍、机电负荷与当地法规符合性的最终结论不在本系统范围内，
   `construction_considerations` 与 `quality_checklist` 里涉及这些的条目必须写成
   「标注待持证专业人员复核」而不是给出结论。
9. **中文写作**，术语与项目其余部分一致（统一空间模型 = Canonical Spatial Model、
   阶段 = stage、门禁 = gate、方案深度 = schematic、施工深度 = construction）。
10. **`hex` 必须是真实的 6 位十六进制颜色**，且与该风格的色彩逻辑自洽
    （例如侘寂不该出现高饱和荧光色）。

## 四、写作质量基线

- 每个文件 **120–200 行 JSON**（格式化后）。
- `history_and_context.summary` 要说清「**为什么会形成这套做法**」，而不是罗列形容词。
- `spatial_principles` 尽量写到「**怎么排**」而不是「**什么感觉**」。
- `positive_prompt_components` 是给 Prompt Compiler 直接消费的，必须**具体到可见物**
  （材料 + 表面处理 + 光线方向 + 家具形态 + 机位），不写「高级感」这类不可执行的词。
- `quality_checklist.criteria` 尽量带数值或明确的通过/不通过判准。

## 五、自查

写完跑：

```bash
python -m omniarchitect style validate --all
```

或对单文件：

```bash
python -m omniarchitect style validate --style <style_id>
```

校验器会检查：Schema 合规、二十字段齐全、`hex` 格式、`compatible_styles` 指向真实存在的
风格、`style_id` 与文件名一致、数值区间是否标注惯例口径。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
