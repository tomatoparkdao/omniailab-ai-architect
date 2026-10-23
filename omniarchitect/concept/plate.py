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
from . import layout as layout_mod
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
                 y0: float = 148.0, step: float = 108.0,
                 scale: float = 1.0, width: float = 240.0) -> None:
    """右栏三条大字：分区／动线／采光。三种图版共用同一套标注。

    大字的第二行只写**另一句**。原文只有一句时，第二行不写——
    否则同一句会上下各印一遍（酒店那版"裙房 2 层做公共核"就是这样重复的）。
    """
    items = [("分区", proto.get("zoning")),
             ("动线", proto.get("circulation")),
             ("采光", proto.get("daylight"))]
    for i, (label, text) in enumerate(items):
        yy = y0 + i * step
        s.line(x0 - 66, yy - 5, x0 - 10, yy - 5, stroke=dia.C_RULE, sw=1.0)
        s.circle(x0 - 66, yy - 5, 2.0, fill=dia.C_RULE, stroke="none")
        s.text(x0, yy, f"{i + 1:02d}  {label}", size=11.5 * scale,
               color=dia.C_ACCENT, weight="600")
        head = _short(text, int(13 * width / 240.0))
        s.text(x0, yy + 26 * scale, head, size=18 * scale, weight="500")
        rest = [x for x in str(text or "").split("；") if x.strip()]
        tail = _short(rest[-1], int(20 * width / 240.0)) if len(rest) > 1 else ""
        if tail and tail != head and len(tail) > len(head):
            s.text(x0, yy + 50 * scale, tail, size=11.5 * scale, color=dia.C_MUTED)


#: 图例：图上真正画了什么就只列什么。没画的东西不进图例——
#: 客户照着图例找水面，图上却没有，比不写图例更糟。
LEGEND_REGION: Dict[str, Tuple[str, str]] = {
    "water": ("水面", "water"), "creek": ("旱溪", "creek"),
    "terrace": ("台地", "terrace"), "green": ("种植", "green"),
    "paving": ("铺装", "paving"), "stone": ("整石", "paving"),
    "building": ("建筑", "building"), "mass": ("房间", "mass"),
    "private": ("私密区", "mass"), "mass2": ("公共区", "mass2"),
    "public": ("公共区", "mass2"), "service": ("后场", "service"),
    "core": ("核心", "core"), "circulation": ("通道", "paving"),
    "counter": ("服务台", "paper"),
}

LEGEND_LINK: Dict[str, Tuple[str, str]] = {
    "path": ("园路", "path"), "flow": ("客流", "accent"),
    "service": ("服务流", "muted"), "sight": ("视线", "line"),
}


def legend_items(frame: Any) -> Tuple[List[str], List[str]]:
    """图例条目：（功能块, 线型），按图里实际出现的种类给，不补不猜。"""
    kinds: List[str] = []
    for r in frame.regions:
        if r.kind in LEGEND_REGION and r.kind not in kinds:
            kinds.append(r.kind)
    links: List[str] = []
    for lk in frame.links:
        if lk.kind in LEGEND_LINK and lk.kind not in links:
            links.append(lk.kind)
    return ([LEGEND_REGION[k][0] for k in kinds],
            [LEGEND_LINK[k][0] for k in links])


def _legend(s: Any, frame: Any, *, x0: float, y0: float, width: float,
            row: float = 26.0) -> None:
    """图例：一行功能块、一行线型。"""
    kinds: List[str] = []
    for r in frame.regions:
        if r.kind in LEGEND_REGION and r.kind not in kinds:
            kinds.append(r.kind)
    links: List[str] = []
    for lk in frame.links:
        if lk.kind in LEGEND_LINK and lk.kind not in links:
            links.append(lk.kind)

    for i, (keys, table) in enumerate(((kinds, LEGEND_REGION), (links, LEGEND_LINK))):
        x = x0
        yy = y0 + i * row
        for k in keys[:6]:
            text, pal_key = table[k]
            cw = 18.0
            if i == 0:
                s.rect(x, yy - 8, cw, 10, fill=layout_mod.PAL[pal_key],
                       stroke=layout_mod.PAL["line"], sw=0.8)
            else:
                s.line(x, yy - 3, x + cw, yy - 3,
                       stroke=layout_mod.PAL[pal_key], sw=1.4,
                       dash=(3, 3) if k == "sight" else ())
            s.text(x + cw + 7, yy, text, size=9.5, color=dia.C_MUTED)
            x += cw + 7 + layout_mod._tw(text, 9.5) + 20
            if x > x0 + width - 60:
                break


#: 景观图版的三种游线（家族 → 环形 / 折线 / 直进）
LOOP = {"courtyard": "ring", "layered": "terrace", "cluster": "grove",
        "linear": "axis", "radial": "ring", "hall": "ring", "grid": "axis"}


def plan_plate(concept: Dict[str, Any], *, discipline: str = "landscape",
               width: int = 1200, height: int = 496, annotate: bool = True,
               heading: bool = False, footer: bool = True,
               sector: str = "",
               note: str = "自有图解 · 空间关系示意，非按比例") -> str:
    """景观／室内的**平面图版**：从上往下看，不是体块。

    几何全部来自 `concept/layout.py`——四步推敲图用的是同一份数据，
    所以主推图上的大堂、走廊、茶座在两张图里必然在同一个位置。

    两幅图（裙房公共层 / 客房标准层）时不放右栏大字：图比字重要，
    而且两幅并排后右栏会把每幅压到 340 px，标签就看不清了。
    """
    frs = layout_mod.frames(concept, discipline, sector=sector)
    if not frs:
        return ""
    two = len(frs) > 1 and width >= 900
    if not two:
        frs = frs[:1]
    if two:
        annotate = False
    compact = width < 900
    pal = dict(layout_mod.PAL)
    s = dia.Svg(width, height, title=f"{concept.get('concept_name', '')} · 平面关系")

    x0 = 56.0
    # 图面比例跟着专业走：庭院是近方形的场地，楼层是长条。
    # 把庭院塞进 800×270 的横条里，环路会被压成一条扁椭圆，"环形游线"就不成立。
    if two:
        y0, h = 120.0, height - 236.0
        w = width - 112.0
        gap = 30.0
        fw = (w - gap) / 2.0
        boxes = [(x0 + i * (fw + gap), y0, fw, h) for i in range(2)]
    elif annotate:
        y0, h = 96.0, min(330.0, height - 166.0)
        # 单幅平面 + 右栏：整块居中。贴左边放，1200 px 的板子右边会剩一大条空白，
        # 看着像画到一半停了。居中之后左右留白对等，是版面的呼吸，不是没排完。
        fig_w = h * 1.28
        rail_w = 340.0
        x0 = max(x0, (width - (fig_w + 54.0 + rail_w)) / 2.0)
        boxes = [(x0, y0, fig_w, h)]
    else:
        y0, h = 100.0, height - 226.0
        boxes = [(x0, y0, width - 112.0, h)]

    reports: List[Tuple[Any, Dict[str, Any]]] = []
    for fr, bx in zip(frs, boxes):
        rep: Dict[str, Any] = {}
        layout_mod.draw(s, fr, bx, pal, label_size=9.5 if compact else 10.5,
                        detail=not compact, report=rep)
        reports.append((fr, rep))

    # 图题与图注：图注只在"这不是排房图"或"数据自相矛盾"时出现。
    # 每张图都印一句免责声明等于没说，反而把真问题埋掉。
    for fr, bx in zip(frs, boxes):
        if fr.note:
            if fr.title:
                s.text(bx[0] + 1, bx[1] - 24, fr.title, size=10.5, color=dia.C_MUTED,
                       weight="600")
            s.text(bx[0] + 1, bx[1] - 9, fr.note, size=9.5, color=dia.C_MUTED)
        elif fr.title:
            s.text(bx[0] + 1, bx[1] - 9, fr.title, size=10.5, color=dia.C_MUTED,
                   weight="600")

    if annotate:
        bx = boxes[0]
        ax = bx[0] + bx[2] + 54.0
        aw = rail_w
        # 一道竖线把右栏绑成一条 rail：没有它，图右上就是一块空白，
        # 客户会以为排版没做完。
        rail_top = y0 + 30.0
        rail_bot = y0 + 44.0 + 3 * 96.0 + 30.0
        s.line(ax - 26.0, rail_top, ax - 26.0, rail_bot, stroke=dia.C_RULE, sw=1.0)
        _annotations(s, concept.get("spatial_prototype") or {},
                     x0=ax, y0=y0 + 44.0, step=96.0,
                     scale=1.24, width=aw)
        # 右栏如果只有三行短句，1200 px 的板子右边会空掉一大块，看着像没排完。
        # 补一条图例：它本来就该有（客户分不清水面与铺装是常事），
        # 而且只列图上真画了的东西。
        _legend(s, frs[0], x0=ax, y0=y0 + 44.0 + 3 * 96.0 + 4.0, width=aw)
    if heading:
        s.text(44, 44, str(concept.get("concept_name") or ""), size=22, weight="600")

    # 放不下的标注必须留痕：图可以少一个标注，但不能假装画全了。
    lost: List[str] = []
    for _, rep in reports:
        for t in rep.get("missing") or []:
            if t not in lost:
                lost.append(t)

    # 底部只留一条基线：比例尺（含数字）压在页脚之上，谁也不许压到谁。
    # 上一版把比例尺固定在框下 34 px，496 高的图里比例尺数字掉到画布外、
    # 和页脚叠在一起——图上看着像印刷事故。
    bar_y = height - 50.0
    iso_mod.north_arrow(s, x0 + 6, bar_y - 8, size=14, color=dia.C_MUTED)
    iso_mod.scale_bar(s, x0 + 44, bar_y, 104, unit="m", seg_m=5.0, segments=2,
                      color=dia.C_MUTED, note="示意")
    if footer:
        # 放不下的标注与图注同一行，不另起一行抢位置——但必须写出来。
        tail = str(note or "")
        if lost:
            tail += ("　｜　" if tail else "") + "未放置标注：" + "、".join(lost)
        s.text(40, height - 16, tail, size=9, color=dia.C_MUTED)
        s.text(width - 40, height - 16, "OmniAiLab 自有图解", size=9,
               color=dia.C_MUTED, anchor="end")
    elif lost:
        s.text(40, height - 16, "未放置标注：" + "、".join(lost), size=9,
               color=dia.C_MUTED)
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


#: 各专业的图注。图是"体块"还是"平面"不能写错——庭院的主图不会画体块。
NOTE_BY_DISCIPLINE = {
    "interior": "自有图解 · 功能与流线示意，非按比例",
    "landscape": "自有图解 · 场地与游线示意，非按比例",
    "architecture": "自有图解 · 体块关系示意，非按比例",
}


def write(concept: Dict[str, Any], out_dir: str | Any, *, family: str = "",
          stem: str = "", heading: bool = True, footer: bool = True,
          annotate: bool = True, width: int = W, height: int = H,
          discipline: str = "architecture", sector: str = "") -> str:
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
                         annotate=annotate, heading=False, footer=footer,
                         sector=sector,
                         note=NOTE_BY_DISCIPLINE.get(discipline, ""))
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


__all__ = ["legend_items", "FAMILY_CN", "LOOP", "MASSING", "STEP_TITLES", "hero_plate", "plan_plate",
           "steps_plate", "write", "write_steps"]
