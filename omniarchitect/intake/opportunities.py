"""Design opportunity analysis.

This is what separates a chief designer from a form: after listening and
checking, it names the three to five problems worth spending the project on.

An opportunity is **a design question with evidence**, not a concept. It never
proposes a layout, a material or a look — those are S2's job and need approval.
Each item answers: what is wrong, how do we know, what would "better" mean,
what does it cost us in constraints, how sure are we, and what should S2 do
with it.

Items are only emitted when the evidence exists. Fewer than three is an honest
result; padding to three is not.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from .feasibility import run_feasibility
from .interview import load_interview
from .needs import build_need_matrix

OPPORTUNITY_FIELDS: Tuple[str, ...] = (
    "opportunity_id", "problem", "evidence", "design_goal", "expected_value",
    "constraints", "priority", "confidence", "next_stage_recommendation",
)

PRIORITY_LABEL = {"high": "高", "medium": "中", "low": "低"}
CONFIDENCE_LABEL = {"high": "高（有文件或核验依据）", "medium": "中（由需求推断）",
                    "low": "低（仅为假设）"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Opportunity:
    opportunity_id: str
    problem: str
    evidence: str
    design_goal: str
    expected_value: str
    constraints: str
    priority: str = "medium"
    confidence: str = "medium"
    next_stage_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "opportunity_id": self.opportunity_id,
            "problem": self.problem,
            "evidence": self.evidence,
            "design_goal": self.design_goal,
            "expected_value": self.expected_value,
            "constraints": self.constraints,
            "priority": self.priority,
            "priority_label": PRIORITY_LABEL.get(self.priority, self.priority),
            "confidence": self.confidence,
            "confidence_label": CONFIDENCE_LABEL.get(self.confidence, self.confidence),
            "next_stage_recommendation": self.next_stage_recommendation,
        }
        # Every declared field must be present — the schema is the contract.
        for f in OPPORTUNITY_FIELDS:
            d.setdefault(f, "")
        return d


def _answer(project: Project, qid: str) -> str:
    ans = (load_interview(project).answers or {}).get(qid) or {}
    return str(ans.get("value") or "") if ans.get("state") in ("answered", "assumed") else ""


def _window_ratio(project: Project) -> Tuple[float, float]:
    """(window opening width / perimeter, total perimeter) — 0 when unknown."""
    try:
        from ..planner import envelope_polygon

        lvl = project.levels[0].id if project.levels else ""
        env = envelope_polygon(project, lvl)
        per = 0.0
        for i in range(len(env)):
            x1, y1 = env[i]
            x2, y2 = env[(i + 1) % len(env)]
            per += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        win = sum(max(e.width_mm if hasattr(e, "width_mm") else 0, 0)
                  for e in project.elements if e.type == "window")
        if win <= 0:
            win = sum(float((e.properties or {}).get("width_mm") or 0)
                      for e in project.elements if e.type == "window")
        return (win / per if per else 0.0), per / 1000.0
    except Exception:
        return 0.0, 0.0


def _collect(project: Project) -> List[Opportunity]:
    out: List[Opportunity] = []
    matrix = build_need_matrix(project)
    acts = " ".join(r["activity"] for r in matrix["rows"])
    feas = run_feasibility(project)
    conflicts = {c["id"]: c for c in feas["conflicts"]}
    profile = str((load_interview(project).profile_id) or "")

    # --- 1. daylight / openness ------------------------------------------
    ratio, perimeter_m = _window_ratio(project)
    mentions_light = any(w in (_answer(project, "base.needs") + _answer(
        project, "res.daily_rhythm")) for w in ("采光", "暗", "通透", "阳光", "晒"))
    if mentions_light or (ratio and ratio < 0.12):
        ev = (f"窗洞宽度合计与外墙周长之比约 {ratio:.2f}（外墙周长约 {perimeter_m:.1f} m）"
              if ratio else "业主明确提出采光/通透诉求")
        out.append(Opportunity(
            opportunity_id="OP-01",
            problem="自然采光与空间通透性不足，白天也要靠人工照明维持观感",
            evidence=ev,
            design_goal="在不扩大外墙开口的前提下，把可用自然光引到进深更大的区域",
            expected_value="白天照明能耗下降，空间显得更大且层次更清楚",
            constraints="承重墙与外立面开口受结构与物业限制；不得以采光为由拆改结构",
            priority="high" if mentions_light else "medium",
            confidence="high" if ratio and ratio < 0.12 else "medium",
            next_stage_recommendation="S2：以采光路径为线索做 2–3 个空间原型，S3 用平面验证光深",
        ))

    # --- 2. circulation & privacy -----------------------------------------
    if "待客" in acts and ("睡眠" in acts or "儿童" in acts):
        out.append(Opportunity(
            opportunity_id="OP-02",
            problem="待客动线与休息/学习动线共用同一条路径，隐私与安静互相干扰",
            evidence="需求中同时出现待客与睡眠/儿童用途，且未设独立的过渡空间",
            design_goal="让访客止步于公共区，卧室与学习区不被穿越",
            expected_value="不需要增加面积即可提升隐私；减少「一有客人全家挪位」的情况",
            constraints="户型进深与入户位置固定；改动限于非承重隔墙",
            priority="high",
            confidence="medium",
            next_stage_recommendation="S2：把公共/私密分层作为概念主线之一，S3 用动线图证明无穿越",
        ))

    # --- 3. area efficiency ----------------------------------------------
    area_conflict = conflicts.get("F-AREA-01") or conflicts.get("F-AREA-02")
    if area_conflict:
        out.append(Opportunity(
            opportunity_id="OP-03",
            problem="有限面积与需求密度不匹配，需要一个「空间复用」策略而不是继续加房间",
            evidence=area_conflict["evidence"],
            design_goal="通过复合使用与可变家具，把同一块面积在不同时段服务不同活动",
            expected_value="在不增加面积的情况下满足更多功能，且保留主要空间的舒适度",
            constraints="复合空间需要收纳与转换机制，造价与日常操作成本会上升",
            priority="high",
            confidence="high",
            next_stage_recommendation="S2：提出复合使用方案；S3 校核每种状态下的通行与家具尺度",
        ))

    # --- 4. storage & equipment ------------------------------------------
    wants_storage = "收纳" in acts
    has_storage = any("storage" in str(p.get("recipe") or "") for p in project.program or [])
    if wants_storage and not has_storage:
        out.append(Opportunity(
            opportunity_id="OP-04",
            problem="收纳需求明确，但 program 中没有独立的储藏空间，收纳只能靠零散柜体",
            evidence="需求中含收纳/储物用途；功能表中无储藏间或专属收纳空间",
            design_goal="把收纳当作独立系统设计：按物品体积、取用频率与动线分配位置",
            expected_value="入住后不易复乱；减少后期加柜造成的动线损失",
            constraints="面积紧张时收纳要嵌进墙体与家具，需与结构厚度协调",
            priority="medium",
            confidence="high",
            next_stage_recommendation="S2：给出收纳系统分区；S3 在平面中标注柜体深度与开启空间",
        ))

    # --- 5. kitchen / dining relationship ---------------------------------
    if "烹饪" in acts and ("聚餐" in acts or "用餐" in acts):
        out.append(Opportunity(
            opportunity_id="OP-05",
            problem="烹饪与用餐的关系没有定：开放还是封闭，直接决定油烟、动线与社交方式",
            evidence="需求中同时出现烹饪与用餐/聚餐用途",
            design_goal="按真实烹饪强度决定厨房边界，而不是按风格偏好决定",
            expected_value="避免「好看但不好用」的开放式厨房，或「好用但封闭」的孤立厨房",
            constraints="排烟与补风条件限制开放可行性，须机电专业确认",
            priority="high",
            confidence="medium",
            next_stage_recommendation="S2：给出开放/半开放/封闭三种关系；S3 用平面比较操作三角",
        ))

    # --- 6. commercial operation efficiency -------------------------------
    if profile in ("retail", "hospitality"):
        out.append(Opportunity(
            opportunity_id="OP-06",
            problem="服务动线与客用动线的关系尚未在平面上成立，运营效率存在隐患",
            evidence="项目类型为餐饮/零售或酒店/民宿，后场与客用区的关系未在方案中固定",
            design_goal="让补货、清运、员工通行不穿越客用区，同时缩短服务半径",
            expected_value="同等面积下提高翻台或客房周转效率，减少运营期改造",
            constraints="租赁物业的后场通道与卸货条件受限，须先确认",
            priority="high",
            confidence="medium",
            next_stage_recommendation="S2：把后场动线作为独立图层；S3 用流线图验证不交叉",
        ))

    # --- 7. construction complexity vs budget -----------------------------
    budget_conflict = conflicts.get("F-BUD-02") or conflicts.get("F-BUD-03")
    if budget_conflict:
        out.append(Opportunity(
            opportunity_id="OP-07",
            problem="预算与造型复杂度冲突，需要在「看起来高级」与「做得出来」之间选路",
            evidence=budget_conflict["evidence"],
            design_goal="用节点与比例而非复杂造型建立品质感，把预算放在高频接触面",
            expected_value="降低施工难度与现场变更，同时保住观感",
            constraints="不得以降低造价为由削减结构安全、防水与机电必要做法",
            priority="high" if budget_conflict["severity"] == "blocker" else "medium",
            confidence="high",
            next_stage_recommendation="S2：定材料与节点策略；S4 细化做法并核算",
        ))

    # --- 8. ceiling height / services -------------------------------------
    tech = conflicts.get("F-TEC-03")
    if tech:
        out.append(Opportunity(
            opportunity_id="OP-08",
            problem="层高与设备整合是这版的硬约束，净高决定了空间感受的上限",
            evidence=tech["evidence"],
            design_goal="按净高目标倒推设备形式与吊顶策略，把设备藏起来而不牺牲层高",
            expected_value="避免入住后「到处是吊顶」的压抑感，也避免后期开孔返工",
            constraints="空调形式受外机位置与管线限制，须与机电专业一起定",
            priority="medium",
            confidence="high",
            next_stage_recommendation="S2：提出吊顶策略；S4 与机电点位一起深化",
        ))

    # --- 9. structural uncertainty ---------------------------------------
    struct = conflicts.get("F-TEC-01")
    if struct:
        out.append(Opportunity(
            opportunity_id="OP-09",
            problem="结构条件不明，使「能改多少」成为设计的前提问题而不是细节问题",
            evidence=struct["evidence"],
            design_goal="在结构可验证范围内，用隔断与家具重新组织空间，减少对拆改的依赖",
            expected_value="把方案从「赌能不能拆」变成「不拆也能成立」",
            constraints="任何拆改须经现场探测或原设计单位确认；未确认前不得出结构相关图纸",
            priority="high",
            confidence="high",
            next_stage_recommendation="S2：给出不依赖拆改的原型；S3 前完成结构核实",
        ))
    return out


def find_opportunities(project: Project, limit: int = 5,
                       minimum: int = 0) -> Dict[str, Any]:
    """Ranked design opportunities. Never pads to reach a target count."""
    items = _collect(project)
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda o: (order.get(o.priority, 9), o.opportunity_id))
    chosen = items[:max(0, limit)]
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "generated_at": _now(),
        "items": [o.to_dict() for o in chosen],
        "count": len(chosen),
        "suppressed": max(0, len(items) - len(chosen)),
        "note": ("最多 5 项、按优先级取前若干；证据不足时少于 3 项属正常结果，"
                 "不得为凑数补条目。这些是「要解决的设计问题」，不是概念方案或平面。"),
        "below_minimum": len(chosen) < minimum,
    }


def markdown(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    for i, o in enumerate(result["items"], 1):
        lines += [
            f"### {i}. {o['opportunity_id']}　{o['problem']}",
            "",
            f"- **依据**：{o['evidence']}",
            f"- **设计目标**：{o['design_goal']}",
            f"- **预期价值**：{o['expected_value']}",
            f"- **约束**：{o['constraints']}",
            f"- **优先级 / 把握**：{o['priority_label']} / {o['confidence_label']}",
            f"- **下一步**：{o['next_stage_recommendation']}",
            "",
        ]
    if not lines:
        lines = ["未识别到有证据支撑的设计机会——资料不足时这是正确结果，"
                 "补齐需求与条件后重跑，不要用假设凑数。", ""]
    return "\n".join(lines)
