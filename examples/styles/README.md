---
name: omniailab-style-examples
description: 示例产物索引 —— 六项能力的真实输出，可直接对照。
version: 1.18.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 示例产物

**这些不是示意，而是本工程真实跑出来的输出**（生成脚本与测试同源）。可以照抄格式，也可以对照检查自己的用法。

| 文件 | 对应能力 | 看什么 |
|---|---|---|
| `01-recommendation-three-options.md` | 推荐引擎 | 三套方向不同的方案、逐条归因的推荐理由、优点与代价、适配核对 |
| `02-italian-minimal-living-room-prompt.md` | 提示词编译 | 中英双语分层提示词、几何如何进入提示词并被标注"不得改动"、校核清单 |
| `03-five-rooms-consistency.md` / `.json` | 跨房间一致性 | 五个房间共用同一一致性指纹，各自保留自己的几何 |
| `04-partial-renovation-prompt.md` | 局部改造 | 墙体与门窗的强约束、只允许改动的部位、必须原样保留的构件 |
| `05-three-styles-comparison.md` | 风格对比（汇报用） | 同一户型三风格的并排比对与色板对照 |
| `06-jobs-package.json` / `06-jobs-brief.md` | 任务包（平台未配置） | 逐任务 `awaiting_platform`、`third_party_fallback: forbidden`、不产出任何图像 |

## 怎么复现

```bash
cd "<本工程根>"

# 1) 三套推荐
python -m omniarchitect style recommend --space-type 住宅 --area 120 --budget mid \
    --location 上海 --maintenance low --prefer 简洁,温暖 --out out

# 2) 意式极简客厅提示词
python -m omniarchitect style compile --style italian-minimal --target interior-render \
    --space 客厅 --width 4200 --depth 6000 --ceiling 2800 --locked --out out

# 3) 五房间一致性
python -m omniarchitect style multiview --style italian-minimal \
    --views 客厅,餐厅,主卧,书房,厨房 --width 4200 --depth 6000 --ceiling 2800 --out out

# 4) 局部改造
python -m omniarchitect style compile --style italian-minimal --target partial-renovation \
    --space "客厅（局部改造）" --width 4200 --depth 6000 --ceiling 2800 \
    --keep "南墙推拉门 2400×2400（位置与尺寸不变）|西侧承重墙（不得开洞）" \
    --change "电视背景墙饰面|地面铺装" --locked --out out

# 5) 三风格对比
python -m omniarchitect style compare \
    --styles modern-minimalism,chinese-neo-classical,industrial-loft --out out

# 6) 任务包
python -m omniarchitect style submit --compile-out out/prompt.json --out out
```

## 关于两个 JSON 文件

`03-five-rooms-consistency.json` 与 `06-jobs-package.json` 是**程序的直接输出**，
用于被其它工具消费（JSON 没有注释语法，因此不含署名行）。
其余 Markdown 产物均带标准署名。

---

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
