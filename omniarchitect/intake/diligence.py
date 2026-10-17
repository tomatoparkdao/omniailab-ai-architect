"""Project due diligence: what we actually know, and how well we know it.

Two registers, both persisted on the project so they survive a restart:

* **source register** — every input file, where it came from, which revision,
  and whether anyone checked it against site conditions;
* **uncertainty register** — every claim that matters but is not settled, with
  a five-state confidence and an explicit blocking scope.

The blocking rule is the important part. Treating every unknown as a blocker
makes the project unstartable; treating none as blockers produces drawings
that cannot be built. So uncertainty is classified by *what it invalidates*,
not by how uncomfortable it feels.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..model import Project
from ..stages import STAGE_ORDER, stage_name

# Five states. Ordered from strongest to weakest evidence — never merge them,
# because "someone told me" and "I measured it" drive different decisions.
CONFIDENCE_STATES: Tuple[str, ...] = (
    "verified",       # measured on site, or confirmed by a responsible party
    "documented",     # supported by a source file, not yet checked on site
    "inferred",       # derived by rule or AI from other information
    "unknown",        # nothing to go on
    "conflicting",    # two sources disagree
)

CONFIDENCE_LABEL: Dict[str, str] = {
    "verified": "已核验",
    "documented": "有文件依据（未现场核验）",
    "inferred": "推断",
    "unknown": "未知",
    "conflicting": "来源冲突",
}

# What an unresolved item actually invalidates. Keyed by topic.
BLOCKING_SCOPES: Dict[str, Dict[str, Any]] = {
    "structural": {
        "blocks": ("S4", "S7"),
        "reason": "结构与承重条件未证实：可以讨论非结构方案，不得承诺拆改、"
                  "不得出结构相关图纸",
        "needs_human": True,
    },
    "dimension": {
        # S3 is where the plan is built at real size, so an unverified
        # dimension bites earlier than most people expect.
        "blocks": ("S3", "S4"),
        "reason": "关键尺寸未证实：可出概念方向与示意，不得出依赖精确尺寸的图纸与工程量",
        "needs_human": False,
    },
    "regulatory": {
        "blocks": ("S7",),
        "reason": "法规与报批条件未确认：不得出具可报审图纸，结论须由持证人员复核",
        "needs_human": True,
    },
    "budget": {
        "blocks": (),
        "reason": "预算口径未定：不阻断设计，但造价结论只能给区间并注明假设",
        "needs_human": False,
    },
    "aesthetic": {
        "blocks": (),
        "reason": "审美方向未定：不阻断，S2 概念阶段收敛即可",
        "needs_human": False,
    },
    "scope": {
        "blocks": (),
        "reason": "设计范围未定：不阻断，但交付清单须标注待确认",
        "needs_human": False,
    },
    "services": {
        "blocks": ("S4",),
        "reason": "机电条件未确认：不得承诺净高、点位与容量，须机电专业复核",
        "needs_human": True,
    },
}

SOURCE_KINDS: Tuple[str, ...] = (
    "cad", "pdf", "image", "scan", "photo", "task_doc", "measure", "note",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _intake(project: Project) -> Dict[str, Any]:
    """Return the *same* intake dict every call.

    Earlier this returned a fresh copy, so two helpers writing through it
    silently overwrote each other (the outer profile_id vanished while the
    interview survived). Holding one object is the fix.
    """
    meta = project.meta if isinstance(project.meta, dict) else {}
    intake = meta.get("intake")
    if not isinstance(intake, dict):
        intake = {}
        meta["intake"] = intake
    project.meta = meta
    return intake


def _store(project: Project) -> Dict[str, Any]:
    return _intake(project)


@dataclass
class SourceEntry:
    """One input document or observation."""

    id: str
    kind: str                      # see SOURCE_KINDS
    file: str = ""
    revision: str = ""
    obtained_at: str = ""
    confidence: str = "documented"
    verified_by: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.kind not in SOURCE_KINDS:
            raise ValueError(f"unknown source kind '{self.kind}'")
        if self.confidence not in CONFIDENCE_STATES:
            raise ValueError(f"unknown confidence '{self.confidence}'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "file": self.file,
            "revision": self.revision, "obtained_at": self.obtained_at,
            "confidence": self.confidence, "confidence_label":
                CONFIDENCE_LABEL.get(self.confidence, self.confidence),
            "verified_by": self.verified_by, "note": self.note,
        }


@dataclass
class UncertaintyItem:
    """A claim that matters but is not settled."""

    id: str
    topic: str                     # key of BLOCKING_SCOPES
    statement: str
    state: str = "unknown"
    sources: List[str] = field(default_factory=list)
    affects: str = "S3"
    action_needed: str = ""
    owner: str = ""

    def __post_init__(self) -> None:
        if self.topic not in BLOCKING_SCOPES:
            raise ValueError(f"unknown uncertainty topic '{self.topic}'")
        if self.state not in CONFIDENCE_STATES:
            raise ValueError(f"unknown state '{self.state}'")

    def to_dict(self) -> Dict[str, Any]:
        scope = blocking_scope(self.topic, self.state)
        return {
            "id": self.id,
            "topic": self.topic,
            "statement": self.statement,
            "state": self.state,
            "state_label": CONFIDENCE_LABEL.get(self.state, self.state),
            "sources": list(self.sources),
            "affects": self.affects,
            "blocks_stages": list(scope["blocks"]),
            "action_needed": self.action_needed or str(scope["reason"]),
            "needs_human": bool(scope["needs_human"]),
            "owner": self.owner,
            "open": self.state in ("unknown", "inferred", "conflicting"),
        }


def blocking_scope(topic: str, state: str) -> Dict[str, Any]:
    """What does an unresolved item of this kind actually block?"""
    scope = BLOCKING_SCOPES.get(topic) or BLOCKING_SCOPES["scope"]
    if state in ("verified", "documented"):
        return {"blocks": [], "reason": "", "needs_human": False}
    if state == "conflicting":
        # A contradiction blocks harder than a blank: a blank can be filled,
        # a contradiction can be acted on wrongly.
        blocks = sorted(set(scope["blocks"]) | {"S2"}, key=STAGE_ORDER.index)
        return {"blocks": blocks, "reason": str(scope["reason"]),
                "needs_human": True}
    return {"blocks": list(scope["blocks"]), "reason": str(scope["reason"]),
            "needs_human": bool(scope["needs_human"])}


def register_source(project: Project, entry: SourceEntry) -> SourceEntry:
    """Add (or replace) a source in the project-level register."""
    intake = _store(project)
    reg = list(intake.get("sources") or [])
    reg = [r for r in reg if r.get("id") != entry.id]
    reg.append(entry.to_dict())
    intake["sources"] = reg
    # Keep `project.sources` in step: it is what S1 reports and demos read.
    legacy = [s for s in (project.sources or []) if s.get("id") != entry.id]
    legacy.append({
        "id": entry.id, "type": entry.kind, "file": entry.file,
        "confidence": entry.confidence, "note": entry.note or entry.revision,
    })
    project.sources = legacy
    return entry


def register_uncertainty(project: Project, item: UncertaintyItem) -> UncertaintyItem:
    intake = _store(project)
    reg = [r for r in (intake.get("uncertainty") or []) if r.get("id") != item.id]
    reg.append(item.to_dict())
    intake["uncertainty"] = reg
    return item


def uncertainty_register(project: Project) -> List[Dict[str, Any]]:
    return list((_store(project).get("uncertainty") or []))


def source_register(project: Project) -> List[Dict[str, Any]]:
    return list((_store(project).get("sources") or []))


# Kinds of input that carry real dimensional authority, and those that do not.
_DIMENSIONAL_KINDS = {"cad", "measure"}
_VISUAL_KINDS = {"image", "photo", "scan", "pdf"}


def assess_sources(project: Project) -> Dict[str, Any]:
    """Summarise what the inputs can and cannot support.

    This answers one question only: **what may we claim** because of these
    files? It never upgrades a photo to a measured dimension.
    """
    reg = source_register(project)
    kinds = [str(r.get("kind") or "") for r in reg]
    has_cad = any(k in _DIMENSIONAL_KINDS for k in kinds)
    has_measure = "measure" in kinds
    has_visual = any(k in _VISUAL_KINDS for k in kinds)
    has_task_doc = "task_doc" in kinds
    counts: Dict[str, int] = {}
    for k in kinds:
        counts[k] = counts.get(k, 0) + 1

    if has_measure or has_cad:
        dimensional = "documented"
    elif has_visual:
        dimensional = "inferred"
    else:
        dimensional = "unknown"

    gaps: List[str] = []
    if not reg:
        gaps.append("没有任何原始资料；尺寸、结构与现状均未证实")
    if not has_cad:
        gaps.append("没有 CAD/DXF 或实测记录：尺寸只能推断，不能作为图纸依据")
    if not has_measure:
        gaps.append("没有现场实测记录：图纸标注与现场是否一致未核验")
    if not has_task_doc:
        gaps.append("没有书面任务书：需求只来自对话，须在 G1 前确认")

    return {
        "count": len(reg),
        "by_kind": counts,
        "has_cad": has_cad,
        "has_measure": has_measure,
        "has_visual": has_visual,
        "has_task_doc": has_task_doc,
        "dimensional_authority": dimensional,
        "gaps": gaps,
    }


def blocking_stages(project: Project) -> Dict[str, List[str]]:
    """Stage -> reasons it may not be treated as authoritative yet."""
    out: Dict[str, List[str]] = {}
    for item in uncertainty_register(project):
        if not item.get("open"):
            continue
        for sid in item.get("blocks_stages") or []:
            out.setdefault(sid, []).append(
                f"{item['id']}（{item['state_label']}）：{item['statement']}"
            )
    return out


def unverified_structural(project: Project) -> bool:
    """True when structure exists in the model but nobody has verified it."""
    if not any(e.type in ("wall", "slab") for e in project.elements):
        return False
    for item in uncertainty_register(project):
        if item.get("topic") == "structural" and item.get("open"):
            return True
    # Elements flagged uncertain by the model itself count too.
    return any(e.uncertain for e in project.elements if e.type in ("wall", "slab"))


# How far this project's information can carry a claim. This is the honest
# answer to "can we draw this?", and it is what S1 declares at the gate.
PRECISION_LEVELS: Tuple[str, ...] = ("diagnostic", "schematic", "authoritative_capable")


def precision_level(project: Project) -> str:
    """diagnostic → schematic → authoritative_capable.

    A CAD file is *documented*, not *verified*: it may be an old revision, so it
    supports scheme drawings with stated caveats, not construction output.
    Only a site measurement (or a signed survey) reaches the top level.
    """
    src = assess_sources(project)
    has_geom = bool(project.spaces or project.elements)
    if src.get("has_measure"):
        return "authoritative_capable"
    if has_geom:
        return "schematic"
    return "diagnostic"


def store_precision(project: Project) -> str:
    """Persist the current precision so downstream guardrails can read it."""
    level = precision_level(project)
    _store(project)["precision"] = level
    return level


def markdown(project: Project) -> str:
    """Human-readable uncertainty register for the S1 bundle."""
    items = uncertainty_register(project)
    lines = ["| # | 事项 | 状态 | 阻断阶段 | 需要人工 | 说明 |",
             "|---|---|---|---|---|---|"]
    if not items:
        lines.append("| — | 无登记项 | — | — | — | 资料尚未整理 |")
    for i, it in enumerate(items, 1):
        blocks = "、".join(stage_name(s) for s in (it.get("blocks_stages") or [])) or "不阻断"
        lines.append(
            f"| {i} | {it['statement']} | {it['state_label']} | {blocks} "
            f"| {'是' if it.get('needs_human') else '否'} | {it.get('action_needed','')} |"
        )
    return "\n".join(lines)
