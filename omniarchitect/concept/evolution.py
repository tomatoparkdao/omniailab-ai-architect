"""概念推敲：按专业讲清"这套方案凭什么成立"。

为什么要有这个模块
------------------
v1.14 的概念推敲页与动画是同一套东西：四个固定体块，从"占满"到"连桥"。
建筑项目还能看，室内与景观就变成了借别人的故事——酒店室内被演成体块生成，
私家庭院被演成建筑加法。客户一眼就知道那不是在讲他的项目。

这里改成：**步骤由本项目的概念数据推出来**，专业决定"推敲什么"。

* 建筑：场地限界 → 体量分解 → 加入要素 → 结果形态；
* 室内：功能重组 → 空间序列 → 界面与通透 → 核心空间体验；
* 景观：场地与边界 → 空间层次 → 园路与节点 → 水景与种植。

推不出来的情况是存在的（概念里没有分区、没有序列、没有采光策略）。
那时 `plan()` 返回 ``ok=False`` 并说明缺什么，调用方出**静态分析图**，
不出动画——宁可少一个动画，也不拿不相干的推演凑数。

图的画法沿用 `concept/iso.py` 与 `concept/diagrams.py` 的确定性矢量能力，
不引入生成式图像，也不新造一套视觉系统。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import diagrams as dia
from . import iso as iso_mod
from . import layout as layout_mod
from .iso import Iso, draw_box, draw_ground, draw_shadow, tree

#: 专业 → 推敲主线。名字不是装饰：它决定画什么、讲解什么。
DISCIPLINE_STEPS: Dict[str, Tuple[str, ...]] = {
    "architecture": ("场地与限界", "体量分解", "加入要素", "结果形态"),
    "interior": ("功能重组", "空间序列", "界面与通透", "核心空间"),
    "landscape": ("场地与边界", "空间层次", "园路与节点", "水景与种植"),
}

DISCIPLINE_CN = {"architecture": "建筑", "interior": "室内", "landscape": "景观"}

@dataclass
class Step:
    n: str
    name: str
    note: str
    scene: str
    #: 依据取自概念的哪个字段，便于追溯
    basis: str = ""


@dataclass
class Plan:
    discipline: str = "architecture"
    steps: List[Step] = field(default_factory=list)
    ok: bool = False
    reason: str = ""
    family: str = "cluster"
    labels: List[str] = field(default_factory=list)
    #: 室内/景观的几何（`concept/layout.py`）。主图与四步图共用这一份，
    #: 所以两张图上的大堂、走廊、茶座必然在同一位置。建筑为空。
    frames: List[layout_mod.Frame] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"discipline": self.discipline, "ok": self.ok, "reason": self.reason,
                "family": self.family, "labels": list(self.labels),
                "steps": [{"n": s.n, "name": s.name, "note": s.note,
                           "scene": s.scene, "basis": s.basis} for s in self.steps]}


# --------------------------------------------------------------------------
# 从概念数据推步骤
# --------------------------------------------------------------------------
def _drop_prefix(text: str) -> str:
    """去掉"教育建筑：""酒店与住宿工装："这类类型前缀。

    这些前缀在报告里有用（说明这是哪一类项目），放到图上就是废话：
    图注要讲的是这一步做了什么，不是复述项目类型。
    """
    t = str(text or "").strip()
    for sep in ("：", ":"):
        if sep in t:
            head, tail = t.split(sep, 1)
            if 2 <= len(head) <= 12 and tail.strip():
                return tail.strip()
    return t


def _clauses(text: Any, n: int = 3, width: int = 34) -> List[str]:
    """把一段策略文字切成短句。图上的字必须短，长句一律截到能读的程度。"""
    raw = str(text or "").replace("\n", "；")
    parts: List[str] = []
    for chunk in raw.replace("。", "；").split("；"):
        chunk = _drop_prefix(chunk.strip(" ，、"))
        if len(chunk) < 4:
            continue
        parts.append(_short(chunk, width))
        if len(parts) >= n:
            break
    return parts


def _short(text: str, n: int = 20) -> str:
    """切短句：优先在句读处断，断不开才加省略号，且只加一个。"""
    t = " ".join(str(text or "").split())
    if len(t) <= n:
        return t
    for sep in ("，", "、", "："):
        head = t.split(sep)[0]
        if 6 <= len(head) <= n:
            return head
    cut = t[: n + 1]
    for sep in ("，", "、", "；"):
        i = cut.rfind(sep)
        if i >= max(6, int(n * 0.6)):
            return cut[:i]
    return t[: n - 1].rstrip("，、；…") + "…"


def _proto(concept: Dict[str, Any]) -> Dict[str, Any]:
    return concept.get("spatial_prototype") or {}


def _sequence(concept: Dict[str, Any]) -> List[str]:
    """空间序列：优先 experience_sequence，其次 circulation，最后 zoning。"""
    for key in ("experience_sequence", "user_experience"):
        v = concept.get(key)
        if isinstance(v, (list, tuple)) and v:
            return [_short(str(x), 12) for x in v][:5]
        if isinstance(v, str) and v.strip():
            got = [x for x in v.replace("→", "；").replace("；", "；").split("；")
                   if x.strip()]
            if len(got) >= 2:
                return [_short(x.strip(), 12) for x in got][:5]
    proto = _proto(concept)
    for key in ("circulation", "experience"):
        if proto.get(key):
            got = [x for x in str(proto[key]).replace("→", "；").split("；")
                   if x.strip()]
            if len(got) >= 2:
                return [_short(x.strip(), 12) for x in got][:5]
    return []


def plan(concept: Dict[str, Any], discipline: str = "architecture", *,
         sector: str = "") -> Plan:
    """推导这套概念的推敲步骤。数据不够时明确说缺什么，不硬编故事。"""
    disc = discipline if discipline in DISCIPLINE_STEPS else "architecture"
    proto = _proto(concept)
    family = str(proto.get("family") or "cluster")
    names = DISCIPLINE_STEPS[disc]

    zoning = _clauses(proto.get("zoning") or proto.get("spatial_logic"), 3, 26)
    circ = _sequence(concept)
    light = _clauses(proto.get("daylight"), 2, 24)
    core = _clauses(concept.get("concept_statement"), 1, 44)
    merits = _clauses("；".join(str(x) for x in (concept.get("advantages") or [])), 2, 26)

    used: List[str] = []

    def pick(*cands: str) -> str:
        """按顺序取第一条还没用过的说法，避免四步讲同一句话。"""
        for c in cands:
            c = str(c or "").strip()
            if c and c not in used:
                used.append(c)
                return c
        return ""

    out = Plan(discipline=disc, family=family,
               labels=zoning or circ or core)
    if disc in ("interior", "landscape"):
        out.frames = layout_mod.frames(concept, disc, sector=sector)

    # 建筑：体块是主线，至少要有一条分区与一条"为什么"的说法
    if disc == "architecture":
        miss = []
        if not zoning:
            miss.append("体量/分区")
        if not (circ or light):
            miss.append("动线或采光")
        if miss:
            out.reason = "概念里没有" + "、".join(miss) + "，无法做体块推演"
            return out
        out.steps = [
            Step("01", names[0], pick(*(zoning[:1] or [""])), "site", "zoning"),
            Step("02", names[1], pick(*(zoning[1:2] + [proto.get("spatial_logic") or ""])),
                 "split", "spatial_logic"),
            Step("03", names[2], pick(*(circ[:1] + light[:1])), "add", "circulation"),
            Step("04", names[3], pick(*(core + merits)), "done", "statement"),
        ]
        out.ok = True
        return out

    # 室内：功能重组 → 序列 → 界面 → 核心。序列缺了，这一页就没有主线。
    if disc == "interior":
        miss = []
        if not zoning:
            miss.append("功能分区")
        if not circ:
            miss.append("空间序列（人怎么走）")
        if not out.frames:
            miss.append("平面组织方式")
        if miss:
            out.reason = "概念里没有" + "、".join(miss) + "，无法做室内推敲"
            return out
        out.steps = [
            Step("01", names[0], pick(*(zoning[:2] + ["按使用把空间重新分组"])), "zones",
                 "zoning"),
            Step("02", names[1], pick(" → ".join(circ[:4]) if circ else "",
                                      proto.get("circulation") or ""), "sequence",
                 "experience_sequence"),
            Step("03", names[2], pick(*(light[:1] + ["界面开合与视线控制"])),
                 "threshold", "daylight"),
            Step("04", names[3], pick(*(core + merits)), "core", "statement"),
        ]
        out.ok = True
        return out

    # 景观：场地 → 层次 → 园路 → 水景种植。没有场地关系就不是景观推敲。
    miss = []
    if not (zoning or proto.get("zoning")):
        miss.append("场地与分区")
    if not (circ or proto.get("daylight")):
        miss.append("游线或视线")
    if not out.frames:
        miss.append("场地组织方式")
    if miss:
        out.reason = "概念里没有" + "、".join(miss) + "，无法做景观推敲"
        return out
    out.steps = [
        Step("01", names[0], pick(*(zoning[:1] or [""])), "site", "zoning"),
        Step("02", names[1], pick(*(zoning[1:2] + light[:1])), "layers", "daylight"),
        Step("03", names[2], pick(" → ".join(circ[:3]) if circ else "",
                                  proto.get("circulation") or ""), "paths",
             "circulation"),
        Step("04", names[3], pick(*(core + merits)), "water", "statement"),
    ]
    out.ok = True
    return out


def applicable(concept: Dict[str, Any], discipline: str = "architecture") -> Tuple[bool, str]:
    """能不能给这个项目出"设计演变"动画。不能就说明原因，调用方出静态图。"""
    p = plan(concept, discipline)
    if not p.ok:
        return False, p.reason
    if len(p.steps) < 3:
        return False, "步骤不足以讲清演变"
    return True, ""


# --------------------------------------------------------------------------
# 场景：每种专业各一套画法
# --------------------------------------------------------------------------
Pal = Dict[str, str]


def _canvas(w: int, h: int) -> "dia.Svg":
    return dia.Svg(w, h, title="")


def _scene_body(step: Step, plan_obj: Plan, pal: Pal, w: int, h: int,
                concept: Optional[Dict[str, Any]] = None) -> str:
    """返回一段 SVG 内容（不含 <svg> 外壳），供静态四联与动画共用。"""
    if plan_obj.discipline == "architecture" or not plan_obj.frames:
        return _arch_body(step, plan_obj, pal, w, h)
    s = _canvas(w, h)
    frame = plan_obj.frames[0]
    # 与主推图同一段代码、同一份几何，只是按步显形。四步不动任何已定区域。
    # 下方留 22 px：入口标签在框外，不留就会被 viewBox 裁掉。
    layout_mod.draw(s, frame, (3.0, 3.0, float(w) - 6.0, float(h) - 25.0), pal,
                    step=STEP_INDEX.get(step.scene, 0),
                    label_size=12.0 if w >= 380 else 10.0, detail=False)
    return "".join(s.body)


#: 场景 → 第几步（0 起）。布局里的 appear 用这个序号。
STEP_INDEX = {"site": 0, "zones": 0, "split": 1, "sequence": 1, "layers": 1,
              "add": 2, "threshold": 2, "paths": 2, "done": 3, "core": 3,
              "water": 3}


def _frame(s: Any, w: int, h: int, pal: Pal, *, pad: float = 18.0) -> Tuple[float, float, float, float]:
    """画一块底板，返回 (x0, y0, w, h)。"""
    x0, y0 = pad, pad
    bw, bh = w - pad * 2, h - pad * 2
    s.rect(x0, y0, bw, bh, fill=pal.get("ground", "#F3F1E9"),
           stroke=pal.get("line", "#D6D2C6"), sw=1.0)
    return x0, y0, bw, bh


def _label(s: Any, x: float, y: float, text: str, *, size: float = 11.0,
           color: str = "", anchor: str = "start", weight: str = "400") -> None:
    if not str(text or "").strip():
        return
    s.text(x, y, str(text), size=size, color=color or "#6E736A", anchor=anchor,
           weight=weight)


# ---------------- 建筑：等距体块 ----------------
def _arch_body(step: Step, p: Plan, pal: Pal, w: int, h: int) -> str:
    s = _canvas(w, h)
    boxes = _arch_boxes(p.family)
    iso = Iso(w * 0.5, h * 0.30, scale=min(w, h) / 44.0, z_scale=1.0)
    draw_ground(iso, s, 2, 0, 54, 40, fill=pal.get("ground", "#F2F0E8"),
                edge=pal.get("line", "#D6D2C6"), grid=0)
    take = {"site": 0, "split": 2, "add": 3, "done": len(boxes)}.get(step.scene, len(boxes))
    if step.scene == "site":
        # 先把"能建到哪儿"画出来：退界范围内的虚线 + 一句说明
        s.polygon(iso.pts([(6, 2, 0.04), (52, 2, 0.04), (52, 38, 0.04), (6, 38, 0.04)]),
                  fill="none", stroke=pal.get("accent", "#2F5D45"), sw=1.4,
                  dash="7 5")
        ax, ay = iso.p(29, 20, 0)
        s.text(ax, ay, "可建范围", size=11, color=pal.get("accent", "#2F5D45"),
               anchor="middle")
    if step.scene != "site":
        s.polygon(iso.pts([(8, 17, 0.05), (48, 17, 0.05), (48, 23, 0.05), (8, 23, 0.05)]),
                  fill=pal.get("court", "#EFE3D2"), stroke="none", sw=0)
    for name, box in list(boxes.items())[:take]:
        x, y, z, bw, bd, bh = box
        draw_shadow(iso, s, x, y, bw, bd, opacity=0.10)
        draw_box(iso, s, x, y, z, bw, bd, bh, fill=pal.get("mass", "#E4EDE3"),
                 edge=pal.get("ink", "#1E2328"), sw=1.2)
        _label(s, iso.p(x + bw / 2, y + bd / 2, bh)[0],
               iso.p(x + bw / 2, y + bd / 2, bh)[1] - 4, name, size=9.5,
               color=pal.get("ink", "#1E2328"), anchor="middle")
    if step.scene in ("add", "done"):
        for tx, ty in ((5, 2), (52, 6), (6, 37), (51, 36)):
            tree(iso, s, tx, ty, r=0.55, h=2.0, crown=pal.get("green", "#C6D6BE"))
    return "".join(s.body)


def _arch_boxes(family: str) -> Dict[str, Tuple[float, float, float, float, float, float]]:
    """家族 → 体块。名字用于图上标注，是"块在干什么"，不是房间名。"""
    table = {
        "linear": {"主体": (8, 4, 0, 40, 13, 10), "南翼": (8, 23, 0, 40, 13, 10),
                   "连接体": (16, 17, 0, 24, 6, 8)},
        "cluster": {"组团 1": (8, 4, 0, 17, 13, 10), "组团 2": (31, 4, 0, 17, 13, 10),
                    "组团 3": (8, 23, 0, 17, 13, 7), "共享体": (31, 23, 0, 17, 13, 9)},
        "courtyard": {"北翼": (8, 3, 0, 40, 9, 9), "南翼": (8, 28, 0, 40, 9, 9),
                      "西翼": (8, 12, 0, 9, 16, 8), "东翼": (39, 12, 0, 9, 16, 8)},
        "radial": {"主馆": (18, 14, 0, 20, 14, 11), "东翼": (38, 15, 0, 10, 12, 7),
                   "西翼": (8, 15, 0, 10, 12, 7)},
        "layered": {"高层": (14, 6, 0, 18, 12, 14), "裙房": (10, 20, 0, 30, 12, 6),
                    "地景": (6, 32, 0, 38, 6, 2)},
        "hall": {"大厅": (16, 14, 0, 24, 14, 12), "侧翼": (8, 4, 0, 40, 8, 6)},
    }
    return table.get(family) or table["cluster"]


# --------------------------------------------------------------------------
# 两种交付形态：静态四联 / 动画分镜
# --------------------------------------------------------------------------
def strip(concept: Dict[str, Any], discipline: str = "architecture", *,
          width: int = 700, height: int = 460,
          theme: Optional[Dict[str, str]] = None,
          sector: str = "") -> str:
    """四步静态图版：一页看完整条推敲，适合放进提案。"""
    p = plan(concept, discipline, sector=sector)
    if not p.ok:
        return ""
    pal = _pal(theme)
    n = max(1, len(p.steps))
    # 四步横排会把每一格压成竖长条，等距图上下留一大片空白。
    # 三步以上走两列网格，格子接近 3:2，图才填得满。
    cols = 2 if n >= 3 else n
    rows = (n + cols - 1) // cols
    cw, chh = width / cols, height / rows
    iw = 460
    ih = max(240, int(iw * (chh - 22) / max(cw, 1)))
    s = dia.Svg(width, height, title=f"{concept.get('concept_name', '')} · 概念推敲")
    for i, step in enumerate(p.steps):
        cx = (i % cols) * cw
        cy = (i // cols) * chh
        body = _scene_body(step, p, pal, iw, ih, concept)
        s.body.append(
            f'<svg x="{cx + 6:.1f}" y="{cy + 4:.1f}" width="{cw - 14:.1f}" '
            f'height="{chh - 26:.1f}" viewBox="0 0 {iw} {ih}" '
            f'preserveAspectRatio="xMidYMid meet">{body}</svg>')
        # 只写序号：步骤名与解释由页面排版，图里再写一遍就是重复
        s.text(cx + 10, cy + chh - 8, step.n, size=11.0, color=pal["accent"],
               weight="600")
    return s.render()


def scenes(concept: Dict[str, Any], discipline: str = "architecture", *,
           width: int = 720, height: int = 500,
           theme: Optional[Dict[str, str]] = None,
           sector: str = "") -> List[str]:
    """每一步一张独立 SVG，给动画用。"""
    p = plan(concept, discipline, sector=sector)
    if not p.ok:
        return []
    pal = _pal(theme)
    out: List[str] = []
    for step in p.steps:
        body = _scene_body(step, p, pal, width, height, concept)
        out.append(f'<svg viewBox="0 0 {width} {height}" '
                   f'xmlns="http://www.w3.org/2000/svg" '
                   f'preserveAspectRatio="xMidYMid meet">{body}</svg>')
    return out


def _pal(theme: Optional[Dict[str, str]] = None) -> Pal:
    """图版配色：以 `layout.PAL` 为底，页面主题覆盖同名 key。

    与 main plate 共用同一张色表，图里不会出现主图没有的颜色。
    """
    pal: Pal = dict(layout_mod.PAL)
    pal.update({"mass": "#E4EDE3", "court": "#EFE3D2", "green": "#DCE6D3"})
    for k, v in (theme or {}).items():
        if k in pal and isinstance(v, str) and v.startswith("#"):
            pal[k] = v
    return pal


__all__ = ["DISCIPLINE_CN", "DISCIPLINE_STEPS", "Plan", "Step", "STEP_INDEX",
           "applicable", "plan", "scenes", "strip"]
