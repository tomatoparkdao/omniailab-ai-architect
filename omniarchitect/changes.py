"""设计变更影响分析 (change impact analysis).

This is the capability that keeps the system from becoming a document
generator. When the client says "I don't like the TV feature wall", the answer
is not "here is a new render". The answer is:

1. **诊断** — is this a material problem, an elevation-design problem, or a
   plan-dimension problem? Those land on different stages.
2. **定位** — which spaces and elements does it actually touch.
3. **影响面** — which artifacts must be regenerated, and which confirmed work
   must be left alone.
4. **回流** — the ordered list of stages to re-run, plus the gates that must be
   re-submitted. Everything already confirmed and untouched stays confirmed.

The hard rule: a finish-only change must never invalidate geometry, and a
geometry change must always invalidate everything downstream of it.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .errors import ModelError, ValidationError
from .model import Element, Project, Space
from .revisions import (
    InvalidationReport,
    apply_geometry_change,
    apply_space_change,
    dependents_of,
    invalidate,
    record_change,
)
from .stages import DOWNSTREAM, STAGE_BY_ID, STAGE_ORDER, stage_name

# --------------------------------------------------------------------------
# domain classification
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class DomainRule:
    id: str
    label: str
    landing_stage: str
    geometry_affecting: bool
    keywords: tuple
    diagnosis: str
    typical_fix: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "landing_stage": self.landing_stage,
            "geometry_affecting": self.geometry_affecting,
            "diagnosis": self.diagnosis,
            "typical_fix": self.typical_fix,
        }


DOMAIN_RULES: List[DomainRule] = [
    DomainRule(
        "scope_program", "任务书与功能范围", "S1", True,
        ("加一间", "少一间", "改成三居", "面积不够", "功能变了", "房间数",
         "program", "add a room", "改户型"),
        "改动落在任务书：功能或面积目标变了，平面的一切推论都要重来",
        "修订任务书并重新确认面积指标，再重跑概念与平面",
    ),
    DomainRule(
        "plan_dimension", "平面尺寸与墙体", "S3", True,
        ("移墙", "墙往", "扩大", "缩小", "尺寸", "进深", "面宽", "开间",
         "拆墙", "砌墙", "往外", "往里", "加宽", "变窄", "mm", "毫米", "厘米",
         "wall", "dimension", "widen", "narrow", "move the wall"),
        "改动落在平面几何：坐标或尺寸变了，所有下游产物必然失效",
        "在统一空间模型里改坐标 → 触发全局失效重算，禁止局部手改图纸",
    ),
    DomainRule(
        "layout_zoning", "分区与动线", "S3", True,
        ("分区", "动线", "布局换", "换布局", "走廊", "开门方向", "门位置",
         "swap", "circulation", "zoning", "replan"),
        "改动落在空间组织：房间边界与门位会变，属几何变更",
        "重排分区与门位，重新校核净宽与流线",
    ),
    DomainRule(
        "elevation", "立面与造型", "S4", False,
        ("背景墙", "电视墙", "立面", "造型", "墙面做法", "护墙", "形象墙",
         "玄关柜", "垭口", "窗套", "feature wall", "elevation", "tv wall"),
        "改动落在立面深化：平面尺寸不变，但立面、材料与效果图要重做",
        "只改该立面的分缝、比例与材料，平面与结构不动",
    ),
    DomainRule(
        "ceiling", "顶面与吊顶", "S4", False,
        ("吊顶", "天花", "顶面", "跌级", "灯槽", "暖气", "窗帘盒", "净高不够",
         "ceiling", "soffit"),
        "改动落在顶面：影响净高、灯位与机电点位，平面不变",
        "重做该区域吊顶剖面与灯槽，复核净高与点位",
    ),
    DomainRule(
        "material", "材料与色彩", "S4", False,
        ("材质", "材料", "颜色", "色彩", "换色", "石材", "木饰面", "涂料",
         "瓷砖", "地板", "地毯", "面料", "软装", "五金", "质感",
         "material", "colour", "color", "finish", "stone", "timber"),
        "改动落在材料层：几何完全不变，只影响做法、表现与清单",
        "换材料与色号即可；不要因此动平面或立面尺寸",
    ),
    DomainRule(
        "lighting", "灯光与照明", "S4", False,
        ("灯光", "照明", "灯带", "筒灯", "色温", "照度", "洗墙", "灯位",
         "灯具", "氛围光", "lighting", "lamp", "kelvin"),
        "改动落在照明：影响灯位、电路点位与效果图夜间表现",
        "重排灯位与灯带走向，同步点位图与夜间效果图",
    ),
    DomainRule(
        "mep", "机电与设备", "S4", False,
        ("插座", "风口", "空调", "水管", "排水", "开关", "点位", "机电",
         "新风", "地暖", "检修口", "mep", "socket", "duct", "hvac"),
        "改动落在机电：影响点位、净高与检修口，需专业协调复核",
        "调整点位并重跑机电协调校核；涉及结构开洞须专业确认",
    ),
    DomainRule(
        "furniture_layout", "家具与尺度", "S3", False,
        ("家具", "沙发", "床", "柜", "餐桌", "尺度", "尺寸不够", "放不下",
         "通行", "过道窄", "furniture", "sofa", "wardrobe", "clearance"),
        "改动落在家具与人体工学：几何边界不变，但布置、通道与清单要重算",
        "只调整家具选型与位置，平面墙体不动",
    ),
    DomainRule(
        "style_concept", "概念与风格", "S2", False,
        ("风格", "概念", "调性", "感觉不对", "不像", "太冷", "太暖", "不够高级",
         "重新定位", "style", "concept", "mood"),
        "改动落在概念层：方向变了，意向板与后续所有设计判断的标尺都要改",
        "重做概念与意向板，并在平面阶段重新验证概念是否成立",
    ),
    DomainRule(
        "visual_only", "表现与镜头", "S5", False,
        ("效果图", "渲染", "镜头", "角度", "光线不对", "重出图", "p图",
         "render", "camera", "angle"),
        "改动只落在表现：设计本身不变，重出图即可",
        "调整机位、材质贴图与光照重新渲染，不动设计数据",
    ),
]

DOMAIN_BY_ID = {r.id: r for r in DOMAIN_RULES}

# artifact types that a finish-level change never invalidates
GEOMETRY_ONLY_TYPES = {"drawing", "model", "schedule_dimension"}
FINISH_TYPES = {"render", "image", "visual", "material_schedule", "cost"}


@dataclass
class Diagnosis:
    primary: str
    label: str
    landing_stage: str
    geometry_affecting: bool
    confidence: float
    matched: List[str] = field(default_factory=list)
    considered: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    typical_fix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "label": self.label,
            "landing_stage": self.landing_stage,
            "landing_stage_name": stage_name(self.landing_stage),
            "geometry_affecting": self.geometry_affecting,
            "confidence": round(self.confidence, 2),
            "matched_keywords": self.matched,
            "alternatives_considered": self.considered,
            "explanation": self.explanation,
            "typical_fix": self.typical_fix,
        }


@dataclass
class ReworkItem:
    stage: str
    stage_name: str
    action: str
    artifacts: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "stage_name": self.stage_name,
            "action": self.action,
            "skills": list(self.skills),
            "artifacts_to_regenerate": list(self.artifacts),
        }


@dataclass
class ChangeImpactReport:
    request: str
    diagnosis: Diagnosis
    scope: str = "local"                      # local | room | level | project
    targets: List[str] = field(default_factory=list)
    affected_spaces: List[str] = field(default_factory=list)
    affected_elements: List[str] = field(default_factory=list)
    affected_artifacts: List[str] = field(default_factory=list)
    preserved: List[str] = field(default_factory=list)
    rework: List[ReworkItem] = field(default_factory=list)
    gates_to_reopen: List[Dict[str, str]] = field(default_factory=list)
    invalidation: Optional[InvalidationReport] = None
    risks: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "applied": self.applied,
            "scope": self.scope,
            "diagnosis": self.diagnosis.to_dict(),
            "targets": self.targets,
            "affected": {
                "spaces": self.affected_spaces,
                "elements": self.affected_elements,
                "artifacts": self.affected_artifacts,
            },
            "preserved_confirmed_work": self.preserved,
            "rework_plan": [r.to_dict() for r in self.rework],
            "gates_to_reopen": self.gates_to_reopen,
            "invalidation": self.invalidation.to_dict() if self.invalidation else None,
            "risks": self.risks,
            "notes": self.notes,
            "method": {
                "change_ledger": "逐条核销的批注台账：每一轮变更都可追溯、可核销",
            },
        }

    def markdown(self) -> str:
        d = self.diagnosis
        lines = [
            "# 设计变更影响分析", "",
            f"**变更请求**：{self.request}", "",
            "## 一、诊断", "",
            f"- 判定领域：**{d.label}**（置信度 {d.confidence:.0%}）",
            f"- 落点阶段：**{stage_name(d.landing_stage)}**",
            f"- 是否改变几何：**{'是' if d.geometry_affecting else '否'}**",
            f"- 判断依据：{d.explanation}",
            f"- 命中关键词：{', '.join(d.matched) or '（无，按默认流程处理）'}",
            f"- 处理原则：{d.typical_fix}",
        ]
        if d.considered:
            lines += ["", "### 同时考虑过的其他可能", ""]
            for c in d.considered:
                lines.append(
                    f"- {c['label']}（{c['score']:.0f}%）→ 排除理由：{c['reason']}"
                )
        lines += ["", "## 二、影响范围", "", f"- 范围：**{self.scope}**"]
        if self.affected_spaces:
            lines.append(f"- 受影响空间：{', '.join(self.affected_spaces)}")
        if self.affected_elements:
            lines.append(f"- 受影响构件：{', '.join(self.affected_elements[:30])}")
        lines += ["", "### 需要重新生成的成果", ""]
        if self.affected_artifacts:
            lines += [f"- `{a}`" for a in self.affected_artifacts]
        else:
            lines.append("- （当前模型尚未登记该范围内的成果）")
        lines += ["", "## 三、保持不变", ""]
        if self.preserved:
            lines += [f"- `{p}`（已确认，与本次变更无交集）" for p in self.preserved]
        else:
            lines.append("- （无已确认成果需要保护）")
        lines += ["", "## 四、回流计划", ""]
        for i, r in enumerate(self.rework, 1):
            lines.append(f"{i}. **{r.stage_name}** — {r.action}")
            if r.skills:
                lines.append(f"   - 负责能力：{', '.join(r.skills)}")
            if r.artifacts:
                lines.append(f"   - 重做：{', '.join(r.artifacts)}")
        lines += ["", "## 五、需要重新提交的确认", ""]
        if self.gates_to_reopen:
            lines += [f"- {g['label']}（{g['stage_name']}）" for g in self.gates_to_reopen]
        else:
            lines.append("- 无需重新确认（变更未越过任何门禁）")
        if self.risks:
            lines += ["", "## 六、风险提示", ""] + [f"- {r}" for r in self.risks]
        if self.notes:
            lines += ["", "### 说明", ""] + [f"- {n}" for n in self.notes]
        lines += ["", "---", "",
                  "> 变更通过失效重算推进，不通过局部手改图纸推进。"
                  "已确认且不受影响的部分保持锁定。"]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# 1. classify
# --------------------------------------------------------------------------
def diagnose(text: str) -> Diagnosis:
    low = text.lower()
    scored: List[Tuple[float, DomainRule, List[str]]] = []
    for rule in DOMAIN_RULES:
        hits = [k for k in rule.keywords if k.lower() in low]
        if not hits:
            continue
        # longer keyword = more specific = stronger signal
        score = sum(len(h) for h in hits) + 2 * (len(hits) - 1)
        scored.append((float(score), rule, hits))
    if not scored:
        rule = DOMAIN_BY_ID["visual_only"]
        return Diagnosis(
            primary=rule.id, label=rule.label, landing_stage=rule.landing_stage,
            geometry_affecting=rule.geometry_affecting, confidence=0.30,
            matched=[], considered=[],
            explanation="未识别到明确的设计领域关键词，按『仅调整表现』处理；"
                        "若实际涉及尺寸或做法，请明确说明改动对象",
            typical_fix=rule.typical_fix,
        )

    scored.sort(key=lambda t: -t[0])
    top_score, top_rule, top_hits = scored[0]
    total = sum(s for s, _, _ in scored) or 1.0
    confidence = min(0.95, 0.45 + 0.5 * (top_score / total))

    considered = [
        {
            "label": r.label,
            "score": 100.0 * s / total,
            "reason": _exclusion_reason(top_rule, r),
        }
        for s, r, _ in scored[1:4]
    ]
    return Diagnosis(
        primary=top_rule.id, label=top_rule.label,
        landing_stage=top_rule.landing_stage,
        geometry_affecting=top_rule.geometry_affecting,
        confidence=confidence, matched=top_hits, considered=considered,
        explanation=top_rule.diagnosis, typical_fix=top_rule.typical_fix,
    )


def _exclusion_reason(winner: DomainRule, other: DomainRule) -> str:
    if winner.geometry_affecting and not other.geometry_affecting:
        return "关键词更像几何改动的具体对象（尺寸/墙体），而非其表面做法"
    if not winner.geometry_affecting and other.geometry_affecting:
        return "未出现改变坐标或尺寸的表述，按不改变几何处理"
    if winner.landing_stage < other.landing_stage:
        return f"改动落点更靠前（{stage_name(winner.landing_stage)}），按更上游处理"
    return "命中关键词更具体、更少歧义"


# --------------------------------------------------------------------------
# 2. locate
# --------------------------------------------------------------------------
def locate(project: Project, text: str, diagnosis: Diagnosis) -> Tuple[List[str], List[str], List[str], str]:
    """Return (targets, affected_spaces, affected_elements, scope)."""
    low = text.lower()
    spaces: List[str] = []
    elements: List[str] = []
    targets: List[str] = []

    name_hits: List[str] = []
    use_hits: List[str] = []
    for s in project.spaces:
        if s.use == "envelope":
            continue
        if (s.name and s.name.lower() in low) or s.id.lower() in low:
            name_hits.append(s.id)
            continue
        use_map = {
            "living": ("客厅", "起居", "living"),
            "dining": ("餐厅", "dining"),
            "kitchen": ("厨房", "kitchen"),
            "bedroom": ("卧室", "主卧", "次卧", "儿童房", "bedroom"),
            "bathroom": ("卫生间", "浴室", "bathroom"),
            "study": ("书房", "study"),
            "storage": ("储藏", "衣帽", "storage"),
            "circulation": ("玄关", "门厅", "走廊", "过道", "entry", "hall", "corridor"),
            "service": ("家务", "洗衣", "laundry"),
        }
        if any(k in low for k in use_map.get(s.use, ())):
            use_hits.append(s.id)

    # A named room beats a category match: "次卧" must not drag in every bedroom.
    spaces = name_hits or use_hits
    targets.extend(spaces)

    if diagnosis.primary == "furniture_layout":
        cat_map = {
            "sofa": ("沙发",), "tv_unit": ("电视",), "dining_table": ("餐桌",),
            "bed_king": ("床", "主卧"), "bed_queen": ("床",), "wardrobe": ("衣柜", "柜"),
            "kitchen_run": ("橱柜", "厨房"), "desk": ("书桌",), "basin": ("台盆",),
        }
        for e in project.elements:
            if e.type != "furniture":
                continue
            cat = str(e.geometry.get("category") or "")
            if any(k in low for k in cat_map.get(cat, ())):
                if not spaces or str(e.geometry.get("space_id") or "") in spaces:
                    elements.append(e.id)

    if diagnosis.primary in ("plan_dimension", "layout_zoning", "scope_program"):
        host_spaces = set(spaces)
        for e in project.elements:
            if e.type != "wall":
                continue
            if e.id.lower() in low:
                elements.append(e.id)
                continue
            if host_spaces and (set(e.properties.get("space_ids") or []) & host_spaces):
                elements.append(e.id)

    if diagnosis.primary == "lighting":
        for s in project.spaces:
            if s.id in spaces and s.properties.get("lighting"):
                targets.append(f"{s.id}:lighting")

    # --- bounding elements: walls, openings and furniture of the room --------
    # Without these the blast radius is only the space itself, and the drawings
    # and renders that actually depict the change would be missed.
    if spaces:
        room_set = set(spaces)
        wall_ids: set[str] = set()
        for e in project.elements:
            if e.type == "wall":
                if set(e.properties.get("space_ids") or []) & room_set:
                    wall_ids.add(e.id)
            elif e.type == "furniture":
                if str(e.geometry.get("space_id") or "") in room_set:
                    elements.append(e.id)
        for e in project.elements:
            if e.is_opening and str(e.geometry.get("host_wall") or "") in wall_ids:
                elements.append(e.id)
        elements.extend(sorted(wall_ids))

    targets = list(dict.fromkeys(targets))
    elements = list(dict.fromkeys(elements))
    if len(spaces) >= max(3, len([s for s in project.spaces if s.use != 'envelope']) // 2):
        scope = "level"
    elif len(spaces) >= 1:
        scope = "room"
    elif diagnosis.primary in ("scope_program",):
        scope = "project"
    else:
        scope = "local"
    return targets, spaces, elements, scope


# --------------------------------------------------------------------------
# 3/4. blast radius, rework plan, gates
# --------------------------------------------------------------------------
# A finish-level change normally leaves plan geometry alone. But a façade or
# ceiling change *does* alter elevations and ceiling plans, so drawings and
# models derived from those walls must still be regenerated.
REGEN_GEOMETRY_FOR = {"elevation", "ceiling", "lighting", "mep"}


def _artifact_kind(artifact_type: str) -> str:
    t = artifact_type.lower()
    if t in ("render", "image", "visual", "walkthrough"):
        return "finish"
    if t in ("drawing", "model", "bim", "ifc"):
        return "geometry"
    if t in ("schedule", "cost", "material_schedule"):
        return "quantity"
    return "document"


RESTAGE_ACTIONS: Dict[str, str] = {
    "S1": "修订任务书与面积指标，重新校核预算口径",
    "S2": "重做概念方向与意向板关键词（标尺变了，后续判断都要重来）",
    "S3": "在统一空间模型里重排分区、房间边界与门位，重跑人体工学校核",
    "S4": "重做受影响区域的做法、材料与灯具定位，复核点位与净高",
    "S5": "由更新后的模型重新构建 3D 场景并重出效果图（保持多视角一致）",
    "S6": "重新审定方案并重跑专业协调与造价适配，更新锁定基线",
    "S7": "重出受影响图纸与模型，保持图纸间尺寸一致",
    "S8": "重算工程量、更新材料表并重新打包交付",
}


def rework_stages(project: Project, diagnosis: Diagnosis, scope: str) -> List[str]:
    """Which stages must re-run — narrowed by what the change can actually touch."""
    plan = list(DOWNSTREAM.get(diagnosis.landing_stage, [diagnosis.landing_stage]))
    d = diagnosis.primary
    if d == "visual_only":
        plan = [s for s in plan if s in ("S5", "S8")]
    elif d in ("material", "lighting", "mep", "ceiling", "elevation", "furniture_layout"):
        # finish / services level: geometry-producing stages stay untouched
        plan = [s for s in plan if s != "S3"]
        if d == "furniture_layout":
            plan = [s for s in plan if s != "S3"] + ["S3"]
            plan = list(dict.fromkeys(plan))
    elif d == "style_concept":
        plan = [s for s in plan if s != "S7"] if scope == "local" else plan
    if scope == "local":
        plan = [s for s in plan if s != "S1"]
    return plan or [diagnosis.landing_stage]


def _artifacts_in(stage_id: str) -> List[str]:
    st = STAGE_BY_ID.get(stage_id)
    return list(st.deliverables) if st else []


def analyse(
    project: Project,
    text: str,
    apply: bool = True,
    author: str = "omniailab-ai-architect",
) -> ChangeImpactReport:
    diag = diagnose(text)
    targets, spaces, elements, scope = locate(project, text, diag)
    rep = ChangeImpactReport(request=text, diagnosis=diag, scope=scope,
                             targets=targets, affected_spaces=spaces,
                             affected_elements=elements)

    # ---- blast radius over registered artifacts -------------------------
    seeds = list(dict.fromkeys([*spaces, *elements, *targets]))
    affected_artifacts = dependents_of(project, seeds) if seeds else []

    filtered: List[str] = []
    regen_geometry = (
        diag.geometry_affecting or diag.primary in REGEN_GEOMETRY_FOR
    )
    for aid in affected_artifacts:
        art = project.artifact(aid)
        kind = _artifact_kind(art.type)
        if kind == "geometry" and not regen_geometry:
            rep.notes.append(
                f"{aid} 为几何类成果且本次变更不改变坐标/尺寸——保持有效，不重算"
            )
            continue
        filtered.append(aid)
    rep.affected_artifacts = filtered

    # scope narrowing: an artifact survives only if it actually references one of
    # the seeds (the affected spaces *or* their bounding elements)
    if scope in ("local", "room") and seeds:
        narrowed = []
        for aid in rep.affected_artifacts:
            art = project.artifact(aid)
            if any(seed in art.depends_on for seed in seeds) or not art.depends_on:
                narrowed.append(aid)
            else:
                rep.preserved.append(aid)
        rep.affected_artifacts = narrowed

    all_ids = {a.id for a in project.artifacts}
    for aid in sorted(all_ids - set(rep.affected_artifacts)):
        if aid not in rep.preserved:
            art = project.artifact(aid)
            if art.status in ("validated", "issued"):
                rep.preserved.append(aid)

    # ---- rework plan ----------------------------------------------------
    plan = rework_stages(project, diag, scope)
    from .stages import skills_for_stage  # local import to avoid a cycle

    for stage_id in plan:
        rep.rework.append(
            ReworkItem(
                stage=stage_id,
                stage_name=stage_name(stage_id),
                action=RESTAGE_ACTIONS.get(stage_id, "重新执行该阶段"),
                artifacts=_artifacts_in(stage_id),
                skills=skills_for_stage(stage_id)[:6],
            )
        )

    # ---- gates to re-open ----------------------------------------------
    for stage_id in plan:
        st = STAGE_BY_ID.get(stage_id)
        if st and st.gate.id in ("G3", "G4", "G5", "G6", "G7", "G8"):
            rep.gates_to_reopen.append(
                {"stage": stage_id, "stage_name": stage_name(stage_id),
                 "gate": st.gate.id, "label": st.gate.label}
            )

    # ---- risks ----------------------------------------------------------
    if diag.geometry_affecting and scope in ("level", "project"):
        rep.risks.append(
            "这是大范围几何变更：材料工程量、施工图与既有报价区间都会失效，"
            "须在变更前先出造价影响判断"
        )
    if diag.primary == "material" and diag.confidence < 0.6:
        rep.risks.append("诊断置信度偏低：请确认改动只是换材料，还是同时改变立面比例/尺寸")
    if diag.primary == "elevation":
        rep.risks.append("立面改动容易被误判为材料改动；若涉及墙体位置或厚度，须按几何变更重走全程")
    if "S7" in plan and project.meta.get("stage_state", {}).get("S7", {}).get("status") == "confirmed":
        rep.risks.append("施工图已确认，本次变更将使其作废并需要专业复核重新签署")
    if not rep.affected_artifacts:
        rep.notes.append("模型内尚未登记该范围内的成果，回流计划按阶段给出，不按成果清单给出")

    # ---- apply ----------------------------------------------------------
    if apply:
        if diag.geometry_affecting and elements:
            wall = next((e for e in elements if e.startswith(("W",))), None)
            if wall:
                try:
                    rep.invalidation = apply_geometry_change(
                        project, wall, {}, author=author,
                        detail=f"变更触发：{text}",
                    )
                except ModelError:
                    rep.invalidation = _soft_invalidate(project, seeds, text, author)
            else:
                rep.invalidation = _soft_invalidate(project, seeds, text, author)
        else:
            rep.invalidation = _soft_invalidate(project, seeds, text, author)
        _reopen_gates(project, plan)
        rep.applied = True

    return rep


def _soft_invalidate(project: Project, seeds: Sequence[str], text: str,
                     author: str) -> InvalidationReport:
    stale = invalidate(project, list(seeds)) if seeds else []
    project.revision += 1
    record_change(project, kind="change", detail=f"变更影响分析：{text}",
                  targets=list(seeds)[:40], author=author, invalidated=stale)
    untouched = [a.id for a in project.artifacts if a.id not in stale]
    return InvalidationReport(revision=project.revision, changed=list(seeds)[:40],
                              stale=stale, untouched=untouched)


def _reopen_gates(project: Project, plan: Sequence[str]) -> None:
    state = dict(project.meta.get("stage_state") or {})
    for stage_id in plan:
        if stage_id in state:
            state[stage_id] = {
                **state[stage_id],
                "status": "rework",
                "confirmed_at": "",
                "note": "变更回流，需重新确认",
            }
    project.meta["stage_state"] = state


# --------------------------------------------------------------------------
# convenience
# --------------------------------------------------------------------------
def explain(project: Project, text: str) -> Dict[str, Any]:
    """Dry run: what would happen, without touching the model."""
    return analyse(project, text, apply=False).to_dict()


def is_geometry_change(text: str) -> bool:
    return diagnose(text).geometry_affecting
