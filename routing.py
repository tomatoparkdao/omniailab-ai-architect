"""Chief Designer routing — stage based.

A request is turned into an explicit plan over the eight project stages: which
stages run, which capabilities own each stage, who must confirm at the gate,
and what the guardrails forbid right now.

Deliberately rule-based and deterministic so the plan can be read, tested and
argued with.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .changes import diagnose, is_geometry_change
from .model import Project
from .stage_state import can_start, confirmed, next_runnable, progress
from .stages import (
    STAGE_BY_ID,
    STAGE_ORDER,
    STAGES,
    stage_name,
    skills_for_stage,
)

# intent id -> stages it implies
INTENT_RULES: List[Dict[str, object]] = [
    {"id": "brief", "stages": ["S1"], "priority": 10,
     "kw": ["需求", "任务书", "brief", "预算", "面积要求", "功能表", "program",
            "功能需求", "户型要求"]},
    {"id": "site", "stages": ["S1"], "priority": 15,
     "kw": ["场地", "原始图", "户型图", "识图", "cad 图", "现场", "采光分析",
            "site", "原始建筑"]},
    {"id": "concept", "stages": ["S2"], "priority": 30,
     "kw": ["概念", "风格", "意向", "moodboard", "理念", "构思", "定位", "concept",
            "氛围", "调性"]},
    {"id": "plan", "stages": ["S3"], "priority": 40,
     "kw": ["平面", "布局", "布置", "分区", "动线", "平面方案", "layout", "plan",
            "空间规划"]},
    {"id": "preliminary", "stages": ["S4"], "priority": 55,
     "kw": ["初步设计", "深化", "立面", "吊顶", "天花", "地材", "做法",
            "材料方案", "灯光方案", "室内设计", "preliminary", "扩初"]},
    {"id": "visual", "stages": ["S5"], "priority": 60,
     "kw": ["效果图", "渲染", "表现", "漫游", "全景", "3d", "三维", "建模",
            "模型", "render", "visual", "bim"]},
    {"id": "freeze", "stages": ["S6"], "priority": 65,
     "kw": ["定稿", "锁定", "协调", "审定", "最终确认", "freeze", "技术协调"]},
    {"id": "document", "stages": ["S7"], "priority": 70,
     "kw": ["施工图", "平立剖", "剖面", "天花图", "灯具定位", "节点", "详图",
            "图纸", "dwg", "dxf", "drawing", "出图", "机电", "消防"]},
    {"id": "quantity", "stages": ["S8"], "priority": 80,
     "kw": ["材料清单", "工程量", "物料", "报价", "概算", "预算表", "清单",
            "takeoff", "boq", "cost", "采购"]},
    {"id": "deliver", "stages": ["S8"], "priority": 90,
     "kw": ["交付", "打包", "归档", "版本", "技术交底", "deliver", "package",
            "验收"]},
]

FULL_PIPELINE = list(STAGE_ORDER)

CHANGE_KEYWORDS = ["改", "移", "移动", "调整", "变更", "修改", "换", "扩", "缩",
                   "不满意", "不喜欢", "重做", "换掉", "改成", "去掉", "重新",
                   "change", "move", "revise", "update", "swap"]


@dataclass
class StageTask:
    order: int
    stage: str
    stage_name: str
    skills: List[str]
    deliverables: List[str]
    gate: str
    gate_label: str
    approver: str
    status: str = "pending"
    blocked_reason: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "order": self.order,
            "stage": self.stage,
            "stage_name": self.stage_name,
            "skills": list(self.skills),
            "deliverables": list(self.deliverables),
            "gate": {"id": self.gate, "label": self.gate_label, "approver": self.approver},
            "status": self.status,
            "blocked_reason": self.blocked_reason,
        }


@dataclass
class RoutePlan:
    request: str
    intents: List[str] = field(default_factory=list)
    tasks: List[StageTask] = field(default_factory=list)
    is_change: bool = False
    change_domain: str = ""
    change_landing_stage: str = ""
    change_geometry_affecting: bool = False
    rework_stages: List[str] = field(default_factory=list)
    guardrail_blocks: List[Dict[str, str]] = field(default_factory=list)
    stops: List[str] = field(default_factory=list)
    non_negotiable: List[str] = field(default_factory=list)
    next_stage: str = ""
    progress_percent: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "request": self.request,
            "intents": list(self.intents),
            "next_stage": self.next_stage,
            "progress_percent": self.progress_percent,
            "is_change": self.is_change,
            "change": {
                "domain": self.change_domain,
                "landing_stage": self.change_landing_stage,
                "geometry_affecting": self.change_geometry_affecting,
                "rework_stages": self.rework_stages,
            } if self.is_change else None,
            "tasks": [t.to_dict() for t in self.tasks],
            "guardrail_blocks": list(self.guardrail_blocks),
            "stops": list(self.stops),
            "non_negotiable": list(self.non_negotiable),
        }

    def markdown(self) -> str:
        lines = ["# 阶段路由计划", "", f"**请求**：{self.request}", ""]
        if self.is_change:
            lines += [
                "## 变更识别", "",
                f"- 变更领域：**{self.change_domain}**",
                f"- 落点阶段：**{stage_name(self.change_landing_stage)}**",
                f"- 是否改变几何：**{'是' if self.change_geometry_affecting else '否'}**",
                f"- 回流阶段：{', '.join(stage_name(s) for s in self.rework_stages)}",
                "",
                "> 变更走失效重算，不走局部手改。",
                "",
            ]
        lines += ["## 阶段任务", "", "| # | 阶段 | 负责能力 | 门禁 | 状态 |", "|---|---|---|---|---|"]
        for t in self.tasks:
            gate = f"{t.gate} {t.gate_label}"
            lines.append(
                f"| {t.order} | {t.stage_name} | {', '.join(t.skills)} | {gate} | {t.status} |"
            )
        if self.guardrail_blocks:
            lines += ["", "## 被门禁拦下的动作", ""]
            for b in self.guardrail_blocks:
                lines.append(f"- **{b['stage_name']}**：{b['reason']}")
        if self.stops:
            lines += ["", "## 必须停下来的地方", ""] + [f"- {s}" for s in self.stops]
        lines += ["", "## 不可协商", ""] + [f"- {n}" for n in self.non_negotiable]
        return "\n".join(lines)


def detect_intents(request: str) -> List[str]:
    low = request.lower()
    if any(k in low for k in ["全流程", "整套", "整个项目", "从头做", "全案",
                              "端到端", "end to end", "everything", "full"]):
        return ["full"]
    hits: List[Tuple[int, str]] = []
    for rule in INTENT_RULES:
        if any(str(k).lower() in low for k in rule["kw"]):  # type: ignore[union-attr]
            hits.append((int(rule["priority"]), str(rule["id"])))
    hits.sort()
    return [h[1] for h in hits]


def stages_for_intents(intents: Sequence[str]) -> List[str]:
    """Intents -> stages, closed over the mandatory prerequisites, in pipeline order."""
    if "full" in intents:
        return list(FULL_PIPELINE)
    wanted: set[str] = set()
    for i in intents:
        for rule in INTENT_RULES:
            if rule["id"] == i:
                wanted.update(str(s) for s in rule["stages"])  # type: ignore[union-attr]
    if not wanted:
        return []
    # transitive closure over REQUIRES_CONFIRMED: a downstream stage is only
    # meaningful if its upstream has been produced and confirmed first
    changed = True
    while changed:
        changed = False
        for s in list(wanted):
            for pre in _prerequisites(s):
                if pre not in wanted:
                    wanted.add(pre)
                    changed = True
    return [s for s in STAGE_ORDER if s in wanted]


def _prerequisites(stage_id: str) -> List[str]:
    from .stages import REQUIRES_CONFIRMED

    return list(REQUIRES_CONFIRMED.get(stage_id, []))


def route(request: str, project: Optional[Project] = None,
          respect_gates: bool = True) -> RoutePlan:
    plan = RoutePlan(request=request)
    plan.intents = detect_intents(request)
    diag = diagnose(request)
    plan.is_change = any(k in request.lower() for k in CHANGE_KEYWORDS) and (
        diag.primary != "visual_only" or is_geometry_change(request)
    )

    if plan.is_change and project is not None:
        from .changes import rework_stages

        plan.change_domain = diag.label
        plan.change_landing_stage = diag.landing_stage
        plan.change_geometry_affecting = diag.geometry_affecting
        plan.rework_stages = rework_stages(project, diag, "room")
        stage_list = list(plan.rework_stages)
    else:
        stage_list = stages_for_intents(plan.intents) or ["S1", "S2", "S3"]

    for i, sid in enumerate(stage_list, start=1):
        st = STAGE_BY_ID.get(sid)
        if st is None:
            continue
        task = StageTask(
            order=i, stage=sid, stage_name=f"{st.code} {st.name}",
            skills=skills_for_stage(sid), deliverables=list(st.deliverables),
            gate=st.gate.id, gate_label=st.gate.label, approver=st.gate.approver,
        )
        if project is not None and respect_gates:
            ok, reason = can_start(project, sid)
            if confirmed(project, sid) and sid not in plan.rework_stages:
                task.status = "already_confirmed"
            elif ok:
                task.status = "ready"
            else:
                task.status = "blocked"
                task.blocked_reason = reason
                plan.guardrail_blocks.append(
                    {"stage": sid, "stage_name": task.stage_name, "reason": reason}
                )
        plan.tasks.append(task)

    if project is not None:
        p = progress(project)
        plan.progress_percent = p["percent"]
        nxt, reason = next_runnable(project)
        plan.next_stage = nxt
        if reason:
            plan.guardrail_blocks.append(
                {"stage": nxt, "stage_name": stage_name(nxt) if nxt else "—", "reason": reason}
            )

    plan.stops = _stops(project)
    plan.non_negotiable = _non_negotiable()
    return plan


def _stops(project: Optional[Project]) -> List[str]:
    stops = [
        "结构安全、消防、无障碍、机电负荷与当地法规符合性——须持证专业人员复核签署",
        "方案深度成果不得当作施工图使用",
    ]
    if project is not None:
        uncertain = [e.id for e in project.elements if e.uncertain]
        if uncertain:
            stops.append(
                "以下构件为推断所得，须现场核对后方可用于施工图：" + ", ".join(uncertain[:12])
            )
        awaiting = progress(project)["awaiting_confirmation"]
        if awaiting:
            stops.append(
                "以下阶段成果已提交、等待确认，未确认前不得推进："
                + "、".join(stage_name(s) for s in awaiting)
            )
    return stops


def _non_negotiable() -> List[str]:
    return [
        "概念与平面可交互迭代，但业主确认功能需求前不得开始精细建模（R1）",
        "CAD 图纸并非最后才画：方案深度图自初步设计（S4）起即可绘制，"
        "区别在 schematic 与 construction 两个深度（R2）",
        "物料与成本估算从前期起动态进行，深化完成后才形成正式清单（R3）",
        "平面未确认不得出正式图纸；设计锁定后不得局部手改，须走变更影响分析（R4）",
        "AI 效果图不是尺寸依据；施工图必须由经校核的几何/BIM 模型生成",
    ]
