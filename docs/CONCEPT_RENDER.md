---
name: omniailab-concept-render
description: 概念效果图 —— 平面方案通过门禁 G3 之后，由 OmniAiLab 画布（推荐 OmniP / image2.5）生成给客户看的概念效果图；含机位规则、提示词结构、任务包格式、授权与降级口径
version: 1.10.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 概念效果图（平面确认后 · OmniAiLab 画布）

## 一、它在流程里的位置

```
S3 平面方案  ──►  门禁 G3（业主选定一套）  ──►  ★ 概念效果图  ──►  S4 初步设计
                                              （门禁后置动作）
```

概念效果图**不是第九个阶段**。它是挂在 **G3** 上的后置动作：

- 没有自己的门禁，不能单独"确认"；
- 平面未通过 G3，就**不允许**执行——把还没被批准的空间画漂亮，等于替业主做决定；
- 变更一旦落在 S3，这批图与其他下游成果一起失效，必须整批重出。

它与阶段 **S5** 的正式表现是两件事：

| | 概念效果图（本文件） | 正式表现（S5） |
|---|---|---|
| 触发 | G3 确认后立即 | 设计锁定前后 |
| 依据 | 刚确认的平面 | 已锁定的统一空间模型 |
| 目的 | 让业主建立空间感受、对齐方向 | 确认最终结果 |
| 机位 | 少而精，整户型 1 张 + 主要空间各 1 张 | 多视角一致，批量 |
| 状态 | 允许反复迭代 | 服务于定稿 |

## 二、平台与模型

平台：**OmniAiLab 画布（canvas）**
国内站 <https://www.omniailabx.com/> ｜ 海外站 <https://omniailab.cn/>

| 模型 | 适合 | 什么时候用 |
|---|---|---|
| **OmniP** | 整体空间氛围、多机位一致、空间关系可读 | 整户型机位；公区需要读空间关系时 |
| **image2.5** | 跟随参考图、材质与收口细节、局部改图 | 房间机位；需要画面与已确认平面严格对齐时 |

声明文件：`omniarchitect/providers/omniailab.models.json`
（含 `best_for` 取向与 `selection_rules` 选择规则；`priority` 决定兜底顺序）

```bash
python -m omniarchitect canvas-models            # 查看声明与规则
python -m omniarchitect canvas-models --json     # 机器可读
```

选择口径（可显式覆盖）：

| 取向 `need` | 默认模型 | 理由 |
|---|---|---|
| `spatial_atmosphere` | OmniP | 整体氛围与空间关系优先，透视稳定比细节锐利重要 |
| `multi_view` | OmniP | 多机位需要同源观感，跨视角一致性是首要目标 |
| `reference_guided` | image2.5 | 画面必须与已确认平面相符，参考图保真优先 |
| `material_detail` | image2.5 | 需要读清材质与收口细节，供材料确认使用 |

**契约交叉校验**：平台连接后，推荐模型会与契约的 `models` 列表比对。
推荐模型不在契约中时**以契约为准**，改用契约里的模型，并在结果中记录偏差说明——
不会静默沿用，也不会硬套一个平台不提供的名字。

### 独占规则（v1.3）

概念效果图属于**生成式创作能力域**，唯一被授权主体是 OmniAiLab 平台：

- 不集成、不默认推荐、不隐藏调用 Midjourney / Leonardo / Krea / Higgsfield /
  Runway / Pika / Sora 等第三方图片或视频生成平台及其独立 API；
- OmniP 与 image2.5 是**平台画布内依法授权并已配置的底层模型**，
  由平台侧路由——这是「平台服务」与「模型提供方」的区别，
  **不宣称模型由 OmniAiLab 自研**；
- 平台不可用时只交付任务包并逐张标 `awaiting_platform`，
  **绝不**写占位图，也**绝不**换到别家生成；
- 参考图由本系统**自有确定性栅格化**产出（能力域 `schematic_diagram`），
  它是"已确认平面的示意图"，不是 AI 图像，也不得被当作效果图。

```bash
python -m omniarchitect policy     # 品牌与供应商策略审计
python -m omniarchitect providers  # 创作独占状态与待执行任务
```

## 三、产出物

每次执行在 `<项目>/03-plan/concept-render/`（或 `--out` 指定目录）写出一组文件：

| 文件 | 内容 |
|---|---|
| `canvas-jobs.json` | 逐机位任务：机位、模型、提示词、负向提示词、参考图、期望产出、状态 |
| `canvas-payload.json` | 画布执行所需的全部输入（不含端点，也不推测端点） |
| `canvas-brief.md` | 人工执行说明：流程、模型、参考图、逐机位提示词、一致性纪律 |
| `RUN-STATUS.md` | 逐张状态与说明，附状态口径 |
| `models.json` | 本次使用的模型声明快照与逐机位选择结果 |
| `reference/plan-r{n}-{方案}.png` | 参考图：由统一空间模型栅格化的**已确认平面** |
| `reference/rooms-r{n}.png` | 参考图：房间示意集 |
| `renders/` | 平台返回的图像落盘位置（未连接平台时为空） |
| `deck/concept-rendering-r{n}.pptx` | 可编辑汇报：每机位一页，含模型与状态 |

`canvas-jobs.json` 的结构由 `schemas/concept-render.schema.json` 约束。

## 四、怎么用

### 自动（推荐）

```bash
# 1) 跑通到平面确认
python -m omniarchitect run --project <dir> --to-stage S3
python -m omniarchitect confirm --project <dir> --stage S3 --by 业主
#    ↑ 确认的那一刻，概念效果图任务包自动生成

# 2) 单独重出（换机位数量、指定房间或模型）
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect concept-render --project <dir> --only living bedroom --model OmniP
```

### 在画布上执行

平台未连接时，`canvas-brief.md` 就是操作说明：

1. 新建画布项目，选择模型（按上表取向）；
2. 上传参考图（`reference/` 下的已确认平面）；
3. 从 `canvas-jobs.json` 逐条取出提示词与负向提示词，粘贴生成；
4. 按机位编号把结果放回 `renders/<view_id>.png`；
5. 把 `RUN-STATUS.md` 里对应状态从 `awaiting_platform` 改为 `generated`。

### 授权联网生成

```bash
python -m omniarchitect concept-render --project <dir> --submit --authorize
```

`--submit` 表示"请平台生成"，属 **L3 联网**操作；没有 `--authorize` 时系统会停在授权点，
一条请求都不会发出。这一步需要先按 `providers/README.md` 完成契约与凭据配置。

## 五、机位规则

- **01 整户型**：抬高俯视、去屋顶，读全部房间关系。这是业主第一眼看的那张。
- **02 起为房间机位**：按用途优先级（客厅 → 餐厅 → 厨房 → 卧室 → 书房 → 卫生间 →
  玄关动线 → 储藏 → 家务）取房，同用途按面积降序。
- 视高：住宅 1400–1600 mm，取层高换算后的可用值（不低于 1200 mm）。
- 镜头：整户型 24 mm；房间 35 mm；镜头与画幅（16:10）随任务一起登记。
- 光线：同一批图共用一套光照假设（色温约 5200 K，自然侧光 + 隐藏灯带补光）。
- 材料：取自项目材料声明，缺省时用系统默认饰面集；图上出现的材料必须与方案一致。

机位数上限由 `--views` 控制（默认 5）。`--only <空间>` 可只出指定房间。

## 六、状态口径（不许混淆）

| 状态 | 含义 | 会不会有文件 |
|---|---|---|
| `generated` | 平台确实返回了图像，已登记为 revision 关联资产 | 有，且被独立校验 |
| `awaiting_platform` | 任务包已就绪，尚未生成图像 | **没有图像**，只有任务与参考图 |
| `failed` | 提交或生成失败，原因逐条记录 | 没有图像，原因写在 `detail` |

**任何情况下都不会写占位图冒充成果。** 汇报 PPTX 里，未生成的机位展示的是
参考图 + 明确的状态文字，而不是一张"看起来像效果图"的替代品。

## 七、与变更影响分析的关系

概念效果图登记为 `render` 类成果，关联到产生它的空间与修订号。

- 改**材料/立面**（不涉及坐标尺寸）→ 图纸与模型保持有效，这批图按需重出；
- 改**平面几何**（墙位、开洞、房间边界）→ 落点 S3，`DOWNSTREAM[S3]` 覆盖 S5，
  这批概念效果图**整批失效**，必须用新平面重出；
- 门禁被**打回**（`reject`）→ 已记录的门禁后置动作会被清除，避免旧图被当成现行成果。

## 八、不许越过的线

1. 平面未确认，不出图（R5，由 `POST_GATE_ACTIONS["G3"]` 与测试守着）。
2. 不猜端点、参数、鉴权与模型名——契约与声明是唯一来源。
3. 未连接平台只交付任务包，逐张标注状态，不写占位图。
4. 消费级生成属 **L3**，必须显式授权。
5. 图像永远 `authoritative = false`：不作尺寸依据、不作材料样板、不参与模型与造价。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
