"""把排好的方案画成一张可读的平面图（矢量）。

用途是**看图**：房间位置、面积、走廊、门窗位置、采光面朝哪、以及 S2 选定的
组织方式（中庭 / 诊疗街 / 双廊 / 工艺顺序）在图上落在哪。不是施工图，
不标尺寸链、轴线与材料做法。DXF 另出（`adapters.dxf`），这里给的是
客户提案与评审能直接看的那一张。

几处刻意为之：
* 门画成门扇 + 开启弧，不画成小圆点——评审看的是"从哪进"；
* 左侧标出带名（教学带 / 共享中庭 / 后勤带），让剖面构成一眼可见；
* 中庭、诊疗街用与走廊不同的底色，否则"概念落地"在图上读不出来；
* 只画本方案自己的隔墙：`base_walls` 里属于别的方案的墙必须过滤掉，
  否则方案 B 会带上方案 A 的隔墙，图上凭空多出一道缝。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

from ..concept.diagrams import Svg

#: 用途 -> 填充色。同一套色系里区分功能，不靠文字。
USE_FILL = {
    "teaching": "#EFE7D6", "study": "#F3EADB", "diagnosis": "#E4EEF4",
    "public": "#F6F1E4", "waiting": "#F6F1E4", "tech": "#DDE8F0",
    "lab": "#DDE8F0", "office": "#E7E9E4", "guest": "#F2E9E1",
    "boh": "#DCD8CE", "service": "#DCD8CE", "storage": "#DCD8CE",
    "bathroom": "#D8E4E8", "ward": "#E9E3F2", "production": "#E8E4DA",
    "warehouse": "#E3DDD0", "circulation": "#FAF8F2",
}
USE_LABEL = {
    "teaching": "教室", "study": "专用", "diagnosis": "诊室", "public": "公共",
    "waiting": "候诊", "tech": "医技", "lab": "检验", "office": "办公",
    "guest": "客房", "boh": "后场", "service": "服务", "storage": "储藏",
    "bathroom": "卫浴", "ward": "病房", "production": "生产",
    "warehouse": "仓储", "circulation": "交通",
}
#: 中庭 / 街 / 连廊：概念的"公共骨架"，必须与普通交通区分开
SPINE_FILL = "#F1EADA"
CORR_FILL = "#FAF8F2"


def _fit(name: str, limit: int) -> str:
    return name if len(name) <= limit else name[:limit]


def _is_spine(sp: Any) -> bool:
    return any(k in sp.name for k in ("中庭", "街", "连廊", "平台"))


def _band_tag(sp: Any) -> str:
    """单个房间属于哪一类带（短标签，用于合成带名）。"""
    use = sp.use
    if _is_spine(sp):
        return "公共骨架"
    if use == "teaching":
        return "教室"
    if use == "study":
        return "专用"
    if use in ("office",):
        return "办公"
    if use in ("service", "storage", "boh"):
        return "辅助"
    if use == "bathroom":
        return "卫浴"
    if use in ("diagnosis",):
        return "诊室"
    if use in ("tech", "lab"):
        return "医技"
    if use in ("waiting", "public"):
        return "公共"
    if use == "guest":
        return "客房"
    if use == "ward":
        return "病房"
    if use == "production":
        return "生产"
    if use == "warehouse":
        return "仓储"
    if use == "circulation":
        return "交通"
    return ""


def _band_name(members: Sequence[Any]) -> str:
    """一条带的名字由它的实际构成决定，不能拿最大那间房代表整条带。

    之前一条带里放着"专用教室 + 办公 + 卫生间"，标签却写成"后勤带"，
    图上等于给了个错的剖面解释。
    """
    total = sum(m.area_m2 for m in members) or 1.0
    share: Dict[str, float] = {}
    for m in members:
        tag = _band_tag(m)
        if tag:
            share[tag] = share.get(tag, 0.0) + m.area_m2
    if not share:
        return ""
    if "公共骨架" in share and share["公共骨架"] / total >= 0.55:
        return "公共骨架"
    ranked = [k for k, v in sorted(share.items(), key=lambda kv: -kv[1])
              if v / total >= 0.18][:2] or [max(share, key=lambda k: share[k])]
    return "、".join(ranked) + "带"


def plan_svg(scheme: Any, *, title: str = "", width: int = 1280,
             base_walls: Sequence[Any] = (), unit: str = "") -> str:
    """画方案平面。`scheme` 是 planner.SchemeResult。

    `base_walls` 传项目里的外墙：外墙不在 scheme.elements 里（它们属于项目），
    不传的话窗会找不到宿主墙，图上就没有窗。属于别的方案的隔墙会被过滤掉。
    """
    rooms = [s for s in scheme.spaces if s.use not in ("envelope", "outdoor")]
    if not rooms:
        raise ValueError("方案里没有可画的房间")
    xs = [p[0] for s in rooms for p in s.boundary_mm2d]
    ys = [p[1] for s in rooms for p in s.boundary_mm2d]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    bw, bh = max(x1 - x0, 1.0), max(y1 - y0, 1.0)

    margin_l, margin_t, margin_r, margin_b = 138, 138, 296, 128
    scale = min((width - margin_l - margin_r) / bw, 560.0 / bh)
    W, H = bw * scale, bh * scale

    s = Svg(int(margin_l + W + margin_r), int(margin_t + H + margin_b),
            title=title or "平面方案")
    s.text(margin_l, 96, title or "平面方案", size=20, weight="600", color="#1E2328")
    circ = sum(x.area_m2 for x in rooms if x.use == "circulation")
    spine = sum(x.area_m2 for x in rooms if x.use == "circulation" and _is_spine(x))
    # 副标题只说这张图是什么深度：组织方式 + 统计口径，不重复标题里的项目名
    lead = "　｜　".join(x for x in (str(scheme.metrics.get("parti_label") or ""), unit) if x)
    sub = ((lead + "　｜　") if lead else "") + (
        f"{len(rooms)} 个房间　｜　"
        f"使用面积 {sum(x.area_m2 for x in rooms):,.0f} m²　｜　"
        f"交通面积 {circ:,.0f} m²（骨架 {spine:,.0f} + 走廊 {circ - spine:,.0f}）")
    s.text(margin_l, 118, sub, size=11.5, color="#6B7280")

    def px(v: float) -> float:
        return margin_l + (v - x0) * scale

    def py(v: float) -> float:
        return margin_t + H - (v - y0) * scale

    # 房间
    for sp in rooms:
        pts = [(px(p[0]), py(p[1])) for p in sp.boundary_mm2d]
        if _is_spine(sp):
            fill = SPINE_FILL
        elif sp.use == "circulation":
            fill = CORR_FILL
        else:
            fill = USE_FILL.get(sp.use, "#F1EFE8")
        s.polygon(pts, fill=fill, stroke="#4A4F4B", sw=1.0)
        bb = sp.bbox()
        cx = (px(bb[0]) + px(bb[2])) / 2.0
        cy = (py(bb[1]) + py(bb[3])) / 2.0
        w_px = abs(px(bb[2]) - px(bb[0]))
        h_px = abs(py(bb[1]) - py(bb[3]))
        if w_px > 62 and h_px > 34:
            s.text(cx, cy - 2, _fit(sp.name, 10), size=10.5, color="#23281F",
                   anchor="middle")
            s.text(cx, cy + 14, f"{sp.area_m2:.0f} m²", size=9.5, color="#5A5F58",
                   anchor="middle")
        elif h_px > 60:
            # 窄条（储藏、配电、服务间）：竖着写，别让房间变成无名白块
            s.text(cx + 1, cy, _fit(sp.name, 5), size=8.5, color="#3C443E",
                   anchor="middle", rotate=-90)
        elif w_px > 26:
            s.text(cx, cy + 3, f"{sp.area_m2:.0f}", size=8.5, color="#5A5F58",
                   anchor="middle")

    # 墙：本方案的隔墙 + 项目外墙；别的方案的隔墙一律不画
    walls = {e.id: e for e in scheme.elements if e.type == "wall"}
    for e in base_walls or ():
        if getattr(e, "type", "") != "wall":
            continue
        if str(getattr(e, "source", "")).startswith("scheme_"):
            continue
        walls[e.id] = e
    for w in walls.values():
        g = w.geometry or {}
        a, b_ = g.get("start"), g.get("end")
        if not (a and b_):
            continue
        t = float(g.get("thickness_mm") or 120) * scale
        s.line(px(float(a[0])), py(float(a[1])), px(float(b_[0])), py(float(b_[1])),
               stroke="#3A3F3A", sw=max(1.0, t))

    # 窗：沿宿主墙按偏移画（窗只记 host_wall + offset + width）
    for e in scheme.elements:
        if e.type != "window":
            continue
        g = e.geometry or {}
        host = walls.get(str(g.get("host_wall") or ""))
        if host is None:
            continue
        hg = host.geometry or {}
        a, b_ = hg.get("start"), hg.get("end")
        if not (a and b_):
            continue
        ax, ay = float(a[0]), float(a[1])
        bx, by = float(b_[0]), float(b_[1])
        L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        off = float(g.get("offset_mm") or 0.0)
        wid = float(g.get("width_mm") or 1200.0)
        p1 = (ax + ux * off, ay + uy * off)
        p2 = (ax + ux * (off + wid), ay + uy * (off + wid))
        s.line(px(p1[0]), py(p1[1]), px(p2[0]), py(p2[1]),
               stroke="#FFFFFF", sw=max(5.0, 300 * scale))
        s.line(px(p1[0]), py(p1[1]), px(p2[0]), py(p2[1]),
               stroke="#2F6FB2", sw=max(2.0, 90 * scale))

    # 门：门扇 + 开启弧（示意，不标开启方向与五金）
    for e in scheme.elements:
        if e.type != "door":
            continue
        g = e.geometry or {}
        host = walls.get(str(g.get("host_wall") or ""))
        if host is None:
            continue
        hg = host.geometry or {}
        a, b_ = hg.get("start"), hg.get("end")
        if not (a and b_):
            continue
        ax, ay = float(a[0]), float(a[1])
        bx, by = float(b_[0]), float(b_[1])
        L = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 or 1.0
        ux, uy = (bx - ax) / L, (by - ay) / L
        off = float(g.get("offset_mm") or 0.0)
        wid = float(g.get("width_mm") or 900.0)
        hx, hy = ax + ux * off, ay + uy * off          # 合页
        cx1, cy1 = ax + ux * (off + wid), ay + uy * (off + wid)
        r = wid * scale
        # 门扇：垂直于墙、向房间内开 90°
        nx, ny = -uy, ux
        lx, ly = hx + nx * wid, hy + ny * wid
        s.line(px(hx), py(hy), px(lx), py(ly), stroke="#5B6068", sw=1.1)
        # 开启弧
        p0 = (px(cx1), py(cy1))
        p1 = (px(lx), py(ly))
        s.path(f"M {p0[0]:.1f} {p0[1]:.1f} A {r:.1f} {r:.1f} 0 0 0 {p1[0]:.1f} {p1[1]:.1f}",
               stroke="#9BA1A8", sw=0.7)

    # 左侧带名：剖面构成看得到（按带聚合，不按单个房间）
    bands: List[Tuple[float, float, List[Any]]] = []
    for sp in rooms:
        bb = sp.bbox()
        top_y, bot_y = py(bb[3]), py(bb[1])
        hit = next((i for i, item in enumerate(bands)
                    if abs(item[0] - top_y) < 3 and abs(item[1] - bot_y) < 6), None)
        if hit is None:
            bands.append((top_y, bot_y, [sp]))
        else:
            bands[hit][2].append(sp)
    for top_y, bot_y, members in bands:
        if bot_y - top_y < 26:
            continue
        label = _band_name(members)
        if not label:
            continue
        s.line(margin_l - 52, top_y + 2, margin_l - 52, bot_y - 2, stroke="#C9CED4",
               sw=1.4)
        s.text(margin_l - 60, (top_y + bot_y) / 2 + 3, label, size=9.5, color="#6B7280",
               anchor="middle", rotate=-90)

    # 主入口：从最靠近外墙的交通空间引一支箭头
    spine_all = [x for x in rooms if x.use == "circulation"]
    if spine_all:
        main = max(spine_all, key=lambda x: x.area_m2)
        bb = main.bbox()
        mx = (px(bb[0]) + px(bb[2])) / 2.0
        south = py(bb[1])
        north = py(bb[3])
        if min(abs(south - (margin_t + H)), abs(north - margin_t)) < 4:
            if abs(south - (margin_t + H)) < 4:
                s.line(mx, south + 34, mx, south + 3, stroke="#3F7D58", sw=2.0, arrow=True)
                s.text(mx, south + 48, "入口", size=10, color="#3F7D58", anchor="middle")
            else:
                s.line(mx, north - 34, mx, north - 3, stroke="#3F7D58", sw=2.0, arrow=True)
                s.text(mx, north - 42, "入口", size=10, color="#3F7D58", anchor="middle")
        else:
            # 骨架不贴外墙（例如中部中庭）：入口开在骨架端部，箭头从图外指向内
            ex = px(bb[0])
            ey = (py(bb[1]) + py(bb[3])) / 2.0
            s.line(ex - 30, ey, ex - 4, ey, stroke="#3F7D58", sw=2.0, arrow=True)
            s.text(ex - 30, ey + 18, "入口", size=9.5, color="#3F7D58", anchor="start")

    # 右栏：图例与指标
    rx = margin_l + W + 34
    s.text(rx, margin_t + 4, "图例", size=12.5, weight="600", color="#1E2328")
    used: List[str] = []
    for sp in rooms:
        if sp.use not in used:
            used.append(sp.use)
    for i, use in enumerate(used[:9]):
        y = margin_t + 28 + i * 22
        fill = USE_FILL.get(use, "#F1EFE8")
        s.rect(rx, y - 9, 16, 12, fill=fill, stroke="#4A4F4B", sw=0.8, rx=0)
        s.text(rx + 24, y, USE_LABEL.get(use, use), size=10.5, color="#3C443E")

    my = margin_t + 28 + min(len(used), 9) * 22 + 18
    s.text(rx, my, "指标", size=12.5, weight="600", color="#1E2328")
    rows = [("房间数", f"{len(rooms)}"),
            ("使用面积", f"{sum(x.area_m2 for x in rooms):,.0f} m²"),
            ("走廊面积", f"{circ - spine:,.0f} m²" if circ - spine > 0.5 else "—"),
            ("中庭 / 街", f"{spine:,.0f} m²"),
            ("交通占比", f"{circ / max(sum(x.area_m2 for x in rooms), 1e-9):.0%}"),
            ("外窗", f"{scheme.metrics.get('window_count', 0)} 扇"),
            ("采光房间", f"{scheme.metrics.get('daylight_rooms_served', '—')}")]
    for i, (k, v) in enumerate(rows):
        y = my + 26 + i * 21
        s.text(rx, y, k, size=10.5, color="#6B7280")
        s.text(rx + 78, y, v, size=10.5, color="#1E2328")

    # 指北 + 比例尺（按像素换算真实长度）
    nx, ny = margin_l + W - 24, margin_t - 30
    s.polygon([(nx, ny - 18), (nx - 7, ny + 6), (nx, ny + 1), (nx + 7, ny + 6)],
              fill="#1E2328", stroke="#1E2328", sw=0.8)
    s.text(nx, ny + 20, "N", size=10, color="#1E2328", anchor="middle")
    bar_m = 5.0
    bar_px = bar_m * 1000 * scale
    bx, by = margin_l, margin_t + H + 34
    s.rect(bx, by, bar_px, 6, fill="#1E2328", stroke="#1E2328", sw=0.8, rx=0)
    s.text(bx, by + 22, f"0 ——— {bar_m:.0f} m（按图换算）", size=10, color="#6B7280")

    s.text(margin_l, margin_t + H + 84,
           "方案深度：房间面积与关系可讨论；不含尺寸链、轴线、构造与机电。"
           "门为示意位置，开启方向与五金须深化。",
           size=10.5, color="#6B7280")
    return s.render()


__all__ = ["SPINE_FILL", "USE_FILL", "USE_LABEL", "plan_svg"]
