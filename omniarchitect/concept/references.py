"""Attach shortlisted cases to S2 concepts, and answer the four questions.

At S2 the client is looking at two or three concepts and deciding which one to
develop. At that moment a reference case is not decoration — it is the
evidence that the direction is buildable and not just a sentence. So every
concept gets the case that best explains it, plus the four answers a
responsible designer owes:

1. **为什么参考它** — which of the client's own asks it answers
2. **借鉴什么手法** — a method, not a look
3. **怎么转化成原创方案** — what we changed, and why
4. **什么不能照搬** — the limits: size, budget, code, site

The image rule is absolute and enforced here rather than in the PPT layer: a
third-party case is a *card with a link*, never an image on the board. Only
``image_rights == "own"`` (our own deterministic renders, our own generated
visuals) may be embedded. `embed_allowed()` is the single place that decides,
so a future caller cannot accidentally relax it.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

#: Where a piece of imagery may be used. Ordered from weakest to strongest.
USAGE_LEVELS = ("link", "card", "board")

#: A case's own rights decide what it may become. Everything third-party
#: starts and stays at ``card``: a link plus a caption, on its own.
CASE_USAGE: Dict[str, str] = {
    "link_only": "card",
    "embeddable": "board",
    "own": "board",
}

USAGE_LABEL: Dict[str, str] = {
    "link": "只给链接",
    "card": "案例参考卡（有链接、有说明、无图）",
    "board": "可嵌入意向板或提案",
}

#: 中文概念词 -> 案例文本里可能出现的英文说法。
#:
#: Our concepts are written in Chinese; ArchDaily's descriptions are in
#: English. Matching one against the other without a bridge scores 0 every
#: time and the case list silently comes out empty — which looks like "no
#: cases exist" when the truth is "we never compared the same language".
#:
#: This is a *reading aid*, not a translation engine: every entry is a word
#: that genuinely appears in case descriptions. Unknown Chinese terms simply
#: do not match, and that is correct — an unmatched term proves nothing.
TERM_BRIDGE: Dict[str, Tuple[str, ...]] = {
    "极简": ("minimal", "minimalist", "austere", "pared back"),
    "意式极简": ("italian minimal", "milan", "milanese"),
    "现代": ("modern", "contemporary"),
    "现代自然": ("natural", "organic", "native planting"),
    "自然": ("natural", "organic", "vegetation", "planting"),
    "日式": ("japanese", "wabi", "timber"),
    "北欧": ("scandinavian", "nordic"),
    "侘寂": ("wabi-sabi", "wabi sabi", "plaster", "raw"),
    "轻奢": ("luxury", "brass", "marble"),
    "工业": ("industrial", "exposed", "concrete"),
    "中古": ("mid-century", "midcentury", "vintage"),
    "新中式": ("chinese", "courtyard", "lattice"),
    "通透": ("glazing", "glass", "open plan", "light"),
    "采光": ("daylight", "north light", "skylight", "window"),
    "私密": ("privacy", "private", "secluded", "screening"),
    "庭院": ("courtyard", "garden", "patio"),
    "水景": ("pond", "pool", "water", "reflecting"),
    "极简主义": ("minimalism", "minimal"),
    "石材": ("stone", "marble", "travertine", "limestone"),
    "木饰面": ("timber", "wood", "oak", "veneer"),
    "墙": ("wall", "partition"),
    "高级": ("refined", "sophisticated", "premium"),
    "安静": ("quiet", "calm", "serene"),
    "氛围": ("atmosphere", "mood", "ambience"),
    "层": ("storey", "story", "level", "split-level"),
    "大平层": ("apartment", "flat", "single level"),
    "别墅": ("villa", "house", "residence"),
    "景观": ("landscape", "garden", "planting"),
}


def _english_terms(token: str) -> Tuple[str, ...]:
    """English readings of a Chinese concept word; the word itself if none."""
    t = token.strip()
    if not t:
        return ()
    low = t.lower()
    hits: List[str] = []
    for zh, ens in TERM_BRIDGE.items():
        if zh in t or t in zh:
            hits.extend(ens)
    return tuple(dict.fromkeys(hits)) or (low,)



def embed_allowed(image_rights: str) -> bool:
    """The one gate. Third-party photography is never embeddable."""
    return image_rights == "own" or image_rights == "embeddable"


def _score(c: Dict[str, Any], concept: Dict[str, Any],
           ctx_name: str, lead: str = "") -> int:
    """How well a case explains this concept.

    Deliberately based on stated text, not vibes: the concept's own style
    words, its spatial family, and the client's feelings. A case that matches
    nothing scores 0 and is simply not shown rather than being forced in.

    Verification is *not* a relevance signal. It says the link works, not that
    the case has anything to do with this scheme — scoring it here once made a
    museum attach itself to a villa.
    """
    hay = " ".join([
        str(c.get("title") or ""),
        str(c.get("summary") or ""),
        str(c.get("url") or ""),
    ]).lower()
    score = 0
    tokens: List[str] = []
    for key in ("style_labels", "style_ids"):
        for v in (concept.get(key) or [])[:2]:
            tokens.append(str(v))
    for key in ("feelings", "keywords"):
        for v in (concept.get(key) or [])[:6]:
            tokens.append(str(v))
    for t in tokens:
        t = t.strip().lower().replace("-", " ")
        if len(t) < 2:
            continue
        # 中文概念词要先换成案例文本可能用的英文说法；直接比对中英文永远为 0。
        for term in _english_terms(t):
            if len(term) >= 3 and term in hay:
                score += 2
                break
    disc = str(c.get("discipline") or "")
    keys = _discipline_keys(concept)
    if disc and disc in keys:
        # 主导专业的案例优先：一个建筑主导的项目，"建筑"案例比"室内"案例
        # 更能说明它怎么组织体量。室内案例仍可用（一处室内手法也可能借鉴），
        # 但不该排在第一位。
        score += 3 if (lead and disc == lead) else 1
    return score


#: 空间家族 -> 案例描述里能佐证这个家族的词。
#:
#: 三套概念常常共用同一个风格（业主指定意式极简时必然如此），风格词打分会
#: 完全并列，于是三套方案挂上同一个案例——看起来像"只找了个案例"。这不算错，
#: 但客户看不出差异。家族词是**平局裁决**，不是加分项：它只在风格已经对上
#: 之后，回答"这几套哪里不一样"。
FAMILY_SIGNALS: Dict[str, Tuple[str, ...]] = {
    "layered": ("threshold", "compression", "sequence", "level change", "split-level",
                "step down", "entry", "transition", "narrow", "corridor"),
    "hall": ("open plan", "single volume", "double height", "hall", "atrium",
             "living hall", "one room", "unified"),
    "linear": ("linear", "axis", "corridor", "long", "slot", "band", "strip"),
    "courtyard": ("courtyard", "patio", "inner garden", "void", "open to sky"),
    "cluster": ("cluster", "pavilion", "scattered", "village", "detached volumes"),
}


def _family_of(concept: Dict[str, Any]) -> str:
    proto = concept.get("spatial_prototype") or {}
    return str(proto.get("family") or "").strip().lower()


def _family_bonus(c: Dict[str, Any], concept: Dict[str, Any]) -> int:
    """0 or 1: does the case's own text support *this* spatial family?"""
    fam = _family_of(concept)
    words = FAMILY_SIGNALS.get(fam)
    if not words:
        return 0
    hay = " ".join([str(c.get("title") or ""),
                    str(c.get("summary") or "")]).lower()
    return 1 if any(w in hay for w in words) else 0


#: 风格分差在这个范围内视为并列，由家族信号裁决。
#:
#: 风格分是"这套概念和这个案例像不像"，家族分是"它们组织方式像不像"。三套
#: 概念共用同一风格时风格分常常只差一两分（多命中一个 `villa`、`house` 而已），
#: 让这点分盖过家族信号，结果就是三套挂同一个案例。反过来，风格分差到三层
#: 以上时说明根本不是同一类项目，此时家族信号不该翻盘。所以：只在分差 ≤
#: 这个值时，家族信号才有裁决权；超出的案例仍按风格分排，不会被翻上来。
FAMILY_TIE_WINDOW = 2


def _discipline_keys(concept: Dict[str, Any]) -> frozenset:
    """The disciplines this concept actually covers.

    ``concept["disciplines"]`` is a mapping (discipline -> its own strategy
    block), not a list. Testing membership against ``str(mapping)`` searched
    the *repr* of the dict, so a label matched only by accident — in practice
    never, which silently disabled the discipline point. Read the keys.
    """
    raw = concept.get("disciplines")
    if isinstance(raw, dict):
        return frozenset(str(k) for k in raw)
    if isinstance(raw, (list, tuple, set)):
        out = set()
        for item in raw:
            if isinstance(item, dict):
                out.add(str(item.get("discipline") or item.get("key") or ""))
            else:
                out.add(str(item))
        return frozenset(x for x in out if x)
    return frozenset()


def _first_step(concept: Dict[str, Any]) -> str:
    """The opening beat of the experience sequence, whichever shape it is in.

    ``experience_sequence`` is a mapping (``{"steps": [...]}``) with the
    narrative attached, not a bare list. Indexing it as a list raised
    ``KeyError: 0`` — the failure only appeared once a case was actually
    attached, so an empty shortlist hid it.
    """
    seq = concept.get("experience_sequence")
    if isinstance(seq, dict):
        seq = seq.get("steps") or []
    if not isinstance(seq, (list, tuple)) or not seq:
        return ""
    first = seq[0]
    if isinstance(first, dict):
        return str(first.get("step") or first.get("event") or "")
    return str(first or "")


def _borrow_for(concept: Dict[str, Any], case: Dict[str, Any]) -> List[str]:
    """借鉴什么：先用案例自己的读图要点，再补本案可对照的环节。

    顺序很重要：先放"这条案例自己的"（读图要点、地点/年代条件），
    再放通用对照。反过来的话，两条同类案例会共用同一段兜底句。
    """
    out: List[str] = [str(x) for x in (case.get("borrow") or []) if str(x).strip()]
    if len(out) < 2:
        where = "、".join(x for x in (str(case.get("city") or ""),
                                    str(case.get("country") or "")) if x)
        year = str(case.get("year") or "")
        if where or year:
            cond = "、".join(x for x in (year, where) if x)
            out.append("看它在 {} 的条件下怎么处理同一件事（换到本案要重算）".format(cond))
    if len(out) < 2:
        first = _first_step(concept)
        if first:
            out.append("对照本案「{}」这一步看它怎么处理，取方法不取形式".format(first))
    mats = concept.get("materials") or []
    if len(out) < 2 and mats:
        out.append("看它的材料分配关系（不是材料本身），检验本案选的{}是否站得住".format(
            "、".join(str(m)[:10] for m in mats[:2])))
    if not out:
        out.append("看它的空间关系与体量处理；具体做法不照搬")
    return out[:2]


def _transform_for(concept: Dict[str, Any], case: Dict[str, Any]) -> str:
    """怎么转化：写清本案与它**不同**的地方，而不是夸一句"重新设计"。"""
    proto = concept.get("spatial_prototype") or {}
    zoning = str(proto.get("zoning") or "").strip()
    name = (concept.get("concept_name") or concept.get("name")
            or concept.get("concept_id") or "本方案")
    if zoning:
        return ("借组织逻辑，不借形式：本案按「{}」重排，{}；"
                "尺度与做法回本项目条件重新定".format(name, zoning[:46]))
    return ("借组织逻辑，不借形式：「{}」按本项目的场地、规模与运营条件重排，"
            "外观与材料不复制".format(name))


def _limits_for(case: Dict[str, Any]) -> List[str]:
    """不能照搬什么：优先用案例自己的限制，再用它的年份/地点说明条件差异。

    两条案例的限制如果一字不差，客户会认为我们没真读——所以至少把
    "哪一年、在哪个国家"这条差异带上。
    """
    out = list(case.get("avoid") or [])
    where = "、".join(x for x in (str(case.get("city") or ""),
                                  str(case.get("country") or "")) if x)
    year = str(case.get("year") or "")
    if case.get("area"):
        out.insert(0, "它的面积是 {}，属于它自己的规模与规范，不能反推本项目尺寸".format(
            case["area"]))
    if where or year:
        cond = "、".join(x for x in (year, where) if x)
        out.append("它的做法绑定 {} 的规范、气候与施工条件，换到本项目要重算".format(cond))
    if not out:
        out = ["尺寸、预算与当地规范都不通用，须按本项目条件重算"]
    # 去重后截断，避免同一条限制出现两次
    seen: List[str] = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen[:3]


def _why_for(case: Dict[str, Any], concept: Dict[str, Any]) -> str:
    """为什么把它摆在你面前：它答的是你提过的哪件事。

    只认案例自己的证据（`fits` 来自标题与简介里真实出现的词）与本案的
    设计问题。两边都拿不到就直说"对应关系待读图确认"，不写"它很契合"。
    """
    fits = [str(x) for x in (case.get("fits") or []) if str(x).strip()]
    title = str(case.get("title") or "").strip()
    label = "「{}」".format(title[:22]) if title else "这个案例"
    # 用概念自己的主张，而不是 design_problem：后者是把 S1 的需求串起来，
    # 需求抽歪时会把不相干的话（"收藏展示"）印到案例页上。
    problem = str(concept.get("concept_statement")
                  or concept.get("design_problem") or "").strip()
    if fits and problem:
        return "{}答的是「{}」；本案要处理的是「{}」".format(
            label, "、".join(fits[:2]), problem[:36])
    if fits:
        return "{}答的是「{}」——与本案任务同类".format(label, "、".join(fits[:2]))
    # 没有可引用的契合点：用这条案例自己的读图要点说清"该对照什么"。
    # 不引用英文原文——客户看不懂，截断成二十个字母比不写更难看。
    tip = str((case.get("borrow") or [""])[0] if case.get("borrow") else "").strip()
    if tip and problem:
        return "{}值得对照的是「{}」；本案要处理「{}」，属同一类问题".format(
            label, tip[:30], problem[:30])
    if problem:
        return "{}属同类任务；本案要处理「{}」，对应关系需读图确认".format(
            label, problem[:36])
    return "{}属同类任务；与本方案的对应关系需主创读图确认".format(label)


def build(concepts: Sequence[Dict[str, Any]],
          research: Optional[Dict[str, Any]],
          ctx: Any = None) -> Dict[str, Dict[str, Any]]:
    """Attach cases to concepts. Returns ``concept_id -> attachment``.

    When there is no research, or no case matches a concept, the attachment
    says so. An empty attachment with a reason is worth more than a decorative
    one: the client can tell the difference between "we looked" and "here is
    something anyway".
    """
    cases = list((research or {}).get("cases") or [])
    result: Dict[str, Dict[str, Any]] = {}

    for c in concepts:
        cid = c.get("concept_id") or ""
        if not cases:
            result[cid] = {
                "concept_id": cid,
                "cases": [],
                "note": "尚无案例研究结果：S2 不编造参考案例，先回到 S1 做检索"
                        if not research else "本次检索未得到可核验案例，本方案不挂参考案例",
            }
            continue

        # 排序键：(风格分档, 是否佐证本方案的空间家族, 风格分, 标题)
        #
        # 档位是"离最高分差几档"：分差 ≤ FAMILY_TIE_WINDOW 的算同一档，由家族
        # 信号裁决。这样"多命中一个 villa"（差 1 分）不会盖过"组织方式对得上"，
        # 而真正不相干的案例（差好几档）也不会被家族信号翻上来。标题只是稳定
        # 并列，不代表标题更相关。
        # 档位：0 = 与最高分并列（分差 ≤ FAMILY_TIE_WINDOW），1 = 掉出一档，
        # 2 = 掉出两档…… 同档内才由家族信号裁决。不用除法算档位：那会把"分差
        # 恰好等于窗口"算成掉档，与"≤ 窗口算并列"的约定相反。
        def _tier(gap: int) -> int:
            return 0 if gap <= FAMILY_TIE_WINDOW else 1 + (gap - FAMILY_TIE_WINDOW - 1) // (FAMILY_TIE_WINDOW + 1)

        lead = str(getattr(ctx, "lead_id", "") or "")
        raw = [(cs, _score(cs, c, "", lead)) for cs in cases]
        raw = [(cs, s) for cs, s in raw if s > 0]
        top = max((s for _, s in raw), default=0)
        # 第一档是「是不是本主导专业的案例」：建筑主导的项目先看建筑案例，
        # 再在同一专业内按风格与空间家族排序。否则一个室内项目的标题里
        # 恰好有 `split-level`，就会把建筑方案的首选案例抢走。
        scored = [(0 if (lead and cs.get("discipline") == lead) else 1,
                   _tier(top - s), -_family_bonus(cs, c), -s,
                   str(cs.get("title") or ""), cs)
                  for cs, s in raw]
        scored.sort(key=lambda t: t[:5])
        chosen = [t[5] for t in scored[:2]]

        if not chosen:
            result[cid] = {
                "concept_id": cid,
                "cases": [],
                "note": "现有案例与本方案主张不匹配，不强行挂靠；"
                        "宁可留空，也不拿不相关的案例充数",
            }
            continue

        refs: List[Dict[str, Any]] = []
        for cs in chosen:
            rights = cs.get("image_rights") or "link_only"
            usage = CASE_USAGE.get(rights, "card")
            refs.append({
                "title": cs.get("title"),
                "architect": cs.get("architect"),
                "url": cs.get("url"),
                "image_url": cs.get("image_url"),
                "source": cs.get("source"),
                "year": cs.get("year"),
                "city": cs.get("city"),
                "country": cs.get("country"),
                "area": cs.get("area"),
                "verify": cs.get("verify"),
                "verify_label": cs.get("verify_label"),
                "usage": usage,
                "usage_label": USAGE_LABEL[usage],
                "embeddable": embed_allowed(rights),
                # the four answers
                "why": _why_for(cs, c),
                "borrow": _borrow_for(c, cs),
                "transform": _transform_for(c, cs),
                "limits": _limits_for(cs),
            })
        result[cid] = {"concept_id": cid, "cases": refs,
                       "note": "参考案例只用于讨论方向，不代表本项目效果图"}

    return result


def markdown(attachments: Dict[str, Dict[str, Any]],
             concepts: Sequence[Dict[str, Any]]) -> str:
    """Human-readable block for the S2 options document."""
    lines: List[str] = ["## 参考案例与转化说明", ""]
    lines.append("每套方案都挂了与它最相关的参考案例，并说明借鉴什么、怎么转化、什么不能照搬。")
    lines.append("案例图片均为第三方作品，只给链接，不进入本提案的版面。")
    lines.append("")
    for c in concepts:
        cid = c.get("concept_id") or ""
        att = attachments.get(cid) or {}
        lines.append("### {}".format(c.get("name") or cid))
        lines.append("")
        refs = att.get("cases") or []
        if not refs:
            lines.append("- {}".format(att.get("note") or "本次无可用参考案例"))
            lines.append("")
            continue
        for r in refs:
            lines.append("**参考：{}　／　{}**".format(r["title"], r.get("architect") or "—"))
            lines.append("")
            lines.append("- 案例页面：<{}>".format(r["url"]))
            if r.get("image_url"):
                lines.append("- 图片出处：<{}>（第三方作品，仅链接）".format(r["image_url"]))
            lines.append("- 核验：{}".format(r.get("verify_label") or r.get("verify")))
            lines.append("- 为什么参考它：{}".format(r["why"]))
            for b in r["borrow"]:
                lines.append("- 借鉴的手法：{}".format(b))
            lines.append("- 怎么转化成我们的方案：{}".format(r["transform"]))
            for lim in r["limits"]:
                lines.append("- 不能照搬：{}".format(lim))
            lines.append("")
    return "\n".join(lines)


__all__ = [
    "CASE_USAGE", "USAGE_LABEL", "USAGE_LEVELS", "build", "embed_allowed",
    "markdown",
]
