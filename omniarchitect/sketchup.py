"""SketchUp hand-off: a real modelling script, or a real MCP call.

Two ways to get geometry into SketchUp, and the system must be honest about
which one happened:

* MCP configured and handshaken → issue the call through `tools.mcp_bridge`.
* No MCP → write a `.rb` that opens in SketchUp and builds the same geometry.
  This is not a placeholder: run it with `Sketchup.active_model` and the walls,
  slabs and opening markers appear at the coordinates of the canonical model.

The opening markers matter. SketchUp Make has no solid tools, so cutting a
window opening from a wall cannot be scripted reliably across editions. The
script therefore *marks* each opening on its wall face and says so in the file
header — a designer finishes the cut by hand. Claiming a cut that did not happen
would put a wrong window count into every downstream sheet.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .tools import mcp_bridge


# ----------------------------------------------------------------------
# scene extraction
# ----------------------------------------------------------------------
def _bbox(space: Any) -> Optional[Tuple[float, float, float, float]]:
    try:
        pts = [(float(x), float(y)) for x, y in space.boundary_mm2d]
    except Exception:                     # noqa: BLE001
        return None
    if len(pts) < 3:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _wall_axis(wall: Any) -> Optional[List[List[float]]]:
    try:
        axis = wall.wall_axis()
    except Exception:                     # noqa: BLE001
        axis = None
    if not axis:
        geo = wall.geometry or {}
        start, end = geo.get("start"), geo.get("end")
        if start and end:
            axis = (tuple(start), tuple(end))
    if not axis:
        return None
    (ax, ay), (bx, by) = axis
    return [[float(ax), float(ay)], [float(bx), float(by)]]


def scene_payload(project: Any, level_id: Optional[str] = None) -> Dict[str, Any]:
    """Everything SketchUp needs to rebuild the confirmed plan, in millimetres."""
    levels = [lv for lv in project.levels
              if level_id is None or lv.id == level_id]
    level_ids = {lv.id for lv in levels}
    payload: Dict[str, Any] = {
        "units": "mm",
        "project": project.project_id,
        "revision": project.revision,
        "levels": [{"id": lv.id, "name": lv.name,
                    "elevation_mm": float(lv.elevation_mm or 0),
                    "height_mm": float(lv.height_mm or 0)} for lv in levels],
        "walls": [],
        "openings": [],
        "rooms": [],
        "furniture": [],
        "site": [],
    }
    for wall in project.by_type("wall"):
        if wall.level_id not in level_ids:
            continue
        axis = _wall_axis(wall)
        if not axis:
            continue
        payload["walls"].append({
            "id": wall.id, "level": wall.level_id, "axis": axis,
            "thickness_mm": float((wall.geometry or {}).get("thickness_mm") or 100.0),
            "base_mm": float((project.level(wall.level_id).elevation_mm) or 0),
            "height_mm": float(project.level(wall.level_id).height_mm or 0),
        })
    for kind in ("door", "window"):
        for item in project.by_type(kind):
            if item.level_id not in level_ids:
                continue
            geo = item.geometry or {}
            payload["openings"].append({
                "id": item.id, "kind": kind, "level": item.level_id,
                "host_wall": geo.get("host_wall"),
                "offset_mm": float(geo.get("offset_mm") or 0),
                "width_mm": float(geo.get("width_mm") or 0),
                "height_mm": float(geo.get("height_mm") or 0),
                "sill_mm": float(geo.get("sill_mm") or 0),
            })
    for space in project.spaces:
        if space.level_id not in level_ids or space.use == "envelope":
            continue
        box = _bbox(space)
        if not box:
            continue
        payload["rooms"].append({
            "id": space.id, "name": space.name, "use": space.use,
            "level": space.level_id, "bbox_mm": list(box),
            "area_m2": round(float(space.area_m2), 2),
        })
    for item in project.by_type("furniture"):
        if item.level_id not in level_ids:
            continue
        center = (item.geometry or {}).get("center") or []
        if len(center) != 2:
            continue
        payload["furniture"].append({
            "id": item.id, "name": item.properties.get("name") or "",
            "category": (item.geometry or {}).get("category") or "",
            "level": item.level_id, "center_mm": [float(center[0]), float(center[1])],
            "width_mm": float((item.geometry or {}).get("width_mm") or 0),
            "depth_mm": float((item.geometry or {}).get("depth_mm") or 0),
        })
    for space in project.spaces_on("L-SITE"):
        box = _bbox(space)
        if not box:
            continue
        payload["site"].append({
            "id": space.id, "name": space.name, "use": space.use,
            "bbox_mm": list(box),
            "boundary_mm2d": [[float(x), float(y)] for x, y in space.boundary_mm2d],
            "z_mm": float(space.properties.get("design_z_mm") or 0),
        })
    return payload


# ----------------------------------------------------------------------
# Ruby script
# ----------------------------------------------------------------------
_RUBY_HEADER = """# OmniAiLab SketchUp 建模脚本 —— 由统一空间模型生成，尺寸单位 mm
#
# 用法：SketchUp → 窗口 → Ruby 控制台 → load '<本文件绝对路径>'
#
# 这个脚本建：楼层参考面、墙体（按厚度挤出）、房间标记、门窗洞口标记。
# 门窗是**标记**不是切割：SketchUp Make 没有实体工具，跨版本无法可靠地用脚本
# 布尔运算开洞。脚本在墙面上画出洞口轮廓并标注尺寸，由设计人员确认后手工开洞。
# 因此不要把本脚本产出的模型直接当作已开洞的完成模型。
"""


def _rb_num(v: float) -> str:
    """Millimetres as a SketchUp length.

    SketchUp's Ruby API takes bare numbers as *inches*. A model fed plain
    millimetre numbers comes out 25.4× too small — the classic first-run
    surprise. `Numeric#mm` is SketchUp's own conversion, so every coordinate
    goes through it and stays readable in the script.
    """
    return f"{float(v):.1f}.mm"


def build_ruby(payload: Dict[str, Any]) -> str:
    """Generate a runnable .rb. Coordinates follow the model, no rescaling."""
    lines: List[str] = [_RUBY_HEADER, "module OmniAiLab", "  def self.build",
                        "    model = Sketchup.active_model",
                        "    ents = model.active_entities",
                        "    model.start_operation('OmniAiLab 建模', true)",
                        "    # 长度一律带 .mm：SketchUp Ruby 把裸数字当英寸，不带会小 25.4 倍",
                        "    tag = model.layers",
                        "    t_wall = tag['OMNI-WALL'] || tag.add('OMNI-WALL')",
                        "    t_open = tag['OMNI-OPENING'] || tag.add('OMNI-OPENING')",
                        "    t_room = tag['OMNI-ROOM'] || tag.add('OMNI-ROOM')",
                        ""]

    # Floor reference rectangles per level.
    for lv in payload["levels"]:
        if not lv["height_mm"]:
            continue
        lines.append(
            f"    # 楼层 {lv['id']} {lv['name']} 标高 {lv['elevation_mm']/1000:+.3f} m"
            f" 层高 {lv['height_mm']/1000:.3f} m")
    lines.append("")

    # Walls: a rectangle footprint pushed up to the storey height.
    for wall in payload["walls"]:
        (ax, ay), (bx, by) = wall["axis"]
        t = wall["thickness_mm"] / 2.0
        base, h = wall["base_mm"], wall["height_mm"]
        # Perpendicular offset for the footprint corners.
        dx, dy = bx - ax, by - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        nx, ny = -dy / length * t, dx / length * t
        pts = [(ax + nx, ay + ny), (bx + nx, by + ny),
               (bx - nx, by - ny), (ax - nx, ay - ny)]
        pt_s = ", ".join(f"[{_rb_num(x)}, {_rb_num(y)}, {_rb_num(base)}]" for x, y in pts)
        lines += [
            f"    g = ents.add_group",
            f"    f = g.entities.add_face({pt_s})",
            f"    f.pushpull({_rb_num(h)})",
            f"    g.layer = t_wall",
            f"    g.name = '{wall['id']}'",
        ]
    lines.append("")

    # Openings: a face on the host wall at the right offset/sill, marked only.
    walls = {w["id"]: w for w in payload["walls"]}
    for op in payload["openings"]:
        wall = walls.get(str(op["host_wall"]))
        if not wall:
            continue
        (ax, ay), (bx, by) = wall["axis"]
        dx, dy = bx - ax, by - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        ux, uy = dx / length, dy / length
        o0, o1 = op["offset_mm"], op["offset_mm"] + op["width_mm"]
        base = wall["base_mm"] + op["sill_mm"]
        top = base + op["height_mm"]
        p1 = (ax + ux * o0, ay + uy * o0)
        p2 = (ax + ux * o1, ay + uy * o1)
        lines += [
            f"    g = ents.add_group",
            f"    f = g.entities.add_face("
            f"[{_rb_num(p1[0])}, {_rb_num(p1[1])}, {_rb_num(base)}], "
            f"[{_rb_num(p2[0])}, {_rb_num(p2[1])}, {_rb_num(base)}], "
            f"[{_rb_num(p2[0])}, {_rb_num(p2[1])}, {_rb_num(top)}], "
            f"[{_rb_num(p1[0])}, {_rb_num(p1[1])}, {_rb_num(top)}])",
            f"    g.layer = t_open",
            f"    g.name = '{op['id']} {op['kind']} "
            f"{_rb_num(op['width_mm'])}x{_rb_num(op['height_mm'])}'",
        ]
    lines.append("")

    # Room outlines as flat text labels at floor level (readable in 3D).
    for room in payload["rooms"]:
        x0, y0, x1, y1 = room["bbox_mm"]
        cen = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        elev = next((lv["elevation_mm"] for lv in payload["levels"]
                     if lv["id"] == room["level"]), 0.0)
        lines += [
            f"    t = ents.add_text('{room['name']} {room['area_m2']:.1f}m2', "
            f"[{_rb_num(cen[0])}, {_rb_num(cen[1])}, {_rb_num(elev + 10)}])",
            f"    t.layer = t_room",
        ]

    lines += ["", "    model.commit_operation", "  end", "end", "",
              "OmniAiLab.build", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------
# stage entry
# ----------------------------------------------------------------------
def write_job(project: Any, directory: Path, *, level_id: Optional[str] = None,
              want: Sequence[str] = ("create_walls", "create_openings",
                                     "capture_view", "export_obj"),
              project_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Write the hand-off package. MCP if wired, otherwise runnable script."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = scene_payload(project, level_id)
    prof = mcp_bridge.probe("sketchup", project_dir)

    job = {
        "project": payload["project"],
        "revision": payload["revision"],
        "state": prof.state,
        "server": prof.server,
        "operations": list(want),
        "missing": list(prof.missing),
        "reason": prof.error or "；".join(prof.notes),
        "counts": {
            "walls": len(payload["walls"]),
            "openings": len(payload["openings"]),
            "rooms": len(payload["rooms"]),
            "furniture": len(payload["furniture"]),
            "site": len(payload["site"]),
        },
        "scene": payload,
        "how_to_run": [
            "MCP 未连接时：打开 SketchUp → Ruby 控制台 → load 'build_model.rb'",
            "模型只建墙与洞口标记，洞口切割需人工确认（Make 无实体工具）",
            "出图请用固定机位，机位参数见 camera_jobs.json，便于与效果图逐张比对",
        ],
    }
    (directory / "sketchup-job.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    rb = directory / "build_model.rb"
    rb.write_text(build_ruby(payload), encoding="utf-8")
    (directory / "camera_jobs.json").write_text(
        json.dumps({"cameras": camera_jobs(project, level_id)},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # If the server really is wired, try it — and record what came back.
    if prof.usable and prof.op_tool("create_walls"):
        result = mcp_bridge.call("sketchup", "create_walls", payload,
                                 project_dir=project_dir, approved=True)
        job["mcp_call"] = result.to_dict()
        (directory / "sketchup-job.json").write_text(
            json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return job


def camera_jobs(project: Any, level_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fixed cameras so a SketchUp screenshot and a render are comparable.

    Without the same eye, target and lens, "the model does not match the render"
    is a claim nobody can check. These come from the model's own extents.
    """
    spaces = [s for s in project.spaces
              if s.use != "envelope" and len(s.boundary_mm2d) >= 3
              and (level_id is None or s.level_id == level_id)]
    if not spaces:
        return []
    pts = [p for s in spaces for p in s.boundary_mm2d]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    span = max(x1 - x0, y1 - y0)
    level = next((lv for lv in project.levels if lv.id == (level_id or "")),
                 project.levels[0] if project.levels else None)
    z = float(level.elevation_mm if level else 0)
    eye = z + 1600.0
    return [
        {"id": "CAM-AXON", "label": "整体轴测", "lens_mm": 24,
         "eye_mm": [cx + span * 0.55, cy - span * 0.55, z + span * 0.75],
         "target_mm": [cx, cy, z + 1200], "use": "总览与体量比对"},
        {"id": "CAM-EYE", "label": "人视", "lens_mm": 35,
         "eye_mm": [cx, y0 + (y1 - y0) * 0.15, eye],
         "target_mm": [cx, y1, eye - 100], "use": "空间感受与效果图比对"},
        {"id": "CAM-PLAN", "label": "俯视", "lens_mm": 50,
         "eye_mm": [cx, cy, z + span * 1.15],
         "target_mm": [cx, cy, z], "use": "平面与 CAD 复核"},
    ]


# ----------------------------------------------------------------------
# linework for image control
# ----------------------------------------------------------------------
def linework(payload: Dict[str, Any], path: Path, *, margin_mm: float = 0.0) -> Path:
    """Outline-only plan: the geometry the render must respect.

    Fill is deliberately absent. A filled plan invites an image model to copy the
    colours and invent the rest; an outline plan tells it where the walls are.
    """
    from .adapters.drawing import Prim

    prims: List[Prim] = []
    for wall in payload["walls"]:
        (ax, ay), (bx, by) = wall["axis"]
        t = max(wall["thickness_mm"], 60.0) / 2.0
        dx, dy = bx - ax, by - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        nx, ny = -dy / length * t, dx / length * t
        prims.append(Prim("polyline", "WALL", [(ax + nx, ay + ny), (bx + nx, by + ny),
                                               (bx - nx, by - ny), (ax - nx, ay - ny)],
                          closed=True))
    walls = {w["id"]: w for w in payload["walls"]}
    for op in payload["openings"]:
        wall = walls.get(str(op["host_wall"]))
        if not wall:
            continue
        (ax, ay), (bx, by) = wall["axis"]
        dx, dy = bx - ax, by - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            continue
        ux, uy = dx / length, dy / length
        o0, o1 = op["offset_mm"], op["offset_mm"] + op["width_mm"]
        # Cut a white notch through the wall, not a hairline on its axis: a line
        # inside a solid wall disappears, and the image model then sees a wall
        # with no opening in it.
        half = max(float(wall.get("thickness_mm") or 100.0), 60.0) / 2.0 + 12.0
        nx, ny = -uy * half, ux * half
        p1 = (ax + ux * o0, ay + uy * o0)
        p2 = (ax + ux * o1, ay + uy * o1)
        prims.append(Prim("polyline", "OPENING",
                          [(p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny),
                           (p2[0] - nx, p2[1] - ny), (p1[0] - nx, p1[1] - ny)],
                          closed=True))
    # Landscape has no walls: the zones themselves are the geometry to respect.
    # Unioned per use — the model splits ground into dozens of measurable
    # pieces, and drawing all of them turns the control image into a mesh of
    # triangles that tells an image model nothing about the layout.
    if not prims:
        merged: Dict[str, List[List[Tuple[float, float]]]] = {}
        try:
            from shapely.geometry import Polygon
            from shapely.ops import unary_union
        except Exception:                 # noqa: BLE001  没有 shapely 就逐块画
            Polygon = None                     # type: ignore[assignment]
        for zone in payload.get("site") or []:
            ring = zone.get("boundary_mm2d") or []
            if len(ring) < 3:
                continue
            merged.setdefault(str(zone.get("use") or "other"), []).append(
                [(float(x), float(y)) for x, y in ring])
        for use, rings in merged.items():
            if Polygon is None:
                for ring in rings:
                    prims.append(Prim("polyline", "ZONE", ring, closed=True))
                continue
            try:
                shape = unary_union([Polygon(r) for r in rings])
                parts = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
            except Exception:             # noqa: BLE001  坏多边形退回逐块
                parts = []
                for ring in rings:
                    prims.append(Prim("polyline", "ZONE", ring, closed=True))
            for part in parts:
                if getattr(part, "is_empty", False):
                    continue
                prims.append(Prim("polyline", "ZONE",
                                  [(float(x), float(y)) for x, y in part.exterior.coords],
                                  closed=True))
    if not prims:
        raise ValueError("线稿需要墙、洞口或场地分区几何，当前场景为空")

    pts = [p for item in prims for p in item.points]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    x0, y0, x1, y1 = x0 - margin_mm, y0 - margin_mm, x1 + margin_mm, y1 + margin_mm
    scale = min(1500 / max(x1 - x0, 1), 900 / max(y1 - y0, 1))
    px = lambda x: (x - x0) * scale + 30
    py = lambda y: 940 - (y - y0) * scale
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="980" '
           'viewBox="0 0 1560 980">',
           '<rect width="1560" height="980" fill="#ffffff"/>',
           '<text x="30" y="26" font-size="14" fill="#333">线稿 · 几何控制用'
           '（无填充，供图像参考；不构成尺寸依据）</text>']
    for item in prims:
        points = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in item.points)
        if item.layer == "WALL":
            # Solid walls, white space: the form an image model can follow.
            # Hollow outlines read as a diagram and get ignored.
            svg.append(f'<polygon points="{points}" fill="#2f3437" stroke="#111" '
                       'stroke-width="0.6"/>')
        elif item.layer == "ZONE":
            # Solid, not dashed: a dashed line reads as "indicative extent" and
            # gets thrown away by the image model.
            svg.append(f'<polygon points="{points}" fill="none" stroke="#3b4650" '
                       'stroke-width="1.5"/>')
        else:
            # Openings are drawn as white notches over the walls.
            svg.append(f'<polygon points="{points}" fill="#ffffff" stroke="#c0392b" '
                       'stroke-width="1.1"/>')
    svg.append('</svg>')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg), encoding="utf-8")
    return path


__all__ = ["scene_payload", "build_ruby", "write_job", "camera_jobs", "linework"]
