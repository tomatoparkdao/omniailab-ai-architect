"""概念主图版：一页只放一个体块，字少、图大。

为什么还画图
------------
现有 `concept-diagrams` 是 A4 式的分析图：信息全、字小，缩到 16:9 的页面上
就不可读了。客户在概念阶段要看的其实是**一张大图**——体块怎么落在场地上、
院子在哪、入口从哪进。这张图不需要十个标注，只需要三条。

所以这里出的是"版画"而不是"分析图"：一个 1280×660 的画布，一个体块，
三条大字标注（15 px），一行免责。图形仍然由 `concept/iso.py` 确定性绘制，
不是生成式图像，因此可以放心印在提案里。

五种空间家族各一套组合（线性／分层／组团／围合／中庭大厅），来自
`concept/prototypes.py` 的 `family`，不另建风格系统。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import diagrams as dia
from . import iso as iso_mod
from .iso import Iso, draw_box, draw_ground, draw_shadow, tree

W, H = 1280, 560

#: 家族 → 体块组合（x, y, z, w, d, h；单位 m）。同一家族的差异只在比例，
#: 不是换一种配色——客户看到的两张图必须能一眼看出"组织方式不同"。
MASSING: Dict[str, Tuple[Tuple[float, float, float, float, float, float], ...]] = {
    "linear": ((8, 9, 0, 40, 9, 7), (8, 25, 0, 40, 9, 7), (8, 18, 0, 7, 7, 7)),
    "layered": ((12, 5, 0, 34, 8, 9.5), (15, 14, 0, 30, 8, 6.5), (18, 23, 0, 24, 8, 3.6)),
    "cluster": ((9, 5, 0, 15, 13, 7), (28, 5, 0, 16, 9, 7),
                (9, 23, 0, 11, 12, 4.2), (24, 18, 0, 20, 14, 7)),
    "radial": ((15, 4, 0, 26, 7, 6), (15, 30, 0, 26, 7, 6),
               (6, 12, 0, 7, 17, 6), (43, 12, 0, 7, 17, 6)),
    "hall": ((9, 5, 0, 38, 8, 5), (9, 27, 0, 38, 8, 5), (12, 15, 0, 32, 11, 9)),
}

FAMILY_CN = {"linear": "线性", "layered": "分层", "cluster": "组团",
             "radial": "围合", "hall": "中庭大厅"}


def _short(text: Any, n: int = 18) -> str:
    """切短句：优先在标点处断，且不把括号与数字切一半。"""
    s = " ".join(str(text or "").replace("；", "，").split())
    for sep in ("，", "。", "——"):
        head = s.split(sep)[0]
        if 4 <= len(head) <= n:
            return head
    cut = s[:n]
    for ch in ("（", "(", "、"):
        if cut.count(ch) > s[:n].count("）") and ch in ("（", "("):
            cut = cut.split(ch)[0]
    return cut.rstrip("，、（(")


def hero_plate(concept: Dict[str, Any], *, title: str = "",
               family: str = "", width: int = W, height: int = H,
               heading: bool = True, footer: bool = True, annotate: bool = True,
               note: str = "自有图解 · 体块关系示意，非按比例") -> str:
    """Return the SVG for one concept plate. Empty string when nothing to draw."""
    proto = concept.get("spatial_prototype") or {}
    fam = family or str(proto.get("family") or "cluster")
    boxes = MASSING.get(fam) or MASSING["cluster"]
    s = dia.Svg(width, height, title=f"{concept.get('concept_name', '')} · 体块关系",
                subtitle=str(concept.get("concept_statement") or ""))

    # 场地范围（m）。投影尺度按可用图幅反算，图不裁边、不缩小到看不见。
    SX0, SY0, SX1, SY1 = 0.0, -2.0, 60.0, 50.0
    # 不写标注时，模型占满整幅；写标注时留右侧 340 px 给三条大字。
    right = 806.0 if annotate else float(width) - 48.0
    area = (40.0, 92.0, right, float(height) - 62.0)
    span_x = ((SX1 - SY0) - (SX0 - SY1)) * iso_mod.COS30
    span_y = ((SX1 + SY1) - (SX0 + SY0)) * iso_mod.SIN30
    sc = min((area[2] - area[0]) / max(span_x, 1e-6),
             (area[3] - area[1]) / max(span_y, 1e-6))
    ox = area[0] - (SX0 - SY1) * iso_mod.COS30 * sc
    oy = area[1] - (SX0 + SY0) * iso_mod.SIN30 * sc
    iso = Iso(ox, oy, scale=sc, z_scale=sc)

    # 1) 场地
    draw_ground(iso, s, SX0, SY0, SX1 - SX0, SY1 - SY0, fill="#F1EFE7",
                edge=dia.C_RULE, grid=0)
    # 2) 院子/广场（先铺地，再立体块，否则色块会盖住房子）
    if fam == "linear":
        court = (9, 18.6, 38, 6)
    elif fam == "cluster":
        court = (20, 5.5, 7, 12)
    elif fam == "radial":
        court = (14, 12, 27, 17)
    else:
        court = (0, 0, 0, 0)
    if court[2] > 0:
        s.polygon(iso.pts([(court[0], court[1], 0.06),
                           (court[0] + court[2], court[1], 0.06),
                           (court[0] + court[2], court[1] + court[3], 0.06),
                           (court[0], court[1] + court[3], 0.06)]),
                  fill="#EFE2D0", stroke="none", sw=0)
    # 3) 入口铺装
    s.polygon(iso.pts([(25, 44, 0.05), (35, 44, 0.05), (35, 49, 0.05), (25, 49, 0.05)]),
              fill="#E8DFCC", stroke="none", sw=0)
    # 4) 体块：画家算法排序，远的先画
    for x, y, z, w, d, h in sorted(boxes, key=lambda b: b[0] + b[1]):
        draw_shadow(iso, s, x, y, w, d, opacity=0.09)
        draw_box(iso, s, x, y, z, w, d, h, fill="#E3EBE2", edge=dia.C_INK, sw=1.1)
    # 5) 种植与尺度人物
    for tx, ty in ((3, 0), (55, 2), (2, 40), (56, 40), (31, 41.5)):
        tree(iso, s, tx, ty, r=1.15, h=2.4)
    for px, py in ((29, 46), (33, 45.2), (10, 12)):
        x1, y1 = iso.p(px, py, 0)
        s.circle(x1, y1, 2.2, fill=dia.C_INK)
        s.line(x1, y1, x1, y1 - 10, stroke=dia.C_INK, sw=1.5)
    ax, ay = iso.p(30, 50.5, 0)
    bx, by = iso.p(30, 45.6, 0)
    s.line(ax, ay, bx, by, stroke=dia.C_ACCENT, sw=2.0, arrow=True)
    s.text(ax, ay + 15, "入口", size=12, color=dia.C_ACCENT, anchor="middle")

    # 6) 三条大字（右侧），每条一根引线。不写标注时模型占满整幅。
    if annotate:
        _annotations(s, proto, x0=902.0, y0=148.0, step=108.0)
    if heading:
        s.text(44, 44, str(title or concept.get("concept_name") or "体块关系"),
               size=22, weight="600")
        s.text(44, 68, f"{FAMILY_CN.get(fam, '组团')}式组织 · {concept.get('concept_id', '')}",
               size=11, color=dia.C_MUTED)
    iso_mod.north_arrow(s, 50, height - 86, size=18, color=dia.C_MUTED)
    iso_mod.scale_bar(s, 84, height - 58, 104, unit="m", seg_m=10.0, segments=2,
                      color=dia.C_MUTED, note="示意" if not annotate else "示意")
    if footer:
        s.text(40, height - 16, note, size=9, color=dia.C_MUTED)
    if footer:
        s.text(width - 40, height - 16, "OmniAiLab 自有图解", size=9,
               color=dia.C_MUTED, anchor="end")
    return s.render()


def _annotations(s: Any, proto: Dict[str, Any], *, x0: float = 902.0,
                 y0: float = 148.0, step: float = 108.0) -> None:
    """右栏三条大字：分区／动线／采光。三种图版共用同一套标注。"""
    items = [("分区", proto.get("zoning")),
             ("动线", proto.get("circulation")),
             ("采光", proto.get("daylight"))]
    for i, (label, text) in enumerate(items):
        yy = y0 + i * step
        s.line(x0 - 66, yy - 5, x0 - 10, yy - 5, stroke=dia.C_RULE, sw=1.0)
        s.circle(x0 - 66, yy - 5, 2.0, fill=dia.C_RULE, stroke="none")
        s.text(x0, yy, f"{i + 1:02d}  {label}", size=11.5, color=dia.C_ACCENT,
               weight="600")
        s.text(x0, yy + 26, _short(text, 13), size=18, weight="500")
        rest = str(text or "").split("；")
        s.text(x0, yy + 50, _short(rest[-1] if len(rest) > 1 else text, 22), size=11.5,
               color=dia.C_MUTED)


#: 景观图版的三种游线（家族 → 环形 / 折线 / 直进）
LOOP = {"courtyard": "ring", "layered": "terrace", "cluster": "grove",
        "linear": "axis", "radial": "ring", "hall": "ring", "grid": "axis"}


def plan_plate(concept: Dict[str, Any], *, discipline: str = "landscape",
               width: int = 1200, height: int = 496, annotate: bool = True,
               heading: bool = False, footer: bool = True,
               note: str = "自有图解 · 空间关系示意，非按比例") -> str:
    """景观／室内的**平面图版**：从上往下看，不是体块。

    景观项目画房子、室内项目画总平面，是这类汇报最容易犯的错：
    客户看到的图必须是他委托的那件事——院子就是院子，标准层就是标准层。
    """
    proto = concept.get("spatial_prototype") or {}
    fam = str(proto.get("family") or "cluster")
    s = dia.Svg(width, height, title=f"{concept.get('concept_name', '')} · 平面关系")

    x0, y0 = 56.0, 96.0
    w = (width - 400.0) if annotate else (width - 112.0)
    h = height - 210.0
    # 场地/楼板：一张纸就够了，不画多余的边框
    s.rect(x0, y0, w, h, fill="#F1EFE7", stroke=dia.C_RULE, sw=1.0)

    if discipline == "interior":
        # 标准层：两排客房 + 中间走廊 + 一端公共核 + 一端后场
        bh = h * 0.30
        s.rect(x0, y0, w * 0.80, bh, fill="#E7EDE6", stroke=dia.C_INK, sw=1.0)
        s.rect(x0, y0 + h - bh, w * 0.80, bh, fill="#E7EDE6", stroke=dia.C_INK, sw=1.0)
        s.rect(x0, y0 + h / 2 - 14, w * 0.80, 28, fill="#FBFAF5",
               stroke=dia.C_RULE, sw=1.0)
        # 端部一分为二：上半公共核（电梯厅/服务台），下半后场（布草/后勤）
        nx = x0 + w * 0.80
        nw = w * 0.20
        s.rect(nx, y0 + h * 0.46, nw, h * 0.54, fill="#E3DED1",
               stroke=dia.C_INK, sw=1.0)
        s.rect(nx, y0, nw, h * 0.46, fill="#EAE6DC", stroke=dia.C_INK, sw=1.0)
        s.text(x0 + 14, y0 + bh / 2 + 5, "客房带", size=12, color=dia.C_MUTED)
        s.text(x0 + 14, y0 + h - bh / 2 + 5, "客房带", size=12, color=dia.C_MUTED)
        s.text(x0 + w * 0.34, y0 + h / 2 + 4, "客房走廊", size=11, color=dia.C_MUTED)
        s.text(nx + 12, y0 + 26, "公共核", size=12, color=dia.C_MUTED)
        s.text(nx + 12, y0 + 48, "电梯厅 / 服务台", size=10, color=dia.C_MUTED)
        s.text(nx + 12, y0 + h * 0.46 + 26, "后场", size=12, color=dia.C_MUTED)
        s.text(nx + 12, y0 + h * 0.46 + 48, "布草 / 后勤通道", size=10, color=dia.C_MUTED)
        # 后场独立成块，客人走廊不穿进去（两块之间就是后勤通道的边界）
        s.line(x0 - 26, y0 + h / 2, x0 - 4, y0 + h / 2, stroke=dia.C_ACCENT,
               sw=2.0, arrow=True)
        s.text(x0 - 28, y0 + h / 2 + 18, "入口", size=11, color=dia.C_ACCENT)
    else:
        # 景观：水面 + 环路 + 种植 + 节点
        loop = LOOP.get(fam, "ring")
        # 建筑边界：院子必须有房子作参照，否则看不出朝向与尺度
        s.rect(x0 + w * 0.06, y0 + h * 0.02, w * 0.20, h * 0.14,
               fill="#E9E4D6", stroke=dia.C_INK, sw=1.0)
        s.text(x0 + w * 0.06 + 8, y0 + h * 0.02 + 18, "建筑", size=10.5,
               color=dia.C_MUTED)
        cx, cy = x0 + w * 0.56, y0 + h * 0.52
        rw, rh = w * 0.17, h * 0.24
        s.polygon([[cx + rw * _cos(i, 14), cy + rh * _sin(i, 14)] for i in range(14)],
                  fill="#DDE7EE", stroke="#9FB3BF", sw=1.0)
        s.text(cx, cy + 4, "水面", size=12, color="#5E7484", anchor="middle")
        if loop == "ring":
            ring = [[cx + rw * 1.55 * _cos(i, 28), cy + rh * 1.5 * _sin(i, 28)]
                    for i in range(28)]
            s.polygon(ring, fill="none", stroke="#D3C9B2", sw=7.0)
            s.polygon(ring, fill="none", stroke="#B3A88D", sw=1.0, dash="10 8")
        elif loop == "terrace":
            for i in range(3):
                s.line(x0 + 24, y0 + h * (0.28 + i * 0.18),
                       x0 + w * 0.36, y0 + h * (0.28 + i * 0.18),
                       stroke="#B9AE95", sw=8.0)
        else:
            s.line(x0 + 26, y0 + h * 0.80, cx, cy, stroke="#B9AE95", sw=9.0)
            s.line(cx, cy, x0 + w - 26, y0 + h * 0.22, stroke="#B9AE95", sw=9.0)
        for tx, ty, tr in ((x0 + w * 0.30, y0 + h * 0.86, 20.0),
                           (x0 + w * 0.09, y0 + h * 0.52, 24.0),
                           (x0 + w * 0.88, y0 + h * 0.20, 22.0),
                           (x0 + w * 0.92, y0 + h * 0.80, 19.0),
                           (cx + rw * 1.95, cy + rh * 0.45, 17.0)):
            s.circle(tx, ty, tr, fill="#DCE6D3", stroke="#8FA684", sw=1.0)
        s.rect(x0 + w * 0.30, y0 + h * 0.06, w * 0.16, h * 0.10,
               fill="#E6DFCE", stroke="none", sw=0)
        s.text(x0 + w * 0.30 + 8, y0 + h * 0.06 + 20, "茶座 / 节点", size=11,
               color=dia.C_MUTED)
        s.line(x0 + w * 0.5, y0 + h + 26, x0 + w * 0.5, y0 + h + 4,
               stroke=dia.C_ACCENT, sw=2.0, arrow=True)
        s.text(x0 + w * 0.5, y0 + h + 44, "主入口", size=11, color=dia.C_ACCENT,
               anchor="middle")

    if annotate:
        _annotations(s, proto, x0=x0 + w + 44.0, y0=150.0, step=104.0)
    if heading:
        s.text(44, 44, str(concept.get("concept_name") or ""), size=22, weight="600")
    iso_mod.north_arrow(s, x0 + 6, height - 96, size=16, color=dia.C_MUTED)
    iso_mod.scale_bar(s, x0 + 44, height - 66, 104, unit="m", seg_m=5.0, segments=2,
                      color=dia.C_MUTED, note="示意")
    if footer:
        s.text(40, height - 16, note, size=9, color=dia.C_MUTED)
        s.text(width - 40, height - 16, "OmniAiLab 自有图解", size=9,
               color=dia.C_MUTED, anchor="end")
    return s.render()


def _cos(i: int, n: int) -> float:
    import math

    return math.cos(2 * math.pi * i / n)


def _sin(i: int, n: int) -> float:
    import math

    return math.sin(2 * math.pi * i / n)


#: 四步演变：每一步体块加到哪。索引对应 MASSING 里前 n 个块。
STEP_TITLES = ("场地", "首选体量", "加入组团", "形成院落")


def steps_plate(concept: Dict[str, Any], *, family: str = "", width: int = 700,
                height: int = 486) -> str:
    """四步演变，**按目标尺寸画**：只有序号与体块，字少到缩图也可读。

    原来的 `diagrams.massing()` 是 A4 分析图（自带标题、注释、图例），
    缩进提案里只剩一团灰。这里只画形，文字由页面自己排。
    """
    proto = concept.get("spatial_prototype") or {}
    fam = family or str(proto.get("family") or "cluster")
    boxes = list(MASSING.get(fam) or MASSING["cluster"])
    s = dia.Svg(width, height, title=f"{concept.get('concept_name', '')} · 体块演变")
    cell = width / 4.0
    # 场地按体块包围盒取景（外扩 5 m）：固定 56×44 的场地会让体块缩成一小坨
    bx0 = min(b[0] for b in boxes) - 5.0
    by0 = min(b[1] for b in boxes) - 5.0
    bx1 = max(b[0] + b[3] for b in boxes) + 5.0
    by1 = max(b[1] + b[4] for b in boxes) + 5.0
    for i in range(4):
        n = min(len(boxes), i + 1)
        sub = sorted(boxes[:n], key=lambda b: b[0] + b[1])
        x0 = i * cell + 8
        x1 = (i + 1) * cell - 12
        SX0, SY0, SX1, SY1 = bx0, by0, bx1, by1
        span_x = ((SX1 - SY0) - (SX0 - SY1)) * iso_mod.COS30
        span_y = ((SX1 + SY1) - (SX0 + SY0)) * iso_mod.SIN30
        sc = min((x1 - x0) / max(span_x, 1e-6),
                 (height - 96.0) / max(span_y, 1e-6))
        iso = Iso(x0 - (SX0 - SY1) * iso_mod.COS30 * sc,
                  52.0 - (SX0 + SY0) * iso_mod.SIN30 * sc, scale=sc, z_scale=sc)
        draw_ground(iso, s, SX0, SY0, SX1 - SX0, SY1 - SY0, fill="#F3F1E9",
                    edge=dia.C_RULE, grid=0)
        # 第 4 步补一块院落铺地，表示"围合完成"
        if i >= 2:
            cx = bx0 + (bx1 - bx0) * 0.34
            cy = by0 + (by1 - by0) * 0.30
            cw, cd = (bx1 - bx0) * 0.26, (by1 - by0) * 0.22
            s.polygon(iso.pts([(cx, cy, 0.06), (cx + cw, cy, 0.06),
                               (cx + cw, cy + cd, 0.06), (cx, cy + cd, 0.06)]),
                      fill="#EFE2D0", stroke="none", sw=0)
        for x, y, z, w, d, h in sub:
            draw_shadow(iso, s, x, y, w, d, opacity=0.08)
            draw_box(iso, s, x, y, z, w, d, h, fill="#E4EBE2", edge=dia.C_INK, sw=1.0)
        s.text(x0 + 2, height - 34, f"0{i + 1}", size=13.0, color=dia.C_ACCENT,
               weight="600")
        s.text(x0 + 30, height - 34, STEP_TITLES[i] if i < len(STEP_TITLES) else "",
               size=11.0, color=dia.C_MUTED)
        if i < 3:
            s.line(x1 + 2, height - 40, x1 + 10, height - 40, stroke=dia.C_RULE,
                   sw=1.0, arrow=True)
    return s.render()


def write(concept: Dict[str, Any], out_dir: str | Any, *, family: str = "",
          stem: str = "", heading: bool = True, footer: bool = True,
          annotate: bool = True, width: int = W, height: int = H,
          discipline: str = "architecture") -> str:
    """落盘一张主图版。

    `width/height` 必须**等于版面上要放的像素尺寸**：图里的字是固定 px 的，
    1280×560 的图缩到 800×452 放，11.5 px 的标注就变成 7 px，等于没写。
    """
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = stem or f"plate-{concept.get('concept_id', 'x').lower()}"
    path = out / f"{name}.svg"
    if discipline in ("interior", "landscape"):
        svg = plan_plate(concept, discipline=discipline, width=width, height=height,
                         annotate=annotate, heading=False, footer=footer)
    else:
        svg = hero_plate(concept, family=family, heading=heading, footer=footer,
                         annotate=annotate, width=width, height=height,
                         title=str(concept.get("concept_name") or ""))
    if not svg:
        return ""
    path.write_text(svg, encoding="utf-8")
    return str(path)


def write_steps(concept: Dict[str, Any], out_dir: str | Any, *, family: str = "",
                stem: str = "", width: int = 700, height: int = 486) -> str:
    """四步演变图落盘（尺寸由页面决定，这里按调用方给的画布画）。"""
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = stem or f"steps-{concept.get('concept_id', 'x').lower()}"
    path = out / f"{name}.svg"
    svg = steps_plate(concept, family=family, width=width, height=height)
    if not svg:
        return ""
    path.write_text(svg, encoding="utf-8")
    return str(path)


__all__ = ["FAMILY_CN", "LOOP", "MASSING", "STEP_TITLES", "hero_plate", "plan_plate",
           "steps_plate", "write", "write_steps"]
