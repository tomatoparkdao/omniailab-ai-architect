"""按行业生成 S3 要排的房间与场地块。

面积不是拍的：每一个数都来自 `brief` 里算出来的量，并写进 `basis`。
S3 出图、面积表、G3 核验都读同一份 program——不允许"图上写一套、报告写另一套"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from .brief import SectorBrief


@dataclass
class ProgramRow:
    key: str
    name: str
    area_m2: float
    zone: str
    recipe: str
    priority: int = 50
    basis: str = ""
    #: 排布带：沿走廊的一条带（front/back，或厂房的多条带）
    band: str = "front"

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "name": self.name, "area_m2": round(self.area_m2, 1),
                "zone": self.zone, "recipe": self.recipe, "band": self.band,
                "priority": self.priority, "basis": self.basis}


@dataclass
class SectorProgram:
    """一套标准层（或单层）的房间清单 + 说明。"""

    rows: List[ProgramRow] = field(default_factory=list)
    unit: str = "标准层"
    note: str = ""
    corridor_width_mm: float = 2400.0
    bands: Tuple[str, ...] = ()
    #: 场地块（总平面用）。没有就不出总平面。
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, float] = field(default_factory=dict)

    def to_rows(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.rows]

    @property
    def area_m2(self) -> float:
        return sum(r.area_m2 for r in self.rows)


def _row(key: str, name: str, area: float, zone: str, recipe: str,
         priority: int = 50, basis: str = "", band: str = "front") -> ProgramRow:
    return ProgramRow(key=key, name=name, area_m2=max(1.0, area), zone=zone,
                      recipe=recipe, priority=priority, basis=basis, band=band)


# --------------------------------------------------------------------------
# 教育：一栋教学楼的标准层
# --------------------------------------------------------------------------
def _balance_per_floor(classes: float) -> int:
    """选"每层几班"，让教学带与后场带的长度尽量相等。

    两条带一样长，平面才是个完整的矩形；差太多时后场会剩一长条空白，
    图上看着像忘了排。这是排布问题，不是面积问题。
    """
    # 小学/中学常用 3–4 层：层数上限决定每层至少几班，不能为了"两条带一样长"
    # 把 24 班排成 6 层。
    per_min = max(4, int(math.ceil(max(classes, 1) / 4.0)))
    per_max = max(per_min, min(8, int(classes) if classes else 8))
    best, best_gap = per_min, 1e9
    for per in range(per_min, per_max + 1):
        special = max(1, math.ceil(per / 4.0))
        office = max(60.0, per * 2.5 * 6.0)
        service = 104.0
        front_w = per * 65.0 / 7.5
        back_w = (special * 90.0 + office + service) / 7.5
        gap = abs(front_w - back_w)
        if gap < best_gap:
            best, best_gap = per, gap
    return best


def education(b: SectorBrief, *, per_floor_classes: int = 0) -> SectorProgram:
    classes = b.get("classes")
    per = per_floor_classes or _balance_per_floor(classes)
    rows: List[ProgramRow] = []
    for i in range(per):
        rows.append(_row(f"T{i + 1:02d}", f"普通教室 {i + 1}", 65.0, "teaching",
                         "classroom", 20, "65 m²/班（含讲台与储藏）"))
    special = max(1, math.ceil(per / 4.0))
    for i in range(special):
        rows.append(_row(f"S{i + 1:02d}", f"专用教室 {i + 1}", 90.0, "special",
                         "study", 40, "每 4 班配 1 间，90 m²", band="back"))
    rows.append(_row("OF1", "教师办公", max(60.0, per * 2.5 * 6.0), "office",
                     "office_cell", 50, "每班 2.5 名教师 × 6 m²", band="back"))
    rows.append(_row("WC1", "卫生间（男）", 32.0, "service", "bathroom", 60,
                     "按学生数与学生洁具比", band="back"))
    rows.append(_row("WC2", "卫生间（女）", 40.0, "service", "bathroom", 60, "同上",
                     band="back"))
    rows.append(_row("ST1", "储藏与保洁", 18.0, "service", "storage", 70, "教学辅助",
                     band="back"))
    rows.append(_row("ST2", "配电与弱电", 14.0, "service", "storage", 75, "设备间",
                     band="back"))
    p = SectorProgram(
        rows=rows, unit="教学楼标准层",
        note=(f"本层排 {per} 班；全楼共 {math.ceil(classes / per) if classes else 1} 层，"
              f"其余楼层同构。食堂与体育馆作为独立体量在总平面另排。"),
        corridor_width_mm=3000.0,
        bands=("teaching", "special", "office", "service"),
        totals={"classes": classes, "per_floor": per,
                "floors": math.ceil(classes / per) if classes else 1},
    )
    total = b.get("building_m2")
    footprint = total / max(1.0, math.ceil(classes / per) if classes else 1)
    side = math.sqrt(max(footprint, 100.0) / 1.6)
    floors = b.get("floors") or _floors(b)
    p.blocks = [
        # 面积写总建筑面积，楼层单列：总图的容积率要的是总量，不是底层投影
        {"key": "teach", "name": "教学楼", "area_m2": footprint * floors,
         "floors": floors,
         "w": round(side * 1.6, 1), "d": round(side, 1), "kind": "building",
         "note": f"{floors:.0f} 层 × {footprint:,.0f} m²"},
    ]
    if b.get("canteen_m2"):
        p.blocks.append({"key": "canteen", "name": "学生食堂", "area_m2": b.get("canteen_m2"),
                         "w": 0, "d": 0, "kind": "building", "note": "单层，贴后勤入口"})
    if b.get("gym_m2"):
        p.blocks.append({"key": "gym", "name": "体育馆", "area_m2": b.get("gym_m2"),
                         "w": 0, "d": 0, "kind": "building", "note": "大跨，独立疏散"})
    site = b.get("site_area")
    if site:
        p.blocks.append({"key": "sport", "name": "运动场", "area_m2": min(site * 0.28, 4000.0),
                         "w": 0, "d": 0, "kind": "sport", "note": "200 m 环形跑道 + 球场"})
    return p


def _floors(b: SectorBrief) -> float:
    classes = b.get("classes") or 0
    return max(2.0, min(5.0, round(classes / 8.0) or 2.0))


# --------------------------------------------------------------------------
# 医疗：门诊医技层
# --------------------------------------------------------------------------
def healthcare(b: SectorBrief) -> SectorProgram:
    op = b.get("outpatient")
    units = b.get("opd_units") or max(4.0, round(op / 400.0))
    # 诊室数按"日门诊 ÷ 每诊室 40 人次"推：8 间诊室撑不起 1200 人次，
    # 那样排出来的平面会在诊室带尽头空出一大片，等于没做功能。
    # 但一层放不下全部诊室：本层按两条诊室带能排下的数量出图，其余交给相邻楼层。
    n_need = int(max(4, min(40, b.get("clinics") or round(op / 40.0))))
    n = min(n_need, 16)
    rows: List[ProgramRow] = []
    for i in range(n):
        rows.append(_row(f"O{i + 1:02d}", f"诊室 {i + 1}", 18.0, "outpatient",
                         "clinic", 20, "18 m²/间（一人一诊室）", band="front"))
    # 候诊按门诊单元分设：一处大候诊会让患者穿过整层去找自己的科室，
    # 也会在诊室带尽头留出一大块用不上的面积。
    n_wait = int(max(2, min(6, units)))
    for i in range(n_wait):
        rows.append(_row(f"WT{i + 1:02d}", f"候诊 {i + 1}", round(max(40.0, op * 0.35 / n_wait), 1),
                         "public", "waiting", 30,
                         f"0.35 m²/人次 ÷ {n_wait} 个门诊单元", band="public"))
    rows.append(_row("LB1", "门诊大厅", max(80.0, op * 0.12), "public", "hall", 25,
                     "入口集散、导医与收费", band="public"))
    rows.append(_row("TX1", "检验", 120.0, "tech", "lab", 40, "按医技 27% 中的检验部分",
                     band="back"))
    rows.append(_row("TX2", "影像（CT/DR）", 150.0, "tech", "lab", 40, "含屏蔽与设备荷载",
                     band="back"))
    rows.append(_row("TX3", "功能检查", 90.0, "tech", "clinic", 45, "超声/心电", band="back"))
    rows.append(_row("NS1", "护士站与治疗", 40.0, "tech", "office_cell", 35, "每个单元一处",
                     band="back"))
    rows.append(_row("WC1", "公共卫生间", 55.0, "service", "bathroom", 60, "含无障碍",
                     band="back"))
    rows.append(_row("ST1", "污物暂存", 16.0, "service", "storage", 70, "贴污物梯",
                     band="back"))
    rows.append(_row("ST2", "洁净物品库", 20.0, "service", "storage", 70, "贴洁梯",
                     band="back"))
    p = SectorProgram(
        rows=rows, unit="门诊医技层",
        note=(f"按日门诊 {op:,.0f} 人约需 {n_need} 间诊室，本层排 {n} 间，"
              f"其余 {max(0, n_need - n)} 间在相邻楼层（共用同一组竖向交通）；"
              f"手术部与 ICU 不在本层——"
              f"{b.get('ors', 0):.0f} 间手术室、{b.get('icu_beds', 0):.0f} 床 ICU 须独立成区，"
              "由医疗工艺顾问确认后另行展开。"),
        corridor_width_mm=2400.0,
        bands=("public", "front", "back"),
        totals={"rooms": n, "units": units},
    )
    total = b.get("building_m2")
    if total:
        side = math.sqrt(total * 0.45 / 1.6)
        p.blocks = [
            {"key": "podium", "name": "门诊医技裙房", "area_m2": total * 0.45,
             "w": round(side * 1.6, 1), "d": round(side, 1), "kind": "building",
             "note": "3 层，医技居中"},
            {"key": "tower", "name": "住院主楼", "area_m2": b.get("ward_m2"),
             "w": 0, "d": 0, "kind": "building", "note": f"{b.get('beds', 0):.0f} 床"},
            {"key": "emergency", "name": "急诊与发热门诊", "area_m2": total * 0.06,
             "w": 0, "d": 0, "kind": "building", "note": "独立出入口"},
        ]
    return p


# --------------------------------------------------------------------------
# 工业：单层厂房
# --------------------------------------------------------------------------
def industrial(b: SectorBrief) -> SectorProgram:
    area = b.get("area")
    annex = b.get("annex_m2")
    bay = b.get("bay", 8.4) or 8.4
    rows: List[ProgramRow] = [
        _row("PR1", "生产区", area * 0.62, "production", "workshop", 20,
             "按工艺设备排布，柱网 " + f"{bay:.1f} m", band="front"),
        _row("WH1", "原料库", area * 0.14, "warehouse", "storage", 30, "贴进货端",
             band="back"),
        _row("WH2", "成品库与发货", area * 0.14, "warehouse", "storage", 30, "贴出货端",
             band="back"),
        _row("OF1", "生产办公", annex * 0.5, "office", "office_cell", 40, "厂前区，独立出入口",
             band="back"),
        _row("OF2", "更衣与休息", annex * 0.3, "office", "office_cell", 45, "进入生产区前",
             band="back"),
        _row("SV1", "配电与空压", area * 0.03, "service", "storage", 60, "贴负荷中心",
             band="back"),
        _row("SV2", "卫生间", 40.0, "service", "bathroom", 60, "按在岗人数",
             band="back"),
    ]
    if "洁净" in " ".join(b.signals.get("process") or []) or b.get("clean"):
        rows.insert(1, _row("PR2", "洁净生产区", area * 0.18, "production", "workshop", 25,
                            "独立空调与压差，人物分流", band="front"))
    p = SectorProgram(
        rows=rows, unit="主厂房单层",
        note=(f"单层 {area:,.0f} m²，柱网 {bay:.1f} m；装卸位 {b.get('docks', 1):.0f} 个。"
              "设备基础、动力管沟、屋面排烟须工艺与结构专项出图。"),
        corridor_width_mm=3000.0,
        bands=("front", "back"),
        totals={"area": area, "bay": bay},
    )
    side = math.sqrt(max(area, 100.0) / 1.8)
    p.blocks = [
        {"key": "plant", "name": "主厂房", "area_m2": area,
         "w": round(side * 1.8, 1), "d": round(side, 1), "kind": "building",
         "note": f"单层，柱网 {bay:.1f} m"},
        {"key": "annex", "name": "厂前区办公", "area_m2": annex, "w": 0, "d": 0,
         "kind": "building", "note": "独立出入口"},
        {"key": "dock", "name": "装卸场", "area_m2": max(400.0, b.get("docks", 1) * 350),
         "w": 0, "d": 0, "kind": "yard", "note": "进出货分端"},
        {"key": "ring", "name": "环形消防车道", "area_m2": 0, "w": 0, "d": 0,
         "kind": "road", "note": "宽 4 m，兼回车"},
    ]
    return p


# --------------------------------------------------------------------------
# 酒店：客房标准层
# --------------------------------------------------------------------------
def hospitality(b: SectorBrief, *, keys_per_floor: int = 0) -> SectorProgram:
    keys = b.get("keys")
    per = keys_per_floor or max(8, min(16, int(round(keys / 6.0)) if keys else 12))
    rows: List[ProgramRow] = []
    types = [("标准大床房", 42.0, 0.6), ("标准双床房", 45.0, 0.4)]
    # 客房排在走廊两侧：一侧排一半。单侧排会把另一侧留成长条空白，
    # 那不是酒店平面该有的样子。
    front_n = max(2, per // 2)
    for i in range(per):
        name, area, _share = types[0] if i % 5 not in (3, 4) else types[1]
        band = "front" if i < front_n else "back"
        rows.append(_row(f"G{i + 1:02d}", f"{name} {i + 1}", area, "guest",
                         "guest_room", 20, f"{area:.0f} m²/间（开间 4.2 m）",
                         band=band))
    rows.append(_row("PB1", "电梯厅", 36.0, "public", "waiting", 30, "2 客梯 + 1 服务梯",
                     band="back"))
    # 后场按"每间客房约 2.6 m²"折：16 间/层 → 约 42 m²，够布草周转、备品与清洁。
    # 写死 26 m² 的话，一层 19 间房只有一只储物柜那么大的后场，图上也撑不起一块。
    boh_total = max(24.0, per * 2.6)
    rows.append(_row("PB2", "服务间与布草", round(boh_total * 0.55, 1), "boh", "storage",
                     40, f"{per} 间/层 × 2.6 m² × 55%（布草周转）", band="back"))
    rows.append(_row("PB3", "备品与清洁", round(boh_total * 0.28, 1), "boh", "storage",
                     45, "与布草合并，贴服务梯", band="back"))
    rows.append(_row("PB4", "员工卫生间", round(boh_total * 0.17, 1), "boh", "bathroom",
                     48, "后场内，不对客人开放", band="back"))
    p = SectorProgram(
        rows=rows, unit="客房标准层",
        note=(f"每层 {per} 间；全店 {keys:.0f} 间约需 {math.ceil(keys / per) if keys else 1} 层。"
              "大堂、餐饮、宴会与后场在裙房另排，须与本层共用同一组竖向交通。"),
        corridor_width_mm=1800.0,
        bands=("front", "back"),
        totals={"keys": keys, "per_floor": per,
                "floors": math.ceil(keys / per) if keys else 1},
    )
    gfa = b.get("building_m2")
    if gfa:
        side = math.sqrt(max(gfa / 6.0, 100.0) / 2.4)
        p.blocks = [
            {"key": "tower", "name": "客房塔楼", "area_m2": b.get("guest_m2"),
             "w": round(side * 1.2, 1), "d": round(side, 1), "kind": "building",
             "note": f"{math.ceil(keys / per) if keys else 1} 层"},
            {"key": "podium", "name": "公共裙房", "area_m2": b.get("public_m2"),
             "w": 0, "d": 0, "kind": "building", "note": "大堂/餐饮/会议"},
            {"key": "boh", "name": "后场", "area_m2": b.get("boh_m2"), "w": 0, "d": 0,
             "kind": "building", "note": "独立货梯，不经过大堂"},
        ]
    return p


# --------------------------------------------------------------------------
# 景观：不给房间，给分区与做法（不套房间算法）
# --------------------------------------------------------------------------
def landscape(b: SectorBrief) -> SectorProgram:
    site = b.get("site_area")
    rows = [
        _row("LZ1", "绿地与种植", b.get("green_m2"), "planting", "planting", 20,
             f"绿地率 {b.get('green_ratio', 0):.0%}"),
        _row("LZ2", "硬质铺装与场地", b.get("paving_m2"), "paving", "paving", 30,
             "含入口广场、主园路与活动场地"),
        _row("LZ3", "水面", b.get("water_m2") or 1.0, "water", "water", 40,
             "静水面，含循环与补水"),
        _row("LZ4", "园路与停留节点", max(20.0, site * 0.06), "path", "paving", 35,
             "主路 1.2 m，支路 0.9 m"),
    ]
    return SectorProgram(
        rows=rows, unit="场地分区",
        note=("景观不出房间表：分区面积与做法是设计数据，图是总平面。"
              "竖向标高与放线须现场测量后定。"),
        bands=("planting", "paving", "water"),
        totals={"site_area": site},
    )


BUILDERS = {
    "education": education,
    "healthcare": healthcare,
    "industrial": industrial,
    "hospitality": hospitality,
    "landscape": landscape,
}


def build(brief: SectorBrief) -> SectorProgram:
    """按行业给出 program；不认识的类型给空表（不硬凑房间）。"""
    fn = BUILDERS.get(brief.sector)
    if fn is None:
        return SectorProgram(rows=[], unit="", note=f"未支持的类型：{brief.sector_label}")
    return fn(brief)


__all__ = ["BUILDERS", "ProgramRow", "SectorProgram", "build", "education",
           "healthcare", "hospitality", "industrial", "landscape"]
