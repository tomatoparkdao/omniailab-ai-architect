"""G1 gate: what the client is signing, what it does *not* authorise, and what
has to happen before it means anything downstream.

G1 answers one question only: **can S2 start?** It is not the place to decide
whether structure may be modified — that belongs to S4 and S7, and is decided by
`intake.guard`. Conflating the two produces the worst of both worlds: a gate
that never opens on real projects, and limitations nobody can see.

So the assessment is split into four consequences:

* ``blocks_gate``    — S2 cannot start until the client chooses (a real
  requirement contradiction, or no requirement at all);
* ``limited_stages`` — S2 may start, but named later stages carry restrictions;
* ``needs_human``    — a responsible professional must sign before it counts;
* ``conditions``     — proceed, with a stated caveat.

Approval levels are explicit: an owner's approval creates a baseline; a demo
approval (``--assume-approval``) never does, because a demo is not a signature.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
from .diligence import (
    blocking_stages,
    precision_level,
    source_register,
    store_precision,
    uncertainty_register,
)
from .feasibility import run_feasibility
from .guard import STAGES_GUARDED, check_stage, signature_blockers
from .interview import completeness, load_interview, summary as interview_summary
from .needs import build_need_matrix
from .opportunities import find_opportunities

DECISIONS = ("approved", "revision_requested", "blocked")
SOURCES = ("owner", "demo")

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

SOURCE_LABEL = {
    "owner": "业主/主创确认",
    "demo": "演示模式（非业主签署，不形成可引用基准）",
}

PRECISION_LABEL = {
    "diagnostic": "诊断级：只能做需求诊断与概念方向，不出技术成果",
    "schematic": "示意级：可出方案图与示意，尺寸须现场核验，不出施工图",
    "authoritative_capable": "可出图级：有实测依据，可出方案深度图纸（施工图仍须专业签署）",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _intake(project: Project) -> Dict[str, Any]:
    meta = project.meta if isinstance(project.meta, dict) else {}
    intake = meta.get("intake")
    if not isinstance(intake, dict):
        intake = {}
        meta["intake"] = intake
    project.meta = meta
    return intake


# --------------------------------------------------------------------------
# assessment
# --------------------------------------------------------------------------
@dataclass
class GateAssessment:
    recommended: str = "approved"
    can_approve: bool = True
    blocks_gate: List[Dict[str, Any]] = field(default_factory=list)
    limited_stages: List[Dict[str, Any]] = field(default_factory=list)
    needs_human: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    precision: str = "diagnostic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended": self.recommended,
            "can_approve": self.can_approve,
            "blocks_gate": list(self.blocks_gate),
            "limited_stages": list(self.limited_stages),
            "needs_human": list(self.needs_human),
            "conditions": list(self.conditions),
            "precision": self.precision,
        }


def assess_gate(project: Project) -> GateAssessment:
    """Split everything we know into the four consequences.

    The distinction that matters: a missing dimension does not stop S2, and an
    unverified structure does not stop S2 either — they stop *specific work*
    later on. Only a contradiction the client must resolve stops the gate.
    """
    res = GateAssessment(precision=precision_level(project))
    feas = run_feasibility(project)
    matrix = build_need_matrix(project)
    # 客户可能只用一句话讲需求（没有功能表）。这时"有没有需求"要看他到底说没说过，
    # 而不是看功能表是否为空——否则"没有图纸但说了痛点"的客户会被误判成没需求。
    _answers = load_interview(project).answers or {}
    answered_needs = bool(_answers.get("base.needs", {}).get("value")) or any(
        str(k).endswith("needs") and (v or {}).get("value") for k, v in _answers.items()
    ) or any(r.get("state") in ("answered", "inferred") for r in (matrix.get("rows") or []))

    # --- 1. contradictions the client has to resolve ----------------------
    for c in feas["conflicts"]:
        if c["severity"] == "blocker" and c["category"] in ("area", "capacity"):
            res.blocks_gate.append({
                "id": c["id"],
                "kind": ("capacity_infeasible" if c["category"] == "capacity"
                         else "requirement_contradiction"),
                "problem": c["problem"],
                "evidence": c["evidence"],
                "needs": ("业主决定：减少人数/工位、改用轮用工位、换场地，"
                          "或书面接受紧凑布局的后果"
                          if c["category"] == "capacity"
                          else "业主决定取舍：合并功能、压缩次要空间，或调整面积目标"),
            })
        elif c["severity"] in ("blocker", "major"):
            # 预算、面积口径这类问题不阻断，但必须写进确认摘要与后续门禁
            res.conditions.append(f"{c['problem']}（{c['evidence']}）")

    # --- 2. is there a brief at all? --------------------------------------
    if not project.program and not answered_needs:
        res.blocks_gate.append({
            "id": "G1-NO-NEEDS",
            "kind": "no_requirement",
            "problem": "没有任何可确认的功能需求",
            "evidence": "功能表为空，且访谈中未获得需求描述",
            "needs": "至少回答一次「最想解决的 3 件事」，或提供功能清单",
        })
    elif matrix["rows"] and all(r["state"] == "inferred" for r in matrix["rows"]):
        res.conditions.append(
            "全部需求行均为推断：S2 前需业主逐条确认用途，否则概念方向可能跑偏"
        )

    # --- 3. stage-level limitations (S2 is not blocked by these) ----------
    for stage in STAGES_GUARDED:
        g = check_stage(project, stage)
        if not g.restrictions and not g.blocked:
            continue
        res.limited_stages.append({
            "stage": stage,
            "blocked": g.blocked,
            "restrictions": list(g.restrictions),
            "blocked_work": list(g.blocked_work),
            "triggered": list(g.triggered),
        })

    # --- 4. who must sign --------------------------------------------------
    res.needs_human = sorted({*signature_blockers(project)})

    res.can_approve = not res.blocks_gate
    res.recommended = "approved" if res.can_approve else "blocked"
    return res


# --------------------------------------------------------------------------
# baseline
# --------------------------------------------------------------------------
def _brief_payload(project: Project) -> Dict[str, Any]:
    """Everything that defines *what was asked for*.

    Deliberately excludes uncertainty state: verifying a condition lifts a
    limitation, it does not change the brief the client signed.
    """
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "program": project.program,
        "constraints": {k: v for k, v in (project.constraints or {}).items()
                        if not k.startswith("_")},
        "answers": (load_interview(project).answers or {}),
        "assumptions": project.assumptions,
        "sources": sorted(
            (str(s.get("id")), str(s.get("kind")), str(s.get("confidence")),
             str(s.get("revision")))
            for s in source_register(project)
        ),
    }


def _digest(payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def brief_digest(project: Project) -> str:
    """Fingerprint of requirements + constraints + sources."""
    return _digest(_brief_payload(project))


def baseline_digest(project: Project) -> str:
    """Fingerprint of the brief *and* the limitations attached to it.

    Two digests are kept apart on purpose: `brief_digest` changing means the
    client asked for something different (a real change); only this one
    changing means a condition was verified or lapsed (the brief is untouched,
    but what may be built has moved).
    """
    payload = _brief_payload(project)
    payload["uncertainty"] = sorted(
        (str(u.get("id")), str(u.get("topic")), str(u.get("state")))
        for u in uncertainty_register(project)
    )
    return _digest(payload)


# --------------------------------------------------------------------------
# approval sheet
# --------------------------------------------------------------------------
def approval_summary_text(project: Project, extra: str = "") -> str:
    """The eight sections a client must be shown, plus what G1 does not cover."""
    assess = assess_gate(project)
    comp = completeness(project)
    matrix = build_need_matrix(project)
    feas = run_feasibility(project)
    opps = find_opportunities(project)
    intr = interview_summary(project)
    unc = [u for u in uncertainty_register(project) if u.get("open")]
    blockers = [c for c in feas["conflicts"] if c["severity"] == "blocker"]
    majors = [c for c in feas["conflicts"] if c["severity"] == "major"]
    cons = project.constraints or {}

    lines = [f"# G1 任务书确认摘要 — {project.name or project.project_id}", "",
             f"- 项目编号：`{project.project_id}`　修订：r{project.revision}",
             f"- 生成时间：{_now()}",
             f"- 信息完整度：{comp['ratio'] * 100:.0f}%（{comp['verdict']}）",
             f"- 本轮可支撑深度：{PRECISION_LABEL.get(assess.precision, assess.precision)}",
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

    depth = (load_interview(project).answers.get("base.deliverable_depth") or {}).get(
        "value") or cons.get("deliverable_depth") or "未说明"
    lines += ["", "## 3. 项目范围与交付深度", "",
              f"- 交付深度：{depth}",
              "- 设计阶段：方案（非施工图深度）",
              f"- 精度等级：{PRECISION_LABEL.get(assess.precision, assess.precision)}"]

    lines += ["", "## 4. 预算口径", ""]
    budget = cons.get("budget_cny")
    lines.append(f"- 金额：{float(budget):,.0f} CNY" if budget
                 else "- 金额：未提供（造价结论只能给区间）")
    lines.append("- 包含范围："
                 + str(cons.get("budget_scope") or "未说明（硬装 / 软装 / 家电 / 设计费须分别注明）"))
    lines.append("- 性质：前期估算，不构成报价或结算依据")

    lines += ["", "## 5. 设计周期目标", "",
              f"- {(load_interview(project).answers.get('base.schedule') or {}).get('value') or cons.get('schedule') or '未说明'}"]
    for c in feas["conflicts"]:
        if c["category"] == "schedule":
            lines.append(f"- 风险：{c['problem']}（{c['evidence']}）")

    lines += ["", "## 6. 重要建筑限制", ""]
    tech = [c for c in feas["conflicts"] if c["category"] == "technical"]
    if tech:
        lines += [f"- {c['problem']}（{c['evidence']}）" for c in tech]
    else:
        lines.append("- 未发现已登记的技术限制；不代表不存在")

    # --- 7. what is still open -------------------------------------------
    lines += ["", "## 7. 仍未解决的问题", ""]
    if unc:
        lines += [f"- {u['statement']}（{u['state_label']}；阻断 "
                  f"{'、'.join(u.get('blocks_stages') or []) or '无'}）" for u in unc]
    if assess.blocks_gate:
        lines += [f"- **需业主决定**：{b['problem']}（{b['evidence']}）"
                  for b in assess.blocks_gate]
    if not unc and not assess.blocks_gate:
        lines.append("- 无")

    # --- 面积口径与容量：客户最先要听懂的两个人话问题 ---
    ab = feas.get("area_basis") or {}
    cap = [c for c in feas["conflicts"] if c["category"] == "capacity"]
    if ab.get("stated_m2") or cap:
        lines += ["", "## 面积与容量（先说清楚这个）", ""]
        if ab:
            lines.append(
                f"- 你说的面积：{ab.get('stated_m2') or '未提供'} ㎡；"
                f"模型实测套内：{ab.get('model_usable_m2') or 0:.1f} ㎡；"
                f"外轮廓：{ab.get('model_envelope_m2') or 0:.1f} ㎡")
            if float(ab.get("diff_ratio") or 0) > 0.05:
                lines.append(
                    f"- **两者差 {float(ab['diff_ratio']) * 100:.0f}%**："
                    "建筑面积含公摊、套内不含，使用面积还要再扣墙体——"
                    "方案与造价必须按同一个口径算，请确认以哪个为准")
        hc = feas.get("headcount") or 0
        if hc:
            lines.append(f"- 使用人数：{hc} 人")
        for c in cap:
            lines.append(f"- {c['problem']}。可选：{'；'.join(c['alternatives'][:3])}")

    lines += ["", "## 8. S2 概念设计的研究重点", ""]
    if opps["items"]:
        lines += [f"- {o['problem']}（下一步：{o['next_stage_recommendation']}）"
                  for o in opps["items"]]
    else:
        lines.append("- 尚无有证据的设计机会；S2 应先补齐需求与条件")

    if majors:
        lines += ["", "## 需在 S2 解决的重要条件", ""]
        lines += [f"- {c['problem']} → {c['recommendation']}" for c in majors]

    # --- the four consequences --------------------------------------------
    lines += ["", "## 本次确认决定什么、不决定什么", "",
              "**决定**：是否进入 S2 概念设计，以及任务书按其现状成立。", ""]
    if assess.limited_stages:
        lines += ["**不决定**（以下限制在后续阶段仍然有效）：", ""]
        for item in assess.limited_stages:
            lines.append(f"- {item['stage']}："
                         f"{'阶段受阻' if item['blocked'] else '部分工作受限'}")
            lines += [f"  - {r}" for r in item["restrictions"]]
    else:
        lines.append("**不决定**：无额外限制。")
    if assess.needs_human:
        lines += ["", "**须专业复核**：", ""] + [f"- {n}" for n in assess.needs_human]
    if assess.conditions:
        lines += ["", "**附条件推进**：", ""] + [f"- {c}" for c in assess.conditions]

    lines += ["", "## 请确认", "",
              "1. 以上 1–6 项与您的理解一致；",
              "2. 第 7 项中的问题您接受在 S2 前解决，或已明确可以搁置；",
              "3. 第 8 项的 S2 研究重点没有遗漏您最在意的问题；",
              "4. 您已阅读「本次确认决定什么、不决定什么」，并理解结构拆改与出图深度"
              "不在本次确认范围内。", "",
              "> 确认后形成任务书基准。此后修改需求将触发变更影响分析，"
              "原确认版保留在 S1 修订记录中，不会被直接覆盖。", ""]
    if extra:
        lines += ["## 备注", "", extra, ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------
@dataclass
class ApprovalOutcome:
    decision: str
    stage_status: str
    source: str = "owner"
    baseline: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    forced: bool = False
    summary_path: str = ""
    assessment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "decision_label": DECISION_LABEL.get(self.decision, self.decision),
            "stage_status": self.stage_status,
            "source": self.source,
            "source_label": SOURCE_LABEL.get(self.source, self.source),
            "baseline": dict(self.baseline),
            "notes": list(self.notes),
            "forced": self.forced,
            "summary_path": self.summary_path,
            "assessment": dict(self.assessment),
        }


def decide_gate(project: Project, decision: str, by: str = "",
                note: str = "", source: str = "owner",
                acknowledge: Sequence[str] = (), force: bool = False,
                summary_path: str = "") -> ApprovalOutcome:
    """Apply one G1 decision.

    ``source`` separates a real signature from a demonstration:

    * ``owner`` — writes a baseline that later stages can be measured against;
    * ``demo``  — records that the gate was waved through in a demo, writes no
      baseline, and can never be mistaken for the client's approval.

    A requirement contradiction blocks approval until the client acknowledges
    each item by id. ``force`` is the shortcut for that acknowledgement and is
    recorded — but it cannot lift a technical or statutory limitation, because
    those live in the stage guard, not in this gate.
    """
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision '{decision}'（应为 {'/'.join(DECISIONS)}）")
    if source not in SOURCES:
        raise ValueError(f"unknown source '{source}'（应为 {'/'.join(SOURCES)}）")

    # 基准摘要里含问答与来源；如果访谈状态是在确认之后才建立的，
    # brief_digest 会在下一次读取时突然变化，看起来像"业主改了需求"（真实踩过）。
    # 所以签名前先把访谈状态落定，再计算摘要。
    from .interview import ensure_intake

    ensure_intake(project)
    # 基准摘要里含问答与来源；如果访谈状态是在确认之后才建立的，
    # brief_digest 会在下一次读取时突然变化，看起来像"业主改了需求"（真实踩过）。
    # 所以签名前先把访谈状态落定，再计算摘要。
    from .interview import ensure_intake

    ensure_intake(project)
    store_precision(project)
    assess = assess_gate(project)
    notes: List[str] = []
    forced_flag = False

    if decision == "approved":
        acknowledged = {str(a) for a in acknowledge}
        open_blocks = [b for b in assess.blocks_gate
                       if str(b["id"]) not in acknowledged]
        if open_blocks and source == "owner":
            if force:
                forced_flag = True
                notes.append("在存在需求矛盾的情况下强制通过；已记录，供后续追溯")
            else:
                decision = "blocked"
                notes.append("存在必须由业主决定的需求矛盾，不能直接通过："
                             + "；".join(b["problem"] for b in open_blocks[:3]))
                notes.append("处理方式：业主对每一项作出取舍后，用 --acknowledge <id> "
                             "逐项确认；或用 --force 通过并留下记录")
        elif open_blocks and source == "demo":
            notes.append("演示模式：需求矛盾未处理，本次通过不构成业主签署")

    if decision == "approved":
        by_label = by or ("业主/主创" if source == "owner" else "演示流程")
        st = confirm_stage(project, "S1", by=by_label,
                           note=note or ("G1 任务书确认" if source == "owner"
                                         else "G1 演示确认（--assume-approval）"))
        entry = {
            "revision": project.revision,
            "digest": baseline_digest(project),
            "brief_digest": brief_digest(project),
            "confirmed_at": st.confirmed_at,
            "confirmed_by": st.confirmed_by,
            "source": source,
            "precision": assess.precision,
            "completeness": completeness(project)["ratio"],
            "forced": forced_flag,
            "acknowledged": sorted({str(a) for a in acknowledge}),
            "limitations": assess.limited_stages,
            "needs_human": assess.needs_human,
            "summary_path": summary_path,
        }
        if source == "owner":
            _intake(project)["baseline"] = entry
            _intake(project)["demo_approval"] = None
            notes.append(f"已形成任务书基准：r{project.revision} / {entry['digest']}")
        else:
            # A demo must not leave behind something a later stage can cite.
            _intake(project)["demo_approval"] = entry
            notes.append("演示模式：未写入任务书基准，后续阶段不得将其作为业主签署引用")
        baseline = entry
    elif decision == "revision_requested":
        st = reject_stage(project, "S1", reason=note or "客户要求修改任务书")
        baseline = _intake(project).get("baseline") or {}
        notes.append("已退回修改；任务书基准未变更，S1 需重新提交 G1")
    else:
        st = block_stage(project, "S1", note or "存在前置条件未解决")
        baseline = _intake(project).get("baseline") or {}
        notes.append("已阻断：解决前置条件后重新提交 G1")

    for item in assess.limited_stages:
        if item["restrictions"]:
            notes.append(f"{item['stage']} 仍受限：{item['restrictions'][0]}")

    return ApprovalOutcome(decision=decision, stage_status=st.status, source=source,
                           baseline=baseline, notes=notes, forced=forced_flag,
                           summary_path=summary_path,
                           assessment=assess.to_dict())


def check_baseline(project: Project) -> Dict[str, Any]:
    """Has anything the client signed changed since G1?"""
    base = _intake(project).get("baseline") or {}
    demo = _intake(project).get("demo_approval") or {}
    if not base:
        return {
            "has_baseline": False,
            "changed": False,
            "demo_only": bool(demo),
            "reason": ("仅有演示确认，未形成可引用基准" if demo else "尚未通过 G1"),
        }
    current = baseline_digest(project)
    current_brief = brief_digest(project)
    brief_changed = current_brief != base.get("brief_digest")
    limits_changed = current != base.get("digest")
    if brief_changed:
        kind, reason = "brief", "任务书内容已变更（需求 / 约束 / 来源），须走变更影响分析"
    elif limits_changed:
        kind, reason = "limitations", "任务书内容未变，但限制条件已更新（已核验或新增）"
    else:
        kind, reason = "none", "与已确认基准一致"
    return {
        "has_baseline": True,
        "changed": brief_changed or limits_changed,
        "change_kind": kind,
        "demo_only": False,
        "baseline_revision": base.get("revision"),
        "current_revision": project.revision,
        "baseline_digest": base.get("digest"),
        "current_digest": current,
        "baseline_brief_digest": base.get("brief_digest"),
        "current_brief_digest": current_brief,
        "confirmed_at": base.get("confirmed_at"),
        "confirmed_by": base.get("confirmed_by"),
        "requires_change_analysis": brief_changed,
        "reason": reason,
    }
