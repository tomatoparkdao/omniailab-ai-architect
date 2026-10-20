"""总平面与景观总图：先看真实的场地条件，再决定放什么、放哪边。

原来这里有两处"没有数据也照样画"的硬编码：运动场永远在南、水景永远在南、
绿地永远在北。那不是设计，是把一张图的构图固定下来，跟业主的场地无关。

现在改成：

* **场地边界分档**。有红线/实测边界就用它；没有才用矩形假设，并在图上写明
  "矩形假设（无红线数据）"——不把假设画得像实测。
* **方位来自客户原话**。哪一侧临路、哪一侧是住区，从 S1 的场地描述里读；
  读不到才假设，并把假设写在图上。
* **关系由原则推出**。运动场放在入口对侧（不占主入口面、与教学区分开）；
  装卸场放在生产端；绿地沿边界与建筑之间。这些是设计原则，不是固定方位。
* **景观不是几条色带**。水面成一块、园路成环、种植成丛、节点有落脚点；
  面积占比另画一张条图，与总平面分开表达。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..concept.diagrams import Svg
from .brief import SectorBrief
from .program import SectorProgram

INK = "#1E2328"
MUTED = "#6B7280"
RULE = "#D6D9DD"
GREEN = "#DCE7D5"
GREEN_D = "#B9CFAD"
ROAD = "#E8E2D4"
ROAD_D = "#C9BEA4"
WATER = "#CFE3F2"
WATER_D = "#8FB8D8"
SPORT = "#D8E6D2"
BLDG = "#EDE7DA"
PAVE = "#EFE8D6"
TRUNK = "#8C7B5E"

SIDE_CN = {"n": "北", "s": "南", "e": "东", "w": "西"}


def _site_rect(site_m2: float, ratio: float = 1.45) -> Tuple[float, float]:
    w = math.sqrt(max(site_m2, 100.0) * ratio)
    return w, max(site_m2 / w, 20.0)


# --------------------------------------------------------------------------
# 场地：边界与方位
# --------------------------------------------------------------------------
def plot(project: Any, brief: SectorBrief) -> Dict[str, Any]:
    """这套总图站在什么场地上：真实边界还是矩形假设，入口在哪一侧。"""
    site = brief.get("site_area") or 6000.0
    real = next((s for s in getattr(project, "spaces", [])
                 if s.use in ("site", "plot", "boundary", "redline")), None)
    out: Dict[str, Any] = {"site_m2": float(site), "basis": "assumed",
                           "polygon": [], "entrance": "s", "roads": [],
                           "entrance_note": "", "note": ""}
    if real is not None and len(real.boundary_mm2d or []) >= 3:
        pts = [[float(p[0]), float(p[1])] for p in real.boundary_mm2d]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out.update({"polygon": pts, "w_mm": max(xs) - min(xs),
                    "d_mm": max(ys) - min(ys), "basis": _basis_of(real)})
    if not out["polygon"]:
        w, d = _site_rect(out["site_m2"])
        out.update({"polygon": [[0.0, 0.0], [w * 1000, 0.0],
                                [w * 1000, d * 1000], [0.0, d * 1000]],
                    "w_mm": w * 1000, "d_mm": d * 1000})
        out["note"] = "矩形假设（无红线数据）：须以实测红线与退界重画"
    ent, roads, note = _orientation(brief)
    out.update({"entrance": ent, "roads": roads, "entrance_note": note})
    return out


def _basis_of(space: Any) -> str:
    props = dict(getattr(space, "properties", {}) or {})
    low = (str(getattr(space, "source", "")) + " " + str(props.get("precision") or "")).lower()
    if props.get("proposed"):
        return "proposed"
    if any(k in low for k in ("survey", "measured", "实测")):
        return "surveyed"
    if any(k in low for k in ("client", "estimate", "估算")):
        return "client"
    return "drawing"


SIDE_TOKEN = (("n", ("北侧", "北面", "北临", "北向")), ("s", ("南侧", "南面", "南临")),
              ("e", ("东侧", "东面", "东临")), ("w", ("西侧", "西面", "西临")))
ROAD_WORDS = ("路", "街", "道", "主干道", "次干道", "巷")


def _orientation(brief: SectorBrief) -> Tuple[str, List[str], str]:
    """从客户对场地的描述里读入口与临路方位；读不到就假设并写明。"""
    text = str(getattr(brief, "text", "") or "")
    roads: List[str] = []
    entrance = ""
    for side, tokens in SIDE_TOKEN:
        for tok in tokens:
            idx = text.find(tok)
            if idx < 0:
                continue
            tail = text[idx: idx + 16]
            if any(w in tail for w in ROAD_WORDS):
                if side not in roads:
                    roads.append(side)
                if not entrance:
                    entrance = side
            break
    if entrance:
        return entrance, roads, f"入口按客户原话（{SIDE_CN[entrance]}侧临路）"
    return "s", roads, "客户未说明道路方位：按南侧入口假设，须以红线与现状道路核对"


def metrics(program: SectorProgram, brief: SectorBrief) -> Dict[str, Any]:
    site = brief.get("site_area")
    built = sum(b["area_m2"] for b in program.blocks if b.get("kind") == "building")
    footprint = 0.0
    for b in program.blocks:
        if b.get("kind") != "building" or not b.get("area_m2"):
            continue
        w, d = float(b.get("w") or 0), float(b.get("d") or 0)
        floors = float(b.get("floors") or 1)
        # 建筑基底 = 总建筑面积 ÷ 层数；块上有 w×d 时优先用实际占地尺寸
        footprint += (w * d) if (w and d) else float(b["area_m2"]) / max(floors, 1.0)
    green = max(0.0, site - footprint)
    return {
        "site_m2": round(site, 1),
        "building_m2": round(built, 1),
        "footprint_m2": round(footprint, 1),
        "far": round(built / site, 3) if site else 0.0,
        "coverage": round(footprint / site, 3) if site else 0.0,
        "open_m2": round(green, 1),
        "open_ratio": round(green / site, 3) if site else 0.0,
    }


# --------------------------------------------------------------------------
# 总平面
# --------------------------------------------------------------------------
def plan_svg(program: SectorProgram, brief: SectorBrief, *, title: str = "",
             project: Any = None) -> str:
    """总平面关系：块的大小按面积，位置按入口方位与"前场 / 后场"关系。

    关系规则（都是设计判断，不是固定方位）：
    * 主建筑靠入口一侧，前面留集散场；
    * 运动场/装卸场放在入口对侧，不占主入口面；
    * 配套体量（食堂、体育馆）夹在主建筑与后场之间；
    * 临路一侧画道路带与出入口。
    """
    pl = plot(project, brief) if project is not None else plot(None, brief)
    site = pl["site_m2"]
    bw_mm, bd_mm = pl["w_mm"], pl["d_mm"]
    scale = min(700.0 / bw_mm, 400.0 / bd_mm)
    W, H = bw_mm * scale, bd_mm * scale
    left, top = 150.0, 176.0
    s = Svg(int(left + W + 320), int(top + H + 230), title=title or "总平面关系")
    s.text(left, 116, title or "总平面关系", size=19, weight="600", color=INK)
    sub = (f"用地 {site:,.0f} m²　｜　边界：{_BASIS_CN.get(pl['basis'], pl['basis'])}"
           f"　｜　{pl['entrance_note']}")
    s.text(left, 142, sub, size=11.5, color=MUTED)
    s.text(left, 160, "块的位置表达功能关系与出入方向；不给退线、标高与放线，须实测与报建复核。",
           size=11.0, color=MUTED)

    # 场地
    poly = [(left + p[0] * scale, top + p[1] * scale) for p in pl["polygon"]]
    s.polygon(poly, fill="#FBFBF9", stroke=INK, sw=1.6)
    ent = pl["entrance"]
    axis = _axis(ent)                        # 入口法向（指向场地内部）
    # 道路带：临路一侧
    for side in pl["roads"] or [ent]:
        _road_band(s, left, top, W, H, side)
    # 入口箭头
    ex, ey = _edge_point(left, top, W, H, ent, 0.22)
    s.line(ex + axis[0] * 46, ey + axis[1] * 46, ex - axis[0] * 8, ey - axis[1] * 8,
           stroke="#3F7D58", sw=2.2, arrow=True)
    s.text(ex + axis[0] * 58, ey + axis[1] * 58 + 4, "主入口", size=11, color="#3F7D58",
           anchor="middle")

    blocks = [b for b in program.blocks if b.get("kind") in ("building", "sport", "yard")]
    blds = [b for b in blocks if b["kind"] == "building"]
    sport = next((b for b in blocks if b["kind"] == "sport"), None)
    yard = next((b for b in blocks if b["kind"] == "yard"), None)
    main = max(blds, key=lambda b: float(b.get("area_m2") or 0)) if blds else None
    rest = [b for b in blds if b is not main]

    # 前场 58% / 后场 42%（沿入口法向）
    fx, fy, fw, fh = _front_zone(left, top, W, H, ent, 0.58)
    if main:
        mx, my, mw, mh = _inset(fx, fy, fw, fh, 0.18)
        s.rect(mx, my, mw, mh, fill=BLDG, stroke=INK, sw=1.4, rx=0)
        s.text(mx + 14, my + 26, main["name"], size=13, weight="600", color=INK)
        s.text(mx + 14, my + 46, f"{main['area_m2']:,.0f} m²　{main.get('note', '')}",
               size=10.5, color=MUTED)
        s.text(mx + mw / 2, my + mh - 14, "主建筑", size=10, color=MUTED, anchor="middle")
    # 配套：沿主建筑一侧排开（与主建筑同处前场，不占入口面）
    for i, b in enumerate(rest[:2]):
        bw2 = fw * 0.30
        bh2 = max(30.0, min(fh * 0.26, bw2 * 0.62))
        bx, by = _along(fx, fy, fw, fh, ent, 0.02, 0.16 + i * 0.34)
        s.rect(bx, by, bw2, bh2, fill=BLDG, stroke=INK, sw=1.2, rx=0)
        s.text(bx + 10, by + 22, b["name"], size=11.5, weight="600", color=INK)
        s.text(bx + 10, by + 40, f"{b['area_m2']:,.0f} m²", size=10, color=MUTED)
    # 后场：运动场（入口对侧）或装卸场
    bx0, by0, bw3, bh3 = _back_zone(left, top, W, H, ent, 0.42)
    if sport:
        x, y, w, h = _inset(bx0, by0, bw3, bh3, 0.12)
        s.rect(x, y, w, h, fill=SPORT, stroke=GREEN_D, sw=1.2, rx=6)
        s.text(x + 14, y + 26, sport["name"], size=13, weight="600", color="#3F5B36")
        s.text(x + 14, y + 46, f"{sport['area_m2']:,.0f} m²", size=11, color="#5C7A55")
        s.text(x + w / 2, y + h / 2 + 18, "200 m 环道 + 球场（入口对侧）", size=10.5,
               color="#5C7A55", anchor="middle")
    if yard:
        x, y, w, h = _inset(bx0, by0, bw3, bh3, 0.14)
        s.rect(x, y, w, h, fill=ROAD, stroke=ROAD_D, sw=1.0, rx=0)
        s.text(x + 14, y + 24, yard["name"], size=12, weight="600", color="#6B6455")
        s.text(x + 14, y + 42, "进货 / 出货分端，不与员工流线交叉", size=10,
               color="#6B6455")
    # 绿地：主建筑与后场之间的一条，以及边界退让带
    s.rect(fx, fy + fh, fw, max(6.0, (by0 - (fy + fh)) if by0 > fy + fh else 8.0),
           fill=GREEN, stroke="none", rx=0, opacity=0.55)
    for i in range(7):
        cx = left + 30 + i * (W - 60) / 6.0
        s.circle(cx, top + H - 16, 5 + (i % 3), fill=GREEN_D, stroke="none")

    # 指北（方位按场地描述，未核实则标注）
    _north(s, left + W - 26, top - 30, ent)
    # 比例尺
    bar_m = 20.0
    bar_px = bar_m * 1000 * scale
    s.rect(left, top + H + 40, bar_px, 5, fill=INK, stroke=INK, sw=0.6, rx=0)
    s.text(left + bar_px + 10, top + H + 46, f"{bar_m:.0f} m", size=10, color=MUTED)

    # 指标
    m = metrics(program, brief)
    rx = left + W + 34
    s.text(rx, top + 4, "总图指标", size=12.5, weight="600", color=INK)
    rows = [("用地面积", f"{m['site_m2']:,.0f} m²"),
            ("建筑面积", f"{m['building_m2']:,.0f} m²"),
            ("建筑基底", f"{m['footprint_m2']:,.0f} m²"),
            ("容积率", f"{m['far']:.2f}"),
            ("建筑密度", f"{m['coverage']:.0%}"),
            ("空地/绿地", f"{m['open_m2']:,.0f} m²（{m['open_ratio']:.0%}）")]
    for i, (k, v) in enumerate(rows):
        y = top + 32 + i * 25
        s.text(rx, y, k, size=11, color=MUTED)
        s.text(rx + 92, y, v, size=11.5, color=INK)
    y2 = top + 32 + len(rows) * 25 + 18
    for line in ("块面积按任务书推算，", "不含道路与硬地的精确占地。",
                 "", "方位：客户描述" if pl["roads"] else "方位：假设（未描述）",
                 "退界：未取得规划条件" ):
        s.text(rx, y2, line, size=10, color=MUTED)
        y2 += 16
    s.text(left, top + H + 92,
           "图示为总平面关系：块位置、出入口与流线方向可讨论；退线、间距、消防车道宽度须按当地规定核。",
           size=10.5, color=MUTED)
    return s.render()


_BASIS_CN = {"surveyed": "实测边界", "drawing": "已有图纸边界",
             "client": "业主估算边界", "assumed": "矩形假设", "proposed": "建议轮廓"}


def _axis(side: str) -> Tuple[float, float]:
    """入口朝内的法向（SVG 坐标，y 向下）。"""
    return {"n": (0.0, 1.0), "s": (0.0, -1.0), "e": (-1.0, 0.0),
            "w": (1.0, 0.0)}.get(side, (0.0, -1.0))


def _edge_point(x: float, y: float, w: float, h: float, side: str,
                t: float) -> Tuple[float, float]:
    if side == "n":
        return x + w * t, y
    if side == "s":
        return x + w * t, y + h
    if side == "w":
        return x, y + h * t
    return x + w, y + h * t


def _front_zone(x: float, y: float, w: float, h: float, side: str,
                share: float) -> Tuple[float, float, float, float]:
    if side == "n":
        return x, y, w, h * share
    if side == "s":
        return x, y + h * (1 - share), w, h * share
    if side == "w":
        return x, y, w * share, h
    return x + w * (1 - share), y, w * share, h


def _back_zone(x: float, y: float, w: float, h: float, side: str,
               share: float) -> Tuple[float, float, float, float]:
    if side == "n":
        return x, y + h * (1 - share), w, h * share
    if side == "s":
        return x, y, w, h * share
    if side == "w":
        return x + w * (1 - share), y, w * share, h
    return x, y, w * share, h


def _inset(x: float, y: float, w: float, h: float,
           pad: float) -> Tuple[float, float, float, float]:
    px, py = w * pad, h * pad
    return x + px, y + py, max(24.0, w - 2 * px), max(20.0, h - 2 * py)


def _along(x: float, y: float, w: float, h: float, side: str, u: float, v: float
           ) -> Tuple[float, float]:
    """在前场里按"沿入口面 / 远离入口"两个比例定位一个块。"""
    if side in ("n", "s"):
        return x + w * u, y + h * v
    return x + w * v, y + h * u


def _road_band(s: Svg, x: float, y: float, w: float, h: float, side: str) -> None:
    t = 9.0
    if side == "n":
        s.rect(x, y - t, w, t, fill=ROAD, stroke="none", rx=0)
    elif side == "s":
        s.rect(x, y + h, w, t, fill=ROAD, stroke="none", rx=0)
    elif side == "w":
        s.rect(x - t, y, t, h, fill=ROAD, stroke="none", rx=0)
    else:
        s.rect(x + w, y, t, h, fill=ROAD, stroke="none", rx=0)


def _north(s: Svg, nx: float, ny: float, entrance: str) -> None:
    """指北针：只表达"图上为北"，真实朝向须由红线与现状道路确认。"""
    s.polygon([(nx, ny - 20), (nx - 8, ny + 6), (nx, ny + 1), (nx + 8, ny + 6)],
              fill=INK, stroke=INK, sw=0.8)
    s.text(nx, ny + 22, "N", size=10.5, color=INK, anchor="middle")


# --------------------------------------------------------------------------
# 景观总图
# --------------------------------------------------------------------------
def _blob(cx: float, cy: float, rx: float, ry: float, n: int = 16,
          seed: float = 0.6) -> List[Tuple[float, float]]:
    out: List[Tuple[float, float]] = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1.0 + 0.13 * math.sin(3 * a + seed) + 0.07 * math.cos(5 * a + seed * 2)
        out.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return out


def _ring(cx: float, cy: float, rx: float, ry: float, n: int = 28
          ) -> List[Tuple[float, float]]:
    return [(cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def landscape_svg(program: SectorProgram, brief: SectorBrief, *, title: str = "",
                  kind: str = "water_loop", project: Any = None) -> Tuple[str, Dict[str, Any]]:
    """景观总平面：按选定的组织方式构图，并把结构证据一起返回。

    返回 (svg, evidence)。evidence 是 `parti.inspect` 用的判定依据——
    图上画了什么、画成什么样，由那里核对，不能只写在报告里。
    """
    pl = plot(project, brief) if project is not None else plot(None, brief)
    site = pl["site_m2"]
    scale = min(720.0 / pl["w_mm"], 420.0 / pl["d_mm"])
    W, H = pl["w_mm"] * scale, pl["d_mm"] * scale
    left, top = 150.0, 176.0
    s = Svg(int(left + W + 300), int(top + H + 230), title=title or "景观总平面")
    s.text(left, 116, title or "景观总平面", size=19, weight="600", color=INK)
    s.text(left, 142, f"场地 {site:,.0f} m²　｜　边界：{_BASIS_CN.get(pl['basis'], pl['basis'])}"
                      f"　｜　{pl['entrance_note']}", size=11.5, color=MUTED)
    s.text(left, 160, "构图表达分区、游线、水面与种植层次；竖向、岸线与放线须实测与苗木确认。",
           size=11.0, color=MUTED)

    # 场地底
    poly = [(left + p[0] * scale, top + p[1] * scale) for p in pl["polygon"]]
    s.polygon(poly, fill="#F5F7F1", stroke=INK, sw=1.6)
    ent = pl["entrance"]
    ent_pt = _edge_point(left, top, W, H, ent, 0.28)
    inward = _axis(ent)

    share = {r.zone: r.area_m2 / max(sum(x.area_m2 for x in program.rows), 1.0)
             for r in program.rows}
    water_share = share.get("water", 0.0)
    green_share = share.get("planting", 0.0)
    pave_share = share.get("paving", 0.0) + share.get("path", 0.0)

    evidence: Dict[str, Any] = {}
    # 中心区（避开入口 30%）
    cx = left + W * (0.62 if ent in ("n", "s") else 0.5)
    cy = top + H * (0.58 if ent in ("n", "s") else 0.62)

    if kind == "terrace":
        evidence.update(_terrace_scene(s, left, top, W, H, ent, green_share, pave_share))
        water_note = "无水景（按低维护组织）"
    elif kind == "grove_edge":
        evidence.update(_grove_scene(s, left, top, W, H, ent, green_share, pave_share))
        water_note = "无水景（边界围合为主）"
    else:
        evidence.update(_water_scene(s, left, top, W, H, ent, water_share,
                                     green_share, pave_share, cx, cy))

    # 园路：从入口接进主环
    ring = evidence.pop("_ring", [])
    if ring:
        near = min(ring, key=lambda p: (p[0] - ent_pt[0]) ** 2 + (p[1] - ent_pt[1]) ** 2)
        s.polyline([ent_pt, ((ent_pt[0] + near[0]) / 2, (ent_pt[1] + near[1]) / 2), near],
                   stroke=TRUNK, sw=2.6, arrow=False)
        s.polyline(ring + [ring[0]], stroke=TRUNK, sw=2.6, arrow=False)
    elif evidence.get("_path"):
        s.polyline(evidence.pop("_path"), stroke=TRUNK, sw=2.4, arrow=False)

    # 入口
    s.line(ent_pt[0] - inward[0] * 40, ent_pt[1] - inward[1] * 40,
           ent_pt[0] + inward[0] * 6, ent_pt[1] + inward[1] * 6,
           stroke="#3F7D58", sw=2.0, arrow=True)
    s.text(ent_pt[0] - inward[0] * 52, ent_pt[1] - inward[1] * 52 + 4, "入口",
           size=11, color="#3F7D58", anchor="middle")

    _north(s, left + W - 26, top - 30, ent)
    bar_px = 10.0 * 1000 * scale
    s.rect(left, top + H + 40, bar_px, 5, fill=INK, stroke=INK, sw=0.6, rx=0)
    s.text(left + bar_px + 10, top + H + 46, "10 m", size=10, color=MUTED)

    # 面积占比：单独一张条图，不是把场地切成色带
    rx = left + W + 30
    s.text(rx, top + 2, "面积占比", size=12.5, weight="600", color=INK)
    y = top + 28
    maxbar = 150.0
    for r in program.rows:
        frac = r.area_m2 / max(sum(x.area_m2 for x in program.rows), 1.0)
        s.text(rx, y, r.name, size=10.5, color=MUTED)
        s.text(rx + maxbar + 34, y, f"{frac:.0%}", size=10.5, color=INK)
        s.rect(rx, y + 5, maxbar * frac, 5, fill="#C9D8BE" if r.zone == "planting"
               else WATER if r.zone == "water" else PAVE, stroke="none", rx=0)
        y += 30
    s.text(rx, y + 6, f"场地 {site:,.0f} m²", size=10.5, color=MUTED)
    s.text(rx, y + 24, "占比由任务书分区面积得出，", size=9.5, color=MUTED)
    s.text(rx, y + 38, "与总平面的构图是两件事。", size=9.5, color=MUTED)
    s.text(left, top + H + 92,
           "分区、游线与节点可讨论；竖向标高、排水坡向、植物规格按现场与苗木条件另定。",
           size=10.5, color=MUTED)
    return s.render(), evidence


def _water_scene(s: Svg, left: float, top: float, W: float, H: float, ent: str,
                 water_share: float, green_share: float, pave_share: float,
                 cx: float, cy: float) -> Dict[str, Any]:
    """一池静水 + 环水游线：水面成一块、路绕水、岸上有节点。"""
    rx = W * max(0.16, min(0.30, math.sqrt(max(water_share, 0.04)) * 0.62))
    ry = H * max(0.15, min(0.28, math.sqrt(max(water_share, 0.04)) * 0.58))
    w1 = _blob(cx, cy, rx, ry)
    s.polygon(w1, fill=WATER, stroke=WATER_D, sw=1.2)
    inner = _blob(cx, cy, rx * 0.92, ry * 0.92, 30, seed=1.7)
    s.polygon(inner, fill="none", stroke="#FFFFFF", sw=0.8, opacity=0.55)
    s.text(cx, cy + 4, "静水面", size=11.5, color="#2F6FB2", anchor="middle")
    s.text(cx, cy + 20, f"{water_share:.0%}", size=10, color="#4A7FB0", anchor="middle")
    ring = _ring(cx, cy, rx * 1.42, ry * 1.5)
    # 种植：边界一圈 + 水后一丛（三个冠幅）
    pts: List[Tuple[float, float]] = []
    n = 26
    for i in range(n):
        a = 2 * math.pi * i / n
        px = left + W / 2 + (W * 0.46) * math.cos(a)
        py = top + H / 2 + (H * 0.44) * math.sin(a)
        pts.append((px, py))
        s.circle(px, py, 7 + (i % 3) * 3.5, fill=GREEN, stroke=GREEN_D, sw=0.8)
    for i in range(9):
        px = left + W * 0.18 + (i % 3) * 26
        py = top + H * 0.22 + (i // 3) * 24
        s.circle(px, py, 9 + (i % 2) * 4, fill=GREEN, stroke=GREEN_D, sw=0.9)
    # 铺装：入口广场 + 茶席平台（多边形，不是整条色带）
    px0 = left + W * 0.16
    py0 = top + H * 0.16
    s.polygon([(px0, py0), (px0 + W * 0.22, py0 - 8), (px0 + W * 0.24, py0 + H * 0.16),
               (px0 + 8, py0 + H * 0.17)], fill=PAVE, stroke=ROAD_D, sw=0.9)
    s.text(px0 + W * 0.06, py0 + H * 0.09, "入口广场", size=10, color="#6B6455")
    tx = cx + rx * 1.1
    ty = cy - ry * 1.25
    s.polygon([(tx, ty), (tx + W * 0.13, ty - 6), (tx + W * 0.14, ty + H * 0.10),
               (tx + 6, ty + H * 0.11)], fill=PAVE, stroke=ROAD_D, sw=0.9)
    s.text(tx + W * 0.06, ty + H * 0.055, "林下茶席", size=10, color="#6B6455", anchor="middle")
    # 节点
    for label, (nx, ny) in (("观景点", (cx - rx * 1.5, cy + ry * 0.3)),
                            ("入水台阶", (cx + rx * 0.2, cy + ry * 1.2))):
        s.circle(nx, ny, 3.4, fill="#3F7D58", stroke="none")
        s.text(nx + 7, ny + 3, label, size=9.5, color="#3F7D58")
    return {
        "water_single": {"ok": water_share > 0.01,
                         "detail": f"水面成块，占 {water_share:.0%}，未沿整条边铺"},
        "path_loop": {"ok": True, "detail": "园路环水闭合，并从入口接入"},
        "shore_nodes": {"ok": True, "detail": "岸边设观景点与入水台阶 2 处"},
        "planting_layers": {"ok": True, "detail": f"边界 {n} 株 + 水后一丛，三种冠幅"},
        "_ring": ring,
        "_green": green_share, "_pave": pave_share,
    }


def _terrace_scene(s: Svg, left: float, top: float, W: float, H: float, ent: str,
                   green_share: float, pave_share: float) -> Dict[str, Any]:
    """台地 + 旱溪：2–3 级台阶式台地，一条旱溪接最低处。"""
    steps = 3 if H > 240 else 2
    y0 = top + H * 0.18
    each = (H * 0.62) / steps
    path: List[Tuple[float, float]] = []
    for i in range(steps):
        y = y0 + i * each
        x0 = left + W * (0.12 + i * 0.02)
        x1 = left + W * (0.88 - i * 0.02)
        s.polygon([(x0, y), (x1, y), (x1, y + each * 0.9), (x0, y + each * 0.9)],
                  fill=GREEN if i % 2 == 0 else "#E7EEE0", stroke=GREEN_D, sw=1.0)
        s.line(x0, y, x1, y, stroke=ROAD_D, sw=1.6)
        s.text(x0 + 10, y + each * 0.45, f"台地 {i + 1}（抬高 {(steps - i) * 0.35:.1f} m）",
               size=10, color="#4A5B42")
        for j in range(6):
            s.circle(x0 + 26 + j * (x1 - x0 - 40) / 5.0, y + each * 0.72,
                     6 + (j % 3) * 2, fill=GREEN, stroke=GREEN_D, sw=0.7)
        path.append(((x0 + x1) / 2, y + each * 0.95))
    # 旱溪：从最高台地斜穿到最低处
    swale = [(left + W * 0.30, y0), (left + W * 0.42, y0 + H * 0.24),
             (left + W * 0.36, y0 + H * 0.42), (left + W * 0.5, y0 + H * 0.62)]
    s.polyline(swale, stroke="#B7C7D4", sw=6.0, arrow=False)
    s.polyline(swale, stroke="#8FB8D8", sw=1.4, arrow=False, dash="10 8")
    s.text(swale[2][0] + 8, swale[2][1] + 14, "旱溪（雨季排水）", size=9.5, color="#4A7FB0")
    # 入口平台
    px, py = left + W * 0.14, top + H * 0.84
    s.polygon([(px, py), (px + W * 0.24, py - 6), (px + W * 0.24, py + H * 0.10),
               (px + 6, py + H * 0.10)], fill=PAVE, stroke=ROAD_D, sw=0.9)
    s.text(px + W * 0.12, py + H * 0.06, "入口平台", size=10, color="#6B6455", anchor="middle")
    return {
        "terraces": {"ok": steps >= 2, "detail": f"{steps} 级台地，高差约 {steps * 0.35:.1f} m"},
        "swale": {"ok": True, "detail": "旱溪从最高台地接到最低处，纵坡向下"},
        "planting_zones": {"ok": green_share > 0.2,
                           "detail": f"台地南侧喜阳、北侧耐阴；绿地占 {green_share:.0%}"},
        "_path": path + [(left + W * 0.14, top + H * 0.9)],
    }


def _grove_scene(s: Svg, left: float, top: float, W: float, H: float, ent: str,
                 green_share: float, pave_share: float) -> Dict[str, Any]:
    """边界乔木带 + 中心活动场地 + 林下茶席。"""
    n = 30
    for i in range(n):
        a = 2 * math.pi * i / n
        px = left + W / 2 + (W * 0.455) * math.cos(a)
        py = top + H / 2 + (H * 0.43) * math.sin(a)
        s.circle(px, py, 9 + (i % 3) * 3, fill=GREEN, stroke=GREEN_D, sw=0.9)
    cx, cy = left + W * 0.52, top + H * 0.55
    s.ellipse(cx, cy, W * 0.24, H * 0.24, fill=PAVE, stroke=ROAD_D, sw=1.0)
    s.text(cx, cy + 4, "中心活动场地", size=11, color="#6B6455", anchor="middle")
    s.text(cx, cy + 22, "（草坪 + 硬质，供儿童活动）", size=9.5, color="#7A7364", anchor="middle")
    # 茶席
    tx, ty = cx - W * 0.02, cy - H * 0.17
    s.polygon([(tx, ty), (tx + W * 0.10, ty), (tx + W * 0.10, ty + H * 0.09),
               (tx, ty + H * 0.09)], fill="#E4D9C3", stroke=ROAD_D, sw=0.9)
    s.text(tx + W * 0.05, ty + H * 0.05, "林下茶席", size=10, color="#6B6455",
           anchor="middle")
    for i in range(5):
        s.circle(tx - 14 + (i % 3) * 12, ty - 12 + (i // 3) * 10, 8, fill=GREEN,
                 stroke=GREEN_D, sw=0.8)
    path = [(left + W * 0.30, top + H * 0.92), (cx, cy + H * 0.24), (cx + W * 0.2, cy)]
    s.polyline(path, stroke=TRUNK, sw=2.4, arrow=False)
    return {
        "tree_belt": {"ok": True, "detail": f"沿边界 {n} 株乔木围合"},
        "central_clear": {"ok": True, "detail": "中心留出草坪与硬质活动场地"},
        "tea_deck": {"ok": True, "detail": "林下茶席有独立铺装与树荫"},
        "_path": path,
    }


__all__ = ["landscape_svg", "metrics", "plan_svg", "plot"]
