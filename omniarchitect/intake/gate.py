"""G1 gate: what the client is actually signing, and what happens after.

G1 was a button. In a real project the client signs a *baseline* — a specific
set of goals, requirements, scope, budget assumptions and open questions — and
everything later is measured against it.

So this module does three things:

1. writes the approval sheet (eight sections, in the order a client reads);
2. maps the three decisions onto the existing stage state machine instead of
   inventing a parallel one (``approved`` → confirmed, ``revision_requested``
   → rework, ``blocked`` → blocked);
3. records a baseline digest, so a later edit can be recognised as a change
   that must go through the change-impact path rather than silently replacing
   what was signed.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..stage_state import (
    BLOCKED,
    CONFIRMED,
    REWORK,
    block_stage,
    confirm_stage,
    get_state,
    reject_stage,
)
from .diligence import blocking_stages, precision_level, store_precision, uncertainty_register
from .feasibility import run_feasibility
from .interview import completeness, load_interview, summary as interview_summary
from .needs import build_need_matrix
from .opportunities import find_opportunities

DECISIONS = ("approved", "revision_requested", "blocked")

DECISION_TO_STATUS = {
    "approved": CONFIRMED,
    "revision_requested": REWORK,
    "blocked": BLOCKED,
}

DECISION_LABEL = {
    "approved": "通过（形成任务书基准）",
    "revision_requested": "退回修改",
    "blocked": "阻断（有前置条件未解决）",
}

PRECISION_LABEL = {
    "diagnostic": "诊断级：只能做需求诊断与概念方向，不出技术成果",
    "schematic": "示意级：可出方案图与示意，尺寸须现场核验，不出施工图",
    "authoritative_capable": "可出图级：有实测依据，可出方案深度图纸（施工图仍须专业签署）",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ApprovalOutcome:
    decision: str
    stage_status: str
    baseline: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    forced: bool = False
    summary_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "decision_label": DECISION_LABEL.get(self.decision, self.decision),
            "stage_status": self.stage_status,
            "baseline": dict(self.baseline),
            "notes": list(self.notes),
            "forced": self.forced,
            "summary_path": self.summary_path,
        }


def _intake(project: Project) -> Dict[str, Any]:
    project.meta = dict(project.meta or {})
    intake = dict(project.meta.get("intake") or {})
    project.meta["intake"] = intake
    return intake


def baseline_digest(project: Project) -> str:
    """A stable fingerprint of everything G1 signs.

    Deliberately excludes geometry: this baseline is about the *brief*, and
    geometry changes already have their own revision machinery.
    """
    payload = {
        "project_id": project.project_id,
        "revision": project.revision,
        "program": project.program,
        "constraints": {k: v for k, v in (project.constraints or {}).items()
                        if not k.startswith("_")},
        "answers": (load_interview(project).answers or {}),
        "assumptions": project.assumptions,
        "uncertainty": [u["id"] for u in uncertainty_register(project)],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def approval_summary_text(project: Project, extra: str = "") -> str:
    """The eight sections a client must be shown before signing G1."""
    comp = completeness(project)
    matrix = build_need_matrix(project)
    feas = run_feasibility(project)
    opps = find_opportunities(project)
    intr = interview_summary(project)
    unc = [u for u in uncertainty_register(project) if u.get("open")]
    blockers = [c for c in feas["conflicts"] if c["severity"] == "blocker"]
    majors = [c for c in feas["conflicts"] if c["severity"] == "major"]
    precision = precision_level(project)

    lines = [f"# G1 任务书确认摘要 — {project.name or project.project_id}", "",
             f"- 项目编号：`{project.project_id}`　修订：r{project.revision}",
             f"- 生成时间：{_now()}",
             f"- 资料完整度：{comp['ratio'] * 100:.0f}%（{comp['verdict']}）",
             f"- 本轮可支撑深度：{PRECISION_LABEL.get(precision, precision)}",
             ""]

    lines += ["## 1. 已确认的设计目标", ""]
    must = [r for r in matrix["rows"] if r["priority"] == "must"]
    if must:
        lines += [f"- {r['activity']}" + (f"（{r['headcount']} 人）" if r["headcount"] else "")
                  for r in must]
    else:
        lines.append("- 尚未形成可排序的目标（需求访谈未完成）")

    lines += ["", "## 2. 功能与空间需求", "",
              f"- 功能项 {len(project.program)} 项；需求行为 {len(matrix['rows'])} 条", ""]
    if project.program:
        lines += ["| 房间 | 目标面积 m² |", "|---|---|"]
        for p in project.program:
            lines.append(f"| {p.get('name','')} | {p.get('area_m2','')} |")
        total = sum(float(p.get("area_m2") or 0) for p in project.program)
        lines += ["", f"合计 {total:.1f} m²"]

    cons = project.constraints or {}
    lines += ["", "## 3. 项目范围与交付深度", "",
              f"- 交付深度：{intr.get('start_mode_label','') and ''}"
              f"{(load_interview(project).answers.get('base.deliverable_depth') or {}).get('value') or cons.get('deliverable_depth') or '未说明'}",
              f"- 设计阶段：方案（非施工图深度）",
              f"- 精度等级：{PRECISION_LABEL.get(precision, precision)}"]

    lines += ["", "## 4. 预算口径", ""]
    budget = cons.get("budget_cny")
    lines.append(f"- 金额：{float(budget):,.0f} CNY" if budget else "- 金额：未提供（造价结论只能给区间）")
    lines.append("- 包含范围："
                 + str(cons.get("budget_scope") or "未说明（硬装 / 软装 / 家电 / 设计费须分别注明）"))
    lines.append("- 性质：前期估算，不构成报价或结算依据")

    lines += ["", "## 5. 设计周期目标", "",
              f"- {(load_interview(project).answers.get('base.schedule') or {}).get('value') or cons.get('schedule') or '未说明'}"]
    sch = [(c["problem"], c["evidence"]) for c in feas["conflicts"]
           if c["category"] == "schedule"]
    for p, e in sch:
        lines.append(f"- 风险：{p}（{e}）")

    lines += ["", "## 6. 重要建筑限制", ""]
    tech = [c for c in feas["conflicts"] if c["category"] == "technical"]
    if tech:
        lines += [f"- {c['problem']}（{c['evidence']}）" for c in tech]
    else:
        lines.append("- 未发现已登记的技术限制；不代表不存在")

    lines += ["", "## 7. 仍未解决的问题", ""]
    if unc:
        lines += [f"- {u['statement']}（{u['state_label']}；阻断 "
                  f"{'、'.join(u.get('blocks_stages') or []) or '无'}）" for u in unc]
    if blockers:
        lines += [f"- **阻断项**：{c['problem']}" for c in blockers]
    if not unc and not blockers:
        lines.append("- 无")

    lines += ["", "## 8. S2 概念设计的研究重点", ""]
    if opps["items"]:
        lines += [f"- {o['problem']}（下一步：{o['next_stage_recommendation']}）"
                  for o in opps["items"]]
    else:
        lines.append("- 尚无有证据的设计机会；S2 应先补齐需求与条件")

    if majors:
        lines += ["", "## 需在 S2 解决的重要条件", ""]
        lines += [f"- {c['problem']} → {c['recommendation']}" for c in majors]

    lines += ["", "## 请确认", "",
              "1. 以上 1–6 项与您的理解一致；",
              "2. 第 7 项中的问题您接受在 S2 前解决，或已明确可以搁置；",
              "3. 第 8 项的 S2 研究重点没有遗漏您最在意的问题。", "",
              "> 确认后形成任务书基准。此后修改需求将触发变更影响分析，"
              "原确认版保留在 S1 修订记录中，不会被直接覆盖。", ""]
    if extra:
        lines += ["## 备注", "", extra, ""]
    return "\n".join(lines)


def decide_gate(project: Project, decision: str, by: str = "",
                note: str = "", force: bool = False,
                summary_path: str = "") -> ApprovalOutcome:
    """Apply one of the three G1 decisions.

    A blocker-level feasibility finding prevents ``approved`` unless ``force``
    is set: signing a brief whose numbers do not add up is not a decision, it
    is a deferred argument.
    """
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision '{decision}'（应为 {'/'.join(DECISIONS)}）")

    store_precision(project)
    feas = run_feasibility(project)
    blockers = [c for c in feas["conflicts"] if c["severity"] == "blocker"]
    notes: List[str] = []
    forced = False
    if blockers and decision == "approved" and not force:
        decision = "blocked"
        notes.append("存在阻断级可行性问题，不能直接通过：" +
                     "；".join(c["problem"] for c in blockers[:3]))
        notes.append("处理方式：先把阻断项解决，或明确接受其影响后以 force 记录")
    elif blockers and decision == "approved" and force:
        forced = True
        notes.append("在存在阻断项的情况下强制通过；已记录，供后续追溯")

    if decision == "approved":
        st = confirm_stage(project, "S1", by=by, note=note or "G1 任务书确认")
        baseline = {
            "revision": project.revision,
            "digest": baseline_digest(project),
            "confirmed_at": st.confirmed_at,
            "confirmed_by": st.confirmed_by,
            "precision": precision_level(project),
            "completeness": completeness(project)["ratio"],
            "forced": forced,
            "summary_path": summary_path,
        }
        _intake(project)["baseline"] = baseline
        notes.append(f"已形成任务书基准：r{project.revision} / {baseline['digest']}")
    elif decision == "revision_requested":
        st = reject_stage(project, "S1", reason=note or "客户要求修改任务书")
        baseline = _intake(project).get("baseline") or {}
        notes.append("已退回修改；任务书基准未变更，S1 需重新提交 G1")
    else:
        st = block_stage(project, "S1", note or "存在前置条件未解决")
        baseline = _intake(project).get("baseline") or {}
        notes.append("已阻断：解决前置条件后重新提交 G1")

    return ApprovalOutcome(decision=decision, stage_status=st.status,
                           baseline=baseline, notes=notes, forced=forced,
                           summary_path=summary_path)


def check_baseline(project: Project) -> Dict[str, Any]:
    """Has anything the client signed changed since G1?"""
    base = _intake(project).get("baseline") or {}
    if not base:
        return {"has_baseline": False, "changed": False, "reason": "尚未通过 G1"}
    current = baseline_digest(project)
    changed = current != base.get("digest")
    return {
        "has_baseline": True,
        "changed": changed,
        "baseline_revision": base.get("revision"),
        "current_revision": project.revision,
        "baseline_digest": base.get("digest"),
        "current_digest": current,
        "confirmed_at": base.get("confirmed_at"),
        "confirmed_by": base.get("confirmed_by"),
        "requires_change_analysis": changed,
        "reason": ("任务书基准已被修改，须走变更影响分析" if changed
                   else "与已确认基准一致"),
    }
