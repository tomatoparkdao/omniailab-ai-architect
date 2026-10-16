"""Drawing primitives — a backend-neutral plan description.

Both the ezdxf writer and the native R12 writer serialise the same primitive
list, so the drawing cannot silently differ between backends.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..geometry import point_along
from ..model import Element, Project, Space, polygon_centroid

LAYERS: Dict[str, Dict[str, Any]] = {
    "A-WALL": {"color": 7, "linetype": "CONTINUOUS"},
    "A-WALL-PART": {"color": 8, "linetype": "CONTINUOUS"},
    "A-DOOR": {"color": 3, "linetype": "CONTINUOUS"},
    "A-GLAZ": {"color": 4, "linetype": "CONTINUOUS"},
    "A-FURN": {"color": 9, "linetype": "CONTINUOUS"},
    "A-FLOR-IDEN": {"color": 6, "linetype": "CONTINUOUS"},
    "A-ANNO-DIMS": {"color": 2, "linetype": "CONTINUOUS"},
    "A-ANNO-TEXT": {"color": 2, "linetype": "CONTINUOUS"},
    "A-AREA": {"color": 8, "linetype": "DASHED"},
    "A-UNCERTAIN": {"color": 1, "linetype": "DASHDOT"},
    "G-ANNO-TTLB": {"color": 7, "linetype": "CONTINUOUS"},
}

TEXT_HEIGHT = {"room": 160.0, "area": 110.0, "dim": 90.0, "title": 220.0, "note": 100.0}
MM_PER_M = 1000.0


@dataclass
class Prim:
    kind: str          # polyline | line | text | circle | arc
    layer: str
    points: List[Tuple[float, float]] = field(default_factory=list)
    closed: bool = False
    text: str = ""
    height: float = 100.0
    center: Tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0
    start_angle: float = 0.0
    end_angle: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "layer": self.layer, "closed": self.closed,
            "text": self.text, "height": self.height,
            "points": [[round(x, 2), round(y, 2)] for x, y in self.points],
        }


def free_spans(length: float, openings: Sequence[Element]) -> List[Tuple[float, float]]:
    """Wall segments left once the openings are removed."""
    cuts = sorted(
        (max(0.0, float(o.geometry.get("offset_mm", 0.0))),
         min(length, float(o.geometry.get("offset_mm", 0.0)) + float(o.geometry.get("width_mm", 0.0))))
        for o in openings
    )
    merged: List[Tuple[float, float]] = []
    for a, b in cuts:
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    spans: List[Tuple[float, float]] = []
    cursor = 0.0
    for a, b in merged:
        if a - cursor > 1:
            spans.append((cursor, a))
        cursor = max(cursor, b)
    if length - cursor > 1:
        spans.append((cursor, length))
    return spans


def build_primitives(
    project: Project,
    level_id: Optional[str] = None,
    include_furniture: bool = True,
    include_dims: bool = True,
    include_titleblock: bool = True,
    title: str = "平面布置图",
    scheme: str = "",
    depth: str = "schematic",
) -> List[Prim]:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    prims: List[Prim] = []

    walls = [e for e in project.by_type("wall") if e.level_id == lid]
    doors = [e for e in project.by_type("door") if e.level_id == lid]
    windows = [e for e in project.by_type("window") if e.level_id == lid]
    furniture = [e for e in project.by_type("furniture") if e.level_id == lid]
    spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]

    holes: Dict[str, List[Element]] = {}
    for o in (*doors, *windows):
        holes.setdefault(str(o.geometry.get("host_wall") or ""), []).append(o)

    for w in walls:
        axis = w.wall_axis()
        if not axis:
            continue
        layer = "A-UNCERTAIN" if w.uncertain else (
            "A-WALL-PART" if w.geometry.get("kind") == "partition" else "A-WALL"
        )
        th = float(w.geometry.get("thickness_mm", 200.0))
        length = w.wall_length_mm()
        (x1, y1), (x2, y2) = axis
        for a, b in free_spans(length, holes.get(w.id, [])):
            rect = _wall_rect(w, a, b, th)
            if rect:
                prims.append(Prim("polyline", layer, rect, closed=True))
            if layer == "A-WALL":  # structural walls read as solid at any scale
                prims.append(Prim("line", layer, [rect[0], rect[2]]))
        for o in holes.get(w.id, []):
            off = float(o.geometry.get("offset_mm", 0))
            ow = float(o.geometry.get("width_mm", 0))
            for edge in (off, off + ow):
                pt = point_along(w, edge)
                ang = math.atan2(y2 - y1, x2 - x1)
                nx, ny = -math.sin(ang), math.cos(ang)
                prims.append(Prim("line", layer, [
                    (pt[0] + nx * th / 2, pt[1] + ny * th / 2),
                    (pt[0] - nx * th / 2, pt[1] - ny * th / 2),
                ]))

    for d in doors:
        host = _host_axis(project, d)
        if not host:
            continue
        (p1, _p2, ang) = host
        w = float(d.geometry.get("width_mm", 900))
        off = float(d.geometry.get("offset_mm", 0))
        start = _advance(p1, ang, off)
        end = _advance(p1, ang, off + w)
        leaf_ang = ang + math.radians(90)
        prims.append(Prim("line", "A-DOOR", [start, _advance(start, leaf_ang, w)]))
        prims.append(Prim("arc", "A-DOOR", center=start, radius=w,
                          start_angle=math.degrees(ang), end_angle=math.degrees(leaf_ang)))
        prims.append(Prim("line", "A-DOOR", [start, end]))

    for win in windows:
        host = _host_axis(project, win)
        if not host:
            continue
        (p1, _p2, ang) = host
        w = float(win.geometry.get("width_mm", 1500))
        off = float(win.geometry.get("offset_mm", 0))
        th = float(win.geometry.get("host_thickness_mm", 240))
        a = _advance(p1, ang, off)
        b = _advance(p1, ang, off + w)
        nx, ny = -math.sin(ang), math.cos(ang)
        for k in (-1, 0, 1):
            dd = k * th / 2
            prims.append(Prim("line", "A-GLAZ", [
                (a[0] + nx * dd, a[1] + ny * dd),
                (b[0] + nx * dd, b[1] + ny * dd),
            ]))

    if include_furniture:
        for f in furniture:
            cx, cy = f.geometry.get("center", [0, 0])
            sw, sd, _sh = f.geometry.get("size_mm", [600, 600, 600])
            rot = math.radians(float(f.geometry.get("rotation_deg", 0) or 0))
            hw, hd = sw / 2.0, sd / 2.0
            pts = [
                (cx + x * math.cos(rot) - y * math.sin(rot),
                 cy + x * math.sin(rot) + y * math.cos(rot))
                for x, y in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))
            ]
            prims.append(Prim("polyline", "A-FURN", list(pts), closed=True))
            prims.append(Prim("line", "A-FURN", [pts[0], pts[2]]))

    for s in spaces:
        cx, cy = polygon_centroid(s.boundary_mm2d)
        prims.append(Prim("polyline", "A-AREA",
                          [(float(p[0]), float(p[1])) for p in s.boundary_mm2d], closed=True))
        prims.append(Prim("text", "A-ANNO-TEXT", center=(cx, cy),
                          text=s.name or s.use, height=TEXT_HEIGHT["room"]))
        prims.append(Prim("text", "A-ANNO-TEXT", center=(cx, cy - 260),
                          text=f"{s.area_m2:.2f} m2", height=TEXT_HEIGHT["area"]))

    if include_dims and spaces:
        pts = [p for s in spaces for p in s.boundary_mm2d]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        off = 1200.0
        prims += _dim_chain((x0, y0 - off), (x1, y0 - off), f"{x1 - x0:.0f}")
        prims += _dim_chain((x0 - off, y0), (x0 - off, y1), f"{y1 - y0:.0f}")

    if include_titleblock and spaces:
        pts = [p for s in spaces for p in s.boundary_mm2d]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bx, by = max(xs) + 1500.0, min(ys)
        w, h = 5200.0, 2200.0
        prims.append(Prim("polyline", "G-ANNO-TTLB",
                          [(bx, by), (bx + w, by), (bx + w, by + h), (bx, by + h)], closed=True))
        prims.append(Prim("line", "G-ANNO-TTLB",
                          [(bx, by + h - 700), (bx + w, by + h - 700)]))
        lines = [
            (f"{project.name or project.project_id}", TEXT_HEIGHT["title"]),
            (f"{title}   1:50", TEXT_HEIGHT["note"]),
            (f"图号 A-{lid}-01   修订 r{project.revision}   深度 {depth}", TEXT_HEIGHT["note"]),
            ("本图为方案阶段图纸，非施工图；结构、消防、机电须经持证专业人员复核", TEXT_HEIGHT["note"]),
            ("OmniArchitect · 由 Canonical Spatial Model 自动生成", TEXT_HEIGHT["note"]),
        ]
        y = by + h - 320
        for text, hh in lines:
            prims.append(Prim("text", "G-ANNO-TTLB", center=(bx + 150, y),
                              text=text, height=hh))
            y -= hh * 2.6 + (120 if hh == TEXT_HEIGHT["title"] else 0)

    return prims


def _wall_rect(wall: Element, a: float, b: float, th: float) -> Optional[List[Tuple[float, float]]]:
    p1 = point_along(wall, a)
    p2 = point_along(wall, b)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None
    nx, ny = -dy / length * th / 2.0, dx / length * th / 2.0
    return [
        (p1[0] + nx, p1[1] + ny),
        (p2[0] + nx, p2[1] + ny),
        (p2[0] - nx, p2[1] - ny),
        (p1[0] - nx, p1[1] - ny),
    ]


def _dim_chain(a, b, label: str) -> List[Prim]:
    return [
        Prim("line", "A-ANNO-DIMS", [a, b]),
        Prim("circle", "A-ANNO-DIMS", center=a, radius=40),
        Prim("circle", "A-ANNO-DIMS", center=b, radius=40),
        Prim("text", "A-ANNO-DIMS",
             center=((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0 + 180),
             text=label, height=TEXT_HEIGHT["dim"]),
    ]


def _host_axis(project: Project, opening: Element):
    """Prefer the resolved axis stashed by `resolve_host_axes`; fall back to lookup."""
    cached = opening.properties.get("_host_axis")
    if cached:
        try:
            return (tuple(cached[0]), tuple(cached[1]), float(cached[2]))
        except Exception:
            pass
    host_id = str(opening.geometry.get("host_wall") or "")
    for w in project.by_type("wall"):
        if w.id != host_id:
            continue
        axis = w.wall_axis()
        if axis is None:
            return None
        (x1, y1), (x2, y2) = axis
        return ((x1, y1), (x2, y2), math.atan2(y2 - y1, x2 - x1))
    return None


def _advance(p, angle_rad: float, dist: float) -> Tuple[float, float]:
    return (p[0] + math.cos(angle_rad) * dist, p[1] + math.sin(angle_rad) * dist)


def resolve_host_axes(project: Project) -> None:
    """Attach a resolved host axis to every opening so no writer can silently
    skip one because it could not re-derive the host."""
    import math as _m

    walls = {w.id: w for w in project.by_type("wall")}
    for o in project.elements:
        if not o.is_opening:
            continue
        w = walls.get(str(o.geometry.get("host_wall") or ""))
        if w is None:
            continue
        axis = w.wall_axis()
        if axis is None:
            continue
        (x1, y1), (x2, y2) = axis
        o.properties["_host_axis"] = [[x1, y1], [x2, y2],
                                      _m.atan2(y2 - y1, x2 - x1)]
        o.geometry["host_thickness_mm"] = float(w.geometry.get("thickness_mm", 200))
