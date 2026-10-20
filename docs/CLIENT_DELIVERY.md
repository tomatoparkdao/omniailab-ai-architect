---
name: omniailab-CLIENT_DELIVERY
description: CLIENT_DELIVERY —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: 1.12.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 客户交付：图文提案与在线文档

这一层解决两个具体问题：客户看不到案例长什么样，以及设计成果没有一个能持续更新的地方。
它不引入新流程，只把 S1–S8 已经产出的 Markdown、JSON、图解与 PPTX 重新组织成客户能读的形态。

模块：`omniarchitect/presentation/html.py`（提案）、`omniarchitect/research/preview.py`（案例图）、
`omniarchitect/presentation/online_doc.py`（文档包）。

---

## 一、四类图，四种身份

交付物里同时会出现四种"图"。它们混着放最省事，也最容易在交付后说不清——客户会以为
手法示意就是原案例的照片，或者以为生成的概念意向图可以直接拿去报建。所以页面上每张图
都带标记，页首有图例：

| 类型 | 是什么 | 能不能放进交付物 |
|---|---|---|
| 真实案例 | 第三方项目的照片，权利属原作者与摄影师 | **只给来源链接**，不下载、不重新托管、不嵌入 |
| 手法示意 | 本系统按案例公开文字绘制的关系图 | 可以，图上写明"非原案例照片" |
| 素材库参考 | 自有素材库（Luxora AI）里的空间意象 | 可以，标注"素材库参考"，不作尺寸依据、不称本项目效果图 |
| 原创意向 | OmniAiLab 原生画布生成，表达氛围 | 可以，标注"原创意向"，不作尺寸与做法依据 |
| 正式效果图 | G3 平面确认后按机位生成 | 可以，带机位与版本号，可作讨论依据 |

**提案里会出现手法示意、素材库参考与图解三类。** 原创意向需要平台已配置；未配置时页面里
不生成任何替代图——这是刻意留空，不是遗漏。正式效果图在 G3 之后才有。

素材库取图的实现是 `research/library.py`，条目索引在 `knowledge/library/catalog.json`
（文本，不含图片）。取不到就返回空，版面显示"无图"，**不拿另一张顶上**。

---

## 二、案例卡片怎么来的

一张卡有六个字段，缺一不可：

1. **图**：`preview.resolve()` 决定。有登记授权就用授权照片并署名，没有就用本系统绘制的手法示意图。
2. **项目名 + 事务所 + 地点 + 年份**：来自案例页面的公开字段，读不到就留空，不补。
3. **推荐理由**：`references._why_for()`，说的是"它回答了你哪个诉求"，不是"它很有名"。
4. **可借鉴手法**：从案例自己的标题与摘要里按词边界提取（`preview.techniques()`）。
   案例没写的词不会出现；一个都提取不到时，画"空间关系示意"，不硬塞一个专业词。
5. **来源入口**：整张卡可点，右上与底部各有一个「查看原案例 ↗」按钮（`target="_blank"`）。
6. **权利状态**：卡面右下角写明这张图是"本系统绘制"还是"已登记授权"。

### 已授权图片怎么登记

把图片放进项目目录，并在 `references/credits.json` 里登记来源：

```json
{
  "images": [
    {
      "url": "<案例页面的完整链接，与 reference-shortlist.json 里的 url 一致>",
      "file": "nachan-01.jpg",
      "license": "<许可证名称与版本>",
      "author": "摄影者姓名",
      "source_url": "<图片原始发布页面>"
    }
  ]
}
```

`license` 与 `source_url` 两样缺一不可：只写"可用"不算授权，将来没人能复核它到底谁给的。
缺任一项，该图会被忽略，卡片退回手法示意——**宁可少一张图，不留一张说不清来源的图**。

---

## 三、提案页面结构

`presentation/html.py::proposal()` 读 S2 的 `concept-options.json` + `reference-shortlist.json`，
输出单页 HTML（不依赖外部字体与脚本，离线可开）。

每套方案按"设计怎么来的"排序，而不是按字段顺序：

```
满幅封面（素材库空间意象 + 衬线大标题 + 四项真实计数）
图例（真实案例 / 手法示意 / 素材库参考 / 正式效果图）
总览（三张带图的方案条目，点击跳到对应段落）
每套方案：
  方案号 + 主张（大字号） + 专业事实（主导专业/空间家族/专业配合）
  满幅 hero（素材库空间意象）+ FIG 图注
  三栏注：最有价值的机会 / 为什么这样组织 / 适合的理由
  Drawings：首图满宽，第二、三张双联 —— 体量演变、剖面、轴测、总平面
  Sequence：两列步骤
  Materials：材料带（有素材照片就放照片）+ 色板
  三栏注：代价与前提 / 要机电配合 / 尚待核实
  Precedents：两张带图案例卡
来源与使用边界
```

版式的五条规则是踩出来的，不是审美偏好：

- **图分级，不平均。** hero 满幅；第一张分析图满宽；其余双联。把 1440×860 的图缩进半栏，
  14px 字变成 7px，图有内容但没传达。
- **文字退到图后面。** 不用侧栏面板装结论——那会把图挤窄。结论放图下的三栏注。
- **图注带编号与归属。** `FIG.01`…连续编号；右端写"本系统确定性绘制"或"素材库 · 标题"。
- **过短的"为什么"要补全**，且清掉内部字段名（`parti`、`massing_kind` 这类词客户不该看到）。
- **没有素材就空着。** 取不到图时整块不出现，封面落到纯色 + 大标题，不缩放一张示意图去占位。

---

## 四、在线文档包

`presentation/online_doc.py::build_package()` 一次生成两家：

```
online-doc/
  feishu/                       notion/
    00-index.md                   00-index.md
    01-brief.md                   01-brief.md
    02-references.md              02-references.md
    03-concepts.md                03-concepts.md
    04-stages.md                  04-stages.md
    05-changes.md                 05-changes.md
    assets/*.svg                  assets/*.svg
    assets/proposal.html          assets/proposal.html
    manifest.json                 manifest.json
    导入说明.md                    导入说明.md
  <project>-feishu.zip          <project>-notion.zip
```

五章对应客户真正会问的五件事：需求怎么定的、看过哪些案例、方案怎么来的、后面做到哪了、
什么时候改了什么。内容全部复用已有产物，不重新生成一份"给客户看的版本"——两份文案
迟早会不一致。

`04-stages.md` 的判据是"有没有产物目录 + 门禁状态"，两者不一致时如实写
"已产出 · 待业主确认"，不写成"未开始"。

### 发布边界

`publish()` 只有拿到客户端才会真的写：

```python
online_doc.publish("feishu", package_root)                      # → not_connected
online_doc.publish("feishu", package_root, client=client, title=…)  # → published + url
```

- 没有客户端：返回 `not_connected`、`url: None`，并说明缺哪个凭证。**不返回任何编造的链接。**
- 有客户端但没返回 url：记 `failed`，不写 `published.json`。
- 发布成功后把地址写进包里的 `published.json`，作为唯一记录。

仓库里不带飞书/Notion 凭证，所以默认路径是"出包、不发"。

### 隐私

每个包、每份文档顶部都有同一句：客户资料默认不公开，对外分享须由业主明确授权后单独操作。
`manifest.json` 里 `privacy` 字段记录同一句，`publish` 默认 `not_connected`——分享永远是
单独一步，不在构建时顺手做掉。

---

## 五、怎么跑

```bash
python scripts/design_three_cases.py          # 联网取案例，出提案 + 文档包
OMNIAILAB_NO_NETWORK=1 python scripts/design_three_cases.py   # 离网，只出概念
```

产物落在 `out/design-round1/<案例>/`：`index.html` 是客户提案，`online-doc/` 是文档包，
`run-*/` 是每一步的原始产物（保留历史，只读最新一次）。

---

## 六、本层不做什么

- 不做门户、不做登录、不做权限系统。文档空间在客户自己的飞书/Notion 里。
- 不把提案做成一个网站：它是单页文件，可以发邮件、可以打印。
- 不替客户决定分享范围。
- 不用生成式图像冒充案例照片，也不在未配置平台时用别的东西顶替。

---

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
