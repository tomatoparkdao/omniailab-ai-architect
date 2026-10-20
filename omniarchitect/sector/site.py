"""总平面：把行业程序里的场地块排到用地上，并算出能核对的指标。

只做**关系**：出入口在哪、什么贴什么、道路能不能环通。不给坐标、
不给标高、不给退线——那些要 redline 与实测。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from ..concept.diagrams import Svg
from .brief import SectorBrief
from .program import SectorProgram

PAD = 60.0
INK = "#1E2328"
MUTED = "#6B7280"
RULE = "#D6D9DD"
GREEN = "#DCE7D5"
ROAD = "#E8E2D4"
WATER = "#CFE3F2"
SPORT = "#D8E6D2"
BLDG = "#EDE7DA"


def _site_rect(site_m2: float, ratio: float = 1.45) -> Tuple[float, float]:
    w = math.sqrt(max(site_m2, 100.0) * ratio)
    return w, max(site_m2 / w, 20.0)


def metrics(program: SectorProgram, brief: SectorBrief) -> Dict[str, Any]:
    site = brief.get("site_area")
    built = sum(b["area_m2"] for b in program.blocks if b.get("kind") == "building")
    footprint = 0.0
    for b in program.blocks:
        if b.get("kind") != "building" or not b.get("area_m2"):
            continue
        w, d = float(b.get("w") or 0), float(b.get("d") or 0)
        footprint += (w * d) if (w and d) else float(b["area_m2"]) / 3.0
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


def plan_svg(program: SectorProgram, brief: SectorBrief, *, title: str = "") -> str:
    """画一张总平面关系图。块的大小按面积，位置按"教学/生产在内、配套在外"。"""
    site = brief.get("site_area") or 6000.0
    sw, sh = _site_rect(site)
    scale = min(760.0 / sw, 420.0 / sh)
    W, H = sw * scale, sh * scale
    left, top = 150.0, 168.0

    s = Svg(int(left + W + 300), int(top + H + 210), title=title or "总平面关系")
    s.text(left, 116, title or "总平面关系（示意）", size=19, weight="600", color=INK)
    s.text(left, 140, "块的位置表达关系与出入方向；不给退线、标高与放线，须实测与报建复核。",
           size=11.5, color=MUTED)

    s.rect(left, top, W, H, fill="#FBFBF9", stroke=INK, sw=1.6, rx=0)
    s.text(left, top - 12, f"用地 {site:,.0f} m²", size=11, color=MUTED)

    # 道路：沿内侧一圈 4 m
    road = 10.0
    s.rect(left + road, top + road, W - 2 * road, H - 2 * road,
           fill="none", stroke=ROAD, sw=7, rx=0)

    blocks = [b for b in program.blocks if b.get("kind") in ("building", "sport")]
    kinds = {b.get("kind") for b in blocks}
    if "sport" in kinds:
        # 运动场永远在南（下）侧，与教学区隔一条路
        sport = next(b for b in blocks if b["kind"] == "sport")
        fw = W * 0.46
        fh = min(H * 0.42, fw * 0.55)
        fx, fy = left + 16, top + H - fh - 16
        s.rect(fx, fy, fw, fh, fill=SPORT, stroke="#A9C39B", sw=1.2, rx=4)
        s.text(fx + 14, fy + 26, sport["name"], size=13, weight="600", color="#3F5B36")
        s.text(fx + 14, fy + 46, f"{sport['area_m2']:,.0f} m²", size=11, color="#5C7A55")
        s.text(fx + fw / 2, fy + fh / 2 + 30, "200 m 环道 + 球场", size=10.5,
               color="#5C7A55", anchor="middle")
    else:
        blds = [b for b in blocks if b["kind"] == "building"]
        # 主建筑在上（北），配套沿右（东）排
        main = max(blds, key=lambda b: float(b.get("area_m2") or 0)) if blds else None
        rest = [b for b in blds if b is not main]
        if main:
            mw = W * 0.58
            md = min(H * 0.46, (W * 0.58) / 1.6)
            s.rect(left + 16, top + 16, mw, md, fill=BLDG, stroke=INK, sw=1.4, rx=0)
            s.text(left + 28, top + 40, main["name"], size=13, weight="600", color=INK)
            s.text(left + 28, top + 60, f"{main['area_m2']:,.0f} m²　{main.get('note', '')}",
                   size=10.5, color=MUTED)
        for i, b in enumerate(rest[:3]):
            bw = W * 0.32
            bh = min(H * 0.22, bw / 1.8)
            bx = left + W - bw - 16
            by = top + 16 + i * (bh + 14)
            s.rect(bx, by, bw, bh, fill=BLDG, stroke=INK, sw=1.2, rx=0)
            s.text(bx + 10, by + 22, b["name"], size=11.5, weight="600", color=INK)
            s.text(bx + 10, by + 40, f"{b['area_m2']:,.0f} m²", size=10, color=MUTED)
        # 装卸场 / 环道
        for b in blocks:
            if b["kind"] == "yard":
                yw, yh = W * 0.3, H * 0.16
                s.rect(left + 16, top + H - yh - 16, yw, yh, fill=ROAD,
                       stroke="#C9BEA4", sw=1.0, rx=0)
                s.text(left + 26, top + H - yh / 2 + 4, b["name"], size=11,
                       color="#6B6455")
                break

    # 入口
    s.line(left + W * 0.18, top + H + 34, left + W * 0.18, top + H + 2,
           stroke="#3F7D58", sw=2.0, arrow=True)
    s.text(left + W * 0.18 - 6, top + H + 52, "主入口", size=11, color="#3F7D58",
           anchor="middle")

    # 指北
    nx, ny = left + W - 26, top - 34
    s.polygon([(nx, ny - 20), (nx - 8, ny + 6), (nx, ny + 1), (nx + 8, ny + 6)],
              fill=INK, stroke=INK, sw=0.8)
    s.text(nx, ny + 22, "N", size=10.5, color=INK, anchor="middle")

    # 右侧指标
    m = metrics(program, brief)
    rx = left + W + 34
    s.text(rx, top + 6, "总图指标", size=12.5, weight="600", color=INK)
    rows = [
        ("用地面积", f"{m['site_m2']:,.0f} m²"),
        ("建筑面积", f"{m['building_m2']:,.0f} m²"),
        ("建筑基底", f"{m['footprint_m2']:,.0f} m²"),
        ("容积率", f"{m['far']:.2f}"),
        ("建筑密度", f"{m['coverage']:.0%}"),
        ("空地/绿地", f"{m['open_m2']:,.0f} m²（{m['open_ratio']:.0%}）"),
    ]
    for i, (k, v) in enumerate(rows):
        y = top + 34 + i * 26
        s.text(rx, y, k, size=11, color=MUTED)
        s.text(rx + 118, y, v, size=11.5, color=INK)
    s.text(rx, top + 34 + len(rows) * 26 + 16, "指标按块面积推算，", size=10, color=MUTED)
    s.text(rx, top + 34 + len(rows) * 26 + 32, "不含道路与硬质地面的精确占地。", size=10,
           color=MUTED)

    s.text(left, top + H + 96,
           "图示为总平面关系：块位置、出入口与流线方向可讨论；退线、间距、消防车道宽度须按当地规定核。",
           size=10.5, color=MUTED)
    return s.render()


def landscape_svg(program: SectorProgram, brief: SectorBrief, *, title: str = "") -> str:
    """景观总平面：分区按占比铺满场地，标出水面与游线。

    只表达"哪一块在哪、占多少、怎么走"，不给放线与标高。
    """
    total = sum(r.area_m2 for r in program.rows) or 1.0
    site = brief.get("site_area") or total
    sw, sh = _site_rect(site)
    scale = min(720.0 / sw, 400.0 / sh)
    W, H = sw * scale, sh * scale
    left, top = 150.0, 168.0
    s = Svg(int(left + W + 280), int(top + H + 220), title=title or "景观总平面")
    s.text(left, 116, title or "景观总平面（示意）", size=19, weight="600", color=INK)
    s.text(left, 140, "分区按面积占比排布；水形、岸线与种植规格须实测与苗源确认。",
           size=11.5, color=MUTED)
    s.rect(left, top, W, H, fill="#F4F6F0", stroke=INK, sw=1.6, rx=0)

    # 分区：绿地在北、铺装居中、水在南
    order = {"planting": 0, "paving": 1, "path": 2, "water": 3}
    rows = sorted(program.rows, key=lambda r: order.get(r.zone, 9))
    green_share = sum(r.area_m2 for r in program.rows if r.zone == "planting") / total
    water_share = sum(r.area_m2 for r in program.rows if r.zone == "water") / total
    gh = H * max(0.25, green_share) * 1.15
    wh = H * max(0.12, water_share) * 1.2
    gh = min(gh, H * 0.55)
    wh = min(wh, H * 0.3)
    s.rect(left, top, W, gh, fill=GREEN, stroke="#A9C39B", sw=1.0, rx=0)
    s.text(left + 14, top + 24, f"绿地与种植 {green_share:.0%}", size=12,
           color="#3F5B36", weight="600")
    # 乔木：沿边界与绿地中排布
    for i in range(9):
        cx = left + 40 + i * (W - 80) / 8.0
        s.circle(cx, top + gh * 0.55, 11 + (i % 3) * 3, fill="#C2D5B4",
                 stroke="#87A276", sw=1.0)
    s.rect(left, top + H - wh, W, wh, fill=WATER, stroke="#9CC3DE", sw=1.0, rx=0)
    s.text(left + 14, top + H - wh + 24, f"水面 {water_share:.0%}", size=12,
           color="#2F6FB2", weight="600")
    for i in range(4):
        s.line(left + 20, top + H - wh + 40 + i * 14, left + W - 20,
               top + H - wh + 40 + i * 14, stroke="#FFFFFF", sw=1.0, dash="18 12")
    # 铺装在中间
    py0, py1 = top + gh, top + H - wh
    s.rect(left + W * 0.18, py0, W * 0.64, max(20.0, py1 - py0), fill="#EFE8D6",
           stroke="#C9BEA4", sw=1.0, rx=0)
    s.text(left + W * 0.2, py0 + 24, "硬质铺装与活动场地", size=11.5, color="#6B6455")
    # 游线
    road = [(left + W * 0.12, top + H * 0.14), (left + W * 0.30, top + gh + 10),
            (left + W * 0.5, (py0 + py1) / 2), (left + W * 0.72, py0 + 14),
            (left + W * 0.86, top + H - wh - 8)]
    s.polyline(road, stroke="#B2A78E", sw=3.2)
    s.text(left + W * 0.5, py1 + 26, "主游线 1.2 m，支路 0.9 m", size=10, color="#6B6455")

    # 指标
    rx = left + W + 34
    s.text(rx, top + 6, "分区占比", size=12.5, weight="600", color=INK)
    for i, r in enumerate(program.rows):
        y = top + 34 + i * 30
        s.text(rx, y, r.name, size=11, color=MUTED)
        s.text(rx + 132, y, f"{r.area_m2 / total:.0%}", size=11.5, color=INK)
    s.text(rx, top + 34 + len(program.rows) * 30 + 14, f"场地 {site:,.0f} m²", size=11,
           color=MUTED)

    # 指北 + 入口
    nx, ny = left + W - 26, top - 34
    s.polygon([(nx, ny - 20), (nx - 8, ny + 6), (nx, ny + 1), (nx + 8, ny + 6)],
              fill=INK, stroke=INK, sw=0.8)
    s.text(nx, ny + 22, "N", size=10.5, color=INK, anchor="middle")
    s.line(left + W * 0.18, top + H + 34, left + W * 0.18, top + H + 2,
           stroke="#3F7D58", sw=2.0, arrow=True)
    s.text(left + W * 0.18 - 6, top + H + 52, "入口", size=11, color="#3F7D58",
           anchor="middle")
    s.text(left, top + H + 96,
           "分区与游线可讨论；竖向标高、排水坡向、植物规格按现场与苗木条件另定。",
           size=10.5, color=MUTED)
    return s.render()


__all__ = ["landscape_svg", "metrics", "plan_svg"]
