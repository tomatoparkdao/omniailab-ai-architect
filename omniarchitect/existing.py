"""原始条件导入 —— 把业主给的实测资料变成统一模型里的几何。

S3 的平面算法不接受"只有文字"的项目：没有轮廓就排不出可核对的房间。
本模块只做一件事：把**业主/测绘方提供**的轮廓与墙读进 `project.spaces` /
`project.elements`，并把来源写进 `project.meta["existing_conditions"]`。

它不是新的阶段、门禁或空间模型，也不产生任何设计判断：

* 只认已量测的数据；缺尺寸的墙标 `uncertain`，不替客户补数；
* 不生成轮廓 —— 没有坐标就是没有，绝不按面积反算一个假轮廓；
* 原有几何不会被覆盖：已有 envelope 时直接拒绝，要走变更流程。

文件格式（`omniailab-existing-conditions/1`）::

    {
      "format": "omniailab-existing-conditions/1",
      "source": "client_survey",
      "surveyed_by": "业主提供的原始户型图 + 现场复核",
      "unit": "mm",
      "level": {"id": "L1", "name": "一层", "height_mm": 2900},
      "envelope": [[0,0],[13200,0],[13200,8200],[0,8200]],
      "walls": [
        {"start": [0,0], "end": [13200,0], "thickness_mm": 240,
         "kind": "exterior", "uncertain": false, "note": ""}
      ]
    }

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .model import Element, Level, Project, Space

FORMAT = "omniailab-existing-conditions/1"
FILE_NAME = "existing-conditions.json"


class ConditionsError(ValueError):
    """资料本身不成立（缺坐标、单位不对、已有几何）。"""


def _polygon_area(points: Sequence[Sequence[float]]) -> float:
    s = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = float(points[i][0]), float(points[i][1])
        x2, y2 = float(points[(i + 1) % n][0]), float(points[(i + 1) % n][1])
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def _pt(value: Any, where: str) -> Tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise ConditionsError(f"{where}：坐标必须是 [x, y]")
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError) as exc:
        raise ConditionsError(f"{where}：坐标必须是数字") from exc


def validate(data: Dict[str, Any]) -> Dict[str, Any]:
    """检查资料能不能当几何用。返回规范化后的副本。"""
    if not isinstance(data, dict):
        raise ConditionsError("资料必须是 JSON 对象")
    fmt = str(data.get("format") or "")
    if fmt and fmt != FORMAT:
        raise ConditionsError(f"格式不认识：{fmt}（期望 {FORMAT}）")
    if str(data.get("unit") or "mm") != "mm":
        raise ConditionsError("只接受 mm：单位不对会让所有尺寸差 1000 倍")

    env = data.get("envelope") or []
    if len(env) < 3:
        raise ConditionsError("envelope 至少要三个点：没有轮廓就排不出平面")
    pts = [_pt(p, f"envelope[{i}]") for i, p in enumerate(env)]
    if _polygon_area(pts) < 1e6:
        raise ConditionsError("轮廓面积小于 1 m²，坐标可能写错了")

    walls = []
    for i, w in enumerate(data.get("walls") or []):
        if not isinstance(w, dict):
            raise ConditionsError(f"walls[{i}] 必须是对象")
        a = _pt(w.get("start"), f"walls[{i}].start")
        b = _pt(w.get("end"), f"walls[{i}].end")
        if abs(a[0] - b[0]) < 1 and abs(a[1] - b[1]) < 1:
            raise ConditionsError(f"walls[{i}] 起终点重合")
        walls.append({
            "start": a, "end": b,
            "thickness_mm": float(w.get("thickness_mm") or 120.0),
            "height_mm": float(w.get("height_mm") or (data.get("level") or {})
                               .get("height_mm") or 2800.0),
            "kind": str(w.get("kind") or "partition"),
            "uncertain": bool(w.get("uncertain")),
            "note": str(w.get("note") or ""),
        })

    level = data.get("level") or {}
    return {
        "format": FORMAT,
        "source": str(data.get("source") or "client_survey"),
        "surveyed_by": str(data.get("surveyed_by") or ""),
        "unit": "mm",
        "level": {
            "id": str(level.get("id") or "L1"),
            "name": str(level.get("name") or "一层"),
            "elevation_mm": float(level.get("elevation_mm") or 0.0),
            "height_mm": float(level.get("height_mm") or 2900.0),
        },
        "envelope": pts,
        "walls": walls,
        "declared_area_m2": data.get("declared_area_m2"),
        "notes": list(data.get("notes") or []),
    }


def has_geometry(project: Project) -> bool:
    return bool([s for s in project.spaces if s.use == "envelope"]) or \
        bool(project.by_type("wall"))


def area_m2(data: Dict[str, Any]) -> float:
    return round(_polygon_area(data["envelope"]) / 1e6, 2)


def apply(project: Project, data: Dict[str, Any], *, replace: bool = False) -> Dict[str, Any]:
    """把资料写进统一模型。已有几何时拒绝，除非显式 replace。"""
    clean = validate(data)
    if has_geometry(project) and not replace:
        raise ConditionsError(
            "项目已有几何；替换轮廓属于几何变更，请走 `omniarchitect change` 影响分析，"
            "不要直接导入")
    if replace:
        project.spaces = [s for s in project.spaces if s.use != "envelope"]
        project.elements = [e for e in project.elements if e.type != "wall"]

    lv = clean["level"]
    if not any(x.id == lv["id"] for x in project.levels):
        project.levels.append(Level(id=lv["id"], name=lv["name"],
                                    elevation_mm=lv["elevation_mm"],
                                    height_mm=lv["height_mm"]))

    project.spaces.append(Space(
        id="S-ENV",
        level_id=lv["id"],
        name="套内轮廓",
        use="envelope",
        boundary_mm2d=[list(p) for p in clean["envelope"]],
        source="existing_conditions",
        confidence=1.0 if not any(w["uncertain"] for w in clean["walls"]) else 0.8,
        properties={"note": clean["surveyed_by"] or clean["source"],
                    "requires_door": False},
    ))

    for i, w in enumerate(clean["walls"], 1):
        kind = w["kind"]
        prefix = {"exterior": "W-EXT", "structural": "W-STR",
                  "partition": "W-PAR"}.get(kind, "W-PAR")
        project.elements.append(Element(
            id=f"{prefix}-{i:03d}",
            type="wall",
            level_id=lv["id"],
            geometry={
                "start": [round(w["start"][0], 1), round(w["start"][1], 1)],
                "end": [round(w["end"][0], 1), round(w["end"][1], 1)],
                "thickness_mm": w["thickness_mm"],
                "height_mm": w["height_mm"],
                "kind": kind,
            },
            source="existing_conditions",
            confidence=0.6 if w["uncertain"] else 0.95,
            uncertain=w["uncertain"],
            properties={"note": w["note"]} if w["note"] else {},
        ))

    summary = {
        "source": clean["source"],
        "surveyed_by": clean["surveyed_by"],
        "level_id": lv["id"],
        "envelope_area_m2": area_m2(clean),
        "walls": len(clean["walls"]),
        "uncertain_walls": sum(1 for w in clean["walls"] if w["uncertain"]),
        "declared_area_m2": clean["declared_area_m2"],
    }
    project.meta["existing_conditions"] = summary
    project.sources.append({"kind": "existing_conditions", "source": clean["source"],
                            "note": clean["surveyed_by"], **summary})
    return summary


def load(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if p.is_dir():
        p = p / FILE_NAME
    if not p.exists():
        raise ConditionsError(f"找不到资料文件：{p}")
    return json.loads(p.read_text(encoding="utf-8"))


def import_file(project: Project, path: str | Path, *, replace: bool = False) -> Dict[str, Any]:
    return apply(project, load(path), replace=replace)


def report(project: Project) -> List[str]:
    """给 CLI / 阶段说明用的一行人话。"""
    got = (project.meta or {}).get("existing_conditions")
    if not got:
        return ["未导入原始条件：S3 需要轮廓与墙才能排平面"]
    lines = [
        f"原始条件：{got.get('envelope_area_m2')} m² 轮廓 / {got.get('walls')} 道墙"
        f"（来源 {got.get('source')}）"
    ]
    if got.get("uncertain_walls"):
        lines.append(f"其中 {got['uncertain_walls']} 道墙尺寸不确定，已标 uncertain，须现场复核")
    return lines


def discover(project_dir: str | Path) -> Path | None:
    d = Path(project_dir)
    p = d / FILE_NAME
    return p if p.exists() else None


__all__ = ["FILE_NAME", "FORMAT", "ConditionsError", "apply", "area_m2", "discover",
           "has_geometry", "import_file", "load", "report", "validate"]
