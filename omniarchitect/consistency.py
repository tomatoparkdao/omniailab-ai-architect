"""Consistency checks across CAD, the visual brief and any exported 3D model.

The failure this prevents: a render, a SketchUp model and a CAD sheet that all
look plausible on their own and disagree with each other. Design review then
argues about pictures instead of about the building.

What can be checked mechanically is checked mechanically:

* the brief's recorded facts are recomputed from the model — a brief that has
  drifted from the model is reported as stale, not silently reused;
* an exported OBJ is measured and compared with the model's own extents, so
  "the model is 25× too small" or "the massing is rotated" shows up as a number.

What cannot be judged by code — whether a rendered image respects the plan — is
listed as a human check with the specific items to look at. It is never marked
as passed.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import visual_brief

#: Tolerance when comparing an exported mesh against the model, in millimetres.
TOL_MM = 50.0


def _model_extent(project: Any, discipline: str) -> Optional[Tuple[float, float, float, float]]:
    if discipline == "landscape":
        spaces = [s for s in project.spaces_on("L-SITE")
                  if s.use in visual_brief.LANDSCAPE_USES and len(s.boundary_mm2d) >= 3]
    else:
        spaces = [s for s in project.spaces
                  if s.use not in visual_brief.SITE_USES and len(s.boundary_mm2d) >= 3]
    pts = [p for s in spaces for p in s.boundary_mm2d]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def obj_extent(path: str | Path) -> Optional[Tuple[float, float, float, float]]:
    """Read an OBJ and return its XY bounding box in millimetres."""
    p = Path(path)
    if not p.is_file():
        return None
    xs: List[float] = []
    ys: List[float] = []
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("v "):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                xs.append(float(parts[1]))
                ys.append(float(parts[2]))
            except ValueError:
                continue
    except OSError:
        return None
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def check_brief(project: Any, pkg: Dict[str, Any],
                level_id: Optional[str] = None) -> Dict[str, Any]:
    """Recompute the brief's facts and compare. A drifted brief is caught here."""
    recorded = pkg.get("geometry") or {}
    current = visual_brief.geometry_facts(project, level_id, pkg.get("discipline", "interior"))
    diffs: List[str] = []
    for key in ("rooms", "doors", "windows", "levels", "storey_height_m",
                "envelope_m", "wall_thickness_mm"):
        a, b = recorded.get(key), current.get(key)
        if key == "storey_height_m":
            if a is not None and b is not None and abs(float(a) - float(b)) > 0.01:
                diffs.append(f"{key}: 任务书 {a} ≠ 模型 {b}")
            continue
        if key == "envelope_m":
            if a and b and (abs(a[0] - b[0]) > 0.05 or abs(a[1] - b[1]) > 0.05):
                diffs.append(f"外轮廓：任务书 {a} ≠ 模型 {b}")
            continue
        if a != b:
            diffs.append(f"{key}: 任务书 {a} ≠ 模型 {b}")
    return {"ok": not diffs, "stale": bool(diffs), "diffs": diffs,
            "recorded": recorded, "current": current}


def check_mesh(project: Any, obj_path: str | Path,
               discipline: str = "interior") -> Dict[str, Any]:
    """Compare an exported mesh footprint with the model footprint."""
    model = _model_extent(project, discipline)
    mesh = obj_extent(obj_path)
    if model is None or mesh is None:
        return {"ok": False, "skipped": True,
                "reason": "缺少模型或网格几何，无法比对"}
    mw, md = model[2] - model[0], model[3] - model[1]
    ow, od = mesh[2] - mesh[0], mesh[3] - mesh[1]
    # An OBJ may be exported in metres (Blender/SketchUp exporters do this).
    # Accept a 1000× mismatch as a unit issue and say so, rather than declaring
    # the model wrong when it is only written in different units.
    scale = 1.0
    if mw > 0 and 1e-5 < (ow / mw) < 0.05:
        scale = 1000.0
        ow, od = ow * scale, od * scale
    dw, dd = abs(ow - mw), abs(od - md)
    ok = dw <= TOL_MM and dd <= TOL_MM
    return {"ok": ok, "skipped": False, "scale_applied": scale,
            "model_mm": [round(mw, 1), round(md, 1)],
            "mesh_mm": [round(ow, 1), round(od, 1)],
            "delta_mm": [round(dw, 1), round(dd, 1)],
            "tolerance_mm": TOL_MM,
            "reason": "" if ok else "网格外轮廓与模型不符：检查单位、旋转与缩放"}


def human_checks(brief_pkg: Dict[str, Any]) -> List[Dict[str, str]]:
    """The part a program cannot settle: does the picture respect the plan."""
    out: List[Dict[str, str]] = []
    for shot in brief_pkg.get("shots") or []:
        out.append({
            "shot": shot.get("id", ""),
            "label": shot.get("label", ""),
            "status": "pending_human" if not shot.get("rendered") else "pending_human",
            "items": "；".join(shot.get("checks") or []),
            "note": "图与平面是否一致须人工比对；程序只能保证提示词与几何同源",
        })
    return out


def report(project: Any, brief_pkg: Dict[str, Any], *, obj_path: str | Path | None = None,
           level_id: Optional[str] = None) -> Dict[str, Any]:
    """One verdict combining the mechanical checks and the human queue."""
    brief = check_brief(project, brief_pkg, level_id)
    mesh = (check_mesh(project, obj_path, brief_pkg.get("discipline", "interior"))
            if obj_path else {"ok": False, "skipped": True, "reason": "未提供导出网格"})
    checks = human_checks(brief_pkg)
    blocking: List[str] = []
    if brief["stale"]:
        blocking.append("视觉任务书已与模型不同步：" + "；".join(brief["diffs"]))
    if not mesh.get("skipped") and not mesh["ok"]:
        blocking.append("三维网格与模型不符：" + mesh.get("reason", ""))
    return {
        "brief_fresh": brief["ok"],
        "brief_diffs": brief["diffs"],
        "mesh_agrees": None if mesh.get("skipped") else mesh["ok"],
        "mesh": mesh,
        "human_checks": checks,
        "blocking": blocking,
        "verdict": ("blocked" if blocking else "ok_for_review"),
        "note": "程序能保证几何同源与网格尺寸；图面是否忠于平面须设计人员逐张比对",
    }


__all__ = ["TOL_MM", "obj_extent", "check_brief", "check_mesh", "human_checks", "report"]
