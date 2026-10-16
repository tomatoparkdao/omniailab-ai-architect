"""设计风格系统 —— OmniAiLab AI Architect 的内部专业模块。

**这个模块不是第二个 Skill。** 它是 `omniailab-ai-architect` 内部的一个专业域，
和 `providers/`、`tools/`、`presentation/` 一样，由主 Skill 直接发现和调用：
没有独立安装、没有独立入口、没有独立仓库。

它原先是一个独立工程（Design Style Intelligence），因此带着自己的 `paths.py`、
自己的平台探测、自己的署名逻辑和自己的 CLI 入口。合并时这些**重复实现全部删除**，
改为引用主包的唯一来源：

| 原先自己实现 | 现在来自 |
|---|---|
| 项目根与目录常量 | `omniarchitect.paths` |
| 平台探测与契约校验 | `omniarchitect.providers` |
| 署名与 front-matter | `omniarchitect.registry` |
| 八阶段与门禁定义 | `omniarchitect.stages` |
| CLI 入口 | 挂到主 CLI 的 `style` 子命令 |

它提供的能力：47 种建筑与室内设计风格的结构化知识库、按需加载与检索、
三方案风格推荐、风格与空间关系检查、材料与灯光体系提取、
中英双语结构化提示词编译（8 种目标）、以及跨机位一致性约束。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from ..paths import project_version

__version__ = project_version()

from .catalog import Catalog, StyleEntry, load_catalog                       # noqa: E402
from .compiler import (                                                      # noqa: E402
    CompiledPrompt,
    SpaceBrief,
    compile_prompt,
    compile_view_set,
)
from .hooks import (                                                         # noqa: E402
    HOOKED_STAGES,
    all_hooks,
    frame_source,
    gate,
    gate_label,
    hook,
    stage_name,
)
from .provider_bridge import (                                               # noqa: E402
    CREATIVE_SCOPES,
    ProviderStatus,
    probe,
    submit,
)
from .recommender import (                                                   # noqa: E402
    Recommendation,
    RecommendationSet,
    RecommendRequest,
    recommend,
)
from .resources import (                                                     # noqa: E402
    CATALOG_FILE,
    PROMPT_TARGETS,
    STYLE_DIR,
    TARGET_STAGES,
    stamped,
)
from .validation import StyleValidationError, validate_style                 # noqa: E402

__all__ = [
    # 知识库与检索
    "Catalog", "StyleEntry", "load_catalog", "STYLE_DIR", "CATALOG_FILE",
    # 推荐
    "RecommendRequest", "Recommendation", "RecommendationSet", "recommend",
    # 提示词编译
    "compile_prompt", "compile_view_set", "CompiledPrompt", "SpaceBrief",
    "PROMPT_TARGETS", "TARGET_STAGES",
    # 八阶段挂钩
    "hook", "all_hooks", "HOOKED_STAGES", "gate", "gate_label", "stage_name",
    "frame_source",
    # 生成出口（唯一主体：OmniAiLab 平台）
    "submit", "probe", "ProviderStatus", "CREATIVE_SCOPES",
    # 数据校验与署名
    "validate_style", "StyleValidationError", "stamped",
    "__version__",
]
