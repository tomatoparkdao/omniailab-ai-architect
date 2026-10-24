---
name: omniailab-examples-demo-brief
description: Example design request —— 120 m² 公寓的示例设计请求（英文原文）
version: 1.20.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 示例设计请求（中英对照）

## 中文

为一套 **120㎡ 公寓**做现代温暖极简的室内设计。两间卧室、一间书房、厨房、客餐厅、两个卫生间。

开局交代（避免它自己猜）：请以带尺寸的准确原始平面为准，并问清所在地区；**不要推断承重墙**。
先出 2 个概念方向，再做一版带批注的平面方案供确认；**只有确认之后**才生成统一空间模型、三维模型、效果图与图纸初稿。

## English

Create a modern warm-minimalist interior for a 120 m² apartment. Two bedrooms, one study, kitchen, living/dining, two bathrooms.

Initial intake: request the accurate base plan with dimensions and ask for the location; do not infer structural walls.
Produce 2 concept directions, then one annotated plan proposal for approval; only after approval generate the canonical model, 3D model, renderings and the first drawing set.

## 这条示例示范了什么

| 示范点 | 说明 |
|---|---|
| 需求写具体 | 面积、房间数、风格各一句，不写"高级一点"这类形容词 |
| 明确交代不确定性 | "不要推断承重墙"——避免把推断值当实测值（`uncertain = true`） |
| 明确门禁顺序 | "只有确认之后才生成模型与效果图"——对应 G3 平面方案确认门禁 |
| 明确要什么产物 | 概念 / 平面 / 模型 / 效果图 / 图纸初稿，按需取用 |

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
