"""Eight-stage professional design workflow (v1.0 stage model).

The system used to run eighteen specialist skills in a line. That confused two
different things:

* **岗位能力 (capability)** — what a design studio's roles can do. Eighteen of
  them, and one capability routinely serves several stages (Lighting Design
  appears at concept direction, at preliminary design *and* at lamp-location
  drawings).
* **业务阶段 (stage)** — how a real project actually advances. Eight stages,
  each with its own deliverable, its own entry/exit criteria and its own
  client-approval gate.

This module is the single authority for the stage model. Routing, the workflow
state machine, change-impact analysis and the CLI all read from here.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from .errors import ModelError

# --------------------------------------------------------------------------
# capability catalogue — the professional capabilities as practised in a design
# studio, mapped to the stages where each one is used. A capability may serve
# several stages; the stage is the business process, the capability is the job.
# --------------------------------------------------------------------------
SOURCE_OMNI = "OmniAiLab"


@dataclass(frozen=True)
class Capability:
    slug: str
    name: str
    stages: tuple
    source: str = SOURCE_OMNI
    legacy: str = ""          # original specialist brief under skills/
    responsibility: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "slug": self.slug,
            "name": self.name,
            "stages": list(self.stages),
            "source": self.source,
            "legacy": self.legacy,
            "responsibility": self.responsibility,
        }


S1, S2, S3, S4, S5, S6, S7, S8 = "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"

CAPABILITIES: List[Capability] = [
    # --- 01 项目启动与设计任务书 ------------------------------------------
    Capability("design-brief", "设计任务书", (S1, S6), legacy="01-brief",
               responsibility="需求访谈、功能任务书、面积与预算口径、验收标准"),
    Capability("site-analysis", "场地与建筑条件分析", (S1,),
               legacy="02-site-analysis",
               responsibility="原始建筑条件、朝向采光、动线与限制、结构不确定性标注"),
    Capability("existing-drawing-analysis", "原始图纸解析", (S1,),
               legacy="09-cad-analysis",
               responsibility="图层、墙体、尺寸、门窗识别；区分可置信信息与推断信息"),

    # --- 02 概念方案设计 --------------------------------------------------
    Capability("concept-design", "概念方案设计", (S2, S3), legacy="03-concept",
               responsibility="设计定位、概念主张、空间原型、风格与案例参照"),
    Capability("moodboard-aesthetic-iteration", "意向板与审美迭代", (S2, S5),
               responsibility="关键词锚定、多框架量化打分、跨轮整改追踪"),
    Capability("create-draw", "概念图解与评图", (S2, S4, S7),
               responsibility="红蓝笔图形语义、概念图解、图面方向表达"),

    # --- 03 平面方案设计 --------------------------------------------------
    Capability("space-planning", "空间规划", (S3,), legacy="04-space-planning",
               responsibility="分区、平面布置、面积配比、流线组织"),
    Capability("layout-optimization", "布局优化", (S3, S6),
               responsibility="多方案比较、房间比例与进深优化、开放度权衡"),
    Capability("ergonomics", "人体工学与尺度", (S3, S4),
               responsibility="净宽、通行、操作面、家具尺度与净距校核"),
    Capability("concept-visualization", "概念效果图", (S3, S4),
               responsibility="平面确认后立即出概念效果图：由 OmniAiLab 画布按机位生成，"
                              "用于业主建立空间感受；一律标注非权威，不得作为尺寸依据"),

    # --- 04 初步设计 -----------------------------------------------------
    Capability("interior-design", "室内设计", (S4, S6), legacy="06-interior",
               responsibility="顶面、墙面、地面、软硬装整合与做法定案"),
    Capability("architectural-design", "建筑设计", (S1, S4), legacy="05-architecture",
               responsibility="建筑体量、立面、剖面与空间组织（建筑项目启用）"),
    Capability("material-design", "材料与色彩设计", (S4, S5, S8), legacy="08-materials",
               responsibility="材料组合、色彩体系、工艺与规格、面积占比"),
    Capability("lighting-design", "灯光设计", (S2, S4, S7), legacy="07-lighting",
               responsibility="自然光、人工照明、照度与氛围；后期灯具定位"),
    Capability("building-services", "机电与设备协同", (S4, S6, S7), legacy="15-mep",
               responsibility="电气、给排水、暖通、消防对空间与净高的影响"),
    Capability("cad-drafting", "CAD 制图", (S4, S7), legacy="14-documents",
               responsibility="方案图与正式施工图两个深度：schematic / construction"),

    # --- 05 3D 建模与效果图表现 ------------------------------------------
    Capability("3d-modeling", "3D 空间建模", (S5,), legacy="11-3d",
               responsibility="由统一空间模型构建可编辑的场景与构件"),
    Capability("scene-rendering", "场景渲染", (S5,), legacy="12-render",
               responsibility="相机、材质、光影、批量多视角一致出图"),
    Capability("ai-visualization", "AI 视觉表现", (S5,),
               responsibility="图片模型辅助表现；输出一律标注为非权威材料"),
    Capability("walkthrough", "漫游与多视角表现", (S5,), legacy="13-walkthrough",
               responsibility="全景、动画漫游、空间序列表达"),

    # --- 06 设计定稿与技术协调 -------------------------------------------
    Capability("design-review", "设计审核", (S6, S7), legacy="17-compliance",
               responsibility="几何、配置、规范初审；列出待专业复核项"),
    Capability("coordination-check", "专业协调校核", (S6, S7),
               responsibility="结构、机电、吊顶净高、点位与做法的冲突检查"),
    Capability("cost-check", "造价适配", (S1, S2, S3, S4, S5, S6),
               responsibility="从前期开始动态估算，随深化收敛，锁定前完成预算适配"),

    # --- 07 施工图深化 ---------------------------------------------------
    Capability("bim-modeling", "BIM 建模", (S5, S7), legacy="10-bim",
               responsibility="参数化构件、IFC、信息模型与专业协同"),
    Capability("construction-detailing", "施工深化与节点", (S7,),
               responsibility="平立剖、吊顶、铺装、节点详图、尺寸与图层标准"),

    # --- 08 物料清单与交付 -----------------------------------------------
    Capability("quantity-takeoff", "工程量计算", (S1, S2, S3, S4, S5, S6, S7, S8),
               legacy="16-quantities",
               responsibility="工程量随阶段滚动更新，最终形成正式清单"),
    Capability("material-schedule", "材料与物料表", (S8,),
               responsibility="材料规格、品牌档位、用量、损耗与替代方案"),
    Capability("documentation", "交付文档", (S8,),
               responsibility="设计文本、说明书、技术交底文件的版式与归档"),
    Capability("delivery", "版本管理与交付", (S8,), legacy="18-revisions",
               responsibility="变更追踪、跨图纸同步、交付核对与版本冻结"),
    Capability("design-presentation", "设计汇报与提案", (S2, S3, S4, S5, S6, S7, S8),
               legacy="design-presentation",
               responsibility="跨阶段通用：把该阶段成果转译为可决策的提案与可编辑 PPTX；"
                              "每份汇报必须含免责与边界页"),
]

CAPABILITY_BY_SLUG: Dict[str, Capability] = {c.slug: c for c in CAPABILITIES}


# --------------------------------------------------------------------------
# the eight stages
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StageGate:
    id: str
    label: str
    requires: str
    approver: str = "业主 / 主创"

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "label": self.label, "requires": self.requires,
                "approver": self.approver}


@dataclass(frozen=True)
class Stage:
    code: str
    id: str
    name: str
    purpose: str
    skills: tuple
    deliverables: tuple
    entry_criteria: tuple
    exit_criteria: tuple
    gate: StageGate
    drawing_depth: str = ""     # "" | "schematic" | "construction"
    modeling_allowed: bool = False
    cost_estimate: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "code": self.code,
            "id": self.id,
            "name": self.name,
            "purpose": self.purpose,
            "skills": list(self.skills),
            "deliverables": list(self.deliverables),
            "entry_criteria": list(self.entry_criteria),
            "exit_criteria": list(self.exit_criteria),
            "gate": self.gate.to_dict(),
            "drawing_depth": self.drawing_depth,
            "modeling_allowed": self.modeling_allowed,
            "cost_estimate": self.cost_estimate,
        }


STAGES: List[Stage] = [
    Stage(
        code="01", id=S1, name="项目启动与设计任务书",
        purpose="把业主需求、场地条件、原始图纸与预算固化成可验收的任务书。",
        skills=("design-brief", "site-analysis", "existing-drawing-analysis",
                "architectural-design", "cost-check", "quantity-takeoff"),
        deliverables=("设计任务书", "使用行为矩阵", "项目与建筑条件报告",
                      "资料登记与待核实清单", "可行性分析", "核心设计问题与机会",
                      "G1 确认摘要"),
        entry_criteria=(
            "业主提出项目想法、初步需求或已上传资料即可启动（不必先集齐全部资料）",
            "资料完整度决定本轮可产出的精度：缺尺寸不出依赖尺寸的权威成果，"
            "缺结构不批准结构改造",
        ),
        exit_criteria=("功能任务书与面积指标确认", "不确定性信息已列明并标记待现场核对",
                       "预算口径与设计标准达成一致",
                       "已注明本轮可支撑的最大深度"),
        gate=StageGate("G1", "任务书确认",
                       "功能需求、面积指标、预算口径必须由业主确认后才能进入概念设计；"
                       "确认即形成任务书基准，后续修改须走变更影响分析"),
        cost_estimate=True,
    ),
    Stage(
        code="02", id=S2, name="概念方案设计",
        purpose="定方向：设计立场、空间原型与风格语言，可被记住且能在平面上成立。",
        skills=("concept-design", "moodboard-aesthetic-iteration", "create-draw",
                "lighting-design", "cost-check", "quantity-takeoff"),
        deliverables=("概念方案（2–3 套方向，空间策略不同）", "概念图解（分区 / 动线 / 采光 / 序列）",
                      "风格意向板（含材料与色调倾向）", "方案比较与总设计师推荐",
                      "可编辑概念提案", "S3 概念交接"),
        entry_criteria=("任务书已确认（G1 基准）",),
        exit_criteria=("每套方向都有可追溯的证据与机会引用",
                       "选定概念的空间策略、风格与材料已由业主确认（G2 基准）",
                       "概念交接文件已生成，S3 可据此校核"),
        gate=StageGate("G2", "概念方案确认",
                       "概念方向与意向板确认后才能进入精细平面与深化"),
        cost_estimate=True,
    ),
    Stage(
        code="03", id=S3, name="平面方案设计",
        purpose="把概念落到尺度上：分区、功能、动线、家具与面积配比。",
        skills=("space-planning", "layout-optimization", "ergonomics",
                "concept-design", "concept-visualization",
                "cost-check", "quantity-takeoff"),
        deliverables=("两至三套平面方案", "方案对比分析（面积、动线、造价影响）",
                      "业主选定后的概念效果图（门禁通过后立即生成）"),
        entry_criteria=("任务书已确认", "概念方向已确认或与平面同步迭代"),
        exit_criteria=("布局在统一空间模型中以真实尺寸成立", "人体工学与净宽校核通过",
                       "业主选定其中一套"),
        gate=StageGate("G3", "平面方案确认",
                       "平面未确认前不得进行精细建模与正式出图——这是最常被跳过、也最贵的一步；"
                       "确认后立即以该平面为依据生成概念效果图，供业主建立空间感受"),
        drawing_depth="schematic",
        cost_estimate=True,
    ),
    Stage(
        code="04", id=S4, name="初步设计与方案深化",
        purpose="把平面发展成可施工的做法：顶墙地、立面、材料与灯光初步。",
        skills=("interior-design", "material-design", "lighting-design",
                "building-services", "ergonomics", "create-draw", "cad-drafting",
                "concept-visualization", "cost-check", "quantity-takeoff"),
        deliverables=("初步设计图纸（方案深度 CAD / 简单 3D 辅助）", "材料及灯光方案"),
        entry_criteria=("平面方案已确认",),
        exit_criteria=("顶面、墙面、地面做法定案", "材料与色彩体系成立",
                       "机电点位与净高初步协调完成", "造价仍在预算区间内"),
        gate=StageGate("G4", "初步设计确认",
                       "做法、材料与机电协调确认后才能进入正式表现与定稿"),
        drawing_depth="schematic",
        cost_estimate=True,
    ),
    Stage(
        code="05", id=S5, name="3D 建模与效果图表现",
        purpose="在已确认的几何上做真实的表现，而不是用效果图代替设计。",
        skills=("3d-modeling", "scene-rendering", "ai-visualization", "walkthrough",
                "material-design", "moodboard-aesthetic-iteration",
                "bim-modeling", "cost-check", "quantity-takeoff"),
        deliverables=("3D 模型（可编辑）", "空间效果图（多视角一致）", "漫游 / 全景"),
        entry_criteria=("平面方案已确认", "初步设计已确认或已锁定主要做法"),
        exit_criteria=("模型由统一空间模型生成，尺寸可追溯", "多视角材质与光影一致",
                       "AI 表现类成果已标注为非尺寸依据"),
        gate=StageGate("G5", "表现成果确认",
                       "效果图与漫游确认后才能进入定稿"),
        cost_estimate=True,
    ),
    Stage(
        code="06", id=S6, name="设计定稿与技术协调",
        purpose="把方案锁死：审定、结构与机电协调、预算适配，形成深化依据。",
        skills=("design-review", "coordination-check", "cost-check",
                "interior-design", "layout-optimization", "design-brief",
                "building-services", "quantity-takeoff"),
        deliverables=("确认版设计方案", "深化依据（锁定版本 + 待办清单）"),
        entry_criteria=("平面与初步设计已确认", "表现成果已确认"),
        exit_criteria=("全部专业冲突已闭环或明确转交", "造价通过预算适配",
                       "设计版本冻结并记录变更基线"),
        gate=StageGate("G6", "设计锁定",
                       "锁定后任何修改都走变更影响分析，不再局部手改"),
        cost_estimate=True,
    ),
    Stage(
        code="07", id=S7, name="CAD / BIM 施工图深化",
        purpose="出可施工的正式图纸与模型：平立剖、吊顶、铺装、节点与尺寸。",
        skills=("cad-drafting", "bim-modeling", "construction-detailing",
                "lighting-design", "building-services", "design-review",
                "coordination-check", "create-draw", "quantity-takeoff"),
        deliverables=("施工图文件（正式深度）", "BIM 模型 / IFC", "审查记录"),
        entry_criteria=("设计已锁定（S6 已确认）",),
        exit_criteria=("图纸间尺寸一致", "节点详图可施工", "专业冲突已协调",
                       "待持证专业人员复核项已列明"),
        gate=StageGate("G7", "施工图审查",
                       "结构、消防、机电与法规符合性须持证专业人员复核签署",
                       approver="持证专业负责人"),
        drawing_depth="construction",
        cost_estimate=True,
    ),
    Stage(
        code="08", id=S8, name="物料清单与交付",
        purpose="把设计变成可采购、可施工、可验收的完整交付包。",
        skills=("quantity-takeoff", "material-schedule", "documentation",
                "delivery", "material-design"),
        deliverables=("材料表 / 物料清单", "工程量清单与成本", "全套交付文件与技术交底"),
        entry_criteria=("施工图已审查",),
        exit_criteria=("工程量与图纸一致", "材料表含规格、用量与替代方案",
                       "交付包版本化并完成核对"),
        gate=StageGate("G8", "交付验收",
                       "交付内容与版本核对完成，业主签收"),
        drawing_depth="construction",
        cost_estimate=True,
    ),
]

STAGE_BY_ID: Dict[str, Stage] = {s.id: s for s in STAGES}
STAGE_ORDER: List[str] = [s.id for s in STAGES]


# --------------------------------------------------------------------------
# dependency and rework graph
# --------------------------------------------------------------------------
# Which stages must already be *confirmed* before a stage may start.
# S2/S3 is deliberately not a strict chain: concept and layout iterate together,
# but nothing downstream may start on an unconfirmed plan.
REQUIRES_CONFIRMED: Dict[str, List[str]] = {
    S1: [],
    S2: [S1],
    S3: [S1],
    S4: [S3],
    S5: [S3],          # S4 recommended, not mandatory: 简单 3D 可在初步设计辅佐
    S6: [S4, S5],
    S7: [S6],
    S8: [S7],
}

# Which stages must be re-run when a change lands in a given stage.
# A change re-flows forward from where it lands, never backward and never sideways
# onto already-confirmed work that the change does not touch.
DOWNSTREAM: Dict[str, List[str]] = {
    S1: [S1, S2, S3, S4, S5, S6, S7, S8],
    S2: [S2, S3, S4, S5, S6, S7, S8],
    S3: [S3, S4, S5, S6, S7, S8],
    S4: [S4, S5, S6, S7, S8],
    S5: [S5, S6, S8],
    S6: [S6, S7, S8],
    S7: [S7, S8],
    S8: [S8],
}

# --------------------------------------------------------------------------
# post-gate actions
# --------------------------------------------------------------------------
# Some work only becomes *meaningful* once a gate has passed. The client-facing
# concept rendering is the clear case: producing it before the plan is approved
# would picture a plan that may still change, which is exactly what the G3 rule
# exists to prevent. So it is attached to G3 rather than to a stage body.
#
# These are not stages: they do not have their own gate, they cannot be
# "confirmed", and a change landing upstream re-runs them through DOWNSTREAM.
POST_GATE_ACTIONS: Dict[str, List[str]] = {
    "G3": ["concept-visualization"],
}

POST_GATE_NOTES: Dict[str, str] = {
    "concept-visualization":
        "平面确认后立即以该平面为依据生成概念效果图（OmniAiLab 画布，"
        "推荐 OmniP / image2.5），供业主建立空间感受；属表现材料，非尺寸依据。",
}

# Hard guardrails derived from the three professional logics.
GUARDRAILS: List[Dict[str, str]] = [
    {
        "id": "R1",
        "rule": "业主确认功能需求之前，不得开始精细建模",
        "enforced": "S5 要求 S1 已确认；未确认时 run_stage 直接阻断",
    },
    {
        "id": "R2",
        "rule": "CAD 图纸不是最后才画：方案深度图纸自 S4 起即可绘制，"
                "区别在于 schematic 与 construction 两个深度，而不是有无",
        "enforced": "Stage.drawing_depth + cad-drafting 技能跨 S4/S7",
    },
    {
        "id": "R3",
        "rule": "物料与成本估算从前期开始动态进行，设计深化完成后才形成正式清单",
        "enforced": "cost-check / quantity-takeoff 覆盖 S1–S8，估算随阶段收敛",
    },
    {
        "id": "R4",
        "rule": "平面未确认前不得出正式图纸；锁定后不得局部手改，须走变更影响分析",
        "enforced": "G3 门禁 + changes.analyse() 强制失效重算",
    },
    {
        "id": "R5",
        "rule": "概念效果图只能在业主确认的平面上生成：平面一变，已出的概念效果图立即失效并重出",
        "enforced": "POST_GATE_ACTIONS['G3'] 挂载该动作；每张图登记到产生它的模型修订",
    },
]


def post_gate_actions(gate_id: str) -> List[str]:
    """Capabilities that must run once a gate has passed."""
    return list(POST_GATE_ACTIONS.get(gate_id, []))


def post_gate_actions_for_stage(stage_id: str) -> List[str]:
    st = STAGE_BY_ID.get(stage_id)
    return post_gate_actions(st.gate.id) if st else []


def stage_of(skill_slug: str) -> List[str]:
    cap = CAPABILITY_BY_SLUG.get(skill_slug)
    return list(cap.stages) if cap else []


def skills_for_stage(stage_id: str) -> List[str]:
    st = STAGE_BY_ID.get(stage_id)
    return list(st.skills) if st else []


def stages_for_skill(skill_slug: str) -> List[str]:
    return stage_of(skill_slug)


def stage_name(stage_id: str) -> str:
    st = STAGE_BY_ID.get(stage_id)
    return f"{st.code} {st.name}" if st else stage_id


def capabilities_for_stage(stage_id: str) -> List[Capability]:
    return [
        c for s in skills_for_stage(stage_id)
        for c in [CAPABILITY_BY_SLUG.get(s)] if c is not None
    ]


def legacy_map() -> Dict[str, List[str]]:
    """Original specialist brief -> the stages it now serves."""
    out: Dict[str, List[str]] = {}
    for c in CAPABILITIES:
        if c.legacy:
            out.setdefault(c.legacy, [])
            for s in c.stages:
                if s not in out[c.legacy]:
                    out[c.legacy].append(s)
    return out


def catalog_report() -> Dict[str, object]:
    return {
        "stages": [s.to_dict() for s in STAGES],
        "capabilities": [c.to_dict() for c in CAPABILITIES],
        "capability_count": len(CAPABILITIES),
        "legacy_coverage": legacy_map(),
        "requires_confirmed": REQUIRES_CONFIRMED,
        "downstream": DOWNSTREAM,
        "post_gate_actions": {k: list(v) for k, v in POST_GATE_ACTIONS.items()},
        "guardrails": GUARDRAILS,
    }


def validate_catalog() -> List[str]:
    """Structural self-check — a broken catalogue must fail loudly at import time."""
    issues: List[str] = []
    seen: set[str] = set()
    for c in CAPABILITIES:
        if c.slug in seen:
            issues.append(f"duplicate capability slug '{c.slug}'")
        seen.add(c.slug)
        if not c.stages:
            issues.append(f"capability '{c.slug}' is not mapped to any stage")
        for s in c.stages:
            if s not in STAGE_BY_ID:
                issues.append(f"capability '{c.slug}' references unknown stage '{s}'")
    for st in STAGES:
        for slug in st.skills:
            if slug not in CAPABILITY_BY_SLUG:
                issues.append(f"stage {st.id} references unknown capability '{slug}'")
            elif st.id not in CAPABILITY_BY_SLUG[slug].stages:
                issues.append(
                    f"stage {st.id} lists '{slug}' but the capability does not declare it "
                    f"(declared: {list(CAPABILITY_BY_SLUG[slug].stages)})"
                )
        if not st.gate.id:
            issues.append(f"stage {st.id} has no gate")
    for s, reqs in REQUIRES_CONFIRMED.items():
        for r in reqs:
            if r not in STAGE_BY_ID:
                issues.append(f"REQUIRES_CONFIRMED[{s}] references unknown stage '{r}'")
    for s, downs in DOWNSTREAM.items():
        for d in downs:
            if d not in STAGE_BY_ID:
                issues.append(f"DOWNSTREAM[{s}] references unknown stage '{d}'")
    known_gates = {st.gate.id for st in STAGES}
    for gate_id, actions in POST_GATE_ACTIONS.items():
        if gate_id not in known_gates:
            issues.append(f"POST_GATE_ACTIONS references unknown gate '{gate_id}'")
        for slug in actions:
            if slug not in CAPABILITY_BY_SLUG:
                issues.append(
                    f"post-gate action '{slug}' on {gate_id} is not a known capability"
                )
    return issues
