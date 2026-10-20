"""把行业程序落到几何上，并调用已有的平面算法出方案。

复用关系（不新写一套平面算法）：

* 房间清单 → `project.program`，与住宅/办公同一份数据结构；
* 排布 → `planner.PlanGenerator` 的 `zone_bands`：按"带"铺房间，
  各行业只是带序与进深不同；
* 墙、门、窗、面积表、DXF → 沿用原有 `_make_spaces` / `_make_elements` / 适配器。

当项目还没有实测轮廓时，会按任务书反算一个**建议轮廓**并明确标记
`schematic / proposed`：这是设计的起点，不是现场尺寸，G3 前必须按实测复核。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from ..model import Element, Level, Project, Space
from ..planner import PlanGenerator, SchemeOptions, SchemeResult
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


def envelope_size(program: SectorProgram, sector: str) -> Envelope:
    """按房间清单反算一个够用的矩形轮廓。

    宽度取"最宽那条带"的自然宽度（房间宽度之和），进深取各带设计进深之和
    加走廊。这样排出来的房间不会因为轮廓过窄而被压扁。
    """
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
                  env: Envelope, *, corridor: float = 0.0) -> Dict[str, SchemeResult]:
    """两套可比方案：同一份任务书，带序相反。

    不是"换个颜色"：带序一换，采光面、服务流线、出入口关系都跟着变，
    面积表也会不一样——这才是业主能选的东西。
    """
    gen = PlanGenerator(project, project.levels[0].id if project.levels else "L1")
    order = _band_order(program)
    corr = corridor or env.corridor_mm
    base = dict(strategy="zone_bands", corridor_width_mm=corr,
                band_order=tuple(order), band_depths=env.band_depths,
                corridor_after=1 if len(order) > 1 else 0)
    opts_a = SchemeOptions(variant="A", title="方案A · 前场采光（任务书直接排布）",
                           flip=False, **base)
    opts_b = SchemeOptions(variant="B", title="方案B · 后场前置（服务流线优先）",
                           flip=True, **base)
    return {"A": gen.generate(opts_a), "B": gen.generate(opts_b)}


def install_landscape_spaces(project: Project, program: SectorProgram,
                             brief: SectorBrief) -> int:
    """把景观分区落成场地空间：每块一个多边形，用途对应水/种植/铺装。

    只用于让模型里"真的有这块地"。图与报告仍读 `landscape_data`。
    """
    site = brief.get("site_area") or sum(r.area_m2 for r in program.rows) or 100.0
    w, d = _site_extent(site)
    level_id = "L-SITE"
    if not any(lv.id == level_id for lv in project.levels):
        project.levels.append(Level(id=level_id, name="场地", elevation_mm=0.0,
                                    height_mm=0.0))
    # 清掉上一轮：只清自己的，不动建筑楼层
    project.spaces = [s for s in project.spaces
                      if not str(s.source).startswith("sector_site")]
    order = ["planting", "paving", "path", "water"]
    rows = sorted(program.rows, key=lambda r: order.index(r.zone) if r.zone in order else 9)
    total = sum(r.area_m2 for r in rows) or 1.0
    x = 0.0
    count = 0
    for r in rows:
        width = w * (r.area_m2 / total)
        ring = [[x, 0.0], [x + width, 0.0], [x + width, d], [x, d]]
        use = {"planting": "planting", "water": "water", "paving": "paving",
               "path": "circulation"}.get(r.zone, "outdoor")
        project.spaces.append(Space(
            id=f"S-LZ-{r.key}", level_id=level_id, name=r.name, use=use,
            boundary_mm2d=ring, source="sector_site", confidence=0.4,
            properties={"precision": "schematic", "proposed": True,
                        "area_m2_target": round(r.area_m2, 1),
                        "note": "按场地面积与占比排布的分区，须实测放线"},
        ))
        x += width
        count += 1
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


__all__ = ["CORRIDOR", "DEPTH_BY_SECTOR", "DESIGN_DEPTH", "Envelope",
           "install_landscape_spaces", "build_schemes", "envelope_size",
           "has_envelope", "install_envelope", "install_program", "landscape_data"]
