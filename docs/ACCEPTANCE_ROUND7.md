---
name: omniailab-ACCEPTANCE_ROUND7
description: ACCEPTANCE_ROUND7 —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: 1.16.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# v1.15.0 验收：三个专业，三种推敲，三类对标

这一轮不加阶段、不加门禁、不加分类。改的是三件事：概念推敲按专业走、
素材库没有同类项目时去真实案例里找、案例说明必须来自证据。

| 项目 | 委托 | 页数 | 素材库实景 | 对标案例 | 推敲方式 | 动画 |
|---|---|---|---|---|---|---|
| A 公共建筑 | 新建 24 班小学 | 10 | 0（如实说明） | 2 | 体量与形态 | 有 |
| B 室内 | 既有酒店精装修（120 间） | 11 | 5 | 2 | 功能与序列 | 有 |
| C 景观 | 私家庭院 800 m² | 10 | 4 | 2 | 场地与游线 | 有 |

复现：`python scripts/design_quick_cases.py school|hotel|garden`

## 一、概念推敲不再一套体块走三专业

| 项目 | 四步（取自本方案自己的分区/序列/采光/主张） |
|---|---|
| 小学 | 场地与限界：教学区 1,560 m² 分 3 栋 → 体量分解：食堂 356 m² 与体育馆 800 m² 独立成体量 → 加入要素：从校门看见中庭 → 结果形态：24 班拆成 3 个组团 |
| 酒店 | 功能重组：裙房 2 层公共核 1,620 m²、塔楼客房 → 空间序列：落客区→大堂→前台→餐厅与厨房同层 → 界面与通透：大堂与餐厅需要自然光 → 核心空间：大堂、餐饮与会议集中成核 |
| 庭院 | 场地与边界：以水面为心、园路成环 → 空间层次：水与路之间留 600mm 收边石带 → 园路与节点：穿门见水→沿水走→茶座在远岸 → 水景与种植：中心静水、园路绕水一圈 |

三条硬规则：

1. **推不出来就不出图**：概念里没有分区/序列/采光时，`evolution.plan()` 返回 `ok=False`
   并说明缺什么；提案改出「这套方案凭什么成立」文字页，`anim.build()` 返回 `skipped`，
   不生成动画。
2. **图与动画同源**：`scenes()` 一份画法，提案四步图与 `concept-motion.html` 都用它。
3. **四步不复读**：说明按顺序取不同字段，实测每个项目的四个 note 各不相同。

## 二、素材库没有，就去真实项目里找

v1.14 的学校案例是「DUA Villa」——因为检索只按专业选分类页（houses），
而 `school` 又被写进了固定噪声词。现在：

| 环节 | 做法 | 实测 |
|---|---|---|
| 分类页 | 按项目类型选（A3→educational-architecture 等） | 4 个类型页各 24 条可解析 |
| 类型词 | school/campus/factory 是信号；别墅在学区项目里扣分 | 学校检索命中 3 所真实学校 |
| 核验 | 详情页回读标题一致才标「已核验」 | 三项目 6 条案例全部 verified |
| 图片 | 第三方照片只给链接，不嵌进 PPTX | 案例页只有文字与项目页链接 |

实际取到的案例（项目名／设计机构／年份／来源）：

- 小学：City Pride School（A Threshold，2025）、Civic Campus Sallarès Deu（JAAS，2025）
- 酒店：Ausma Hotel（Field Studio，2026）、Finch Bay Hotel（Alfredo Ribadeneira Arquitectos，2025）
- 庭院：Son Llodrà House: Merge into the Landscape（Bastidas Architecture，2023）、
  Gondomar Urban Park（Paulo Merlini arquitetos，2023）

## 三、案例说明不再套话

四个问题的答案全部来自该案例自己的文字或本案的策略字段：

| 问题 | 来源 | 反例（已删除） |
|---|---|---|
| 为什么看它 | 案例 `fits`（标题/简介里真实出现的词）+ 本案概念主张 | 「它在 C-A 这个方向上…」这类空话 |
| 借什么 | `READING_SIGNALS` 命中的手法；不足时用案例的地点/年代补一句 | 两条案例共用同一段兜底句 |
| 怎么转化 | 本案 `zoning` 原文，说清不同在哪 | 「按你的地块重排」 |
| 不照搬 | 案例 `avoid` + 年份/地点条件差异 | 三条案例同一句「尺寸不通用」 |

同时删掉了没有依据的量化断言（原「软装比例要减三成」「最省钱的一招」）。

## 四、诚实的部分

| 项 | 现状 |
|---|---|
| 素材库实景 | 小学 0 张：索引里没有教育空间实景。不拿用途不对的照片充数，改用对标案例 |
| 概念意象 | 平台 `not_configured`：三项目均 0 张生成、12 张待平台，不放替代图 |
| 案例图片 | 第三方摄影有版权，只给项目页链接；可再分发的 PPTX 里不放 |
| 几何 | 概念阶段无实测几何，每页注明「示意，不作尺寸依据」 |
| 动画 | 四步推演是自有矢量图解，不是生成式视频；渲染不出时返回 skipped |

## 五、回归

| 项 | 结果 |
|---|---|
| 单测 | `scripts/run_tests.py` 全绿（新增 6 条：专业推敲四步、缺数据必须拒绝、动画跳过、类型路由、案例读图去重） |
| 交付自检 | `scripts/verify_all.py` 全绿 |
| 内容审计 | `python -m omniarchitect audit` 待处理 0 |
| 格式 | `normalize_attribution.py --check` 不一致 0；`check_tables.py` 通过 |

S1–S8、G1–G8、36 类分类、47 种风格、31 项能力、S2→S3 概念继承、Luxora AI 优先原则均未改动。

---
© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
