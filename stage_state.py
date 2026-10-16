"""Stage state machine.

Persisted in `project.meta["stage_state"]` so a run can stop at a gate, be
resumed days later, and still know exactly what is confirmed, what is awaiting
confirmation and what has been sent back for rework.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Project
from .stages import (
    REQUIRES_CONFIRMED,
    STAGE_BY_ID,
    STAGE_ORDER,
    Stage,
    stage_name,
)

PENDING = "pending"
IN_PROGRESS = "in_progress"
AWAITING = "awaiting_confirmation"
CONFIRMED = "confirmed"
REWORK = "rework"
BLOCKED = "blocked"
SKIPPED = "skipped"

ACTIVE_STATUSES = (IN_PROGRESS, AWAITING, REWORK, BLOCKED)
FINAL_STATUSES = (CONFIRMED, SKIPPED)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class StageState:
    stage: str
    status: str = PENDING
    confirmed_at: str = ""
    confirmed_by: str = ""
    revision: int = 0
    attempts: int = 0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "confirmed_at": self.confirmed_at,
            "confirmed_by": self.confirmed_by,
            "revision": self.revision,
            "attempts": self.attempts,
            "note": self.note,
        }


def _store(project: Project) -> Dict[str, Any]:
    project.meta = dict(project.meta or {})
    state = dict(project.meta.get("stage_state") or {})
    project.meta["stage_state"] = state
    return state


def get_state(project: Project, stage_id: str) -> StageState:
    raw = (_store(project).get(stage_id) or {})
    return StageState(
        stage=stage_id,
        status=str(raw.get("status") or PENDING),
        confirmed_at=str(raw.get("confirmed_at") or ""),
        confirmed_by=str(raw.get("confirmed_by") or ""),
        revision=int(raw.get("revision") or 0),
        attempts=int(raw.get("attempts") or 0),
        note=str(raw.get("note") or ""),
    )


def set_state(project: Project, state: StageState) -> StageState:
    _store(project)[state.stage] = state.to_dict()
    return state


def all_states(project: Project) -> List[StageState]:
    return [get_state(project, s) for s in STAGE_ORDER]


def confirmed(project: Project, stage_id: str) -> bool:
    return get_state(project, stage_id).status == CONFIRMED


def can_start(project: Project, stage_id: str) -> Tuple[bool, str]:
    """Guardrail check. Returns (allowed, reason)."""
    if stage_id not in STAGE_BY_ID:
        return False, f"unknown stage '{stage_id}'"
    st = STAGE_BY_ID[stage_id]
    current = get_state(project, stage_id)
    if current.status == CONFIRMED:
        return False, f"{stage_name(stage_id)} 已确认；如需修改请走变更影响分析"

    missing = [s for s in REQUIRES_CONFIRMED.get(stage_id, []) if not confirmed(project, s)]
    if missing:
        labels = "、".join(stage_name(m) for m in missing)
        return False, (
            f"前置阶段未确认：{labels}。"
            f"阶段推进不能在未确认的上游成果上继续（见门禁 {st.gate.id}：{st.gate.label}）"
        )

    # R4: nothing downstream of an unconfirmed plan may produce formal output
    if stage_id in ("S5", "S6", "S7", "S8") and not confirmed(project, "S3"):
        return False, "平面方案（S3）未确认，不得进行精细建模或正式出图 —— 这是最贵的一步"

    # R1: no fine modelling before functional requirements are confirmed
    if stage_id == "S5" and not confirmed(project, "S1"):
        return False, "任务书（S1）未确认：业主确认功能需求之前不得开始精细建模"

    if current.status == IN_PROGRESS:
        return False, f"{stage_name(stage_id)} 正在进行中"
    return True, ""


def start_stage(project: Project, stage_id: str) -> StageState:
    st = get_state(project, stage_id)
    st.status = IN_PROGRESS
    st.attempts += 1
    st.revision = project.revision
    st.note = ""
    return set_state(project, st)


def submit_for_confirmation(project: Project, stage_id: str, note: str = "") -> StageState:
    st = get_state(project, stage_id)
    st.status = AWAITING
    st.revision = project.revision
    st.note = note
    return set_state(project, st)


def confirm_stage(project: Project, stage_id: str, by: str = "",
                  note: str = "", force: bool = False) -> StageState:
    if stage_id not in STAGE_BY_ID:
        raise KeyError(stage_id)
    st = get_state(project, stage_id)
    if st.status == CONFIRMED and not force:
        return st
    st.status = CONFIRMED
    st.confirmed_at = _now()
    st.confirmed_by = by or "业主/主创"
    st.revision = project.revision
    if note:
        st.note = note
    return set_state(project, st)


def reject_stage(project: Project, stage_id: str, reason: str = "") -> StageState:
    st = get_state(project, stage_id)
    st.status = REWORK
    st.confirmed_at = ""
    st.note = reason or "阶段成果未通过确认，须修改后重新提交"
    return set_state(project, st)


def block_stage(project: Project, stage_id: str, reason: str) -> StageState:
    st = get_state(project, stage_id)
    st.status = BLOCKED
    st.note = reason
    return set_state(project, st)


def invalidate_from(project: Project, from_stage: str) -> List[str]:
    """Mark every confirmed stage at or after `from_stage` as needing rework."""
    from .stages import DOWNSTREAM

    touched = DOWNSTREAM.get(from_stage, [from_stage])
    out: List[str] = []
    for sid in STAGE_ORDER:
        if sid not in touched:
            continue
        st = get_state(project, sid)
        if st.status in (CONFIRMED, AWAITING, IN_PROGRESS):
            st.status = REWORK if sid != from_stage else PENDING
            st.confirmed_at = ""
            st.note = f"上游 {stage_name(from_stage)} 发生变更，成果需重新生成并确认"
            set_state(project, st)
            out.append(sid)
    return out


def progress(project: Project) -> Dict[str, Any]:
    states = all_states(project)
    done = [s.stage for s in states if s.status == CONFIRMED]
    awaiting = [s.stage for s in states if s.status == AWAITING]
    rework = [s.stage for s in states if s.status == REWORK]
    nxt = next((s for s in STAGE_ORDER if get_state(project, s).status != CONFIRMED), "")
    return {
        "confirmed": done,
        "awaiting_confirmation": awaiting,
        "in_rework": rework,
        "current": nxt,
        "current_name": stage_name(nxt) if nxt else "",
        "percent": round(100.0 * len(done) / len(STAGE_ORDER), 1),
        "rows": [
            {
                "stage": s.stage,
                "name": stage_name(s.stage),
                "status": s.status,
                "confirmed_at": s.confirmed_at,
                "attempts": s.attempts,
                "note": s.note,
            }
            for s in states
        ],
    }


def next_runnable(project: Project) -> Tuple[str, str]:
    """First stage that is not confirmed and whose guardrails allow it now."""
    for sid in STAGE_ORDER:
        if confirmed(project, sid):
            continue
        ok, reason = can_start(project, sid)
        return sid, ("" if ok else reason)
    return "", "全部阶段已确认"


def markdown(project: Project) -> str:
    p = progress(project)
    icon = {
        CONFIRMED: "已确认", AWAITING: "待确认", IN_PROGRESS: "进行中",
        REWORK: "需返工", BLOCKED: "受阻", PENDING: "未开始", SKIPPED: "跳过",
    }
    lines = ["# 阶段推进状态", "",
             f"进度 {p['percent']}%　当前：{p['current_name'] or '已完成'}", "",
             "| 阶段 | 状态 | 确认时间 | 提交次数 | 说明 |", "|---|---|---|---|---|"]
    for r in p["rows"]:
        lines.append(
            f"| {r['name']} | {icon.get(r['status'], r['status'])} | "
            f"{r['confirmed_at'][:19] or '—'} | {r['attempts']} | {r['note'] or '—'} |"
        )
    return "\n".join(lines)
