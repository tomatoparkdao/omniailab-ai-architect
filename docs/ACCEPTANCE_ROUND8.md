---
name: omniailab-ACCEPTANCE_ROUND8
description: ACCEPTANCE_ROUND8 —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: 1.17.1
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 验收 · 第八轮：室内与景观图版的几何一致性

> 本轮只做小范围视觉质量修正：图与推敲图同源、标签指对地方、景观概念不画错水。
> 不加项目分类、不动 S1–S8、不重构设计系统。

## 一、为什么改

v1.15 的图版和四步图各写一套百分比坐标，于是同一件东西在两张图上不在同一个位置：

| 问题 | 现象 | 后果 |
|---|---|---|
| 两套几何 | `plate.plan_plate` 与 `evolution._interior_body` 各算各的 | 主推图里的大堂到了四步图里变成一条横带，最后一步还挪一下 |
| 公共核错位 | 客房标准层图里塞了一个"公共核" | 大堂被画成走廊边上的一个房间 |
| 公共层与客房层混成一张 | `plan_layout=public_core` 只出一幅图 | 看不出"公共核在裙房、客房在塔楼" |
| 茶座是浮标 | 标签按百分比贴在左上角，没有对应图形 | 指向空地，而且与需求相反（远岸才对） |
| 环路不接入口 | 环是个独立椭圆，入口箭头在框外 | "绕水一周"走不通 |
| 备选也画水池 | 只有一套景观图版 | 「不做池子」的方案被画成有池子 |

## 二、改了什么

### 1 一份几何，两处渲染

新增 `omniarchitect/concept/layout.py`：区域是归一化矩形，节点是归一化点，
联系是折线。`plate.plan_plate()` 与 `evolution` 调**同一个 `draw()`**，
四步只按 `appear` 逐项显形、按 `emphasis` 点亮，**不移动任何已定区域**。

守卫：`test_plate_and_steps_share_one_geometry`（两个入口拿到的 frames 必须相等）。

### 2 按 `plan_layout` / `massing_kind` 决定画什么

| 判据 | 出图 |
|---|---|
| `plan_layout=public_core` | 两幅：裙房公共层 + 客房标准层 |
| `plan_layout=guest_wing` | 一幅客房标准层 |
| `plan_layout=tech_core` / `cluster_atrium` / `process_line` … | 各自的三段式（门诊／医疗街／医技，教学／连廊／办公，生产／通道／仓储） |
| `massing_kind=pond` | 一池静水 + 环形游线 |
| `massing_kind=terraces` | 旱溪台地（无水面） |
| `massing_kind=grove` | 林下茶席 + 边缘浅渠 |

没有 `plan_layout` 的室内按业态落到三段式，**绝不套客房图版**。

### 3 公共核与客房层分开

裙房公共层：后场（服务梯·后勤）在左，餐厅（全日）与会议（宴会·无窗）在上，
大堂（公共核）居中，前台是服务台，客梯厅在右下；客流（落客→大堂→前台→客梯厅）
在右半，服务流（后勤入口→服务梯）在左半，两条线不交叉。

客房标准层：客房（带模数分隔）／走廊／客梯厅／服务核（布草·服务梯），
**没有大堂、没有公共核**。

守卫：`test_public_core_is_two_frames_and_keeps_the_lobby_off_the_guest_floor`、
`test_guest_flow_and_service_flow_never_cross`。

### 4 景观：关系闭合，水按概念

| 要求 | 做法 | 守卫 |
|---|---|---|
| 穿门见水 | 入口正对水面，进门即水 | `test_labels…` |
| 茶座在远岸 | 茶座与入口分处水面两侧 | `test_landscape_tea_seat_sits_across_the_water_from_the_gate` |
| 看得到倒影 | 茶座→房子的视线穿过水面 | 同上 |
| 环与入口接通 | 入口到环路的路径端点落在椭圆上（容差 5%） | `test_entry_path_touches_the_ring…` |
| 路不穿水 | 所有 `path` 顶点不得落在水面 bbox 内 | 同上 |
| 备选不画水 | `terraces` 方案无 `water` 区域，SVG 里不出现水色 | `test_dry_stream_alternative_draws_no_water_at_all` |
| 房子不随方案移动 | 三种景观方案的 `house` 矩形完全相同 | `test_every_landscape_variant_has_its_own_layout_and_a_fixed_house` |

### 5 标签由几何算，不按百分比贴

* 放得下放区域内（左上／居中）；椭圆区域居中（bbox 的角不在水面上）；
* 放不下引到外侧，引线只连最近的边，避开别的区域与水平流线（走廊）；
* 互不重叠、不出界；四步图里只标"这一步新出现的"，一次不超过 3–4 个。

守卫：`test_labels_stay_in_the_frame_and_never_overlap`。

### 6 顺手修掉的三处文字毛病

* 右栏大字与第二行原本可能印同一句（"裙房 2 层做公共核"上下各一遍）；
* `_clip` 会把一句话截成"……形成一……"（两个省略号 / 半句），改为按句读断、
  断不开才加一个省略号；
* 图注原来说"体块关系"，在庭院页上是错的，改为按专业给"场地与游线／功能与流线"。

## 三、三个验收项目

| 项目 | 页数 | 图版 |
|---|---|---|
| 24 班小学（建筑） | 9 | 等距体块（未改，回归通过） |
| 120 间客房酒店（室内） | 11 | 两幅：裙房公共层 / 客房标准层 |
| 800 ㎡ 私家庭院（景观） | 9–10 | 一池静水 + 环形游线；备选旱溪台地 |

> 庭院页数在 9–10 之间浮动：对标案例页依赖联网检索，取不到 2 个案例时该页不出。

复现：

```bash
python scripts/design_quick_cases.py hotel
python scripts/design_quick_cases.py garden
```

产物：`out/concept-round/<case>/shots/*.png`（整页）、`run-*/02-concept/concept-proposal.{html,pptx}`、
`concept-motion.html`（按专业的推演动画）。

## 四、仍未做到

* 概念意象平台未配置：两案例均 0 张生成图，`awaiting_platform` 如实标注，不放替代图；
* 图版是**关系示意**，不按尺寸绘制；面积、净宽、高差在 S3 按实测复核；
* 素材库没有教育/医疗/工业实景，这三类靠对标案例页支撑；
* 四步的名称仍是通用四段（场地与边界／空间层次／园路与节点／水景与种植），
  旱溪方案的第四步名不精确——文字说明与图一致，但名称没改名。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
