"""School and hotel deepening from actual levels in the spatial model.

Do not use the residential fit-out template for a teaching building or a hotel.
All files here remain review-only until survey, specialist coordination and
the normal project gates are genuinely satisfied.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .. import finishes, quantities
from ..adapters import BlenderAdapter, DxfAdapter, IfcAdapter, MeshAdapter
from ..adapters.drawing import Prim
from ..registry import SIGNATURE


def _levels(project: Any) -> list[str]:
    state = project.meta.get("sector_levels") or {}
    return [project.levels[0].id, *state.get("generated_ids", [])]


def _takeoff(project: Any) -> dict[str, Any]:
    floors = []
    sums: dict[str, float] = {}
    for lid in _levels(project):
        t = quantities.takeoff(project, lid)
        floors.append({"level": lid, "quantities": t.quantities,
                       "rooms": quantities.room_schedule(project, lid),
                       "doors": quantities.schedule_doors(project, lid),
                       "windows": quantities.schedule_windows(project, lid)})
        for key, value in t.quantities.items():
            sums[key] = sums.get(key, 0.0) + value
    return {"by_floor": floors, "totals": {k: round(v, 2) for k, v in sums.items()}}


def _campus_takeoff(project: Any) -> dict[str, Any]:
    """Schedule the actual site polygons, not the requested programme areas."""
    spaces = project.spaces_on("L-SITE")
    plot = next(s for s in spaces if s.id == "S-CAMPUS-PLOT")
    blocks = []
    for space in spaces:
        key = space.properties.get("site_block_key")
        if not key:
            continue
        height = float(space.properties.get("height_mm") or 0)
        target = space.properties.get("target_area_m2")
        blocks.append({"key": key, "name": space.name,
                       "footprint_m2": round(space.area_m2, 2),
                       "programme_area_m2": round(float(target), 2)
                       if target is not None else None,
                       "height_m": round(height / 1000, 2) if height else None,
                       "massing_volume_m3": round(space.area_m2 * height / 1000, 2)
                       if height else None,
                       "note": space.properties.get("note") or ""})
    return {"boundary_basis": project.meta["campus_site"]["basis"],
            "plot_area_m2": round(plot.area_m2, 2),
            "blocks": blocks,
            "status": "proposed_massing_only",
            "not_included": ["退界与消防车道", "200m 跑道放线", "食堂与体育馆房间/结构",
                             "地形与场地竖向", "实测复核与专业签署"]}


def _sheet_svg(prims: list[Prim], path: Path) -> None:
    """Preview the very same vector primitives written to CAD."""
    pts = [p for item in prims for p in item.points]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    scale = min(1050 / max(x1-x0, 1), 550 / max(y1-y0, 1))
    px = lambda x: 80 + (x-x0)*scale
    py = lambda y: 610 - (y-y0)*scale
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" '
           'viewBox="0 0 1200 700">',
           '<rect width="1200" height="700" fill="#f7f6f2"/>',
           '<text x="80" y="48" font-size="20" fill="#202b31">模型立面 / 剖面 · 方案预览</text>']
    for item in prims:
        color = "#4894af" if item.layer == "A-ELEV-GLAZ" else "#27333b"
        if item.kind in ("line", "polyline"):
            points = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in item.points)
            tag = "polygon" if item.closed else "polyline"
            svg.append(f'<{tag} points="{points}" fill="none" '
                       f'stroke="{color}" stroke-width="{1.5 if item.layer == "A-ELEV-GLAZ" else 2}"/>')
        elif item.kind == "text":
            svg.append(f'<text x="{px(item.center[0]):.1f}" '
                       f'y="{py(item.center[1]):.1f}" text-anchor="middle" '
                       f'font-size="12" fill="#55616a">{escape(item.text)}</text>')
    svg += ['<text x="80" y="672" font-size="13" fill="#67737a">'
            '来自统一模型；边界/结构/净高及签署待核，不可用于施工。</text>', '</svg>']
    path.write_text('\n'.join(svg), encoding="utf-8")


def _school_elevations(project: Any, directory: Path) -> list[str]:
    """North/south elevations and massing section from model coordinates."""
    envelope = next(s for s in project.spaces_on(project.levels[0].id)
                    if s.use == "envelope")
    x0, y0, x1, y1 = envelope.bbox()
    tops = {lv.id: lv.elevation_mm + lv.height_mm for lv in project.levels}
    ztop = max(tops.values())
    wall_by_id = {w.id: w for w in project.by_type("wall")}
    dxf = DxfAdapter()
    arts = []
    for side, yref in (("南", y0), ("北", y1)):
        prims = [Prim("polyline", "A-ELEV",
                      [(x0, 0), (x1, 0), (x1, ztop), (x0, ztop)], closed=True)]
        for lv in project.levels:
            z = lv.elevation_mm
            prims.append(Prim("line", "A-ELEV", [(x0, z), (x1, z)]))
            prims.append(Prim("text", "A-ANNO-TEXT", text=lv.name or lv.id,
                              center=(x0 - 1900, z + 350), height=250))
        for win in project.by_type("window"):
            wall = wall_by_id.get(win.geometry.get("host_wall"))
            axis = wall.wall_axis() if wall else None
            if not axis:
                continue
            (ax, ay), (bx, by) = axis
            if abs(by - ay) > 50 or abs((ay + by) / 2 - yref) > 800:
                continue
            length = max(wall.wall_length_mm(), 1)
            off = float(win.geometry.get("offset_mm") or 0)
            width = float(win.geometry.get("width_mm") or 0)
            start = ax + (bx - ax) * off / length
            end = ax + (bx - ax) * (off + width) / length
            lv = project.level(win.level_id)
            sill = lv.elevation_mm + float(win.geometry.get("sill_mm") or 0)
            head = sill + float(win.geometry.get("height_mm") or 0)
            prims.append(Prim("polyline", "A-ELEV-GLAZ",
                              [(start, sill), (end, sill), (end, head), (start, head)],
                              closed=True))
        prims.append(Prim("text", "A-ANNO-TEXT", text=f"{side}立面（方案深度，待审查）",
                          center=((x0 + x1) / 2, -1500), height=320))
        result = dxf.draw_primitives(prims, directory / f"A-立面-{side}.dxf",
                                     "A-ELEV", project.revision)
        if not result.ok:
            raise ValueError(f"{side}立面 DXF 审计失败：{result.errors}")
        arts.extend(result.artifacts)
        preview = directory / f"A-立面-{side}.svg"
        _sheet_svg(prims, preview)
        arts.append(str(preview))

    section = [Prim("polyline", "A-SECTION",
                    [(y0, 0), (y1, 0), (y1, ztop), (y0, ztop)], closed=True)]
    for lv in project.levels:
        z = lv.elevation_mm
        section.append(Prim("line", "A-SECTION", [(y0, z), (y1, z)]))
        section.append(Prim("text", "A-ANNO-TEXT", text=f"{lv.name} ±{z/1000:.2f}m",
                            center=(y0 - 2300, z + 350), height=240))
    section.append(Prim("text", "A-ANNO-TEXT", text="教学楼体量剖面（结构/净高待核）",
                        center=((y0+y1)/2, -1500), height=320))
    result = dxf.draw_primitives(section, directory / "A-体量剖面.dxf",
                                 "A-SECTION", project.revision)
    if not result.ok:
        raise ValueError(f"体量剖面 DXF 审计失败：{result.errors}")
    preview = directory / "A-体量剖面.svg"
    _sheet_svg(section, preview)
    return [*arts, *result.artifacts, str(preview)]


def run(runner: Any, stage: str, directory: Path) -> Any:
    from ..workflow import StageOutcome

    directory.mkdir(parents=True, exist_ok=True)
    project = runner.project
    sector = (project.meta.get("sector_levels") or {}).get("sector")
    label = "教学楼" if sector == "education" else "酒店客房楼"
    floor_ids = _levels(project)
    data = _takeoff(project)
    notes = ["按统一模型逐层提量；建议轮廓、结构/消防/机电与签署状态须另行核实。"]
    if stage == "S5":
        mesh = MeshAdapter().export_multilevel_obj(project, directory, stem="whole-building")
        if not mesh.ok:
            return StageOutcome(stage, status="failed", adapter="mesh",
                                artifacts=mesh.artifacts, error="整楼 OBJ 读回失败")
        arts = list(mesh.artifacts)
        from .model_preview import export as preview_model
        for name, angle in (("isometric-ne", 42.0), ("isometric-sw", 222.0)):
            view = directory / f"{name}.svg"
            preview_model(mesh.artifacts[0], view,
                          title=f"{label} · {'东北' if angle < 180 else '西南'}轴测模型视图",
                          azimuth_deg=angle)
            arts.append(str(view))
        from ..planner import SchemeResult
        from .plandraw import plan_svg

        for lid in floor_ids:
            floor_elements = [e for e in project.elements if e.level_id == lid]
            floor = SchemeResult(variant="A", title=f"{label} {lid}", strategy="installed",
                                 spaces=[s for s in project.spaces_on(lid)
                                         if s.use != "envelope"],
                                 elements=floor_elements,
                                 metrics={"window_count": sum(e.type == "window"
                                                              for e in floor_elements)})
            svg = directory / f"{lid}-model-plan.svg"
            svg.write_text(plan_svg(floor, title=f"{label} {lid} · 模型平面预览"),
                           encoding="utf-8")
            arts.append(str(svg))
        blender = BlenderAdapter()
        if blender.preflight().available:
            for lid in floor_ids:
                result = blender.build(project, directory / f"blender-{lid}",
                                       level_id=lid, render=False)
                arts.extend(result.artifacts)
                if not result.ok:
                    notes.append(f"Blender {lid} 场景构建失败：{result.errors[:1]}")
        else:
            result = blender.build(project, directory / "blender", render=False)
            arts.extend(result.artifacts)
            notes.append("本机无 Blender：仅有场景重建脚本，无 .blend 或写实渲染。")
        ifc = IfcAdapter().export(project, directory / "ifc", stem="whole-building")
        arts.extend(ifc.artifacts)
        notes.append("IFC4 已生成并读回" if not ifc.validation.get("degraded") and ifc.ok
                     else "IfcOpenShell 不可用或生成失败：未交付真实 IFC。")
        notes.append(f"整楼 OBJ 已读回：{mesh.validation['vertices']} 顶点 / "
                     f"{mesh.validation['faces']} 面；{len(floor_ids)} 个楼层。")
        return StageOutcome(stage, status="degraded", adapter="mesh",
                            artifacts=arts, notes=notes)
    if stage in ("S4", "S7"):
        arts = []
        depth = "schematic" if stage == "S4" else "review_only"
        for lid in floor_ids:
            path = directory / f"{label}-{lid}-平面.dxf"
            result = DxfAdapter().draw_plan(
                project, path, level_id=lid, title=f"{label} {lid} 平面（待审查）",
                scheme="A", depth=depth, include_furniture=True)
            arts.extend(result.artifacts)
            if not result.ok:
                return StageOutcome(stage, status="failed", adapter="dxf",
                                    artifacts=arts, error=f"{lid} DXF 审计失败：{result.errors}")
            if sector == "hospitality":
                from ..interior_surfaces import export as export_surfaces
                try:
                    arts.extend(export_surfaces(project, directory / lid, lid))
                except ValueError as exc:
                    return StageOutcome(stage, status="failed", adapter="dxf",
                                        artifacts=arts, error=f"{lid} 饰面分区图失败：{exc}")
        if sector == "education":
            try:
                arts.extend(_school_elevations(project, directory))
                if project.meta.get("campus_site"):
                    from .site_delivery import export as export_site
                    arts.extend(export_site(project, directory / "campus"))
            except ValueError as exc:
                return StageOutcome(stage, status="failed", adapter="dxf",
                                    artifacts=arts, error=str(exc))
        rows = [f"# {label} {'初步深化' if stage == 'S4' else 'CAD 图纸'}（待审查）", "",
                f"- 已生成 {len(floor_ids)} 层独立可编辑平面 DXF；各层来自模型，不以图纸反推。",
                "- 几何基准与 G3 状态见 project-s3.json；未确认时仅供方案讨论。", "",
                "| 楼层 | 空间数 | 教室/客房数 | 使用面积 m² |", "|---|---:|---:|---:|"]
        key = "teaching" if sector == "education" else "guest"
        for floor in data["by_floor"]:
            rows.append(f"| {floor['level']} | {len(floor['rooms'])} | "
                        f"{sum(r['use'] == key for r in floor['rooms'])} | "
                        f"{floor['quantities']['floor_area_m2']:.1f} |")
        if sector == "education":
            rows += ["", "## 建筑专业待深化", "",
                     "- 总平已由场地空间模型生成 CAD；食堂/体育馆只有建议体量，"
                     "运动场只有用地预留；尚无房间、结构及可施工节点。",
                     "- 南/北立面与体量剖面已按模型坐标出 CAD；结构柱网、"
                     "构造节点、无障碍与疏散仍须补实测及专项设计。",
                     "- 外墙材料、防火构造、教室采光与声学须确认；图纸不可用于施工。"]
        else:
            rows += ["", "## 酒店工装待深化", "",
                     "- 客房标准层及末层已分别建模；大堂、餐饮、宴会厅与后场仍待实测平面。",
                     "- 客房楼各层顶面与地面功能分区已出 CAD/预览；材料、防火、隔声和构造未定。",
                     "- 顶墙地材料、灯具回路、客房样板间、机电末端与消防接口须专项确认。",
                     "- 后场与客流分离仍需现场流线核实，不能凭示意图宣称完成。"]
        mats = finishes.concept_materials(project)
        rows += ["", "## 已选概念的材料方向", ""]
        rows += [f"- {m['name']}：{m['application']}（{m['finish'] or '做法待定'}）"
                 for m in mats] or ["- 材料未确认；不得套用住宅饰面默认值。"]
        rows += ["", SIGNATURE]
        report = directory / "deepening-review.md"
        report.write_text("\n".join(rows), encoding="utf-8")
        arts.append(str(report))
        return StageOutcome(stage, status="degraded", adapter="dxf",
                            artifacts=arts, notes=notes + ["平面已读回；立面/节点尚未完成。"])

    if stage == "S6":
        issues = (["食堂、体育馆、运动场的独立体量与疏散", "教学楼竖向交通和消防核算",
                   "结构柱网、地勘与现场红线"] if sector == "education" else
                  ["大堂/餐饮/宴会厅和后场实测平面", "客房层管井与消防末端",
                   "声学、照明与机电设备容量"])
        payload = {"status": "needs_specialist_review", "sector": sector,
                   "revision": project.revision, "levels": floor_ids,
                   "open_items": issues, "geometry_locked": False}
        path = directory / "coordination.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md = directory / "coordination.md"
        md.write_text("\n".join([f"# {label}技术协调（未闭环）", ""] +
                   [f"- {item}" for item in issues] + ["", "未获专业审查和 G6 确认，"
                   "本文件不等于设计锁定。", "", SIGNATURE]), encoding="utf-8")
        return StageOutcome(stage, status="degraded", artifacts=[str(path), str(md)],
                            notes=notes + ["专业协调未闭环；未声明设计锁定。"])

    if stage == "S8":
        key = "teaching" if sector == "education" else "guest"
        actual = sum(r["use"] == key for f in data["by_floor"] for r in f["rooms"])
        data.update({"project_id": project.project_id, "revision": project.revision,
                     "sector": sector, "status": "review_only",
                     "modeled_primary_rooms": actual,
                     "basis": "各楼层统一模型净使用面积/构件几何；非总建筑面积"})
        if sector == "education" and project.meta.get("campus_site"):
            data["campus_site"] = _campus_takeoff(project)
        path = directory / "sector-takeoff.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        q = data["totals"]
        mats = finishes.concept_materials(project)
        rows = [f"# {label}全楼工程量与材料（待审查）", "",
                f"- 模型中 {'普通教室' if sector == 'education' else '客房'}：{actual} 间",
                f"- 模型层数：{len(floor_ids)}；使用面积 {q.get('floor_area_m2', 0):.1f} m²"
                "（非总建筑面积）", "",
                "| 项目 | 模型数量 | 待确认材料/设备 |", "|---|---:|---|"]
        for label_name, qty_key, unit in (
            ("地面", "floor_area_m2", "m²"), ("顶面", "ceiling_area_m2", "m²"),
            ("墙面", "wall_finish_area_m2", "m²"), ("门", "door_count", "樘"),
            ("窗", "window_count", "樘"), ("家具", "furniture_count", "件")):
            rows.append(f"| {label_name} | {q.get(qty_key, 0):.1f} {unit} | "
                        "按样板与专业图纸确认 |")
        rows += ["", "## 概念材料（不等于采购规格）", ""]
        rows += [f"- {m['name']}：{m['application']}" for m in mats] or ["- 尚未确认材料品种。"]
        if "campus_site" in data:
            campus = data["campus_site"]
            rows += ["", "## 校园总平面模型量（仅为方案体量）", "",
                     f"- 场地边界来源：{campus['boundary_basis']}；模型场地 "
                     f"{campus['plot_area_m2']:.2f} m²，不等于实测红线。", "",
                     "| 空间 | 模型占地 m² | 任务面积 m² | 体量高度 m | 说明 |",
                     "|---|---:|---:|---:|---|"]
            for block in campus["blocks"]:
                height = (f"{block['height_m']:.2f}" if block["height_m"] is not None
                          else "未建模")
                target = (f"{block['programme_area_m2']:.2f}"
                          if block["programme_area_m2"] is not None else "—")
                rows.append(f"| {block['name']} | {block['footprint_m2']:.2f} | "
                            f"{target} | {height} | {block['note']} |")
            rows += ["", "食堂、体育馆的体量高度仅为建模假设，体积不能作为结算工程量。"
                     "运动场只是用地预留，未设计 200m 跑道。"
                     "任务面积与模型占地应逐项核对，不得自动视为满足。"]
        rows += ["", "## 交付限制", "",
                 "- 仅统计已建模空间；未建模配套不得假定数量为零。",
                 "- 面积、数量、单价与损耗须造价和专业人员复核；当前不输出虚构总价。",
                 "- 所有图纸、模型、物料仍待 G3–G8 与持证专业签署。", "", SIGNATURE]
        md = directory / "sector-materials.md"
        md.write_text("\n".join(rows), encoding="utf-8")
        return StageOutcome(stage, status="degraded", artifacts=[str(path), str(md)],
                            notes=notes + [f"全楼已建模 {actual} 间，配套范围未冒充完工。"])
    raise ValueError(stage)
