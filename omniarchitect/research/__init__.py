"""Professional case research and reference-image recommendation.

One job: when a client has described a project, go and find real, openable,
relevant built work — and be explicit about what could not be found.

The first destination is always the first-party library (Luxora AI), whose only
address lives in ``omniarchitect/paths.py``. Anything else is a *supplement*,
and a supplement is only worth showing if a script could actually read it.

Division of labour:

| module | answers |
|---|---|
| `sources` | where references come from, what each may be used for, what was measured |
| `brief` | what to research for this project type, without waiting for G1 |
| `cases` | real retrieval, with verification and honest failure |
| `report` | the two artifacts a client and the downstream stages read |
| `research` | the orchestration and where state lives |

The rule that shapes every module here: **an empty, explained result is
correct; a plausible invented one is not.** A client who is shown six real
projects with working links is being helped. A client shown eight convincing
fakes is being robbed of the ability to judge the design.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from .brief import (
    ASPECTS,
    DEFAULT_AVOID,
    Direction,
    ResearchBrief,
    derive,
    should_start,
)
from .cases import (
    CATEGORY_PAGES,
    VERIFY_LABEL,
    VERIFY_STATES,
    Case,
    Fetch,
    SearchLog,
    fetch,
    manual_entries,
    parse_detail,
    parse_listing,
    search,
)
from .report import SHORTLIST_JSON, SHORTLIST_MD, ResearchResult, write
from .research import allocate, load, run, summary_lines
from .sources import (
    ACCESS_LABEL,
    FIRST_PARTY,
    IMAGE_RIGHTS_LABEL,
    KIND_LABEL,
    KIND_ORDER,
    SEARCH_LABEL,
    SOURCES,
    SOURCE_INDEX,
    Source,
    case_sources,
    recommend,
    registry_markdown,
)

__all__ = [
    "ACCESS_LABEL", "ASPECTS", "CATEGORY_PAGES", "DEFAULT_AVOID", "Direction",
    "FIRST_PARTY", "Fetch", "IMAGE_RIGHTS_LABEL", "KIND_LABEL", "KIND_ORDER",
    "ResearchBrief", "ResearchResult", "SEARCH_LABEL", "SHORTLIST_JSON",
    "SHORTLIST_MD", "SOURCES", "SOURCE_INDEX", "SearchLog", "Source",
    "VERIFY_LABEL", "VERIFY_STATES", "allocate", "case_sources", "derive",
    "fetch", "load", "manual_entries", "parse_detail", "parse_listing",
    "recommend", "registry_markdown", "run", "search", "should_start",
    "summary_lines", "write",
]
