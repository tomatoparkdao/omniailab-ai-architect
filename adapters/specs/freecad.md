---
name: omniailab-adapters-specs-freecad
description: FREECAD adapter —— Purpose: Parametric mechanical and CAD geometry.
version: 1.4.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# FREECAD adapter

Purpose: Parametric mechanical and CAD geometry.

Reference: FreeCAD MCP（社区开源实现，需自行部署）

**Preflight:** detect installed tool, version, available operations, execution host, units, auth, filesystem permission. Never presume a tool exists.

**Contract:** receive project_id/revision, stable element IDs, operation, parameters; return artifact pointers, new revision, log, errors and validation report.

**Safety:** sandbox arbitrary scripts, limit paths, keep transaction/undo backups, require approval before modifying originals.

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
