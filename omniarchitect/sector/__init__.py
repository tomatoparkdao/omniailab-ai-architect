"""行业设计层：把"这是什么项目"变成"这套项目怎么排"。

三个入口，各管一件事，彼此不重复：

* `brief.build(ctx)`    —— 从 S1 的话里抽出可算的输入，列出矛盾与缺口；
* `moves.moves(brief)`  —— 由这些数推出 2–3 条组织方式，写明代价；
* `program.build(brief)`—— 把选定的方式折成房间清单，交给已有平面算法。

不新增阶段、不新增门禁、不新建第二套几何：S3 仍走 `planner.PlanGenerator`，
只是房间来自行业程序，排布换成"按带"这一种通用算法。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from . import brief, layout, moves, program, site, stage

__all__ = ["brief", "layout", "moves", "program", "site", "stage"]
