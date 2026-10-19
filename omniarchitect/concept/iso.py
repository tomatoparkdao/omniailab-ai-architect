"""等距投影与体块着色：让"体量"真的像个体量。

为什么要单独一层
----------------
概念阶段最有说服力的图不是平面，而是**体块**：一个 L 形体量退台之后，第三层
露出来的平台朝向哪、临街那面实到什么程度、院是切进去的还是围出来的。这些
判断在俯视矩形里读不出来——矩形没有高度，也就没有明暗、没有遮挡、没有前后。

所以这里只做三件事，别的都不做：

1. **等距投影**：世界坐标 (x, y, z) → 图面坐标，30° 轴测，与建筑惯用的
   isometric 一致，尺度可度量（v 轴与 h 轴同比例，不缩放）。
2. **面法向着色**：同一个体块的顶面、两个可见侧面分三档明度。没有明暗的体块
   看起来像贴纸，业主也判断不出哪个面朝街。
3. **画家算法排序**：按 `x + y` 由远及近绘制，保证后画的体块压住前面的。

这里**不出尺寸**。图中所有长度都是"相对关系"，图注统一写"非按比例"。
定位要精确的地方（开间、进深、层高）由 S3/S4 的图纸负责，不由概念图负责。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .diagrams import Svg

COS30 = math.cos(math.radians(30.0))
SIN30 = 0.5

Point = Tuple[float, float]


# --------------------------------------------------------------------------
# 颜色
# --------------------------------------------------------------------------
def _rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def shade(hex_color: str, factor: float) -> str:
    """`factor` < 1 压暗，> 1 提亮（向白靠）。保持色相，只改明度。"""
    r, g, b = _rgb(hex_color)
    if factor <= 1.0:
        out = (r * factor, g * factor, b * factor)
    else:
        t = min(1.0, factor - 1.0)
        out = (r + (255 - r) * t, g + (255 - g) * t, b + (255 - b) * t)
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, int(round(v)))) for v in out))


def mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _rgb(a)
    br, bg, bb = _rgb(b)
    t = max(0.0, min(1.0, t))
    return "#{:02X}{:02X}{:02X}".format(
        int(round(ar + (br - ar) * t)),
        int(round(ag + (bg - ag) * t)),
        int(round(ab + (bb - ab) * t)))


# --------------------------------------------------------------------------
# 投影
# --------------------------------------------------------------------------
class Iso:
    """World (x, y, z) → sheet (sx, sy).

    `x` 向东、`y` 向北、`z` 向上。原点在构造函数给的图面位置：所有坐标都是
    **图面像素**，调用方先用 `fit()` 把米的尺度换算成像素再传进来。
    """

    def __init__(self, ox: float, oy: float, scale: float = 26.0,
                 z_scale: Optional[float] = None) -> None:
        self.ox, self.oy = ox, oy
        self.s = float(scale)
        self.zs = float(z_scale if z_scale is not None else self.s)

    def p(self, x: float, y: float, z: float = 0.0) -> Point:
        sx = self.ox + (x - y) * COS30 * self.s
        sy = self.oy + (x + y) * SIN30 * self.s - z * self.zs
        return sx, sy

    def pts(self, coords: Iterable[Tuple[float, float, float]]) -> List[Point]:
        return [self.p(*c) for c in coords]

    def depth(self, x: float, y: float, z: float = 0.0) -> float:
        """Painter's-algorithm key: larger = nearer the viewer = drawn later."""
        return x + y + z * 0.35


#: 三个可见面的明度系数。顶面最亮，+y 面居中，+x 面最暗。
FACE_LIGHT = {"top": 1.30, "front": 1.00, "side": 0.74}


def box_faces(iso: Iso, x: float, y: float, z: float,
              w: float, d: float, h: float) -> Dict[str, List[Point]]:
    """The three faces of an axis-aligned box that the viewer can actually see."""
    x1, y1, z1 = x + w, y + d, z + h
    return {
        "top": iso.pts([(x, y, z1), (x1, y, z1), (x1, y1, z1), (x, y1, z1)]),
        "front": iso.pts([(x, y1, z1), (x1, y1, z1), (x1, y1, z), (x, y1, z)]),
        "side": iso.pts([(x1, y1, z1), (x1, y, z1), (x1, y, z), (x1, y1, z)]),
    }


def draw_box(iso: Iso, s: Svg, x: float, y: float, z: float,
             w: float, d: float, h: float, *, fill: str = "#FFFFFF",
             edge: str = "#1E2328", sw: float = 1.1, opacity: float = 1.0,
             roof: bool = True) -> None:
    """One opaque box with three tonal faces.

    `roof=False` 去掉顶面：用于"剖开"的体量，让读者看见里面的地面与隔墙。
    """
    f = box_faces(iso, x, y, z, w, d, h)
    s.polygon(f["front"], fill=shade(fill, FACE_LIGHT["front"]), stroke=edge,
              sw=sw, opacity=opacity)
    s.polygon(f["side"], fill=shade(fill, FACE_LIGHT["side"]), stroke=edge,
              sw=sw, opacity=opacity)
    if roof:
        s.polygon(f["top"], fill=shade(fill, FACE_LIGHT["top"]), stroke=edge,
                  sw=sw, opacity=opacity)


def draw_shadow(iso: Iso, s: Svg, x: float, y: float, w: float, d: float,
                *, dx: float = 0.55, dy: float = 0.55, opacity: float = 0.10) -> None:
    """Soft footprint offset to the south-east.

    阴影不是装饰：它把体量"钉"在地面上。没有阴影的轴测，读起来像一张剪贴画。
    """
    s.polygon(iso.pts([(x + dx, y + dy, 0), (x + w + dx, y + dy, 0),
                       (x + w + dx, y + d + dy, 0), (x + dx, y + d + dy, 0)]),
              fill="#1E2328", opacity=opacity)


def draw_ground(iso: Iso, s: Svg, x0: float, y0: float, w: float, d: float,
                *, fill: str = "#EFEDE6", edge: str = "#D6D2C6",
                grid: int = 0, grid_color: str = "#DCD8CC") -> None:
    """The base plane. A faint grid gives the model something to sit on."""
    s.polygon(iso.pts([(x0, y0, 0), (x0 + w, y0, 0),
                       (x0 + w, y0 + d, 0), (x0, y0 + d, 0)]),
              fill=fill, stroke=edge, sw=1.0)
    for i in range(1, grid):
        t = i / grid
        s.line(*iso.p(x0 + w * t, y0, 0), *iso.p(x0 + w * t, y0 + d, 0),
               stroke=grid_color, sw=0.6)
        s.line(*iso.p(x0, y0 + d * t, 0), *iso.p(x0 + w, y0 + d * t, 0),
               stroke=grid_color, sw=0.6)


def water_plane(iso: Iso, s: Svg, x: float, y: float, w: float, d: float,
                *, fill: str = "#C3DCE8", line: str = "#8FB6C9") -> None:
    """Water: a cool plane with a few parallel glints, not a flat blue rectangle."""
    s.polygon(iso.pts([(x, y, 0), (x + w, y, 0), (x + w, y + d, 0), (x, y + d, 0)]),
              fill=fill, stroke=line, sw=0.9, opacity=1.0)
    for i in range(1, 5):
        t = i / 5.0
        s.line(*iso.p(x + w * 0.06, y + d * t, 0), *iso.p(x + w * 0.94, y + d * t, 0),
               stroke="#FFFFFF", sw=1.4, dash="10 7")
    s.line(*iso.p(x + w * 0.10, y + d * 0.20, 0), *iso.p(x + w * 0.44, y + d * 0.20, 0),
           stroke="#FFFFFF", sw=2.2)


def tree(iso: Iso, s: Svg, x: float, y: float, *, r: float = 0.55, h: float = 1.9,
         crown: str = "#C6D6BE", trunk: str = "#8A7A63", opacity: float = 1.0) -> None:
    """A tree as a trunk line plus a flattened crown ellipse in plan-iso.

    Earlier this was a flat circle: twelve identical circles read as bullet
    points, not planting. Height and a shadow offset make it read as a tree.
    """
    sx, sy = iso.p(x, y, 0)
    top = iso.p(x, y, h)
    s.line(sx, sy, top[0], top[1], stroke=trunk, sw=1.5 * (iso.s / 26.0))
    rx = r * iso.s * 1.15
    ry = rx * 0.52
    s.ellipse(top[0], top[1], rx, ry, fill=shade(crown, 0.92), stroke=shade(crown, 0.68),
              sw=0.9, opacity=opacity)
    s.ellipse(top[0] - rx * 0.28, top[1] - ry * 0.30, rx * 0.55, ry * 0.48,
              fill=shade(crown, 1.12), stroke="none", opacity=0.75 * opacity)


def canopy_plan(s: Svg, cx: float, cy: float, r: float, *, seed: int = 1,
                fill: str = "#CBDCC2", edge: str = "#A8BF9E", lobes: int = 7,
                shadow: bool = True) -> None:
    """A plan-view tree crown: several overlapping lobes, not one perfect circle.

    景观总平面里的树不是符号，是冠幅。冠幅是不规则的，所以画成簇。
    """
    import math as _m

    if shadow:
        s.ellipse(cx + r * 0.22, cy + r * 0.26, r * 1.02, r * 0.96,
                  fill="#1E2328", opacity=0.07)
    pts_out: List[Tuple[float, float]] = []
    pts_in: List[Tuple[float, float]] = []
    for i in range(lobes * 2):
        ang = (i / (lobes * 2)) * _m.tau
        k = 1.0 + 0.16 * _m.sin(ang * 3 + seed * 1.7) + 0.07 * _m.sin(ang * 5 + seed)
        x = cx + _m.cos(ang) * r * k
        y = cy + _m.sin(ang) * r * k * 0.96
        pts_out.append((x, y))
        ik = 0.52 + 0.10 * _m.sin(ang * 4 + seed)
        pts_in.append((cx + _m.cos(ang) * r * ik, cy + _m.sin(ang) * r * ik * 0.96))
    s.polygon(pts_out, fill=fill, stroke=edge, sw=0.9)
    s.polygon(pts_in, fill=shade(fill, 1.14), stroke="none", opacity=0.85)


def shrub_plan(s: Svg, cx: float, cy: float, r: float, *, fill: str = "#DCE7D2",
               edge: str = "#B7C9AB", seed: int = 1) -> None:
    s.ellipse(cx, cy, r, r * 0.86, fill=fill, stroke=edge, sw=0.7)
    s.ellipse(cx - r * 0.25, cy - r * 0.22, r * 0.45, r * 0.38, fill=shade(fill, 1.10),
              stroke="none", opacity=0.8)


def north_arrow(s: Svg, x: float, y: float, size: float = 30.0,
                color: str = "#1E2328") -> None:
    s.line(x, y + size, x, y - size * 0.55, stroke=color, sw=1.2)
    s.polygon([(x, y - size), (x - size * 0.30, y - size * 0.30),
               (x + size * 0.30, y - size * 0.30)], fill=color)
    s.text(x, y - size * 1.18, "N", size=11, color=color, anchor="middle", weight="600")


def scale_bar(s: Svg, x: float, y: float, width: float, *,
              unit: str = "m", seg_m: float = 5.0, segments: int = 2,
              color: str = "#1E2328", note: str = "示意") -> None:
    """A graphic scale. Ticks are drawn from the same numbers as the segments, so
    the bar can never claim a length its own geometry doesn't have."""
    seg = width / segments
    for i in range(segments):
        s.rect(x + i * seg, y, seg, 5, fill=color if i % 2 == 0 else "#FFFFFF",
               stroke=color, sw=0.8, rx=0)
    for i in range(segments + 1):
        s.text(x + i * seg, y + 18, f"{seg_m * i:.0f}", size=9, color=color,
               anchor="middle")
    s.text(x + width + 10, y + 18, f"{unit}　{note}", size=9, color=color)
