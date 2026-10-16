"""Geometric operations on the canonical model.

Shapely is used when available (accurate polygon clipping for non-rectangular
envelopes); a pure-Python fallback keeps the core usable without it.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

from .model import Element, Space, polygon_area_mm2

Point = Tuple[float, float]
Poly = Sequence[Sequence[float]]

try:  # pragma: no cover - exercised implicitly
    from shapely.geometry import Polygon, Point as ShapelyPoint  # type: ignore
    from shapely.ops import unary_union  # type: ignore

    HAS_SHAPELY = True
except Exception:  # pragma: no cover
    HAS_SHAPELY = False


def polygon_to_shapely(points: Poly):
    if not HAS_SHAPELY or len(points) < 3:
        return None
    try:
        poly = Polygon([(float(p[0]), float(p[1])) for p in points])
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None


def polygon_area(points: Poly) -> float:
    poly = polygon_to_shapely(points)
    if poly is not None:
        return float(poly.area)
    return polygon_area_mm2(points)


def point_in_polygon(pt: Point, points: Poly) -> bool:
    x, y = pt
    inside = False
    n = len(points)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(points[i][0]), float(points[i][1])
        xj, yj = float(points[j][0]), float(points[j][1])
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def distance_to_boundary(poly, pt: Point) -> float:
    """Distance from a point to a shapely polygon's boundary (mm)."""
    if poly is None:
        return float("inf")
    p = ShapelyPoint(pt[0], pt[1])
    return float(poly.boundary.distance(p))


def rect(x: float, y: float, w: float, h: float) -> List[List[float]]:
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def rect_center(r: Sequence[Sequence[float]]) -> Point:
    xs = [p[0] for p in r]
    ys = [p[1] for p in r]
    return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)


def rect_size(r: Sequence[Sequence[float]]) -> Tuple[float, float]:
    xs = [p[0] for p in r]
    ys = [p[1] for p in r]
    return (max(xs) - min(xs), max(ys) - min(ys))


def clip_polygon(points: Poly, clip: Poly) -> Optional[List[List[float]]]:
    """Intersect two polygons; returns an outer ring or None.

    With shapely this is exact. Without it, an axis-aligned rectangle is clipped
    by a rectilinear ring using a grid decomposition plus boundary tracing —
    still exact for rectilinear geometry, which is what a floor plan is.
    """
    a = polygon_to_shapely(points)
    b = polygon_to_shapely(clip)
    if a is None or b is None:
        return _rectilinear_clip(points, clip)
    inter = a.intersection(b)
    if inter.is_empty:
        return None
    if inter.geom_type == "MultiPolygon":
        inter = max(inter.geoms, key=lambda g: g.area)
    if inter.geom_type != "Polygon":
        return None
    return [[float(x), float(y)] for x, y in inter.exterior.coords[:-1]]


def _is_axis_rect(points: Poly) -> bool:
    if len(points) != 4:
        return False
    xs = {round(float(p[0]), 6) for p in points}
    ys = {round(float(p[1]), 6) for p in points}
    return len(xs) == 2 and len(ys) == 2


def _rectilinear_clip(subject: Poly, clip: Poly) -> Optional[List[List[float]]]:
    """Grid-decompose, keep cells inside both, then trace the boundary loops."""
    if not _is_axis_rect(subject) or len(clip) < 3:
        return None
    rx0 = min(float(p[0]) for p in subject)
    rx1 = max(float(p[0]) for p in subject)
    ry0 = min(float(p[1]) for p in subject)
    ry1 = max(float(p[1]) for p in subject)
    if rx1 - rx0 < 1e-9 or ry1 - ry0 < 1e-9:
        return None

    xs = sorted({round(float(p[0]), 6) for p in clip} | {rx0, rx1})
    ys = sorted({round(float(p[1]), 6) for p in clip} | {ry0, ry1})
    xs = [x for x in xs if rx0 - 1e-9 <= x <= rx1 + 1e-9]
    ys = [y for y in ys if ry0 - 1e-9 <= y <= ry1 + 1e-9]

    cells: List[Tuple[float, float, float, float]] = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx0, cx1, cy0, cy1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            if cx1 - cx0 < 1e-9 or cy1 - cy0 < 1e-9:
                continue
            if not point_in_polygon(((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0), clip):
                continue
            cells.append((cx0, cy0, cx1, cy1))
    if not cells:
        return None

    loops = _trace_loops(cells)
    if not loops:
        return None
    loops.sort(key=lambda lp: -polygon_area_mm2(lp))
    return loops[0]


def _trace_loops(cells: Sequence[Tuple[float, float, float, float]]) -> List[List[List[float]]]:
    """Boundary loops of a union of axis-aligned cells: shared edges cancel."""
    keys: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = []
    for x0, y0, x1, y1 in cells:
        corners = [
            ((x0, y0), (x1, y0), "h"),
            ((x1, y0), (x1, y1), "v"),
            ((x0, y0), (x0, y1), "v"),
            ((x0, y1), (x1, y1), "h"),
        ]
        for a, b, orient in corners:
            keys.append((a, b, orient))

    # cancel edges appearing twice (interior faces)
    pool: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    used = [False] * len(keys)
    for i, (a, b, _o) in enumerate(keys):
        if used[i]:
            continue
        matched = False
        for j in range(i + 1, len(keys)):
            if used[j]:
                continue
            c, d, _o2 = keys[j]
            if {a, b} == {c, d}:
                used[i] = used[j] = True
                matched = True
                break
        if not matched:
            used[i] = True
            pool.append((a, b))

    loops: List[List[List[float]]] = []
    guard = 0
    while pool and guard < 10000:
        guard += 1
        start, nxt = pool.pop(0)
        loop = [start, nxt]
        while loop[-1] != loop[0] and guard < 10000:
            guard += 1
            here = loop[-1]
            found = None
            for idx, (a, b) in enumerate(pool):
                if a == here:
                    found = (idx, b)
                    break
                if b == here:
                    found = (idx, a)
                    break
            if not found:
                break
            pool.pop(found[0])
            loop.append(found[1])
            if len(loop) > 4000:
                break
        if len(loop) >= 4 and loop[0] == loop[-1]:
            ring = loop[:-1]
            if polygon_area_mm2(ring) > 1.0:
                loops.append([[float(p[0]), float(p[1])] for p in ring])
    return loops


def clip_rect_to(points: Poly, clip: Poly) -> Optional[Tuple[List[List[float]], bool]]:
    """Clip and report whether clipping actually happened."""
    out = clip_polygon(points, clip)
    if out is None:
        return None
    original = polygon_area(points)
    clipped = polygon_area(out)
    return out, (original - clipped) > 1.0


# --------------------------------------------------------------------------
# walls
# --------------------------------------------------------------------------
def wall_polygon(element: Element) -> Optional[List[List[float]]]:
    """Footprint of a wall as a rectangle polygon."""
    axis = element.wall_axis()
    if axis is None:
        return None
    (x1, y1), (x2, y2) = axis
    th = float(element.geometry.get("thickness_mm", 200.0))
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return None
    nx, ny = -dy / length * th / 2.0, dx / length * th / 2.0
    return [
        [x1 + nx, y1 + ny],
        [x2 + nx, y2 + ny],
        [x2 - nx, y2 - ny],
        [x1 - nx, y1 - ny],
    ]


def wall_direction(element: Element) -> str:
    axis = element.wall_axis()
    if axis is None:
        return "unknown"
    (x1, y1), (x2, y2) = axis
    if abs(y2 - y1) < 1e-6:
        return "horizontal"
    if abs(x2 - x1) < 1e-6:
        return "vertical"
    return "diagonal"


def point_along(element: Element, offset_mm: float) -> Point:
    """Point at a given distance along the wall axis from its start."""
    axis = element.wall_axis()
    if axis is None:
        return (0.0, 0.0)
    (x1, y1), (x2, y2) = axis
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    t = offset_mm / length
    return (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)


# --------------------------------------------------------------------------
# checks used by the QA stage
# --------------------------------------------------------------------------
def space_bbox(space: Space) -> Tuple[float, float, float, float]:
    return space.bbox()


def furniture_clearance_issues(
    project,
    min_clearance_mm: float = 600.0,
) -> List[str]:
    """Report furniture placed closer than `min_clearance_mm` to another item
    in the same space (a cheap proxy for circulation blockage)."""
    issues: List[str] = []
    spaces = {s.id: s for s in project.spaces}
    by_space: dict[str, list[Element]] = {}
    for e in project.by_type("furniture"):
        by_space.setdefault(str(e.geometry.get("space_id") or ""), []).append(e)

    for space_id, items in by_space.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                ca = a.geometry.get("center")
                cb = b.geometry.get("center")
                if not ca or not cb:
                    continue
                sa = a.geometry.get("size_mm") or [0, 0, 0]
                sb = b.geometry.get("size_mm") or [0, 0, 0]
                dx = abs(ca[0] - cb[0]) - (sa[0] + sb[0]) / 2.0
                dy = abs(ca[1] - cb[1]) - (sa[1] + sb[1]) / 2.0
                gap = max(dx, dy)
                if gap < min_clearance_mm:
                    issues.append(
                        f"{a.id}↔{b.id} in {space_id}: gap {gap:.0f}mm < {min_clearance_mm:.0f}mm"
                    )
    return issues


def opening_area_m2(project) -> float:
    return sum(
        float(e.geometry.get("width_mm", 0))
        * float(e.geometry.get("height_mm", 0))
        / 1e6
        for e in project.elements
        if e.is_opening
    )


def glazing_ratio(project, level_id: str | None = None) -> float:
    """Window area / floor area — a crude daylight proxy, not a compliance check."""
    floor = 0.0
    glaz = 0.0
    for s in project.spaces:
        if level_id and s.level_id != level_id:
            continue
        if s.use in ("envelope", "outdoor"):
            continue
        floor += s.area_m2
    for e in project.by_type("window"):
        if level_id and e.level_id != level_id:
            continue
        glaz += (
            float(e.geometry.get("width_mm", 0))
            * float(e.geometry.get("height_mm", 0))
            / 1e6
        )
    return (glaz / floor) if floor else 0.0
