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
from datetime import datetime
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
    DomainRule(
        "roof_envelope", "屋面与外立面", "S4", False,
        ("屋顶花园", "屋顶绿化", "屋面", "屋顶", "露台", "女儿墙", "泛水",
         "屋面防水", "外立面", "幕墙", "roof", "facade", "parapet"),
        "改动落在建筑围护：屋面或立面的构造、防水与开口变了，室内平面通常不变",
        "先定围护构造与泛水，再核结构荷载与机电出口，最后才谈做法与观感",
    ),
    DomainRule(
        "landscape_scope", "景观与场地", "S3", True,
        ("庭院", "花园", "园林", "景观", "铺装", "种植", "植栽", "苗木",
         "水景", "泳池", "水池", "园路", "绿化", "草坪", "室外",
         "landscape", "garden", "paving", "planting"),
        "改动落在室外：竖向、排水与种植是几何问题，不是铺个面就完",
        "先定竖向与排水，再定铺装与种植；涉及水体时同步结构与防水",
    ),
    DomainRule(
        "site_planning", "用地与总图", "S2", True,
        ("用地", "退线", "容积率", "限高", "建筑位置", "总图", "场地",
         "出入口", "红线", "绿地率", "setback", "floor area ratio"),
        "改动落在地上：用地指标与总图关系变了，建筑体量与基础条件都要重算",
        "先核规划指标与退线，再动总图与体量；禁止在指标未清时承诺可报",
    ),
    DomainRule(
        "structure_scope", "结构改造", "S3", True,
        ("加固", "承重", "加层", "加建", "夹层", "楼板", "荷载", "柱网",
         "基础", "抗震", "碳纤维", "粘钢", "reinforce", "structural"),
        "改动落在结构：受力路径变了，必须先是鉴定、再是方案",
        "先出鉴定与可行性，再谈加固做法；无鉴定不强推方案",
    ),
]

DOMAIN_BY_ID = {r.id: r for r in DOMAIN_RULES}


# --------------------------------------------------------------------------
# 跨专业变更：一次改动同时落在多个专业上
#
# DOMAIN_RULES 决定"这件事主要落在哪个阶段"，但真实改动很少只落一处。
# "屋顶改成花园"不是换材料——它同时动到建筑屋面、结构附加荷载、防水排水、
# 景观分区和造价。只把它归类成"改材料"是这一层最容易犯、后果最贵的错。
#
# 这些规则不替代领域判定，只在其上补一份"还牵动了谁"。
CROSS_DISCIPLINE_RULES: List[Dict[str, Any]] = [
    {
        "id": "XD-ROOF-GARDEN",
        "triggers": ("屋顶花园", "屋顶绿化", "屋面改成花园", "露台改花园",
                     "屋顶改", "roof garden", "green roof"),
        "not_just": "改材料",
        "why": "屋顶从不可上人变成可上人带种植：多了一层活荷载、一套防水与排水、"
               "一套灌溉与照明，还要能上人到达。",
        "affects": [
            {"discipline": "architecture", "aspect": "屋面构造与泛水、上人通道与栏杆",
             "needs": "屋面防水等级、泛水高度、女儿墙高度与可上人开口",
             "blocks_stage": "S3"},
            {"discipline": "structure", "aspect": "附加荷载（种植土、水体、人群）",
             "needs": "屋面允许附加荷载与原结构复核结论",
             "blocks_stage": "S3"},
            {"discipline": "landscape", "aspect": "种植分区、园路、排水找坡",
             "needs": "种植土厚度与植物选型、排水坡度与溢流口",
             "blocks_stage": "S3"},
            {"discipline": "mep", "aspect": "灌溉水源与水压、景观照明配电、检修口",
             "needs": "灌溉方式、室外配电回路、给水接驳点",
             "blocks_stage": "S4"},
        ],
        "extra_risks": ["覆土后净高与排水坡向冲突", "检修口被种植区覆盖导致无法维护"],
    },
    {
        "id": "XD-POOL",
        "triggers": ("泳池", "水池", "水景", "鱼池", "spa", "pool", "water feature"),
        "not_just": "加一个装饰",
        "why": "水体是结构荷载 + 防水 + 循环设备 + 电气安全的组合，且一旦渗漏"
               "修复代价极高。",
        "affects": [
            {"discipline": "structure", "aspect": "水体与池壁荷载、下沉或架空做法",
             "needs": "水深、池壁材料、基底是楼板还是地坪",
             "blocks_stage": "S3"},
            {"discipline": "architecture", "aspect": "防水构造、池边收口、溢流与补水",
             "needs": "防水做法与蓄水试验要求",
             "blocks_stage": "S3"},
            {"discipline": "mep", "aspect": "循环过滤设备、补水与排水、水下照明电气安全",
             "needs": "循环方式、设备位置与噪音、等电位做法",
             "blocks_stage": "S3"},
        ],
        "extra_risks": ["水下灯具未做等电位与安全电压", "溢流无去处导致倒灌"],
    },
    {
        "id": "XD-BUILDING-MOVE",
        "triggers": ("建筑位置", "楼往", "整体移", "退线变", "挪动建筑", "后退",
                     "往后退", "移位", "挪两米", "挪动",
                     "building position", "setback", "move the building"),
        "not_just": "微调",
        "why": "建筑一动，用地指标、基础条件、室外管线与场地排水全部重算。",
        "affects": [
            {"discipline": "planning", "aspect": "退线、容积率、日照与绿地率",
             "needs": "用地红线、退线要求、当地规划条件来源",
             "blocks_stage": "S2"},
            {"discipline": "architecture", "aspect": "总平面、出入口与场地关系",
             "needs": "场地标高与周边道路",
             "blocks_stage": "S3"},
            {"discipline": "structure", "aspect": "基础形式与持力层条件",
             "needs": "地勘报告或基础现状",
             "blocks_stage": "S3"},
            {"discipline": "landscape", "aspect": "场地竖向、排水去向与园路",
             "needs": "场地排水出口与市政接驳",
             "blocks_stage": "S3"},
        ],
        "extra_risks": ["退线变化可能导致方案不可报", "场地排水出口改变后需重做竖向"],
    },
    {
        "id": "XD-ADD-FLOOR",
        "triggers": ("加一层", "加建", "加盖", "增加层数", "加夹层", "跃层",
                     "add a floor", "mezzanine"),
        "not_just": "加房间",
        "why": "新增楼层改变荷载路径、竖向交通、消防疏散与规划指标。",
        "affects": [
            {"discipline": "structure", "aspect": "新增荷载路径与基础承载",
             "needs": "原基础形式、持力层、能否加桩",
             "blocks_stage": "S3"},
            {"discipline": "planning", "aspect": "容积率、限高、消防高度分类",
             "needs": "限高与容积率指标",
             "blocks_stage": "S2"},
            {"discipline": "architecture", "aspect": "竖向交通与疏散距离",
             "needs": "楼梯位置、疏散宽度与距离",
             "blocks_stage": "S3"},
            {"discipline": "mep", "aspect": "竖向管井延伸、消防系统容量",
             "needs": "原有立管与消防容量余量",
             "blocks_stage": "S4"},
        ],
        "extra_risks": ["加层后建筑高度分类变化，消防要求整体提高"],
    },
    {
        "id": "XD-FACADE-OPENING",
        "triggers": ("开窗", "加窗", "落地窗", "幕墙", "开洞", "扩窗",
                     "facade", "curtain wall", "window opening"),
        "not_just": "换个立面样式",
        "why": "立面开口同时是结构开洞、防水节点、设备进排风与遮阳能耗问题。",
        "affects": [
            {"discipline": "structure", "aspect": "开洞对梁柱与墙体承载的影响",
             "needs": "洞口尺寸位置与结构构件关系",
             "blocks_stage": "S3"},
            {"discipline": "architecture", "aspect": "防水节点、窗台泛水、遮阳",
             "needs": "洞口周边构造做法",
             "blocks_stage": "S4"},
            {"discipline": "mep", "aspect": "设备进排风面积、外机位置",
             "needs": "需通风的设备清单与风量",
             "blocks_stage": "S4"},
        ],
        "extra_risks": ["大面积玻璃导致夏季过热与结露", "开洞切断原有防水层"],
    },
    {
        "id": "XD-STRUCT-REINFORCE",
        "triggers": ("加固", "碳纤维", "粘钢", "承重不够", "楼板开裂", "结构改造",
                     "reinforce", "strengthen"),
        "not_just": "做点修补",
        "why": "结构加固必须先有鉴定结论，否则是在没有依据的前提下施工。",
        "affects": [
            {"discipline": "structure", "aspect": "鉴定结论、加固方案与施工可行性",
             "needs": "结构检测鉴定报告",
             "blocks_stage": "S3"},
            {"discipline": "architecture", "aspect": "加固后的净高与空间可用性",
             "needs": "加固厚度与占用空间",
             "blocks_stage": "S4"},
        ],
        "extra_risks": ["无鉴定直接加固属于无依据施工", "加固占用净高影响使用"],
    },
]

CROSS_BY_ID = {r["id"]: r for r in CROSS_DISCIPLINE_RULES}

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
    cross_discipline: List[Dict[str, Any]] = field(default_factory=list)
    intent: Dict[str, Any] = field(default_factory=dict)
    authorization: Dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    blocked_reason: str = ""
    changelog: str = ""
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
            "cross_discipline": self.cross_discipline,
            "design_intent": self.intent,
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
        if self.cross_discipline:
            lines += ["", "### 跨专业影响（这不只是一处改动）", ""]
            for x in self.cross_discipline:
                lines.append(f"**{x['id']}** — 不是「{x['not_just']}」：{x['why']}")
                lines.append("")
                lines.append("| 专业 | 受影响的内容 | 需要什么才能定 | 影响阶段 |")
                lines.append("|---|---|---|---|")
                for a in x["affects"]:
                    lines.append(f"| {_disc_label(a['discipline'])} | {a['aspect']} | "
                                 f"{a['needs']} | {a['blocks_stage']} |")
                lines.append("")
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
        if self.intent and self.intent.get("has_intent"):
            lines += ["", "## 设计意图影响", "",
                      f"- 设计意图基准：`{self.intent.get('design_intent_id', '')}`"
                      f"（主导：{self.intent.get('lead_label', '')}）"]
            if self.intent.get("requires_formal"):
                lines.append(f"- **{self.intent['headline']}**")
                for f in self.intent.get("touched") or []:
                    lines.append(f"  - {f['name']}（{f['basis']}）")
                levels = self.intent.get("levels") or []
                if levels:
                    lines += ["", "| 级 | 处理步骤 | 说明 |", "|---|---|---|"]
                    for lv in levels:
                        note = lv.get("rule") or lv.get("action") or ""
                        if lv.get("options"):
                            note = "可选路径：" + "；".join(
                                o["path"] for o in lv["options"][:3])
                        lines.append(f"| {lv['level']} | {lv['name']} | {note} |")
            else:
                lines.append("- 未触及核心设计特征，可按常规变更处理。")
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


def _disc_label(did: str) -> str:
    from .disciplines import DISCIPLINES

    d = DISCIPLINES.get(did)
    return d.label if d else did


def _intent_impact(project: Project, text: str) -> Dict[str, Any]:
    """改动是否动了已确认的设计意图。

    G2 之前没有意图基准——那时谈不上"保护"，只能做一般影响分析。
    G2 之后动了受保护特征，就必须走正式说明：先找保留意图的技术路径，
    再谈改设计。
    """
    from . import intent as _intent

    check = _intent.protect_check(project, text)
    if not check.get("has_intent"):
        return {"has_intent": False, "requires_formal": False,
                "note": check.get("note", ""), "touched": []}

    resolved = _intent.resolve(project, text)
    touched = check.get("touched") or []
    names = "、".join(t["name"] for t in touched)
    # 是否走正式流程以 resolve 的结论为准：面层级调整属于"可接受调整"，
    # protect_check 只看"有没有碰到"，判不了"碰到之后要不要走完整流程"。
    requires_formal = bool(resolved.get("requires_formal", check.get("requires_formal")))
    verdict = str(resolved.get("verdict") or "")
    headline = (
        f"这条改动触及已确认的设计意图（{names}）：不能按普通变更处理——"
        "先由结构 / 机电给出保留原意图的技术路径，确不可行才提最小必要修改"
    ) if (touched and requires_formal) else (
        f"触及设计特征（{names}），但属于可接受调整范围："
        "只改面层做法，不改变空间关系与视觉特征"
    ) if touched else "未触及设计意图"
    return {
        "has_intent": True,
        "design_intent_id": check.get("design_intent_id", ""),
        "lead_label": check.get("lead_label", ""),
        "requires_formal": requires_formal,
        "touched": touched,
        "levels": resolved.get("levels") or [],
        "verdict": verdict,
        "headline": headline,
        "note": ("设计意图保护不否决技术判断：安全与规范不可突破；"
                 "在此前提下最大限度保留原设计。"),
    }


def cross_discipline_impacts(text: str) -> List[Dict[str, Any]]:
    """这次改动还牵动了哪些专业。

    领域判定只回答"主要落在哪个阶段"，回答不了"还动了谁"。这里补上：
    命中的规则会展开成逐专业的影响项，每项带"需要什么才能定"和影响阶段。
    """
    out: List[Dict[str, Any]] = []
    low = text.lower()
    for rule in CROSS_DISCIPLINE_RULES:
        hits = [t for t in rule["triggers"] if t.lower() in low]
        if not hits:
            continue
        out.append({
            "id": rule["id"],
            "triggered_by": hits,
            "not_just": rule["not_just"],
            "why": rule["why"],
            "affects": [dict(a) for a in rule["affects"]],
            "disciplines": sorted({a["discipline"] for a in rule["affects"]}),
            "extra_risks": list(rule["extra_risks"]),
        })
    return out


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


@dataclass
class ChangeRequest:
    """阶段 A 的产物：一份**没有执行**的变更提案。

    为什么要有这个东西
    ------------------
    "分析完就直接改"是本轮最危险的漏洞：识别出"触及核心设计意图"之后仍然继续
    改项目、让成果失效、重开门禁。等于自己提醒自己，然后自己无视。

    所以把"提出"和"执行"分成两件事：`propose()` 只出提案，改项目必须凭
    `authorize()` 返回的授权，而授权绑定版本、概念、意图与批准人。
    """

    request_id: str
    text: str
    revision: int
    concept_id: str = ""
    design_intent_id: str = ""
    intent_digest: str = ""
    requires_authorization: bool = False
    approval_scope: List[str] = field(default_factory=list)
    report: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "text": self.text,
            "project_revision": self.revision,
            "concept_id": self.concept_id,
            "design_intent_id": self.design_intent_id,
            "intent_digest": self.intent_digest,
            "requires_authorization": self.requires_authorization,
            "approval_scope": list(self.approval_scope),
            "created_at": self.created_at,
            "applied": False,
            "note": ("这是变更提案，不是执行记录。未经授权不得改动项目数据。"),
            "impact": self.report,
        }


#: 需要业主明确批准的范围标签
APPROVAL_INTENT = "design_intent"
APPROVAL_SCOPE_CHANGE = "scope_change"
APPROVAL_HARD_BLOCK = "hard_gate"


def _intent_digest(project: Project) -> str:
    from . import intent as _intent

    data = _intent.load(project) or {}
    if not data:
        return ""
    seed = "|".join([str(data.get("design_intent_id") or ""),
                     str(data.get("revision") or ""),
                     *[str(f.get("statement") or "")
                       for f in (data.get("signature_features") or [])]])
    import hashlib

    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def propose(project: Project, text: str,
            author: str = "omniailab-ai-architect") -> ChangeRequest:
    """阶段 A：只分析、只出报告，**不碰项目数据**。

    返回的提案里写明：改了什么、牵动哪些专业、是否触及已确认的设计意图、
    要谁批。调用方拿这份提案去找业主确认，再回到 `authorize_change()`。
    """
    rep = analyse(project, text, apply=False, author=author)
    intent_id = ""
    from . import intent as _intent

    data = _intent.load(project) or {}
    intent_id = str(data.get("design_intent_id") or "")
    concept_id = str(((project.meta or {}).get("concept") or {}).get("selected") or "")

    block = _hard_block_reason(project)
    scope: List[str] = []
    if rep.intent.get("requires_formal"):
        scope.append(APPROVAL_INTENT)
    if block:
        scope.append(APPROVAL_HARD_BLOCK)
    if rep.scope in ("level", "project"):
        scope.append(APPROVAL_SCOPE_CHANGE)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    req = ChangeRequest(
        request_id=f"CR-{stamp}-{abs(hash(text)) % 1000:03d}",
        text=text, revision=int(project.revision),
        concept_id=concept_id, design_intent_id=intent_id,
        intent_digest=_intent_digest(project),
        requires_authorization=bool(scope),
        approval_scope=scope, report=rep.to_dict(),
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    if block:
        rep.risks.append(block)
        req.report.setdefault("hard_gate", {})["reason"] = block
    return req


def authorize_change(req: ChangeRequest, *, by: str, note: str = "",
                     scope: Sequence[str] = (), source: str = "owner") -> Dict[str, Any]:
    """阶段 B 的第一半：业主批准。只认真实业主，不认演示与脚本。

    `--force`、`apply=True`、脚本代理、演示批准都不在这条路径上——它们连
    调用这个函数的机会都没有，因为执行需要这里返回的授权指纹。
    """
    if source != "owner":
        raise PermissionError(
            f"变更授权只接受真实业主确认（source=owner），收到 {source!r}。"
            "演示模式、脚本代理与 --force 都不能批准设计意图变更。")
    if not by or not str(by).strip():
        raise PermissionError("变更授权必须记录批准人：没有名字的批准等于没有批准")
    want = set(scope or req.approval_scope)
    missing = set(req.approval_scope) - want
    if missing:
        raise PermissionError(
            "以下范围未获批准，不能执行：" + "、".join(sorted(missing)) +
            "（可以只批准部分范围，但未批准的部分不得改动）")
    payload = {
        "request_id": req.request_id,
        "by": str(by).strip(),
        "note": note,
        "approved_scope": sorted(want),
        "source": source,
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "project_revision": req.revision,
        "concept_id": req.concept_id,
        "design_intent_id": req.design_intent_id,
        "intent_digest": req.intent_digest,
    }
    payload["fingerprint"] = _fingerprint(payload)
    return payload


def _fingerprint(auth: Dict[str, Any]) -> str:
    import hashlib

    seed = "|".join(str(auth.get(k) or "") for k in
                    ("request_id", "by", "at", "project_revision",
                     "concept_id", "design_intent_id", "intent_digest")) + \
        "|" + ",".join(auth.get("approved_scope") or [])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]


def validate_authorization(project: Project, req: ChangeRequest,
                           auth: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
    """授权是否仍然有效。版本、概念、意图任一变化即失效。"""
    if not auth:
        return False, "没有授权记录"
    if req.requires_authorization and auth.get("source") != "owner":
        return False, f"授权来源不是业主（{auth.get('source')!r}）"
    if auth.get("fingerprint") != _fingerprint(auth):
        return False, "授权记录被改动过（指纹不符）"
    if auth.get("request_id") != req.request_id:
        return False, "授权对应的不是这份变更请求"
    if int(auth.get("project_revision") or -1) != int(project.revision):
        return False, (f"项目已从 r{auth.get('project_revision')} 走到 "
                       f"r{project.revision}：授权针对的是旧版本，需重新确认")
    if str(auth.get("design_intent_id") or "") != _intent_id_now(project):
        return False, "设计意图基准已变化：原授权不适用"
    if str(auth.get("intent_digest") or "") != _intent_digest(project):
        return False, "设计意图内容已变化：原授权不适用"
    return True, ""


def _intent_id_now(project: Project) -> str:
    from . import intent as _intent

    return str((_intent.load(project) or {}).get("design_intent_id") or "")


def _hard_block_reason(project: Project) -> str:
    """硬门槛已证明不成立时，变更也不能在没有书面接受的情况下执行。"""
    try:
        from . import hardgate

        v = hardgate.evaluate(project)
        if v.failed:
            return ("硬门槛已判定不成立，变更不能绕过：" + "；".join(
                r.statement for r in v.failed))
    except Exception:                                   # noqa: BLE001
        return ""
    return ""


def apply_change(project: Project, req: ChangeRequest, *,
                 authorization: Optional[Dict[str, Any]] = None,
                 author: str = "omniailab-ai-architect") -> ChangeImpactReport:
    """阶段 B 的第二半：凭授权执行。没有有效授权就拒绝，什么都不改。"""
    ok, why = validate_authorization(project, req, authorization)
    if req.requires_authorization and not ok:
        rep = _report_from(req)
        rep.notes.append(f"未执行：{why}")
        rep.notes.append("变更已作为提案保留；取得业主确认后重新提交执行。")
        rep.blocked = True
        rep.blocked_reason = why
        return rep

    # 重新分析一次（项目可能已变化），再执行
    rep = analyse(project, req.text, apply=False, author=author)
    rep.authorization = dict(authorization or {})
    _execute(project, rep, req.text, author=author)
    rep.changelog = f"changes/change-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    return rep


def _report_from(req: ChangeRequest) -> ChangeImpactReport:
    raw = req.report or {}
    diag = diagnose(req.text)
    rep = ChangeImpactReport(request=req.text, diagnosis=diag,
                             scope=str(raw.get("scope") or "local"))
    rep.targets = list(raw.get("targets") or [])
    rep.affected_spaces = list((raw.get("affected") or {}).get("spaces") or [])
    rep.affected_elements = list((raw.get("affected") or {}).get("elements") or [])
    rep.affected_artifacts = list((raw.get("affected") or {}).get("artifacts") or [])
    rep.cross_discipline = list(raw.get("cross_discipline") or [])
    rep.intent = dict(raw.get("design_intent") or {})
    rep.risks = list(raw.get("risks") or [])
    return rep


def _execute(project: Project, rep: ChangeImpactReport, text: str,
             author: str = "omniailab-ai-architect") -> None:
    seeds = list(dict.fromkeys([*rep.affected_spaces, *rep.affected_elements,
                                *rep.targets]))
    diag = rep.diagnosis
    elements = rep.affected_elements
    if diag.geometry_affecting and elements:
        wall = next((e for e in elements if e.startswith(("W",))), None)
        if wall:
            try:
                rep.invalidation = apply_geometry_change(
                    project, wall, {}, author=author, detail=f"变更触发：{text}")
            except ModelError:
                rep.invalidation = _soft_invalidate(project, seeds, text, author)
        else:
            rep.invalidation = _soft_invalidate(project, seeds, text, author)
    else:
        rep.invalidation = _soft_invalidate(project, seeds, text, author)
    _reopen_gates(project, rework_stages(project, diag, rep.scope))
    rep.applied = True


def analyse(
    project: Project,
    text: str,
    apply: bool = True,
    author: str = "omniailab-ai-architect",
    authorization: Optional[Dict[str, Any]] = None,
) -> ChangeImpactReport:
    diag = diagnose(text)
    targets, spaces, elements, scope = locate(project, text, diag)
    rep = ChangeImpactReport(request=text, diagnosis=diag, scope=scope,
                             targets=targets, affected_spaces=spaces,
                             affected_elements=elements)

    # ---- 跨专业：这次改动还牵动了谁 -------------------------------------
    rep.cross_discipline = cross_discipline_impacts(text)

    # ---- 设计意图：动了受保护特征就不能按普通变更走 ---------------------
    rep.intent = _intent_impact(project, text)
    if rep.intent.get("requires_formal"):
        rep.risks.append(rep.intent["headline"])
    if rep.cross_discipline:
        stages = [a["blocks_stage"] for x in rep.cross_discipline
                  for a in x["affects"]]
        earliest = min(stages) if stages else diag.landing_stage
        if diag.primary == "visual_only" and not diag.matched:
            # 关键词没命中领域、只落到兜底的"仅表现"时，跨专业规则知道的更多：
            # 用它们给出的最早影响阶段纠正落点，而不是把屋面改造当成重出图。
            labels = sorted({_disc_label(a["discipline"])
                             for x in rep.cross_discipline for a in x["affects"]})
            rep.diagnosis = Diagnosis(
                primary="cross_discipline", label="跨专业改动",
                landing_stage=earliest,
                geometry_affecting=diag.geometry_affecting,
                confidence=0.55, matched=[], considered=[],
                explanation=("未命中单专业关键词，但识别出多处牵连（"
                             + "、".join(labels) + "）："
                             + "；".join(x["why"] for x in rep.cross_discipline)),
                typical_fix="按跨专业影响逐项核对，不要当成单一专业的局部改动",
            )
            diag = rep.diagnosis
        elif earliest < diag.landing_stage:
            # 领域判定说落在 S4，但跨专业规则指出 S3 就要定条件：
            # 取更早的那个——晚定等于返工。
            rep.diagnosis = Diagnosis(
                primary=diag.primary, label=diag.label,
                landing_stage=earliest, geometry_affecting=diag.geometry_affecting,
                confidence=diag.confidence, matched=diag.matched,
                considered=diag.considered,
                explanation=(diag.explanation +
                             f"；但跨专业规则指出 {earliest} 就要定条件，"
                             "按更早的阶段处理"),
                typical_fix=diag.typical_fix,
            )
            diag = rep.diagnosis
        # 跨专业改动不能按"局部"处理：它一定越过多个专业的边界。
        # 但也不能一概升成 project —— 屋顶花园不动平面坐标。
        if scope == "local":
            rep.scope = "room"
        for x in rep.cross_discipline:
            labels = "、".join(sorted({_disc_label(a["discipline"])
                                       for a in x["affects"]}))
            rep.risks.append(
                f"这不只是{x['not_just']}：牵动{labels}——{x['why']}")
            rep.risks += x["extra_risks"]

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
        # 触及已确认设计意图的变更必须凭授权执行。
        # 这一步是"自己提醒自己"和"真的改不了"之间的分界线：
        # 识别出 requires_formal 之后仍然照改，等于保护机制不存在。
        if rep.intent.get("requires_formal"):
            ok, why = validate_authorization(
                project,
                ChangeRequest(request_id="adhoc", text=text,
                              revision=int(project.revision),
                              design_intent_id=_intent_id_now(project),
                              intent_digest=_intent_digest(project),
                              requires_authorization=True,
                              approval_scope=[APPROVAL_INTENT]),
                authorization)
            if not ok:
                rep.applied = False
                rep.blocked = True
                rep.blocked_reason = why
                rep.notes.append(
                    "未执行：本次改动触及已确认的设计意图，需业主书面确认后才能执行")
                rep.notes.append(f"原因：{why}")
                rep.notes.append(
                    "正确路径：先 `changes.propose()` 出提案 → 业主确认 → "
                    "`changes.authorize_change()` 出授权 → 再执行")
                return rep
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
        rep.authorization = dict(authorization or {})

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
