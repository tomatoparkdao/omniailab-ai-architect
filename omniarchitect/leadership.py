"""设计主导权：先判断客户买的是什么设计，再决定谁说话算数。

为什么需要这一层
----------------
多专业不等于多专业平权。真实事务所里：

* 客户买的是"一栋房子" → 建筑师定形，结构和机电研究怎么把它实现；
* 客户买的是"一套已建成的房子怎么装" → 室内定调，结构机电只处理避不开的事；
* 客户买的是"一个院子" → 景观定意境，结构机电处理水与电。

如果系统对所有项目用同一套权重、同一套问诊、同一套概念组织方式，结果必然是
"以技术协调为中心、牺牲设计品质"——每个专业都提要求，最后谁都不负责美学。

设计主导 ≠ 专业免责
------------------
主导专业有**设计统筹权**，没有**安全豁免权**。三条不可突破：

1. 结构安全；
2. 消防与强制性规范；
3. 经核实的物理限制（荷载、净高、排水坡度等）。

在满足这三条的前提下，最大限度保留设计意图——这是本模块的全部主张。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# --------------------------------------------------------------------------
# 五种主导模式
#
# `design_disciplines` 是"能定美学"的专业；`support_disciplines` 是"研究怎么实现"；
# `coordination` 是"只处理接口"的。三类不是平级关系。
MODES: Dict[str, Dict[str, Any]] = {
    "A": {
        "id": "A",
        "key": "architecture_lead",
        "label": "建筑主导",
        "lead": "architecture",
        "design_disciplines": ("architecture", "interior", "landscape"),
        "support_disciplines": ("structure", "mep"),
        "coordination": ("planning",),
        "when": "新建或整体改造：建筑形态、体量、立面与内外空间关系都由本次委托决定",
        "lead_owns": ("总体规划", "建筑形态", "体量", "立面", "楼层关系",
                      "建筑与室外环境", "内外空间整体美学"),
        "must_not": "不得让结构或机电在概念阶段主导建筑形态",
    },
    "B": {
        "id": "B",
        "key": "interior_lead",
        "label": "室内主导",
        "lead": "interior",
        "design_disciplines": ("interior",),
        "support_disciplines": ("structure", "mep"),
        "coordination": ("architecture",),
        "when": "建筑已建成，客户只委托室内精装修",
        "lead_owns": ("空间体验", "功能布局", "顶墙地", "精装修造型",
                      "材料", "灯光", "固定家具", "整体氛围"),
        "must_not": "不得为迎合机电布置而改变已确认的室内美学方案；"
                    "不得强制重启完整建筑设计流程",
    },
    "C": {
        "id": "C",
        "key": "landscape_lead",
        "label": "景观主导",
        "lead": "landscape",
        "design_disciplines": ("landscape",),
        "support_disciplines": ("structure", "mep"),
        "coordination": ("architecture",),
        "when": "独立庭院、花园、室外景观或屋顶花园",
        "lead_owns": ("景观空间", "地形", "园路", "铺装", "植物", "水景",
                      "景观设施", "景观照明", "空间意境"),
        "must_not": "不得因水泵或管线布置方便就取消核心水景；"
                    "不得调用住宅房间组合算法",
    },
    "D": {
        "id": "D",
        "key": "architecture_integrated",
        "label": "建筑综合主导",
        "lead": "architecture",
        "design_disciplines": ("architecture", "interior", "landscape"),
        "support_disciplines": ("structure", "mep"),
        "coordination": ("planning",),
        "when": "建筑、室内、庭院与景观一次性整体设计",
        "lead_owns": ("建筑内外整体关系", "统一设计语言", "室内外过渡"),
        "must_not": "不得把室内与景观当作建筑的附属；它们是独立的设计创造力",
    },
    "E": {
        "id": "E",
        "key": "interior_landscape_joint",
        "label": "室内与景观联合主导",
        "lead": "interior",
        "joint_lead": "landscape",
        "design_disciplines": ("interior", "landscape"),
        "support_disciplines": ("structure", "mep"),
        "coordination": ("architecture",),
        "when": "建筑已建成，客户同时委托室内与景观改造",
        "lead_owns": ("整体设计语言（室内与景观共同确定）",),
        "must_not": "不得重启完整建筑设计；仅在改造涉及建筑本体时增加建筑协调",
    },
}

MODE_ORDER = ("A", "B", "C", "D", "E")

#: 不可突破的三条。任何主导模式都不能覆盖。
HARD_CONSTRAINTS: Sequence[Dict[str, str]] = (
    {"id": "HC-SAFETY", "text": "结构安全：承重、抗震、荷载必须由专业计算确认",
     "cannot_be_traded": "美学"},
    {"id": "HC-FIRE", "text": "消防与强制性规范：疏散、防火分区、耐火等级须合规",
     "cannot_be_traded": "美学"},
    {"id": "HC-PHYSICS", "text": "经核实的物理限制：净高、坡度、排水、检修空间",
     "cannot_be_traded": "美学"},
)

#: 设计优先序：主导专业关心的维度加权，辅助专业不因"好施工"而胜出
PRIORITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "architecture": {
        "aesthetic": 1.30, "spatial": 1.25, "needs": 1.05, "opportunity": 1.00,
        "downstream": 1.00, "buildability": 0.90, "budget": 0.90,
    },
    "interior": {
        "aesthetic": 1.30, "spatial": 1.20, "needs": 1.15, "opportunity": 1.05,
        "downstream": 1.00, "buildability": 0.90, "budget": 0.90,
    },
    "landscape": {
        "aesthetic": 1.35, "spatial": 1.20, "opportunity": 1.10, "needs": 0.95,
        "downstream": 1.00, "buildability": 0.85, "budget": 0.90,
    },
}


@dataclass
class Leadership:
    """一次委托里谁主导、谁支撑、谁只处理接口。"""

    mode: str = "B"
    lead: str = "interior"
    joint_lead: str = ""
    design_disciplines: List[str] = field(default_factory=list)
    support_disciplines: List[str] = field(default_factory=list)
    coordination: List[str] = field(default_factory=list)
    existing_building: bool = False
    design_priority: List[str] = field(default_factory=list)
    technical_constraints: List[Dict[str, str]] = field(default_factory=list)
    review_requirements: List[str] = field(default_factory=list)
    evidence: str = ""
    confidence: float = 0.6

    @property
    def label(self) -> str:
        return str(MODES.get(self.mode, {}).get("label", self.mode))

    @property
    def lead_label(self) -> str:
        from .disciplines import DISCIPLINES

        d = DISCIPLINES.get(self.lead)
        base = d.label if d else self.lead
        if self.joint_lead:
            j = DISCIPLINES.get(self.joint_lead)
            return f"{base} + {j.label if j else self.joint_lead}"
        return base

    @property
    def design_intent_owner(self) -> str:
        return self.lead_label

    def is_design(self, did: str) -> bool:
        return did in self.design_disciplines

    def is_support(self, did: str) -> bool:
        return did in self.support_disciplines

    def mode_info(self) -> Dict[str, Any]:
        return dict(MODES.get(self.mode, {}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "mode_key": self.mode_info().get("key", ""),
            "mode_label": self.label,
            "project_lead_discipline": self.lead,
            "joint_lead_discipline": self.joint_lead,
            "lead_label": self.lead_label,
            "design_intent_owner": self.design_intent_owner,
            "design_disciplines": list(self.design_disciplines),
            "supporting_disciplines": list(self.support_disciplines),
            "coordination_disciplines": list(self.coordination),
            "existing_building_constraints": self.existing_building,
            "design_priority": list(self.design_priority),
            "technical_constraints": [dict(x) for x in self.technical_constraints],
            "professional_review_requirements": list(self.review_requirements),
            "lead_owns": list(self.mode_info().get("lead_owns") or []),
            "must_not": self.mode_info().get("must_not", ""),
            "when": self.mode_info().get("when", ""),
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "note": ("主导专业有设计统筹权，没有安全豁免权：结构安全、消防与强制性"
                     "规范、经核实的物理限制三条不可突破。"),
        }


def _answers(project: Any) -> Dict[str, str]:
    from .intake.interview import load_interview

    raw = load_interview(project).answers or {}
    return {k: str((v or {}).get("value") or "") for k, v in raw.items()}


def _firm(scope: Any, did: str) -> bool:
    """这个专业是不是**有实据**在范围内。

    区分很重要：`interior` 可能因为"项目类型是住宅"被预设进来（弱证据），
    `architecture` 可能因为"项目类型判为建筑类"被推断进来（弱证据）。
    弱证据不能用来抢主导权——否则一个纯庭院委托会被判成"建筑主导"，
    然后被要求先做整栋建筑设计。
    """
    from .disciplines import DECLARED, REQUIRED

    e = (getattr(scope, "entries", {}) or {}).get(did)
    if e is None:
        return False
    if e.state in (DECLARED, REQUIRED):
        return True
    ev = str(e.evidence or "")
    return ev.startswith("文中出现") or ev.startswith("新建迹象")


def detect(project: Any, scope: Any, *, profile_id: str = "") -> Leadership:
    """按范围与现有条件判断主导模式。

    判定顺序刻意从"最小介入"开始：先看是不是专项委托，再看是否整体设计。
    这样纯室内委托永远不会被升级成建筑主导。
    """
    from .disciplines import DISCIPLINES

    active = set(scope.active())
    answers = _answers(project)
    # 判定依据必须包含**客户原话**：范围层已把原话存进 `basis`。
    # 只靠问答槽位会漏掉"买了一套/已有房子"这类关键限定——它们不落在任何槽位里。
    blob = " ".join([str(project.name or ""),
                     *[str(x) for x in (getattr(scope, "basis", ()) or ())],
                     *[v for k, v in answers.items() if k != "base.project_type"]])
    pid = profile_id or str((project.meta or {}).get("profile_id") or "")

    # 既有建筑：有楼层/空间几何，或客户明说"已建成/买了一套/二手房"
    existing = bool(getattr(project, "levels", None) or getattr(project, "spaces", None))
    for word in ("已建成", "已交付", "买了一套", "二手房", "现有", "已有", "已完成",
                 "已装修", "入住", "老房", "原房", "翻新", "改造"):
        if word in blob:
            existing = True
            break

    has_arch = "architecture" in active and _firm(scope, "architecture")
    has_int = "interior" in active and _firm(scope, "interior")
    has_land = "landscape" in active and _firm(scope, "landscape")

    from .disciplines import NEW_BUILD_HINTS, _hits

    new_build = bool(_hits(blob, NEW_BUILD_HINTS))
    nature = str(answers.get("project_nature") or "")
    if has_arch and "新建" in nature:
        new_build = True

    # ---- 模式判定 -----------------------------------------------------
    if has_land and not has_int and not has_arch:
        mode = "C"                       # 纯景观：连建筑都不在实据范围
    elif has_land and not has_int and not new_build:
        mode = "C"                       # 景观 + 弱建筑迹象，仍按景观主导
    elif has_arch and new_build and has_int and has_land:
        mode = "D"                       # 建筑+室内+景观整体
    elif has_arch and new_build:
        mode = "A"                       # 建筑主导（含室内/景观深化）
    elif has_int and has_land and existing:
        mode = "E"                       # 既有建筑的室内+景观联合
    elif has_int:
        mode = "B"                       # 室内主导
    elif has_land:
        mode = "C"
    elif has_arch:
        mode = "A"
    else:
        mode = "B"

    info = MODES[mode]
    lead = info["lead"]
    joint = info.get("joint_lead", "") if mode == "E" else ""

    # 支撑专业必须是"在范围内"的，不能凭空要求
    support = [d for d in info["support_disciplines"] if d in active]
    coord = [d for d in info["coordination"] if d in active]
    # 主导专业本身必须在范围内；不在就退回"范围内最靠前的设计专业"
    if lead not in active:
        for cand in ("architecture", "interior", "landscape"):
            if cand in active:
                lead = cand
                break

    priority = _design_priority(mode, lead)
    constraints = _technical_constraints(active, existing)
    reviews = _reviews(lead, active)

    evidence_bits = []
    if new_build:
        evidence_bits.append("有新建迹象")
    if existing:
        evidence_bits.append("既有建筑/现状条件")
    evidence_bits.append("范围：" + "、".join(scope.labels(sorted(active))))

    return Leadership(
        mode=mode, lead=lead, joint_lead=joint,
        design_disciplines=[d for d in info["design_disciplines"] if d in active]
        or ([lead] if lead in DISCIPLINES else []),
        support_disciplines=support, coordination=coord,
        existing_building=existing, design_priority=priority,
        technical_constraints=constraints, review_requirements=reviews,
        evidence="；".join(evidence_bits),
        confidence=0.8 if (new_build or existing) else 0.6,
    )


def _design_priority(mode: str, lead: str) -> List[str]:
    """主导专业先看什么。这不是权重表，是**讨论顺序**。"""
    if mode in ("C",):
        return ["景观意境与空间序列", "地形与竖向", "植物与水景", "与建筑的关系",
                "维护与耐久"]
    if mode in ("B",):
        return ["空间体验与功能", "顶墙地造型", "材料与光", "家具与固定件",
                "设备整合的隐蔽性"]
    if mode in ("A", "D"):
        return ["建筑体量与形态", "内外空间关系", "立面与轮廓", "功能组织",
                "室内与景观的延续性"]
    return ["整体设计语言", "室内外过渡", "空间体验"]


def _technical_constraints(active: Sequence[str], existing: bool) -> List[Dict[str, str]]:
    out = [dict(x) for x in HARD_CONSTRAINTS]
    if "structure" in active and existing:
        out.append({"id": "TC-EXISTING-STRUCT",
                    "text": "既有结构：拆改前须确认承重属性，不得凭图纸推定",
                    "cannot_be_traded": "设计意图"})
    if "mep" in active:
        out.append({"id": "TC-MEP-HEIGHT",
                    "text": "净高与检修空间：设备可隐藏，但不能取消检修条件",
                    "cannot_be_traded": "设计意图（可调整形式）"})
    return out


def _reviews(lead: str, active: Sequence[str]) -> List[str]:
    out: List[str] = []
    if "structure" in active:
        out.append("结构安全由注册结构工程师复核签署")
    if "mep" in active:
        out.append("负荷、消防与系统选型由机电工程师复核签署")
    if "planning" in active:
        out.append("规划指标与报批可行性由当地专业人员核对")
    if lead in ("architecture", "interior", "landscape"):
        out.append("设计意图的取舍由总设计师与业主确认")
    return out


# --------------------------------------------------------------------------
# 读写：与 disciplines 一样存在 meta 里，schema 向后兼容
def store(project: Any, lead: Leadership) -> Dict[str, Any]:
    payload = lead.to_dict()
    meta = getattr(project, "meta", None)
    if not isinstance(meta, dict):
        project.meta = {}
        meta = project.meta
    meta["leadership"] = payload
    return payload


def load(project: Any) -> Optional[Dict[str, Any]]:
    raw = (getattr(project, "meta", {}) or {}).get("leadership") or {}
    return dict(raw) or None


def ensure(project: Any, scope: Any, *, profile_id: str = "") -> Leadership:
    """已判定就复用，未判定就判定并存档。

    复用是刻意的：主导权不能在 S1/S2/S3 之间悄悄漂移。
    """
    raw = load(project)
    if raw and raw.get("mode"):
        return Leadership(
            mode=raw["mode"], lead=raw.get("project_lead_discipline", "interior"),
            joint_lead=raw.get("joint_lead_discipline", ""),
            design_disciplines=list(raw.get("design_disciplines") or []),
            support_disciplines=list(raw.get("supporting_disciplines") or []),
            coordination=list(raw.get("coordination_disciplines") or []),
            existing_building=bool(raw.get("existing_building_constraints")),
            design_priority=list(raw.get("design_priority") or []),
            technical_constraints=list(raw.get("technical_constraints") or []),
            review_requirements=list(raw.get("professional_review_requirements") or []),
            evidence=str(raw.get("evidence") or ""),
            confidence=float(raw.get("confidence") or 0.6),
        )
    lead = detect(project, scope, profile_id=profile_id)
    store(project, lead)
    return lead


def weights_for(lead: Leadership) -> Dict[str, float]:
    """按主导专业给比较维度加权。未列出的维度按 1.0。"""
    base = PRIORITY_WEIGHTS.get(lead.lead)
    if lead.joint_lead and base is None:
        base = PRIORITY_WEIGHTS.get(lead.joint_lead)
    if base is None:
        return {}
    return dict(base)


def summary_lines(lead: Leadership) -> List[str]:
    lines = [f"- 主导模式：**{lead.label}**（{lead.mode}）——{lead.mode_info().get('when', '')}"]
    lines.append(f"- 设计主导：**{lead.lead_label}**（对整体设计效果有统筹权）")
    if lead.support_disciplines:
        from .disciplines import DISCIPLINES

        names = "、".join(DISCIPLINES[d].label for d in lead.support_disciplines
                         if d in DISCIPLINES)
        lines.append(f"- 技术支撑：{names}（研究如何实现，不主导形态）")
    if lead.design_priority:
        lines.append(f"- 讨论顺序：{' → '.join(lead.design_priority)}")
    lines.append("- 不可突破：" + "；".join(x["text"] for x in lead.technical_constraints[:3]))
    return lines


__all__ = ["MODES", "MODE_ORDER", "HARD_CONSTRAINTS", "PRIORITY_WEIGHTS",
           "Leadership", "detect", "ensure", "load", "store", "weights_for",
           "summary_lines"]
