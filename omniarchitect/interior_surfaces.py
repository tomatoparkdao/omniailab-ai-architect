"""Editable room-by-room ceiling and floor finish review sheets.

The polygons and area figures are read from the installed canonical spaces.
Finish names remain pending unless the selected concept actually supplies them.
These are not reflected ceiling services drawings or construction details.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any

from . import finishes
from .adapters import DxfAdapter
from .adapters.drawing import Prim
from .geometry import point_in_polygon
from .registry import SIGNATURE


def proposed_lighting(project: Any, level_id: str) -> list[dict[str, Any]]:
    """Deterministic review points from rooms and installed furniture, not circuits."""
    rooms = [s for s in project.spaces_on(level_id)
             if s.use != "envelope" and len(s.boundary_mm2d) >= 3]
    furniture = [e for e in project.by_type("furniture") if e.level_id == level_id]
    points: list[dict[str, Any]] = []
    for room in rooms:
        cx, cy = room.centroid
        x0, y0, x1, y1 = room.bbox()
        length = max(x1-x0, y1-y0)
        if room.use == "circulation" and length > 6000:
            count = math.ceil(length / 4000)
            candidates = [((x0 + (i+.5)*(x1-x0)/count, cy)
                           if x1-x0 >= y1-y0 else
                           (cx, y0 + (i+.5)*(y1-y0)/count)) for i in range(count)]
        else:
            candidates = [(cx, cy)]
        for x, y in candidates:
            if point_in_polygon((x, y), room.boundary_mm2d):
                points.append({"space_id": room.id, "name": room.name,
                               "kind": "ambient_proposed", "x_mm": round(x, 2),
                               "y_mm": round(y, 2)})
        for item in furniture:
            if item.properties.get("space_id") != room.id or (
                item.geometry.get("category") != "nightstand"):
                continue
            center = item.geometry.get("center") or []
            if len(center) != 2 or not point_in_polygon(center, room.boundary_mm2d):
                continue
            points.append({"space_id": room.id, "name": room.name,
                           "kind": "bedside_task_proposed", "x_mm": round(float(center[0]), 2),
                           "y_mm": round(float(center[1]), 2),
                           "furniture_id": item.id})
    return points


def _typical_elevation(project: Any, directory: Path, level_id: str,
                       rooms: list[Any], hotel: bool) -> tuple[list[str], dict[str, Any]]:
    """Unfold four actual room edges and their matching modeled openings."""
    room = next((s for s in rooms if s.use == "guest"), None) if hotel else next(
        (s for s in rooms if s.properties.get("zone") == "day"), None)
    room = room or rooms[0]
    zone = str(room.properties.get("zone") or "")
    height = (2700 if hotel else int(finishes.ZONE_CEILING.get(
        zone, finishes.ZONE_CEILING[""])[1]))
    ring = room.boundary_mm2d
    edges = []
    for i, a in enumerate(ring):
        b = ring[(i+1) % len(ring)]
        length = math.hypot(b[0]-a[0], b[1]-a[1])
        if length > 100:
            edges.append((a, b, length))
    if not edges:
        raise ValueError(f"{room.name} 无有效墙面边界")
    gap = 1100.0
    placed = []
    row_width: dict[int, float] = {}
    for i, (a, b, length) in enumerate(edges):
        row = i // 2
        x = row_width.get(row, 0.0)
        y = -row * (height + 1800.0)
        placed.append((a, b, length, x, y))
        row_width[row] = x + length + gap
    prims: list[Prim] = []
    for i, (_a, _b, length, x, y) in enumerate(placed, 1):
        prims.extend([Prim("polyline", "I-ELEV", [(x, y), (x+length, y),
                    (x+length, y+height), (x, y+height)], closed=True),
                    Prim("text", "I-ANNO", text=f"墙面 {i} · {length/1000:.2f}m",
                         center=(x+length/2, y-400), height=180)])
    openings = []
    unmapped = []
    for item in project.elements:
        if item.level_id != level_id or item.type not in ("door", "window"):
            continue
        props = item.properties
        if room.id not in (props.get("space_id"), props.get("from_space"),
                          props.get("to_space")):
            continue
        wall = next((e for e in project.elements
                     if e.id == item.geometry.get("host_wall")), None)
        axis = wall.wall_axis() if wall else None
        if not axis:
            unmapped.append(item.id)
            continue
        (wx0, wy0), (wx1, wy1) = axis
        wlen = math.hypot(wx1-wx0, wy1-wy0)
        if wlen < 1:
            unmapped.append(item.id)
            continue
        off = float(item.geometry.get("offset_mm") or 0)
        width = float(item.geometry.get("width_mm") or 0)
        mid = off + width/2
        mx = wx0 + (wx1-wx0)*mid/wlen
        my = wy0 + (wy1-wy0)*mid/wlen
        match = None
        for i, (a, b, length, x, y) in enumerate(placed, 1):
            ux, uy = (b[0]-a[0])/length, (b[1]-a[1])/length
            t = (mx-a[0])*ux + (my-a[1])*uy
            distance = abs((mx-a[0])*uy - (my-a[1])*ux)
            if -250 <= t <= length+250 and distance <= 260:
                match = (i, x, y, length, ux, uy, a)
                break
        if match is None:
            unmapped.append(item.id)
            continue
        edge_id, x, y, length, ux, uy, a = match
        start_x = wx0 + (wx1-wx0)*off/wlen
        start_y = wy0 + (wy1-wy0)*off/wlen
        end_x = wx0 + (wx1-wx0)*(off+width)/wlen
        end_y = wy0 + (wy1-wy0)*(off+width)/wlen
        t0 = max(0.0, min(length, (start_x-a[0])*ux+(start_y-a[1])*uy))
        t1 = max(0.0, min(length, (end_x-a[0])*ux+(end_y-a[1])*uy))
        lo, hi = sorted((t0, t1))
        sill = float(item.geometry.get("sill_mm") or 0) if item.type == "window" else 0.0
        head = min(float(height), sill+float(item.geometry.get("height_mm") or 2100))
        if hi-lo <= 10 or head <= sill:
            unmapped.append(item.id)
            continue
        prims.append(Prim("polyline", "I-OPEN", [(x+lo, y+sill), (x+hi, y+sill),
                     (x+hi, y+head), (x+lo, y+head)], closed=True))
        openings.append({"id": item.id, "type": item.type, "edge": edge_id,
                         "width_mm": round(hi-lo, 2), "sill_mm": round(sill, 2),
                         "height_mm": round(head-sill, 2)})

    stem = "I-07-typical-wall-elevations"
    cad = directory / f"{stem}.dxf"
    result = DxfAdapter().draw_primitives(prims, cad, "I-ELEV", project.revision)
    if not result.ok:
        raise ValueError(f"typical elevation CAD read-back failed: {result.errors}")
    xs = [p[0] for prim in prims for p in prim.points]
    ys = [p[1] for prim in prims for p in prim.points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    scale = min(1060/max(x1-x0, 1), 580/max(y1-y0, 1))
    px = lambda x: 70+(x-x0)*scale
    py = lambda y: 680-(y-y0)*scale
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" '
           'viewBox="0 0 1200 760">', '<rect width="1200" height="760" fill="#f7f5f0"/>',
           f'<text x="70" y="45" font-size="24" fill="#29343a">'
           f'{escape(room.name)} · 四墙展开（方案）</text>',
           '<text x="70" y="70" font-size="13" fill="#647078">'
           '墙长与开口来自统一模型；饰面分缝、基层与机电点位未设计</text>']
    for prim in prims:
        if prim.kind == "polyline":
            pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in prim.points)
            svg.append(f'<polygon points="{pts}" fill="'
                       f'{"#dce8ea" if prim.layer == "I-OPEN" else "#e9e5db"}" '
                       'stroke="#526068" stroke-width="1.5"/>')
        elif prim.kind == "text":
            svg.append(f'<text x="{px(prim.center[0]):.1f}" '
                       f'y="{py(prim.center[1]):.1f}" font-size="12" '
                       f'text-anchor="middle" fill="#34424a">{escape(prim.text)}</text>')
    svg += ['<text x="70" y="735" font-size="12" fill="#657277">'
            '代表空间展开；未逐间复核，不得作为施工节点或下料依据。</text>', '</svg>']
    view = directory / f"{stem}.svg"
    view.write_text("\n".join(svg), encoding="utf-8")
    return [str(cad), str(view)], {"space_id": room.id, "room_name": room.name,
        "height_mm": height, "edges_mm": [round(edge[2], 2) for edge in edges],
        "openings": openings, "unmapped_openings": unmapped,
        "status": "representative_review_only"}


def export(project: Any, directory: Path, level_id: str) -> list[str]:
    """Write finish and proposed-lighting CAD sheets from model geometry."""
    rooms = [s for s in project.spaces_on(level_id)
             if s.use != "envelope" and len(s.boundary_mm2d) >= 3]
    if not rooms:
        raise ValueError("no installed room polygons for interior finish sheets")
    directory.mkdir(parents=True, exist_ok=True)
    sector = (project.meta.get("sector_levels") or {}).get("sector")
    hotel = sector == "hospitality"
    hotel_heights = {"guest": 2700, "public": 3000,
                     "service": 2600, "boh": 2600}
    floor_by_zone = {r["zone"]: r for r in finishes.floor_rows(project)}
    areas = []
    artifacts: list[str] = []
    points = [p for room in rooms for p in room.boundary_mm2d]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    x1, y1 = max(p[0] for p in points), max(p[1] for p in points)
    scale = min(900 / max(x1-x0, 1), 620 / max(y1-y0, 1))
    colors = {"day": "#e9d9bd", "night": "#d9e2d4", "service": "#dce4e8",
              "entry": "#e6dfd0", "wet": "#c9dce2", "guest": "#e8ded2",
              "public": "#dedbd1", "boh": "#d0d6d9"}
    for kind, layer, title in (("ceiling", "I-CEILING", "顶面分区"),
                               ("floor", "I-FLOOR", "地面饰面分区")):
        prims: list[Prim] = []
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
               'viewBox="0 0 1200 800">',
               '<rect width="1200" height="800" fill="#f7f5f0"/>',
               f'<text x="60" y="55" font-size="25" fill="#29343a">{title} · 方案预览</text>',
               '<text x="60" y="78" font-size="13" fill="#647078">'
               '与统一模型同一房间边界；材料及机电定位待确认</text>']
        for room in rooms:
            zone = str(room.properties.get("zone") or "")
            label = finishes.ZONE_LABEL.get(zone, zone or finishes.ZONE_LABEL[""])
            if kind == "ceiling":
                if hotel:
                    height = hotel_heights.get(zone, 2600)
                else:
                    _method, height = finishes.ZONE_CEILING.get(zone, finishes.ZONE_CEILING[""])
                detail = f"建议顶标高 {height}mm"
            else:
                detail = (finishes.PENDING if hotel else
                          floor_by_zone.get(label, {}).get("material", finishes.PENDING))
            ring = [(float(x), float(y)) for x, y in room.boundary_mm2d]
            cx, cy = room.centroid
            prims.extend([Prim("polyline", layer, ring, closed=True),
                          Prim("text", "I-ANNO", text=room.name,
                               center=(cx, cy+160), height=160),
                          Prim("text", "I-ANNO", text=f"{room.area_m2:.2f}m2 · {detail}",
                               center=(cx, cy-170), height=105)])
            pts = ' '.join(f'{60+(x-x0)*scale:.1f},{105+(y1-y)*scale:.1f}' for x, y in ring)
            px, py = 60+(cx-x0)*scale, 105+(y1-cy)*scale
            svg.extend([f'<polygon points="{pts}" fill="{colors.get(zone, "#e6e4dd")}" '
                        'stroke="#53616a" stroke-width="1.5"/>',
                        f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="middle" '
                        f'font-size="13" fill="#223038">{escape(room.name)}</text>',
                        f'<text x="{px:.1f}" y="{py+16:.1f}" text-anchor="middle" '
                        f'font-size="10" fill="#4a5a61">{room.area_m2:.1f} m²</text>'])
            if kind == "ceiling":
                areas.append({"space_id": room.id, "name": room.name,
                              "zone": zone, "gross_area_m2": round(room.area_m2, 2),
                              "proposed_ceiling_height_mm": int(height),
                              "floor_finish": (finishes.PENDING if hotel else
                                               floor_by_zone.get(label, {}).get(
                                                   "material", finishes.PENDING))})
        svg += ['<text x="60" y="765" font-size="13" fill="#67717a">'
                '方案分区与毛面积；基层、构造、损耗、灯具回路及现场尺寸未核，不可施工。</text>',
                '</svg>']
        stem = "I-04-ceiling" if kind == "ceiling" else "I-05-floor-finish"
        dxf_path = directory / f"{stem}.dxf"
        result = DxfAdapter().draw_primitives(prims, dxf_path, layer, project.revision)
        if not result.ok:
            raise ValueError(f"{stem} CAD read-back failed: {result.errors}")
        svg_path = directory / f"{stem}.svg"
        svg_path.write_text("\n".join(svg), encoding="utf-8")
        artifacts.extend([str(dxf_path), str(svg_path)])
    light_points = proposed_lighting(project, level_id)
    light_prims = [Prim("polyline", "I-CEILING",
                        [(float(x), float(y)) for x, y in room.boundary_mm2d], closed=True)
                   for room in rooms]
    light_svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
                 'viewBox="0 0 1200 800">',
                 '<rect width="1200" height="800" fill="#f7f5f0"/>',
                 '<text x="60" y="55" font-size="25" fill="#29343a">照明点位 · 方案预览</text>',
                 '<text x="60" y="78" font-size="13" fill="#647078">'
                 '房间中心为环境灯建议点；床头点对应已建模床头柜，回路/照度未设计</text>']
    for room in rooms:
        pts = ' '.join(f'{60+(x-x0)*scale:.1f},{105+(y1-y)*scale:.1f}'
                       for x, y in room.boundary_mm2d)
        light_svg.append(f'<polygon points="{pts}" fill="#ece8df" '
                         'stroke="#829098" stroke-width="1.2"/>')
    for item in light_points:
        x, y = item["x_mm"], item["y_mm"]
        radius = 180 if item["kind"] == "ambient_proposed" else 125
        light_prims.append(Prim("circle", "I-LIGHT", center=(x, y), radius=radius))
        light_svg.append(f'<circle cx="{60+(x-x0)*scale:.1f}" '
                         f'cy="{105+(y1-y)*scale:.1f}" '
                         f'r="{max(3.0, radius*scale):.1f}" fill="none" '
                         'stroke="#aa7a38" stroke-width="2"/>')
    light_svg += [f'<text x="60" y="746" font-size="13" fill="#59666d">'
                  f'建议点位 {len(light_points)} 处；灯具、照度、开关、回路及消防应急照明待专业确认。'
                  '</text>', '</svg>']
    light_dxf = directory / "I-06-lighting-proposal.dxf"
    result = DxfAdapter().draw_primitives(light_prims, light_dxf, "I-LIGHT",
                                          project.revision)
    if not result.ok:
        raise ValueError(f"lighting CAD read-back failed: {result.errors}")
    light_preview = directory / "I-06-lighting-proposal.svg"
    light_preview.write_text("\n".join(light_svg), encoding="utf-8")
    artifacts.extend([str(light_dxf), str(light_preview)])
    elevation_artifacts, elevation = _typical_elevation(
        project, directory, level_id, rooms, hotel)
    artifacts.extend(elevation_artifacts)
    schedule = directory / "interior-surface-areas.json"
    schedule.write_text(json.dumps({"status": "review_only", "revision": project.revision,
                    "basis": "canonical room polygons; gross room areas, not net purchase quantities",
                    "rooms": areas, "lighting_points": light_points,
                    "typical_wall_elevation": elevation},
                    ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts.append(str(schedule))
    note = directory / "interior-surfaces.md"
    note.write_text("\n".join(["# 顶面、地面及照明点位方案（待审查）", "",
        "四张可编辑 DXF 与 SVG 预览由同一房间、门窗及家具模型生成。面积为房间毛面积，"
        "未扣除设备、固定家具及损耗，不可直接用于采购。",
        "顶标高与灯位均为方案建议；灯具规格、照度、回路、消防应急照明、"
        "机电末端、检修口、地面排版与收边节点尚未定位或核验。",
        "酒店客房区与后勤区按不同功能分区出图；隔声、防火、耐磨及清洁等级尚需专项确认。"
        if hotel else "住宅各功能区按任务书分区；饰面选型待概念与样板确认。",
        f"代表空间 {elevation['room_name']} 的墙面展开仅供方案检视；"
        f"未匹配开口 {len(elevation['unmapped_openings'])} 处须人工校对。",
        "未经现场实测、材料选型及专业签署，不得用于施工。", "", SIGNATURE]),
        encoding="utf-8")
    artifacts.append(str(note))
    return artifacts
