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


def embed_allowed(image_rights: str) -> bool:
    """The one gate. Third-party photography is never embeddable."""
    return image_rights == "own" or image_rights == "embeddable"


def _score(c: Dict[str, Any], concept: Dict[str, Any],
           ctx_name: str) -> int:
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
        if len(t) >= 3 and t in hay:
            score += 2
    if c.get("discipline") and c.get("discipline") in str(concept.get("disciplines")):
        score += 1
    return score


def _borrow_for(concept: Dict[str, Any], case: Dict[str, Any]) -> List[str]:
    """What we take from the case, phrased as method tied to this concept."""
    out: List[str] = []
    seq = concept.get("experience_sequence") or []
    if seq:
        first = seq[0] if isinstance(seq[0], str) else str(seq[0].get("step") or "")
        if first:
            out.append("它的入场处理可以直接对照你的「{}」这一步，看它是怎么收住视线的".format(first))
    mats = concept.get("materials") or []
    if mats:
        out.append("它的材料分布关系（不是材料本身）可用来检验你选的{}是否站得住".format(
            "、".join(str(m)[:10] for m in mats[:2])))
    if not out:
        out.append("主要看它的空间关系与体量处理，不照搬具体做法")
    return out[:2]


def _transform_for(concept: Dict[str, Any], case: Dict[str, Any]) -> str:
    """How the case becomes *this* project's own scheme."""
    name = concept.get("name") or concept.get("concept_id") or "本方案"
    return ("「{}」借的是它的组织逻辑，落地时按你的地块、层数和实测尺寸重排；"
            "形态与材料按本方案的主张重新定，不复制它的外观".format(name))


def _limits_for(case: Dict[str, Any]) -> List[str]:
    out = list(case.get("avoid") or [])
    if case.get("area"):
        out.insert(0, "它的面积是 {}，属于它自己的规模与规范，不能反推本项目尺寸".format(
            case["area"]))
    if not out:
        out = ["尺寸、预算与当地规范都不通用，须按本项目条件重算"]
    return out[:3]


def _why_for(case: Dict[str, Any], concept: Dict[str, Any]) -> str:
    fits = case.get("fits") or []
    if fits:
        return "；".join(fits[:2])
    return "它在「{}」这个方向上是我们这次找到的可核验案例".format(
        concept.get("name") or concept.get("concept_id") or "本方向")


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

        scored = [(_score(cs, c, ""), cs) for cs in cases]
        scored = [(s, cs) for s, cs in scored if s > 0]
        scored.sort(key=lambda x: -x[0])
        chosen = [cs for _, cs in scored[:2]]

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
