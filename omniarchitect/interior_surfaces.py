"""Editable room-by-room ceiling and floor finish review sheets.

The polygons and area figures are read from the installed canonical spaces.
Finish names remain pending unless the selected concept actually supplies them.
These are not reflected ceiling services drawings or construction details.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from . import finishes
from .adapters import DxfAdapter
from .adapters.drawing import Prim
from .registry import SIGNATURE


def export(project: Any, directory: Path, level_id: str) -> list[str]:
    """Write two audited CAD sheets, matching SVGs and gross-area schedule."""
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
    schedule = directory / "interior-surface-areas.json"
    schedule.write_text(json.dumps({"status": "review_only", "revision": project.revision,
                    "basis": "canonical room polygons; gross room areas, not net purchase quantities",
                    "rooms": areas}, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts.append(str(schedule))
    note = directory / "interior-surfaces.md"
    note.write_text("\n".join(["# 顶面与地面分区（待审查）", "",
        "两张可编辑 DXF 与 SVG 预览由同一房间多边形生成。面积为房间毛面积，"
        "未扣除设备、固定家具及损耗，不可直接用于采购。",
        "顶标高为方案建议；灯具、机电末端、检修口、地面排版与收边节点尚未定位。",
        "酒店客房区与后勤区按不同功能分区出图；隔声、防火、耐磨及清洁等级尚需专项确认。"
        if hotel else "住宅各功能区按任务书分区；饰面选型待概念与样板确认。",
        "未经现场实测、材料选型及专业签署，不得用于施工。", "", SIGNATURE]),
        encoding="utf-8")
    artifacts.append(str(note))
    return artifacts
