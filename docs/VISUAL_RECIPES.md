---
name: omniailab-visual-recipes
description: 表现技法库 —— 把已确认的平面与立面转成业主看得懂的图与板：平面图上色、3D 立轴、正投影剖面、三视图展示板、概念设计板、实体材质情绪板；每条配方写明输入、门禁、几何保真与文字叠加边界
version: 1.21.1
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 表现技法库（Visual Recipes）

设计做完了，业主却看不出来——这是提案环节最常见的失败。图纸对设计师是语言，对业主
是密码。这一层解决的就是"把已定的东西翻译成看得懂的图"，**不产生新的设计结论**。

所以它不是新的设计能力，也不是新 Skill：它挂在提示词编译层（`style/recipes.py` +
`style/compiler.py`），继续共用风格锁定、一致性指纹、几何保真条款与产出后校核清单。
同一张图不会因为换了入口就少一道校核。

## 一、六条配方

| 配方 | 族 | 输入 | 最早可用 | 说明 |
|---|---|---|---|---|
| `plan-color` | 图纸派生 | 已确认平面 | G3 之后 | 平面转三维俯视上色图，房间关系一眼可读 |
| `plan-axon` | 图纸派生 | 已确认平面 | G3 之后 | 等距剖切轴测，30–45° 抬高、去屋顶 |
| `section-elevation` | 图纸派生 | 平面 + 剖切位置 | S4 | 严格正投影，无透视 |
| `presentation-board` | 版面 | 平面 + 立面 + 透视 | G3 之后 | 三栏并置的提案封面页 |
| `concept-sheet` | 版面 | S2 概念包 + 锁定风格 | S2 | 一页说清概念、色板、材料、家具、照明 |
| `material-moodboard` | 版面 | 锁定风格的材料声明 | S2 | 实体材质叠放的质感板 |

配方登记在三处，且只有一处是真源：`recipes.py` 定义，`resources.PROMPT_TARGETS`
与 `TARGET_STAGES` 由它派生，`provider_bridge.TARGET_SCOPE` 声明能力域。测试守着
这三处不许各写一套。

## 二、三条被改掉的原始写法

这几条提示词本身很实用，但直接照抄会出专业事故。融合时改了三处：

| 原始写法 | 问题 | 现在的做法 |
|---|---|---|
| 红色尺寸标注 | 图像模型写的数字是编的，业主会当真 | 画面内禁止任何文字与数字；标注由 DXF 矢量层叠加 |
| 用简短标签说明 | 中文字形必错，还会编出错字 | `text_policy=overlay`：模型留白，标签由排版层排真字 |
| 平面图上色当平面图用 | 几何被重画后不可核对 | 一律标"表现图"，禁止量尺寸、报审、下料 |

第三条最容易被忽略：上色图、立轴图、剖面图**看起来**比平面图更"专业"，所以更容易
被当成依据。配方里的 `checks` 第一条就是"与已确认平面叠合逐间核对"。

## 三、平面门禁：探索可以，花钱不行

四条配方以已确认平面为唯一几何依据（`PLAN_GATED`）。平面没过 G3 时：

* 仍然可以编译，用于探索——但正向提示词第一行写死"【探索稿·平面未确认】"；
* 任务包里 `gate.blocked = true`，并给出"不得提交"的警告；
* `provider_bridge.submit()` **直接拒收**，不建任务包、不排队、不花钱。

演示与探索不需要门禁，正式成果需要。这个区分和 S3 的探索/签发是同一套逻辑：
能看，不等于能签。

## 四、文字为什么要叠加而不是生成

版面型配方（展示板、概念板）里有大量标签：图名、色板名、材料名、家具语汇、照明要点。
让模型写中文，结果只有三种：乱码、错字、缺字。所以：

1. 提示词要求"为文字留出空白区"，负向约束写死"不得出现任何文字、数字"；
2. 配方把该写的标签列进 `text_overlay`（`CompiledPrompt.text_overlay`）；
3. 排版层（`presentation/`）拿这份清单排真字，字号、位置、语言都可控。

顺带解决一个隐患：模型不会替我们编造尺寸数字。

## 五、在流程里的位置

配方不是"另外跑一个命令"，它们已经接进阶段产出：

| 环节 | 自动带上的配方 | 产物 | 状态 |
|---|---|---|---|
| S2 概念（`generate`） | `concept-sheet` `material-moodboard` | `concept-visual-jobs.json` | 未配置平台即 `awaiting_platform` |
| G3 通过后（`approve S3`） | `plan-color` `plan-axon` `presentation-board` | `drawing-visuals.json` / `.md` | `awaiting_authorization`，授权后才计费 |
| S3/S4 手动补充 | `section-elevation` | `style prompt --target section-elevation` | 需给剖切位置与参考图 |

S2 的四条任务（方向意象 / 材料氛围 / 概念设计板 / 实体材质情绪板）走同一套双开关与
幂等台账；概念设计板的 `text_overlay` 会随任务包一起下发，排版层据此写标签。

G3 之后的图纸派生只**编译不提交**：平面签了不等于授权花钱，任务停在
`awaiting_authorization`，等显式授权再提交。

## 六、怎么用

```bash
# 图纸派生：必须带参考图，平面已过 G3 才能用于正式成果
python -m omniarchitect style compile --style italian-minimal \
  --target plan-color --space 客厅 --width 4200 --depth 6000 \
  --refs plan.png --plan-confirmed

# 版面：概念板不需要平面门禁
python -m omniarchitect style compile --style italian-minimal \
  --target concept-sheet --space 厨房

# 提交（平台未配置时只登记待执行，绝不改道第三方）
python -m omniarchitect style submit --compile-out out/prompt.json \
  --out out/jobs --authorize
```

不打开 `--plan-confirmed` 时，`plan-color` / `plan-axon` / `section-elevation` /
`presentation-board` 出来的是探索稿，`submit` 会拒绝并说明原因。

## 七、边界

* 这些图是**表现**，不是图纸：不得作为尺寸、面积、构造或报审依据；
* 几何由模型重绘，必然有偏差，必须与已确认平面叠合核对后才可交付；
* 人物剪影只作比例参照，不得据此判断净高或净宽；
* 材质情绪板是氛围参考，实际选材以材料表与实物样板为准；
* 平台未配置时不生成替代图，任务包登记为待执行（品牌策略禁止第三方回退）。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
