"""S1 → S2 承接：把已确认的任务书读成概念设计能用的输入。

这一层**不做设计**，只回答五个问题：

1. G1 到底确认了没有？确认的是哪个版本？现在还是不是同一份？
2. 已确认的需求有哪些？哪些是推断的？
3. 有哪些设计机会必须被回应？
4. 哪些限制会跟着概念一路走到 S3？
5. 数据够不够支撑"按真实尺寸成立"的说法？

答案全部带证据（来源问卷 id / 空间 id / 机会 id），因为概念方案里每一句
"因为……所以……" 都要能追回去。追不回去的判断，宁可写"待核实"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..intake.diligence import (
    assess_sources,
    precision_level,
    uncertainty_register,
)
from ..intake.feasibility import run_feasibility
from ..intake.gate import assess_gate, check_baseline
from ..intake.interview import ensure_intake, load_interview
from ..intake.needs import build_need_matrix
from ..intake.opportunities import find_opportunities
from ..intake.profiles import PROFILES
from ..model import Project
from ..stage_state import CONFIRMED, get_state


def _answer(project: Project, qid: str) -> str:
    return str((load_interview(project).answers or {}).get(qid, {}).get("value") or "")


def _area_from_geometry(project: Project) -> Optional[float]:
    """Usable floor area of the envelope, in m². None when there is no geometry."""
    if not project.spaces and not project.elements:
        return None
    try:
        from ..model import polygon_area_mm2
        from ..planner import envelope_polygon

        env = envelope_polygon(project, project.levels[0].id if project.levels else "")
        if not env:
            return None
        return round(polygon_area_mm2(env) / 1_000_000.0, 1)
    except Exception:
        return None


def _budget_tier(budget_cny: float, area_m2: Optional[float]) -> Tuple[str, str]:
    """Rough tier from budget per m². Returns ('', reason) rather than guessing."""
    if not budget_cny or not area_m2:
        return "", "预算或面积缺失，无法判断档位"
    per_m2 = budget_cny / area_m2
    if per_m2 < 3000:
        return "economy", f"约 {per_m2:,.0f} 元/m²（硬装口径，偏低）"
    if per_m2 < 6500:
        return "mid", f"约 {per_m2:,.0f} 元/m²（硬装口径，常规）"
    if per_m2 < 13000:
        return "premium", f"约 {per_m2:,.0f} 元/m²（硬装口径，偏高）"
    return "luxury", f"约 {per_m2:,.0f} 元/m²（硬装口径，高端）"


def _parse_budget(text: str) -> float:
    if not text:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", text)
    if m:
        return float(m.group(1)) * 10000.0
    m = re.search(r"(\d[\d,]{2,})\s*(?:元|块|rmb|cny)", text, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    return 0.0


# --------------------------------------------------------------------------
# 信号：把证据折成 0–1 的强度，供原型匹配使用
# --------------------------------------------------------------------------
def _signals(project: Project, ctx: "ConceptContext") -> Dict[str, Dict[str, Any]]:
    """Each signal carries its own strength *and* the reason it fired."""
    out: Dict[str, Dict[str, Any]] = {}
    acts = " ".join(r["activity"] for r in ctx.needs)
    raw_needs = _answer(project, "base.needs")
    evidence_text = acts + " " + raw_needs

    def put(key: str, strength: float, reason: str) -> None:
        if strength <= 0:
            return
        out[key] = {"strength": round(min(1.0, strength), 2), "reason": reason}

    op_ids = {o["opportunity_id"] for o in ctx.opportunities}
    op_theme = {}
    for o in ctx.opportunities:
        # opportunities carry free-text problems; map by keyword to a theme
        blob = o["problem"] + o["design_goal"]
        for theme, words in (
            ("daylight", ("采光", "通透", "自然光", "暗")),
            ("privacy", ("隐私", "安静", "穿越", "私密")),
            ("area", ("面积", "复用", "密度", "装不下")),
            ("storage", ("收纳", "储物", "储藏")),
            ("kitchen", ("烹饪", "厨房", "用餐", "油烟")),
            ("structure", ("结构", "拆改", "承重", "改造范围")),
        ):
            if any(w in blob for w in words):
                op_theme.setdefault(theme, o["opportunity_id"])

    if "daylight" in op_theme:
        put("daylight", 0.75 if "采光" in raw_needs or "暗" in raw_needs else 0.6,
            f"设计机会 {op_theme['daylight']} 指向采光")
    if "privacy" in op_theme:
        put("privacy", 0.8, f"设计机会 {op_theme['privacy']} 指向隐私/穿越")
    if "area" in op_theme:
        put("area", 0.85, f"设计机会 {op_theme['area']} 指向面积效率")
    if "storage" in op_theme:
        put("storage", 0.6, f"设计机会 {op_theme['storage']} 指向收纳")
    if "kitchen" in op_theme:
        put("kitchen", 0.6, f"设计机会 {op_theme['kitchen']} 指向烹饪与用餐")
    if "structure" in op_theme:
        put("structure", 0.55,
            f"设计机会 {op_theme['structure']} 指向「减少对拆改的依赖」")

    if "聚餐" in acts or "待客" in acts:
        put("arrival", 0.5, "需求含待客/聚餐：入户与过渡需要承接访客")
    if "烹饪" in acts:
        put("kitchen", max(0.6, out.get("kitchen", {}).get("strength", 0)),
            "需求含烹饪：厨房边界与后场关系需要确定")
    if "儿童" in acts or "儿童活动" in acts:
        put("flexibility", 0.55, "需求含儿童活动：空间需随年龄变化")
    if "居家办公" in evidence_text or "远程" in evidence_text:
        put("focus", 0.6, "需求含居家办公：需要可关闭的专注空间")
    if "照护" in evidence_text or "老人" in evidence_text:
        put("acoustic", 0.45, "需求含老人/照护：安静与无障碍要求提高")

    # 面积压力：需求面积 ÷ 可用面积
    if ctx.area_available_m2 and ctx.target_area_m2:
        ratio = ctx.target_area_m2 / ctx.area_available_m2
        if ratio > 0.95:
            put("area", max(out.get("area", {}).get("strength", 0), min(1.0, ratio - 0.6)),
                f"需求合计 {ctx.target_area_m2:.0f} m² ÷ 可用 {ctx.area_available_m2:.0f} m²"
                f" = {ratio:.2f}")

    # 项目类型自带的信号
    if ctx.profile_id == "office":
        people = _answer(project, "off.headcount")
        if people:
            put("collaboration", 0.55, f"办公人数：{people}")
            put("focus", max(out.get("focus", {}).get("strength", 0), 0.45),
                "办公项目默认需要专注与协作两类空间")
        if _answer(project, "off.meeting"):
            put("acoustic", 0.5, f"会议频率：{_answer(project, 'off.meeting')}")
        # 增长计划在 headcount 答案里常被一起说到，两处都读
        growth = _answer(project, "off.growth") or (
            _answer(project, "off.headcount") if any(
                w in _answer(project, "off.headcount") for w in ("扩", "增长", "计划到", "两年")) else "")
        if growth:
            put("growth", 0.5, f"增长计划：{growth}")
        visitor = _answer(project, "off.visitor")
        if visitor:
            put("arrival", 0.6, f"访客情况：{visitor}")
            if any(w in visitor for w in ("不需要", "不进", "只到前", "止于")):
                put("privacy", 0.5, f"访客只需到前场：{visitor}")
        brand = _answer(project, "off.brand")
        if brand and not any(w in brand for w in ("不需要", "没有", "暂无")):
            put("brand", 0.6, f"品牌要求：{brand}")
        facility = _answer(project, "off.facility")
        if facility:
            put("service", 0.55, f"特殊空间：{facility}")
            if any(w in facility for w in ("打印", "机房", "茶水")):
                put("acoustic", max(out.get("acoustic", {}).get("strength", 0), 0.45),
                    f"设备与茶水带来的噪声：{facility}")
    if ctx.profile_id == "hospitality":
        put("arrival", 0.8, "酒店/民宿：到达序列是产品的第一印象")
        put("operation", 0.75, "酒店/民宿：运营与后勤效率直接决定毛利")
        put("brand", 0.6, "酒店/民宿：品牌体验需要可识别的空间语言")
    if ctx.profile_id == "retail":
        put("operation", 0.8, "餐饮/商业：坪效与服务流线是核心指标")
        put("brand", 0.7, "餐饮/商业：品牌识别决定进店率")
        if "烹饪" in acts:
            put("kitchen", 0.7, "餐饮项目：后厨与前场关系是设计主线")
    if ctx.profile_id == "exhibition":
        put("exhibit", 0.85, "展厅：内容叙事是空间组织的依据")
        put("experience", 0.6, "展厅：参观体验与停留时长是评价标准")
    if ctx.profile_id == "architecture":
        put("structure", 0.6, "新建建筑：结构与跨度决定空间可能")
        put("outdoor", 0.5, "新建建筑：场地与室外关系是概念的一部分")

    # 业主明确说过的诉求（不需要机会条目的支撑）。
    #
    # 早先这里只有采光、收纳、体验、可变四项，于是「保证私密性」「室外带庭院和水景」
    # 「进门要有仪式感」这些业主亲口说的话，在信号层完全不存在——建筑主导的项目
    # 于是拿不到 privacy / outdoor / arrival，推敲时只能按采光一条线索选策略。
    # 业主说过的话就是最强证据，不该因为没有对应的机会条目而被丢掉。
    for key, words in (
        ("daylight", ("采光", "通透", "阳光", "亮")),
        ("privacy", ("私密", "隐私", "隐蔽", "不被看到", "安静")),
        ("outdoor", ("庭院", "院子", "花园", "水景", "室外", "露台", "屋顶花园")),
        ("arrival", ("仪式感", "入户", "玄关", "到达", "门厅")),
        ("storage", ("收纳", "储物")),
        ("experience", ("氛围", "感觉", "格调", "体验")),
        ("flexibility", ("以后", "将来", "变化", "二胎")),
        ("maintenance", ("好维护", "少打理", "省心", "不想花时间")),
    ):
        if any(w in raw_needs for w in words):
            put(key, max(out.get(key, {}).get("strength", 0), 0.6),
                f"业主原话提到「{[w for w in words if w in raw_needs][0]}」")

    ctx.opportunity_ids = op_ids
    return out


@dataclass
class ConceptContext:
    """Everything S2 is allowed to rely on, with its provenance."""

    project_id: str = ""
    revision: int = 1
    name: str = ""
    profile_id: str = "residential"
    profile_label: str = ""

    gate_confirmed: bool = False
    gate_source: str = ""
    gate_confirmed_by: str = ""
    gate_stale: bool = False
    gate_change_kind: str = ""
    gate_reason: str = ""

    precision: str = "diagnostic"
    area_available_m2: Optional[float] = None
    target_area_m2: float = 0.0

    style_preference: str = ""
    #: 业主原话里的空间感受诉求：{原词: [手法 id]}。
    #: 这是 S2 用来判断「这套方向给不给得出他要的感觉」的唯一依据；
    #: 业主没说就是空字典，不替他推断（见 `design/vocabulary.fit`）。
    feelings: Dict[str, List[str]] = field(default_factory=dict)
    feeling_text: str = ""
    location: str = ""
    budget_cny: float = 0.0
    budget_tier: str = ""
    budget_note: str = ""
    maintenance: str = ""

    answers: Dict[str, str] = field(default_factory=dict)
    program: List[Dict[str, Any]] = field(default_factory=list)
    needs: List[Dict[str, Any]] = field(default_factory=list)
    need_gaps: List[str] = field(default_factory=list)
    opportunities: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    uncertainty: List[Dict[str, Any]] = field(default_factory=list)
    sources: Dict[str, Any] = field(default_factory=dict)

    signals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    opportunity_ids: set = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)

    #: 主导专业与设计优先序。由 `leadership.ensure()` 决定，S2 据此加权——
    #: 不是四个维度平权：主导专业关心的维度先看，辅助专业不因"好施工"而胜出。
    lead: Dict[str, Any] = field(default_factory=dict)

    #: 统一硬门槛判定（`hardgate.evaluate`）。S2 排序与 G2 判定读同一份，
    #: 避免"S2 说可行、G2 说不行"这类互相打脸。
    hard_gate: Dict[str, Any] = field(default_factory=dict)

    @property
    def lead_id(self) -> str:
        return str(self.lead.get("project_lead_discipline") or "")

    @property
    def lead_label(self) -> str:
        return str(self.lead.get("lead_label") or "")

    @property
    def lead_weights(self) -> Dict[str, float]:
        from ..leadership import PRIORITY_WEIGHTS

        return dict(PRIORITY_WEIGHTS.get(self.lead_id) or {})

    @property
    def can_claim_dimensions(self) -> bool:
        """May this round claim "verified against real dimensions"?"""
        return self.precision == "authoritative_capable"

    @property
    def dimensional_note(self) -> str:
        return {
            "diagnostic": "无几何数据：本轮只做方向性空间概念，图解为拓扑关系，不按比例。",
            "schematic": "几何来自图纸但尺寸未现场核实：概念按关系组织，尺寸以 S3 校核为准。",
            "authoritative_capable": "有现场实测资料：概念可用实测尺寸讨论，仍需 S3 在模型中复核。",
        }.get(self.precision, "")

    def signal(self, key: str) -> float:
        return float((self.signals.get(key) or {}).get("strength") or 0.0)

    def label(self, key: str) -> str:
        return str((self.signals.get(key) or {}).get("reason") or "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "name": self.name,
            "profile_id": self.profile_id,
            "profile_label": self.profile_label,
            "gate": {
                "confirmed": self.gate_confirmed,
                "source": self.gate_source,
                "confirmed_by": self.gate_confirmed_by,
                "stale": self.gate_stale,
                "change_kind": self.gate_change_kind,
                "reason": self.gate_reason,
            },
            "precision": self.precision,
            "dimensional_note": self.dimensional_note,
            "can_claim_dimensions": self.can_claim_dimensions,
            "area_available_m2": self.area_available_m2,
            "target_area_m2": self.target_area_m2,
            "style_preference": self.style_preference,
            "feelings": dict(self.feelings),
            "feeling_text": self.feeling_text,
            "location": self.location,
            "budget_cny": self.budget_cny,
            "budget_tier": self.budget_tier,
            "budget_note": self.budget_note,
            "maintenance": self.maintenance,
            "program_count": len(self.program),
            "answers": dict(self.answers),
            "need_rows": len(self.needs),
            "need_gaps": list(self.need_gaps),
            "opportunities": list(self.opportunities),
            "conflicts": list(self.conflicts),
            "uncertainty": list(self.uncertainty),
            "sources": self.sources,
            "signals": self.signals,
            "lead": dict(self.lead),
            "hard_gate": dict(self.hard_gate),
            "warnings": list(self.warnings),
        }

    def brief_lines(self) -> List[str]:
        """A short, honest summary — used in reports and the deck."""
        try:
            from ..model import polygon_area_mm2  # noqa: F401
        except Exception:  # pragma: no cover
            pass
        g = "已确认" if self.gate_confirmed else "未确认"
        lines = [
            f"项目类型：{self.profile_label}　G1：{g}"
            + (f"（{self.gate_confirmed_by}）" if self.gate_confirmed_by else ""),
            f"资料精度：{self.precision}　{self.dimensional_note}",
        ]
        if self.area_available_m2:
            lines.append(f"可用面积：约 {self.area_available_m2:.0f} m²"
                         f"（需求合计 {self.target_area_m2:.0f} m²）")
        elif self.target_area_m2:
            lines.append(f"需求面积：{self.target_area_m2:.0f} m²（无几何，未核对）")
        if self.style_preference:
            lines.append(f"业主指定风格：{self.style_preference}（尊重，不替换）")
        if self.feelings:
            lines.append("业主说的感受：" + "、".join(f"「{w}」" for w in self.feelings)
                         + "（S2 据此校核空间序列）")
        if self.budget_note:
            lines.append(f"预算档位：{self.budget_tier or '未定'}　{self.budget_note}")
        if self.opportunities:
            lines.append("必须回应的设计机会："
                         + "、".join(o["opportunity_id"] for o in self.opportunities))
        return lines


def build_context(project: Project, *, require_gate: bool = True) -> ConceptContext:
    """Read S1 into a shape S2 can reason about. Never invents a value."""
    ensure_intake(project)
    interview = load_interview(project)
    profile = PROFILES.get(interview.profile_id) or PROFILES["residential"]

    st = get_state(project, "S1")
    base = check_baseline(project)
    gate_confirmed = st.status == CONFIRMED and bool(base.get("has_baseline"))
    if not base.get("has_baseline") and st.status == CONFIRMED:
        # Legacy project confirmed before baselines existed: confirmed, but we
        # cannot compare against a signed version, and we say so.
        gate_confirmed = True

    ctx = ConceptContext(
        project_id=project.project_id,
        revision=project.revision,
        name=project.name or project.project_id,
        profile_id=profile.id,
        profile_label=profile.label,
        gate_confirmed=gate_confirmed,
        gate_source="owner" if base.get("has_baseline") else ("legacy" if gate_confirmed else ""),
        gate_confirmed_by=str(base.get("confirmed_by") or ""),
        gate_stale=bool(base.get("requires_change_analysis")),
        gate_change_kind=str(base.get("change_kind") or ""),
        gate_reason=str(base.get("reason") or ""),
        precision=precision_level(project),
        area_available_m2=_area_from_geometry(project),
        target_area_m2=round(sum(float(p.get("area_m2") or 0)
                                for p in project.program or []), 1),
        program=list(project.program or []),
        sources=dict(assess_sources(project)),
    )

    ctx.answers = {str(k): str((v or {}).get("value") or "")
                   for k, v in (interview.answers or {}).items()}
    # 主导专业：S2 的权重与讨论顺序由它决定，不是所有项目套同一套权重
    try:
        from .. import disciplines as _disc
        from .. import leadership as _lead

        _scope = _disc.ensure(project, profile_id=profile.id)
        ctx.lead = _lead.ensure(project, _scope, profile_id=profile.id).to_dict()
        # 硬门槛：与 S1、G2 用同一份判定，不各自算一套
        from .. import hardgate as _hg

        ctx.hard_gate = _hg.evaluate(project, scope=_scope).to_dict()
    except Exception as exc:                       # noqa: BLE001
        ctx.warnings.append(f"主导专业判定失败，按室内主导处理：{type(exc).__name__}")
    cons = project.constraints or {}
    ctx.style_preference = str(cons.get("style") or "").strip()
    # 感受诉求来自业主原话（S1 的 base.feeling 或首句解析），不做推断。
    from ..design import vocabulary as _vocab

    _feeling_text = _answer(project, "base.feeling")
    ctx.feeling_text = _feeling_text
    ctx.feelings = _vocab.read_feelings(_feeling_text) if _feeling_text else {}
    ctx.location = _answer(project, "base.location")
    ctx.budget_cny = float(cons.get("budget_cny") or 0) or _parse_budget(_answer(project, "base.budget"))
    # 没有几何时用任务书面积估算档位：否则预算项拿不到分，风格推荐会退化成
    # 只按项目类型匹配（真实出现过：湖畔民宿被推荐成非洲当代）。
    _area_for_tier = ctx.area_available_m2 or (ctx.target_area_m2 or None)
    ctx.budget_tier, ctx.budget_note = _budget_tier(ctx.budget_cny, _area_for_tier)
    if ctx.budget_tier and not ctx.area_available_m2:
        ctx.budget_note += "；按任务书面积估算，无几何未核对"
    ctx.maintenance = _answer(project, "base.maintenance")

    matrix = build_need_matrix(project)
    ctx.needs = list(matrix.get("rows") or [])
    ctx.need_gaps = list(matrix.get("gaps") or [])

    ops = find_opportunities(project)
    ctx.opportunities = list(ops.get("items") or [])
    ctx.conflicts = list(run_feasibility(project).get("conflicts") or [])
    ctx.uncertainty = [u for u in uncertainty_register(project)
                       if u.get("open") and "S2" in (u.get("blocks_stages") or [])]

    if require_gate and not gate_confirmed:
        ctx.warnings.append(
            "G1 尚未确认：本轮概念只能作为探索，不得作为正式设计依据，也不能锁定方案。"
        )
    if ctx.gate_stale:
        ctx.warnings.append(f"任务书基准已变化（{ctx.gate_change_kind}）：概念须重新生成后再提交 G2。")
    if ctx.precision == "diagnostic":
        ctx.warnings.append("无几何数据：不得声称概念已通过精确尺寸可行性校核。")
    if not ctx.opportunities:
        ctx.warnings.append("S1 未识别到有证据的设计机会：概念将直接依据需求与原话，不补造问题。")

    ctx.signals = _signals(project, ctx)
    return ctx


def assert_ready(project: Project) -> ConceptContext:
    """Raise with a precise reason when S2 must not produce a formal concept."""
    ctx = build_context(project, require_gate=True)
    if not ctx.gate_confirmed:
        from ..errors import ValidationError

        raise ValidationError(
            "S1 任务书尚未通过 G1：概念方案必须基于已确认的需求。"
            "先运行 confirm --stage S1，或用 --explore 生成本轮探索性概念（不可锁定）。"
        )
    return ctx


__all__ = ["ConceptContext", "build_context", "assert_ready"]
