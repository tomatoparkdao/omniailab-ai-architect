"""Paths, constants and the attribution helper for the design-style module.

This module was a separate project's `paths.py`. Now that the style system lives
inside the main skill, every path resolves through the main package's own
`omniarchitect.paths`, so there is exactly one definition of "where is the
project root" in the repository.

Nothing here is fetched at runtime. The style knowledge is local, original data;
the only network capability is the OmniAiLab platform, and that is opt-in and
never triggered implicitly.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import List

# 路径常量复用主包的唯一定义，不再自己推算 ROOT。
from ..paths import (  # noqa: F401
    DOCS,
    EXAMPLES,
    KNOWLEDGE,
    ROOT,
    SCHEMAS,
    project_version,
)

# --------------------------------------------------------------------------
# 风格数据
STYLE_DIR = KNOWLEDGE / "styles"
CATALOG_FILE = STYLE_DIR / "catalog.json"

# 本模块自己产出的索引文件名。它住在风格数据目录里，但**不是**一条风格记录 ——
# 扫描风格数据的每一处都必须把它排除，否则它会被当成一条缺了二十个字段的坏数据。
INDEX_FILENAME = "catalog.json"
STYLE_SCHEMA = SCHEMAS / "design-style.schema.json"
PROMPT_SCHEMA = SCHEMAS / "compiled-prompt.schema.json"

# --------------------------------------------------------------------------
# 阶段挂钩范围
#
# S1 是需求接单（还没有风格可选）、S6 是设计冻结（风格已锁定并随修订号追踪），
# 两步不挂风格动作。阶段 id 的权威定义在 `omniarchitect.stages`。
HOOKED_STAGES = ("S2", "S3", "S4", "S5", "S7", "S8")

# --------------------------------------------------------------------------
# 提示词编译器可产出的目标类型
#
# 前八种是"空间长什么样"；后六种来自 `recipes.py` 的**表现技法库**——
# 把已确认的平面/立面转成业主看得懂的图与板。两族的边界写死在那里，
# 这里**派生**而不是重抄，避免同一件事在两处各说一套。
from .recipes import RECIPES as _RECIPES  # noqa: E402  (no cycle: recipes 不反向依赖)

_LEGACY_TARGETS = (
    "concept",            # 概念图
    "moodboard",          # 情绪板（拼贴版面）
    "interior-render",    # 室内效果图
    "exterior-render",    # 建筑外观图
    "material-closeup",   # 材料特写
    "partial-renovation", # 局部改造
    "multi-view",         # 多视角效果图
    "walkthrough-video",  # 漫游视频
)

PROMPT_TARGETS = _LEGACY_TARGETS + tuple(_RECIPES)

# 每种目标通常用在哪些阶段。
TARGET_STAGES = {
    "concept": ("S2",),
    "moodboard": ("S2",),
    "interior-render": ("S4", "S5"),
    "exterior-render": ("S4", "S5"),
    "material-closeup": ("S4", "S7"),
    "partial-renovation": ("S6", "S7"),
    "multi-view": ("S5",),
    "walkthrough-video": ("S5",),
}
TARGET_STAGES.update({rid: tuple(r.stages) for rid, r in _RECIPES.items()})


def style_files(style_dir: Path | None = None) -> List[Path]:
    """Every style record in the catalogue directory — index excluded.

    Single definition, used by the index builder and by the validator, so the
    two can never disagree about what counts as a style.
    """
    from pathlib import Path as _P

    d = style_dir or STYLE_DIR
    return [p for p in sorted(_P(d).glob("*.json")) if p.name != INDEX_FILENAME]


def stamped(body: str, *, name: str = "", description: str = "") -> str:
    """Wrap a generated document with the repository's front-matter and signature.

    The header and the footer come from the main package's single source
    (`omniarchitect.registry`), so a document produced by the style module can
    never carry a different version or a different signature than one produced
    anywhere else in the skill.
    """
    from ..registry import SIGNATURE, frontmatter_block

    out = ""
    if name:
        out += frontmatter_block(name, description) + "\n"
    out += body.rstrip("\n")
    out += "\n\n---\n" + SIGNATURE + "\n"
    return out
