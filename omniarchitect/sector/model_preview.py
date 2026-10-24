"""Read a delivered OBJ and draw a truthful, non-photorealistic axonometric view.

The SVG uses only vertices/faces from the saved OBJ. It is a model inspection
view, not a generated effect image or a substitute for professional rendering.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path
from typing import Sequence, Tuple


COLORS = {
    "floor": "#d6c7ac", "wall": "#e7e1d5", "glass": "#8faab0",
    "door": "#a78067", "furniture": "#a89980", "ceiling": "#e6e1d8",
    "site_ground": "#e5e6da", "site_building": "#c9b597",
    "site_sport": "#9bb996", "site_forecourt": "#cfc7b8",
    "landscape_planting": "#93ae86", "landscape_lawn": "#9ebc88",
    "landscape_water": "#82b5c8", "landscape_paving": "#cabda2",
    "landscape_gravel": "#c3baaa", "landscape_path": "#ad9d80",
    "landscape_canopy": "#55784d", "landscape_trunk": "#806b54",
}


def export(obj_path: str | Path, target: str | Path, *, title: str,
           azimuth_deg: float = 42.0, elevation_deg: float = 28.0,
           labels: Sequence[Tuple[float, float, float, str]] = ()) -> dict:
    """Project real OBJ faces to SVG; fail if no valid geometry can be read."""
    source = Path(obj_path)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[str, list[int]]] = []
    material = "floor"
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            values = line.split()
            vertices.append((float(values[1]), float(values[2]), float(values[3])))
        elif line.startswith("usemtl "):
            material = line.split(maxsplit=1)[1].strip()
        elif line.startswith("f "):
            indices = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            if len(indices) >= 3 and all(0 <= i < len(vertices) for i in indices):
                faces.append((material, indices))
    if not vertices or not faces:
        raise ValueError(f"OBJ 无可投影面：{source}")

    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    sin_a, cos_a, sin_e, cos_e = math.sin(az), math.cos(az), math.sin(el), math.cos(el)
    projected = []
    for x, y, z in vertices:
        along = sin_a*x + cos_a*y
        projected.append((cos_a*x - sin_a*y,
                          sin_e*along - cos_e*z,
                          cos_e*along + sin_e*z))
    min_u = min(p[0] for p in projected)
    max_u = max(p[0] for p in projected)
    min_v = min(p[1] for p in projected)
    max_v = max(p[1] for p in projected)
    scale = min(1060/max(max_u-min_u, 1), 590/max(max_v-min_v, 1))
    ox = 600 - (min_u+max_u)*scale/2
    oy = 395 - (min_v+max_v)*scale/2
    visible = []
    for mat, indices in faces:
        p0, p1, p2 = (vertices[i] for i in indices[:3])
        a = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
        b = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
        normal = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
                  a[0]*b[1]-a[1]*b[0])
        facing = normal[0]*sin_a*cos_e + normal[1]*cos_a*cos_e + normal[2]*sin_e
        if facing <= 1e-6:
            continue
        depth = sum(projected[i][2] for i in indices)/len(indices)
        points = " ".join(f"{ox+projected[i][0]*scale:.1f},"
                          f"{oy+projected[i][1]*scale:.1f}" for i in indices)
        visible.append((depth, mat, points))
    if not visible:
        raise ValueError(f"OBJ 没有面向该视角的面：{source}")
    # A site-wide ground polygon has a misleading centroid depth: sorting it
    # with individual blocks can paint over half the campus. It is a substrate.
    visible.sort(key=lambda row: (row[1] != "site_ground", row[0]))
    rows = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" '
            'viewBox="0 0 1200 760">',
            '<rect width="1200" height="760" fill="#f6f6f3"/>',
            f'<text x="70" y="45" font-size="24" fill="#233139">{escape(title)}</text>',
            '<text x="70" y="69" font-size="13" fill="#56676a">'
            '从交付 OBJ 几何读回投影 · 模型轴测示意，非写实渲染/施工依据</text>']
    for _depth, mat, points in visible:
        stroke = 'stroke="none"' if mat in (
            "landscape_planting", "landscape_lawn", "landscape_water",
            "landscape_paving", "landscape_gravel", "landscape_path") else (
            'stroke="#485558" stroke-opacity=".22" stroke-width=".55"')
        rows.append(f'<polygon points="{points}" fill="{COLORS.get(mat, "#c4c6bf")}" '
                    f'{stroke}/>')
    # 房间名直接标在投影后的中心点：轴测图没有名字，客户认不出哪间是哪间。
    # 白描边保证压在墙线上也读得清。
    for x, y, z, text in labels:
        along = sin_a*x + cos_a*y
        u = cos_a*x - sin_a*y
        v = sin_e*along - cos_e*z
        lx, ly = ox + u*scale, oy + v*scale
        rows.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="13" text-anchor="middle" '
            f'fill="#233139" stroke="#f6f6f3" stroke-width="3" paint-order="stroke" '
            f'font-family="sans-serif">{escape(text)}</text>')
    rows += [f'<text x="70" y="731" font-size="12" fill="#657277">'
             f'OBJ 顶点 {len(vertices)} · 面 {len(faces)} · 当前视角可见面 {len(visible)}'
             '</text>', '</svg>']
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(rows), encoding="utf-8")
    return {"source": str(source), "preview": str(destination),
            "vertices": len(vertices), "faces": len(faces),
            "visible_faces": len(visible)}
