"""行业设计层：把"这是什么项目"变成"这套项目怎么排"。

四个入口，各管一件事，彼此不重复：

* `brief.build(ctx)`     —— 从 S1 的话里抽出可算的输入，列出矛盾与缺口；
* `moves.moves(brief)`   —— 由这些数推出 2–3 条组织方式，写明代价与落地方式；
* `parti.resolve(...)`   —— 读出 S2 选定的组织方式，并在平面上核对结构是否成立；
* `program.build(brief)` —— 把选定的方式折成房间清单，交给 `plans` 按 parti 排。

不新增阶段、不新增门禁、不新建第二套几何：房间仍由 `planner._strip` 摆放，
墙门窗仍由 `PlanGenerator` 生成，差别只在"按什么组织"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from . import brief, layout, moves, parti, plans, program, site, stage

__all__ = ["brief", "layout", "moves", "parti", "plans", "program", "site", "stage"]
