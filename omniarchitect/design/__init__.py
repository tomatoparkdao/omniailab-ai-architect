"""设计能力层 —— 让总设计师像一个建筑师，而不是一套流程。

这个包只装**专业判断**，不装状态、不装门禁、不装审批。目录里每个模块都在回答
一个设计师真的会问的问题：

| 模块 | 回答的问题 |
|---|---|
| `vocabulary` | 人走进去会经历什么？业主要的那个感觉，这套方案给不给得出？ |
| `enabling` | 结构与机电怎么把这个设计实现出来，代价是什么，谁来核？ |

分工边界（不要在这里重复已有能力）：

* 空间怎么组织 → `concept/prototypes.py`（本包不定义原型）；
* 看起来像什么 → `style/`（本包不定义风格、不定义色板）；
* 能不能做、是否触红线 → `hardgate.py`（本包只给实现路径，不替代安全判定）；
* 这套概念向专业提了什么要求 → `concept/disciplines.py`（本包回答"怎么实现"）。

新增内容只允许是"专业知识 + 可核验判据"。任何带状态机、带签字、带门禁的东西
都不属于这里。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from . import enabling, vocabulary
from .enabling import MEP_GOALS, STRUCTURE_GOALS, Goal, Path, mep_paths, structure_paths
from .vocabulary import (
    FEELING_WORDS,
    SEQUENCE_STEPS,
    VOCABULARY,
    Device,
    all_devices,
    device,
    fit,
    read_feelings,
    sequence_for,
)

__all__ = [
    "vocabulary", "enabling",
    "Device", "VOCABULARY", "FEELING_WORDS", "SEQUENCE_STEPS",
    "device", "all_devices", "read_feelings", "sequence_for", "fit",
    "Goal", "Path", "STRUCTURE_GOALS", "MEP_GOALS", "structure_paths", "mep_paths",
]
