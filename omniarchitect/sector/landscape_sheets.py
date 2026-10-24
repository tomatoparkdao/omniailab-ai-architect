"""Landscape specialist sheets: paving, planting, grading, node index.

Every sheet is read straight out of the L-SITE model. Nothing is invented:
polygons are the ones S3 confirmed, tree positions are the ones the concept
placed, design levels are the ones stored per space. Where a garden needs a
number the model does not hold — species, nursery size, slope, construction —
the sheet says so instead of guessing.

Why separate sheets and not one coloured plan: a paving contractor, a nursery
and a drainage subcontractor read three different drawings. Mixing them means
each of them has to ignore most of the sheet.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import math
from html import escape
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple

from ..adapters import DxfAdapter
from ..adapters.drawing import Prim

#: Layer → fill, used by the SVG preview only (CAD keeps its own layer colours).
FILLS = {
    "L-ZONE-PAVE": "#ded3c1",
    "L-ZONE-GRAVEL": "#e2ddd2",
    "L-ZONE-PATH": "#cdbb9b",
    "L-ZONE-PLANT": "#c6d8b2",
    "L-ZONE-LAWN": "#b3cd99",
    "L-ZONE-WATER": "#a8cbdd",
}

#: What each landscape space is, in words a client can check against the plan.
USE_LABEL = {"paving": "硬质铺装", "circulation": "园路", "planting": "绿地与种植",
             "water": "水面", "lawn": "草坪与地被"}

INFILL_LABEL = {"gravel": "透水砂砾", "lawn": "草坪与地被"}

#: Suggested canopy so trees read as trees on paper. Not a nursery spec.
CANOPY_MM = 4500.0


def _spaces(project: Any, uses: Sequence[str]) -> List[Any]:
    return [s for s in project.spaces_on("L-SITE")
            if s.use in uses and len(s.boundary_mm2d) >= 3]


def _trees(project: Any) -> List[Any]:
    return [e for e in project.by_type("other")
            if e.level_id == "L-SITE"
            and e.properties.get("landscape_kind") == "tree"
            and len(e.geometry.get("center") or []) == 2]


def _nodes(project: Any) -> List[Any]:
    return [e for e in project.by_type("other")
            if e.level_id == "L-SITE"
            and e.properties.get("landscape_kind") == "view_node"
            and len(e.geometry.get("center") or []) == 2]


def _layer_of(space: Any) -> str:
    kind = space.properties.get("infill_kind")
    if kind == "gravel":
        return "L-ZONE-GRAVEL"
    if kind == "lawn":
        return "L-ZONE-LAWN"
    return {"paving": "L-ZONE-PAVE", "circulation": "L-ZONE-PATH",
            "planting": "L-ZONE-PLANT", "water": "L-ZONE-WATER",
            "lawn": "L-ZONE-LAWN"}.get(space.use, "L-ZONE-PAVE")


def _label_of(space: Any) -> str:
    kind = space.properties.get("infill_kind")
    if kind in INFILL_LABEL:
        return INFILL_LABEL[kind]
    return USE_LABEL.get(space.use, space.use)


# ----------------------------------------------------------------------
def _arrow(x0: float, y0: float, x1: float, y1: float, layer: str) -> List[Prim]:
    """A line with a real arrowhead — drainage direction needs no legend."""
    head = 900.0
    ang = math.atan2(y1 - y0, x1 - x0)
    out = [Prim("line", layer, [(x0, y0), (x1, y1)])]
    for sign in (1, -1):
        a = ang + math.pi + sign * math.radians(22)
        out.append(Prim("line", layer, [(x1, y1),
                                        (x1 + head * math.cos(a),
                                         y1 + head * math.sin(a))]))
    return out


# ----------------------------------------------------------------------
def _merge_rings(prims: Sequence[Prim], layer: str) -> List[Tuple[list, list]]:
    """Union the same-material pieces into (outer ring, holes) pairs.

    The model stores paving as dozens of measurable pieces — good for a take-off,
    unreadable on a drawing. Unioning them for *display* keeps the area numbers
    coming from the pieces while the plan shows one bed, one path, one water body.
    Holes matter: a loop path unioned without its inner ring turns into a solid
    disc that hides the garden inside it.
    """
    raw = [list(p.points) for p in prims
           if p.kind == "polyline" and p.closed and p.layer == layer and len(p.points) >= 3]
    if not raw:
        return []
    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        merged = unary_union([Polygon(r) for r in raw])
        shapes = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    except Exception:                      # noqa: BLE001  没有 shapely 就按原样画
        return [(r, []) for r in raw]
    out: List[Tuple[list, list]] = []
    for shape in shapes:
        if shape.is_empty or shape.geom_type != "Polygon":
            continue
        outer = [(float(x), float(y)) for x, y in shape.exterior.coords]
        holes = [[(float(x), float(y)) for x, y in ring.coords]
                 for ring in shape.interiors]
        out.append((outer, holes))
    return out


def _dominant(prims: Sequence[Prim], layer: str) -> Tuple[float, float] | None:
    """Centre of the biggest piece on a layer — where a material name belongs."""
    best, best_area = None, -1.0
    for p in prims:
        if p.kind != "polyline" or not p.closed or p.layer != layer:
            continue
        pts = p.points
        area = abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1]
                       - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts))))
        if area > best_area:
            best, best_area = p, area
    if best is None:
        return None
    pts = best.points
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))



def paving_sheet(project: Any) -> Tuple[List[Prim], List[Tuple[str, float]]]:
    """Hard surfaces only: paving, gravel infill and garden paths."""
    spaces = _spaces(project, ("paving", "circulation"))
    if not spaces:
        return ([], [])
    prims: List[Prim] = []
    seen: dict[str, float] = {}
    for s in spaces:
        layer = _layer_of(s)
        prims.append(Prim("polyline", layer, list(s.boundary_mm2d), closed=True))
        label = _label_of(s)
        seen[label] = seen.get(label, 0.0) + s.area_m2
    # One label per material, on its biggest piece: labelling all 60 infill
    # pieces turns the sheet into a wall of numbers that hides the layout.
    for label, area in seen.items():
        layer = next((_layer_of(s) for s in spaces if _label_of(s) == label), "L-ZONE-PAVE")
        spot = _dominant(prims, layer)
        if spot:
            prims.append(Prim("text", "L-ANNO", text=f"{label} {area:.1f}m²",
                              center=spot, height=300))
    return prims, sorted(seen.items(), key=lambda kv: -kv[1])


def planting_sheet(project: Any) -> Tuple[List[Prim], List[Tuple[str, str, str]]]:
    """Planting beds plus every tree the concept placed, with its host bed."""
    beds = _spaces(project, ("planting",))
    trees = _trees(project)
    if not beds and not trees:
        return ([], [])
    prims: List[Prim] = []
    scattered: dict[str, float] = {}
    for bed in beds:
        prims.append(Prim("polyline", "L-ZONE-PLANT", list(bed.boundary_mm2d), closed=True))
        # Named beds get their name; the lawn is cut into many small infill
        # pieces by the model, so those are summed instead of labelled one by one.
        if bed.area_m2 >= 20.0:
            cx, cy = bed.centroid
            prims.append(Prim("text", "L-ANNO", text=f"{bed.name} {bed.area_m2:.1f}m²",
                              center=(cx, cy), height=240))
        else:
            key = bed.name
            scattered[key] = scattered.get(key, 0.0) + bed.area_m2
    for label, area in scattered.items():
        spot = _dominant(prims, "L-ZONE-PLANT")
        if spot:
            prims.append(Prim("text", "L-ANNO", text=f"{label} 合计 {area:.1f}m²",
                              center=(spot[0], spot[1] - 900), height=240))
    names = {s.id: s.name for s in project.spaces}
    rows: List[Tuple[str, str, str]] = []
    for tree in trees:
        x, y = tree.geometry["center"]
        prims.append(Prim("circle", "L-TREE", center=(x, y), radius=CANOPY_MM / 2.0))
        prims.append(Prim("line", "L-TREE", [(x - 300, y), (x + 300, y)]))
        prims.append(Prim("line", "L-TREE", [(x, y - 300), (x, y + 300)]))
        prims.append(Prim("text", "L-ANNO", text=str(tree.id),
                          center=(x, y - CANOPY_MM / 2.0 - 260), height=200))
        host = str(tree.properties.get("host_zone") or "")
        rows.append((str(tree.id), str(tree.properties.get("species") or "待选型"),
                     names.get(host, host or "未落区")))
    return prims, rows


def grading_sheet(project: Any) -> Tuple[List[Prim], List[Tuple[str, float]]]:
    """Design levels per zone, with drainage running downhill towards water."""
    spaces = _spaces(project, ("paving", "circulation", "planting", "water"))
    if not spaces:
        return ([], [])
    prims: List[Prim] = []
    for s in spaces:
        prims.append(Prim("polyline", _layer_of(s), list(s.boundary_mm2d), closed=True))

    # One level tag per material family, not per piece. 99 tags reading "+0.00"
    # is not a grading plan, it is noise: the model splits ground into pieces
    # that share a level by definition.
    family: dict[str, tuple[float, float]] = {}
    weight: dict[str, float] = {}
    for s in spaces:
        key = _label_of(s)
        z = float(s.properties.get("design_z_mm") or 0.0)
        area = max(s.area_m2, 0.01)
        zx, zy = family.get(key, (0.0, 0.0))
        family[key] = (zx + z * area, zy + area)
        weight[key] = weight.get(key, 0.0) + area
    levels: List[Tuple[str, str]] = []
    for key, (zsum, w) in family.items():
        z = zsum / max(w, 0.01)
        levels.append((key, f"{z/1000:+.2f} m"))      # metres, not raw millimetres
        spot = _dominant(prims, next((_layer_of(s) for s in spaces
                                      if _label_of(s) == key), "L-ZONE-PAVE"))
        if spot:
            prims.append(Prim("text", "L-ANNO", text=f"{key} {z/1000:+.2f}",
                              center=spot, height=300))

    # Drainage: a few radial arrows from the big beds to the bank. One arrow per
    # piece draws a hedgehog; arrows from the overall centroid all overlap into
    # one meaningless stroke. What a reader needs is "the ground falls this way".
    water = [s for s in spaces if s.use == "water"]
    if water:
        tx, ty = water[0].centroid
        sources = sorted([s for s in spaces if s.use in ("planting", "paving")],
                         key=lambda s: -s.area_m2)[:4]
        for s in sources:
            sx, sy = s.centroid
            dist = math.hypot(tx - sx, ty - sy)
            if dist < 3000.0:               # already at the bank, arrow says nothing
                continue
            ex, ey = sx + (tx - sx) * 0.62, sy + (ty - sy) * 0.62
            prims.extend(_arrow(sx, sy, ex, ey, "L-ANNO"))
    return prims, sorted(levels, key=lambda kv: kv[1], reverse=True)


def node_sheet(project: Any) -> Tuple[List[Prim], List[Tuple[str, str]]]:
    """Stop nodes and the interfaces a detail designer has to resolve."""
    nodes = _nodes(project)
    spaces = _spaces(project, ("paving", "circulation", "water", "planting"))
    if not spaces:
        return ([], [])
    prims: List[Prim] = []
    for s in spaces:
        prims.append(Prim("polyline", _layer_of(s), list(s.boundary_mm2d), closed=True))
    rows: List[Tuple[str, str]] = []
    for node in nodes:
        x, y = node.geometry["center"]
        prims.append(Prim("circle", "L-NODE", center=(x, y), radius=1500.0))
        prims.append(Prim("text", "L-NODE", text=str(node.id),
                          center=(x, y + 1900.0), height=260))
        rows.append((str(node.id), str(node.properties.get("name") or "停留节点")))
    # Water edge is the other place where a detail is unavoidable.
    for s in spaces:
        if s.use != "water":
            continue
        x0, y0, x1, y1 = s.bbox()
        rows.append(("N-WATER", "水岸收边与安全做法（岸线标高 "
                     f"{float(s.properties.get('design_z_mm') or 0)/1000:+.2f} m）"))
        prims.append(Prim("text", "L-NODE", text="水岸收边",
                          center=((x0 + x1) / 2, y0 - 700), height=260))
        break
    return prims, rows


# ----------------------------------------------------------------------
def _render(prims: Sequence[Prim], path: Path, *, title: str, note: str,
            table: Sequence[Tuple[str, ...]] = (), headers: Sequence[str] = (),
            table_title: str = "") -> None:
    """Draw the same primitives as a filled preview, keeping true proportions."""
    pts = [p for item in prims if item.points for p in item.points]
    pts += [item.center for item in prims if item.kind in ("text", "circle")]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    span_x, span_y = max(x1 - x0, 1.0), max(y1 - y0, 1.0)

    # A table needs a fixed column on the right; the plan shrinks to make room.
    table_w = 330.0 if table else 0.0
    avail_w = 1180.0 - table_w
    scale = min(avail_w / span_x, 560.0 / span_y)      # one scale, no stretching
    ox = 40.0 + (avail_w - span_x * scale) / 2.0
    px = lambda x: ox + (x - x0) * scale
    py = lambda y: 660.0 - (y - y0) * scale

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="780" '
           'viewBox="0 0 1200 780">',
           '<rect width="1200" height="780" fill="#f7f6f2"/>',
           f'<text x="40" y="42" font-size="19" fill="#202b31">{escape(title)}</text>',
           f'<text x="40" y="66" font-size="12.5" fill="#6b767c">{escape(note)}</text>']
    # Fill first, then outlines, then text. Same-material pieces are unioned
    # first: the model keeps 60 paving pieces for measuring, but a drawing needs
    # one bed, one path, one water body.
    order: List[str] = []
    for item in prims:
        if item.kind == "polyline" and item.closed and item.layer not in order:
            order.append(item.layer)
    order.sort(key=lambda lay: -len([p for p in prims
                                     if p.kind == "polyline" and p.layer == lay]))
    for layer in order:
        fill = FILLS.get(layer, "none")
        for outer, holes in _merge_rings(prims, layer):
            parts = []
            for ring in [outer] + holes:
                parts.append('M ' + ' L '.join(
                    f'{px(x):.1f} {py(y):.1f}' for x, y in ring) + ' Z')
            svg.append(f'<path d="{" ".join(parts)}" fill="{fill}" fill-rule="evenodd" '
                       'stroke="#5b6a6f" stroke-width="1.1" stroke-opacity=".55"/>')
    for item in prims:
        if item.kind == "line" and item.points:
            (ax, ay), (bx, by) = item.points[0], item.points[1]
            svg.append(f'<line x1="{px(ax):.1f}" y1="{py(ay):.1f}" x2="{px(bx):.1f}" '
                       f'y2="{py(by):.1f}" stroke="#7d8b90" stroke-width="1.2"/>')
        elif item.kind == "circle":
            cx, cy = item.center
            color = "#8aa878" if item.layer == "L-TREE" else "#c9743f"
            svg.append(f'<circle cx="{px(cx):.1f}" cy="{py(cy):.1f}" '
                       f'r="{max(item.radius * scale, 2.0):.1f}" fill="{color}" '
                       'fill-opacity=".30" stroke="' + color + '" stroke-width="1.3"/>')
        elif item.kind == "text" and item.text:
            size = max(min(item.height * scale * 1.6, 13.0), 8.5)
            svg.append(f'<text x="{px(item.center[0]):.1f}" y="{py(item.center[1]):.1f}" '
                       f'text-anchor="middle" font-size="{size:.1f}" fill="#33424a">'
                       f'{escape(item.text)}</text>')
    if table:
        tx = 1200.0 - table_w + 30.0
        svg.append(f'<line x1="{tx - 24:.0f}" y1="96" x2="{tx - 24:.0f}" y2="700" '
                   'stroke="#cfd5d2" stroke-width="1"/>')
        svg.append(f'<text x="{tx:.0f}" y="112" font-size="13" fill="#33424a" '
                   f'font-weight="600">{escape(table_title)}</text>')
        y = 140.0
        if headers:
            svg.append(f'<text x="{tx:.0f}" y="{y:.0f}" font-size="11" '
                       'fill="#6b767c">' + ' · '.join(escape(h) for h in headers) + '</text>')
            y += 20
        for row in table:
            cells = [f"{c:,.2f}" if isinstance(c, float) else str(c) for c in row]
            svg.append(f'<text x="{tx:.0f}" y="{y:.0f}" font-size="11.5" '
                       f'fill="#33424a">{escape(" · ".join(cells))}</text>')
            y += 19
            if y > 690:
                break
    svg.append('</svg>')
    path.write_text('\n'.join(svg), encoding="utf-8")


def _legend_svg(prims: Sequence[Prim], path: Path, *, title: str) -> None:
    _render(prims, path, title=title, note="图例取自本图实际绘制的图层")


# ----------------------------------------------------------------------
SHEETS = {
    "paving": ("L-02", "铺装平面图", "本图只表达硬质铺装与园路；绿地、水面见 L-03 与总平面。规格与收边待定"),
    "planting": ("L-03", "种植平面图", "本图只表达种植区与苗木点位；乔木为方案点位，树种与冠幅待苗木选型"),
    "grading": ("L-04", "竖向设计图", "设计相对标高（无实测高程基准）；坡度与排水路径待专业设计"),
    "node": ("L-05", "节点索引图", "索引位置与清单；构造做法待节点详图"),
}


def run(runner: Any, stage: str, directory: Path) -> Any:
    """Write paving / planting / grading / node sheets for the current model."""
    from ..workflow import StageOutcome

    directory.mkdir(parents=True, exist_ok=True)
    project = runner.project
    if not _spaces(project, ("paving", "circulation", "planting", "water")):
        return StageOutcome(stage, status="blocked",
                            error="L-SITE 无景观几何，无法出专项图",
                            next_action="先完成景观 S3 并核对场地边界")

    dxf = DxfAdapter()
    if not dxf.preflight().available:
        return StageOutcome(stage, status="degraded", adapter="dxf",
                            notes=["ezdxf 不可用：景观专项图未生成"])

    builders = {"paving": paving_sheet, "planting": planting_sheet,
                "grading": grading_sheet, "node": node_sheet}
    arts: List[str] = []
    notes: List[str] = ["专项图均读自 L-SITE 统一模型；规格、树种、坡度与构造未审定。"]
    failures: List[str] = []
    for key, builder in builders.items():
        code, name, caveat = SHEETS[key]
        prims, table = builder(project)
        if not prims:
            notes.append(f"{code} {name}：当前模型没有对应内容，未出图")
            continue
        stem = f"{code}-{name}"
        result = dxf.draw_primitives(prims, directory / f"{stem}.dxf",
                                     required_layer_prefix="L-ZONE")
        if not result.ok:
            failures.append(f"{stem}：" + "; ".join(result.errors[:2]))
            continue
        arts.extend(result.artifacts)
        stats = result.validation.get("stats", {})
        headers = {"paving": ("材质", "面积 m²"),
                   "planting": ("编号", "树种", "所在种植区"),
                   "grading": ("区域", "设计标高 m"),
                   "node": ("编号", "节点")}[key]
        _render(prims, directory / f"{stem}.svg", title=f"{code} {name}", note=caveat,
                table=table, headers=headers, table_title={"paving": "铺装面积汇总",
                                                           "planting": "苗木点位表",
                                                           "grading": "设计标高",
                                                           "node": "节点清单"}[key])
        arts.append(str(directory / f"{stem}.svg"))
        notes.append(f"{code} {name}：{stats.get('entities', '?')} 实体，读回通过")

    if failures:
        return StageOutcome(stage, status="failed", adapter="dxf", artifacts=arts,
                            error="景观专项图审计失败：" + "；".join(failures))
    return StageOutcome(stage, status="degraded" if len(arts) < 8 else "ok",
                        adapter="dxf", artifacts=arts, notes=notes)
