---
name: omniailab-existing-drawing-analysis
description: 原始图纸解析 —— 图层、墙体、尺寸、门窗识别；区分可置信信息与推断信息
version: 1.1.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
capability: existing-drawing-analysis
stages: [S1]
---
# CAD Understanding

## Responsibility
Extract dimensions, layers, walls, openings and annotations; flag uncertain parsing.

## Inputs
Project brief, canonical model, source files, explicit constraints and design revision.

## Outputs
Structured findings, changes to canonical model (if applicable), artifacts and QA notes.

## Procedure
1. Confirm applicable input quality and assumptions.
2. Formulate a task plan and check project constraints.
3. Execute available tool adapters; avoid unverified claims.
4. Validate dimensional and semantic consistency.
5. Update revisions and list downstream artifacts to regenerate.

## Gate
If professional sign-off, statutory compliance or site measurement is needed, explicitly stop at draft/review stage.

## 阶段归属（v1.0 八阶段体系）

- 专业能力：`existing-drawing-analysis`（原始图纸解析）
- 参与阶段：S1
- 说明：专业能力是设计事务所的岗位能力，可跨阶段调用；项目推进按 `docs/WORKFLOW.md` 的八个业务阶段进行。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
