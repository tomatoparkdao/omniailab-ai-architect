"""Turn an unfinished S1 into a research direction.

The rule this module exists to enforce: **case research does not wait for G1**.
A client who says "three-storey minimalist villa with a courtyard" has already
told us enough to start looking, and making them answer twenty questions first
is how a design brief turns into a form.

So the trigger is deliberately early. As soon as S1 knows the project type
(and optionally the dominant discipline, style and feelings), ``derive()``
produces:

- which disciplines to research (architecture / interior / landscape)
- which *aspects* to look at, per discipline, for this project type
- the query terms to use, split into `idea` (what to look for) and `avoid`
  (what would mislead)

Nothing here is a guess about the project. Aspects come from a fixed table
keyed by project type; query terms come from what the client actually said
plus the discipline vocabulary. When information is missing the direction says
so instead of filling the gap.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..design import vocabulary
from ..disciplines import DISCIPLINES


def _disc_label(key: str) -> str:
    """Chinese label for a discipline key; the registry is not a string map."""
    obj = DISCIPLINES.get(key)
    return getattr(obj, "label", key) or key

# --------------------------------------------------------------------------
# what to look at, by project type
# --------------------------------------------------------------------------
#: Project-type -> discipline -> aspects worth studying.
#:
#: These are the questions a senior designer actually opens a case for. A
#: villa case is useful for its massing, its facade depth, its courtyard, and
#: how inside meets outside — not for its kitchen cabinet hardware.
ASPECTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "architecture": {
        "architecture": ("建筑形态与体量关系", "立面开合与材料分层",
                          "庭院/景观与建筑的关系", "室内外过渡与视线控制"),
        "interior": ("公共区空间序列", "主卧区私密性处理", "材料与光的关系"),
        "landscape": ("庭院空间层级", "水景与建筑的关系", "植物与硬景比例"),
    },
    "residential": {
        "architecture": ("套内空间结构（可改性）",),
        "interior": ("空间氛围与整体调性", "材料搭配与收口",
                      "自然采光与人工照明", "家具尺度与动线", "细部做法"),
        "landscape": ("阳台/露台与室内的关系",),
    },
    "hospitality": {
        "architecture": ("建筑与场地的关系", "到达体验"),
        "interior": ("公共区域的空间节奏", "客房体验与私密性",
                      "品牌氛围的表达方式", "灯光与材料的配合"),
        "landscape": ("入口与庭院体验",),
    },
    "retail": {
        "architecture": ("店面与街道的关系",),
        "interior": ("动线与停留点", "视觉焦点与陈列", "灯光层次"),
        "landscape": ("外摆与过渡空间",),
    },
    "exhibition": {
        "architecture": ("建筑形态与城市界面",),
        "interior": ("参观动线与节奏", "展陈与空间的一体化"),
        "landscape": ("室外展场与集散",),
    },
    "office": {
        "architecture": ("建筑与办公效率的关系",),
        "interior": ("开放与封闭的比例", "协作区与专注区", "公共区体验"),
        "landscape": ("室外休憩空间",),
    },
    "landscape": {
        "landscape": ("景观空间布局", "植物配置与季相", "水景与铺装",
                       "庭院体验与动线", "维护条件"),
    },
}

#: Aspect table keyed by the intake profile id when it differs from type.
PROFILE_TO_TYPE: Dict[str, str] = {
    "residential": "residential",
    "office": "office",
    "hospitality": "hospitality",
    "retail": "retail",
    "exhibition": "exhibition",
    "architecture": "architecture",
}

#: Words that must not appear in what we show a client, because they describe
#: other people's budgets and sites rather than design intent.
DEFAULT_AVOID: Tuple[str, ...] = ("效果图风格", "网红", "无来源图片")


@dataclass
class Direction:
    """One discipline's research brief."""

    discipline: str
    aspects: Tuple[str, ...]
    idea: Tuple[str, ...]
    avoid: Tuple[str, ...] = DEFAULT_AVOID
    sources: Tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discipline": self.discipline,
            "discipline_label": _disc_label(self.discipline),
            "aspects": list(self.aspects),
            "idea": list(self.idea),
            "avoid": list(self.avoid),
            "sources": list(self.sources),
            "note": self.note,
        }


@dataclass
class ResearchBrief:
    """What to research, and how confident we are that it is the right target."""

    project_type: str
    project_type_label: str
    disciplines: Tuple[str, ...]
    directions: Tuple[Direction, ...]
    trigger: str
    readiness: str
    missing: Tuple[str, ...] = ()
    feelings: Tuple[str, ...] = ()
    style: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_type": self.project_type,
            "project_type_label": self.project_type_label,
            "disciplines": list(self.disciplines),
            "directions": [d.to_dict() for d in self.directions],
            "trigger": self.trigger,
            "readiness": self.readiness,
            "missing": list(self.missing),
            "feelings": list(self.feelings),
            "style": self.style,
            "note": self.note,
        }


# --------------------------------------------------------------------------
# reading the project
# --------------------------------------------------------------------------
def _answer(project: Any, slot: str) -> str:
    """Read a slot from the interview store, falling back to constraints."""
    try:
        from ..intake.interview import load_interview

        state = load_interview(project)
        answers = state.get("answers") or {}
        from ..intake.profiles import QUESTION_INDEX

        for qid, ans in answers.items():
            q = QUESTION_INDEX.get(qid)
            if q and q.slot == slot and ans.get("state") in ("answered", "assumed"):
                return str(ans.get("value") or "")
    except Exception:
        pass
    cons = getattr(project, "constraints", None) or {}
    if slot == "style":
        return str(cons.get("style") or "")
    if slot == "project_type":
        return str(cons.get("project_type") or "")
    return ""


#: Client words that mean "a new building", not "a fit-out". The intake profile
#: cannot separate these on its own — both land in `residential` — but the
#: research direction is completely different, so the split happens here.
NEW_BUILD_WORDS: Tuple[str, ...] = (
    "新建", "自建", "盖", "地块", "有块地", "宅基地", "独栋", "别墅", "土建",
    "毛坯", "报建", "扩建", "改建", "加建",
)

FITOUT_WORDS: Tuple[str, ...] = (
    "精装", "精装修", "大平层", "公寓", "旧房", "翻新", "软装", "硬装", "改造",
)

#: Client words that mean the outdoor work is the project itself.
PURE_LANDSCAPE_WORDS: Tuple[str, ...] = (
    "庭院", "花园", "景观", "院子", "露台", "屋顶花园", "水景", "绿化",
)


def classify(project: Any, declared: str = "") -> str:
    """Which aspect table to use: architecture / residential / landscape.

    Three cases that the intake profile merges but research must not:

    - ``architecture`` a new building (massing, facade, courtyard)
    - ``residential``  a fit-out inside an existing shell
    - ``landscape``    outdoor work as the whole job
    """
    text = " ".join([declared, getattr(project, "name", "") or "",
                     str((getattr(project, "constraints", None) or {}).get("style") or "")])
    has_new = any(w in text for w in NEW_BUILD_WORDS)
    has_fit = any(w in text for w in FITOUT_WORDS)
    has_land = any(w in text for w in PURE_LANDSCAPE_WORDS)

    if has_new and not has_fit:
        return "architecture"
    if has_fit and not has_new:
        return "residential"
    if has_land and not has_new and not has_fit:
        return "landscape"
    if has_new:
        return "architecture"
    return "residential"


def _profile_id(project: Any) -> str:
    try:
        from ..intake.interview import load_interview

        state = load_interview(project)
        pid = state.get("profile_id")
        if pid and pid in PROFILE_TO_TYPE:
            return pid
    except Exception:
        pass
    from ..intake.profiles import profile_for

    # Feed the declared project type into the matcher as well as the name —
    # "新建别墅" only appears in `constraints`, never in a project name.
    declared = ""
    try:
        declared = _answer(project, "project_type")
    except Exception:
        declared = ""
    prof = profile_for(declared, getattr(project, "name", "") or "",
                       str((getattr(project, "constraints", None) or {}).get("style") or ""))
    return prof.id


def _active_disciplines(project: Any, aspect_type: str = "") -> Tuple[str, ...]:
    """Which disciplines have a case to research.

    Uses the S1 discipline scope when it exists; otherwise infers from what the
    project actually contains. A pure-fit-out flat has no landscape case to
    study, and pretending otherwise wastes the client's attention.

    ``aspect_type`` matters because a brand-new villa with a courtyard has no
    spaces modelled yet at the moment we research — geometry is empty, but the
    job plainly includes a building and a garden.
    """
    try:
        from .. import disciplines as disc

        scope = disc.ensure(project)
        active = tuple(scope.active())
        if active and len(active) > 1:
            return active
        if active and aspect_type == "architecture":
            # Geometry is empty but the client asked for a new build; the
            # scope engine only sees 'landscape' from the words so far.
            return tuple(dict.fromkeys(("architecture",) + active))
        if active:
            return active
    except Exception:
        pass

    out: List[str] = []
    if aspect_type == "architecture":
        out.append("architecture")
    if getattr(project, "levels", None) and "architecture" not in out:
        out.append("architecture")
    if getattr(project, "spaces", None):
        out.append("interior")
    if getattr(project, "elements", None):
        out.append("landscape")
    if aspect_type == "landscape" and "landscape" not in out:
        out.append("landscape")
    if aspect_type == "residential" and "interior" not in out:
        out.append("interior")
    if not out:
        out.append("interior")
    return tuple(dict.fromkeys(out))


def _feeling_words(project: Any) -> Tuple[str, ...]:
    """Client's own words for how the space should feel, mapped to devices."""
    raw: List[str] = []
    for slot in ("feeling", "style"):
        v = _answer(project, slot)
        if v:
            raw.append(v)
    try:
        from ..intake.interview import load_interview

        state = load_interview(project)
        for ans in (state.get("answers") or {}).values():
            if ans.get("state") in ("answered", "assumed") and ans.get("value"):
                raw.append(str(ans["value"]))
    except Exception:
        pass
    text = " ".join(raw)
    try:
        hits = vocabulary.read_feelings(text)
    except Exception:
        return ()
    return tuple(hits or ())


def _query_terms(project: Any, discipline: str,
                 feelings: Sequence[str], style: str,
                 project_type: str) -> Tuple[str, ...]:
    """Terms to search with. English because the scriptable source is English.

    ``project_type`` here is the *aspect* type from `classify()`, not the
    intake profile id: searching "apartment renovation" for a new villa with a
    courtyard is how a case list ends up irrelevant.
    """
    terms: List[str] = []
    t = (project_type or "").lower()
    if discipline == "architecture":
        base = {
            "architecture": ["villa", "courtyard"],
            "residential": ["apartment building", "renovation"],
            "hospitality": ["hotel", "retreat"],
            "retail": ["restaurant", "cafe"],
            "exhibition": ["museum", "pavilion"],
            "office": ["office building", "workplace"],
        }.get(t, ["house", "villa"])
        terms.extend(base[:2])
    elif discipline == "interior":
        base = {
            "architecture": ["interior design", "living room"],
            "residential": ["apartment interior", "residential interior"],
            "hospitality": ["hotel interior", "lobby"],
            "retail": ["restaurant interior", "retail interior"],
            "exhibition": ["gallery interior"],
            "office": ["office interior", "workspace"],
        }.get(t, ["interior design"])
        terms.extend(base[:2])
    elif discipline == "landscape":
        base = {
            "architecture": ["courtyard", "garden"],
            "residential": ["terrace", "balcony"],
            "landscape": ["private garden", "courtyard"],
            "hospitality": ["hotel garden"],
            "retail": ["outdoor seating"],
            "exhibition": ["museum garden"],
            "office": ["courtyard office"],
        }.get(t, ["garden", "courtyard"])
        terms.extend(base[:2])

    # style words the client used, translated through the style vocabulary
    for w in [style] + list(feelings):
        if not w:
            continue
        for token in str(w).replace("，", " ").replace("、", " ").split():
            token = token.strip()
            if token and token not in terms and len(token) <= 12:
                terms.append(token)
    return tuple(dict.fromkeys(terms))[:6]


def _readiness(project: Any) -> Tuple[str, Tuple[str, ...], str]:
    """Can we research yet? What is still missing? Be honest about it."""
    from ..intake.interview import completeness

    try:
        comp = completeness(project)
    except Exception:
        comp = {"verdict": "thin", "missing": [], "ratio": 0.0}
    missing = tuple(comp.get("missing") or ())
    verdict = comp.get("verdict") or "thin"
    if verdict == "thin" and not missing:
        return "early", (), "信息很少，按项目类型先给方向性参考，不作为结论"
    if verdict == "thin":
        return "early", missing, "信息仍少，先做方向性检索；有更具体的诉求再收紧"
    return "workable", missing, "已足以做定向检索"


# --------------------------------------------------------------------------
# derive
# --------------------------------------------------------------------------
def derive(project: Any) -> ResearchBrief:
    """Build the research direction from whatever S1 already knows."""
    pid = _profile_id(project)
    ptype = PROFILE_TO_TYPE.get(pid, "residential")

    declared_type = _answer(project, "project_type")
    style = _answer(project, "style")
    feelings = _feeling_words(project)

    # `ptype` comes from the intake profile, which merges "new villa" and
    # "flat fit-out" into `residential`. Research must not: the same
    # `residential` profile yields three different study lists depending on
    # whether the client is building, fitting out, or landscaping.
    aspect_type = classify(project, declared_type)
    disciplines = _active_disciplines(project, aspect_type)
    readiness, missing, readiness_note = _readiness(project)

    table = ASPECTS.get(aspect_type) or ASPECTS.get(ptype) or ASPECTS["residential"]

    directions: List[Direction] = []
    for disc in disciplines:
        aspects = tuple(table.get(disc) or ())
        if not aspects:
            continue
        idea = _query_terms(project, disc, feelings, style, aspect_type)
        from .sources import case_sources

        src = tuple(s.id for s in case_sources(disc))
        note = ""
        if disc == "landscape" and not aspects:
            note = "本项目无景观范围，不做景观案例研究"
        directions.append(Direction(
            discipline=disc, aspects=aspects, idea=idea,
            sources=src, note=note,
        ))

    trigger = "S1 已识别项目类型" if declared_type else "S1 已推断项目类型"
    if feelings:
        trigger += "、业主感受词"
    if style:
        trigger += "、风格倾向"

    return ResearchBrief(
        project_type=ptype,
        project_type_label=declared_type or _disc_label(ptype),
        disciplines=disciplines,
        directions=tuple(directions),
        trigger=trigger,
        readiness=readiness,
        missing=missing,
        feelings=feelings,
        style=style,
        note=readiness_note,
    )


def should_start(project: Any) -> Tuple[bool, str]:
    """The trigger rule, stated once so every caller agrees.

    Start as soon as a project type exists. Do **not** wait for a complete
    interview and do **not** wait for G1 — the whole point is that the client
    sees relevant work while they are still describing the project.
    """
    pid = _profile_id(project)
    declared = _answer(project, "project_type")
    if pid or declared:
        return True, "项目类型已确定，可以开始初步案例研究"
    return False, "连项目类型都还没有，先问出用途再检索"


__all__ = [
    "ASPECTS", "DEFAULT_AVOID", "Direction", "PROFILE_TO_TYPE", "ResearchBrief",
    "derive", "should_start",
]
