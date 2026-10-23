"""Proposed campus block model shared by site CAD, preview and 3D massing.

Only the teaching building has designed room/facade geometry. Ancillary blocks
are explicitly massing reservations, never room plans or approved footprints.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path
from typing import Any

from ..adapters import DxfAdapter
from ..adapters.drawing import Prim
from ..geometry import point_in_polygon
from ..model import Element, Level, Space
from . import site


def _rect(cx: float, cy: float, width: float, depth: float) -> list[list[float]]:
    return [[cx-width/2, cy-depth/2], [cx+width/2, cy-depth/2],
            [cx+width/2, cy+depth/2], [cx-width/2, cy+depth/2]]


def install_school(project: Any, program: Any, brief: Any) -> dict[str, Any]:
    """Place 24-class-school blocks on a proposed site, without fake approvals."""
    plot = site.plot(project, brief)
    boundary = plot["polygon"]
    xs, ys = [p[0] for p in boundary], [p[1] for p in boundary]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    width, depth = x1-x0, y1-y0
    first = project.levels[0]
    envelope = next(s for s in project.spaces_on(first.id) if s.use == "envelope")
    bx0, by0, bx1, by1 = envelope.bbox()
    teaching_w, teaching_d = bx1-bx0, by1-by0
    if teaching_w > width*.55 or teaching_d > depth*.40:
        raise ValueError("教学楼轮廓过大：当前场地无法放置配套与运动场")
    blocks = {b["key"]: b for b in program.blocks}
    if not {"teach", "canteen", "gym", "sport"}.issubset(blocks):
        raise ValueError("校园总平面缺教学楼、食堂、体育馆或运动场面积输入")
    entrance = plot["entrance"]
    # Local design axes: near entrance = north in canonical XY, or rotate the
    # same composition for other known approach sides. No planning setbacks
    # are inferred from this geometry.
    def location(u: float, v: float) -> tuple[float, float]:
        if entrance == "s":
            v = 1-v
        elif entrance == "e":
            u, v = v, 1-u
        elif entrance == "w":
            u, v = 1-v, u
        return x0+u*width, y0+v*depth

    teach_center = location(.52, .72)
    canteen_center = location(.16, .58)
    gym_center = location(.84, .58)
    sport_center = location(.50, .32)
    forecourt_center = location(.52, .92)
    def size(area: float, aspect: float, max_w: float, max_d: float) -> tuple[float, float]:
        w = min(math.sqrt(max(area, 1)*1e6*aspect), max_w)
        return w, min(max(area, 1)*1e6/w, max_d)
    canteen_w, canteen_d = size(float(blocks["canteen"]["area_m2"]), 1.2,
                                width*.19, depth*.30)
    gym_w, gym_d = size(float(blocks["gym"]["area_m2"]), 1.25,
                        width*.21, depth*.38)
    sport_w, sport_d = size(float(blocks["sport"]["area_m2"]), 1.4,
                            width*.45, depth*.49)
    if entrance in ("e", "w"):
        teaching_w, teaching_d = teaching_d, teaching_w
        canteen_w, canteen_d = canteen_d, canteen_w
        gym_w, gym_d = gym_d, gym_w
        sport_w, sport_d = sport_d, sport_w
    candidates = [
        ("teach", "教学楼", "site_building", _rect(*teach_center, teaching_w, teaching_d),
         0.0, "与 L1–L4 教学楼模型定位一致，非额外体量"),
        ("canteen", "学生食堂（体量预留）", "site_building",
         _rect(*canteen_center, canteen_w, canteen_d), 5400.0,
         "仅为单层体量预留；厨房工艺、卫生与疏散未设计"),
        ("gym", "体育馆（体量预留）", "site_building",
         _rect(*gym_center, gym_w, gym_d), 9000.0,
         "仅为大跨体量预留；结构与独立疏散未设计"),
        ("sport", "运动场（空间预留）", "sport",
         _rect(*sport_center, sport_w, sport_d), 0.0,
         "200m 跑道尚未放线与校核，不得按本轮廓认定"),
        ("forecourt", "北侧集散场地（待核）", "forecourt",
         _rect(*forecourt_center, width*.28, depth*.08), 0.0,
         "人车分流与校门安防尚未专项核实"),
    ]
    for key, name, use, ring, _height, _note in candidates:
        if not all((min(xs)-1 <= x <= max(xs)+1 and min(ys)-1 <= y <= max(ys)+1)
                   if plot["basis"] == "assumed" else point_in_polygon((x, y), boundary)
                   for x, y in ring):
            raise ValueError(f"{name} 超出场地边界，不能生成伪总平面")
    for i, (_key_a, name_a, _use_a, ring_a, _height_a, _note_a) in enumerate(candidates):
        ax0, ay0, ax1, ay1 = (ring_a[0][0], ring_a[0][1],
                              ring_a[2][0], ring_a[2][1])
        for _key_b, name_b, _use_b, ring_b, _height_b, _note_b in candidates[i+1:]:
            ox0, oy0, ox1, oy1 = (ring_b[0][0], ring_b[0][1],
                                   ring_b[2][0], ring_b[2][1])
            if min(ax1, ox1) > max(ax0, ox0) and min(ay1, oy1) > max(ay0, oy0):
                raise ValueError(f"{name_a} 与 {name_b} 的场地占地重叠，须重新排布")
    if not any(lv.id == "L-SITE" for lv in project.levels):
        project.levels.append(Level(id="L-SITE", name="场地", elevation_mm=0,
                                    height_mm=0))
    project.spaces = [s for s in project.spaces if s.source != "sector_campus"]
    project.elements = [e for e in project.elements if e.source != "sector_campus"]
    project.spaces.append(Space(id="S-CAMPUS-PLOT", level_id="L-SITE",
        name="校园边界（待测绘）", use="envelope", boundary_mm2d=boundary,
        source="sector_campus", confidence=.3,
        properties={"proposed": plot["basis"] != "surveyed", "requires_door": False,
                    "basis": plot["basis"], "note": plot["note"]}))
    project.spaces.append(Space(id="S-CAMPUS-GROUND", level_id="L-SITE",
        name="场地基面", use="site_ground", boundary_mm2d=boundary,
        source="sector_campus", confidence=.3,
        properties={"proposed": True, "requires_door": False,
                    "design_z_mm": -120,
                    "note": "基面下置仅供模型显示，不计入建筑/绿地工程量或实测标高"}))
    for key, name, use, ring, height, note in candidates:
        project.spaces.append(Space(
            id=f"S-CAMPUS-{key.upper()}", level_id="L-SITE", name=name,
            use=use, boundary_mm2d=ring, source="sector_campus", confidence=.3,
            properties={"site_block_key": key, "proposed": True,
                        "requires_door": False, "height_mm": height, "note": note,
                        "target_area_m2": float(blocks[key]["area_m2"])
                        if key in ("canteen", "gym", "sport") else None}))
        if height:
            project.elements.append(Element(
                id=f"E-CAMPUS-{key.upper()}", type="other", level_id="L-SITE",
                geometry={"footprint_mm2d": ring, "height_mm": height},
                source="sector_campus", confidence=.3, uncertain=True,
                properties={"site_kind": "massing", "host_space": f"S-CAMPUS-{key.upper()}",
                            "note": note}))
    dx = teach_center[0]-teaching_w/2-bx0
    dy = teach_center[1]-teaching_d/2-by0
    project.meta["site_level_offsets_mm"] = {
        lv.id: [round(dx, 2), round(dy, 2)] for lv in project.levels
        if lv.id != "L-SITE"}
    project.meta["campus_site"] = {
        "basis": plot["basis"], "entrance": entrance,
        "plot_m2": round(float(plot["site_m2"]), 1),
        "teaching_footprint_m2": round(teaching_w*teaching_d/1e6, 2),
        "support_blocks": ["canteen", "gym", "sport"],
        "status": "proposed_massing_only"}
    return dict(project.meta["campus_site"])


def _primitives(project: Any) -> list[Prim]:
    spaces = project.spaces_on("L-SITE")
    plot = next(s for s in spaces if s.id == "S-CAMPUS-PLOT")
    prims = [Prim("polyline", "S-PLOT", [(float(x), float(y)) for x, y in plot.boundary_mm2d],
                  closed=True)]
    for space in spaces:
        key = space.properties.get("site_block_key")
        if not key:
            continue
        layer = "S-SPORT" if key == "sport" else (
            "S-FORECOURT" if key == "forecourt" else "S-FOOTPRINT")
        prims.append(Prim("polyline", layer,
                          [(float(x), float(y)) for x, y in space.boundary_mm2d],
                          closed=True))
        prims.append(Prim("text", "S-ANNO", text=space.name,
                          center=space.centroid, height=220))
    gate = _gate(project)
    if gate:
        (gx, gy), (rx0, ry0, rx1, ry1) = gate["point"], gate["road_band"]
        prims.append(Prim("polyline", "S-ROAD",
                          [(float(rx0), float(ry0)), (float(rx1), float(ry0)),
                           (float(rx1), float(ry1)), (float(rx0), float(ry1))],
                          closed=True))
        prims.append(Prim("text", "S-ROAD", text="城市道路（示意）",
                          center=((rx0 + rx1) / 2, (ry0 + ry1) / 2), height=260))
        prims.append(Prim("text", "S-ANNO", text="主入口",
                          center=(gx, gy), height=260))
    prims.append(Prim("text", "S-ANNO", text="校园总平面（体量方案，非报建/施工图）",
                      center=plot.centroid, height=300))
    return prims


def _gate(project: Any) -> dict[str, Any] | None:
    """入口在哪一侧 + 该侧的临路带。只读已记录的方位，不重新判断。"""
    meta = (project.meta or {}).get("campus_site") or {}
    side = str(meta.get("entrance") or "")
    plot = next((s for s in project.spaces_on("L-SITE") if s.id == "S-CAMPUS-PLOT"), None)
    if not side or plot is None:
        return None
    x0, y0, x1, y1 = plot.bbox()
    road = 12000.0
    if side == "n":
        return {"point": ((x0 + x1) / 2, y1), "inward": (0, -1),
                "road_band": (x0, y1 + 400, x1, y1 + 400 + road)}
    if side == "s":
        return {"point": ((x0 + x1) / 2, y0), "inward": (0, 1),
                "road_band": (x0, y0 - 400 - road, x1, y0 - 400)}
    if side == "e":
        return {"point": (x1, (y0 + y1) / 2), "inward": (-1, 0),
                "road_band": (x1 + 400, y0, x1 + 400 + road, y1)}
    return {"point": (x0, (y0 + y1) / 2), "inward": (1, 0),
            "road_band": (x0 - 400 - road, y0, x0 - 400, y1)}


def export(project: Any, directory: Path, stem: str = "A-总平面-体量方案") -> list[str]:
    """Editable DXF plus view of the exact same site polygons."""
    directory.mkdir(parents=True, exist_ok=True)
    dxf = directory / f"{stem}.dxf"
    result = DxfAdapter().draw_primitives(_primitives(project), dxf, "S-FOOTPRINT",
                                          project.revision)
    if not result.ok:
        raise ValueError(f"校园总平 CAD 读回失败：{result.errors}")
    plot = next(s for s in project.spaces_on("L-SITE") if s.id == "S-CAMPUS-PLOT")
    # 画框要把临路带一起圈进来：只按红线算，道路会被裁到画布外面。
    x0, y0, x1, y1 = plot.bbox()
    gate = _gate(project)
    if gate:
        gx0, gy0, gx1, gy1 = gate["road_band"]
        x0, y0 = min(x0, gx0), min(y0, gy0)
        x1, y1 = max(x1, gx1), max(y1, gy1)
    scale = min(960/max(x1-x0, 1), 560/max(y1-y0, 1))
    px = lambda x: 100+(x-x0)*scale
    py = lambda y: 640-(y-y0)*scale
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
           'viewBox="0 0 1200 800">', '<defs><marker id="g" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
           'markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" '
           'fill="#b4462f"/></marker></defs>',
           '<rect width="1200" height="800" fill="#f6f6f2"/>',
           '<text x="100" y="48" font-size="24" fill="#21313b">校园总平面 · 体量方案</text>',
           '<text x="100" y="72" font-size="13" fill="#59676c">场地边界与配套位置为方案建议；'
           '仅教学楼具备逐层房间模型</text>']
    colors = {"teach": "#d9c8a6", "canteen": "#e7d8ba", "gym": "#c9d3d9",
              "sport": "#a7c2a2", "forecourt": "#ddd6c8"}
    for sp in [plot, *[s for s in project.spaces_on("L-SITE")
                       if s.properties.get("site_block_key")]]:
        key = str(sp.properties.get("site_block_key") or "plot")
        pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in sp.boundary_mm2d)
        svg.append(f'<polygon points="{pts}" fill="{colors.get(key,"#f0eee7")}" '
                   'stroke="#4d5a5d" stroke-width="2"/>')
        if key != "plot":
            cx, cy = sp.centroid
            svg.append(f'<text x="{px(cx):.1f}" y="{py(cy):.1f}" text-anchor="middle" '
                       f'font-size="13" fill="#233139">{escape(sp.name)}</text>')
    gate = _gate(project)
    if gate:
        gx, gy = gate["point"]
        bx0, by0, bx1, by1 = gate["road_band"]
        svg.append(f'<polygon points="{px(bx0):.1f},{py(by1):.1f} {px(bx1):.1f},{py(by1):.1f} '
                   f'{px(bx1):.1f},{py(by0):.1f} {px(bx0):.1f},{py(by0):.1f}" '
                   'fill="#e2e0d8" stroke="#9a948a" stroke-width="1.5"/>')
        svg.append(f'<text x="{px((bx0+bx1)/2):.1f}" y="{py((by0+by1)/2):.1f}" '
                   'text-anchor="middle" font-size="12" fill="#6a6660">城市道路（示意）</text>')
        ix, iy = gate["inward"]
        svg.append(f'<line x1="{px(gx - ix*2000):.1f}" y1="{py(gy - iy*2000):.1f}" '
                   f'x2="{px(gx + ix*6000):.1f}" y2="{py(gy + iy*6000):.1f}" '
                   'stroke="#b4462f" stroke-width="5" marker-end="url(#g)"/>')
        svg.append(f'<text x="{px(gx + ix*9000):.1f}" y="{py(gy + iy*9000):.1f}" '
                   'font-size="13" fill="#b4462f" text-anchor="middle">主入口</text>')
        # 人行流线：校门 → 集散场地（家长接送止于此，不进教学区）
        fore = next((s for s in project.spaces_on("L-SITE")
                     if s.properties.get("site_block_key") == "forecourt"), None)
        if fore is not None:
            fx, fy = fore.centroid
            svg.append(f'<line x1="{px(gx):.1f}" y1="{py(gy):.1f}" x2="{px(fx):.1f}" '
                       f'y2="{py(fy):.1f}" stroke="#6b7f8a" stroke-width="2.5" '
                       'stroke-dasharray="9 6"/>')
            svg.append(f'<text x="{px((gx+fx)/2+4000):.1f}" y="{py((gy+fy)/2):.1f}" '
                       'font-size="12" fill="#6b7f8a">人行流线（家长止于集散场地）</text>')
    svg += ['<text x="100" y="755" font-size="13" fill="#657077">'
            '用地红线、退界、消防车道与运动场尺度未核；食堂/体育馆只有体量预留。</text>',
            '</svg>']
    preview = directory / f"{stem}.svg"
    preview.write_text('\n'.join(svg), encoding="utf-8")
    return [str(dxf), str(preview)]
