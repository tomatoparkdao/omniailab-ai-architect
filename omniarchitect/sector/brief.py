"""行业输入：把 S1 说过的话整理成能算的数，并指出还缺什么。

这一层**不设计**，只做三件事：

1. 从客户原话里抽取可用的量（班数、床位、客房数、柱网、用地……），
   每一个都记下它来自哪句话——没有出处的数不许进设计；
2. 由这些量推出该类型的基本盘（面积需求、层数需求、后场比例……）；
3. 把"数据之间对不上"的地方写成设计矛盾。矛盾才是推敲的起点：
   只说"公共面开放、后勤面收实"，任何公共建筑都成立，也就什么也没说。

缺输入时不猜：写进 `missing`，由 S2 明确告诉客户"要补什么才能继续推"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# 类型 -> 行业（决定用哪套量纲与默认值）
# --------------------------------------------------------------------------
SECTOR_OF: Dict[str, str] = {
    "A3": "education",
    "A4": "healthcare",
    "A12": "industrial", "A13": "industrial",
    "A6": "hospitality", "B4": "hospitality",
    "A5": "retail",
    "A1": "housing",
    "A2": "office", "B3": "office",
    "B1": "housing", "B2": "housing", "B6": "retail", "B7": "education",
    "B10": "culture", "B11": "public", "B12": "industrial",
    "C1": "landscape", "C2": "landscape", "C3": "landscape", "C4": "landscape",
    "C5": "landscape", "C6": "landscape", "C7": "landscape", "C8": "landscape",
    "C9": "landscape",
    "B5": "food", "B8": "healthcare", "B9": "leisure", "B10": "culture",
    "B11": "public", "B12": "industrial",
}

SECTOR_LABELS = {
    "education": "教育", "healthcare": "医疗", "industrial": "工业",
    "hospitality": "酒店与住宿", "landscape": "景观", "retail": "商业零售",
    "housing": "住宅", "office": "办公", "food": "餐饮", "leisure": "娱乐",
    "culture": "文化展陈", "public": "公共与交通", "generic": "未归类",
}

#: 每个行业的必需输入：(键, 中文名, 缺了会怎样)
NEEDS: Dict[str, Tuple[Tuple[str, str, str], ...]] = {
    "education": (
        ("classes", "班数与学制", "算不出教室数量、专用教室配比与食堂批次"),
        ("students", "学生人数", "算不出食堂座位、厕所洁具与疏散宽度"),
    ),
    "healthcare": (
        ("beds", "床位规模", "算不出住院部面积、电梯与竖向分区"),
        ("outpatient", "日门诊量", "算不出门诊单元数量与候诊面积"),
    ),
    "industrial": (
        ("process", "生产工艺顺序", "排不出厂房内部流程与物流方向"),
        ("grid", "柱网与设备尺寸", "定不了跨度、层高与设备基础"),
    ),
    "hospitality": (
        ("keys", "客房数", "算不出客房层数、布草量与竖向交通"),
    ),
    "landscape": (
        ("site_area", "场地面积", "算不出分区占比与容量"),
    ),
    "retail": (("site_area", "建筑面积", "算不出业态配比与客流组织"),),
    "office": (("area", "使用面积", "算不出工位与会议室配比"),),
    "housing": (("area", "套内面积", "算不出房间尺度"),),
    "food": (("seats", "座位数", "算不出前场与后场比例"),),
    "leisure": (("area", "经营面积", "算不出包间与公共区配比"),),
}


# --------------------------------------------------------------------------
# 抽取
# --------------------------------------------------------------------------
_NUM = r"(\d+(?:\.\d+)?)"
PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("classes", _NUM + r"\s*(?:个)?班"),
    ("students", _NUM + r"\s*(?:名|位|个)?\s*(?:学生|孩子|幼儿)"),
    ("per_class", r"每班\s*" + _NUM),
    ("beds", _NUM + r"\s*(?:张)?床"),
    ("outpatient", r"(?:日?门诊(?:量)?|门诊人数)\s*" + _NUM),
    ("keys", _NUM + r"\s*(?:间)?\s*客房"),
    ("rooms", _NUM + r"\s*(?:间)?\s*(?:房间|包间|诊室)"),
    ("seats", _NUM + r"\s*(?:个)?\s*(?:座位|餐位)"),
    ("site_area", r"用地\s*" + _NUM + r"\s*(?:亩|平方米|平米|㎡|m2)"),
    ("area", _NUM + r"\s*(?:平方米|平米|㎡|m2|㎡)"),
    ("floors", _NUM + r"\s*层"),
    ("shifts", _NUM + r"\s*(?:班|批)\s*(?:制|供餐)"),
)
GRID_RE = re.compile(r"柱网\s*" + _NUM + r"\s*(?:m|米)?\s*[x×*]\s*" + _NUM)
MU_RE = re.compile(r"用地\s*" + _NUM + r"\s*亩")
PROCESS_WORDS = ("原料", "下料", "加工", "装配", "检测", "包装", "入库", "出货",
                 "洁净", "无尘", "防爆", "冷库", "月台", "卸货")
CARE_WORDS = ("手术", "ICU", "重症", "影像", "CT", "核磁", "检验", "病理", "产科",
              "儿科", "感染", "负压", "透析", "急诊", "发热")
EDU_WORDS = ("小学", "初中", "高中", "九年一贯", "幼儿园", "托育", "职校", "完中")
HOTEL_WORDS = ("大堂", "宴会", "会议", "SPA", "泳池", "行政酒廊", "全日餐厅",
               "中餐厅", "后勤", "布草")


@dataclass
class SectorBrief:
    """一个项目的行业输入与由它推出的事实。"""

    sector: str = "generic"
    sector_label: str = ""
    codes: List[str] = field(default_factory=list)
    primary: str = ""
    discipline: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    sources: Dict[str, str] = field(default_factory=dict)
    #: 由输入推出的事实（带算式），S2 的说明与 S3 的任务书都读这里
    facts: List[Dict[str, str]] = field(default_factory=list)
    quant: Dict[str, float] = field(default_factory=dict)
    #: 数据之间对不上的地方 —— 推敲要解决的正是这些
    tensions: List[str] = field(default_factory=list)
    #: 还缺什么输入；每条都说明"缺了会怎样"
    missing: List[str] = field(default_factory=list)
    #: 用到的默认值（写进报告，避免把假设当条件）
    assumptions: List[str] = field(default_factory=list)
    ancillary: List[Dict[str, str]] = field(default_factory=list)
    #: 客户原话里的关键词（工艺、专科、酒店功能区…），不是猜的
    signals: Dict[str, List[str]] = field(default_factory=dict)

    def get(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.quant.get(key, default) or default)
        except (TypeError, ValueError):
            return default

    @property
    def has_data(self) -> bool:
        return bool(self.inputs) or bool(self.quant)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector": self.sector,
            "sector_label": self.sector_label,
            "codes": list(self.codes),
            "primary": self.primary,
            "discipline": self.discipline,
            "inputs": dict(self.inputs),
            "sources": dict(self.sources),
            "facts": [dict(f) for f in self.facts],
            "quant": {k: round(v, 2) for k, v in self.quant.items()},
            "tensions": list(self.tensions),
            "missing": list(self.missing),
            "assumptions": list(self.assumptions),
            "ancillary": [dict(a) for a in self.ancillary],
            "signals": {k: list(v) for k, v in self.signals.items()},
        }


def sector_of(codes: Sequence[str]) -> str:
    for code in codes:
        if code in SECTOR_OF:
            return SECTOR_OF[code]
    return "generic"


def _text_of(ctx: Any) -> str:
    parts = [str(getattr(ctx, "name", "") or "")]
    for key in ("project_type", "needs", "site_conditions", "structure", "feeling"):
        v = (getattr(ctx, "answers", {}) or {}).get(f"base.{key}")
        if v:
            parts.append(str(v))
    for v in (getattr(ctx, "answers", {}) or {}).values():
        if v:
            parts.append(str(v))
    return " ".join(parts)


def _first(text: str, key: str) -> Optional[float]:
    if key == "site_area":
        mu = MU_RE.search(text)
        if mu:
            return float(mu.group(1)) * 666.67
    if key == "grid":
        g = GRID_RE.search(text)
        return None
    for name, pattern in PATTERNS:
        if name != key:
            continue
        m = re.search(pattern, text)
        if m:
            return float(m.group(1))
    return None


def _quantities(brief: SectorBrief, text: str) -> None:
    """按行业把输入推成设计要用的量。每个结论都写进 facts。"""
    s = brief.sector
    inp = brief.inputs

    def fact(label: str, value: str, formula: str = "") -> None:
        brief.facts.append({"label": label, "value": value, "formula": formula})

    if s == "education":
        classes = float(inp.get("classes") or 0)
        per = float(inp.get("per_class") or (30 if "幼儿园" in text or "托育" in text
                                             else 45))
        if classes and "per_class" not in inp:
            brief.assumptions.append(f"每班人数按 {per:.0f} 人计（客户未给班额）")
        students = float(inp.get("students") or classes * per)
        teaching = classes * 65.0
        special = max(2.0, math.ceil(classes / 4.0)) * 90.0
        office = max(60.0, classes * 2.5 * 6.0)
        canteen = 0.0
        if any(a["label"] == "学生食堂" for a in brief.ancillary) or "食堂" in text:
            seats = students * 0.6
            batches = float(inp.get("shifts") or 2)
            canteen = seats / max(batches, 1.0) * 1.1
            fact("食堂面积", f"{canteen:,.0f} m²",
                 f"{students:,.0f} 人 × 60% 同时就餐 ÷ {batches:.0f} 批 × 1.1 m²/座")
        gym = 0.0
        if any(a["label"] == "校园体育馆" for a in brief.ancillary) or "体育馆" in text:
            gym = max(800.0, classes * 24.0)
            fact("体育馆面积", f"{gym:,.0f} m²",
                 f"按 {classes:.0f} 班排课取 {classes * 24:.0f} m²（不含看台）")
        corridor = (teaching + special) * 0.28
        total = teaching + special + office + canteen + gym + corridor
        brief.quant.update({"classes": classes, "students": students,
                            "teaching_m2": teaching, "special_m2": special,
                            "office_m2": office, "canteen_m2": canteen,
                            "gym_m2": gym, "corridor_m2": corridor,
                            "building_m2": total,
                            "footprint_m2": total / max(float(inp.get("floors") or 3), 1)})
        fact("普通教室", f"{classes:.0f} 间 / {teaching:,.0f} m²", f"{classes:.0f} 班 × 65 m²")
        fact("专用教室", f"{math.ceil(classes / 4.0):.0f} 间 / {special:,.0f} m²",
             "每 4 班配 1 间，90 m²/间")
        fact("学生规模", f"{students:,.0f} 人", f"{classes:.0f} 班 × {per:.0f} 人")
        fact("总建筑面积（估）", f"{total:,.0f} m²", "教学 + 专用 + 办公 + 配套 + 走廊 28%")
        site = float(inp.get("site_area") or 0)
        if site:
            footprint = total / max(float(inp.get("floors") or 3), 1)
            far = total / site
            cover = footprint / site
            brief.quant.update({"site_area": site, "far": far, "coverage": cover})
            fact("容积率 / 建筑密度", f"{far:.2f} / {cover:.0%}",
                 f"{total:,.0f} m² ÷ {site:,.0f} m²；底层 {footprint:,.0f} m²")
            if far > 1.2:
                brief.tensions.append(
                    f"容积率 {far:.2f} 高于中小学校园常见区间（0.8–1.2）："
                    f"{total:,.0f} m² 的建筑量压在 {site:,.0f} m² 用地上，"
                    "操场与消防车道会互相挤占，须先决定竖向策略")
            elif far < 0.6:
                brief.tensions.append(
                    f"容积率仅 {far:.2f}：用地相对宽裕，方案应优先横向展开、"
                    "把操场与教学区分开，而不是盖高")
            if cover > 0.30:
                brief.tensions.append(
                    f"建筑密度 {cover:.0%} 偏高：可绿化的地面被压到 "
                    f"{max(0.0, site - footprint):,.0f} m²，校园活动场地要靠屋顶或架空补")

    elif s == "healthcare":
        beds = float(inp.get("beds") or 0)
        outpatient = float(inp.get("outpatient") or 0)
        if beds:
            total = beds * 90.0
            outpatient_a = total * 0.18
            tech = total * 0.27
            ward = total * 0.40
            support = total * 0.12
            admin = total * 0.03
            ors = max(2.0, round(beds / 50.0))
            icu = max(4.0, round(beds * 0.03))
            brief.quant.update({"beds": beds, "outpatient": outpatient,
                                "building_m2": total, "outpatient_m2": outpatient_a,
                                "tech_m2": tech, "ward_m2": ward,
                                "support_m2": support, "admin_m2": admin,
                                "ors": ors, "icu_beds": icu})
            fact("总建筑面积（估）", f"{total:,.0f} m²", f"{beds:.0f} 床 × 90 m²/床")
            fact("门诊 / 医技 / 住院", f"{outpatient_a:,.0f} / {tech:,.0f} / {ward:,.0f} m²",
                 "按综合医院 18% / 27% / 40% 分区")
            fact("手术室与 ICU", f"{ors:.0f} 间 / {icu:.0f} 床", "每 50 床 1 间；ICU 取 3%")
        if outpatient:
            units = max(4.0, round(outpatient / 400.0))
            brief.quant.update({"opd_units": units,
                                "waiting_m2": outpatient * 0.35})
            fact("门诊单元与候诊", f"{units:.0f} 个单元 / {outpatient * 0.35:,.0f} m²",
                 f"日门诊 {outpatient:.0f} 人 ÷ 400 人/单元；候诊 0.35 m²/人次")
            if beds and outpatient / beds > 6:
                brief.tensions.append(
                    f"日门诊 {outpatient:.0f} 人对 {beds:.0f} 床，门诊压力高于常见配比（3–5 人/床）："
                    "门诊入口、挂号与候诊要独立成区，不能借用住院大厅")
        specials = [w for w in CARE_WORDS if w in text]
        if specials:
            brief.signals["specialties"] = specials
            brief.tensions.append(
                "客户提到 " + "、".join(specials) +
                "：这些单元的洁污与人物分流要求高于普通病房，须先定垂直分区再排平面")
        brief.tensions.append(
            "洁污分流不是一条走廊能解决的：污物、尸体、餐车与洁净供应需要独立竖向通道，"
            "平面上必须能在两端各留一部污物梯")
        brief.tensions.append(
            "本条不含医疗工艺与感控合规结论：手术部、ICU、产房、负压病房的流程须由"
            "医疗工艺顾问与院感部门确认")

    elif s == "industrial":
        area = float(inp.get("area") or 0)
        grid = GRID_RE.search(text)
        bay = 8.4
        if grid:
            bay = float(grid.group(1))
            brief.facts.append({"label": "柱网", "value": f"{grid.group(1)} × {grid.group(2)} m",
                                "formula": "客户指定"})
        else:
            brief.assumptions.append(f"柱网按 {bay:.1f} × {bay:.1f} m 假设（客户未给设备尺寸）")
        process = [w for w in PROCESS_WORDS if w in text]
        if process:
            brief.signals["process"] = process
        floors = float(inp.get("floors") or 1)
        if area:
            annex = area * 0.08
            docks = max(1.0, round(float(inp.get("shifts") or area / 3000.0)))
            brief.quant.update({"area": area, "annex_m2": annex,
                                "bays_x": math.ceil(math.sqrt(area) / bay),
                                "bays_y": math.ceil(area / (bay * math.ceil(math.sqrt(area) / bay)) / bay),
                                "docks": docks, "floors": floors, "bay": bay})
            fact("厂房面积", f"{area:,.0f} m²", "客户给定")
            fact("柱网与跨数", f"{bay:.1f} m；约 "
                 f"{brief.quant['bays_x']:.0f} × {max(1.0, brief.quant['bays_y']):.0f} 跨",
                 "按面积与柱网反算，须与工艺设备核对")
            fact("配套办公", f"{annex:,.0f} m²", "按厂房 8% 估")
            if "洁净" in text or "无尘" in text:
                brief.tensions.append(
                    "洁净区把工艺流线切成两段：人流、物料、废弃物必须三通道，"
                    "洁净走廊与非洁净区不能共用一扇门")
            if any(w in text for w in ("冷库", "冷链")):
                brief.tensions.append("冷链段要贴月台布置，否则保温距离与转运时间都会失控")
            if floors > 1:
                brief.tensions.append(
                    f"{floors:.0f} 层厂房：垂直运输（货梯/提升机）会成为产能瓶颈，"
                    "须先算清上下层之间的物流量再定层数")
            else:
                brief.tensions.append(
                    "单层厂房用地最省事但占地大：若用地紧张，须比较「单层大跨 + 卸货场」"
                    "与「两层 + 货梯」的总额，而不是默认单层")
            if not process:
                brief.missing.append("没有工艺顺序：厂房内部只能按通用流程排，须客户给工序与物流方向")

    elif s == "hospitality":
        keys = float(inp.get("keys") or 0)
        if keys:
            gfa = keys * 75.0
            guest = keys * 45.0
            public = gfa * 0.18
            boh = gfa * 0.15
            brief.quant.update({"keys": keys, "building_m2": gfa, "guest_m2": guest,
                                "public_m2": public, "boh_m2": boh,
                                "per_key_m2": 75.0})
            fact("总建筑面积（估）", f"{gfa:,.0f} m²", f"{keys:.0f} 间 × 75 m²/间")
            fact("客房 / 公共 / 后场", f"{guest:,.0f} / {public:,.0f} / {boh:,.0f} m²",
                 "客房 45 m²/间；公共 18%；后场 15%")
            fact("单房面积（含公摊）", "75 m²/间", "中高端城市酒店常见区间 65–90")
        zones = [w for w in HOTEL_WORDS if w in text]
        if zones:
            brief.signals["areas"] = zones
        brief.tensions.append(
            "后场不是「剩下塞进去」的面积：布草、员工、收货、垃圾四条流线与客人动线"
            "必须完全分开，电梯与走廊不能混用")
        if "既有" in text or "改造" in text or "精装" in text:
            brief.tensions.append(
                "既有建筑改造受柱网、管井与疏散宽度约束：客房开间一旦被结构定死，"
                "房型数量就跟着定死，方案只能在公共区与后场之间调")
        if not keys:
            brief.missing.append("没有客房数：算不出客房层数、布草量与竖向交通，只能给关系示意")

    elif s == "landscape":
        site = float(inp.get("site_area") or inp.get("area") or 0)
        if site:
            green = site * (0.45 if "庭院" in text else 0.35)
            paving = site * 0.30
            water = site * (0.08 if any(w in text for w in ("水景", "水池", "水")) else 0.0)
            brief.quant.update({"site_area": site, "green_m2": green,
                                "paving_m2": paving, "water_m2": water,
                                "green_ratio": green / site,
                                "water_ratio": water / site})
            fact("绿地 / 铺装 / 水面", f"{green:,.0f} / {paving:,.0f} / {water:,.0f} m²",
                 f"按场地 {site:,.0f} m²；绿地 {green / site:.0%}")
            if water / site > 0.12:
                brief.tensions.append(
                    f"水面占 {water / site:.0%}：夏季维护与冬季观感都会成为负担，"
                    "须明确补水、循环与清淤方式")
            if "儿童" in text or "小孩" in text:
                brief.tensions.append("有儿童使用：水景深度、岸线与铺装防滑须按儿童安全先定，再谈构图")
            if any(w in text for w in ("好维护", "少打理", "省心")):
                brief.tensions.append("业主要求低维护：种植须以乡土、耐修剪为主，水景不宜大面积")

    elif s == "retail":
        area = float(inp.get("area") or 0)
        if area:
            brief.quant.update({"area": area, "circulation_m2": area * 0.35,
                                "tenant_m2": area * 0.60})
            fact("可租 / 公共交通", f"{area * 0.6:,.0f} / {area * 0.35:,.0f} m²",
                 "按建筑面积的 60% / 35% 估，主力店另计")

    elif s in ("office", "housing", "food", "leisure"):
        area = float(inp.get("area") or 0)
        if area:
            brief.quant.update({"area": area})

    # 缺什么
    for key, label, consequence in NEEDS.get(s, ()):
        if key in inp or key in brief.quant:
            continue
        brief.missing.append(f"缺{label}：{consequence}")


def build(ctx: Any) -> SectorBrief:
    """从 S2 上下文整理出行业输入。没有可用数据时返回空 brief，不编。"""
    tax = dict(getattr(ctx, "taxonomy", {}) or {})
    codes = [str(c) for c in (getattr(ctx, "taxonomy_codes", ()) or tax.get("codes") or [])]
    text = _text_of(ctx)
    brief = SectorBrief(
        sector=sector_of(codes),
        sector_label=SECTOR_LABELS.get(sector_of(codes), ""),
        codes=codes,
        primary=codes[0] if codes else "",
        discipline=str(getattr(ctx, "lead_id", "") or ""),
        ancillary=[dict(a) for a in (tax.get("ancillary") or [])],
    )
    # 抽数不看行业：先把这个项目提到的所有量都取出来，再由行业决定用哪些。
    # 只按 NEEDS 抽会漏掉"厂房 12000 平方米"里的面积——它不在工业的必需项里，
    # 但排程序必须用它。
    for key, _pattern in PATTERNS:
        value = _first(text, key)
        if value is None:
            continue
        brief.inputs.setdefault(key, value)
        brief.sources.setdefault(key, "客户原话")
    grid = GRID_RE.search(text)
    if grid:
        brief.inputs["grid_x"] = float(grid.group(1))
        brief.inputs["grid_y"] = float(grid.group(2))
        brief.inputs.setdefault("grid", float(grid.group(1)))
        brief.sources["grid"] = "客户原话"
    # 景观与庭院常只说"800 平方米院子"，没有"用地"二字：当成场地面积用。
    if brief.sector == "landscape" and "site_area" not in brief.inputs \
            and "area" in brief.inputs:
        brief.inputs["site_area"] = brief.inputs["area"]
        brief.sources["site_area"] = brief.sources.get("area", "客户原话")
    # 面积：优先客户给的可用面积
    if "area" not in brief.inputs and getattr(ctx, "area_available_m2", None):
        brief.inputs["area"] = float(ctx.area_available_m2)
        brief.sources["area"] = "S1 记录的面积"
    if getattr(ctx, "program", None) and "area" in brief.inputs:
        pass
    for w in EDU_WORDS:
        if w in text:
            brief.signals.setdefault("stage", []).append(w)
    if not brief.codes:
        brief.missing.append("未识别项目类型：先确认这是建筑、室内还是景观项目")
        return brief
    _quantities(brief, text)
    return brief


def from_project(project: Any) -> SectorBrief:
    """从项目本身（S3 用的就是它）整理输入，口径与 S2 完全一致。

    S2 用 `ConceptContext`，S3 手里只有 `Project`。两处都走 `build()`，
    只是喂给它的字段来源不同——不允许 S3 另写一份解析。
    """
    from types import SimpleNamespace

    from .. import taxonomy as _tx
    from ..intake import interview as _iv

    tax = _iv.classification(project)
    raw_answers = dict((_iv.load_interview(project).answers or {}))
    answers = {str(k): str((v or {}).get("value") or "") for k, v in raw_answers.items()}
    lead = str(((getattr(project, "meta", {}) or {}).get("leadership") or {})
               .get("project_lead_discipline")
               or ((getattr(project, "meta", {}) or {}).get("leadership") or {}).get("lead")
               or "")
    if not lead:
        spec = _tx.resolve(str((tax.get("codes") or [""])[0]))
        lead = spec.discipline if spec else "architecture"
    constraints = dict(getattr(project, "constraints", {}) or {})
    area = constraints.get("area_m2") or constraints.get("area_available_m2")
    adapter = SimpleNamespace(
        name=project.name, taxonomy=tax,
        taxonomy_codes=tuple(tax.get("codes") or []),
        answers=answers, program=list(getattr(project, "program", []) or []),
        area_available_m2=float(area) if area else None,
        target_area_m2=0.0, lead_id=lead,
    )
    return build(adapter)


__all__ = ["NEEDS", "SECTOR_LABELS", "SECTOR_OF", "SectorBrief", "build", "from_project",
           "sector_of"]
