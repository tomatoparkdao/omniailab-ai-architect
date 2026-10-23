---
name: omniailab-adapters-specs-ifc
description: IFC adapter —— Purpose: IFC read/write, BIM spatial/semantic audit.
version: 1.17.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# IFC adapter

Purpose: IFC read/write, BIM spatial/semantic audit.

Reference: IfcOpenShell（开源 IFC 读写库，需自行安装）

**Preflight:** detect installed tool, version, available operations, execution host, units, auth, filesystem permission. Never presume a tool exists.

**Contract:** receive project_id/revision, stable element IDs, operation, parameters; return artifact pointers, new revision, log, errors and validation report.

**Safety:** sandbox arbitrary scripts, limit paths, keep transaction/undo backups, require approval before modifying originals.

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
