"""把行业程序落到几何上，并调用已有的平面算法出方案。

复用关系（不新写一套平面算法）：

* 房间清单 → `project.program`，与住宅/办公同一份数据结构；
* 排布 → `plans.build()`：按 S2 选定的 parti 排（几条带、哪条是走廊/中庭/街），
  房间仍由 `planner._strip` 摆放，墙门窗仍由 `PlanGenerator` 生成；
  没有可执行的 parti 时才回落到通用 `zone_bands`，并在记录里标明"未落实概念"；
* 墙、门、窗、面积表、DXF → 沿用原有 `_make_spaces` / `_make_elements` / 适配器。

当项目还没有实测轮廓时，会按任务书反算一个**建议轮廓**并明确标记
`schematic / proposed`：这是设计的起点，不是现场尺寸，G3 前必须按实测复核。
`geometry_basis()` 把轮廓分成实测 / 已有图纸 / 业主估算 / 系统建议四档——
只有前三档能作为正式确认的几何依据。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Element, Level, Project, Space
from ..planner import PlanGenerator, SchemeOptions, SchemeResult
from . import parti as parti_mod
from . import plans
from .brief import SectorBrief
from .program import SectorProgram

#: 各房间的"设计进深"（mm）。决定一个带里每个房间占多宽：
#: 宽度 = 面积 ÷ 进深。教室 7.5 m、客房 8 m、厂房 12 m 是常见做法。
DESIGN_DEPTH: Dict[str, float] = {
    "classroom": 7500, "study": 7500, "clinic": 4500, "ward": 6000,
    "guest_room": 8000, "waiting": 8000, "office_cell": 4500, "lab": 6000,
    "workshop": 12000, "bathroom": 3600, "storage": 4000, "laundry": 3600,
    "living": 4800, "bedroom": 4200, "kitchen": 3600, "dining": 3600,
}

#: 分行业覆盖设计进深：厂房的生产/仓储是"大进深大厅"，不是 4 m 小房间；
#: 用通用值会把 12000 m² 的厂房排成 840 m 长的窄条。
DEPTH_BY_SECTOR: Dict[str, Dict[str, float]] = {
    "industrial": {"workshop": 60000, "storage": 30000, "office_cell": 15000,
                   "bathroom": 6000, "lab": 18000},
    "hospitality": {"guest_room": 8000, "storage": 4000, "waiting": 8000},
    "healthcare": {"clinic": 4500, "lab": 6000, "waiting": 8000, "bathroom": 3600,
                   "storage": 4000, "office_cell": 4500},
    "education": {"classroom": 7500, "study": 7500, "office_cell": 4500,
                  "bathroom": 3600, "storage": 4000},
}

#: 走廊宽度（mm）：教学楼要容纳课间人流，客房层只需一辆布草车。
CORRIDOR = {"education": 3000.0, "healthcare": 2400.0, "hospitality": 1800.0,
            "industrial": 0.0, "retail": 4000.0, "office": 1500.0}


@dataclass
class Envelope:
    width_mm: float
    depth_mm: float
    band_depths: Tuple[Tuple[str, float], ...] = ()
    corridor_mm: float = 2400.0
    proposed: bool = True
    note: str = ""

    @property
    def area_m2(self) -> float:
        return self.width_mm * self.depth_mm / 1e6

    def to_dict(self) -> Dict[str, Any]:
        return {"width_mm": round(self.width_mm), "depth_mm": round(self.depth_mm),
                "area_m2": round(self.area_m2, 1),
                "bands": {k: round(v) for k, v in self.band_depths},
                "corridor_mm": round(self.corridor_mm),
                "proposed": self.proposed, "note": self.note}


def _band_order(program: SectorProgram) -> List[str]:
    out: List[str] = [b for b in program.bands if any(r.band == b for r in program.rows)]
    for r in program.rows:
        if r.band not in out:
            out.append(r.band)
    return out


def envelope_size(program: SectorProgram, sector: str, *,
                  kind: str = "") -> Envelope:
    """按房间清单反算一个够用的矩形轮廓。

    有 parti 时用 parti 的剖面构成（几条带、多深、有没有中庭/街/双廊），
    所以轮廓跟着组织方式走：诊疗街是长的、医技居中是厚的、厂房是扁而大的。
    没有 parti 时退回"最宽那条带"的通用反算——那时的轮廓只是够用，不代表设计。

    宽度取"最宽那条带"的自然宽度（房间宽度之和），进深取各带设计进深之和
    加走廊。这样排出来的房间不会因为轮廓过窄而被压扁。
    """
    prof = plans.profile_size(program, sector, kind) if kind else None
    if prof:
        return Envelope(width_mm=float(prof["width_mm"]), depth_mm=float(prof["depth_mm"]),
                        band_depths=tuple((l, float(d)) for l, d in prof["bands"]),
                        corridor_mm=0.0, proposed=True, note=str(prof["note"]))
    order = _band_order(program)
    corridor = CORRIDOR.get(sector, 2400.0)
    override = DEPTH_BY_SECTOR.get(sector, {})
    depth_of = lambda r: override.get(r.recipe, DESIGN_DEPTH.get(r.recipe, 4500.0))  # noqa: E731
    design = {}
    areas = {}
    for band in order:
        rows = [r for r in program.rows if r.band == band]
        design[band] = max((depth_of(r) for r in rows), default=4500.0)
        areas[band] = sum(r.area_m2 for r in rows)

    # 宽度先取"按设计进深排开"的最大值，再反算每带需要的进深：
    # 一个带里的面积除以这条宽度，就是它必须有的深度。取两者较大值，
    # 否则窄带里的房间会被 `_strip` 压扁（面积表会集体偏低，那是假的）。
    W = max((areas[b] * 1e6 / design[b] for b in order), default=12000.0)
    depths: List[Tuple[str, float]] = []
    for _ in range(4):
        depths = [(b, max(design[b], areas[b] * 1e6 / W)) for b in order]
        need = max((areas[b] * 1e6 / dict(depths)[b] for b in order), default=W)
        if need <= W * 1.01:
            break
        W = need
    H = sum(d for _b, d in depths) + (corridor if len(depths) > 1 else 0.0)
    # 取整到 300 mm，避免出现 69.83 m 这种假精度
    W = math.ceil(W / 300.0) * 300.0
    H = math.ceil(H / 300.0) * 300.0
    return Envelope(width_mm=W, depth_mm=H, band_depths=tuple(depths),
                    corridor_mm=corridor, proposed=True,
                    note=("按任务书面积与设计进深反算的建议轮廓；"
                          "不是现场实测，也不是最终建筑轮廓"))


def has_envelope(project: Project) -> bool:
    return any(s.use == "envelope" for s in project.spaces) or bool(
        project.by_type("wall"))


def site_geometry_basis(project: Project, brief: SectorBrief) -> Dict[str, Any]:
    """景观的几何依据：场地有没有边界坐标，与建筑轮廓是两件事。

    景观没有外墙，`geometry_basis` 会说"无几何"——那会把"只知道 800 m² 面积"
    说成可以正式确认。这里按场地空间与输入来源另判一次：
    有实测/图纸边界 → 可作正式依据；只有客户报的面积 → 业主估算，只能探索。
    """
    real = [s for s in project.spaces
            if s.level_id == "L-SITE" and not str(s.source).startswith("sector_site")]
    if real:
        src = str(real[0].source).lower()
        kind = "surveyed" if any(k in src for k in ("survey", "measured", "实测")) \
            else "drawing"
    elif "site_area" in brief.inputs:
        kind = "client"
    else:
        kind = "proposed"
    note = {
        "surveyed": "实测场地边界：可作为正式确认的几何依据",
        "drawing": "已有图纸边界：可作设计依据，签发后仍须现场核对",
        "client": "客户只给了场地面积、没有边界坐标：分区只能试排，须实测放线",
        "proposed": "没有场地几何：分区按面积假设试排，不能作为正式依据",
    }[kind]
    return {"kind": kind, "label": BASIS_LABEL[kind],
            "can_formal": kind in ("surveyed", "drawing"), "note": note,
            "area_m2": brief.get("site_area")}


#: 几何依据四档。只有前三档能支撑"正式确认"，第四档只能做探索。
BASIS_LABEL: Dict[str, str] = {
    "surveyed": "实测边界",
    "drawing": "已有图纸边界",
    "client": "业主估算边界",
    "proposed": "系统建议轮廓",
    "none": "无几何",
}


def geometry_basis(project: Project) -> Dict[str, Any]:
    """这套平面站在什么几何上？——四档分开，不把假设说成实测。

    区分标准只看可核对的来源字段，不做推测：
    * `properties.proposed` 为真 → 建议轮廓（本系统反算的）；
    * 来源写明 survey/measured/实测 → 实测；
    * 来源写明 client/estimate 或 properties.estimate → 业主估算；
    * 其余（drawing_import / dxf / 未标注）→ 已有图纸，须现场复核。
    """
    env = next((s for s in project.spaces if s.use == "envelope"), None)
    walls = [w for w in project.by_type("wall")
             if not str(w.source).startswith("scheme_")]
    if env is None and not walls:
        return {"kind": "none", "label": BASIS_LABEL["none"], "can_formal": False,
                "note": "还没有任何平面几何：不能出可核对的平面", "source": ""}
    src = str(getattr(env, "source", "") if env is not None else
              (walls[0].source if walls else ""))
    props = dict(getattr(env, "properties", {}) or {}) if env is not None else {}
    low = (src + " " + str(props.get("precision") or "")).lower()
    if props.get("proposed"):
        kind = "proposed"
    elif any(k in low for k in ("survey", "measured", "实测", "authoritative")):
        kind = "surveyed"
    elif any(k in low for k in ("client", "estimate", "估算")) or props.get("estimate"):
        kind = "client"
    else:
        kind = "drawing"
    notes = {
        "surveyed": "实测边界：可作为正式确认的几何依据",
        "drawing": "已有图纸边界：可作为设计依据，但图纸标注不等于现场实测，签发前须核对",
        "client": "业主估算边界：只能做方案探索，不能作为正式确认的几何依据",
        "proposed": "系统按任务书反算的建议轮廓：只能做方案探索，须实测后重出",
    }
    return {"kind": kind, "label": BASIS_LABEL[kind],
            "can_formal": kind in ("surveyed", "drawing"),
            "note": notes[kind], "source": src,
            "width_mm": round(_extent(env, walls)[0]),
            "depth_mm": round(_extent(env, walls)[1])}


def _extent(env: Optional[Space], walls: Sequence[Any]) -> Tuple[float, float]:
    pts: List[Sequence[float]] = []
    if env is not None and env.boundary_mm2d:
        pts = list(env.boundary_mm2d)
    else:
        for w in walls:
            g = w.geometry or {}
            for key in ("start", "end"):
                p = g.get(key)
                if p:
                    pts.append(p)
    if not pts:
        return 0.0, 0.0
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def install_program(project: Project, program: SectorProgram) -> int:
    """把行业程序写进项目（与住宅 program 同一结构）。返回写入行数。"""
    rows = program.to_rows()
    project.program = rows
    project.meta = dict(project.meta or {})
    project.meta["sector_program"] = {
        "unit": program.unit, "note": program.note,
        "rows": len(rows), "area_m2": round(program.area_m2, 1),
        "bands": list(program.bands),
    }
    return len(rows)


def install_envelope(project: Project, env: Envelope) -> None:
    """写入建议轮廓与外墙。只在此项目还没有任何几何时调用。"""
    level = project.levels[0] if project.levels else None
    if level is None:
        level = Level(id="L1", name="一层", elevation_mm=0.0, height_mm=3900.0)
        project.levels = [level]
    W, H = env.width_mm, env.depth_mm
    ring = [[0.0, 0.0], [W, 0.0], [W, H], [0.0, H]]
    project.spaces.append(Space(
        id="S-ENV", level_id=level.id, name="建议轮廓（按任务书推算）",
        use="envelope", boundary_mm2d=ring, source="concept_generator",
        confidence=0.35,
        properties={"precision": "schematic", "proposed": True, "uncertain": True,
                    "note": env.note, "requires_door": False},
    ))
    t = 240.0
    edges = [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]
    for i, (a, b) in enumerate(edges, 1):
        project.elements.append(Element(
            id=f"W-EXT-{i:03d}", type="wall", level_id=level.id,
            geometry={"start": [a[0] + (t / 2 if a[0] == 0 else -t / 2), a[1]],
                      "end": [b[0] + (t / 2 if b[0] == 0 else -t / 2), b[1]],
                      "thickness_mm": t, "height_mm": level.height_mm,
                      "kind": "exterior"},
            # 注意：source 不能以 `scheme_` 开头——那是"方案生成的隔墙"的标记，
            # 外墙用这个前缀会被 `_base_walls()` 过滤掉，结果一扇窗都生不出来。
            source="concept_exterior", confidence=0.35, uncertain=True,
            properties={"note": "按建议轮廓生成，须按实测与结构条件复核"},
        ))
    project.meta = dict(project.meta or {})
    project.meta["proposed_envelope"] = env.to_dict()


def build_schemes(project: Project, program: SectorProgram, sector: str,
                  env: Envelope, *, parti: Optional[parti_mod.Parti] = None,
                  corridor: float = 0.0,
                  level_id: Optional[str] = None) -> Dict[str, SchemeResult]:
    """两套方案：A = S2 选定的组织方式，B = 另一种组织逻辑。

    有 parti 时按 `plans.build()` 排：教室带夹中庭、房间夹双廊、原料到成品
    单向推进——这些结构在图上看得见，才算概念落地。
    B 不是把 A 翻一下：它是另一套 parti（例如选了"组团中庭"，对照方案就是
    "线形连廊"），面积表与流线都不一样，业主才有真正可比的东西。
    没有可执行的 parti 时回落到通用 `zone_bands`（A 正序 / B 反序），
    记录里会写明 `concept_implemented=False`。
    """
    gen = PlanGenerator(project, level_id or
                        (project.levels[0].id if project.levels else "L1"))
    corr = corridor or env.corridor_mm
    if parti is not None and parti.kind in plans.BUILDERS:
        a = plans.build(parti.kind, gen, SchemeOptions(
            variant="A", title=f"方案A · {parti.label or parti.concept_name}"
                               f"（{parti.concept_name}）",
            corridor_width_mm=corr))
        alt = parti.alt if parti.alt in plans.BUILDERS else ""
        if alt:
            b = plans.build(alt, gen, SchemeOptions(
                variant="B", title=f"方案B · {parti_mod.KIND_LABEL.get(alt, alt)}"
                                   "（另一种组织逻辑）",
                corridor_width_mm=corr))
        else:
            b = _band_scheme(gen, program, corr, variant="B",
                             title="方案B · 通用带序（对照）", flip=True)
        if a is not None and b is not None:
            return {"A": a, "B": b}
    return {
        "A": _band_scheme(gen, program, corr, variant="A",
                          title="方案A · 前场采光（通用带序）", flip=False),
        "B": _band_scheme(gen, program, corr, variant="B",
                          title="方案B · 后场前置（通用带序）", flip=True),
    }


def _band_scheme(gen: PlanGenerator, program: SectorProgram, corr: float, *,
                 variant: str, title: str, flip: bool) -> SchemeResult:
    order = _band_order(program)
    return gen.generate(SchemeOptions(
        variant=variant, title=title, strategy="zone_bands",
        corridor_width_mm=corr, band_order=tuple(order),
        corridor_after=1 if len(order) > 1 else 0, flip=flip))


def install_landscape_spaces(project: Project, program: SectorProgram,
                             brief: SectorBrief, *, kind: str = "water_loop") -> int:
    """把景观分区落成场地空间：让模型里"真的有这块地"。

    水面成一块、种植沿边界、铺装贴入口、园路成环。主图、CAD、
    OBJ 与提量均读取这些 L-SITE 空间；没有几何库时保留未分区面积警告。
    """
    site = brief.get("site_area") or sum(r.area_m2 for r in program.rows) or 100.0
    w, d = _site_extent(site)
    level_id = "L-SITE"
    if not any(lv.id == level_id for lv in project.levels):
        project.levels.append(Level(id=level_id, name="场地", elevation_mm=0.0,
                                    height_mm=0.0))
    project.spaces = [s for s in project.spaces
                      if not str(s.source).startswith("sector_site")]
    project.elements = [e for e in project.elements
                        if not str(e.source).startswith("sector_site")]
    rows = {r.zone: r for r in program.rows}
    count = 0

    def put(key: str, name: str, use: str, ring: List[List[float]], area: float,
            note: str, design_z_mm: float = 0.0) -> None:
        nonlocal count
        project.spaces.append(Space(
            id=f"S-LZ-{key}", level_id=level_id, name=name, use=use,
            boundary_mm2d=ring, source="sector_site", confidence=0.4,
            properties={"precision": "schematic", "proposed": True,
                        "area_m2_target": round(area, 1),
                        "landscape_kind": kind, "note": note,
                        "design_z_mm": design_z_mm}))
        count += 1

    planting = rows.get("planting")
    water = rows.get("water")
    paving = rows.get("paving")
    path = rows.get("path")

    if water and water.area_m2 > 1:
        # 水面成一块：放在入口对侧偏一侧，直径按面积反算。
        # 台地/林下方案里水景让位于地形与围合，只留一处小水面（跌水/水钵）。
        area = water.area_m2 if kind == "water_loop" else max(6.0, site * 0.008)
        # 12 边椭圆多边形的实面积，而非连续圆的近似面积。
        r = math.sqrt(area * 1e6 / (6 * math.sin(math.pi / 6) * 1.22 * 0.82))
        cx, cy = w * 0.58, d * 0.55
        ring = [[cx + r * 1.22 * math.cos(2 * math.pi * i / 12),
                 cy + r * 0.82 * math.sin(2 * math.pi * i / 12)] for i in range(12)]
        put("WATER", "水面" if kind == "water_loop" else "小水面（跌水 / 水钵）",
            "water", ring, area,
            "静水面：形状为拓扑示意，岸线与水深须实测与专项设计",
            design_z_mm=-120.0)

    if planting:
        edge = max(1500.0, min(w, d) * 0.10)
        strip_area = planting.area_m2 / 4.0
        bands = [
            ("N", [[0, d], [w, d], [w, d-edge], [w*.75, d-edge*1.12],
                   [w*.5, d-edge*.94], [w*.25, d-edge*1.10], [0, d-edge]]),
            ("S", [[0, 0], [w, 0], [w, edge], [w*.75, edge*1.10],
                   [w*.5, edge*.92], [w*.25, edge*1.12], [0, edge]]),
            ("W", [[0, edge*1.15], [edge, edge*1.15], [edge*1.08, d*.32],
                   [edge*.90, d*.68], [edge, d-edge*1.15], [0, d-edge*1.15]]),
            ("E", [[w-edge, edge*1.15], [w, edge*1.15], [w, d-edge*1.15],
                   [w-edge, d-edge*1.15], [w-edge*1.10, d*.68],
                   [w-edge*.91, d*.32]]),
        ]
        for tag, ring in bands:
            put(f"PLANT-{tag}", f"{planting.name}（{tag} 侧）", "planting", ring,
                strip_area, "折线边界种植台地：+0.18m 为方案建议，须复核土层、排水与管线",
                design_z_mm=180.0)

    if paving:
        pw, pd = w * 0.30, d * 0.15
        ring = [[w*.18, d*.13], [w*.18+pw*.75, d*.13],
                [w*.18+pw, d*.18], [w*.18+pw*.9, d*.13+pd*.62],
                [w*.18+pw*.2, d*.13+pd*.72], [w*.18, d*.21]]
        put("PAVE", paving.name, "paving", ring, paving.area_m2,
            "入口活动平台：折线边界，材料、基层及坡向待确认")

    if path:
        # 由相邻内外折线构成闭合环路，每段是独立多边形；不再以四条矩形带
        # 冒充园路。半径留出中央水景与入口平台，宽度只作方案建议。
        t = max(1200.0, min(w, d) * 0.065)
        cx, cy = w*.52, d*.55
        rx, ry = w*.29, d*.27
        n = 16
        inner = [[cx+(rx-t/2)*math.cos(2*math.pi*i/n),
                  cy+(ry-t/2)*math.sin(2*math.pi*i/n)] for i in range(n)]
        outer = [[cx+(rx+t/2)*math.cos(2*math.pi*i/n),
                  cy+(ry+t/2)*math.sin(2*math.pi*i/n)] for i in range(n)]
        for i in range(n):
            j = (i+1) % n
            put(f"PATH-{i+1:02d}", f"{path.name}（环路 {i+1:02d}）", "circulation",
                [outer[i], outer[j], inner[j], inner[i]], path.area_m2/n,
                "闭合游线；路宽及与水景/平台交接须复核")
    if water and path and kind == "water_loop":
        for i, (angle, name) in enumerate(((0.0, "临水观景点"),
                                            (math.pi, "水景观察点")), 1):
            project.elements.append(Element(
                id=f"L-NODE-{i:02d}", type="other", level_id=level_id,
                geometry={"center": [w*.52 + (w*.29-t/2-700)*math.cos(angle),
                                     d*.55 + (d*.27-t/2-700)*math.sin(angle)],
                          "radius_mm": 350.0},
                source="sector_site_node", confidence=0.35, uncertain=True,
                properties={"landscape_kind": "view_node", "name": name,
                            "note": "方案停留节点；与岸线的安全距离和构造未确认"}))
    # 草坪与透水地被是实际空间而非图上的底色。利用已登记的几何可选依赖
    # 对场地扣除水景、铺装与园路，并把中央环内留作草坪，其余作待选型透水地被。
    # 无 Shapely 时保留原分区及明确的面积缺口，不假装已覆盖全场。
    from ..geometry import HAS_SHAPELY
    if HAS_SHAPELY and path:
        from shapely.geometry import Polygon
        from shapely.ops import triangulate, unary_union

        occupied = [Polygon(s.boundary_mm2d) for s in project.spaces_on(level_id)
                    if s.source == "sector_site" and s.use in
                    ("planting", "water", "paving", "circulation")]
        site_shape = Polygon([(0, 0), (w, 0), (w, d), (0, d)])
        residual = site_shape.difference(unary_union(occupied))
        center_shape = Polygon(inner)
        infill = (("LAWN", "中央草坪与地被", "planting",
                   residual.intersection(center_shape)),
                  ("GRAVEL", "透水砂砾活动地面", "paving",
                   residual.difference(center_shape)))

        def leaf_polygons(shape: Any, depth: int = 0) -> List[Any]:
            if shape.is_empty:
                return []
            if shape.geom_type != "Polygon":
                return [part for g in getattr(shape, "geoms", [])
                        for part in leaf_polygons(g, depth)]
            if shape.area < 1000:
                return []
            if not shape.interiors:
                return [shape]
            if depth >= 3:
                raise ValueError("景观剩余区域无法拆成无洞多边形，未写入不准确面积")
            return [part for tri in triangulate(shape)
                    for part in leaf_polygons(tri.intersection(shape), depth + 1)]

        for tag, name, use, shape in infill:
            for i, polygon in enumerate(leaf_polygons(shape), 1):
                ring = [[float(x), float(y)] for x, y in polygon.exterior.coords[:-1]]
                put(f"{tag}-{i:03d}", name, use, ring,
                    polygon.area / 1e6,
                    "方案地表分区；基层、排水、土层和材料待专项确认")
                project.spaces[-1].properties["infill_kind"] = tag.lower()
    # 概念级乔木位置跟随种植带的真实多边形；不是单独画在 SVG 上的装饰图标。
    # 苗木品种、冠幅和最终株距均需苗源/管线复核。
    plant_zones = [s for s in project.spaces_on(level_id)
                   if s.source == "sector_site" and s.use == "planting"
                   and not s.properties.get("infill_kind")]
    tree_no = 0
    for zone in plant_zones:
        x0, y0, x1, y1 = zone.bbox()
        horizontal = x1 - x0 >= y1 - y0
        span = (x1 - x0) if horizontal else (y1 - y0)
        tree_count = max(1, int(span // 5500))
        for i in range(tree_count):
            fraction = (i + 0.5) / tree_count
            x = x0 + span * fraction if horizontal else (x0 + x1) / 2
            y = (y0 + y1) / 2 if horizontal else y0 + span * fraction
            tree_no += 1
            project.elements.append(Element(
                id=f"TREE-{tree_no:03d}", type="other", level_id=level_id,
                geometry={"center": [x, y], "crown_radius_mm": 1100.0,
                          "trunk_radius_mm": 130.0, "height_mm": 3200.0},
                source="sector_site_tree", confidence=0.35, uncertain=True,
                properties={"landscape_kind": "tree", "species": "待选型",
                            "host_zone": zone.id,
                            "note": "方案建议点位，须避让管线并按苗木冠幅复核"}))
    return count


def _site_extent(area_m2: float) -> Tuple[float, float]:
    w = math.sqrt(max(area_m2, 10.0) * 1.4) * 1000.0
    return w, (max(area_m2, 10.0) * 1e6) / w


def landscape_data(program: SectorProgram, brief: SectorBrief) -> Dict[str, Any]:
    """景观不给房间：给分区面积、占比与做法，供总平面与报告使用。"""
    total = sum(r.area_m2 for r in program.rows) or 1.0
    zones = []
    for r in program.rows:
        zones.append({
            "key": r.key, "name": r.name, "area_m2": round(r.area_m2, 1),
            "share": f"{r.area_m2 / total:.0%}", "kind": r.zone,
            "note": r.basis,
        })
    return {
        "zones": zones,
        "site_area_m2": round(brief.get("site_area"), 1),
        "green_ratio": f"{brief.get('green_ratio', 0):.0%}",
        "water_ratio": f"{brief.get('water_ratio', 0):.0%}",
        "note": program.note,
    }


__all__ = ["BASIS_LABEL", "CORRIDOR", "DEPTH_BY_SECTOR", "DESIGN_DEPTH", "Envelope",
           "build_schemes", "envelope_size", "geometry_basis",
           "has_envelope", "install_envelope", "install_landscape_spaces",
           "install_program", "landscape_data", "site_geometry_basis"]
