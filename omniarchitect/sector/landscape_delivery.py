"""Landscape S4–S8 deliverables from the canonical L-SITE geometry.

These are review drawings, not surveyed grading, planting specifications or
signed construction documents.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from ..adapters import DxfAdapter, MeshAdapter
from ..registry import SIGNATURE


KINDS = {"planting": "种植带", "water": "水景", "paving": "铺装",
         "circulation": "园路"}
COLORS = {"planting": "#739468", "water": "#76b5c9",
          "paving": "#d5bd95", "circulation": "#a38b6c"}


def _zones(project: Any) -> list[Any]:
    return [s for s in project.spaces_on("L-SITE")
            if s.use in KINDS and len(s.boundary_mm2d) >= 3]


def _preview(zones: list[Any], trees: list[Any], path: Path,
             nodes: list[Any] | None = None) -> None:
    points = [p for s in zones for p in s.boundary_mm2d]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    x1, y1 = max(p[0] for p in points), max(p[1] for p in points)
    scale = min(1000 / max(x1 - x0, 1), 600 / max(y1 - y0, 1))
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
             'viewBox="0 0 1200 800">',
             '<rect width="1200" height="800" fill="#f5f3ed"/>',
             '<text x="80" y="55" font-size="25" fill="#242d26">景观空间模型 · 方案预览</text>',
             '<text x="80" y="77" font-size="13" fill="#58645b">依据 L-SITE 多边形；非实测竖向与施工放线图</text>',
             '<rect x="80" y="95" width="1040" height="620" fill="#eee9dc" stroke="#ccd0c5"/>']
    infill = [s for s in zones if s.properties.get("infill_kind")]
    if infill:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        for kind, fill, label in (("gravel", "#ddd0b5", "透水砂砾地"),
                                   ("lawn", "#adc69a", "中央草坪")):
            selected = [Polygon(s.boundary_mm2d) for s in infill
                        if s.properties.get("infill_kind") == kind]
            if not selected:
                continue
            merged = unary_union(selected)
            polygons = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
            for polygon in polygons:
                paths = []
                for ring in [polygon.exterior, *polygon.interiors]:
                    points = list(ring.coords)
                    paths.append('M ' + ' L '.join(
                        f'{80+(x-x0)*scale:.1f} {95+(y1-y)*scale:.1f}' for x, y in points)
                        + ' Z')
                parts.append(f'<path d="{" ".join(paths)}" fill="{fill}" fill-rule="evenodd"/>')
            pt = merged.representative_point()
            parts.append(f'<text x="{80+(pt.x-x0)*scale:.1f}" '
                         f'y="{95+(y1-pt.y)*scale:.1f}" text-anchor="middle" '
                         f'font-size="12" fill="#3b4639">{label}</text>')
    for s in zones:
        if s.properties.get("infill_kind"):
            continue
        pts = ' '.join(f'{80 + (p[0]-x0)*scale:.1f},{95 + (y1-p[1])*scale:.1f}'
                       for p in s.boundary_mm2d)
        cx, cy = s.centroid
        parts.append(f'<polygon points="{pts}" fill="{COLORS[s.use]}" '
                     'fill-opacity="0.84" stroke="#f5f3ed" stroke-width="2"/>')
        if s.use != "circulation":
            parts.append(f'<text x="{80+(cx-x0)*scale:.1f}" y="{95+(y1-cy)*scale:.1f}" '
                         f'text-anchor="middle" font-size="12" fill="#1a2923">{escape(s.name)}</text>')
    paths = [s for s in zones if s.use == "circulation"]
    if paths:
        parts.append(f'<text x="{80+(x1-x0)*scale/2:.1f}" y="{95+(y1-y0)*scale*.18:.1f}" '
                     'text-anchor="middle" font-size="14" fill="#312b20">环形游线</text>')
    for tree in trees:
        cx, cy = tree.geometry["center"]
        radius = float(tree.geometry.get("crown_radius_mm") or 1100) * scale
        parts.append(f'<circle cx="{80+(cx-x0)*scale:.1f}" '
                     f'cy="{95+(y1-cy)*scale:.1f}" r="{radius:.1f}" '
                     'fill="#406940" fill-opacity="0.67" stroke="#25472e" stroke-width="1"/>')
    for node in nodes or []:
        cx, cy = node.geometry["center"]
        px, py = 80+(cx-x0)*scale, 95+(y1-cy)*scale
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" '
                     'fill="#f4e6b9" stroke="#594a2f" stroke-width="2"/>')
        parts.append(f'<text x="{px+9:.1f}" y="{py-8:.1f}" font-size="11" '
                     f'fill="#493d2e">{escape(str(node.properties.get("name") or "停留点"))}</text>')
    parts += ['<text x="80" y="757" font-size="14" fill="#48534a">'
              '水面 / 种植 / 铺装 / 游线均来自同一模型；交叠区需专业复核。</text>',
              '</svg>']
    path.write_text('\n'.join(parts), encoding="utf-8")


def run(runner: Any, stage: str, directory: Path) -> Any:
    from ..workflow import StageOutcome

    directory.mkdir(parents=True, exist_ok=True)
    zones = _zones(runner.project)
    trees = [e for e in runner.project.by_type("other") if e.level_id == "L-SITE"
             and e.properties.get("landscape_kind") == "tree"
             and len(e.geometry.get("center") or []) == 2]
    nodes = [e for e in runner.project.by_type("other") if e.level_id == "L-SITE"
             and e.properties.get("landscape_kind") == "view_node"
             and len(e.geometry.get("center") or []) == 2]
    if not zones:
        return StageOutcome(stage, status="blocked", error="L-SITE 无可深化的景观空间几何",
                            next_action="先完成景观 S3 并核对场地边界")
    arts: list[str] = []
    notes = ["本成果为方案/待审查深度；场地实测、竖向、植物规格及专业签署未被模拟。"]
    if stage in ("S4", "S7"):
        name = "L-01-景观总平面" if stage == "S4" else "L-01-景观分区复核图"
        result = DxfAdapter().draw_landscape(
            runner.project, directory / f"{name}.dxf",
            title="景观总平面（方案深度）" if stage == "S4" else "景观分区复核（待实测）")
        arts.extend(result.artifacts)
        if not result.ok:
            return StageOutcome(stage, status="failed", adapter="dxf", artifacts=arts,
                                error="景观 DXF 读回审计失败：" + "; ".join(result.errors))
        _preview(zones, trees, directory / "landscape-model-plan.svg", nodes)
        arts.append(str(directory / "landscape-model-plan.svg"))
        lines = ["# 景观" + ("初步深化" if stage == "S4" else "图纸审查") + "（待审查）", "",
                 "| 区域 | 用途 | 模型面积 m² | 建议相对标高 | 待确认做法 |",
                 "|---|---|---:|---:|---|"]
        for s in [z for z in zones if not z.properties.get("infill_kind")]:
            lines.append(f"| {s.name} | {KINDS[s.use]} | {s.area_m2:.2f} | "
                         f"{float(s.properties.get('design_z_mm', 0))/1000:+.2f} m | "
                         "材料/构造/标高待专业确认 |")
        for kind, label in (("lawn", "中央草坪与地被"),
                            ("gravel", "透水砂砾活动地面")):
            area = sum(s.area_m2 for s in zones
                       if s.properties.get("infill_kind") == kind)
            if area:
                lines.append(f"| {label}（同材拼块汇总） | "
                             f"{'绿地/种植' if kind == 'lawn' else '透水铺装'} | "
                             f"{area:.2f} | +0.00 m | 基层/排水待专业确认 |")
        lines += ["", "- 水景：需核水深、防水、溢流和儿童安全。",
                  "- 种植：需核土层、管线、苗木规格和养护条件。",
                  "- 园路与铺装：需核基层、坡向、无障碍和排水。",
                  "- 所列标高仅为相对 ±0.00 的方案台地示意，未建立实测高程基准；"
                  "边界过渡、坡度与排水均未验证。",
                  "- L-SITE 坐标是当前方案模型；若为系统建议边界，不得当作实测放线数据。",
                  "- 本图未含已审定竖向、种植定位及节点构造，不得用于施工。",
                  "", SIGNATURE]
        report = directory / "landscape-review.md"
        report.write_text("\n".join(lines), encoding="utf-8")
        arts.append(str(report))
        return StageOutcome(stage, adapter="dxf", status="degraded", artifacts=arts,
                            notes=notes + ["可编辑景观 DXF 已通过独立读回；专项节点仍待深化。"])
    if stage == "S5":
        result = MeshAdapter().export_obj(runner.project, directory,
                                          level_id="L-SITE", stem="landscape-model")
        arts.extend(result.artifacts)
        if not result.ok:
            return StageOutcome(stage, adapter="mesh", status="failed", artifacts=arts,
                                error="景观 OBJ 读回失败")
        from .model_preview import export as preview_model
        for name, angle in (("isometric-ne", 42.0), ("isometric-sw", 222.0)):
            view = directory / f"{name}.svg"
            preview_model(result.artifacts[0], view, title="庭院景观 · 模型轴测示意",
                          azimuth_deg=angle)
            arts.append(str(view))
        _preview(zones, trees, directory / "landscape-model-plan.svg", nodes)
        arts.append(str(directory / "landscape-model-plan.svg"))
        return StageOutcome(stage, adapter="mesh", status="degraded", artifacts=arts,
                            notes=notes + ["可编辑 OBJ/MTL 记录水面、种植台地、铺装及环路的方案相对标高；"
                                           "本机未生成写实渲染或植物单株模型。"])
    if stage == "S6":
        report = directory / "landscape-coordination.md"
        report.write_text("\n".join(["# 景观专业协调（待审查）", "",
            "- 建筑/场地接口：入口标高、散水、地下结构覆土待核。",
            "- 结构：水景荷载、挡墙及基础待专业复核。",
            "- 机电：给排水、电源、照明与检修口待协调。",
            "- 竖向：当前 L-SITE 仅有平面几何，不具实测标高；不得声称排水已校核。",
            "- 设计冻结和业主确认仍由 G6 管理；本文件不是签署记录。", "", SIGNATURE]),
            encoding="utf-8")
        return StageOutcome(stage, status="degraded", artifacts=[str(report)], notes=notes)
    if stage == "S8":
        from ..concept.handoff import plan_record
        from ..geometry import HAS_SHAPELY

        by_kind = {k: round(sum(s.area_m2 for s in zones if s.use == k), 2)
                   for k in KINDS}
        design_data = plan_record(runner.project).get("design_data") or {}
        union_area = None
        overlap_area = None
        if HAS_SHAPELY:
            from shapely.geometry import Polygon
            from shapely.ops import unary_union

            polygons = [Polygon(s.boundary_mm2d) for s in zones]
            union_area = round(unary_union(polygons).area / 1e6, 2)
            overlap_area = round(sum(s.area_m2 for s in zones)-union_area, 2)
        data = {"project_id": runner.project.project_id,
                "revision": runner.project.revision, "basis": "L-SITE 方案多边形毛面积",
                "quantities_m2": by_kind,
                "modeled_zone_gross_m2": round(sum(by_kind.values()), 2),
                "site_area_estimate_m2": round(float(design_data.get("site_area_m2") or 0), 2),
                "covered_union_m2": union_area,
                "overlap_m2": overlap_area,
                "proposed_tree_count": len(trees),
                "proposed_view_nodes": len(nodes),
                "zones": [{"id": s.id, "name": s.name, "use": s.use,
                           "area_m2": round(s.area_m2, 2)} for s in zones],
                "status": "review_only",
                "missing": ["实测边界与竖向", "植物品种及确认株数",
                            "铺装规格与损耗", "水景深度/设备/防水", "专业审核签署"]}
        if data["site_area_estimate_m2"] and (
            union_area is None or abs(data["site_area_estimate_m2"]-union_area) > 1
            or (overlap_area or 0) > 1):
            data["missing"].insert(0, "未分区地面或模型交叠须复核")
        path = directory / "landscape-takeoff.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        rows = ["# 景观工程量与材料（待审查）", "",
                "| 类别 | 方案毛面积 m² | 材料/品种 |", "|---|---:|---|"]
        for kind, value in by_kind.items():
            rows.append(f"| {KINDS[kind]} | {value:.2f} | 待选型/样板确认 |")
        if data["site_area_estimate_m2"]:
            rows += ["", f"模型分区毛面积合计 {data['modeled_zone_gross_m2']:.2f} m²；"
                     f"与任务书场地估算 {data['site_area_estimate_m2']:.2f} m² "
                     f"差 {data['site_area_estimate_m2']-data['modeled_zone_gross_m2']:+.2f} m²。"
                     f"独立多边形并集 {union_area if union_area is not None else '未核'} m²；"
                     f"交叠 {overlap_area if overlap_area is not None else '未核'} m²。"
                     "仅为方案估算边界，不代表实测红线。"]
        rows += ["", f"模型内方案乔木点位：{len(trees)} 处（仅供空间推敲，非采购株数）。",
                  "以上为模型分区毛面积；未实测、未扣材料损耗，不能直接作为采购量。", "",
                  "确认植物株数、水景设备、铺装厚度和损耗没有输入，不虚构采购数量。", "",
                  "## 待补条件", ""] + [f"- {x}" for x in data["missing"]] + ["", SIGNATURE]
        md = directory / "landscape-materials.md"
        md.write_text("\n".join(rows), encoding="utf-8")
        return StageOutcome(stage, status="degraded", artifacts=[str(path), str(md)],
                            notes=notes + ["面积已按模型统计；并集与交叠有独立核算时已单列。"
                                           "仍不是可采购清单。"])
    raise ValueError(stage)
