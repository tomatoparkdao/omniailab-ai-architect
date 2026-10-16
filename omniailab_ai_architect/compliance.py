"""Rule and geometry checking (specialist skill 17).

Explicit, listed checks — code / severity / evidence. The output is an
*initial* review, never a permit. Anything touching structure, fire safety,
accessibility, electrical or mechanical load must be signed off by a licensed
professional in the project's jurisdiction, and that statement is part of the
report itself rather than a footnote.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .geometry import furniture_clearance_issues, glazing_ratio, point_along
from .model import Project, Space

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "info": 2}

# Indicative minima. They vary by jurisdiction and by building class; they are
# declared here so they can be replaced rather than silently assumed.
MINIMA: Dict[str, float] = {
    "bedroom_double_m2": 9.0,
    "bedroom_single_m2": 5.0,
    "kitchen_m2": 4.0,
    "bathroom_m2": 2.5,
    "corridor_width_mm": 1000.0,
    "door_clear_mm": 800.0,
    "bath_door_clear_mm": 700.0,
    "ceiling_height_mm": 2400.0,
    "glazing_ratio": 1.0 / 7.0,
    "entry_door_clear_mm": 900.0,
    "bedroom_clearance_mm": 600.0,
    "kitchen_clearance_mm": 900.0,
}


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    refs: List[str] = field(default_factory=list)
    rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "refs": list(self.refs),
            "rule": self.rule,
        }


@dataclass
class ComplianceReport:
    project_id: str
    revision: int
    issues: List[Issue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    disclaimer: str = (
        "本报告为方案阶段自动初审，仅覆盖可量化的几何与配置项。结构安全、消防、"
        "无障碍、电气、暖通、给排水及当地法规符合性，须由具备相应资质的专业人员复核并签署，"
        "不得以本报告替代。"
    )

    @property
    def blockers(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "blocker"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "summary": self.summary,
            "issues": [i.to_dict() for i in sorted(
                self.issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 9)
            )],
            "disclaimer": self.disclaimer,
        }

    def markdown(self) -> str:
        lines = [f"# 设计校核报告 — {self.project_id} (r{self.revision})", ""]
        lines.append(
            f"- 阻断项：{sum(1 for i in self.issues if i.severity == 'blocker')}"
            f"　提示项：{sum(1 for i in self.issues if i.severity == 'warning')}"
            f"　信息项：{sum(1 for i in self.issues if i.severity == 'info')}"
        )
        lines.append("")
        for sev, label in (("blocker", "阻断"), ("warning", "提示"), ("info", "信息")):
            group = [i for i in self.issues if i.severity == sev]
            if not group:
                continue
            lines.append(f"## {label}（{len(group)}）")
            for i in group:
                refs = f"　[{', '.join(i.refs)}]" if i.refs else ""
                lines.append(f"- **{i.code}** {i.message}{refs}")
                if i.rule:
                    lines.append(f"  - 依据/口径：{i.rule}")
            lines.append("")
        lines.append("---")
        lines.append(self.disclaimer)
        return "\n".join(lines)


def check(project: Project, level_id: Optional[str] = None) -> ComplianceReport:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    rep = ComplianceReport(project_id=project.project_id, revision=project.revision)
    spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
    walls = {w.id: w for w in project.by_type("wall")}
    doors = [d for d in project.by_type("door") if d.level_id == lid]
    windows = [w for w in project.by_type("window") if w.level_id == lid]

    # --- G01 无门房间 ------------------------------------------------------
    door_walls = {str(d.geometry.get("host_wall")) for d in doors}
    for s in spaces:
        if s.properties.get("requires_door") is False:
            continue
        touching = _touching_walls(project, s, lid)
        if touching and not (touching & door_walls):
            rep.issues.append(Issue(
                "G01", "blocker",
                f"{s.name or s.use} 没有任何门，房间不可达",
                refs=[s.id],
                rule="每个封闭空间至少应有一处出入口",
            ))

    # --- G02 房间面积下限 --------------------------------------------------
    for s in spaces:
        a = s.area_m2
        use = s.use
        if use == "bedroom":
            key = "bedroom_double_m2" if a >= 7 else "bedroom_single_m2"
            if a < MINIMA[key]:
                rep.issues.append(Issue(
                    "G02", "blocker",
                    f"{s.name or '卧室'} 面积 {a:.2f} m² 低于最小值 {MINIMA[key]} m²",
                    refs=[s.id], rule="住宅卧室最小使用面积（初审口径，须按当地规范复核）",
                ))
        elif use == "kitchen" and a < MINIMA["kitchen_m2"]:
            rep.issues.append(Issue(
                "G02", "blocker",
                f"厨房面积 {a:.2f} m² 低于最小值 {MINIMA['kitchen_m2']} m²",
                refs=[s.id], rule="住宅厨房最小使用面积",
            ))
        elif use == "bathroom" and a < MINIMA["bathroom_m2"]:
            rep.issues.append(Issue(
                "G02", "blocker",
                f"卫生间面积 {a:.2f} m² 低于最小值 {MINIMA['bathroom_m2']} m²",
                refs=[s.id], rule="住宅卫生间最小使用面积",
            ))

    # --- G03 走廊净宽 -----------------------------------------------------
    for s in spaces:
        if s.use != "circulation" or s.properties.get("scheme_key") != "corridor":
            continue
        b = s.bbox()
        width = min(b[2] - b[0], b[3] - b[1])
        if width < MINIMA["corridor_width_mm"]:
            rep.issues.append(Issue(
                "G03", "warning",
                f"走廊净宽 {width:.0f} mm 小于 {MINIMA['corridor_width_mm']:.0f} mm",
                refs=[s.id], rule="住宅套内过道净宽",
            ))

    # --- G04 门洞净宽 -----------------------------------------------------
    for d in doors:
        w = float(d.geometry.get("width_mm", 0))
        kind = str(d.geometry.get("kind") or "")
        to_space = str(d.properties.get("to_space") or "")
        target = next((s for s in spaces if s.id == to_space), None)
        if kind == "entry":
            need = MINIMA["entry_door_clear_mm"]
            label = "入户门"
        elif target is not None and target.use == "bathroom":
            need = MINIMA["bath_door_clear_mm"]
            label = "卫生间门"
        else:
            need = MINIMA["door_clear_mm"]
            label = "房间门"
        if w < need:
            rep.issues.append(Issue(
                "G04", "warning",
                f"{label} {d.id} 净宽 {w:.0f} mm 小于建议值 {need:.0f} mm",
                refs=[d.id], rule="门洞净宽",
            ))

    # --- G05 自然采光（窗地比） -------------------------------------------
    total_floor = sum(s.area_m2 for s in spaces)
    glaz = sum(
        float(w.geometry.get("width_mm", 0)) * float(w.geometry.get("height_mm", 0)) / 1e6
        for w in windows
    )
    ratio = glaz / total_floor if total_floor else 0.0
    if ratio < MINIMA["glazing_ratio"]:
        rep.issues.append(Issue(
            "G05", "blocker",
            f"整体窗地比 {ratio:.3f} ({ratio*7:.2f}/7) 低于 1/7，自然采光不足",
            refs=[s.id for s in spaces[:6]],
            rule="住宅卧室、起居室、厨房的窗地面积比不宜小于 1/7（初审口径）",
        ))
    served = {w.properties.get("space_id") for w in windows if w.properties.get("space_id")}
    for s in spaces:
        if s.properties.get("daylight_required") and s.id not in served:
            rep.issues.append(Issue(
                "G05b", "warning",
                f"{s.name or s.use} 要求自然采光但未分配到外窗",
                refs=[s.id], rule="主要使用房间应有直接采光",
            ))

    # --- G06 层高 ---------------------------------------------------------
    heights = {l.id: l.height_mm for l in project.levels}
    h = heights.get(lid, 0.0)
    if h and h < MINIMA["ceiling_height_mm"]:
        rep.issues.append(Issue(
            "G06", "blocker", f"层高 {h:.0f} mm 低于 {MINIMA['ceiling_height_mm']:.0f} mm",
            refs=[lid], rule="住宅室内净高",
        ))

    # --- G07 家具净距 / 通道 ----------------------------------------------
    for msg in furniture_clearance_issues(project, min_clearance_mm=MINIMA["bedroom_clearance_mm"]):
        rep.issues.append(Issue("G07", "warning", f"家具间距偏小：{msg}",
                                rule="主要通道净宽不宜小于 600 mm"))

    # --- G08 卫生间不得直对厨房 -------------------------------------------
    for s in spaces:
        if s.use != "bathroom":
            continue
        for other in spaces:
            if other.id == s.id:
                continue
            if other.use in ("kitchen", "dining") and _shared_boundary(s, other):
                rep.issues.append(Issue(
                    "G08", "warning",
                    f"{s.name or '卫生间'} 与 {other.name or other.use} 直接相邻，需确认门位与隔墙做法",
                    refs=[s.id, other.id], rule="卫生间不宜直接开向厨房、餐厅",
                ))

    # --- G09 不确定构件（结构/现场信息） ----------------------------------
    uncertain = [e.id for e in project.elements if e.uncertain]
    if uncertain:
        rep.issues.append(Issue(
            "G09", "blocker",
            f"{len(uncertain)} 个构件为推断所得（结构墙/门窗），须现场核对后方可用于施工图",
            refs=uncertain[:12],
            rule="梁柱与承重墙不得依据图纸推定；须现场探测或由原设计单位确认",
        ))

    # --- G10 效果图不得作为尺寸依据 ---------------------------------------
    for a in project.artifacts:
        if a.type in ("render", "image", "visual") and a.depends_on and a.status == "validated":
            rep.issues.append(Issue(
                "G10", "info",
                f"表现类产物 {a.id} 已校验通过——注意其不构成尺寸依据",
                refs=[a.id], rule="生成式图像不得反推几何",
            ))

    # --- G11 悬空/重叠空间检查 --------------------------------------------
    overlaps = _space_overlaps(spaces)
    for a, b, area in overlaps:
        rep.issues.append(Issue(
            "G11", "blocker",
            f"{a.name or a.id} 与 {b.name or b.id} 重叠 {area:.2f} m²",
            refs=[a.id, b.id], rule="同一楼层空间不应重叠",
        ))

    rep.summary = {
        "level_id": lid,
        "spaces": len(spaces),
        "doors": len(doors),
        "windows": len(windows),
        "floor_area_m2": round(total_floor, 2),
        "glazing_ratio": round(ratio, 4),
        "blockers": sum(1 for i in rep.issues if i.severity == "blocker"),
        "warnings": sum(1 for i in rep.issues if i.severity == "warning"),
        "infos": sum(1 for i in rep.issues if i.severity == "info"),
        "pass": not any(i.severity == "blocker" for i in rep.issues),
    }
    return rep


def _touching_walls(project: Project, space: Space, lid: str) -> set[str]:
    from .geometry import polygon_to_shapely, distance_to_boundary

    poly = polygon_to_shapely(space.boundary_mm2d)
    hits: set[str] = set()
    for w in project.by_type("wall"):
        if w.level_id != lid:
            continue
        axis = w.wall_axis()
        if not axis:
            continue
        (x1, y1), (x2, y2) = axis
        mp = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        if poly is not None and distance_to_boundary(poly, mp) <= 5.0:
            hits.add(w.id)
        else:
            # fall back: either endpoint near the boundary
            for pt in ((x1, y1), (x2, y2)):
                if poly is not None and distance_to_boundary(poly, pt) <= 30.0:
                    hits.add(w.id)
                    break
    return hits


def _shared_boundary(a: Space, b: Space, tol: float = 80.0) -> bool:
    from .geometry import polygon_to_shapely

    pa = polygon_to_shapely(a.boundary_mm2d)
    pb = polygon_to_shapely(b.boundary_mm2d)
    if pa is None or pb is None:
        return False
    return pa.distance(pb) <= tol


def _space_overlaps(spaces: Sequence[Space]) -> List[tuple]:
    from .geometry import polygon_to_shapely

    out = []
    polys = [(s, polygon_to_shapely(s.boundary_mm2d)) for s in spaces]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            sa, pa = polys[i]
            sb, pb = polys[j]
            if pa is None or pb is None:
                continue
            inter = pa.intersection(pb)
            if not inter.is_empty and inter.area > 0.25e6:  # > 0.25 m²
                out.append((sa, sb, inter.area / 1e6))
    return out
