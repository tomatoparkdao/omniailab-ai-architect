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

import re
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

#: 版面线宽系数。`视觉.md` 里写"细线"时这里是 0.9，写"粗线"时 1.5。
#: 语义色（公共/私密/服务）不随主题变——它们表达内容，不表达风格。
LINE_W = 1.0


def apply_theme(theme: Dict[str, Any] | None) -> Dict[str, Any]:
    """把项目视觉规范应用到本模块的图元配色与线宽。

    只改**表达**：纸色、墨色、线色、强调色、线宽。分区语义色、风险红、光色不动——
    那些是信息层，跟着内容走，不跟着客户喜好的排版走。

    返回实际生效的值，便于调用方写进报告（"这张图用了哪套配色"）。
    """
    global C_INK, C_MUTED, C_RULE, C_BG, C_ACCENT, LINE_W
    t = dict(theme or {})
    if t.get("ink"):
        C_INK = str(t["ink"])
    if t.get("muted"):
        C_MUTED = str(t["muted"])
    if t.get("line"):
        C_RULE = str(t["line"])
    if t.get("paper"):
        C_BG = str(t["paper"])
    if t.get("accent"):
        C_ACCENT = str(t["accent"])
    if t.get("line_weight"):
        try:
            LINE_W = max(0.5, min(2.0, float(t["line_weight"])))
        except (TypeError, ValueError):
            LINE_W = 1.0
    return {"ink": C_INK, "muted": C_MUTED, "line": C_RULE, "paper": C_BG,
            "accent": C_ACCENT, "line_weight": LINE_W}


def reset_theme() -> None:
    """回到仓库默认配色。测试与"无规范项目"靠它保证不串味。"""
    apply_theme({"ink": "#1E2328", "muted": "#6B7280", "line": "#D6D9DD",
                 "paper": "#FBFBFA", "accent": "#3F7D58", "line_weight": 1.0})


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
                 title: str = "", subtitle: str = "", bg: Optional[str] = None) -> None:
        self.w, self.h = width, height
        self.body: List[str] = []
        self.defs: List[str] = []
        self.title = title
        self.subtitle = subtitle
        # 默认值不能写在参数里：那是导入时求值，apply_theme 改了全局也不生效
        self.bg = C_BG if bg is None else bg
        self.lw = LINE_W
        self._marker("arrow", C_CIRC)

    # -- primitives -----------------------------------------------------
    def _marker(self, name: str, color: str) -> None:
        self.defs.append(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>'
        )

    def rect(self, x: float, y: float, w: float, h: float, *, fill: str = "none",
             stroke: Optional[str] = None, sw: float = 1.0, rx: float = 8.0,
             dash: str = "", opacity: float = 1.0) -> None:
        stroke = C_RULE if stroke is None else stroke
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw * self.lw:.2f}"'
            f'{d} opacity="{opacity}"/>'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, *,
             stroke: Optional[str] = None, sw: float = 1.2, dash: str = "",
             arrow: bool = False) -> None:
        stroke = C_RULE if stroke is None else stroke
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arrow)"' if arrow else ""
        self.body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw * self.lw:.2f}"{d}{m}/>'
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
            f'stroke-width="{sw * self.lw:.2f}" stroke-linejoin="round"{d}{m}/>'
        )

    def path(self, d: str, *, fill: str = "none", stroke: str = C_RULE,
             sw: float = 1.5, opacity: float = 1.0) -> None:
        self.body.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw * self.lw:.2f}" opacity="{opacity}"/>'
        )

    def circle(self, cx: float, cy: float, r: float, *, fill: str = "none",
               stroke: str = C_RULE, sw: float = 1.2) -> None:
        self.body.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw * self.lw:.2f}"/>'
        )

    def polygon(self, pts: Sequence[Tuple[float, float]], *, fill: str = "none",
                stroke: str = "none", sw: float = 1.0, opacity: float = 1.0,
                dash: str = "") -> None:
        """Filled polygon — the primitive every axonometric face needs.

        `polyline` is stroke-only by design; a solid face cannot be faked with a
        thick stroke, so axonometric work needs this.
        """
        if len(pts) < 3:
            return
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s = (f' stroke="{stroke}" stroke-width="{sw * self.lw:.2f}"'
             if stroke != "none" else "")
        self.body.append(
            f'<polygon points="{path}" fill="{fill}"{s} stroke-linejoin="round"'
            f' opacity="{opacity}"{d}/>'
        )

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, *, fill: str = "none",
                stroke: str = "none", sw: float = 1.0, opacity: float = 1.0,
                rotate: float = 0.0) -> None:
        t = f' transform="rotate({rotate:.1f} {cx:.1f} {cy:.1f})"' if rotate else ""
        s = f' stroke="{stroke}" stroke-width="{sw * self.lw:.2f}"' if stroke != "none" else ""
        self.body.append(
            f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
            f'fill="{fill}"{s} opacity="{opacity}"{t}/>'
        )

    def gradient(self, name: str, stops: Sequence[Tuple[float, str]],
                 *, x2: float = 0.0, y2: float = 1.0, opacity: float = 1.0) -> str:
        """Linear gradient in objectBoundingBox space; returns `url(#name)`."""
        body = "".join(
            f'<stop offset="{o:.2f}" stop-color="{c}" stop-opacity="{opacity}"/>'
            for o, c in stops)
        self.defs.append(
            f'<linearGradient id="{name}" x1="0" y1="0" x2="{x2:.2f}" y2="{y2:.2f}">'
            f"{body}</linearGradient>")
        return f"url(#{name})"

    def clip_rect(self, name: str, w: float, h: float) -> str:
        """A clip so painted grounds never bleed over the sheet margin."""
        self.defs.append(
            f'<clipPath id="{name}"><rect x="0" y="0" width="{w:.1f}" height="{h:.1f}"/></clipPath>')
        return f"url(#{name})"

    def text(self, x: float, y: float, content: str, *, size: int = 14,
             color: Optional[str] = None, anchor: str = "start", weight: str = "400",
             opacity: float = 1.0, mono: bool = False, rotate: float = 0.0) -> None:
        color = C_INK if color is None else color
        family = ("ui-monospace, SFMono-Regular, Menlo, monospace" if mono else
                  "'Microsoft YaHei', 'Noto Sans SC', 'PingFang SC', sans-serif")
        t = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ""
        self.body.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}" opacity="{opacity}"{t}>{escape(str(content))}</text>'
        )

    def label(self, x: float, y: float, w: float, h: float, lines: Sequence[str],
              *, size: int = 13, color: Optional[str] = None, weight: str = "400",
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


# --------------------------------------------------------------------------
# 体量：等距轴测 + 连续形态演变
# --------------------------------------------------------------------------
#: 每一步的盒子用"米"作单位，再由 Iso 换算成图面像素。尺寸是**关系量**，
#: 不是实测值——图注统一写"体量关系 · 非按比例"。
Box = Tuple[float, float, float, float, float, float, str]   # x, y, z, w, d, h, fill

_MASS_C = "#E7E0D0"      # 主体量：暖石灰
_MASS_2 = "#D8D0BE"      # 次体量：深一档
_MASS_3 = "#F6F3EC"      # 轻体量：白
_MASS_CUT = "#C9C0AC"    # 被切开的面：最暗，读得出"这里削掉了"


def _wrap(text: str, per_line: int = 13, max_lines: int = 4) -> List[str]:
    """按**汉字数**折行（`_fit` 的预算是半角单位，直接传会砍掉一半字）。

    先按标点切短语再拼行：纯按字数硬切会把"12×12 米"切成"1 / 2×12 米"，
    数字被拆开，读起来像排版事故。
    """
    s = " ".join(str(text or "").split())
    if not s:
        return []
    parts = [x for x in re.split(r"(?<=[，、；。：,;])", s) if x]
    lines: List[str] = []
    cur = ""
    for part in parts:
        rest = part
        while len(rest) > per_line:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(rest[:per_line])
            rest = rest[per_line:]
        if len(cur) + len(rest) <= per_line:
            cur += rest
        else:
            if cur:
                lines.append(cur)
            cur = rest
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max(1, per_line - 1)] + "…"
    return lines


def _evolution(kind: str) -> List[Tuple[str, str, List[Box], Tuple[float, float, float, float]]]:
    """每个体量类型的形成过程：三步，最后一步就是结果。

    每一步必须**看得出差别**：先做满，再减去，最后加入场地。上一版把三步画成
    同一个回字形，客户看到的是三张一样的图——那就等于没讲形成过程。

    第四项是该步的水面 (x, y, w, d)；宽或深为 0 表示这一步还没有水。
    """
    no_water = (0.0, 0.0, 0.0, 0.0)
    if kind == "stepped":
        return [
            ("先做满", "可建体量按三层做满：一个 8.4×6 米的完整长方体",
             [(0, 0, 0, 8.4, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 8.4, 6.0, 2.9, _MASS_C),
              (0, 0, 5.8, 8.4, 6.0, 2.9, _MASS_C)], no_water),
            ("逐层退台", "每上一层退 1.2 米：退出来的平台朝南，是下一层的露台",
             [(0, 0, 0, 8.4, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 7.2, 5.2, 2.9, _MASS_C),
              (0, 0, 5.8, 5.4, 4.4, 2.9, _MASS_3)], no_water),
            ("顶层收成院", "顶层只剩 4.8 米宽：剩下的屋顶做成种植屋面，与露台连着",
             [(0, 0, 0, 8.4, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 7.2, 5.2, 2.9, _MASS_2),
              (0, 0, 5.8, 4.8, 4.0, 2.9, _MASS_3)], (5.0, 1.0, 3.2, 3.0)),
        ]
    if kind == "floating":
        return [
            ("先落地", "底层先落在地上：院子与房子在同一标高，地面全被占住",
             [(0, 0, 0, 9.0, 6.0, 2.8, _MASS_2),
              (0, 0, 2.8, 9.0, 6.0, 2.8, _MASS_C),
              (0, 0, 5.6, 9.0, 6.0, 2.8, _MASS_C)], no_water),
            ("底层掏空", "底层只留柱与楼梯：地面还给院子，视线能穿过去",
             [(0.5, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (4.2, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (7.9, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (0.5, 5.2, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (4.2, 5.2, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (7.9, 5.2, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (0, 0, 2.8, 9.0, 6.0, 5.6, _MASS_C)], no_water),
            ("水穿其下", "水面从架空层底下穿过：院子延伸进屋，不是停车场",
             [(0.5, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (4.2, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (7.9, 0.3, 0.0, 0.45, 0.45, 2.8, _MASS_CUT),
              (0, 0, 2.8, 9.0, 6.0, 5.6, _MASS_C)], (0.1, 1.4, 3.4, 4.0)),
        ]
    if kind == "twin_wings":
        return [
            ("一条长体量", "面宽 14 米、进深 6 米：能建多少建多少，中间没有院子",
             [(0, 0, 0, 14.0, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 14.0, 6.0, 2.9, _MASS_C)], no_water),
            ("中间断开", "从中间拿出 4 米：两翼各 5 米，端头仍然对齐",
             [(0, 0, 0, 5.0, 6.0, 2.9, _MASS_C),
              (9.0, 0, 0, 5.0, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 5.0, 6.0, 2.9, _MASS_C),
              (9.0, 0, 2.9, 5.0, 6.0, 2.9, _MASS_3)], no_water),
            ("双翼夹院", "两翼之间是院与水；一道片墙把街上的视线收住",
             [(0, 0, 0, 5.0, 6.0, 2.9, _MASS_C),
              (9.0, 0, 0, 5.0, 6.0, 2.9, _MASS_C),
              (0, 0, 2.9, 5.0, 6.0, 2.9, _MASS_2),
              (9.0, 0, 2.9, 5.0, 6.0, 2.9, _MASS_2),
              (5.0, 0, 0, 0.4, 6.0, 5.8, _MASS_3)], (5.4, 1.2, 3.2, 3.6)),
        ]
    if kind == "courtyard_carved":
        return [
            ("先做满", "四面围合的可建体量做满：12×12 米，两层通高 5.4 米",
             [(0, 0, 0, 12.0, 12.0, 5.4, _MASS_C)], no_water),
            ("院从中间挖出", "中间 8×8 米整块挖掉：房间全部朝院，光从上面下来",
             [(0, 0, 0, 12.0, 2.0, 5.4, _MASS_C),
              (0, 10.0, 0, 12.0, 2.0, 5.4, _MASS_C),
              (0, 2.0, 0, 2.0, 8.0, 5.4, _MASS_2),
              (10.0, 2.0, 0, 2.0, 8.0, 5.4, _MASS_2)], no_water),
            ("引水入院", "院底放一块静水：倒影把层高与天空读进院子",
             [(0, 0, 0, 12.0, 2.0, 5.4, _MASS_C),
              (0, 10.0, 0, 12.0, 2.0, 5.4, _MASS_C),
              (0, 2.0, 0, 2.0, 8.0, 5.4, _MASS_2),
              (10.0, 2.0, 0, 2.0, 8.0, 5.4, _MASS_2)], (2.3, 2.3, 7.4, 7.4)),
        ]
    # 默认：单一体量 → 顶部退台 → 侧院
    return [
        ("先做满", "可建体量按三层做满：10×7 米，没有退让",
         [(0, 0, 0, 10.0, 7.0, 2.9, _MASS_C),
          (0, 0, 2.9, 10.0, 7.0, 2.9, _MASS_C),
          (0, 0, 5.8, 10.0, 7.0, 2.9, _MASS_C)], no_water),
        ("顶部退出平台", "顶层后退 2 米、收窄 1 米：西侧得到一个朝院子的平台",
         [(0, 0, 0, 10.0, 7.0, 2.9, _MASS_C),
          (0, 0, 2.9, 10.0, 7.0, 2.9, _MASS_2),
          (0, 2.0, 5.8, 8.0, 5.0, 2.9, _MASS_3)], no_water),
        ("院落补齐", "剩下的空地做成院：进院先看见树，再看见门",
         [(0, 0, 0, 10.0, 7.0, 2.9, _MASS_C),
          (0, 0, 2.9, 10.0, 7.0, 2.9, _MASS_2),
          (0, 2.0, 5.8, 8.0, 5.0, 2.9, _MASS_3)], (0.4, 7.4, 4.4, 2.4)),
    ]


def _draw_mass_step(s: Svg, iso_mod: Any, boxes: Sequence[Box],
                    water: Tuple[float, float, float, float], *,
                    ox: float, oy: float, scale: float,
                    ground: Tuple[float, float, float, float],
                    yard: Sequence[Tuple[float, float, str]] = ()) -> None:
    # 2:1 轴测：把竖向压到 0.78，院子与退台才看得进去，而不是只看到外墙
    iso = iso_mod.Iso(ox, oy, scale=scale, z_scale=scale * 0.78)
    gx, gy, gw, gd = ground
    iso_mod.draw_ground(iso, s, gx, gy, gw, gd, grid=0)
    # 阴影先画：压在地面上，逐个体量按底面投
    for (x, y, z, w, d, h, _f) in boxes:
        if z <= 0.01:
            iso_mod.draw_shadow(iso, s, x, y, w, d, dx=0.6, dy=0.6, opacity=0.16)
    wx, wy, ww, wd = water
    if ww > 0 and wd > 0:
        iso_mod.water_plane(iso, s, wx, wy, ww, wd)
    ordered = sorted(boxes, key=lambda b: iso.depth(b[0] + b[3] * 0.5, b[1] + b[4] * 0.5, b[2]))
    for (x, y, z, w, d, h, fill) in ordered:
        iso_mod.draw_box(iso, s, x, y, z, w, d, h, fill=fill,
                         edge="#3A3F44", sw=0.9)
    # 院的标记：等距图上"凹进去的洞"必须被指认，否则看起来像画错了
    for (cwx, cwy, label) in yard:
        cx, cy = iso.p(cwx, cwy, 0.02)
        s.text(cx, cy + 5, label, size=max(10, int(scale * 0.78)), anchor="middle",
               color="#4E7C63", weight="600")


def massing(concept: Dict[str, Any], ctx: Any) -> str:
    """体量关系：四联等距轴测，前三步是形成过程，第四格是结果。

    上一版画的是俯视矩形拼接——没有高度、没有明暗、没有遮挡，读不出"哪个面
    朝街、哪一层退进去"。体量推敲的**全部信息都在第三维**，所以这里改用等距
    轴测，并把"怎么长成这样"画成可数的三步：做满 → 减去 → 加入场地。

    图注写死"体量关系 · 非按比例"：尺度是关系量，尺寸由 S3/S4 图纸负责。
    """
    from . import iso as iso_mod

    p = concept["spatial_prototype"]
    d = concept.get("deliberation") or {}
    kind = _massing_kind(concept)
    steps = _evolution(kind)

    # 地面紧贴体量：留白多一圈，体块就小一圈，客户看到的是空白不是房子
    xs = [b[0] for b in steps[-1][2]] + [b[0] + b[3] for b in steps[-1][2]]
    ys = [b[1] for b in steps[-1][2]] + [b[1] + b[4] for b in steps[-1][2]]
    mx = max(1.6, (max(xs) - min(xs)) * 0.12)
    my = max(1.6, (max(ys) - min(ys)) * 0.12)
    ground = (min(xs) - mx, min(ys) - my,
              (max(xs) - min(xs)) + 2 * mx, (max(ys) - min(ys)) + 2 * my)

    s = Svg(1440, 800, title=f"{concept['concept_id']} 体量演变")
    _header(s, f"{concept['concept_name']} · 体量如何形成",
            _fit(d.get("parti") or p.get("spatial_logic") or "", 92),
            "等距轴测 · 体量关系 · 非按比例")

    cell_w = (1440 - 2 * MARGIN) / 4.0
    top = 128
    oy = top + 196.0
    for i, (label, note, boxes, water) in enumerate(steps):
        x0 = MARGIN + i * cell_w
        if i:
            s.line(x0 - 8, top, x0 - 8, 620, stroke=C_RULE, sw=0.8, dash="2 6")
        s.text(x0, top - 26, f"0{i + 1}", size=20, color="#B9BEB4", weight="600")
        s.text(x0 + 34, top - 26, _fit(label, 12), size=14, weight="600")
        yard = (((water[0] + water[2] / 2), (water[1] + water[3] / 2), "院"),
                ) if water[2] > 0 else ()
        _draw_mass_step(s, iso_mod, boxes, water, ox=x0 + cell_w / 2 - 18, oy=oy,
                        scale=min(15.5, cell_w / (ground[2] * 1.16)), ground=ground,
                        yard=yard)
        for j, line in enumerate(_wrap(note, 12, 3)):
            s.text(x0, 646 + j * 20, line, size=12.5, color="#4C534C")

    # 结果格
    x0 = MARGIN + 3 * cell_w
    last_label, last_note, last_boxes, last_water = steps[-1]
    s.line(x0 - 8, top, x0 - 8, 620, stroke=C_RULE, sw=0.8, dash="2 6")
    s.text(x0, top - 26, "04", size=20, color=C_INK, weight="600")
    s.text(x0 + 34, top - 26, "结果：建成后的体量", size=14, weight="600")
    yard = (((last_water[0] + last_water[2] / 2), (last_water[1] + last_water[3] / 2), "院"),
            ) if last_water[2] > 0 else ()
    _draw_mass_step(s, iso_mod, last_boxes, last_water, ox=x0 + cell_w / 2 - 10,
                    oy=oy + 14, scale=min(17.0, cell_w / (ground[2] * 1.02)),
                    ground=ground, yard=yard)
    for j, line in enumerate(_wrap(last_note, 12, 3)):
        s.text(x0, 646 + j * 20, line, size=12.5, color="#4C534C")

    s.line(MARGIN, 716, 1440 - MARGIN, 716, stroke=C_RULE, sw=1)
    s.text(MARGIN, 742, "体量逻辑", size=12, weight="600", color=C_INK)
    s.text(MARGIN + 66, 742, _fit(d.get("massing") or p.get("zoning") or "", 84),
           size=12, color="#4C534C")
    s.text(MARGIN, 766, "界面处理", size=12, weight="600", color=C_INK)
    s.text(MARGIN + 66, 766, _fit(d.get("facade") or "", 84), size=12, color="#4C534C")
    s.text(MARGIN, 784, "体量只表达关系、朝向与层次，不含尺寸、层数与结构结论；须在 S3/S4 用真实条件校核。"
           + "　" + ctx.dimensional_note, size=10, color=C_MUTED)
    return s.render()


# --------------------------------------------------------------------------
# 7. 剖面与竖向（建筑主导：楼层怎么分、光怎么进来）
# --------------------------------------------------------------------------
def _poché(s: Svg, x: float, y: float, w: float, h: float, *,
           fill: str = "#DDD6C4", line: str = "#FFFFFF", step: float = 8.0) -> None:
    """Solid cut face with faint bedding lines.

    斜线填充（hatch）在小尺寸剖面上会溢到轮廓外——线是画在矩形里的，但斜线的
    端点落在矩形之外。现代建筑剖面本来就多用实心 poché，于是改用实填 + 极细的
    水平分层线：既读得出"这是被剖到的实体"，又不会脏了整张图。
    """
    s.rect(x, y, w, h, fill=fill, stroke="#4A4F4B", sw=0.9, rx=0)
    yy = y + step
    while yy < y + h - 1:
        s.line(x + 1, yy, x + w - 1, yy, stroke=line, sw=0.5)
        yy += step


def _person(s: Svg, x: float, ground: float, height: float, *,
            color: str = "#B4AC9A") -> None:
    """A 1.7 m silhouette: the only thing on the sheet that gives real scale."""
    h = height
    head_r = h * 0.075
    s.circle(x, ground - h + head_r, head_r, fill=color, stroke="none")
    body_top = ground - h + head_r * 2
    s.polygon([(x - h * 0.085, body_top), (x + h * 0.085, body_top),
               (x + h * 0.07, ground - h * 0.42), (x - h * 0.07, ground - h * 0.42)],
              fill=color)
    s.polygon([(x - h * 0.07, ground - h * 0.42), (x - h * 0.012, ground - h * 0.42),
               (x - h * 0.012, ground), (x - h * 0.062, ground)], fill=color)
    s.polygon([(x + h * 0.012, ground - h * 0.42), (x + h * 0.07, ground - h * 0.42),
               (x + h * 0.062, ground), (x + h * 0.012, ground)], fill=color)


def section(concept: Dict[str, Any], ctx: Any) -> str:
    """剖面：楼板有厚度、墙被剖开、人在里面、光从一侧进来。

    上一版剖面只有几条水平线和一个箭头：读起来像"层数示意"，不像剖面。剖面
    之所以是概念阶段最硬的图，是因为它同时回答了三个问题——**每层承担什么、
    哪一处是通的、光从哪个面进来**。这三件事都必须画出来才成立。

    没有尺寸：层高按关系等分，图注写明"不含层高尺寸"。
    """
    p = concept["spatial_prototype"]
    d = concept.get("deliberation") or {}
    kind = _massing_kind(concept)
    prog = list(d.get("levels_program") or [])
    levels = max(2, min(3, len(prog) or 3))

    s = Svg(1440, 820, title=f"{concept['concept_id']} 剖面与楼层")
    _header(s, f"{concept['concept_name']} · 剖面",
            _fit(d.get("section") or "", 96), "剖面示意 · 非按比例 · 不含层高尺寸")

    ground = 700
    base_x, span = 300, 620
    storey = 132
    wall = 13
    slab = 9
    right = base_x + span

    # ---- 地坪与覆土 ----
    _poché(s, base_x - wall, ground, span + 2 * wall, 26)
    s.line(base_x - wall, ground, right + wall, ground, stroke=C_INK, sw=2.2)
    s.text(base_x - wall, ground + 42, "室外地坪 ±0", size=10, color=C_MUTED)

    # ---- 层：楼板 + 外墙剖面 ----
    for i in range(levels + 1):
        y = ground - i * storey
        _poché(s, base_x - wall, y - slab / 2, span + 2 * wall, slab, step=7)
    for x in (base_x - wall, right):
        _poché(s, x, ground - levels * storey, wall, levels * storey, step=7)

    # ---- 通高 / 挑空：按策略放在不同位置 ----
    void_w = 148
    void_x = base_x + span * 0.52
    if kind in ("courtyard_carved", "default"):
        # 院井：从屋顶通到地面，两侧楼板断开
        s.rect(void_x, ground - levels * storey + slab, void_w,
               levels * storey - slab, fill="#F4F7F1", stroke="none", rx=0)
        s.rect(void_x, ground - 26, void_w, 26, fill="#C6D8C4", stroke="none", rx=0)
        s.text(void_x + void_w / 2, ground - levels * storey + 30, "院 · 通高",
               size=11, color=C_ACCENT, anchor="middle", weight="600")
        for i in range(1, levels):
            y = ground - i * storey
            s.rect(void_x, y - slab / 2, void_w, slab, fill="#F4F7F1", stroke="none", rx=0)
    elif kind == "floating":
        s.rect(base_x, ground - storey + slab, span, storey - slab,
               fill="#F4F3EC", stroke="none", rx=0)
        s.text(base_x + 16, ground - storey + 34, "架空层：净高压低，只走人",
               size=11, color=C_MUTED)
        for cx in (base_x + 90, base_x + span - 110):
            s.rect(cx, ground - storey + slab, 16, storey - slab, fill="#D8D1BE",
                   stroke="#4A4F4B", sw=0.8, rx=0)
    elif kind == "stepped":
        # 退台：每层右侧缩进，露台在剖面上是一个缺口
        for i in range(1, levels):
            s.rect(right - i * 62, ground - i * storey - slab, i * 62, slab,
                   fill="#FBFBFA", stroke="none", rx=0)
            s.text(right - i * 62 + 5, ground - i * storey - 12, "露台", size=9.5,
                   color=C_ACCENT)

    # ---- 家具与人的尺度 ----
    furn = ("床", "起居", "厨岛")
    for i in range(levels):
        gy = ground - i * storey
        bx0 = base_x + 40
        s.rect(bx0, gy - 34, 96, 34, fill="#CFC7B4", stroke="#8F8776", sw=0.8, rx=1)
        s.text(bx0 + 48, gy - 12, furn[min(i, 2)], size=9.5, color="#585347",
               anchor="middle")
        s.rect(bx0 + 150, gy - 26, 60, 26, fill="#D6CFBD", stroke="#8F8776", sw=0.8, rx=1)
    _person(s, base_x + 300, ground, storey * 0.62)
    _person(s, base_x + 330, ground - storey, storey * 0.62)

    # ---- 楼梯（层间联系，切到就画）----
    for i in range(levels):
        y0 = ground - i * storey - slab / 2
        sx0 = base_x + span - 176
        for k in range(8):
            s.line(sx0 + k * 12, y0 - k * (storey - slab) / 8,
                   sx0 + k * 12, y0 - slab, stroke="#9A9382", sw=0.9)
        s.line(sx0, y0, sx0 + 8 * 12, y0 - (storey - slab), stroke="#6E746C", sw=1.2)

    # ---- 光：从右侧进入，带落点 ----
    for i in range(levels):
        y = ground - i * storey - storey * 0.55
        s.line(right + 82, y - 62, right - 6, y, stroke=C_LIGHT, sw=2.0, arrow=True)
    s.text(right + 96, ground - levels * storey - 20, "主要采光面", size=10,
           color=C_LIGHT, anchor="start")
    if kind in ("courtyard_carved", "default"):
        for i in range(levels):
            y = ground - i * storey - storey * 0.5
            s.line(void_x + void_w / 2, ground - levels * storey - 40, void_x + void_w / 2,
                   y, stroke=C_LIGHT, sw=1.4, dash="7 5", arrow=True)
        s.text(void_x + void_w / 2 + 8, ground - levels * storey - 46, "顶部采光",
               size=10, color=C_LIGHT)

    # ---- 右侧：层标注 ----
    for i in range(levels):
        y = ground - i * storey
        label = prog[i] if i < len(prog) else f"第 {i + 1} 层"
        s.text(base_x - wall - 14, y + slab / 2 - 6, f"L{i + 1}", size=13,
               weight="600", anchor="end")
        for j, line in enumerate(_wrap(label, 7, 2)):
            s.text(base_x - wall - 14, y + slab / 2 + 12 + j * 14, line, size=10,
                   color=C_MUTED, anchor="end")

    # ---- 图例（顶部横排，与剖面拉开距离）----
    lx, ly = 300, 154
    _poché(s, lx, ly, 26, 12, step=5)
    s.text(lx + 34, ly + 11, "被剖到的楼板与墙体", size=11, color=C_MUTED)
    s.rect(lx + 216, ly, 26, 12, fill="#F4F7F1", stroke="#C6D8C4", sw=0.9, rx=0)
    s.text(lx + 250, ly + 11, "通高 / 院井", size=11, color=C_MUTED)
    s.line(lx + 372, ly + 6, lx + 408, ly + 6, stroke=C_LIGHT, sw=2.0, arrow=True)
    s.text(lx + 416, ly + 11, "光的方向", size=10.5, color=C_LIGHT)
    _person(s, lx + 520, ly + 14, 26)
    s.text(lx + 538, ly + 11, "人体尺度 1.7 m", size=11, color=C_MUTED)

    # ---- 右栏：这张剖面在说什么 ----
    rx = 1000
    s.line(rx - 26, 200, rx - 26, 700, stroke=C_RULE, sw=0.8)
    s.text(rx, 218, "这张剖面在说什么", size=13, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(
            "楼板被剖开，能数出几层；院井从屋顶通到地面，光从上面下来；"
            "楼梯沿院边折上，每一层都在同一侧到达。", 24, 4)):
        s.text(rx, 244 + i * 21, line, size=12, color="#3C443E")

    s.text(rx, 366, "竖向关系", size=12.5, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(d.get("section") or "未给出竖向关系", 24, 3)):
        s.text(rx, 390 + i * 21, line, size=12, color="#3C443E")

    s.text(rx, 486, "专业配合", size=12.5, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(d.get("integration") or "按主导专业推进，其余专业做界面协调。",
                                   24, 3)):
        s.text(rx, 510 + i * 21, line, size=12, color="#3C443E")

    # ---- 底栏 ----
    s.line(MARGIN, 756, 1440 - MARGIN, 756, stroke=C_RULE, sw=1)
    s.text(MARGIN, 780,
           "剖面表达楼层分工与通高关系：层高按关系等分，不含尺寸、结构构件与管线结论；"
           "结构与设备须在 S4 依据真实条件复核。", size=10, color=C_MUTED)
    s.text(1440 - MARGIN, 780, ctx.dimensional_note, size=10, color=C_MUTED,
           anchor="end")
    return s.render()


# --------------------------------------------------------------------------
# 7b. 室内剖切轴测（室内主导：空间怎么被重新组织、光落在哪、视线通到哪）
# --------------------------------------------------------------------------
def axon(concept: Dict[str, Any], ctx: Any) -> str:
    """室内剖切轴测：切掉两面墙的盒子，家具、界面与光一起看。

    室内不能用建筑的体块图：体量图回答"这栋楼长什么样"，而室内要回答的是
    "站在客厅能看见什么、光落在哪一面、哪一段是没有隔断的"。所以这里画的是
    **一个被切开的房间**：地面、两面内墙、家具块、光斑与视线。

    没有真实几何，所以只表达关系——进深分几段、通高在哪、视线是否被挡。图注
    写明"不含开间进深尺寸"。
    """
    from . import iso as iso_mod

    d = concept.get("deliberation") or {}
    mats = [str(m.get("name") or "") for m in (concept.get("material_direction") or [])][:3]
    light = (concept.get("lighting_direction") or [""])[0]

    s = Svg(1440, 860, title=f"{concept['concept_id']} 空间轴测")
    _header(s, f"{concept['concept_name']} · 剖切轴测",
            _fit(d.get("parti") or concept.get("concept_statement") or "", 96),
            "剖切轴测 · 关系示意 · 不含开间进深尺寸")

    # 房间尺寸用关系量：8 米面宽、6 米进深、3 米净高
    RW, RD, RH = 8.0, 6.0, 3.0
    scale = 44.0
    iso = iso_mod.Iso(420, 400, scale=scale, z_scale=scale * 0.92)

    # 地面
    iso_mod.draw_ground(iso, s, 0, 0, RW, RD, fill="#EFEBE1", edge="#B9B3A3", grid=0)
    # 地面分格：木地板方向，暗示铺装
    for i in range(1, 16):
        s.line(*iso.p(RW * i / 16, 0, 0), *iso.p(RW * i / 16, RD, 0),
               stroke="#E0DACA", sw=0.6)

    # 两面内墙（切掉靠近观察者的两面）
    back = iso.pts([(0, 0, 0), (RW, 0, 0), (RW, 0, RH), (0, 0, RH)])
    side = iso.pts([(0, 0, 0), (0, RD, 0), (0, RD, RH), (0, 0, RH)])
    s.polygon(back, fill="#E4DFD2", stroke="#4A4F4B", sw=1.3)
    s.polygon(side, fill="#D6D0C0", stroke="#4A4F4B", sw=1.3)

    # 后墙上的洞口：一扇窗（光从这面进来）+ 一条通高
    wx0, wx1 = RW * 0.48, RW * 0.86
    win = iso.pts([(wx0, 0, 1.0), (wx1, 0, 1.0), (wx1, 0, 2.5), (wx0, 0, 2.5)])
    s.polygon(win, fill="#DCEBF2", stroke="#7FA5B8", sw=1.2)
    gf = s.gradient("gl", [(0.0, "#FFFFFF"), (1.0, "#CFE3EC")], x2=0, y2=1)
    s.polygon(win, fill=gf, stroke="none", opacity=0.75)

    # 家具：按"起居—餐—卧室"三段布置，这一段是否连通一眼可见
    blocks = [
        (0.6, 4.2, 0, 2.2, 1.0, 0.45, "#CFC7B2"),     # 沙发
        (3.2, 3.6, 0, 1.2, 1.2, 0.32, "#BDB4A0"),     # 茶几
        (5.4, 3.8, 0, 2.2, 1.0, 0.75, "#C7BEA8"),     # 长桌
        (0.6, 0.4, 0, 2.4, 0.6, 2.2, "#D2CAB6"),      # 通高柜
        (4.4, 0.4, 0, 2.0, 0.6, 1.9, "#C9C0AB"),      # 书柜
    ]
    for (x, y, z, w, dd, h, fill) in sorted(
            blocks, key=lambda b: iso.depth(b[0] + b[3] / 2, b[1] + b[4] / 2, b[2])):
        iso_mod.draw_shadow(iso, s, x, y, w, dd, dx=0.35, dy=0.35, opacity=0.10)
        iso_mod.draw_box(iso, s, x, y, z, w, dd, h, fill=fill, edge="#3A3F44", sw=0.9)

    # 光：从窗进来，落在地面上的一块梯形
    beam = iso.pts([(wx0, 0, 1.0), (wx1, 0, 1.0), (wx1 + 1.2, 2.6, 0), (wx0 + 0.6, 2.6, 0)])
    gt = s.gradient("beam", [(0.0, "#F3C97A"), (1.0, "#F7E7C4")], x2=0, y2=1)
    s.polygon(beam, fill=gt, stroke="none", opacity=0.34)
    s.text(*iso.p((wx0 + wx1) / 2, -0.35, 2.72), "主要采光面", size=11.5,
           color="#A9701F", anchor="middle")

    # 视线：站位 → 窗 → 室外（能不能看见天空）
    eye = iso.p(4.6, 5.0, 1.55)
    target = iso.p((wx0 + wx1) / 2, 0.0, 1.9)
    s.line(eye[0], eye[1], target[0], target[1], stroke=C_CIRC, sw=1.4, dash="7 5",
           arrow=True)
    s.circle(eye[0], eye[1], 4.5, fill=C_CIRC, stroke="none")
    s.text(eye[0] - 6, eye[1] + 26, "站这里看", size=10.5, color=C_CIRC, anchor="middle")

    # 无隔断的一段：用地面箭头说明"连续的空间"
    a0 = iso.p(1.4, 2.1, 0.02)
    a1 = iso.p(7.6, 2.1, 0.02)
    s.line(a0[0], a0[1], a1[0], a1[1], stroke=C_ACCENT, sw=2.0, arrow=True)
    s.text((a0[0] + a1[0]) / 2, a0[1] - 12, "连续空间：一盏灯到底", size=11,
           color=C_ACCENT, anchor="middle")

    # ---- 右侧说明 ----
    rx = 790
    s.line(rx - 26, 150, rx - 26, 720, stroke=C_RULE, sw=0.8)
    s.text(rx, 168, "这张图在说什么", size=13, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(
            "切掉靠观察者的两面墙，剩下的是一段连续的空间：从哪里坐下、光落在哪块"
            "地面、视线能不能穿到窗。蓝色虚线是站立位置看向窗的视线。", 24, 4)):
        s.text(rx, 194 + i * 21, line, size=12, color="#3C443E")

    s.text(rx, 320, "界面与材料", size=12.5, weight="600", color=C_INK)
    if mats:
        for i, m in enumerate(mats):
            s.rect(rx, 334 + i * 32, 11, 19, fill="#D8D1BE", stroke="#9A9382", sw=0.6, rx=1)
            s.text(rx + 20, 349 + i * 32, _fit(m, 18), size=12, color="#3C443E")
    else:
        s.text(rx, 334, "本方案未指定材料方向。", size=11.5, color=C_MUTED)

    s.text(rx, 462, "光", size=12, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(light or "未指定采光方向", 24, 3)):
        s.text(rx, 486 + i * 21, line, size=12, color="#3C443E")

    s.text(rx, 590, "剖面关系", size=12, weight="600", color=C_INK)
    for i, line in enumerate(_wrap(d.get("section") or "未给出竖向关系", 24, 3)):
        s.text(rx, 614 + i * 21, line, size=12, color="#3C443E")

    # ---- 底栏 ----
    s.line(MARGIN, 776, 1440 - MARGIN, 776, stroke=C_RULE, sw=1)
    s.text(MARGIN, 800,
           "轴测只表达空间关系、视线与光的落点：不含开间进深、净高与家具尺寸；"
           "尺寸与定位须在 S3 平面与 S4 深化中确定。", size=10, color=C_MUTED)
    s.text(1440 - MARGIN, 800, ctx.dimensional_note, size=10, color=C_MUTED,
           anchor="end")
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


def _blob_path(cx: float, cy: float, rx: float, ry: float, *, seed: int = 1,
               n: int = 10) -> str:
    """A smooth organic outline — water and planting beds are never rectangles."""
    import math

    pts = []
    for i in range(n):
        ang = i / n * math.tau
        k = 1 + 0.13 * math.sin(ang * 3 + seed * 1.3) + 0.06 * math.sin(ang * 5 + seed * 2.1)
        pts.append((cx + math.cos(ang) * rx * k, cy + math.sin(ang) * ry * k))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(1, len(pts) + 1):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i % len(pts)]
        d += f" Q {x0:.1f} {y0:.1f} {(x0 + x1) / 2:.1f} {(y0 + y1) / 2:.1f}"
    return d + " Z"


def _paving(s: Svg, x: float, y: float, w: float, h: float, *, fill: str = "#E5DFD1",
            joint: str = "#C9C1AD", step: float = 26.0) -> None:
    """Hard paving: a filled area with a joint grid, not a beige rectangle."""
    s.rect(x, y, w, h, fill=fill, stroke=joint, sw=1.0, rx=0)
    ny = int(h // step)
    nx = int(w // step)
    for i in range(1, nx):
        s.line(x + i * step, y, x + i * step, y + h, stroke=joint, sw=0.5)
    for j in range(1, ny):
        s.line(x, y + j * step, x + w, y + j * step, stroke=joint, sw=0.5)


def landscape(concept: Dict[str, Any], ctx: Any) -> str:
    """景观总平面：建筑轮廓、硬质、绿地、乔灌木、水面、园路、活动区，各说各的。

    上一版是"矩形当水池、圆点当树、蓝线当园路"——那是流程图，不是景观图。
    景观总平面之所以能读，靠的是**图面层次**：底（土/草）→ 建筑与铺装（硬）→
    水体（软而深）→ 种植（三种冠幅）→ 路径（双线带缘）→ 标注与指北。
    少任何一层，画面就塌成色块。

    仍然是示意图：不给放线、不给标高、不给面积。面积以分区占比单独列出。
    """
    import math

    from . import iso as iso_mod

    d = concept.get("deliberation") or {}
    zones = d.get("zones") or []
    s = Svg(1440, 900, title=f"{concept['concept_id']} 景观总平面")
    _header(s, f"{concept['concept_name']} · 总平面",
            _fit(d.get("parti") or "", 96), "总平面示意 · 非按比例 · 不放线")

    # ---------------- 左：总平面 ----------------
    px, py, pw, ph = 56, 138, 820, 596
    s.rect(px - 10, py - 10, pw + 20, ph + 20, fill="#FFFFFF", stroke=C_RULE, sw=1, rx=2)

    # 底：草地
    s.rect(px, py, pw, ph, fill="#E8EEE2", stroke="#B9C4B2", sw=1.0, rx=0)
    # 草地的细微纹理：不等距横线，避免大片纯色
    for i in range(1, 15):
        yy = py + ph * i / 15.0
        s.line(px + 4, yy, px + pw - 4, yy, stroke="#DFE7D9", sw=0.5)

    # 建筑轮廓：左上角压住场地一角（院子在房子南侧）
    bx, by, bw, bh = px, py, pw * 0.46, ph * 0.26
    s.rect(bx, by, bw, bh, fill="#CBC5B4", stroke="#4E534E", sw=2.2, rx=0)
    for i in range(1, 8):                     # 建筑用斜线填充，和绿地分开
        s.line(bx + bw * i / 8, by + 2, bx + bw * i / 8 - bh * 0.8, by + bh - 2,
               stroke="#AFA897", sw=0.8)
    s.text(bx + 14, by + 26, "建筑", size=12, color="#4A4F4B", weight="600")
    s.text(bx + 14, by + 44, "（不在本次景观范围内）", size=10, color="#6E736D")

    # 硬质：茶席平台（靠建筑、面向水）
    tx, ty, tw, th = px + pw * 0.56, py + ph * 0.10, pw * 0.28, ph * 0.16
    _paving(s, tx, ty, tw, th, step=24)
    s.text(tx + 10, ty + 20, "茶席 / 停留", size=11, color=C_INK, weight="600")
    s.text(tx + 10, ty + 38, "背靠种植，面向水", size=9.5, color=C_MUTED)

    # 水：有机形 + 岸线 + 涟漪 + 倒影
    wcx, wcy = px + pw * 0.46, py + ph * 0.60
    wrx, wry = pw * 0.20, ph * 0.17
    s.path(_blob_path(wcx, wcy, wrx + 8, wry + 7, seed=3), fill="#DCE7DC",
           stroke="#B9C4B2", sw=1.0)
    s.path(_blob_path(wcx, wcy, wrx, wry, seed=3), fill="#BBD6E2", stroke="#7FA5B8", sw=1.2)
    s.path(_blob_path(wcx - wrx * 0.10, wcy - wry * 0.12, wrx * 0.62, wry * 0.56, seed=5),
           fill="#CFE3EC", stroke="none", opacity=0.9)
    for i in range(1, 4):
        s.path(_blob_path(wcx, wcy, wrx * (1 - i * 0.16), wry * (1 - i * 0.15), seed=3),
               fill="none", stroke="#FFFFFF", sw=0.9, opacity=0.55)
    s.text(wcx, wcy + 4, "静水", size=13, color="#2F6F8A", anchor="middle", weight="600")
    s.text(wcx, wcy + 22, "水底铺深色砾石", size=9.5, color="#3F7C93", anchor="middle")

    # 种植：边界乔木带（冠幅不等）+ 点景树 + 灌木丛
    tree_pts = ([(px + 26, py + ph - 34 - i * 92) for i in range(5)]
                + [(px + pw - 40 - i * 116, py + ph - 30) for i in range(4)]
                + [(px + pw - 44, py + 60 + i * 110) for i in range(3)])
    for k, (tx2, ty2) in enumerate(tree_pts):
        iso_mod.canopy_plan(s, tx2, ty2, 26 + (k % 3) * 5, seed=k + 2,
                            fill="#B7CCA8", edge="#87A276")
    iso_mod.canopy_plan(s, px + pw * 0.78, py + ph * 0.42, 32, seed=9,
                        fill="#B7CCA8", edge="#87A276")
    iso_mod.canopy_plan(s, px + pw * 0.30, py + ph * 0.86, 24, seed=4,
                        fill="#C2D5B4", edge="#87A276")


    # 灌木：顺着水岸东侧成一串，不散落成点
    for k in range(7):
        ang = -0.5 + k * 0.30
        sx = wcx + (wrx + 22) * math.cos(ang) * 1.05
        sy = wcy + (wry + 20) * math.sin(ang) * 1.05
        iso_mod.shrub_plan(s, sx, sy, 10 + (k % 3) * 2, seed=k)

    # 园路：入口（南）→ 沿水西侧绕行 → 平台。**不能穿水**：这是上一版最刺眼的错。
    road = [(px + pw * 0.30, py + ph - 6), (px + pw * 0.26, py + ph * 0.82),
            (px + pw * 0.15, py + ph * 0.62), (px + pw * 0.14, py + ph * 0.40),
            (px + pw * 0.28, py + ph * 0.30), (px + pw * 0.56, py + ph * 0.24)]
    for off in (-7, 7):
        pts = [(x + off, y) for x, y in road]
        s.polyline(pts, stroke="#B2A78E", sw=1.4, arrow=False)
    s.polyline(road, stroke="#EFE8D6", sw=11.0, arrow=False)
    s.polyline(road, stroke="#C9BEA4", sw=0.9, arrow=False)
    s.text(px + pw * 0.045, py + ph * 0.50, "园路 900–1200", size=10, color="#6B6455")

    # 入口
    s.polygon([(px + pw * 0.30 - 16, py + ph + 10), (px + pw * 0.30 + 16, py + ph + 10),
               (px + pw * 0.30, py + ph - 14)], fill="#8C7F63")
    s.text(px + pw * 0.30, py + ph + 28, "入口", size=11, color="#6B6455", anchor="middle")

    # 图面辅助：指北 + 比例条
    iso_mod.north_arrow(s, px + pw - 34, py + 40, size=24, color="#4A4F4B")
    iso_mod.scale_bar(s, px + 22, py + ph + 12, 120, seg_m=5, segments=2,
                      color="#4A4F4B")

    # ---------------- 右上：分区占比 ----------------
    bx2, by2 = 916, 168
    s.text(bx2, by2 - 22, "分区占比", size=13, weight="600")
    s.text(bx2, by2 - 4, "取自本方案声明的分区，未声明的不补", size=9.5, color=C_MUTED)
    if zones:
        total = max(1, len(zones))
        for i, z in enumerate(zones):
            y = by2 + 14 + i * 46
            name = str(z.get("name") or "")
            share = str(z.get("share") or "")
            s.rect(bx2, y, 468, 34, fill=_zone_fill(name), stroke="#D4D0C4", sw=0.8, rx=2)
            s.text(bx2 + 12, y + 22, _fit(name, 15), size=12.5, color=C_INK)
            s.text(bx2 + 456, y + 22, share, size=12, color="#5C6157", anchor="end")
    else:
        s.text(bx2, by2 + 16, "本方案未给分区占比：不编面积。", size=11, color=C_RISK)

    # ---------------- 右下：图例 ----------------
    lx, ly = 916, 470
    s.text(lx, ly - 14, "图例", size=12, weight="600", color=C_INK)
    s.rect(lx, ly, 22, 14, fill="#D9D6CE", stroke="#5A5F5B", sw=1.2, rx=0)
    s.text(lx + 32, ly + 12, "建筑轮廓", size=11.5, color="#4F554F")
    _paving(s, lx, ly + 26, 22, 14, step=8)
    s.text(lx + 32, ly + 40, "硬质铺装", size=11.5, color="#4F554F")
    s.path(_blob_path(lx + 11, ly + 59, 11, 7, seed=3), fill="#BBD6E2", stroke="#7FA5B8", sw=1)
    s.text(lx + 32, ly + 68, "静水面", size=11.5, color="#4F554F")
    iso_mod.canopy_plan(s, lx + 11, ly + 86, 11, seed=3, shadow=False)
    s.text(lx + 32, ly + 96, "乔木（冠幅）", size=11.5, color="#4F554F")
    iso_mod.shrub_plan(s, lx + 11, ly + 110, 7, seed=1)
    s.text(lx + 32, ly + 124, "灌木 / 地被", size=11.5, color="#4F554F")
    s.line(lx, ly + 130, lx + 22, ly + 130, stroke="#F3EFE4", sw=8)
    s.line(lx, ly + 130, lx + 22, ly + 130, stroke="#CFC5AE", sw=0.8)
    s.text(lx + 32, ly + 148, "园路", size=11.5, color="#4F554F")

    # ---------------- 底栏：做法三行 ----------------
    y0 = 796
    s.line(MARGIN, y0 - 22, 1440 - MARGIN, y0 - 22, stroke=C_RULE, sw=1)
    for i, (label, key) in enumerate((("水景", "water"), ("植物", "planting"),
                                      ("铺装", "paving"))):
        x = MARGIN + i * 460
        s.text(x, y0, label, size=11, weight="600", color=C_INK)
        val = str(d.get(key) or "未设定")
        for j, line in enumerate(_wrap(val, 30, 2)):
            s.text(x + 40, y0 + j * 17, line, size=11, color=C_MUTED)
    s.text(MARGIN, 872, "总平面为关系示意：不给放线、标高与面积；面积以分区占比单列，"
           "施工图阶段的竖向与定位须由持证专业人员按现场条件出图。",
           size=10, color=C_MUTED)
    return s.render()


# --------------------------------------------------------------------------
DIAGRAM_KINDS = ("functional", "zoning", "circulation", "daylight", "sequence",
                 "massing", "section", "landscape", "axon")


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
            # 室内不套建筑的体块图：体量回答的是"这栋楼长什么样"。
            # 室内先给剖切轴测（空间重组、视线、光的落点），有房间级数据时
            # 再补分区/动线/采光；没有就只留轴测与序列——不拿任务书原句填满图框。
            want = (["axon", "zoning", "circulation", "daylight", "sequence"]
                    if has_rooms else ["axon", "sequence"])
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
        "axon": lambda: axon(concept, ctx),
    }
    titles = {
        "functional": "功能关系图", "zoning": "分区图", "circulation": "动线概念图",
        "daylight": "采光策略图", "sequence": "空间序列图", "massing": "体量概念图",
        "section": "剖面与楼层图", "landscape": "景观总平面",
        "axon": "室内剖切轴测",
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
           "apply_theme", "reset_theme", "LINE_W",
           "functional_relations", "zoning", "circulation", "daylight",
           "sequence", "massing", "section", "landscape", "axon", "Group"]
