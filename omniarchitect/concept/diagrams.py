"""概念图解：本项目自有的确定性 SVG 生成器。

为什么自己画而不是交给生成式模型：概念图解要能**被指出问题**——哪条动线穿了
私密区、哪个房间没有外墙、服务核挡住了哪个采光面。AI 生成的"概念图"通常好看
但不可核对，业主一旦照着讨论，讨论的就是一张不存在的东西。

所以这里的图由数据算出坐标，纯文本 SVG，可被 XML 解析器校验，也可直接放进
PPTX 与浏览器。图上标注取自真实房间名与需求活动名，不编造。

没有几何数据时，图表达的是**拓扑关系**（谁挨着谁、怎么走、光从哪来），
图上明写"非按比例"——不伪装成平面。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

CANVAS_W = 1200
CANVAS_H = 760
MARGIN = 56

#: 语义色（与 DESIGN_CRITERIA 的批注色彩语义一致）
C_INK = "#1E2328"
C_MUTED = "#6B7280"
C_RULE = "#D6D9DD"
C_BG = "#FBFBFA"
C_PUBLIC = "#CFE3F2"      # 公共：蓝
C_PRIVATE = "#E4DCF2"     # 私密：紫
C_SERVICE = "#E8E2D2"     # 服务：暖灰
C_CIRC = "#2F6FB2"        # 动线：蓝
C_LIGHT = "#E8A33D"       # 光：橙
C_RISK = "#C0392B"        # 问题：红
C_ACCENT = "#3F7D58"      # 亮点：绿


def _dw(text: str) -> int:
    """Display width in half-width units (CJK counts 2)."""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in str(text))


def _fit(text: str, budget_units: int) -> str:
    """Trim with an ellipsis so a label never spills out of its box."""
    s = str(text or "")
    if _dw(s) <= budget_units:
        return s
    out = ""
    used = 0
    for ch in s:
        w = 2 if ord(ch) > 0x2E80 else 1
        if used + w > budget_units - 1:
            break
        out += ch
        used += w
    return out + "…"


class Svg:
    """Minimal deterministic SVG writer. No styling libraries, no canvas."""

    def __init__(self, width: int = CANVAS_W, height: int = CANVAS_H,
                 title: str = "", subtitle: str = "", bg: str = C_BG) -> None:
        self.w, self.h = width, height
        self.body: List[str] = []
        self.defs: List[str] = []
        self.title = title
        self.subtitle = subtitle
        self.bg = bg
        self._marker("arrow", C_CIRC)

    # -- primitives -----------------------------------------------------
    def _marker(self, name: str, color: str) -> None:
        self.defs.append(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
        )

    def rect(self, x: float, y: float, w: float, h: float, *, fill: str = "none",
             stroke: str = C_RULE, sw: float = 1.0, rx: float = 8.0,
             dash: str = "", opacity: float = 1.0) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
            f'{d} opacity="{opacity}"/>'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, *,
             stroke: str = C_RULE, sw: float = 1.2, dash: str = "",
             arrow: bool = False) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}{m}/>'
        )

    def polyline(self, pts: Sequence[Tuple[float, float]], *, stroke: str = C_CIRC,
                 sw: float = 2.2, arrow: bool = True, dash: str = "") -> None:
        if len(pts) < 2:
            return
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.body.append(
            f'<polyline points="{path}" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round"{d}{m}/>'
        )

    def path(self, d: str, *, fill: str = "none", stroke: str = C_RULE,
             sw: float = 1.5, opacity: float = 1.0) -> None:
        self.body.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'opacity="{opacity}"/>'
        )

    def circle(self, cx: float, cy: float, r: float, *, fill: str = "none",
               stroke: str = C_RULE, sw: float = 1.2) -> None:
        self.body.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def text(self, x: float, y: float, content: str, *, size: int = 14,
             color: str = C_INK, anchor: str = "start", weight: str = "400",
             opacity: float = 1.0, mono: bool = False) -> None:
        family = ("ui-monospace, SFMono-Regular, Menlo, monospace" if mono else
                  "'Microsoft YaHei', 'Noto Sans SC', 'PingFang SC', sans-serif")
        self.body.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" opacity="{opacity}">{escape(str(content))}</text>'
        )

    def label(self, x: float, y: float, w: float, h: float, lines: Sequence[str],
              *, size: int = 13, color: str = C_INK, weight: str = "400",
              padding: float = 6.0) -> None:
        """Centre a short block of text; trims rather than overflowing."""
        budget = max(4, int((w - 2 * padding) / (size * 0.52)))
        rows = [_fit(t, budget) for t in lines][:3]
        line_h = size * 1.35
        total = line_h * len(rows)
        start = y + (h - total) / 2 + size * 0.95
        for i, row in enumerate(rows):
            self.text(x + w / 2, start + i * line_h, row, size=size,
                      color=color, anchor="middle", weight=weight)

    # -- output ---------------------------------------------------------
    def render(self) -> str:
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
            f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'role="img" aria-label="{escape(self.title)}">',
            f"<title>{escape(self.title)}</title>",
            f"<desc>{escape(self.subtitle or self.title)}</desc>",
            "<defs>" + "".join(self.defs) + "</defs>",
            f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>',
        ]
        return "\n".join(head + self.body + ["</svg>", ""])


def _header(s: Svg, title: str, sub: str, note: str) -> None:
    s.text(MARGIN, 52, title, size=24, weight="600")
    s.text(MARGIN, 78, sub, size=13, color=C_MUTED)
    s.text(CANVAS_W - MARGIN, 52, note, size=11, color=C_MUTED, anchor="end")
    s.line(MARGIN, 96, CANVAS_W - MARGIN, 96, stroke=C_RULE, sw=1)


def _footer(s: Svg, lines: Sequence[str]) -> None:
    y = CANVAS_H - 24 - 16 * (len(lines) - 1)
    for i, t in enumerate(lines):
        s.text(MARGIN, y + i * 16, t, size=10, color=C_MUTED)


# --------------------------------------------------------------------------
# 数据准备：房间/活动分组（都来自真实数据）
# --------------------------------------------------------------------------
@dataclass
class Group:
    key: str
    label: str
    items: List[str] = field(default_factory=list)
    kind: str = "public"      # public / private / service


_ZONE_KIND = {
    "day": "public", "public": "public", "living": "public", "social": "public",
    "night": "private", "private": "private", "quiet": "private", "focus": "private",
    "guest": "public", "service": "service", "wet": "service", "core": "service",
    "back": "service", "utility": "service", "staff": "service",
}

#: 没有 program 时，把需求活动折成功能组（不编房间名，直接用活动名）
_ACTIVITY_GROUP = {
    "家庭聚集 / 观看": ("公共 · 聚集", "public"),
    "聚餐 / 待客": ("公共 · 待客", "public"),
    "烹饪 / 备餐": ("服务 · 烹饪", "service"),
    "用餐": ("公共 · 用餐", "public"),
    "睡眠 / 休息": ("私密 · 休息", "private"),
    "儿童活动 / 学习": ("私密 · 学习", "private"),
    "居家办公": ("私密 · 专注", "private"),
    "更衣 / 收纳": ("私密 · 收纳", "private"),
    "洗浴 / 如厕": ("服务 · 卫浴", "service"),
    "家务 / 家政": ("服务 · 家政", "service"),
    "交通 / 通行": ("动线", "service"),
}


def groups_for(concept: Dict[str, Any], program: Sequence[Dict[str, Any]],
               needs: Sequence[Dict[str, Any]]) -> List[Group]:
    out: List[Group] = []
    if program:
        by_kind: Dict[str, Group] = {}
        for p in program:
            kind = _ZONE_KIND.get(str(p.get("zone") or "day"), "public")
            g = by_kind.setdefault(kind, Group(kind, {"public": "公共区",
                                                      "private": "私密区",
                                                      "service": "服务与辅助"}[kind],
                                              kind=kind))
            g.items.append(str(p.get("name") or ""))
        for kind in ("public", "service", "private"):
            if kind in by_kind:
                out.append(by_kind[kind])
        return out

    seen: Dict[str, Group] = {}
    for r in needs:
        act = str(r.get("activity") or "")
        label, kind = _ACTIVITY_GROUP.get(act, ("其他需求", "public"))
        g = seen.setdefault(label, Group(label, label, kind=kind))
        if act and act not in g.items:
            g.items.append(act)
    order = {"public": 0, "service": 1, "private": 2}
    return sorted(seen.values(), key=lambda g: (order.get(g.kind, 9), g.label))


# --------------------------------------------------------------------------
# 1. 功能关系图
# --------------------------------------------------------------------------
def functional_relations(concept: Dict[str, Any], ctx: Any,
                         program: Sequence[Dict[str, Any]],
                         needs: Sequence[Dict[str, Any]]) -> str:
    groups = groups_for(concept, program, needs)
    s = Svg(title=f"{concept['concept_id']} 功能关系图",
            subtitle="谁挨着谁：同一组内为直接相邻，组间连线为主要联系")
    _header(s, f"{concept['concept_name']} · 功能关系",
            "节点为功能组，组内条目取自任务书房间或需求矩阵活动",
            "拓扑示意 · 非按比例")

    if not groups:
        s.text(MARGIN, 200, "任务书与需求矩阵均为空：无依据可画，不生成占位节点。",
               size=15, color=C_RISK)
        _footer(s, ["缺少功能依据时不出图——这是规则，不是故障。"])
        return s.render()

    fill = {"public": C_PUBLIC, "private": C_PRIVATE, "service": C_SERVICE}
    top, bottom = 150, CANVAS_H - 110
    col_w = (CANVAS_W - 2 * MARGIN - 80 * (len(groups) - 1)) / max(1, len(groups))
    boxes: Dict[str, Tuple[float, float, float, float]] = {}
    for i, g in enumerate(groups):
        x = MARGIN + i * (col_w + 80)
        # 高度按条目数自适应，条目多的组更"重"
        h = min(bottom - top, 130 + 34 * len(g.items))
        y = top + (bottom - top - h) / 2
        s.rect(x, y, col_w, h, fill=fill.get(g.kind, C_PUBLIC), stroke=C_INK, sw=1.4)
        s.text(x + 14, y - 12, g.label, size=13, weight="600", color=C_INK)
        for j, item in enumerate(g.items[:6]):
            s.text(x + 16, y + 30 + j * 26, f"· {_fit(item, int((col_w - 40) / 7))}",
                   size=12, color=C_INK)
        if len(g.items) > 6:
            s.text(x + 16, y + 30 + 6 * 26, f"… 另有 {len(g.items) - 6} 项",
                   size=11, color=C_MUTED)
        boxes[g.key] = (x, y, col_w, h)

    # 连线：相邻组必有联系；服务组与公共/私密均连
    keys = [g.key for g in groups]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        ax, ay, aw, ah = boxes[a]
        bx, by, bw, bh = boxes[b]
        s.line(ax + aw, ay + ah / 2, bx, by + bh / 2, stroke=C_INK, sw=1.4, arrow=True)
    for g in groups:
        if g.kind == "service":
            for other in groups:
                if other.key == g.key or other.kind == "service":
                    continue
                gx, gy, gw, gh = boxes[g.key]
                ox, oy, ow, oh = boxes[other.key]
                s.line(gx + gw / 2, gy + (0 if oy < gy else gh),
                       ox + ow / 2, oy + (oh if oy < gy else 0),
                       stroke=C_LIGHT, sw=1.2, dash="6 4")

    _footer(s, [f"连线说明：实线=主要联系，虚线=服务供给关系（{concept['spatial_prototype']['prototype_id']}）。",
                ctx.dimensional_note])
    return s.render()


# --------------------------------------------------------------------------
# 2. 分区图
# --------------------------------------------------------------------------
def zoning(concept: Dict[str, Any], ctx: Any,
           program: Sequence[Dict[str, Any]],
           needs: Sequence[Dict[str, Any]]) -> str:
    """The partition diagram changes shape with the spatial family.

    A linear scheme drawn as concentric rings would be a drawing of a different
    project. So the geometry is chosen by `family`, and the labels come from the
    real functional groups.
    """
    groups = groups_for(concept, program, needs) or [Group("public", "公共区", kind="public")]
    p = concept["spatial_prototype"]
    fam = p.get("family", "linear")
    s = Svg(title=f"{concept['concept_id']} 分区图")
    _header(s, f"{concept['concept_name']} · 分区",
            f"空间家族：{p['family_zh']}　分区原则：{_fit(p['zoning'], 54)}",
            "拓扑示意 · 非按比例")

    top, bottom = 132, CANVAS_H - 150
    area_h = bottom - top
    cx, cy = CANVAS_W / 2, top + area_h / 2

    if fam == "layered":
        # 递进：外 → 内逐层收窄
        for i, g in enumerate(groups):
            pad = 26 + i * 74
            s.rect(MARGIN + pad, top + pad * 0.55, CANVAS_W - 2 * (MARGIN + pad),
                   area_h - pad * 1.1, fill=boxes_color(g.kind), stroke=C_INK,
                   sw=1.2, opacity=0.95)
            s.text(MARGIN + pad + 14, top + pad * 0.55 + 26,
                   f"{i + 1}. {g.label}", size=14, weight="600")
            s.text(MARGIN + pad + 14, top + pad * 0.55 + 48,
                   _fit("　".join(g.items[:4]), 34), size=11)
        s.text(CANVAS_W - MARGIN - 12, bottom + 24, "↓ 由外向内逐级私密", size=11,
               anchor="end", color=C_MUTED)

    elif fam == "cluster":
        # 组团：网格，每组一格，格间留通道
        cols = min(3, len(groups)) or 1
        rows = (len(groups) + cols - 1) // cols
        cw = (CANVAS_W - 2 * MARGIN) / cols
        ch = area_h / max(1, rows)
        for i, g in enumerate(groups):
            x = MARGIN + (i % cols) * cw
            y = top + (i // cols) * ch
            s.rect(x + 14, y + 12, cw - 28, ch - 40, fill=boxes_color(g.kind),
                   stroke=C_INK, sw=1.2)
            s.text(x + 26, y + 36, g.label, size=13, weight="600")
            s.text(x + 26, y + 58, _fit("　".join(g.items[:4]), int((cw - 60) / 7)),
                   size=11)
            # 格间通道：竖缝/横缝
            s.line(x + cw - 7, y + 12, x + cw - 7, y + ch - 28, stroke=C_CIRC,
                   sw=1.4, dash="5 5")
        s.text(MARGIN, bottom + 24, "虚线为组团间通道；组团内部不承担穿越",
               size=11, color=C_MUTED)

    elif fam == "radial":
        # 环形：核心 + 环外房间
        s.rect(cx - 78, cy - 52, 156, 104, fill=C_SERVICE, stroke=C_INK, sw=1.4)
        s.label(cx - 78, cy - 52, 156, 104, ["核心", "收纳 / 设备"], size=12)
        import math

        n = max(4, len(groups) * 2)
        for i, g in enumerate(groups):
            ang = -90 + i * (360 / max(1, len(groups)))
            rad = 210
            gx = cx + rad * math.cos(math.radians(ang)) - 92
            gy = cy + rad * math.sin(math.radians(ang)) - 40
            s.rect(gx, gy, 184, 80, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.label(gx, gy, 184, 80, [g.label], size=12)
            s.line(cx + 78 * math.cos(math.radians(ang)),
                   cy + 52 * math.sin(math.radians(ang)),
                   gx + 92, gy + 40, stroke=C_CIRC, sw=1.4, arrow=True)
        s.circle(cx, cy, 240, stroke=C_RULE, sw=1.2)
        s.text(MARGIN, bottom + 24, "圆为回游环：每组至少有两条到达路径",
               size=11, color=C_MUTED)

    elif fam == "courtyard":
        # 院落：中心留空，四周房间
        s.rect(MARGIN + 150, top + 40, CANVAS_W - 2 * (MARGIN + 150), area_h - 80,
               fill="#FFFFFF", stroke=C_INK, sw=1.4, dash="2 0")
        s.rect(cx - 120, cy - 70, 240, 140, fill=C_ACCENT, stroke="none",
               opacity=0.16, rx=0)
        s.text(cx, cy + 6, "院", size=22, anchor="middle", color=C_ACCENT, weight="600")
        s.text(cx, cy + 30, "室外 / 采光", size=11, anchor="middle", color=C_ACCENT)
        for i, g in enumerate(groups):
            gx = MARGIN + 20 if i % 2 == 0 else CANVAS_W - MARGIN - 176
            gy = top + 60 + (i // 2) * 120
            s.rect(gx, gy, 156, 96, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.label(gx, gy, 156, 96, [g.label], size=12)
            s.line(gx + (156 if i % 2 == 0 else 0), gy + 48,
                   cx + (-120 if i % 2 == 0 else 120), cy, stroke=C_CIRC, sw=1.3,
                   arrow=True)
        s.text(MARGIN, bottom + 24, "所有主要房间朝向院落；服务空间靠外侧",
               size=11, color=C_MUTED)

    elif fam == "hall":
        # 大厅式：一整片，靠家具与灯带分区
        s.rect(MARGIN + 20, top + 20, CANVAS_W - 2 * MARGIN - 40, area_h - 40,
               fill="#FFFFFF", stroke=C_INK, sw=1.4)
        for i, g in enumerate(groups):
            x = MARGIN + 60 + i * ((CANVAS_W - 2 * MARGIN - 120) / max(1, len(groups)))
            s.rect(x, cy - 70, (CANVAS_W - 2 * MARGIN - 160) / max(1, len(groups)),
                  140, fill=boxes_color(g.kind), stroke=C_RULE, sw=1.0, dash="6 4")
            s.text(x + 12, cy - 40, g.label, size=12, weight="600")
            s.text(x + 12, cy - 18, _fit("　".join(g.items[:3]), 22), size=10,
                   color=C_MUTED)
        s.text(MARGIN, bottom + 24, "无固定隔墙：分区由家具、地台与灯带表达",
               size=11, color=C_MUTED)

    else:
        # 线性：横带
        band_h = area_h / max(1, len(groups))
        for i, g in enumerate(groups):
            y = top + i * band_h
            s.rect(MARGIN, y + 6, CANVAS_W - 2 * MARGIN, band_h - 18,
                   fill=boxes_color(g.kind), stroke=C_INK, sw=1.2, rx=6)
            s.text(MARGIN + 16, y + 32, g.label, size=15, weight="600")
            s.text(MARGIN + 16, y + 56, "　".join(g.items[:6]) if g.items else "（未细化）",
                   size=12)
            if i < len(groups) - 1:
                s.text(cx, y + band_h - 8, "↓", size=16, anchor="middle", color=C_MUTED)

    s.text(MARGIN, CANVAS_H - 92, "分区判据（来自 S1）：", size=12, weight="600")
    s.text(MARGIN, CANVAS_H - 72, _fit(p["zoning"], 116), size=11, color=C_MUTED)
    _footer(s, [ctx.dimensional_note])
    return s.render()


def boxes_color(kind: str) -> str:
    return {"public": C_PUBLIC, "private": C_PRIVATE, "service": C_SERVICE}.get(kind, C_PUBLIC)


# --------------------------------------------------------------------------
# 3. 动线图
# --------------------------------------------------------------------------
def circulation(concept: Dict[str, Any], ctx: Any,
                program: Sequence[Dict[str, Any]],
                needs: Sequence[Dict[str, Any]]) -> str:
    """The path is drawn in the shape the prototype actually implies."""
    groups = groups_for(concept, program, needs) or [Group("public", "公共区", kind="public")]
    order = ([g for g in groups if g.kind == "public"]
             + [g for g in groups if g.kind == "service"]
             + [g for g in groups if g.kind == "private"]) or groups
    p = concept["spatial_prototype"]
    fam = p.get("family", "linear")
    s = Svg(title=f"{concept['concept_id']} 动线概念图")
    _header(s, f"{concept['concept_name']} · 动线", _fit(p["circulation"], 88),
            "拓扑示意 · 非按比例")
    cx, cy = CANVAS_W / 2, 340
    n = len(order)

    if fam in ("radial",):
        import math

        s.circle(cx, cy, 176, stroke=C_RULE, sw=1.4)
        s.circle(cx, cy, 74, fill=C_SERVICE, stroke=C_INK, sw=1.2)
        s.text(cx, cy + 5, "核心", size=13, anchor="middle")
        pts = []
        for i, g in enumerate(order):
            ang = -90 + i * (360 / max(1, n))
            x = cx + 176 * math.cos(math.radians(ang))
            y = cy + 176 * math.sin(math.radians(ang))
            s.circle(x, y, 26, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.text(x, y + 4, str(i + 1), size=12, anchor="middle", weight="600")
            s.text(x + 34 * math.cos(math.radians(ang)), y + 34 * math.sin(math.radians(ang)) + 4,
                   _fit(g.label, 10), size=11,
                   anchor="middle")
            pts.append((x, y))
        s.polyline(pts + [pts[0]], stroke=C_CIRC, sw=2.6)
        s.text(MARGIN, CANVAS_H - 132, "闭合环线：任何一点都有两条路径到达", size=11,
               color=C_CIRC)

    elif fam == "layered":
        steps = [(MARGIN + 60, cy + 130), (MARGIN + 320, cy + 130),
                 (MARGIN + 320, cy - 10), (MARGIN + 600, cy - 10),
                 (MARGIN + 600, cy - 130), (CANVAS_W - MARGIN - 40, cy - 130)]
        for i, g in enumerate(order[:len(steps)]):
            x, y = steps[i]
            s.rect(x - 58, y - 26, 116, 52, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.label(x - 58, y - 26, 116, 52, [f"{i + 1} {_fit(g.label, 8)}"], size=11)
        s.polyline(steps[:len(order)], stroke=C_CIRC, sw=2.6)
        s.text(MARGIN, CANVAS_H - 132, "折线递进：每转折一次，私密度提高一级",
               size=11, color=C_CIRC)

    elif fam == "courtyard":
        s.rect(cx - 110, cy - 80, 220, 160, fill=C_ACCENT, stroke="none", opacity=0.14, rx=0)
        s.text(cx, cy + 6, "院", size=22, anchor="middle", color=C_ACCENT)
        ring = [(cx - 240, cy - 140), (cx + 240, cy - 140), (cx + 240, cy + 140),
                (cx - 240, cy + 140)]
        for i, (x, y) in enumerate(ring):
            g = order[i % len(order)]
            s.circle(x, y, 30, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.text(x, y + 4, str(i + 1), size=12, anchor="middle", weight="600")
            s.text(x, y + 50, _fit(g.label, 10), size=11, anchor="middle")
        s.polyline(ring + [ring[0]], stroke=C_CIRC, sw=2.4)
        s.text(MARGIN, CANVAS_H - 132, "环绕院落的连续路径；雨天不需穿越室外",
               size=11, color=C_CIRC)

    elif fam == "cluster":
        trunk = [(MARGIN - 20, cy)]
        for i, g in enumerate(order):
            x = MARGIN + 40 + i * ((CANVAS_W - 2 * MARGIN - 80) / max(1, n))
            s.circle(x, cy, 30, fill=boxes_color(g.kind), stroke=C_INK, sw=1.2)
            s.text(x, cy + 4, str(i + 1), size=12, anchor="middle", weight="600")
            s.text(x, cy + 52, _fit(g.label, 10), size=11, anchor="middle")
            trunk.append((x, cy))
            s.line(x, cy + 32, x, cy + 96, stroke=C_RULE, sw=1.2, dash="4 4")
            s.text(x, cy + 116, "组团", size=10, anchor="middle", color=C_MUTED)
        s.polyline(trunk, stroke=C_CIRC, sw=2.6)
        s.text(MARGIN, CANVAS_H - 132, "主干 + 分支：主路径只在组团入口停靠",
               size=11, color=C_CIRC)

    else:
        step_w = (CANVAS_W - 2 * MARGIN) / max(1, n)
        pts: List[Tuple[float, float]] = []
        for i, g in enumerate(order):
            x = MARGIN + step_w * (i + 0.5)
            s.circle(x, cy, 34, fill=boxes_color(g.kind), stroke=C_INK, sw=1.4)
            s.text(x, cy + 5, str(i + 1), size=16, anchor="middle", weight="600")
            s.text(x, cy + 62, _fit(g.label, int(step_w / 8)), size=12, anchor="middle")
            pts.append((x, cy))
        s.polyline([(MARGIN - 24, cy)] + pts, stroke=C_CIRC, sw=2.6)
        s.text(MARGIN - 20, cy - 18, "入口", size=12, color=C_CIRC)
        pub = [i for i, g in enumerate(order) if g.kind == "public"]
        if pub and len(pub) < n:
            x = MARGIN + step_w * (max(pub) + 1)
            s.line(x, 190, x, CANVAS_H - 190, stroke=C_RISK, sw=1.6, dash="8 6")
            s.text(x + 10, 210, "访客止步", size=11, color=C_RISK)

    s.text(MARGIN, CANVAS_H - 108, "动线判据：", size=12, weight="600")
    s.text(MARGIN, CANVAS_H - 88, _fit(p["circulation"], 118), size=11, color=C_MUTED)
    if concept.get("s1_opportunity_refs"):
        s.text(MARGIN, CANVAS_H - 68,
               "回应机会：" + "、".join(concept["s1_opportunity_refs"]),
               size=11, color=C_ACCENT)
    _footer(s, [ctx.dimensional_note])
    return s.render()


def daylight(concept: Dict[str, Any], ctx: Any,
             program: Sequence[Dict[str, Any]],
             needs: Sequence[Dict[str, Any]]) -> str:
    groups = groups_for(concept, program, needs)
    p = concept["spatial_prototype"]
    s = Svg(title=f"{concept['concept_id']} 采光策略图")
    _header(s, f"{concept['concept_name']} · 采光与视线",
            _fit(p["daylight"], 90), "拓扑示意 · 非按比例")

    x0, y0 = MARGIN + 40, 150
    w, h = CANVAS_W - 2 * MARGIN - 80, CANVAS_H - 330
    s.rect(x0, y0, w, h, fill="#FFFFFF", stroke=C_INK, sw=1.6)
    s.text(x0, y0 - 10, "外墙（假设采光面）", size=11, color=C_MUTED)

    # 三层进深：近窗最亮，往里递减。这是"光深"关系，不是实测。
    for i in range(3):
        alpha = 0.30 - i * 0.09
        s.rect(x0 + w * i / 3, y0, w / 3, h, fill=C_LIGHT, stroke="none",
               rx=0, opacity=max(0.05, alpha))
    for i in range(1, 3):
        s.line(x0 + w * i / 3, y0, x0 + w * i / 3, y0 + h, stroke=C_MUTED, dash="4 6")
        s.text(x0 + w * i / 3 + 6, y0 + h - 10, f"{i * 3}m 光深（示意）",
               size=10, color=C_MUTED)

    # 分组落位：靠窗优先给公共/长时间停留组
    n = max(1, len(groups))
    for i, g in enumerate(groups):
        gx = x0 + 12 + (w - 24) * (i % 3) / 3
        gy = y0 + 16 + (h - 90) * (i // 3) / max(1, (n + 2) // 3)
        s.rect(gx, gy, w / 3 - 24, min(70, h / 3), fill=boxes_color(g.kind),
               stroke=C_INK, sw=1.0, opacity=0.92)
        s.label(gx, gy, w / 3 - 24, min(70, h / 3), [g.label], size=12)

    s.text(MARGIN, CANVAS_H - 108, "采光判据：", size=12, weight="600")
    s.text(MARGIN, CANVAS_H - 88, _fit(p["daylight"], 116), size=11, color=C_MUTED)
    s.text(MARGIN, CANVAS_H - 68,
           "光深示意按常见工程经验的三段表达，不代表实测照度；照度与遮阳在 S4 照明专项校核。",
           size=10, color=C_MUTED)
    _footer(s, [ctx.dimensional_note])
    return s.render()


# --------------------------------------------------------------------------
# 5. 空间序列图
# --------------------------------------------------------------------------
def sequence(concept: Dict[str, Any], ctx: Any) -> str:
    p = concept["spatial_prototype"]
    steps = _sequence_steps(concept)
    s = Svg(title=f"{concept['concept_id']} 空间序列")
    _header(s, f"{concept['concept_name']} · 空间序列",
            "从进门到最私密处，每一段有一个视觉落点", "体验示意")

    n = len(steps)
    step_w = (CANVAS_W - 2 * MARGIN) / max(1, n)
    base = 300
    for i, (title, note) in enumerate(steps):
        x = MARGIN + i * step_w + 16
        y = base - 30 - (i % 2) * 26
        s.rect(x, y, step_w - 32, 128, fill="#FFFFFF", stroke=C_INK, sw=1.2)
        s.text(x + 12, y + 24, f"0{i + 1}", size=12, color=C_ACCENT, weight="600")
        s.text(x + 12, y + 48, _fit(title, int((step_w - 56) / 7)), size=14, weight="600")
        s.label(x + 8, y + 52, step_w - 40, 66, [note], size=10, color=C_MUTED)
        if i < n - 1:
            s.line(x + step_w - 30, y + 64, x + step_w - 6, y + 64,
                   stroke=C_CIRC, sw=2, arrow=True)

    s.text(MARGIN, CANVAS_H - 110, "序列判据：", size=12, weight="600")
    s.text(MARGIN, CANVAS_H - 90, _fit(p["experience"], 116), size=11, color=C_MUTED)
    _footer(s, [ctx.dimensional_note])
    return s.render()


def _sequence_steps(concept: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Derive the sequence from the concept's own experience sequence.

    这一版不再把 `circulation` 原文截断 28 个字贴到图上——那正是"机器生成"
    的痕迹（图上一段被切断的句子，业主读不出任何东西）。改为读
    `design/vocabulary.sequence_for()` 给出的空间事件，并附上手法名称，
    让每一步都能被指认、被反对。
    """
    seq = concept.get("experience_sequence") or {}
    steps = seq.get("steps") or []
    if not steps:
        # 老数据（camel 之前生成的概念）没有该字段：按家族给一句可读的事件，
        # 不再贴 circulation 原文。
        fallback = {
            "courtyard": [("落客", "从外部进入，视线先被院墙收住"),
                          ("穿院", "光与天气成为第一个空间事件")],
            "layered": [("入户", "先卸下东西，不直接看见主体空间"),
                        ("过渡", "换鞋、挂衣、放包——脏与净在此分开")],
            "radial": [("入口", "看到核心体块，不知道后面有多深"),
                       ("绕行", "绕过核心后空间一次打开")],
            "hall": [("进入", "先感受到体量与光，而不是看到家具"),
                     ("站定", "光成为空间的主体，人在其中被照亮")],
            "cluster": [("到达", "先看到一组体量，不是一个门厅"),
                        ("选择", "有两条以上路径，访客自行选择方向")],
        }
        return fallback.get(str((concept.get("spatial_prototype") or {}).get("family")),
                            [("入户", "一条明确的界面把外部挡住"),
                             ("转向", "空间在第一个转折处展开")])

    from ..design import vocabulary as _vocab

    out: List[Tuple[str, str]] = []
    for s in steps:
        dev = _vocab.VOCABULARY.get(str(s.get("device") or ""))
        note = str(s.get("event") or "")
        out.append((f"{s.get('step', '')}" + (f" · {dev.name}" if dev else ""), note))
    return out


# --------------------------------------------------------------------------
# 6. 体量概念图（建筑主导）
# --------------------------------------------------------------------------
def _massing_kind(concept: Dict[str, Any]) -> str:
    d = concept.get("deliberation") or {}
    kind = str((concept.get("spatial_prototype") or {}).get("massing_kind") or "")
    return kind or ("courtyard" if (concept.get("spatial_prototype") or {}).get("family")
                    == "courtyard" else "")


def _water_band(s: Svg, x: float, y: float, w: float, h: float, label: str = "水面") -> None:
    s.rect(x, y, w, h, fill="#CFE3F2", stroke="none", opacity=0.85)
    s.text(x + 8, y + h / 2 + 4, label, size=10, color="#2F6FB2")


def massing(concept: Dict[str, Any], ctx: Any) -> str:
    """体量关系。分型来自推敲策略的 `massing_kind`，不是按空间家族猜的。"""
    p = concept["spatial_prototype"]
    d = concept.get("deliberation") or {}
    kind = _massing_kind(concept)
    s = Svg(title=f"{concept['concept_id']} 体量概念")
    _header(s, f"{concept['concept_name']} · 体量关系",
            _fit(d.get("parti") or p.get("spatial_logic") or "", 88),
            "体量示意 · 非按比例")

    cx, cy = CANVAS_W / 2, 380
    if kind == "courtyard_carved":
        # 四面围合，中间是院与水；临街与院内要能分开看
        for (dx, dy, w, h) in ((-230, -110, 190, 100), (40, -110, 190, 100),
                               (-230, 10, 190, 100), (40, 10, 190, 100)):
            s.rect(cx + dx, cy + dy, w, h, fill="#FFFFFF", stroke=C_INK, sw=1.4)
        s.rect(cx - 30, cy - 100, 60, 200, fill="#F2F2EF", stroke=C_INK, sw=1.2)
        _water_band(s, cx - 24, cy - 20, 48, 108, "水")
        s.text(cx + 4, cy - 40, "院", size=13, anchor="middle", color=C_ACCENT)
        s.text(cx + 4, cy + 124, "院墙（挡住街上视线）", size=10, anchor="middle",
               color=C_MUTED)
        # 临街面：实；院内面：透。这两句话是这张图的核心结论
        s.text(cx - 236, cy - 132, "临街面：实（窗少而深）", size=10, color=C_MUTED)
        s.line(cx - 250, cy - 136, cx - 250, cy + 130, stroke=C_MUTED, sw=1, dash="4 3")
        s.text(cx + 250, cy - 132, "院内面：透（近全玻璃）", size=10, anchor="end",
               color=C_ACCENT)
        s.text(cx - 330, cy + 40, "入口", size=11, color=C_CIRC)
        s.line(cx - 310, cy + 44, cx - 240, cy + 44, stroke=C_CIRC, sw=1.6, arrow=True)
    elif kind == "stepped":
        # 三层逐层后退，退出来的平台是上一层的院子
        for i, (w, dy, fill) in enumerate(((440, 0, "#FFFFFF"), (350, -90, "#F2F2EF"),
                                          (260, -180, "#FFFFFF"))):
            s.rect(cx - 220, cy + dy, w, 78, fill=fill, stroke=C_INK, sw=1.4)
            s.text(cx - 210, cy + dy + 46, f"L{i + 1}", size=11, color=C_MUTED)
            if i < 2:
                s.text(cx - 220 + w + 10, cy + dy + 46, "露台", size=10, color=C_ACCENT)
                s.line(cx - 220 + w, cy + dy + 8, cx - 220 + w + 60, cy + dy + 8,
                       stroke=C_ACCENT, sw=1.2, arrow=True)
    elif kind == "floating":
        # 底层架空，上部体量完整，水从下面穿过
        _water_band(s, cx - 250, cy + 60, 500, 46, "水面穿过建筑底部")
        for dx in (-220, -80, 80, 220):
            s.line(cx + dx, cy + 100, cx + dx, cy - 10, stroke=C_INK, sw=3)
        s.rect(cx - 240, cy - 180, 480, 170, fill="#FFFFFF", stroke=C_INK, sw=1.4)
        s.text(cx - 230, cy - 90, "主体量（L2–L3）", size=12, color=C_INK)
        s.text(cx - 230, cy + 56, "架空层（柱与楼梯）", size=11, color=C_MUTED)
    elif kind == "twin_wings":
        # 两个体量 + 中间的院与水
        s.rect(cx - 260, cy - 90, 170, 180, fill="#FFFFFF", stroke=C_INK, sw=1.4)
        s.rect(cx + 90, cy - 90, 170, 180, fill="#FFFFFF", stroke=C_INK, sw=1.4)
        _water_band(s, cx - 80, cy - 30, 160, 50, "院 + 水")
        s.text(cx - 175, cy - 4, "公共翼", size=11, anchor="middle", color=C_INK)
        s.text(cx + 175, cy - 4, "私密翼", size=11, anchor="middle", color=C_INK)
        s.text(cx, cy + 76, "片墙收住视线", size=10, anchor="middle", color=C_MUTED)
        s.line(cx - 90, cy + 56, cx + 90, cy + 56, stroke=C_MUTED, sw=1.2)
    else:
        s.rect(cx - 210, cy - 40, 420, 120, fill="#FFFFFF", stroke=C_INK, sw=1.4)
        s.rect(cx - 150, cy - 150, 300, 110, fill="#F2F2EF", stroke=C_INK, sw=1.4)
        for i in range(4):
            s.line(cx - 150 + i * 100, cy - 150, cx - 150 + i * 100, cy - 40,
                   stroke=C_RULE, sw=1)

    s.text(MARGIN, CANVAS_H - 108, "体量逻辑：", size=12, weight="600")
    s.label(MARGIN, CANVAS_H - 106, CANVAS_W - 2 * MARGIN, 44,
            [_fit(d.get("massing") or p.get("zoning") or "", 116),
             _fit(d.get("facade") or "", 116)], size=11, color=C_MUTED)
    _footer(s, ["体量只表达关系与朝向，不含尺寸、层数与结构结论；须在 S3/S4 用真实条件校核。",
                ctx.dimensional_note])
    return s.render()


# --------------------------------------------------------------------------
# 7. 剖面与竖向（建筑主导：楼层怎么分、光怎么进来）
# --------------------------------------------------------------------------
def section(concept: Dict[str, Any], ctx: Any) -> str:
    """剖面示意：每层承担什么、院或挑空在哪、光从哪一侧来。

    剖面是「楼层空间」唯一能被讨论的图：平面上三层可以画得一样，剖面一画
    就看出哪层在压缩、哪层在放开、哪层有院子。
    """
    p = concept["spatial_prototype"]
    d = concept.get("deliberation") or {}
    kind = _massing_kind(concept)
    prog = list(d.get("levels_program") or [])
    n = max(1, min(4, len(prog) or 3))

    s = Svg(title=f"{concept['concept_id']} 剖面关系")
    _header(s, f"{concept['concept_name']} · 剖面与楼层",
            _fit(d.get("section") or "", 88), "剖面示意 · 非按比例")

    ground = 560
    base_x, width = 190, 580
    step = 84
    # 地面
    s.line(120, ground, 980, ground, stroke=C_INK, sw=2)
    s.text(120, ground + 20, "室外地坪", size=10, color=C_MUTED)

    for i in range(n):
        y = ground - i * step
        s.line(base_x, y, base_x + width, y, stroke=C_INK, sw=2)
        label = prog[i] if i < len(prog) else f"L{i + 1}"
        # 层号与用途写在板线之上的图内左侧：放右侧会被画布边缘裁成半句。
        s.text(base_x + 8, y - 10, f"L{i + 1}", size=12, color=C_INK, weight="600")
        s.text(base_x + 46, y - 10, _fit(label, 26), size=10, color=C_MUTED)

    # 通高 / 挑空：按策略放到不同位置
    void_w = 130
    void_x = base_x + 250
    if kind == "courtyard_carved":
        s.rect(void_x, ground - step * 2, void_w, step * 2, fill="#FFFFFF",
               stroke=C_RULE, sw=1, dash="5 4")
        _water_band(s, void_x + 12, ground - step * 2, void_w - 24, 22, "水")
        s.text(void_x + 8, ground - step * 2 - 8, "院（两层通高）", size=11, color=C_ACCENT)
    elif kind == "floating":
        s.rect(base_x, ground - step, width, step, fill="#F7F7F5", stroke="none")
        s.text(base_x + 12, ground - step + 40, "架空层：净高压低", size=11, color=C_MUTED)
    elif kind == "stepped":
        for i in range(n):
            y = ground - i * step
            s.line(base_x + width, y, base_x + width + 90 * (i % 2), y,
                   stroke=C_ACCENT, sw=1.4, dash="4 3")
    elif kind == "twin_wings":
        s.line(void_x + void_w / 2, ground, void_x + void_w / 2, ground - step * n,
               stroke=C_RULE, sw=1, dash="5 4")
        s.text(void_x + void_w / 2 + 6, ground - step * n + 18, "院", size=11, color=C_ACCENT)
    else:
        s.rect(void_x, ground - step * 2, void_w, step * 2, fill="#F7F7F5",
               stroke=C_RULE, sw=1, dash="5 4")

    # 采光：侧光 + 顶部光（有院/井时）
    for i in range(n):
        y = ground - i * step - step * 0.6
        s.line(120, y, base_x - 12, y, stroke=C_LIGHT, sw=1.6, arrow=True)
    if kind in ("courtyard_carved",):
        s.line(void_x + void_w / 2, ground - step * n - 46, void_x + void_w / 2,
               ground - step * n - 6, stroke=C_LIGHT, sw=1.6, arrow=True)
        s.text(void_x + void_w / 2 + 6, ground - step * n - 50, "采光井", size=10, color=C_LIGHT)

    # 图例放在图内左上角，不跟地坪线抢位置
    s.line(120, 132, 168, 132, stroke=C_LIGHT, sw=1.6, arrow=True)
    s.text(176, 136, "光的方向", size=10, color=C_LIGHT)
    s.rect(120, 146, 30, 12, fill="#FFFFFF", stroke=C_RULE, sw=1, dash="4 3")
    s.text(158, 157, "通高 / 挑空", size=10, color=C_MUTED)
    s.text(MARGIN, CANVAS_H - 104, "竖向判据：", size=12, weight="600")
    s.label(MARGIN, CANVAS_H - 102, CANVAS_W - 2 * MARGIN, 44,
            [_fit(d.get("section") or "", 116),
             _fit(d.get("integration") or "", 116)], size=11, color=C_MUTED)
    _footer(s, ["剖面表达楼层分工与通高关系，不含层高尺寸、结构构件与设备管线结论。",
                ctx.dimensional_note])
    return s.render()


# --------------------------------------------------------------------------
# 8. 景观结构图（景观主导：分区、游线、水、植物层级）
# --------------------------------------------------------------------------
#: 分区名 → 语义色。认不出的分区用中性色，不硬套色。
_ZONE_COLOR = (
    (("水", "池", "溪", "渠"), "#CFE3F2"),
    (("草坪", "停留", "茶席", "硬质"), "#E8E2D2"),
    (("种植", "林", "绿", "花"), "#D8E6D2"),
    (("园路", "路径", "游线"), "#EDEDEA"),
    (("服务", "收纳", "设备"), "#E4DCF2"),
)


def _zone_fill(name: str) -> str:
    for keys, color in _ZONE_COLOR:
        if any(k in name for k in keys):
            return color
    return "#F2F2EF"


def landscape(concept: Dict[str, Any], ctx: Any) -> str:
    """景观结构：场地关系（左）+ 分区占比（右）+ 水/植物/铺装（下）。

    分区占比是**数据**，场地关系是**示意**，两者分开画。早先把占比画成
    竖条纹铺满场地，再叠上游线和水面，读起来像一张色卡，看不出哪里是水、
    人怎么绕——图看着满，信息是零。
    """
    d = concept.get("deliberation") or {}
    zones = d.get("zones") or []
    s = Svg(title=f"{concept['concept_id']} 景观结构")
    _header(s, f"{concept['concept_name']} · 分区与游线",
            _fit(d.get("parti") or "", 88), "分区示意 · 非按比例")

    # ---- 左：场地关系 ----
    sx, sy, sw, sh = 150, 156, 540, 380
    s.rect(sx, sy, sw, sh, fill="#FBFBFA", stroke=C_INK, sw=1.6)
    s.text(sx, sy - 10, "场地边界", size=10, color=C_MUTED)

    # 乔木带（上、左、右三边）
    for i in range(5):
        s.circle(sx + 52 + i * 108, sy + 32, 19, fill="#D8E6D2", stroke="#B9CDB2", sw=1)
    for i in range(4):
        s.circle(sx + 30, sy + 104 + i * 74, 19, fill="#D8E6D2", stroke="#B9CDB2", sw=1)
        s.circle(sx + sw - 30, sy + 104 + i * 74, 19, fill="#D8E6D2", stroke="#B9CDB2", sw=1)
    s.text(sx + 52, sy + 68, "乔木带：骨架与边界", size=10, color="#5C7A55")

    # 水面
    wx, wy, ww, wh = sx + sw * 0.28, sy + sh * 0.46, sw * 0.36, 88
    s.rect(wx, wy, ww, wh, fill="#CFE3F2", stroke="#9CC3DE", sw=1.2, rx=6)
    s.text(wx + 14, wy + 46, "水面", size=12, color="#2F6FB2")
    s.text(wx + 14, wy + 66, "做法见下方水景一行", size=9, color="#2F6FB2")

    # 茶席
    tx, ty = sx + sw * 0.54, sy + sh * 0.12
    s.rect(tx, ty, 148, 60, fill="#E8E2D2", stroke="#C9BFA6", sw=1.2)
    s.text(tx + 12, ty + 25, "茶席 / 停留", size=11, color=C_INK)
    s.text(tx + 12, ty + 44, "背靠种植，面向房子", size=9, color=C_MUTED)

    # 游线：绕水一圈
    cy = sy + sh * 0.66
    s.polyline([(sx + 26, cy), (sx + sw * 0.20, sy + sh * 0.30),
                (sx + sw * 0.52, sy + sh * 0.24), (sx + sw - 32, sy + sh * 0.38),
                (sx + sw - 44, cy + 52), (sx + 44, cy + 56), (sx + 26, cy)],
               stroke=C_CIRC, sw=2)
    s.text(sx + 40, cy + 78, "游线：单向绕行，主路 900–1200 mm", size=10, color=C_CIRC)

    # 入口
    s.text(sx - 6, sy + sh + 26, "入口", size=10, color=C_MUTED)
    s.line(sx + 22, sy + sh + 20, sx + 22, sy + sh - 8, stroke=C_CIRC, sw=1.6, arrow=True)

    # ---- 右：分区占比（数据条，不是场地形状）----
    bx, by, bw = CANVAS_W - 336, 176, 230
    s.text(bx, by - 18, "分区占比", size=12, weight="600")
    if zones:
        for i, z in enumerate(zones):
            y = by + i * 42
            name = str(z.get("name") or "")
            s.rect(bx, y, bw, 34, fill=_zone_fill(name), stroke=C_RULE, sw=0.8)
            s.text(bx + 10, y + 22, _fit(name, 11), size=11, color=C_INK)
            s.text(bx + bw - 10, y + 22, str(z.get("share") or ""), size=11,
                   color=C_MUTED, anchor="end")
    else:
        s.text(bx, by + 20, "本方案未给分区占比", size=11, color=C_MUTED)

    # ---- 下：做法三行 ----
    for i, (label, key) in enumerate((("水景", "water"), ("植物", "planting"),
                                      ("铺装", "paving"))):
        y = CANVAS_H - 128 + i * 20
        s.text(MARGIN, y, f"{label}：", size=11, weight="600")
        s.text(MARGIN + 46, y, _fit(d.get(key) or "未设定", 96), size=10, color=C_MUTED)
    _footer(s, ["左图为空间关系示意、右图为分区占比；都不代表实际放线、面积与尺寸。",
                ctx.dimensional_note])
    return s.render()


# --------------------------------------------------------------------------
DIAGRAM_KINDS = ("functional", "zoning", "circulation", "daylight", "sequence",
                 "massing", "section", "landscape")


def build(concept: Dict[str, Any], ctx: Any,
          program: Sequence[Dict[str, Any]],
          needs: Sequence[Dict[str, Any]],
          out_dir: str | Path, *, kinds: Sequence[str] = ()) -> List[Dict[str, str]]:
    """Write every diagram this concept actually needs. Returns a manifest."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    want = list(kinds) or ["functional", "zoning", "circulation", "daylight", "sequence"]
    if not kinds:
        # 图种跟着**主导专业**走，不跟项目类型走：三层别墅的项目类型仍是住宅，
        # 但它需要的是一张剖面与一张体量图，而不是五张房间关系图。
        #
        # 建筑主导且没有房间数据时，功能关系图/分区图只会画出"其他需求"的圆圈——
        # 那不是信息，是噪音。此时只给能表达体量、剖面与序列的三张。
        lead = str(getattr(ctx, "lead_id", "") or "")
        has_rooms = bool([r for r in (program or []) if str(r.get("name") or "").strip()])
        if lead == "landscape":
            want = ["landscape", "sequence"]
        elif lead == "architecture":
            want = ["massing", "section", "sequence"]
            if has_rooms:
                want += ["functional", "zoning", "circulation"]
        elif lead == "interior":
            want = ["zoning", "circulation", "daylight", "sequence"]
        elif ctx.profile_id == "architecture":
            want = ["massing", "section", "sequence"]

    makers = {
        "functional": lambda: functional_relations(concept, ctx, program, needs),
        "zoning": lambda: zoning(concept, ctx, program, needs),
        "circulation": lambda: circulation(concept, ctx, program, needs),
        "daylight": lambda: daylight(concept, ctx, program, needs),
        "sequence": lambda: sequence(concept, ctx),
        "massing": lambda: massing(concept, ctx),
        "section": lambda: section(concept, ctx),
        "landscape": lambda: landscape(concept, ctx),
    }
    titles = {
        "functional": "功能关系图", "zoning": "分区图", "circulation": "动线概念图",
        "daylight": "采光策略图", "sequence": "空间序列图", "massing": "体量概念图",
        "section": "剖面与楼层图", "landscape": "景观结构图",
    }
    made: List[Dict[str, str]] = []
    for kind in dict.fromkeys(want):
        if kind not in makers:
            continue
        svg = makers[kind]()
        path = out / f"{concept['concept_id'].lower()}-{kind}.svg"
        path.write_text(svg, encoding="utf-8")
        made.append({
            "kind": kind, "title": titles[kind], "path": str(path),
            "concept_id": concept["concept_id"],
            "evidence_refs": ",".join(concept.get("s1_opportunity_refs") or []),
            "note": "由本系统确定性绘制，坐标为关系推演，非实测尺寸",
        })
    return made


__all__ = ["Svg", "DIAGRAM_KINDS", "build", "groups_for",
           "functional_relations", "zoning", "circulation", "daylight",
           "sequence", "massing", "section", "landscape", "Group"]
