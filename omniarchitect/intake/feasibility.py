"""Design feasibility: five constraint families, each with a stated basis.

A chief designer who accepts every requirement is not being helpful, they are
postponing the argument to the construction site. This module checks the five
things that actually collide:

1. programme vs available area;
2. behaviour vs spatial conditions;
3. budget vs design ambition;
4. schedule / approvals vs scope;
5. existing building and services vs the intended intervention.

Every finding carries its evidence. When the evidence is missing, the finding
is *"we cannot judge yet, here is what to verify"* — never a made-up number.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from .diligence import uncertainty_register
from .interview import load_interview
from .needs import build_need_matrix

CONFLICT_SEVERITIES: Tuple[str, ...] = ("blocker", "major", "minor", "info")

SEVERITY_LABEL = {
    "blocker": "阻断",
    "major": "重要",
    "minor": "次要",
    "info": "需核实",
}

CATEGORY_LABEL = {
    "area": "功能与面积",
    "behavior": "行为与空间条件",
    "budget": "预算与目标",
    "schedule": "周期与审批",
    "technical": "现有建筑与专业条件",
}

# Reference build-cost bands. These are planning ranges, not quotes, and they
# are deliberately wide; the point is to catch "budget is half of what this
# scope needs", not to price a project.
COST_BAND_CNY_PER_M2: Dict[str, Tuple[float, float]] = {
    "basic": (1800.0, 3200.0),
    "standard": (3000.0, 6000.0),
    "premium": (6000.0, 12000.0),
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Conflict:
    id: str
    category: str
    problem: str
    evidence: str
    affected: str
    severity: str = "major"
    recommendation: str = ""
    alternatives: List[str] = field(default_factory=list)
    needs_human: bool = False
    blocks_stage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "category_label": CATEGORY_LABEL.get(self.category, self.category),
            "problem": self.problem,
            "evidence": self.evidence,
            "affected": self.affected,
            "severity": self.severity,
            "severity_label": SEVERITY_LABEL.get(self.severity, self.severity),
            "recommendation": self.recommendation,
            "alternatives": list(self.alternatives),
            "needs_human": self.needs_human,
            "blocks_stage": self.blocks_stage,
        }


def _answer(project: Project, qid: str) -> str:
    ans = (load_interview(project).answers or {}).get(qid) or {}
    return str(ans.get("value") or "") if ans.get("state") in ("answered", "assumed") else ""


def _constraints(project: Project) -> Dict[str, Any]:
    return dict(project.constraints or {})


def _model_area_m2(project: Project) -> float:
    """Usable area from the model; 0.0 when there is no geometry yet."""
    try:
        return float(project.usable_area_m2)
    except Exception:
        return 0.0


def _envelope_area_m2(project: Project) -> float:
    try:
        from ..model import polygon_area_mm2
        from ..planner import envelope_polygon

        lvl = project.levels[0].id if project.levels else ""
        env = envelope_polygon(project, lvl)
        return polygon_area_mm2(env) / 1_000_000.0
    except Exception:
        return 0.0


def _stated_area_m2(project: Project) -> float:
    """Area the client stated, parsed from the interview or constraints."""
    import re

    for key in ("floor_area_m2", "area_m2"):
        v = _constraints(project).get(key)
        if v:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    text = _answer(project, "base.floor_area")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平方米|平米|m2|m²)", text or "")
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 0.0
    return 0.0


def _program_area_m2(project: Project) -> Tuple[float, int]:
    total = 0.0
    n = 0
    for p in project.program or []:
        try:
            a = float(p.get("area_m2") or 0)
        except (TypeError, ValueError):
            a = 0.0
        if a > 0:
            total += a
            n += 1
    return total, n


# --------------------------------------------------------------------------
# 1. programme vs area
# --------------------------------------------------------------------------
def _check_area(project: Project) -> List[Conflict]:
    out: List[Conflict] = []
    need, n_rooms = _program_area_m2(project)
    avail = _model_area_m2(project) or _stated_area_m2(project)
    if need <= 0 and n_rooms == 0:
        return out

    if avail <= 0:
        out.append(Conflict(
            id="F-AREA-00", category="area",
            problem="功能需求有面积，但可用面积尚未确定，无法判断是否装得下",
            evidence=f"任务书需求合计 {need:.1f} m²（{n_rooms} 项），可用面积未知",
            affected="全部功能分区",
            severity="info",
            recommendation="先确认可用面积口径（建筑面积 / 使用面积 / 套内），再判可行性",
            alternatives=["按购房合同或租赁合同的建筑面积换算，并注明是否含公摊"],
            needs_human=True,
        ))
        return out

    ratio = need / avail if avail else 0.0
    if ratio > 1.15:
        out.append(Conflict(
            id="F-AREA-01", category="area",
            problem="需求面积超过可用面积，按现需求装不下",
            evidence=(f"需求合计 {need:.1f} m² ÷ 可用 {avail:.1f} m² = {ratio:.2f}"
                      f"（超出 {need - avail:.1f} m²）"),
            affected="功能分区与房间数量",
            severity="blocker",
            recommendation="在概念阶段之前完成取舍：合并功能、压缩次要空间，或调整面积目标",
            alternatives=[
                "把低频功能合并到复合空间（如书房兼客房）",
                "降低次要空间的面积，保留主空间品质",
                "换更大面积或减少功能项（需业主决策）",
            ],
            needs_human=True,
            blocks_stage="S3",
        ))
    elif ratio > 0.95:
        out.append(Conflict(
            id="F-AREA-02", category="area",
            problem="需求面积已占满可用面积，几乎没有余量",
            evidence=f"需求 {need:.1f} m² / 可用 {avail:.1f} m² = {ratio:.2f}",
            affected="通行、收纳与设备空间",
            severity="major",
            recommendation="预留 8–12% 给通行、收纳与设备，否则平面会在深化阶段被迫削房间",
            alternatives=["从次要房间各让出少量面积", "用定制家具替代独立储藏间"],
        ))
    else:
        out.append(Conflict(
            id="F-AREA-03", category="area",
            problem="面积有余量",
            evidence=f"需求 {need:.1f} m² / 可用 {avail:.1f} m² = {ratio:.2f}",
            affected="可考虑提升单空间品质或增加功能",
            severity="info",
            recommendation="余量优先给主空间尺度与收纳，其次才增加房间数量",
        ))
    return out


def _area_basis(project: Project) -> Dict[str, Any]:
    """把"面积"这件事拆开：客户说的、合同写的、模型量的，不是同一个数。"""
    stated = _stated_area_m2(project)
    model = _model_area_m2(project)
    envelope = _envelope_area_m2(project)
    cons = _constraints(project)
    declared_basis = str(cons.get("area_basis")
                         or _answer(project, "base.area_basis") or "").strip()
    diff = (abs(stated - model) / stated) if (stated > 0 and model > 0) else 0.0
    return {
        "stated_m2": round(stated, 1),
        "model_usable_m2": round(model, 1),
        "model_envelope_m2": round(envelope, 1),
        "declared_basis": declared_basis or "未说明",
        "diff_ratio": round(diff, 3),
        "labels": {
            "stated": "客户口头/文字给出的面积",
            "model_usable": "模型实测套内使用面积（不含墙体与公摊）",
            "model_envelope": "模型外轮廓面积（含墙体，不等于建筑面积）",
            "note": "建筑面积含公摊，套内面积不含公摊，使用面积再扣墙体——三者不可混用",
        },
    }


# --------------------------------------------------------------------------
# 1b. the number on the contract vs the number in the model
# --------------------------------------------------------------------------
def _check_area_basis(project: Project) -> List[Conflict]:
    """客户说 150、模型只有 131：这不是小数差，是承诺差。"""
    basis = _area_basis(project)
    stated = float(basis["stated_m2"])
    model = float(basis["model_usable_m2"])
    if stated <= 0 or model <= 0:
        return []
    diff = abs(stated - model)
    ratio = basis["diff_ratio"]
    if ratio <= 0.05:
        return []
    bigger = "客户口径更大" if stated > model else "模型更大"
    return [Conflict(
        id="F-AREA-BASIS",
        category="area",
        problem=(f"客户说的 {stated:.0f}㎡ 与模型实测 {model:.1f}㎡ 对不上"
                 f"（差 {diff:.1f}㎡，{ratio * 100:.0f}%）"),
        evidence=(f"口径：{basis['declared_basis']}；{bigger}；"
                  f"外轮廓 {basis['model_envelope_m2']:.1f}㎡"),
        affected="方案容量、造价与交付承诺",
        severity="major",
        recommendation=("先确认以哪个面积为准：以实测为准要同步下调功能目标；"
                        "以合同建筑面积为准要扣除公摊后再算"),
        alternatives=[
            "按实测套内面积做方案，并把功能/预算按同一口径调整",
            "提供带公摊的建筑面积与图纸，重新核算可用面积",
            "确认是否为两套合并或含赠送面积，补充依据",
        ],
        needs_human=True,
    )]


# --------------------------------------------------------------------------
# 1c. how many people actually fit
# --------------------------------------------------------------------------
def _headcount(project: Project) -> int:
    import re

    cons = _constraints(project)
    for key in ("headcount", "occupants"):
        try:
            v = int(float(cons.get(key)))
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    for qid in ("occupants", "off.headcount", "base.headcount"):
        text = _answer(project, qid)
        m = re.search(r"(\d{1,4})\s*(?:人|位|工位)?", text or "")
        if m:
            try:
                v = int(m.group(1))
                if v > 1:
                    return v
            except ValueError:
                continue
    return 0


def _check_capacity(project: Project) -> List[Conflict]:
    """办公/商业：人数与面积的关系要在选方案之前说清楚。

    人均面积用的是**规划经验区间**，不是任何地区的法规指标——法规符合性由
    持证专业人员在项目所在地复核。这里只回答一个朴素问题：装不装得下。
    """
    from .profiles import profile_for

    pid = str((load_interview(project).answers or {}).get("profile_id") or "") or \
        profile_for(project.name or "").id
    if pid not in ("office", "retail", "exhibition"):
        return []

    n = _headcount(project)
    area = _model_area_m2(project) or _stated_area_m2(project)
    if not n or not area:
        return []

    per = area / n
    out: List[Conflict] = []
    base_evidence = (f"{n} 人 ÷ 可用 {area:.1f}㎡ = 人均 {per:.1f}㎡（含交通与辅助，"
                     "经验区间，不是法规指标）")

    if per < 4.0:
        out.append(Conflict(
            id="F-CAP-01", category="capacity",
            problem=f"{n} 个人放进 {area:.0f}㎡ 明显装不下（人均仅 {per:.1f}㎡）",
            evidence=base_evidence,
            affected="工位数量、会议室、通行与消防疏散",
            severity="blocker",
            recommendation="先解决容量矛盾，再谈风格与效果",
            alternatives=[
                f"减少常驻人数到 {int(area / 6)} 人左右（人均 6㎡ 的紧凑口径）",
                "改用轮用工位/混合办公，按同时在座人数而非编制人数设计",
                "换更大场地，或把会议、接待移到共享空间",
            ],
            needs_human=True,
            blocks_stage="S2",
        ))
    elif per < 6.0:
        out.append(Conflict(
            id="F-CAP-02", category="capacity",
            problem=f"人均 {per:.1f}㎡ 偏紧，只能做紧凑布局",
            evidence=base_evidence,
            affected="工位尺寸、会议与专注空间的取舍",
            severity="major",
            recommendation="明确取舍：要么压缩会议/接待，要么减少固定工位",
            alternatives=["用轮用工位释放面积", "把大会议改为两间小会议室"],
            needs_human=True,
        ))
    elif per > 12.0:
        out.append(Conflict(
            id="F-CAP-04", category="capacity",
            problem=f"人均 {per:.1f}㎡ 偏宽裕，可按品质型办公规划",
            evidence=base_evidence,
            affected="可增加会议、专注间与休闲区",
            severity="info",
            recommendation="余量优先给会议与专注空间，而不是放大工位",
        ))

    # 会议位：经验值 1 间 / 12–15 人
    meetings = [p for p in (project.program or [])
                if str(p.get("recipe") or "") in ("meeting", "boardroom")]
    need_rooms = max(1, round(n / 15))
    if len(meetings) < need_rooms:
        out.append(Conflict(
            id="F-CAP-03", category="capacity",
            problem=f"会议位偏少：{n} 人只有 {len(meetings)} 间会议空间",
            evidence=f"经验配置约每 12–15 人 1 间；{n} 人至少需要 {need_rooms} 间",
            affected="会议排队与电话间占用",
            severity="major",
            recommendation="补会议/电话间，或明确采用共享会议策略",
            alternatives=["把大空间拆成 2 间小会议", "设置 2–3 个电话亭替代部分会议需求"],
        ))
    return out


# --------------------------------------------------------------------------
# 2. behaviour vs spatial conditions
# --------------------------------------------------------------------------
def _check_behavior(project: Project) -> List[Conflict]:
    out: List[Conflict] = []
    matrix = build_need_matrix(project)
    rows = matrix["rows"]
    acts = " ".join(r["activity"] for r in rows)

    if "聚餐" in acts:
        big = max((r.get("headcount") or 0) for r in rows if "聚餐" in r["activity"])
        if big >= 8:
            out.append(Conflict(
                id="F-BEH-01", category="behavior",
                problem="多人聚餐与日常起居共用同一空间，需要两种布置同时成立",
                evidence=f"需求中出现 {big} 人聚餐；同时存在日常起居用途",
                affected="客厅/餐厅的尺度与家具布置",
                severity="major",
                recommendation="明确聚餐频率：高频则固定大餐桌，低频则用可扩展桌并保留通行宽度",
                alternatives=["固定 8 人桌 + 日常靠墙使用", "两张可拼合桌", "餐厨一体化放大用餐区"],
                needs_human=True,
            ))
        elif big >= 6:
            out.append(Conflict(
                id="F-BEH-02", category="behavior",
                problem="6 人以上用餐时通行与座位需要同时校核",
                evidence=f"需求中出现 {big} 人聚餐",
                affected="餐厅与相邻通道",
                severity="minor",
                recommendation="按坐姿占位 + 后撤通行同时校核，不要只看桌子尺寸",
            ))

    if "居家办公" in acts or "专注" in acts:
        has_study = any("study" in str(p.get("recipe") or "") for p in project.program or [])
        if not has_study:
            out.append(Conflict(
                id="F-BEH-03", category="behavior",
                problem="需要安静工作，但没有可关闭的独立空间",
                evidence="需求含居家办公/专注用途；program 中没有独立书房或可闭合房间",
                affected="专注工作的可行性",
                severity="major",
                recommendation="设可闭合的独立空间，或把工作位放到卧室区并处理隔声",
                alternatives=["书房兼客房（折叠床）", "主卧内设工作位 + 隔声门", "客厅角部用柜体围合"],
                needs_human=True,
            ))

    if "照护" in acts or "无障碍" in acts:
        out.append(Conflict(
            id="F-BEH-04", category="behavior",
            problem="存在照护/无障碍需求，但净宽与扶手预埋尚未进入条件",
            evidence="需求中识别到老人或照护用途",
            affected="门洞净宽、卫浴做法、夜间照明",
            severity="major",
            recommendation="在平面阶段就按无障碍净宽校核，卫浴墙体预留扶手基层",
            alternatives=["拆分为可独立使用的老人房套间"],
            needs_human=True,
        ))

    # Household size vs bathroom count — a classic that only surfaces on day one.
    household = _answer(project, "res.household")
    if household:
        import re

        people = 0
        m = re.search(r"(\d+)\s*(?:口|人)", household)
        if m:
            people = int(m.group(1))
        baths = len([s for s in project.spaces if "bath" in (s.use or "").lower()])
        if people >= 4 and baths and baths < 2:
            out.append(Conflict(
                id="F-BEH-05", category="behavior",
                problem="常住人数与卫生间数量不匹配",
                evidence=f"常住约 {people} 人，模型内卫生间 {baths} 个",
                affected="早晚高峰使用与私密性",
                severity="major",
                recommendation="按早晚高峰同时使用校核；不足时增设客卫或做干湿分离的双盆",
                alternatives=["主卫 + 客卫", "双盆 + 独立马桶间的单卫"],
                needs_human=True,
            ))
    return out


# --------------------------------------------------------------------------
# 3. budget vs ambition
# --------------------------------------------------------------------------
def _budget_from_text(text: str) -> float:
    """Parse "硬装 80 万" / "1,200,000 元" into CNY. 0.0 when absent."""
    import re

    if not text:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", text)
    if m:
        try:
            return float(m.group(1)) * 10000.0
        except ValueError:
            return 0.0
    m = re.search(r"(\d[\d,\.]{2,})\s*(?:元|块|rmb|cny)", text, re.I)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return 0.0
    return 0.0


def _check_budget(project: Project) -> List[Conflict]:
    out: List[Conflict] = []
    cons = _constraints(project)
    budget = cons.get("budget_cny")
    try:
        budget = float(budget) if budget else 0.0
    except (TypeError, ValueError):
        budget = 0.0
    if not budget:
        budget = _budget_from_text(_answer(project, "base.budget"))
    area = _model_area_m2(project) or _stated_area_m2(project)
    band_key = str(cons.get("cost_band") or "standard")
    low, high = COST_BAND_CNY_PER_M2.get(band_key, COST_BAND_CNY_PER_M2["standard"])

    if not budget:
        out.append(Conflict(
            id="F-BUD-00", category="budget",
            problem="预算口径未定，无法判断目标与投入是否匹配",
            evidence="未获得预算金额，也未说明包含范围",
            affected="材料档次、造型复杂度、设备配置",
            severity="info",
            recommendation="先定金额 + 包含范围（硬装 / 软装 / 家电 / 设计费），再谈档次",
            alternatives=["按单位造价区间反推：面积 × 区间 = 可承受总额"],
            needs_human=True,
        ))
        return out

    if area <= 0:
        out.append(Conflict(
            id="F-BUD-01", category="budget",
            problem="预算已给，但面积未知，无法换算单位造价",
            evidence=f"预算 {budget:,.0f} CNY；可用面积未知",
            affected="投入强度判断",
            severity="info",
            recommendation="确认面积后再判断；在此之前只能按总额讨论范围",
            needs_human=True,
        ))
        return out

    per_m2 = budget / area
    if per_m2 < low * 0.8:
        out.append(Conflict(
            id="F-BUD-02", category="budget",
            problem="预算明显低于目标档次所需投入",
            evidence=(f"{budget:,.0f} CNY ÷ {area:.1f} m² = {per_m2:,.0f} 元/m²；"
                      f"参考区间 {low:,.0f}–{high:,.0f} 元/m²（{band_key} 档，"
                      f"规划参考值，非报价）"),
            affected="材料档次、造型复杂度、定制家具比例",
            severity="blocker",
            recommendation="先定取舍：降档次、缩范围，还是追加预算——三者必须选一个",
            alternatives=["减少定制、提高成品比例", "缩小设计范围（如先做公区）",
                          "保留结构造型，降低表面材料档次"],
            needs_human=True,
            blocks_stage="S2",
        ))
    elif per_m2 < low:
        out.append(Conflict(
            id="F-BUD-03", category="budget",
            problem="预算处于目标档次下沿，做法需要克制",
            evidence=(f"{per_m2:,.0f} 元/m² vs 参考区间 {low:,.0f}–{high:,.0f} 元/m²"
                      f"（规划参考值）"),
            affected="材料与节点选择",
            severity="major",
            recommendation="把预算集中在高频接触面（台面、地面、五金），其余用克制做法",
            alternatives=["减少造型、增加留白", "用灯光而非材料提升质感"],
        ))
    else:
        out.append(Conflict(
            id="F-BUD-04", category="budget",
            problem="预算与目标档次基本匹配",
            evidence=f"{per_m2:,.0f} 元/m² 落在参考区间 {low:,.0f}–{high:,.0f} 元/m² 内",
            affected="无",
            severity="info",
            recommendation="注意口径：以上为规划参考区间，实际造价须以当地报价为准",
        ))
    return out


# --------------------------------------------------------------------------
# 4. schedule / approvals vs scope
# --------------------------------------------------------------------------
def _check_schedule(project: Project) -> List[Conflict]:
    out: List[Conflict] = []
    depth = _answer(project, "base.deliverable_depth") or str(
        _constraints(project).get("deliverable_depth") or "")
    schedule = _answer(project, "base.schedule") or str(
        _constraints(project).get("schedule") or "")
    import re

    weeks = 0
    m = re.search(r"(\d{1,2})\s*(?:周|个星期)", schedule or "")
    if m:
        weeks = int(m.group(1))
    months = re.search(r"(\d{1,2})\s*(?:个)?月", schedule or "")
    if not weeks and months:
        weeks = int(months.group(1)) * 4

    needs_drawings = any(k in depth for k in ("施工图", "全流程"))
    if needs_drawings and weeks and weeks < 8:
        out.append(Conflict(
            id="F-SCH-01", category="schedule",
            problem="交付深度含施工图，但周期不足以完成深化与审图",
            evidence=f"目标周期约 {weeks} 周；交付深度「{depth}」",
            affected="施工图质量与现场变更量",
            severity="major",
            recommendation="要么延长周期，要么缩小首期交付范围（先出方案 + 关键节点）",
            alternatives=["分期交付：先方案与主要节点，施工图后补", "增加绘图资源并锁定确认节奏"],
            needs_human=True,
        ))
    if any(s in (project.name or "") for s in ("新建", "自建")) or _answer(
            project, "arc.approval"):
        approval = _answer(project, "arc.approval") or "未说明"
        out.append(Conflict(
            id="F-SCH-02", category="schedule",
            problem="涉及报批，报批状态未知或未完成，会直接限制设计深度",
            evidence=f"报批状态：{approval}",
            affected="S7 施工图与报审",
            severity="major" if "已" in approval else "blocker",
            recommendation="确认立项 / 规划许可 / 施工许可的实际状态，再排设计节奏",
            alternatives=["先做方案与报批配合图，施工图待许可后启动"],
            needs_human=True,
            blocks_stage="" if "已" in approval else "S7",
        ))
    return out


# --------------------------------------------------------------------------
# 5. existing building and services
# --------------------------------------------------------------------------
def _check_technical(project: Project) -> List[Conflict]:
    out: List[Conflict] = []
    items = uncertainty_register(project)
    structural_open = any(i.get("topic") == "structural" and i.get("open") for i in items)
    services_open = any(i.get("topic") == "services" and i.get("open") for i in items)
    inferred_walls = [e for e in project.elements
                      if e.type == "wall" and e.uncertain]

    if structural_open or inferred_walls:
        n = len(inferred_walls)
        out.append(Conflict(
            id="F-TEC-01", category="technical",
            problem="承重与结构条件未证实，拆改范围无法判断",
            evidence=(f"不确定登记中有结构项；模型内 {n} 段墙体为推断所得"
                      if n else "不确定登记中有结构项"),
            affected="能否拆墙、能否开门洞、能否加层",
            severity="blocker",
            recommendation="现场探测或取原设计单位确认后，再决定拆改；在此之前只做非结构方案",
            alternatives=["保留现有墙体做表面处理", "用轻质隔断调整而不动结构"],
            needs_human=True,
            blocks_stage="S4",
        ))
    if services_open:
        out.append(Conflict(
            id="F-TEC-02", category="technical",
            problem="机电条件未确认，净高与点位存在返工风险",
            evidence="不确定登记中有机电/设备项，或缺少机电资料",
            affected="吊顶净高、点位布置、设备容量",
            severity="major",
            recommendation="先取得机电现状资料或现场核查，再锁定天花与设备方案",
            alternatives=["采用明装或局部吊顶，减少对净高的依赖"],
            needs_human=True,
        ))
    lvl_height = project.levels[0].height_mm if project.levels else 0.0
    if lvl_height and lvl_height < 2600:
        out.append(Conflict(
            id="F-TEC-03", category="technical",
            problem="层高偏低，吊顶与地暖会进一步压缩净高",
            evidence=f"模型层高 {lvl_height:.0f} mm",
            affected="净高、空调形式、灯具选型",
            severity="major",
            recommendation="按净高倒推：先定净高目标，再选空调形式与吊顶做法",
            alternatives=["局部吊顶藏设备，其余保留原顶", "明装风管机或壁挂式方案"],
        ))
    return out


# --------------------------------------------------------------------------
def run_feasibility(project: Project) -> Dict[str, Any]:
    """Run all five families and return a ranked, evidenced verdict."""
    conflicts: List[Conflict] = []
    for fn in (_check_area, _check_area_basis, _check_capacity,
               _check_behavior, _check_budget, _check_schedule, _check_technical):
        try:
            conflicts.extend(fn(project))
        except Exception as exc:  # a check must never take S1 down
            conflicts.append(Conflict(
                id=f"F-ERR-{fn.__name__}", category="technical",
                problem=f"检查未完成：{type(exc).__name__}",
                evidence=str(exc)[:200],
                affected="该项可行性结论",
                severity="info",
                recommendation="补齐数据后重跑该项检查",
                needs_human=True,
            ))

    order = {s: i for i, s in enumerate(CONFLICT_SEVERITIES)}
    conflicts.sort(key=lambda c: (order.get(c.severity, 9), c.id))
    blockers = [c for c in conflicts if c.severity == "blocker"]
    majors = [c for c in conflicts if c.severity == "major"]
    if blockers:
        verdict = "not_feasible_yet"
        headline = "存在阻断项：需先解决取舍，才能承诺当前需求可行"
    elif majors:
        verdict = "feasible_with_conditions"
        headline = "可行，但有重要条件需在概念阶段解决"
    else:
        verdict = "feasible"
        headline = "按现有信息未发现结构性冲突"
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "generated_at": _now(),
        "verdict": verdict,
        "headline": headline,
        "conflicts": [c.to_dict() for c in conflicts],
        "area_basis": _area_basis(project),
        "headcount": _headcount(project),
        "counts": {
            "blocker": len(blockers), "major": len(majors),
            "minor": len([c for c in conflicts if c.severity == "minor"]),
            "info": len([c for c in conflicts if c.severity == "info"]),
        },
        "blocked_stages": sorted({c.blocks_stage for c in conflicts if c.blocks_stage}),
        "note": ("造价与工期结论均为规划参考区间，不是报价与承诺；"
                 "结构、消防、无障碍与法规符合性须由持证专业人员在项目所在地复核。"),
    }


def markdown(result: Dict[str, Any]) -> str:
    """Human-readable feasibility report."""
    lines = [f"**结论：{result['headline']}**", "",
             "| 类别 | 严重度 | 问题 |", "|---|---|---|"]
    for c in result["conflicts"]:
        lines.append(f"| {c['category_label']} | {c['severity_label']} | {c['problem']} |")
    lines += ["", "## 逐项说明", ""]
    for c in result["conflicts"]:
        lines += [f"### {c['id']}　{c['problem']}", "",
                  f"- **类别 / 严重度**：{c['category_label']} / {c['severity_label']}",
                  f"- **事实依据**：{c['evidence']}",
                  f"- **受影响的需求**：{c['affected']}",
                  f"- **建议方向**：{c['recommendation']}"]
        if c["alternatives"]:
            lines.append("- **可替代方案**：")
            lines += [f"  - {a}" for a in c["alternatives"]]
        lines.append(f"- **需要人工审核**：{'是' if c['needs_human'] else '否'}"
                     + (f"　**阻断阶段**：{c['blocks_stage']}" if c["blocks_stage"] else ""))
        lines.append("")
    lines += ["> " + result["note"], ""]
    return "\n".join(lines)
