"""可校核的参考图 —— 交给图像模型的是"看得见的图纸"，不是 DXF 路径。

为什么必须这一步
----------------
DXF 是 CAD 交换格式，不是图像模型的输入。把 `.dxf` 写进 `references` 只是把
一个路径字符串塞进 JSON，既不能证明模型收到了什么，也不能证明它看到的是哪一版
几何。所以图纸派生的参考图必须由**本项目的矢量图元**重新输出成 SVG/PNG：

* 同一份 `build_primitives()` 同时喂 DXF、SVG 与 PNG，三者的墙、门、窗、房间
  位置不可能互相矛盾；
* 尺寸与房间标注是**矢量文字**，由我们写、可核对，不由图像模型编；
* 图像模型只负责着色与质感，**不许改写几何**——这一点写进提示词与负向约束。

清单里同时给出"这份参考图有什么、缺什么"。缺立面就写缺立面，不拿平面图冒充。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Project

#: 参考图比例：像素/毫米。0.1 ≈ 图纸 1:10 的屏幕观感，13m 户型约 1300px 宽
PX_PER_MM = 0.1

#: AI 输入格式的事实：DXF 不是图像模型输入
AI_INPUT_FORMATS = ("svg", "png")
NON_INPUT_FORMATS = ("dxf", "dwg")

LAYER_STYLE: Dict[str, Dict[str, str]] = {
    "A-WALL": {"stroke": "#1c1c1e", "width": "1.6"},
    "A-WALL-PART": {"stroke": "#5a5a60", "width": "1.0"},
    "A-UNCERTAIN": {"stroke": "#c82828", "width": "1.0", "dash": "6 3"},
    "A-DOOR": {"stroke": "#966428", "width": "1.0"},
    "A-GLAZ": {"stroke": "#2878be", "width": "1.0"},
    "A-FURN": {"stroke": "#78787e", "width": "0.8", "fill": "#d6d6d8"},
    "A-AREA": {"stroke": "#c8cdd2", "width": "0.6", "fill": "#ebeef0", "dash": "8 4"},
    "A-ANNO-DIMS": {"stroke": "#2b7a3d", "width": "0.8"},
    "A-ANNO-TEXT": {"stroke": "#2b7a3d", "width": "0.6"},
    "G-ANNO-TTLB": {"stroke": "#1c1c1e", "width": "0.8"},
}
DEFAULT_STYLE = {"stroke": "#333333", "width": "0.8"}
DESIGN_CRITERIA_NOTE = "参考图由本项目矢量图元直接输出；尺寸与标注可核对。"


class ReferenceError_(RuntimeError):
    """参考图做不出来时抛这个——不要用半成品冒充。"""


def _bounds(prims: Sequence[Any]) -> Tuple[float, float, float, float]:
    xs: List[float] = []
    ys: List[float] = []
    for pr in prims:
        for p in pr.points:
            xs.append(p[0])
            ys.append(p[1])
        if pr.kind in ("circle", "arc"):
            xs.append(pr.center[0])
            ys.append(pr.center[1])
        if pr.kind == "text":
            xs.append(pr.center[0])
            ys.append(pr.center[1])
    if not xs:
        raise ReferenceError_("没有可输出的图元：平面参考图需要空间与墙体")
    pad = 900.0
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def write_svg(prims: Sequence[Any], out_path: str | Path, *,
              title: str = "已确认平面（参考图）",
              footer: str = "") -> str:
    """把图元写成 SVG。文字是真文字，尺寸是真数字。"""
    x0, y0, x1, y1 = _bounds(prims)
    scale = PX_PER_MM
    w = max(360.0, (x1 - x0) * scale)
    h = max(280.0, (y1 - y0) * scale) + 34.0

    def tx(p: Tuple[float, float]) -> Tuple[float, float]:
        return ((p[0] - x0) * scale, (y1 - p[1]) * scale)

    root = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": f"{w:.0f}", "height": f"{h:.0f}",
        "viewBox": f"0 0 {w:.1f} {h:.1f}",
    })
    ET.SubElement(root, "rect", {"x": "0", "y": "0", "width": f"{w:.0f}",
                                 "height": f"{h:.0f}", "fill": "#fafaf8"})
    g = ET.SubElement(root, "g", {"stroke-linecap": "round",
                                  "stroke-linejoin": "round"})

    # 先填充（空间与家具），再描边，最后文字
    for pr in prims:
        style = LAYER_STYLE.get(pr.layer, DEFAULT_STYLE)
        if pr.kind == "polyline" and pr.closed and style.get("fill"):
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (tx(p) for p in pr.points))
            ET.SubElement(g, "polygon", {"points": pts, "fill": style["fill"],
                                         "stroke": "none", "opacity": "0.55"})

    for pr in prims:
        style = LAYER_STYLE.get(pr.layer, DEFAULT_STYLE)
        common = {"stroke": style["stroke"], "stroke-width": style["width"], "fill": "none"}
        if style.get("dash"):
            common["stroke-dasharray"] = style["dash"]
        if pr.kind == "polyline" and pr.points:
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (tx(p) for p in pr.points))
            tag = "polygon" if pr.closed else "polyline"
            ET.SubElement(g, tag, {"points": pts, **common})
        elif pr.kind == "line" and len(pr.points) >= 2:
            (ax, ay), (bx, by) = tx(pr.points[0]), tx(pr.points[1])
            ET.SubElement(g, "line", {"x1": f"{ax:.1f}", "y1": f"{ay:.1f}",
                                      "x2": f"{bx:.1f}", "y2": f"{by:.1f}", **common})
        elif pr.kind == "circle":
            cx, cy = tx(pr.center)
            ET.SubElement(g, "circle", {"cx": f"{cx:.1f}", "cy": f"{cy:.1f}",
                                        "r": f"{pr.radius * scale:.1f}", **common})
        elif pr.kind == "arc":
            cx, cy = tx(pr.center)
            r = pr.radius * scale
            start = pr.start_angle
            end = pr.end_angle
            a0 = (start) * 3.141592653589793 / 180.0
            a1 = (end) * 3.141592653589793 / 180.0
            large = 1 if abs(end - start) > 180 else 0
            sx, sy = cx + r * __import__("math").cos(a0), cy - r * __import__("math").sin(a0)
            ex, ey = cx + r * __import__("math").cos(a1), cy - r * __import__("math").sin(a1)
            ET.SubElement(g, "path", {
                "d": f"M {sx:.1f} {sy:.1f} A {r:.1f} {r:.1f} 0 {large} 0 {ex:.1f} {ey:.1f}",
                **common})

    for pr in prims:
        if pr.kind != "text" or not pr.text:
            continue
        style = LAYER_STYLE.get(pr.layer, DEFAULT_STYLE)
        cx, cy = tx(pr.center)
        ET.SubElement(g, "text", {
            "x": f"{cx:.1f}", "y": f"{cy:.1f}",
            "font-family": "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif",
            "font-size": f"{max(6.0, pr.height * scale):.1f}",
            "fill": style["stroke"], "text-anchor": "middle",
            "dominant-baseline": "middle",
        }).text = pr.text

    ET.SubElement(root, "text", {
        "x": "8", "y": f"{h - 8:.0f}", "font-family": "sans-serif",
        "font-size": "9", "fill": "#8a8a90",
    }).text = footer or f"{title} · {DESIGN_CRITERIA_NOTE} · 非权威成果"

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
    return str(p)


def _local_png(project: Project, out_path: Path, *, level_id: Optional[str],
               title: str, scheme: str) -> Tuple[Optional[str], str]:
    """尽力输出 PNG；Pillow 不可用就退回只给 SVG，并说明原因。"""
    try:
        from .providers.local import LocalDeterministicProvider

        prov = LocalDeterministicProvider()
        cap = prov.probe()
        if not cap.usable:
            return None, "本机未安装 Pillow：只输出 SVG（矢量，尺寸可核对）"
        return prov.plan_png(project, out_path, level_id=level_id,
                             title=title, scheme=scheme), ""
    except Exception as exc:                       # noqa: BLE001 - 降级要带原因
        return None, f"PNG 输出失败（{type(exc).__name__}: {exc}）：只输出 SVG"


def build_reference(project: Project, out_dir: str | Path, *,
                    level_id: Optional[str] = None, scheme: str = "",
                    title: str = "已确认平面（参考图）") -> Dict[str, Any]:
    """输出一份可上传的参考图，并如实列出它包含/缺少什么。"""
    from .adapters.drawing import build_primitives

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    prims = build_primitives(project, level_id=lid, include_furniture=True,
                             include_dims=True, include_titleblock=False,
                             title=title, scheme=scheme, depth="presentation")

    svg_path = out / f"reference-plan-{scheme or 'A'}.svg"
    write_svg(prims, svg_path, title=title,
              footer=f"{project.name or project.project_id} · r{project.revision} · "
                     f"{title} {scheme} · 非权威成果")

    png_path, png_note = _local_png(project, out / f"reference-plan-{scheme or 'A'}.png",
                                    level_id=lid, title=title, scheme=scheme)

    dim_texts = [p.text for p in prims if p.kind == "text" and p.layer == "A-ANNO-DIMS"]
    room_texts = [p.text for p in prims if p.kind == "text" and p.layer == "A-ANNO-TEXT"]
    spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
    walls = [w for w in project.by_type("wall") if w.level_id == lid]
    doors = [d for d in project.by_type("door") if d.level_id == lid]
    windows = [w for w in project.by_type("window") if w.level_id == lid]
    height = next((float(l.height_mm) for l in project.levels if l.id == lid), 0.0)

    files = [str(svg_path)] + ([str(png_path)] if png_path else [])
    sizes = {Path(f).name: Path(f).stat().st_size for f in files if Path(f).exists()}

    return {
        "level_id": lid,
        "scheme": scheme,
        "files": files,
        "svg": str(svg_path),
        "png": str(png_path or ""),
        "png_note": png_note,
        "sizes": sizes,
        # 清单：这份参考图有什么
        "has_plan_geometry": bool(spaces and walls),
        "has_openings": bool(doors or windows),
        "has_furniture": any(p.layer == "A-FURN" for p in prims),
        "has_dimensions": bool(dim_texts),
        "has_room_labels": bool(room_texts),
        "has_level_height": height > 0,
        "has_elevation": False,        # 尚无立面适配器产出
        "has_perspective": False,      # 无 AI 生成即无透视
        "counts": {
            "spaces": len(spaces), "walls": len(walls),
            "doors": len(doors), "windows": len(windows),
            "dimension_texts": len(dim_texts), "room_texts": len(room_texts),
            "primitives": len(prims),
        },
        "dimension_samples": dim_texts[:6],
        # 事实：图像模型吃的是什么
        "ai_input": {
            "accepted": list(AI_INPUT_FORMATS),
            "not_accepted": list(NON_INPUT_FORMATS),
            "note": "DXF 是 CAD 交换格式，不作为图像模型输入；本参考图由矢量图元输出。",
        },
        "vector_authoritative": True,
        "note": ("参考图来自本项目矢量图元（与 DXF 同一份 primitives）："
                 "墙、门窗、房间位置可核对，尺寸标注为真数字。"),
    }


def verify_files(reference: Dict[str, Any], *, min_bytes: int = 2048) -> Dict[str, Any]:
    """逐个核对参考文件是否真的存在、是否像个真文件。"""
    rows: List[Dict[str, Any]] = []
    for f in reference.get("files") or []:
        p = Path(f)
        ok = p.exists() and p.stat().st_size >= (min_bytes if p.suffix.lower() != ".svg" else 512)
        rows.append({"path": str(p), "exists": p.exists(),
                     "bytes": p.stat().st_size if p.exists() else 0, "ok": ok,
                     "format": p.suffix.lower().lstrip(".")})
    return {"files": rows, "all_ok": all(r["ok"] for r in rows) and bool(rows)}


def write_manifest(reference: Dict[str, Any], out_dir: str | Path) -> str:
    p = Path(out_dir) / "reference-manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reference, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    return str(p)


__all__ = ["build_reference", "write_svg", "verify_files", "write_manifest",
           "ReferenceError_", "AI_INPUT_FORMATS", "NON_INPUT_FORMATS", "PX_PER_MM"]
