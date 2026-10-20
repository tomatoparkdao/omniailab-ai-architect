"""把排好的方案画成一张可读的平面图（矢量）。

用途是**看图**：房间位置、面积、走廊、门窗位置、采光面朝哪。不是施工图，
不标尺寸链、轴线与材料做法。DXF 另出（`adapters.dxf`），这里给的是
客户提案与评审能直接看的那一张。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

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


def _fit(size: int, limit: int) -> str:
    return size if len(size) <= limit else size[:limit]


def plan_svg(scheme: Any, *, title: str = "", width: int = 1280,
             base_walls: Sequence[Any] = ()) -> str:
    """画方案平面。`scheme` 是 planner.SchemeResult。

    `base_walls` 传项目里的外墙：外墙不在 scheme.elements 里（它们属于项目），
    不传的话窗会找不到宿主墙，图上就没有窗。
    """
    rooms = [s for s in scheme.spaces if s.use not in ("envelope", "outdoor")]
    if not rooms:
        raise ValueError("方案里没有可画的房间")
    xs = [p[0] for s in rooms for p in s.boundary_mm2d]
    ys = [p[1] for s in rooms for p in s.boundary_mm2d]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    bw, bh = max(x1 - x0, 1.0), max(y1 - y0, 1.0)

    margin_l, margin_t, margin_r, margin_b = 96, 132, 300, 120
    scale = min((width - margin_l - margin_r) / bw, 560.0 / bh)
    W, H = bw * scale, bh * scale

    s = Svg(int(margin_l + W + margin_r), int(margin_t + H + margin_b),
            title=title or "平面方案")
    s.text(margin_l, 96, title or "平面方案", size=20, weight="600", color="#1E2328")
    sub = (f"{scheme.title}　｜　{len(rooms)} 个房间　｜　"
           f"使用面积 {sum(x.area_m2 for x in rooms):,.0f} m²　｜　"
           f"走廊占比 {float(scheme.metrics.get('corridor_ratio') or 0):.0%}")
    s.text(margin_l, 118, sub, size=11.5, color="#6B7280")

    def px(v: float) -> float:
        return margin_l + (v - x0) * scale

    def py(v: float) -> float:
        return margin_t + H - (v - y0) * scale

    # 房间
    for sp in rooms:
        ring = [(px(p[0]), py(p[1])) for p in sp.boundary_mm2d]
        pts = [(r[0], r[1]) for r in ring]
        fill = USE_FILL.get(sp.use, "#F1EFE8")
        s.polygon(pts, fill=fill, stroke="#4A4F4B", sw=1.0)
        bb = sp.bbox()
        cx = (px(bb[0]) + px(bb[2])) / 2.0
        cy = (py(bb[1]) + py(bb[3])) / 2.0
        w_px = abs(px(bb[2]) - px(bb[0]))
        h_px = abs(py(bb[1]) - py(bb[3]))
        if w_px > 62 and h_px > 34:
            label = _fit(sp.name, 10)
            s.text(cx, cy - 2, label, size=10.5, color="#23281F", anchor="middle")
            s.text(cx, cy + 14, f"{sp.area_m2:.0f} m²", size=9.5, color="#5A5F58",
                   anchor="middle")

    # 墙：隔墙与外墙都画出来，平面才有"墙"的读感
    walls = {e.id: e for e in scheme.elements if e.type == "wall"}
    walls.update({e.id: e for e in (base_walls or ()) if getattr(e, "type", "") == "wall"})
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
               stroke="#2F6FB2", sw=max(5.0, 260 * scale))

    # 门：在房间贴走廊的一侧画一段弧（示意开启方向）
    for e in scheme.elements:
        if e.type != "door":
            continue
        g = e.geometry or {}
        at = g.get("center") or g.get("position")
        if not at:
            continue
        cx, cy = px(float(at[0])), py(float(at[1]))
        s.circle(cx, cy, 5.0, fill="#FFFFFF", stroke="#4A4F4B", sw=0.9)

    # 窗：外墙上的短双线
    for e in scheme.elements:
        if e.type != "window":
            continue
        g = e.geometry or {}
        w0 = g.get("start") or g.get("p1")
        w1 = g.get("end") or g.get("p2")
        if not (w0 and w1):
            continue
        s.line(px(float(w0[0])), py(float(w0[1])), px(float(w1[0])), py(float(w1[1])),
               stroke="#2F6FB2", sw=3.2)

    # 右栏：图例与指标
    rx = margin_l + W + 36
    s.text(rx, margin_t + 6, "图例", size=12.5, weight="600", color="#1E2328")
    used: List[str] = []
    for sp in rooms:
        if sp.use not in used:
            used.append(sp.use)
    for i, use in enumerate(used[:9]):
        y = margin_t + 30 + i * 24
        s.rect(rx, y - 9, 16, 12, fill=USE_FILL.get(use, "#F1EFE8"),
               stroke="#4A4F4B", sw=0.8, rx=0)
        s.text(rx + 24, y, USE_LABEL.get(use, use), size=10.5, color="#3C443E")

    my = margin_t + 30 + min(len(used), 9) * 24 + 20
    s.text(rx, my, "指标", size=12.5, weight="600", color="#1E2328")
    rows = [("房间数", f"{len(rooms)}"),
            ("使用面积", f"{sum(x.area_m2 for x in rooms):,.0f} m²"),
            ("走廊面积", f"{float(scheme.metrics.get('corridor_area_m2') or 0):,.0f} m²"),
            ("走廊占比", f"{float(scheme.metrics.get('corridor_ratio') or 0):.0%}"),
            ("外窗", f"{scheme.metrics.get('window_count', 0)} 扇"),
            ("采光房间", f"{scheme.metrics.get('daylight_rooms_served', '—')}")]
    for i, (k, v) in enumerate(rows):
        y = my + 26 + i * 22
        s.text(rx, y, k, size=10.5, color="#6B7280")
        s.text(rx + 84, y, v, size=10.5, color="#1E2328")

    # 指北 + 比例尺（按像素换算真实长度）
    nx, ny = margin_l + W - 24, margin_t - 28
    s.polygon([(nx, ny - 18), (nx - 7, ny + 6), (nx, ny + 1), (nx + 7, ny + 6)],
              fill="#1E2328", stroke="#1E2328", sw=0.8)
    s.text(nx, ny + 20, "N", size=10, color="#1E2328", anchor="middle")
    bar_m = 5.0
    bar_px = bar_m * 1000 * scale
    bx, by = margin_l, margin_t + H + 34
    s.rect(bx, by, bar_px, 6, fill="#1E2328", stroke="#1E2328", sw=0.8, rx=0)
    s.text(bx, by + 22, f"0 ——— {bar_m:.0f} m（按图换算）", size=10, color="#6B7280")

    s.text(margin_l, margin_t + H + 84,
           "方案深度：房间面积与关系可讨论；不含尺寸链、轴线、构造与机电。",
           size=10.5, color="#6B7280")
    return s.render()


__all__ = ["USE_FILL", "USE_LABEL", "plan_svg"]
