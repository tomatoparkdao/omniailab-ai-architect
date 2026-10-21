"""One call that turns "the client just described a project" into a shortlist.

This is the orchestrator, and it is deliberately thin: `brief.derive()` decides
*what* to look for, `cases.search()` finds it, `report.write()` renders it.
Everything interesting lives there. What lives here is the policy layer:

- how many cases a discipline gets (so 8 is a ceiling, not a quota to pad)
- what to do when nothing is verifiable (say so, do not substitute)
- how the result is attached to the project without inventing a new store

State goes in ``project.meta["research"]``, alongside the other S1/S2 blocks.
Not a second database — the same place everything else about this project
lives, so a change to the brief invalidates it like any other artifact.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from . import cases as case_mod
from .brief import ResearchBrief, derive, should_start
from .report import ResearchResult, render_markdown, write
from .sources import FIRST_PARTY, recommend

#: Which discipline gets how many of the 5–8 slots.
#:
#: The dominant discipline gets the most, because that is where the design
#: argument is won. A fit-out project does not get two landscape cases just so
#: the table looks balanced.
ALLOCATION: Dict[str, int] = {
    "architecture": 4,
    "interior": 3,
    "landscape": 2,
}

MAX_TOTAL = 8
META_KEY = "research"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def allocate(disciplines: Sequence[str]) -> Dict[str, int]:
    """Split the 8 slots across disciplines, dominant first, capped at 8."""
    order = [d for d in ("architecture", "interior", "landscape") if d in disciplines]
    if not order:
        return {}
    plan: Dict[str, int] = {}
    budget = MAX_TOTAL
    for i, d in enumerate(order):
        want = ALLOCATION.get(d, 2)
        if i == 0:
            want = min(want + 1, 5)
        take = min(want, budget)
        if take <= 0:
            continue
        plan[d] = take
        budget -= take
    return plan


def run(project: Any, out_dir: Optional[str] = None,
        fetch_fn: Optional[case_mod.Fetcher] = None,
        verify_pages: bool = True,
        store: bool = True) -> ResearchResult:
    """Research this project, then optionally render and attach the result.

    ``fetch_fn`` exists so tests can run without network and so a run can be
    replayed against recorded responses. It is never used to fabricate data:
    the fixture path only feeds real captured pages.

    When ``OMNIAILAB_NO_NETWORK`` is set and no ``fetch_fn`` was supplied, we
    degrade to a *directions-only* result: what to look at and where to look,
    with no case claims. That is a real answer, not an error — but it must
    never be dressed up as "we searched and found nothing".
    """
    import os

    offline = (os.environ.get("OMNIAILAB_NO_NETWORK", "").strip().lower()
               in ("1", "true", "yes", "on"))
    ok, why = should_start(project)
    brief = derive(project)

    result = ResearchResult(
        brief=brief, cases=[], manual=[], log=[],
        project_id=getattr(project, "project_id", ""),
        revision=int(getattr(project, "revision", 0) or 0),
        generated_at=_now(),
    )
    if not ok:
        result.log.append({"source": "-", "action": "skip", "detail": why})
        if store:
            _store(project, result, reason=why)
        return result

    if offline and fetch_fn is None:
        result.manual = [
            e for d in brief.directions
            for e in case_mod.manual_entries(d.discipline, d.idea)
        ]
        result.log.append({
            "source": "-", "action": "offline",
            "detail": "OMNIAILAB_NO_NETWORK 已置位：只给检索方向与入口，未联网，不声称找到案例",
        })
        if store:
            _store(project, result, reason="离网模式：未检索，只给方向")
        if out_dir:
            write(result, out_dir)
        return result

    plan = allocate(brief.disciplines)
    log = case_mod.SearchLog()

    for d in brief.directions:
        n = plan.get(d.discipline, 0)
        if n <= 0:
            continue
        found = case_mod.search(d.discipline, d.idea, limit=n,
                                fetch_fn=fetch_fn,
                                verify_pages=verify_pages, log=log,
                                aspect=getattr(d, "aspect", "") or "")
        for c in found:
            c.fits = _fits(c, brief)
        result.cases.extend(found)

    result.log = log.to_list()
    result.manual = [
        e for d in brief.directions
        for e in case_mod.manual_entries(d.discipline, d.idea)
    ]

    # The manual list is long and mostly noise for a client; keep one entry
    # per source, and never repeat the first-party library inside it.
    seen = set()
    trimmed: List[Dict[str, str]] = []
    for e in result.manual:
        if e["source"] in seen or e["source"] == FIRST_PARTY.id:
            continue
        seen.add(e["source"])
        trimmed.append(e)
    result.manual = trimmed

    if store:
        _store(project, result)
    if out_dir:
        write(result, out_dir)
    return result


def _fits(c: case_mod.Case, brief: ResearchBrief) -> List[str]:
    """Which of the client's own asks this case speaks to.

    Only terms that actually appear in the case's own title/description are
    claimed. No term, no claim — an empty list is a valid answer.
    """
    hay = (c.title + " " + c.summary + " " + c.url).lower()
    out: List[str] = []
    for f in brief.feelings:
        token = str(f).lower()
        if len(token) >= 2 and token in hay:
            out.append("你提到「{}」".format(f))
    if brief.style:
        for token in str(brief.style).replace("、", " ").replace("，", " ").split():
            if len(token) >= 2 and token.lower() in hay:
                out.append("你提到的{}倾向".format(token))
    if c.area:
        out.append("规模可参照（{}，但须按本项目实测校核）".format(c.area))
    return out[:3]


def _store(project: Any, r: ResearchResult, reason: str = "") -> None:
    """Attach to the project in the one place project state lives."""
    meta = getattr(project, "meta", None)
    if meta is None:
        return
    payload = r.to_dict()
    if reason:
        payload["skipped_because"] = reason
    meta[META_KEY] = payload


def load(project: Any) -> Optional[Dict[str, Any]]:
    meta = getattr(project, "meta", None) or {}
    val = meta.get(META_KEY)
    return val if isinstance(val, dict) else None


def summary_lines(project: Any) -> List[str]:
    """One-paragraph status line for the CLI and for stage summaries."""
    data = load(project)
    if not data:
        return ["尚未做过案例研究。"]
    counts = data.get("counts") or {}
    brief = data.get("brief") or {}
    lines = [
        "案例研究：{} 个案例（已核验 {} 个）".format(
            counts.get("total", 0), counts.get("verified", 0)),
        "第一优先入口：{}".format((data.get("first_entry") or {}).get("name", "—")),
        "检索方向：{}".format("、".join(
            d.get("discipline_label", "") for d in brief.get("directions", []))),
    ]
    if data.get("skipped_because"):
        lines.append("未检索原因：" + str(data["skipped_because"]))
    return lines


__all__ = [
    "ALLOCATION", "MAX_TOTAL", "META_KEY", "allocate", "load", "run",
    "summary_lines",
]
