"""School and hotel deepening from actual levels in the spatial model.

Do not use the residential fit-out template for a teaching building or a hotel.
All files here remain review-only until survey, specialist coordination and
the normal project gates are genuinely satisfied.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import math
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


def _sheet_svg(prims: list[Prim], path: Path, title: str = "") -> None:
    """Preview the very same vector primitives written to CAD."""
    pts = [p for item in prims for p in item.points]
    # Text has width but no points: without its anchor in the bbox, a level tag
    # sitting outside the wall gets clipped in half by the canvas edge.
    pts += [item.center for item in prims if item.kind in ("text", "circle")]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    pad_x = max((x1 - x0) * 0.07, 1500.0)
    pad_y = max((y1 - y0) * 0.05, 800.0)
    x0, y0, x1, y1 = x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y
    scale = min(1050 / max(x1-x0, 1), 550 / max(y1-y0, 1))
    px = lambda x: 80 + (x-x0)*scale
    py = lambda y: 610 - (y-y0)*scale
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" '
           'viewBox="0 0 1200 700">',
           '<rect width="1200" height="700" fill="#f7f6f2"/>',
           f'<text x="80" y="48" font-size="20" fill="#202b31">'
           f'{escape(title or "模型立面 / 剖面 · 方案预览")}</text>']
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


def _opening_span(wall_axis: Any, offset: float, width: float,
                  along_x: bool) -> tuple[float, float] | None:
    """Project an opening onto the facade axis, whichever way the wall runs."""
    if not wall_axis:
        return None
    (ax, ay), (bx, by) = wall_axis
    length = math.hypot(bx - ax, by - ay)
    if length < 1:
        return None
    ux, uy = (bx - ax) / length, (by - ay) / length
    p0 = (ax + ux * offset, ay + uy * offset)
    p1 = (ax + ux * (offset + width), ay + uy * (offset + width))
    if along_x:
        return (min(p0[0], p1[0]), max(p0[0], p1[0]))
    return (min(p0[1], p1[1]), max(p0[1], p1[1]))


def _school_elevations(project: Any, directory: Path) -> list[str]:
    """Four elevations from model coordinates, plus the massing section.

    Two elevations is not a facade design: the east and west ends are where a
    school shows its stairs, its gable and its end classroom window rhythm.
    """
    envelope = next(s for s in project.spaces_on(project.levels[0].id)
                    if s.use == "envelope")
    x0, y0, x1, y1 = envelope.bbox()
    tops = {lv.id: lv.elevation_mm + lv.height_mm for lv in project.levels}
    ztop = max(tops.values())
    wall_by_id = {w.id: w for w in project.by_type("wall")}
    dxf = DxfAdapter()
    arts = []

    #: (name, reference coordinate, project onto X?, the coordinate pair to draw)
    sides = (("南", y0, True, x0, x1), ("北", y1, True, x0, x1),
             ("东", x1, False, y0, y1), ("西", x0, False, y0, y1))
    for side, ref, along_x, a, b in sides:
        prims = [Prim("polyline", "A-ELEV",
                      [(a, 0), (b, 0), (b, ztop), (a, ztop)], closed=True)]
        for lv in project.levels:
            z = lv.elevation_mm
            prims.append(Prim("line", "A-ELEV", [(a, z), (b, z)]))
            prims.append(Prim("text", "A-ANNO-TEXT", text=f"{lv.name} {z/1000:+.2f}",
                              center=(a - 2000, z + 350), height=250))
        for item in project.by_type("window"):
            wall = wall_by_id.get(item.geometry.get("host_wall"))
            axis = wall.wall_axis() if wall else None
            if not axis:
                continue
            (ax, ay), (bx, by) = axis
            # A wall belongs to this facade when it runs along it and sits on it.
            if along_x:
                if abs(by - ay) > 50 or abs((ay + by) / 2 - ref) > 800:
                    continue
            else:
                if abs(bx - ax) > 50 or abs((ax + bx) / 2 - ref) > 800:
                    continue
            span = _opening_span(axis, float(item.geometry.get("offset_mm") or 0),
                                 float(item.geometry.get("width_mm") or 0), along_x)
            if not span:
                continue
            lv = project.level(item.level_id)
            sill = lv.elevation_mm + float(item.geometry.get("sill_mm") or 0)
            head = sill + float(item.geometry.get("height_mm") or 0)
            prims.append(Prim("polyline", "A-ELEV-GLAZ",
                              [(span[0], sill), (span[1], sill),
                               (span[1], head), (span[0], head)], closed=True))
        prims.append(Prim("text", "A-ANNO-TEXT", text=f"{side}立面（方案深度，待审查）",
                          center=((a + b) / 2, -1500), height=320))
        result = dxf.draw_primitives(prims, directory / f"A-立面-{side}.dxf",
                                     "A-ELEV", project.revision)
        if not result.ok:
            raise ValueError(f"{side}立面 DXF 审计失败：{result.errors}")
        arts.extend(result.artifacts)
        preview = directory / f"A-立面-{side}.svg"
        _sheet_svg(prims, preview, title=f"{side}立面 · 方案深度")
        arts.append(str(preview))

    section = [Prim("polyline", "A-SECTION",
                    [(y0, 0), (y1, 0), (y1, ztop), (y0, ztop)], closed=True)]
    for lv in project.levels:
        z = lv.elevation_mm
        section.append(Prim("line", "A-SECTION", [(y0, z), (y1, z)]))
        section.append(Prim("text", "A-ANNO-TEXT", text=f"{lv.name} ±{z/1000:.2f}m",
                            center=(y0 - 2300, z + 350), height=240))
        section.append(Prim("text", "A-ANNO-TEXT",
                            text=f"层高 {lv.height_mm/1000:.2f}m",
                            center=(y1 + 2200, z + lv.height_mm / 2), height=230))
    section.append(Prim("text", "A-ANNO-TEXT", text="教学楼体量剖面（结构/净高待核）",
                        center=((y0+y1)/2, -1500), height=320))
    result = dxf.draw_primitives(section, directory / "A-体量剖面.dxf",
                                 "A-SECTION", project.revision)
    if not result.ok:
        raise ValueError(f"体量剖面 DXF 审计失败：{result.errors}")
    preview = directory / "A-体量剖面.svg"
    _sheet_svg(section, preview, title="体量剖面 · 方案深度")
    return [*arts, *result.artifacts, str(preview)]


#: Opening schedule grouping: a door and a window of the same size are still
#: different products, so the type prefixes never merge.
def _opening_schedule(project: Any, directory: Path) -> list[str]:
    """Door and window schedule counted from the model, not typed by hand.

    Construction needs this table to order frames. The numbers here are the
    modelled openings; wall build-ups, fire ratings and hardware still need the
    specifier.
    """
    groups: dict[tuple[str, float, float], dict[str, Any]] = {}
    for kind, label in (("door", "门"), ("window", "窗")):
        for item in project.by_type(kind):
            w = float(item.geometry.get("width_mm") or 0)
            h = float(item.geometry.get("height_mm") or 0)
            if w <= 0 or h <= 0:
                continue
            key = (label, w, h)
            row = groups.setdefault(key, {"count": 0, "levels": set(), "items": []})
            row["count"] += 1
            row["levels"].add(item.level_id)
            row["items"].append(item.id)
    if not groups:
        return []

    ordered = sorted(groups.items(), key=lambda kv: (kv[0][0] != "门", -kv[1]["count"]))
    floor_order = {lv.id: i for i, lv in enumerate(project.levels)}
    rows: list[tuple[str, str, str, str, str]] = []
    counter = {"门": 0, "窗": 0}
    for (label, w, h), data in ordered:
        # Doors and windows are numbered in their own series: M-01…, C-01…
        # A shared counter that runs M-01, M-02, C-03 looks like a missing sheet.
        counter[label] += 1
        prefix = "M" if label == "门" else "C"
        code = f"{prefix}-{counter[label]:02d}"
        # Floors read bottom-up, the way they are built — not alphabetically.
        lv_names = "、".join(str(project.level(x).name or x) for x in
                             sorted(data["levels"], key=lambda i: floor_order.get(i, 99)))
        rows.append((code, label, f"{w:.0f}×{h:.0f}", str(data["count"]), lv_names))

    # CAD sheet: a real table drawn with lines and text, so it can be edited.
    prims: list[Prim] = []
    col_w = (1900.0, 1200.0, 2200.0, 1400.0, 4200.0)
    row_h = 700.0
    x = 0.0
    tops = [0.0]
    for w in col_w:
        x += w
        tops.append(x)
    height = row_h * (len(rows) + 1)          # header + data rows, no blank tail
    for r in range(len(rows) + 2):            # grid lines: one more than rows
        y = -r * row_h
        prims.append(Prim("line", "A-ANNO-TEXT", [(0.0, y), (tops[-1], y)]))
    for xv in tops:
        prims.append(Prim("line", "A-ANNO-TEXT", [(xv, 0.0), (xv, -height)]))
    headers = ("编号", "类型", "洞口宽×高 mm", "数量", "所在楼层")
    for c, text in enumerate(headers):
        prims.append(Prim("text", "A-ANNO-TEXT", text=text,
                          center=((tops[c] + tops[c + 1]) / 2, -row_h * 0.62),
                          height=260))
    for r, row in enumerate(rows, start=1):
        for c, text in enumerate(row):
            prims.append(Prim("text", "A-ANNO-TEXT", text=text,
                              center=((tops[c] + tops[c + 1]) / 2,
                                      -row_h * (r + 0.62)), height=250))
    prims.append(Prim("text", "A-ANNO-TEXT", text="门窗表（方案深度，待审查）",
                      center=(tops[-1] / 2, -height - 600), height=340))

    dxf = DxfAdapter()
    result = dxf.draw_primitives(prims, directory / "A-门窗表.dxf",
                                 "A-ANNO", project.revision)
    if not result.ok:
        raise ValueError(f"门窗表 DXF 审计失败：{result.errors}")
    _sheet_svg(prims, directory / "A-门窗表.svg", title="门窗表 · 方案深度")

    lines = ["# 门窗表（方案深度，待审查）", "",
             "| 编号 | 类型 | 洞口宽×高 mm | 数量 | 所在楼层 |", "|---|---|---|---:|---|"]
    lines += [f"| {c} | {k} | {s} | {n} | {lv} |" for c, k, s, n, lv in rows]
    lines += ["", f"合计 {sum(int(r[3]) for r in rows)} 樘（按模型洞口统计）。", "",
              "- 本表只统计模型里已定位的门窗洞口；数量可直接用于询价，不能直接下料。",
              "- 未含：门扇材质与五金、防火等级、隔声要求、窗料系列、玻璃配置、"
              "过梁与塞缝做法。",
              "- 洞口尺寸以结构预留为准；砌体与混凝土墙的洞口偏差须现场复核。",
              "", SIGNATURE]
    md = directory / "A-门窗表.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return [*result.artifacts, str(directory / "A-门窗表.svg"), str(md)]


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
                # 施工图审图与门窗询价都先看这张表：有多少樘、什么尺寸。
                arts.extend(_opening_schedule(project, directory))
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
                     "- 客房楼各层顶面、地面、灯位建议及代表客房墙面展开已出 CAD/预览；"
                     "材料、防火、隔声和构造未定。",
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
                            artifacts=arts, notes=notes + [
                                "平面与已列立面已读回；其他空间立面及节点尚未完成。"])

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
        if sector == "hospitality":
            from ..interior_surfaces import proposed_lighting
            per_floor = {lid: proposed_lighting(project, lid) for lid in floor_ids}
            data["lighting_proposal"] = {
                "status": "proposed_points_only",
                "by_floor": {lid: len(points) for lid, points in per_floor.items()},
                "total_points": sum(len(points) for points in per_floor.values()),
                "basis": "客房及公区中心与模型床头柜坐标；非灯具采购数/回路图"}
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
        if "lighting_proposal" in data:
            lights = data["lighting_proposal"]
            rows += ["", "## 照明建议点位（非采购数量）", "",
                     f"- 客房楼逐层方案点位合计 {lights['total_points']} 处；"
                     "环境灯与床头任务灯位置来自模型房间及床头柜。",
                     "- 灯具型号、照度、色温、开关回路及消防应急照明"
                     "未做专业设计，不能据此采购或施工。"]
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
