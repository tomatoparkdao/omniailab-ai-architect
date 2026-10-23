"""Rule-based residential plan generator.

Reads the canonical model (the surveyed shell) and produces *interior*
schemes: partitions, doors, exterior windows and furniture. The shell itself is
never invented — it comes from the base plan, and any element inferred from a
raster/PDF source carries ``uncertain = true`` until confirmed on site.

Two genuinely different schemes come out of the same program:

* **band_day_night** — a public band on the entry side, a corridor, then a
  private band whose wet rooms sit against the corridor and whose bedrooms take
  the façade.
* **spine_centre** — a single service spine (corridor + wet rooms) down the
  middle, so day rooms *and* night rooms both get daylight.

Rooms are allocated by a minimum-dimension aware strip packer. Anything that
cannot reach a usable size is *reported*, not silently squeezed — a plan that
quietly drops the kitchen is worse than one that says it could not place it.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .errors import ModelError, ValidationError
from .geometry import (
    clip_polygon,
    clip_rect_to,
    polygon_area,
    wall_polygon,
)
from .model import Element, Project, Space, polygon_centroid

Rect = Tuple[float, float, float, float]  # x0, y0, x1, y1
Seg = Tuple[Tuple[float, float], Tuple[float, float]]

# --------------------------------------------------------------------------
# furniture catalogue (mm)
# --------------------------------------------------------------------------
FURNITURE: Dict[str, Dict[str, object]] = {
    "sofa": {"size": [2200, 900, 800]},
    "coffee_table": {"size": [1200, 600, 420]},
    "tv_unit": {"size": [1800, 420, 450]},
    "dining_table": {"size": [1600, 900, 750]},
    "sideboard": {"size": [1600, 420, 800]},
    "kitchen_run": {"size": [3000, 620, 850]},
    "kitchen_island": {"size": [1800, 900, 900]},
    "fridge": {"size": [700, 700, 1800]},
    "bed_king": {"size": [1800, 2000, 500]},
    "bed_queen": {"size": [1500, 2000, 500]},
    "nightstand": {"size": [450, 400, 550]},
    "wardrobe": {"size": [1800, 600, 2400]},
    "desk": {"size": [1400, 600, 750]},
    "bookshelf": {"size": [1200, 350, 2000]},
    "shower": {"size": [900, 900, 2000]},
    "wc": {"size": [400, 700, 750]},
    "basin": {"size": [900, 520, 850]},
    "bathtub": {"size": [1700, 800, 600]},
    "shoe_cabinet": {"size": [1000, 350, 1100]},
    "washer": {"size": [600, 620, 850]},
    "shelf_unit": {"size": [900, 400, 2000]},
}

ROOM_RECIPES: Dict[str, Dict[str, object]] = {
    "living": {"use": "living", "furniture": ["sofa", "coffee_table", "tv_unit"],
               "daylight": True, "min_depth": 3600},
    "dining": {"use": "dining", "furniture": ["dining_table", "sideboard"],
               "daylight": True, "min_depth": 2400},
    "kitchen": {"use": "kitchen", "furniture": ["kitchen_run", "fridge"],
                "daylight": True, "min_depth": 2400},
    "master_bedroom": {"use": "bedroom", "furniture": ["bed_king", "nightstand", "wardrobe"],
                       "daylight": True, "min_depth": 2900},
    "bedroom": {"use": "bedroom", "furniture": ["bed_queen", "nightstand", "wardrobe"],
                "daylight": True, "min_depth": 2700},
    "study": {"use": "study", "furniture": ["desk", "bookshelf"],
              "daylight": True, "min_depth": 2400},
    "bathroom": {"use": "bathroom", "furniture": ["shower", "wc", "basin"],
                 "daylight": False, "min_depth": 1600},
    "storage": {"use": "storage", "furniture": ["shelf_unit"],
                "daylight": False, "min_depth": 1000},
    "laundry": {"use": "service", "furniture": ["washer", "shelf_unit"],
                "daylight": False, "min_depth": 1400},
    "entry": {"use": "circulation", "furniture": ["shoe_cabinet"],
              "daylight": False, "min_depth": 1500},
    "hall": {"use": "circulation", "furniture": [], "daylight": False, "min_depth": 1200},
    "corridor": {"use": "circulation", "furniture": [], "daylight": False, "min_depth": 1000},
    "balcony": {"use": "outdoor", "furniture": [], "daylight": True, "min_depth": 1200},

    # ---- 行业房间（学校 / 医疗 / 酒店 / 厂房）----
    # 与住宅同一套排布规则：只是用途、采光要求与最小进深不同。
    # 教室要 7.5 m 进深才排得下 45 人的课桌；诊室 18 m² 一人一诊；
    # 病房按 3 床间；客房按 4.2 m 开间；生产区只关心柱网与通道。
    "classroom": {"use": "teaching", "furniture": ["desk"], "daylight": True,
                  "min_depth": 6300},
    "clinic": {"use": "diagnosis", "furniture": ["desk", "basin"], "daylight": True,
               "min_depth": 3600},
    "ward": {"use": "ward", "furniture": ["bed_queen", "nightstand"], "daylight": True,
             "min_depth": 3300},
    "guest_room": {"use": "guest", "furniture": ["bed_king", "nightstand", "wardrobe"],
                   "daylight": True, "min_depth": 4200},
    "waiting": {"use": "public", "furniture": [], "daylight": True, "min_depth": 3000},
    "office_cell": {"use": "office", "furniture": ["desk", "shelf_unit"],
                    "daylight": True, "min_depth": 3000},
    "lab": {"use": "lab", "furniture": ["desk"], "daylight": False, "min_depth": 4200},
    "workshop": {"use": "production", "furniture": [], "daylight": False,
                 "min_depth": 6000},
}

OPEN_PLAN_RECIPES = ("living", "dining", "entry", "hall", "corridor")
FACADE_RECIPES = ("living", "dining", "kitchen", "master_bedroom", "bedroom", "study")


@dataclass
class RoomSpec:
    key: str
    name: str
    target_area_m2: float
    min_width_mm: float = 1800.0
    zone: str = "day"
    recipe: str = "bedroom"
    priority: int = 50
    #: 排布带：沿走廊的一条带。行业程序指定（教学带 / 后场带），
    #: 不指定时等于 zone——住宅与办公仍按 zone 排，行为不变。
    band: str = ""

    @property
    def use(self) -> str:
        return str(ROOM_RECIPES.get(self.recipe, {}).get("use", "other"))

    @property
    def daylight(self) -> bool:
        return bool(ROOM_RECIPES.get(self.recipe, {}).get("daylight", False))

    @property
    def min_depth(self) -> float:
        return float(ROOM_RECIPES.get(self.recipe, {}).get("min_depth", 1500))

    @property
    def furniture(self) -> List[str]:
        return list(ROOM_RECIPES.get(self.recipe, {}).get("furniture", []))


@dataclass
class SchemeOptions:
    variant: str = "A"
    title: str = ""
    strategy: str = "band_day_night"
    corridor_width_mm: float = 1100.0
    partition_thickness_mm: float = 120.0
    exterior_wall_thickness_mm: float = 240.0
    door_width_mm: float = 900.0
    bathroom_door_width_mm: float = 750.0
    entry_door_width_mm: float = 1000.0
    window_height_mm: float = 1500.0
    window_sill_mm: float = 900.0
    wall_height_mm: float = 2800.0
    furnish: bool = True
    #: 办公策略用：把会议/接待带换到另一侧，用来生成第二套可比方案
    flip: bool = False
    #: `zone_bands` 用：房间带的顺序（从入口到后场）。行业程序给，不由算法猜。
    band_order: Tuple[str, ...] = ()
    #: 走廊插在第几个带之后（0 表示最前面）
    corridor_after: int = 1
    #: 各带的进深（mm）。行业程序给：教室 7500、客房 8000、厂房 12000……
    #: 不给就按面积与最小进深反算。
    band_depths: Tuple[Tuple[str, float], ...] = ()

    @classmethod
    def from_dict(cls, d: Dict[str, object], variant: str = "A") -> "SchemeOptions":
        base = cls(variant=variant)
        for k, v in (d or {}).items():
            if hasattr(base, k) and v is not None:
                setattr(base, k, v)
        return base


@dataclass
class SchemeResult:
    variant: str
    title: str
    strategy: str
    spaces: List[Space] = field(default_factory=list)
    elements: List[Element] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, object] = field(default_factory=dict)

    def area_table(self) -> List[Dict[str, object]]:
        rows = []
        for s in self.spaces:
            if s.use in ("envelope", "outdoor"):
                continue
            target = s.properties.get("target_area_m2")
            rows.append({
                "id": s.id,
                "name": s.name,
                "use": s.use,
                "area_m2": round(s.area_m2, 2),
                "target_m2": target,
                "delta_m2": round(s.area_m2 - float(target or s.area_m2), 2),
            })
        return rows

    def report(self) -> Dict[str, object]:
        return {
            "variant": self.variant,
            "title": self.title,
            "strategy": self.strategy,
            "metrics": self.metrics,
            "areas": self.area_table(),
            "warnings": self.warnings,
        }


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------
def envelope_polygon(project: Project, level_id: str) -> List[List[float]]:
    for s in project.spaces:
        if s.level_id == level_id and s.use == "envelope":
            return [list(map(float, p)) for p in s.boundary_mm2d]
    polys = []
    try:
        from shapely.geometry import Polygon as SPoly
        from shapely.ops import unary_union
    except Exception:  # pragma: no cover
        SPoly = None
    for w in project.by_type("wall"):
        if w.level_id != level_id or SPoly is None:
            continue
        fp = wall_polygon(w)
        if fp:
            polys.append(SPoly(fp))
    if not polys:
        raise ModelError(f"no envelope space and no walls on level '{level_id}'")
    merged = unary_union(polys)
    hull = merged.convex_hull
    return [[float(x), float(y)] for x, y in hull.exterior.coords[:-1]]


def entry_point(project: Project, envelope: Sequence[Sequence[float]]) -> Tuple[float, float]:
    declared = project.constraints.get("entry_point")
    if declared and len(declared) == 2:
        return (float(declared[0]), float(declared[1]))
    xs = [p[0] for p in envelope]
    ys = [p[1] for p in envelope]
    return ((min(xs) + max(xs)) / 2.0, min(ys))


# --------------------------------------------------------------------------
# rect helpers
# --------------------------------------------------------------------------
def _area(r: Rect) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _w(r: Rect) -> float:
    return r[2] - r[0]


def _h(r: Rect) -> float:
    return r[3] - r[1]


def _poly_of(r: Rect) -> List[List[float]]:
    """Bounds tuple -> ring. `geometry.rect` takes (x, y, w, h) and must never
    be fed a bounds tuple; this keeps the two conventions apart."""
    x0, y0, x1, y1 = r
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _strip(rect: Rect, specs: Sequence[RoomSpec], axis: str,
           min_depth_of=None, gap: float = 0.0) -> Tuple[Dict[str, Rect], Dict[str, str], float]:
    """Lay rooms out along `axis`, complete but honest.

    Every room is placed — a plan that silently drops the kitchen is useless.
    If the strip cannot give every room its minimum width, all rooms are scaled
    down together (never below 80% of their target width), and each room that
    ends up under its minimum is reported so a designer can arbitrate.

    Returns (placed, deviations, residual_span_mm).
    """
    x0, y0, x1, y1 = rect
    along_x = axis == "x"
    total = (x1 - x0) if along_x else (y1 - y0)
    cross = (y1 - y0) if along_x else (x1 - x0)
    if total <= 0 or cross <= 0:
        return {}, {}, 0.0

    specs = list(specs)
    target_w = [(s.target_area_m2 * 1e6) / cross for s in specs]
    floor_w = [max(s.min_width_mm, 600.0) for s in specs]
    desired = [max(tw, fw) for tw, fw in zip(target_w, floor_w)]

    scale = 1.0
    if sum(desired) > total:
        scale = total / sum(desired)
        # do not let scaling push a room below 80% of its target width
        desired = [max(tw * 0.8, d * scale) for tw, d in zip(target_w, desired)]
        if sum(desired) > total:
            scale2 = total / sum(desired)
            desired = [d * scale2 for d in desired]

    placed: Dict[str, Rect] = {}
    deviations: Dict[str, str] = {}
    cursor = x0 if along_x else y0
    for i, spec in enumerate(specs):
        w = desired[i]
        if along_x:
            placed[spec.key] = (cursor, y0, cursor + w, y1)
        else:
            placed[spec.key] = (x0, cursor, x1, cursor + w)
        cursor += w + gap
        if w + 0.5 < floor_w[i]:
            deviations[spec.key] = (
                f"{spec.name} 净宽 {w:.0f} mm，低于最小值 {floor_w[i]:.0f} mm"
                f"（缺口 {floor_w[i]-w:.0f} mm）"
            )
    used = sum(desired) + gap * max(len(specs) - 1, 0)
    return placed, deviations, max(0.0, total - used)


def _depth_for(specs: Sequence[RoomSpec], span: float, floor: float = 2400.0) -> float:
    """Smallest strip depth at which every room can reach its minimum width."""
    if not specs:
        return floor
    lo = max(floor, max((s.min_depth for s in specs), default=floor))
    hi = 20000.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        need = sum(max(s.target_area_m2 * 1e6 / mid, s.min_width_mm) for s in specs)
        if need <= span:
            hi = mid
        else:
            lo = mid
    return hi


def _strip_fill(rect: Rect, specs: Sequence[RoomSpec], axis: str) -> Dict[str, Rect]:
    """Split `rect` proportionally to target areas — used for service rows where
    filling the whole strip is the right answer (a wet-room row is fully used)."""
    x0, y0, x1, y1 = rect
    along_x = axis == "x"
    total = sum(max(s.target_area_m2, 0.1) for s in specs) or 1.0
    span = (x1 - x0) if along_x else (y1 - y0)
    out: Dict[str, Rect] = {}
    cursor = x0 if along_x else y0
    consumed = 0.0
    for i, spec in enumerate(specs):
        share = max(spec.target_area_m2, 0.1) / total
        size = span * share
        if i == len(specs) - 1:
            size = span - consumed
        else:
            size = max(size, min(spec.min_width_mm, span))
        size = min(size, span - consumed)
        if size <= 0:
            continue
        if along_x:
            out[spec.key] = (cursor, y0, cursor + size, y1)
        else:
            out[spec.key] = (x0, cursor, x1, cursor + size)
        cursor += size
        consumed += size
    return out


def _shared_edge(a: Rect, b: Rect, tol: float = 1.0) -> Optional[Seg]:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if abs(ax1 - bx0) <= tol or abs(bx1 - ax0) <= tol:
        x = ax1 if abs(ax1 - bx0) <= tol else bx1
        y_lo, y_hi = max(ay0, by0), min(ay1, by1)
        if y_hi - y_lo > 60:
            return ((x, y_lo), (x, y_hi))
    if abs(ay1 - by0) <= tol or abs(by1 - ay0) <= tol:
        y = ay1 if abs(ay1 - by0) <= tol else by1
        x_lo, x_hi = max(ax0, bx0), min(ax1, bx1)
        if x_hi - x_lo > 60:
            return ((x_lo, y), (x_hi, y))
    return None


# --------------------------------------------------------------------------
# generator
# --------------------------------------------------------------------------
class PlanGenerator:
    def __init__(self, project: Project, level_id: Optional[str] = None) -> None:
        self.project = project
        self.level_id = level_id or (project.levels[0].id if project.levels else "L1")
        self._deviations: Dict[str, str] = {}
        self._overrun: float = 0.0
        self._residual: float = 0.0

    def read_program(self) -> List[RoomSpec]:
        raw = self.project.program
        if not raw:
            raise ValidationError("project has no `program` — cannot generate a plan")
        out: List[RoomSpec] = []
        for i, item in enumerate(raw):
            recipe = str(item.get("recipe") or item.get("use") or "bedroom")
            out.append(
                RoomSpec(
                    key=str(item.get("key") or f"R{i+1:02d}"),
                    name=str(item.get("name") or recipe),
                    target_area_m2=float(item.get("area_m2") or 10.0),
                    min_width_mm=float(item.get("min_width_mm") or 1800.0),
                    zone=str(item.get("zone") or "day"),
                    recipe=recipe,
                    priority=int(item.get("priority", 50)),
                    band=str(item.get("band") or item.get("zone") or "day"),
                )
            )
        return out

    def shell(self, opts: SchemeOptions) -> Tuple[List[List[float]], Rect]:
        """Layout core = the usable interior.

        When a surveyed `envelope` space exists it already *is* the interior
        face, so no further inset is applied — insetting twice would push every
        room off the façade and no room would ever touch a window. When no
        envelope is recorded, walls are assumed to be centre-line and the core
        is pulled in by half the wall thickness.
        """
        env = envelope_polygon(self.project, self.level_id)
        xs = [p[0] for p in env]
        ys = [p[1] for p in env]
        has_envelope = any(
            s.level_id == self.level_id and s.use == "envelope" for s in self.project.spaces
        )
        t = 0.0 if has_envelope else opts.exterior_wall_thickness_mm / 2.0
        return env, (min(xs) + t, min(ys) + t, max(xs) - t, max(ys) - t)

    # ------------------------------------------------------------------
    def generate(self, opts: SchemeOptions) -> SchemeResult:
        res = SchemeResult(variant=opts.variant, title=opts.title or f"方案{opts.variant}",
                           strategy=opts.strategy)
        env, core = self.shell(opts)
        specs = self.read_program()
        by_key = {s.key: s for s in specs}

        zones = self._zonify(core, specs, opts, env)
        if self._overrun > 1.0:
            res.warnings.append(
                f"任务书在该轮廓下超出可用进深 {self._overrun:.0f} mm，"
                f"已按优先级压缩房间尺度——须由主创决定减项还是调整标准"
            )
        for key, msg in self._deviations.items():
            res.warnings.append(msg)
        if self._residual > 1000.0:
            res.warnings.append(
                f"公共带尚有 {self._residual/1000.0:.2f} m 宽未分配，作为交通与收纳余量"
            )
        placed: Dict[str, Rect] = {}
        for key, r in zones.items():
            clipped = clip_rect_to(_poly_of(r), env)
            if clipped is None:
                res.warnings.append(f"{key}：分区落在套内轮廓之外，已丢弃")
                continue
            poly, was_clipped = clipped
            placed[key] = (min(p[0] for p in poly), min(p[1] for p in poly),
                           max(p[0] for p in poly), max(p[1] for p in poly))
            if was_clipped:
                res.warnings.append(f"{key}：被非矩形轮廓裁剪，实际面积小于分配面积")

        res.spaces = self._make_spaces(placed, by_key, opts, env, res)
        res.elements = self._make_elements(placed, by_key, opts, res, env, res.spaces)
        res.metrics = self._metrics(res, by_key, opts, placed)
        return res

    # ------------------------------------------------------------------
    # zoning
    # ------------------------------------------------------------------
    def _zonify(self, core: Rect, specs: List[RoomSpec], opts: SchemeOptions,
                env: Sequence[Sequence[float]]) -> Dict[str, Rect]:
        if opts.strategy == "band_day_night":
            return self._band_day_night(core, specs, opts)
        if opts.strategy == "spine_centre":
            return self._spine_centre(core, specs, opts)
        if opts.strategy == "office_cluster":
            return self._office_cluster(core, specs, opts)
        if opts.strategy == "zone_bands":
            return self._zone_bands(core, specs, opts)
        raise ModelError(f"unknown strategy '{opts.strategy}'")

    def _band_day_night(self, core: Rect, specs: List[RoomSpec],
                        opts: SchemeOptions) -> Dict[str, Rect]:
        """南侧公共带 / 走廊 / 北侧私密带（卫浴贴走廊、卧室取采光面）。"""
        x0, y0, x1, y1 = core
        W, H = x1 - x0, y1 - y0
        day = [s for s in specs if s.zone in ("day", "entry")]
        night = [s for s in specs if s.zone == "night"]
        svc = [s for s in specs if s.zone == "service"]
        self._deviations: Dict[str, str] = {}

        day_a = sum(s.target_area_m2 for s in day) * 1e6
        rest_a = sum(s.target_area_m2 for s in (night + svc)) * 1e6

        svc_a = sum(s.target_area_m2 for s in svc) * 1e6
        svc_depth = min(max(svc_a / max(W, 1.0), max((s.min_depth for s in svc), default=1500.0)),
                        3000.0)
        bed_min = max((s.min_depth for s in night), default=2700.0)
        night_fit = svc_depth + bed_min
        day_fit = _depth_for(day, W, 2600.0)

        corr = opts.corridor_width_mm
        upper = H - corr - night_fit
        if upper < day_fit:
            short = day_fit - upper
            corr = max(1000.0, corr - short)
            upper = H - corr - night_fit
        if upper < day_fit:
            self._overrun = day_fit - upper
            day_h = max(upper, 2600.0)
        else:
            self._overrun = 0.0
            day_h = min(max(H - corr - rest_a / max(W, 1.0), day_fit), upper)

        zones: Dict[str, Rect] = {}
        day_band: Rect = (x0, y0, x1, y0 + day_h)
        corr_rect: Rect = (x0, day_band[3], x1, day_band[3] + corr)
        night_band: Rect = (x0, corr_rect[3], x1, y1)

        placed, dev, residual = _strip(day_band, sorted(day, key=lambda s: s.priority), "x")
        zones.update(placed)
        self._deviations.update(dev)
        self._residual = residual
        zones["corridor"] = corr_rect

        svc_row: Rect = (x0, night_band[1], x1, night_band[1] + svc_depth)
        bed_row: Rect = (x0, svc_row[3], x1, y1)
        if svc:
            zones.update(_strip_fill(svc_row, sorted(svc, key=lambda s: s.priority), "x"))
        if night:
            n_placed, n_dev, _ = _strip(
                bed_row, sorted(night, key=lambda s: -s.target_area_m2), "x"
            )
            zones.update(n_placed)
            self._deviations.update(n_dev)
        return zones

    def _zone_bands(self, core: Rect, specs: List[RoomSpec],
                    opts: SchemeOptions) -> Dict[str, Rect]:
        """按"带"排：每个 zone 一条带，走廊插在指定位置。

        学校、医院、客房层、厂房共用这一套排布——差别只在带序与房间清单，
        不为每个行业写一个专用算法。带高按面积比分配，但每带不低于该带
        房间的最小进深；分不下的写进 deviations，不静默压缩。
        """
        x0, y0, x1, y1 = core
        W, H = x1 - x0, y1 - y0
        self._deviations = {}
        self._overrun = 0.0
        self._residual = 0.0

        order: List[str] = [str(z) for z in (opts.band_order or ())]
        for sp in specs:
            key_band = sp.band or sp.zone
            if key_band not in order:
                order.append(key_band)
        groups = {z: [sp for sp in specs if (sp.band or sp.zone) == z] for z in order}
        groups = {z: g for z, g in groups.items() if g}
        if not groups:
            raise ModelError("zone_bands 需要带序或 zone 标注")

        corr = float(opts.corridor_width_mm)
        if corr < 500.0:          # 厂房这类不需要公共走廊的，直接铺满
            corr = 0.0
        avail = max(H - corr, 1.0)
        areas = {z: sum(sp.target_area_m2 for sp in g) * 1e6 for z, g in groups.items()}
        mins = {z: max([sp.min_depth for sp in g] or [2000.0]) for z, g in groups.items()}
        total_a = sum(areas.values()) or 1.0

        given = dict(opts.band_depths or ())
        heights = {z: max(mins[z], float(given.get(z) or (avail * areas[z] / total_a)))
                   for z in groups}
        # 走廊之外只有 avail：超了就把"非最小"的带按比例收回来
        over = sum(heights.values()) - avail
        if over > 0:
            slack = {z: max(0.0, heights[z] - mins[z]) for z in groups}
            total_slack = sum(slack.values()) or 1.0
            for z in groups:
                heights[z] -= over * slack[z] / total_slack
                heights[z] = max(mins[z], heights[z])
            self._overrun = max(0.0, sum(heights.values()) - avail)
        elif over < 0:
            # 有余量给面积最大的那条带，避免留一整条空带
            biggest = max(areas, key=lambda z: areas[z])
            heights[biggest] += -over

        bands = list(groups.keys())
        after = max(0, min(int(opts.corridor_after), len(bands)))
        zones: Dict[str, Rect] = {}
        y = y0
        for i, z in enumerate(bands):
            h = heights[z]
            if opts.flip:
                band: Rect = (x0, y1 - h - (y - y0), x1,
                              y1 - (y - y0))
            else:
                band = (x0, y, x1, y + h)
            placed, dev, residual = _strip(
                band, sorted(groups[z], key=lambda sp: sp.priority), "x")
            # 余量小的时候把这一带铺满：一条带末端只剩几米，图上像"忘了排"。
            # 超过 12% 就不铺——那说明任务书本身没填满这条带，应当留白并报出来。
            band_w = x1 - x0
            if residual > 0 and band_w > 0 and residual <= band_w * 0.18:
                used = band_w - residual
                k = band_w / used if used > 0 else 1.0
                bx0 = x0
                placed = {key: (bx0 + (r[0] - bx0) * k, r[1],
                                bx0 + (r[2] - bx0) * k, r[3])
                          for key, r in placed.items()}
                if k > 1.08:
                    for sp in groups[z]:
                        got = (placed[sp.key][2] - placed[sp.key][0]) * \
                            (placed[sp.key][3] - placed[sp.key][1]) / 1e6
                        if sp.target_area_m2 and got > sp.target_area_m2 * 1.08:
                            self._deviations.setdefault(
                                sp.key,
                                f"{sp.name}：按带宽放大到 {got:.1f}㎡"
                                f"（任务书 {sp.target_area_m2:.1f}㎡）——"
                                "楼层轮廓比房间需求宽，差额不是任务书的要求")
                residual = 0.0
            if residual > 0 and band_w > 0:
                # 留白要画成"预留"，不能留一条空白：图上空白会被读成"漏排了"
                used = band_w - residual
                if opts.flip:
                    zones[f"reserve{len(zones)}"] = (
                        x0, band[1], x0 + residual, band[3]) if used <= 1.0 else \
                        (x1 - residual, band[1], x1, band[3])
                else:
                    zones[f"reserve{len(zones)}"] = (
                        (x0, band[1], x0 + residual, band[3]) if used <= 1.0
                        else (x1 - residual, band[1], x1, band[3]))
            zones.update(placed)
            self._deviations.update(dev)
            self._residual = max(self._residual, residual)
            y += h
            if corr > 0 and i + 1 == after and after < len(bands):
                if opts.flip:
                    zones["corridor"] = (x0, y1 - (y - y0) - corr, x1, y1 - (y - y0))
                else:
                    zones["corridor"] = (x0, y, x1, y + corr)
                y += corr
        if corr > 0 and "corridor" not in zones:
            zones["corridor"] = (x0, max(y0, y1 - corr), x1, y1)

        for sp in specs:
            r = zones.get(sp.key)
            if not r:
                continue
            got = max(0.0, (r[2] - r[0]) * (r[3] - r[1])) / 1e6
            if sp.target_area_m2 and got < sp.target_area_m2 * 0.8:
                self._deviations[sp.key] = (
                    f"{sp.name}：目标 {sp.target_area_m2:.1f}㎡，实得 {got:.1f}㎡，"
                    "差额需主创决定从哪让出")
        return zones

    def _office_cluster(self, core: Rect, specs: List[RoomSpec],
                        opts: SchemeOptions) -> Dict[str, Rect]:
        """办公布局：前场接待/会议带 → 主通道 → 开放办公 + 专注/服务后场。

        与住宅的 band / spine 是**不同算法**，不是把 office 房间塞进住宅带：
        * 会议与接待共用一条前场带（访客动线止于通道，不进工位区）；
        * 开放办公是**一整块**连续空间，不切小间——办公的价值在连续可用面宽；
        * 专注间与服务靠后场竖排，形成声环境上的"硬边"；
        * 两套方案靠 `flip` 把前场带与后场列换到另一侧，其余参数不变。
        """
        x0, y0, x1, y1 = core
        W, H = x1 - x0, y1 - y0
        entry = [s for s in specs if s.zone == "entry"]
        meeting = [s for s in specs if s.recipe in ("meeting", "boardroom")]
        focus = [s for s in specs if s.recipe in ("focus", "phone_booth")]
        svc = [s for s in specs if s.zone == "service"]
        claimed = {s.key for s in entry + meeting + focus + svc}
        open_specs = [s for s in specs if s.key not in claimed]
        self._deviations = {}
        self._overrun = 0.0
        self._residual = 0.0

        corr = max(1100.0, float(opts.corridor_width_mm))
        front_specs = entry + meeting
        front_a = sum(s.target_area_m2 for s in front_specs) * 1e6
        front_min = max([s.min_depth for s in front_specs] or [3000.0])
        front_h = min(max(front_a / max(W, 1.0) * 1.2, front_min), H * 0.45)
        front_h = max(front_h, min(H * 0.4, 2400.0))

        if opts.flip:
            front: Rect = (x0, y1 - front_h, x1, y1)
            corr_rect: Rect = (x0, front[1] - corr, x1, front[1])
            back: Rect = (x0, y0, x1, corr_rect[1])
        else:
            front = (x0, y0, x1, y0 + front_h)
            corr_rect = (x0, front[3], x1, front[3] + corr)
            back = (x0, corr_rect[3], x1, y1)

        zones: Dict[str, Rect] = {}
        if front_specs:
            order = sorted(entry, key=lambda s: s.priority) + \
                sorted(meeting, key=lambda s: s.priority)
            if opts.flip:
                order = list(reversed(order))
            placed, dev, residual = _strip(front, order, "x")
            zones.update(placed)
            self._deviations.update(dev)
            self._residual = residual
        zones["corridor"] = corr_rect

        back_h = max(back[3] - back[1], 1.0)
        col_specs = focus + svc
        col_w = 0.0
        if col_specs:
            col_a = sum(s.target_area_m2 for s in col_specs) * 1e6
            # 竖排一列要塞下专注间 + 服务间：宽度必须按"总面积 ÷ 后场高度"留
            # 余量，否则 _strip 会按比例把最后一间压成 1–2㎡（真实踩过）。
            col_w = min(max(col_a / back_h * 1.2,
                            max(s.min_width_mm for s in col_specs)), W * 0.42)
            if back_h * col_w < col_a:
                self._deviations["office-column"] = (
                    f"后场竖列仅 {back_h * col_w / 1e6:.1f}㎡，不足 {col_a / 1e6:.1f}㎡："
                    "专注与服务空间会被压缩，需主创决定减项")
            if opts.flip:
                col: Rect = (back[0], back[1], back[0] + col_w, back[3])
                open_rect: Rect = (back[0] + col_w, back[1], back[2], back[3])
            else:
                col = (back[2] - col_w, back[1], back[2], back[3])
                open_rect = (back[0], back[1], back[2] - col_w, back[3])
            placed, dev, _ = _strip(col, sorted(col_specs, key=lambda s: -s.target_area_m2), "y")
            zones.update(placed)
            self._deviations.update(dev)
        else:
            open_rect = back

        # 逐间核对：实得面积明显小于目标的，必须写进 warnings，由主创决定减项
        for spec in specs:
            r = zones.get(spec.key)
            if not r:
                continue
            got = max(0.0, (r[2] - r[0]) * (r[3] - r[1])) / 1e6
            if spec.target_area_m2 and got < spec.target_area_m2 * 0.8:
                self._deviations[spec.key] = (
                    f"{spec.name}：目标 {spec.target_area_m2:.1f}㎡，实得 {got:.1f}㎡，"
                    "差额需主创决定从哪让出")

        if open_specs:
            # 开放办公优先整体一块；多于一项时按面积横向分带
            if len(open_specs) == 1:
                zones[open_specs[0].key] = open_rect
            else:
                placed, dev, residual = _strip(
                    open_rect, sorted(open_specs, key=lambda s: -s.target_area_m2), "x")
                zones.update(placed)
                self._deviations.update(dev)
                self._residual = max(self._residual, residual)
        return zones

    def _spine_centre(self, core: Rect, specs: List[RoomSpec],
                      opts: SchemeOptions) -> Dict[str, Rect]:
        """南侧日区 / 中部服务脊（走廊 + 卫浴）/ 北侧夜区——两侧房间都见光。"""
        x0, y0, x1, y1 = core
        W, H = x1 - x0, y1 - y0
        day = [s for s in specs if s.zone in ("day", "entry")]
        night = [s for s in specs if s.zone == "night"]
        svc = [s for s in specs if s.zone == "service"]
        self._deviations: Dict[str, str] = {}

        svc_a = sum(s.target_area_m2 for s in svc) * 1e6
        svc_depth = min(max(svc_a / max(W, 1.0), max((s.min_depth for s in svc), default=1500.0)),
                        3000.0)
        corr = opts.corridor_width_mm
        spine_h = svc_depth + corr

        bed_fit = _depth_for(night, W, 2600.0)
        day_fit = _depth_for(day, W, 2600.0)
        upper = H - spine_h - bed_fit
        if upper < day_fit:
            short = day_fit - upper
            corr = max(1000.0, corr - short)
            spine_h = svc_depth + corr
            upper = H - spine_h - bed_fit
        self._overrun = max(0.0, day_fit - upper)
        day_a = sum(s.target_area_m2 for s in day) * 1e6
        day_h = day_fit if upper <= day_fit else min(max(day_a / max(W, 1.0), day_fit), upper)
        day_h = max(day_h, 2600.0)

        zones: Dict[str, Rect] = {}
        day_band: Rect = (x0, y0, x1, y0 + day_h)
        corr_rect: Rect = (x0, day_band[3], x1, day_band[3] + corr)
        svc_row: Rect = (x0, corr_rect[3], x1, corr_rect[3] + svc_depth)
        night_band: Rect = (x0, svc_row[3], x1, y1)

        placed, dev, residual = _strip(day_band, sorted(day, key=lambda s: s.priority), "x")
        zones.update(placed)
        self._deviations.update(dev)
        self._residual = residual
        zones["corridor"] = corr_rect
        if svc:
            zones.update(_strip_fill(svc_row, sorted(svc, key=lambda s: s.priority), "x"))
        if night:
            n_placed, n_dev, _ = _strip(
                night_band, sorted(night, key=lambda s: -s.target_area_m2), "x"
            )
            zones.update(n_placed)
            self._deviations.update(n_dev)
        return zones

    # ------------------------------------------------------------------
    # canonical objects
    # ------------------------------------------------------------------
    def _make_spaces(self, placed, by_key, opts, env, res) -> List[Space]:
        out: List[Space] = []
        for key, r in placed.items():
            spec = by_key.get(key)
            recipe = spec.recipe if spec else (
                "corridor" if key == "corridor" else
                "hall" if str(key).startswith("reserve") else "hall")
            poly = clip_polygon(_poly_of(r), env) or _poly_of(r)
            area = polygon_area(poly)
            if area < 1.2e6:
                res.warnings.append(f"{key}：裁剪后仅 {area/1e6:.2f} m²，低于可用下限，已丢弃")
                continue
            out.append(
                Space(
                    id=f"S{opts.variant}-{key}",
                    level_id=self.level_id,
                    name=(spec.name if spec else (
                        "走廊" if key == "corridor" else
                        "预留（交通 / 辅助）" if str(key).startswith("reserve") else key)),
                    use=(spec.use if spec else "circulation"),
                    boundary_mm2d=[[round(p[0], 2), round(p[1], 2)] for p in poly],
                    source=f"scheme_{opts.variant}",
                    properties={
                        "scheme": opts.variant,
                        "scheme_key": key,
                        "recipe": recipe,
                        "zone": spec.zone if spec else ("entry" if key == "corridor" else "service"),
                        "target_area_m2": spec.target_area_m2 if spec else None,
                        "daylight_required": bool(spec.daylight) if spec else False,
                        "open_plan": (spec.recipe in OPEN_PLAN_RECIPES) if spec else True,
                        "requires_door": key != "corridor",
                    },
                )
            )
        return out

    def _make_elements(self, placed, by_key, opts, res, env, spaces_list) -> List[Element]:
        lv = self.level_id
        elements: List[Element] = []
        space_id = {k: f"S{opts.variant}-{k}" for k in placed}
        keys = list(placed.keys())

        wall_no = door_no = win_no = fur_no = 0
        adjacency: Dict[str, List[str]] = {k: [] for k in keys}
        wall_of_pair: Dict[Tuple[str, str], str] = {}

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                sa, sb = by_key.get(a), by_key.get(b)
                if (sa and sb and sa.recipe in OPEN_PLAN_RECIPES
                        and sb.recipe in OPEN_PLAN_RECIPES
                        and "corridor" not in (a, b)):
                    continue  # open plan: no partition between them
                seg = _shared_edge(placed[a], placed[b])
                if seg is None:
                    continue
                wall_no += 1
                wid = f"W{opts.variant}-P{wall_no:03d}"
                elements.append(
                    Element(
                        id=wid, type="wall", level_id=lv,
                        geometry={
                            "start": [round(seg[0][0], 2), round(seg[0][1], 2)],
                            "end": [round(seg[1][0], 2), round(seg[1][1], 2)],
                            "thickness_mm": opts.partition_thickness_mm,
                            "height_mm": opts.wall_height_mm,
                            "kind": "partition",
                        },
                        source=f"scheme_{opts.variant}",
                        properties={"scheme": opts.variant, "between": [a, b],
                                    "space_ids": [space_id[a], space_id[b]]},
                    )
                )
                adjacency[a].append(b)
                adjacency[b].append(a)
                wall_of_pair[(a, b)] = wid
                wall_of_pair[(b, a)] = wid

        # every enclosed room gets exactly one door
        door_walls: Dict[str, str] = {}
        for key in keys:
            if key == "corridor":
                continue
            spec = by_key.get(key)
            neighbours = adjacency.get(key, [])

            def rank(n: str) -> Tuple[int, float]:
                ns = by_key.get(n)
                if n == "corridor":
                    return (0, 0.0)
                if ns and ns.recipe in OPEN_PLAN_RECIPES:
                    return (1, 0.0)
                seg = _shared_edge(placed[key], placed[n])
                length = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]) if seg else 0.0
                return (2, -length)

            for n in sorted(neighbours, key=rank):
                seg = _shared_edge(placed[key], placed[n])
                if seg is None:
                    continue
                seg_len = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
                width = (opts.bathroom_door_width_mm
                         if (spec and spec.use == "bathroom") else opts.door_width_mm)
                if seg_len < width + 150:
                    width = max(650.0, seg_len - 150.0)
                if seg_len < width + 120:
                    continue
                wid = wall_of_pair[(key, n)]
                door_no += 1
                elements.append(
                    Element(
                        id=f"D{opts.variant}-{door_no:03d}", type="door", level_id=lv,
                        geometry={
                            "host_wall": wid, "offset_mm": round((seg_len - width) / 2.0, 1),
                            "width_mm": round(width, 1), "height_mm": 2100, "swing": "in",
                            "thickness_mm": opts.partition_thickness_mm,
                        },
                        source=f"scheme_{opts.variant}",
                        properties={"scheme": opts.variant, "from_space": space_id[n],
                                    "to_space": space_id[key]},
                    )
                )
                door_walls[key] = wid
                break
            else:
                if neighbours:
                    res.warnings.append(
                        f"{spec.name if spec else key}：相邻隔墙过短，无法开门（须人工处理）"
                    )

        entry_door = self._entry_door(opts, res)
        if entry_door:
            elements.append(entry_door)

        # exterior windows, placed on the surveyed shell
        spaces = {s.properties["scheme_key"]: s for s in spaces_list}
        for key, space in spaces.items():
            spec = by_key.get(key)
            if not (spec and spec.daylight):
                continue  # corridors and wet rooms are not given a façade window
            best = None
            for wall in self._facade_walls(space):
                seg = self._facade_segment(space, wall)
                if seg is None:
                    continue
                length = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
                if length < 900:
                    continue
                if best is None or length > best[1]:
                    best = (wall, length, seg)
            if best is None:
                if spec and spec.daylight:
                    res.warnings.append(f"{spec.name}：该房间没有可利用的外墙，无法获得自然采光")
                continue
            wall, length, seg = best
            width = min(2100.0, max(900.0, round(length * 0.55 / 100) * 100))
            start_off = self._offset_along_wall(wall, seg[0])
            if start_off is None:
                continue
            win_no += 1
            elements.append(
                Element(
                    id=f"WN{opts.variant}-{win_no:03d}", type="window", level_id=lv,
                    geometry={
                        "host_wall": wall.id,
                        "offset_mm": round(start_off + (length - width) / 2.0, 1),
                        "width_mm": width, "height_mm": opts.window_height_mm,
                        "sill_mm": opts.window_sill_mm,
                    },
                    source=f"scheme_{opts.variant}_on_surveyed_shell",
                    properties={"scheme": opts.variant, "space_id": space.id,
                                "site_confirmation_required": wall.uncertain},
                )
            )

        if opts.furnish:
            for key, space in spaces.items():
                spec = by_key.get(key)
                if spec is None or not spec.furniture:
                    continue
                for item in furniture_layout(placed[key], spec.recipe, spec.furniture):
                    fur_no += 1
                    elements.append(
                        Element(
                            id=f"F{opts.variant}-{fur_no:03d}", type="furniture",
                            level_id=lv, geometry=item, source=f"scheme_{opts.variant}",
                            properties={"scheme": opts.variant, "space_id": space.id,
                                        "category": item["category"]},
                        )
                    )
        return elements

    # -- shell helpers ---------------------------------------------------
    def _base_walls(self) -> List[Element]:
        return [e for e in self.project.by_type("wall") if not e.source.startswith("scheme_")]

    def _facade_walls(self, space: Space) -> List[Element]:
        env = envelope_polygon(self.project, self.level_id)
        hugs = _hugs_envelope(space.boundary_mm2d, env, tol=40.0)
        if not hugs:
            return []
        out = []
        for w in self._base_walls():
            axis = w.wall_axis()
            if not axis:
                continue
            # 外墙通常是一条通长线，一段墙可能服务好几个房间：不能用"墙中点
            # 靠近房间贴边"来判断（中点往往落在别的房间上），要看墙段与该贴边
            # 是否有共线重叠。
            if any(_wall_overlaps(axis, seg, tol=120.0) for seg in hugs):
                out.append(w)
        return out

    def _facade_segment(self, space: Space, wall: Element) -> Optional[Seg]:
        """Span of this room along the given façade wall.

        The wall's axis is its centre-line, which sits half a thickness outside
        the interior face the room actually touches — so the tolerance has to
        follow the wall thickness, not a fixed constant.
        """
        axis = wall.wall_axis()
        if not axis:
            return None
        (x1, y1), (x2, y2) = axis
        tol = float(wall.geometry.get("thickness_mm", 200)) / 2.0 + 80.0
        pts: List[float] = []
        poly = space.boundary_mm2d
        for i in range(len(poly)):
            px, py = poly[i]
            t = _project_on_segment((px, py), (x1, y1), (x2, y2))
            if t is None:
                continue
            proj = (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            if math.hypot(proj[0] - px, proj[1] - py) <= tol:
                pts.append(t)
        if len(pts) < 2:
            return None
        lo, hi = min(pts), max(pts)
        if hi - lo < 1e-6:
            return None
        return ((x1 + (x2 - x1) * lo, y1 + (y2 - y1) * lo),
                (x1 + (x2 - x1) * hi, y1 + (y2 - y1) * hi))

    def _offset_along_wall(self, wall: Element, pt: Tuple[float, float]) -> Optional[float]:
        axis = wall.wall_axis()
        if not axis:
            return None
        t = _project_on_segment(pt, axis[0], axis[1], clamp=True)
        return None if t is None else t * wall.wall_length_mm()

    def _entry_door(self, opts: SchemeOptions, res: SchemeResult) -> Optional[Element]:
        env = envelope_polygon(self.project, self.level_id)
        ex, ey = entry_point(self.project, env)
        best = None
        best_d = float("inf")
        for w in self._base_walls():
            axis = w.wall_axis()
            if not axis:
                continue
            t = _project_on_segment((ex, ey), axis[0], axis[1], clamp=True)
            if t is None:
                continue
            px = axis[0][0] + (axis[1][0] - axis[0][0]) * t
            py = axis[0][1] + (axis[1][1] - axis[0][1]) * t
            d = math.hypot(px - ex, py - ey)
            if d < best_d:
                best_d, best = d, (w, t)
        if best is None or best_d > 2000.0:
            res.warnings.append("入户点附近没有已测绘的外墙，入户门未生成")
            return None
        wall, t = best
        length = wall.wall_length_mm()
        width = min(opts.entry_door_width_mm, max(850.0, length - 200.0))
        offset = min(max(t * length - width / 2.0, 100.0), max(length - width - 100.0, 100.0))
        return Element(
            id=f"DE{opts.variant}-001", type="door", level_id=self.level_id,
            geometry={"host_wall": wall.id, "offset_mm": round(offset, 1),
                      "width_mm": round(width, 1), "height_mm": 2200, "swing": "in",
                      "kind": "entry"},
            source=f"scheme_{opts.variant}",
            properties={"scheme": opts.variant, "site_confirmation_required": wall.uncertain},
        )

    # -- metrics ---------------------------------------------------------
    def _metrics(self, res, by_key, opts, placed) -> Dict[str, object]:
        rooms = [s for s in res.spaces if s.use not in ("envelope", "outdoor")]
        total = sum(s.area_m2 for s in rooms)
        walls = [e for e in res.elements if e.type == "wall"]
        doors = [e for e in res.elements if e.type == "door"]
        windows = [e for e in res.elements if e.type == "window"]
        furn = [e for e in res.elements if e.type == "furniture"]
        target = sum(s.target_area_m2 for s in by_key.values())
        corr = next((s for s in rooms if s.properties.get("scheme_key") == "corridor"), None)
        glaz = sum(float(e.geometry.get("width_mm", 0)) * float(e.geometry.get("height_mm", 0)) / 1e6
                   for e in windows)
        day_rooms = [s for s in rooms if s.properties.get("daylight_required")]
        served = {e.properties.get("space_id") for e in windows if e.properties.get("space_id")}
        present = {s.properties.get("scheme_key") for s in rooms}
        missing = [k for k in by_key if k not in present]
        return {
            "variant": res.variant,
            "strategy": opts.strategy,
            "room_count": len(rooms),
            "planned_rooms": len(by_key),
            "missing_rooms": missing,
            "total_area_m2": round(total, 2),
            "program_target_m2": round(target, 2),
            "program_delta_m2": round(total - target, 2),
            "partition_count": len(walls),
            "partition_length_m": round(sum(w.wall_length_mm() for w in walls) / 1000.0, 2),
            "door_count": len(doors),
            "window_count": len(windows),
            "furniture_count": len(furn),
            "corridor_area_m2": round(corr.area_m2, 2) if corr else 0.0,
            "corridor_ratio": round((corr.area_m2 / total) if (corr and total) else 0.0, 3),
            "open_plan_ratio": round(
                sum(s.area_m2 for s in rooms if s.properties.get("open_plan")) / max(total, 1e-9), 3
            ),
            "glazing_ratio": round(glaz / max(total, 1e-9), 3),
            "glazing_ratio_inverse": round((total / glaz) if glaz else 0.0, 2),
            "daylight_rooms_served": f"{len(served & {s.id for s in day_rooms})}/{len(day_rooms)}",
            "areas_m2": {s.id: round(s.area_m2, 2) for s in rooms},
            "warnings": list(res.warnings),
        }


# --------------------------------------------------------------------------
# geometry micro-helpers
# --------------------------------------------------------------------------
def _project_on_segment(p, a, b, clamp: bool = False) -> Optional[float]:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom < 1e-9:
        return None
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / denom
    if clamp:
        return min(max(t, 0.0), 1.0)
    return t if -1e-6 <= t <= 1 + 1e-6 else None


def _hugs_envelope(poly, env, tol: float = 40.0) -> List[Seg]:
    out: List[Seg] = []
    n = len(poly)
    for i in range(n):
        p = poly[i]
        q = poly[(i + 1) % n]
        for j in range(len(env)):
            a = env[j]
            b = env[(j + 1) % len(env)]
            if _seg_on_seg(p, q, a, b, tol):
                out.append(((float(p[0]), float(p[1])), (float(q[0]), float(q[1]))))
                break
    return out


def _wall_overlaps(wall: Seg, hug: Seg, tol: float = 120.0) -> bool:
    """墙段与房间贴边是否共线且有重叠（用于判断这面墙是否给这个房间采光）。"""
    (ax, ay), (bx, by) = wall
    (cx, cy), (dx, dy) = hug
    # 贴边两端点到墙线的距离都要在容差内（共线）
    for (px, py) in ((cx, cy), (dx, dy)):
        wx, wy = bx - ax, by - ay
        L = math.hypot(wx, wy)
        if L < 1e-6:
            return False
        dist = abs((px - ax) * wy - (py - ay) * wx) / L
        if dist > tol:
            return False
    # 投影重叠长度
    wx, wy = bx - ax, by - ay
    L = math.hypot(wx, wy)
    ux, uy = wx / L, wy / L

    def t(px: float, py: float) -> float:
        return (px - ax) * ux + (py - ay) * uy

    t1, t2 = sorted((t(cx, cy), t(dx, dy)))
    return min(t2, L) - max(t1, 0.0) > 1.0


def _seg_on_seg(p, q, a, b, tol: float) -> bool:
    for pt in (p, q):
        t = _project_on_segment(pt, a, b, clamp=True)
        proj = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        if math.hypot(proj[0] - pt[0], proj[1] - pt[1]) > tol:
            return False
    return True


def _point_near_polyline(pt, segs: Sequence[Seg], tol: float = 300.0) -> bool:
    for a, b in segs:
        t = _project_on_segment(pt, a, b, clamp=True)
        proj = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        if math.hypot(proj[0] - pt[0], proj[1] - pt[1]) <= tol:
            return True
    return False


# --------------------------------------------------------------------------
# furniture rules
# --------------------------------------------------------------------------
def furniture_layout(r: Rect, recipe: str, items: Sequence[str],
                     side_of_door: Optional[str] = None) -> List[Dict[str, object]]:
    """Place furniture along the long wall opposite the door, then wrap around.

    Rule-based and inspectable on purpose: a designer can read the rule and
    argue with it, which is the point at scheme stage.
    """
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    out: List[Dict[str, object]] = []
    if w < 900 or h < 900:
        return out

    # anchor against the longest wall; a shallow room anchors top/bottom
    anchor = "N" if w >= h else "W"
    if h < 3000 and w > h:
        anchor = "N"
    elif w < 3000 and h > w:
        anchor = "W"

    def place(item: str, offset: float) -> bool:
        spec = FURNITURE.get(item)
        if not spec:
            return False
        sw, sd, sh = spec["size"]
        gap = 60.0
        if anchor in ("N", "S"):
            if sw > w - 2 * gap:
                return False
            cy = (y1 - sd / 2 - gap) if anchor == "N" else (y0 + sd / 2 + gap)
            cx = x0 + offset + sw / 2
            if cx + sw / 2 > x1 - gap:
                return False
            rot = 0.0 if anchor == "N" else 180.0
        else:
            if sw > h - 2 * gap:
                return False
            cx = (x0 + sd / 2 + gap) if anchor == "W" else (x1 - sd / 2 - gap)
            cy = y0 + offset + sw / 2
            if cy + sw / 2 > y1 - gap:
                return False
            rot = 90.0 if anchor == "W" else 270.0
        out.append({
            "category": item,
            "center": [round(cx, 1), round(cy, 1)],
            "size_mm": [sw, sd, sh],
            "rotation_deg": rot,
            "anchor_edge": anchor,
        })
        return True

    def run(seq: Sequence[str]) -> None:
        offset = 100.0
        span = (w if anchor in ("N", "S") else h) - 200.0
        for item in seq:
            spec = FURNITURE.get(item)
            if not spec:
                continue
            sw = spec["size"][0]
            if offset + sw > span:
                continue
            if place(item, offset):
                offset += sw + 100.0

    primary = [i for i in items if i in ("sofa", "bed_king", "bed_queen", "kitchen_run",
                                         "desk", "shoe_cabinet", "bathtub")]
    secondary = [i for i in items if i not in primary and i not in ("coffee_table",)]
    if primary:
        run(primary)
    if secondary:
        run(secondary)
    if "coffee_table" in items:
        sw, sd, sh = FURNITURE["coffee_table"]["size"]
        out.append({
            "category": "coffee_table",
            "center": [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)],
            "size_mm": [sw, sd, sh], "rotation_deg": 0.0, "anchor_edge": "centre",
        })
    if "kitchen_island" in items and w * h > 15e6:
        sw, sd, sh = FURNITURE["kitchen_island"]["size"]
        out.append({
            "category": "kitchen_island",
            "center": [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)],
            "size_mm": [sw, sd, sh], "rotation_deg": 0.0, "anchor_edge": "centre",
        })
    return out
