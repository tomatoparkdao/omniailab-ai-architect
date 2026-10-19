---
name: 设计能力：空间体验与技术实现
description: 让方案像一个建筑师做的——空间体验词表与序列、业主感受的匹配判断、结构与机电的实现路径，以及为什么它们不再被当成审批口
version: 1.11.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 设计能力：空间体验与技术实现

> 这一层解决一个问题：**方案看起来像一个建筑师做的，还是一套流程生成的。**
> 它不新增阶段、不新增门禁、不新增审批。全部是判据。

## 一、为什么要有这一层

在此之前，S2 已经有两层：

| 层 | 模块 | 回答 |
|---|---|---|
| 空间组织 | `concept/prototypes.py` | 房间怎么排、人怎么走、光从哪进 |
| 视觉语言 | `style/` + `concept/palette.py` | 看起来像什么、材料与配色 |

两层都对，但中间空了一段最关键的：**人走进去会经历什么。**

原型说的是「中脊把厨卫压在中间，两侧都是完整房间」。业主听不懂，也不该听懂。
他要知道的是：进门先看到什么？要不要拐弯？哪一步最亮？哪一处会想站住。

这段空白不是文风问题。Appleton 的前景—庇护理论（1975）、Palladio
在《建筑四书》里主张的「层高由平面推出」、以及从 enfilade（套间序列）
到走廊的演变，讲的全是这件事——**空间是被经历的，不是被列举的。**

## 二、两个模块，各管一件事

### `omniarchitect/design/vocabulary.py` —— 空间体验

| 内容 | 说明 |
|---|---|
| `VOCABULARY`（11 条） | 压缩与释放 / 前景与庇护 / 门槛与过渡 / 套间序列 / 框景 / 借景 / 节奏与重复 / 光的层次 / 材料的真实与触感 / 比例与层高关系 / 到达序列 |
| `FAMILY_DEVICES` | 每个空间家族**天然擅长**哪些手法（结构性判断，不是词面匹配） |
| `ENTRY_EVENT` | 22 套原型各一句「进门先看到什么」，必须具体到能画 |
| `read_feelings()` | 业主原话 → 手法 id（长词优先，「不压抑」不会被读成「压抑」） |
| `sequence_for()` | 原型 → 体验序列（第一眼 / 转折 / 主空间 / 留下什么） |
| `fit()` | 业主要的感觉，这套方向给不给得出：`met` / `at_risk` / `not_stated` |

每个词条必须带四项，缺一项就是装饰：

1. `why` —— 机制的说明（为什么有效），不是形容词堆叠；
2. `how` —— 具体做法，能被画出来；
3. `test` —— **在图上怎么核验**（这一项是整张表的用途）；
4. `misuse` —— 用错了会怎样。

### `omniarchitect/design/enabling.py` —— 结构与机电怎么实现设计

设计问题不是「这个通高能不能做」，是「这个通高怎么做才成立」。所以这里给的是
**实现路径**，不是可行性结论。共 8 个目标、24 条路径。

| 专业 | 目标 |
|---|---|
| 结构 | 通高开洞 / 拆改承重墙 / 新增荷载 / 大跨度 |
| 机电 | 不吊顶的净高 / 湿区移位 / 无窗空间 / 开放厨房 |

每条路径写清四件事：怎么做、换来什么、**拿什么换**（代价）、**必须由谁核**。
没有零代价的路径——说「都能做」等于没说。

## 三、行为改变（这是本轮真正动到系统的地方）

### 1. 结构与机电不再是审批口

旧逻辑：概念提到「挑空」→ 结构方向标 `requires_input` → 比较表把它当成
「不能推荐」。这等于因为图纸没到就否掉一个设计。

新逻辑：提到「挑空」→ 给出三条实现路径（边梁抬 / 钢梁框架 / 局部悬挑），
各自写代价与签字责任 → 状态 `proposed`，资料缺失写到 `open_questions`。

**安全底线没有松动**：每条路径都带 `sign_off`，必须由持证专业出计算书；
物理上做不到的（中间层开天窗、地下层要自然光）直接返回 `blocked` 并给替代做法，
不列假路径。

### 2. S1 多问一句话

新增槽位 `feeling`（权重 2，「想要的空间感受」），对应一道题：

> 如果用一句话形容推开门那一刻想要的感受，你会怎么说？

刻意不给选项——选项会把业主的答案框成我们预设的那几种。这一句换来的，是
S2 全部审美方向的依据。业主第一句话里已经说了「敞亮」「要显大」时，
`seed_from_text()` 直接记下，不再问第二遍。

### 3. 图解不再贴截断原文

`diagrams.py::_sequence_steps()` 原先在最后一步贴 `circulation[:28]`——
图上一段被切断的句子。现在读体验序列，每步是一个空间事件，并标注手法名。

## 四、边界（比功能重要）

* **业主没说，不替他决定。** `fit()` 在无感受诉求时返回 `not_stated`，
  不输出「推荐温馨」。
* **不编造名作案例。** 词条只写做法与判据。写了「某某建筑因此著名」
  就等于替建筑师背书，而我们无法核实。
* **不自造术语。** 词表里的概念全部有公开的专业依据；新词要先证明有出处。
* **本层不替代 `hardgate`。** 红线（安全、消防、强制规范）仍由它判定。

## 五、怎么用

**不需要额外命令。** S2 每次生成时自动包含这两层：

| 落点 | 你会看到什么 |
|---|---|
| `concept-options.md` | 每套概念下多出「走进去会经历什么」一节：第一眼 / 转折 / 主空间 / 记住的是，每步标出用了哪个手法 |
| `concept-comparison.md` | 美学维度引用 `feeling_fit` 的结论——这套方向对你说的那种感觉，是强项、够用、还是勉强 |
| `concept-diagrams/*.svg` | 序列图上的每一步是一个空间事件，不是被截断的原文 |
| `concept-handoff.json` | `experience_sequence` 与 `feeling_fit` 随交接传给 S3 |

想直接看词表与判定结果，用 Python 读：

```bash
export PYTHONPATH=<你的路径>/omniailab-ai-architect

# 看词表：每条含机制、做法、图上怎么核验、用错了会怎样
python -c "from omniarchitect.design import vocabulary as v; print('\n'.join(f'{d.id}｜{d.name}｜{d.test}' for d in v.VOCABULARY.values()))"

# 看业主原话被读成了哪些手法
python -c "from omniarchitect.design import vocabulary as v; print(v.read_feelings('要敞亮一点，进门别一眼看穿'))"

# 看某个原型走进去的经历（以住宅的默认原型为例）
python -c "from omniarchitect.design import vocabulary as v; from omniarchitect.concept import prototypes as p; print(v.sequence_for(p.for_profile('residential')[0].to_dict()))"

# 看某个技术目标有哪些实现路径、各自要谁签字
python -c "from omniarchitect.design import enabling as e; r=e.structure_paths('想做通高客厅'); [print(p['name'],'|',p['trades'],'|',p['sign_off']) for g in r['goals'] for p in g['paths']]"
```

> 这些是模块能力，不是步骤。它们没有独立命令，因为**不该由你手动触发**——
> 触发点是 S2 生成那一刻，和业主在 S1 说的那句话。

> 免责边界：本层给出的是设计判断与实现方向，不产生结构计算、机电负荷计算、
> 也不判定当地法规符合性。上述内容须由项目所在地持证专业人员在方案复核后签署。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
