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
from .iso import Iso, draw_box, draw_ground, draw_shadow, tree

#: 专业 → 推敲主线。名字不是装饰：它决定画什么、讲解什么。
DISCIPLINE_STEPS: Dict[str, Tuple[str, ...]] = {
    "architecture": ("场地与限界", "体量分解", "加入要素", "结果形态"),
    "interior": ("功能重组", "空间序列", "界面与通透", "核心空间"),
    "landscape": ("场地与边界", "空间层次", "园路与节点", "水景与种植"),
}

DISCIPLINE_CN = {"architecture": "建筑", "interior": "室内", "landscape": "景观"}

#: 室内/景观的"家族 → 版面原型"。只决定示意图的几何关系，不声称尺寸。
PLAN_KIND = {
    "cluster": "bands", "linear": "bands", "layered": "bands",
    "courtyard": "ring", "radial": "ring", "hall": "ring", "grid": "bands",
}


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
    t = " ".join(str(text or "").split())
    if len(t) <= n:
        return t
    for sep in ("，", "、", "："):
        head = t.split(sep)[0]
        if 6 <= len(head) <= n:
            return head
    return t[: n - 1] + "…"


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
    core = _clauses(concept.get("concept_statement"), 1, 30)
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
    disc = plan_obj.discipline
    if disc == "architecture":
        return _arch_body(step, plan_obj, pal, w, h)
    if disc == "interior":
        return _interior_body(step, plan_obj, pal, w, h, concept or {})
    return _land_body(step, plan_obj, pal, w, h)


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


# ---------------- 室内：标准层示意 ----------------
def _band_labels(concept: Dict[str, Any], p: Plan) -> Tuple[str, str, str]:
    """三条带的短标签：按概念自己声明的排布方式取，不凭空造房间名。"""
    proto = _proto(concept)
    layout = str(proto.get("plan_layout") or proto.get("plan_strategy") or "")
    table = {
        "public_core": ("公共核", "客房走廊", "后场与客房"),
        "guest_wing": ("客房", "走廊", "客房"),
        "tech_core": ("门诊与候诊", "走廊", "医技"),
        "dual_corridor": ("洁净区", "走廊", "污染区"),
        "medical_street": ("门诊", "医疗街", "医技"),
        "cluster_atrium": ("教学", "共享", "专用/办公"),
        "linear_corridor": ("教学", "连廊", "办公/后勤"),
        "process_line": ("生产", "通道", "仓储"),
        "stacked_module": ("生产", "通道", "仓储"),
    }
    for key, val in table.items():
        if key in layout:
            return val
    if p.family in ("courtyard", "radial"):
        return ("使用空间", "院/核", "使用空间")
    got = p.labels[:3]
    got += ["交通", "辅助"][: max(0, 3 - len(got))]
    return (got[0][:9], got[1][:9], got[2][:9])


def _interior_body(step: Step, p: Plan, pal: Pal, w: int, h: int,
                   concept: Optional[Dict[str, Any]] = None) -> str:
    """室内标准层示意：三条带 + 每一步该看的那一件事。

    这不是平面图，是"关系图"：带的名字来自概念自己声明的排布方式，
    几何只用来表达"谁挨着谁"，不声称尺寸。
    """
    s = _canvas(w, h)
    x0, y0, bw, bh = _frame(s, w, h, pal, pad=14)
    ink = pal.get("ink", "#1E2328")
    line = pal.get("line", "#D6D2C6")
    accent = pal.get("accent", "#2F5D45")
    mass, mass2 = pal.get("mass", "#E7EDE6"), pal.get("mass2", "#C9DCC8")
    top, mid, bot = _band_labels(concept or {}, p)

    # 三条带：公共／交通／私密。高度比只表达"主次"，不是尺寸。
    bh_top, bh_mid = bh * 0.34, bh * 0.12
    y_top = y0 + bh * 0.06
    y_mid = y_top + bh_top + bh * 0.03
    y_bot = y_mid + bh_mid + bh * 0.03
    s.rect(x0 + bw * 0.05, y_top, bw * 0.90, bh_top, fill=mass, stroke=ink, sw=1.0)
    s.rect(x0 + bw * 0.05, y_mid, bw * 0.90, bh_mid, fill="#FBFAF5", stroke=line,
           sw=1.0)
    s.rect(x0 + bw * 0.05, y_bot, bw * 0.90, bh_top, fill=mass, stroke=ink, sw=1.0)
    _label(s, x0 + bw * 0.07, y_top + 22, top, size=10.0, color=ink)
    _label(s, x0 + bw * 0.07, y_mid + bh_mid * 0.74, mid, size=9.5, color=ink)
    _label(s, x0 + bw * 0.07, y_bot + 22, bot, size=10.0, color=ink)

    if step.scene == "zones":
        # 竖向分隔：让"重新分组"这件事看得见
        for i in range(1, 3):
            cx = x0 + bw * (0.05 + 0.90 * i / 3)
            s.line(cx, y_top, cx, y_top + bh_top, stroke=line, sw=1.0, dash="5 4")
            s.line(cx, y_bot, cx, y_bot + bh_top, stroke=line, sw=1.0, dash="5 4")
    elif step.scene == "sequence":
        pts = [(x0 + bw * 0.10, y0 + bh * 0.96), (x0 + bw * 0.26, y_mid + bh_mid / 2),
               (x0 + bw * 0.58, y_mid + bh_mid / 2), (x0 + bw * 0.84, y_top + 26)]
        s.polyline(pts, stroke=accent, sw=2.0, arrow=True)
        for i, pt in enumerate(pts):
            s.circle(pt[0], pt[1], 3.0, fill=accent)
            s.text(pt[0] + 6, pt[1] - 8, f"{i + 1}", size=9.5, color=accent)
        s.text(x0 + bw * 0.10, y0 + bh * 0.96 + 12, "入口", size=9.5, color=accent)
    elif step.scene == "threshold":
        # 界面开窗：画在带的外侧，不压在文字上
        for i in range(4):
            fx = x0 + bw * (0.52 + i * 0.11)
            s.line(fx, y_top, fx, y_top - 9, stroke=accent, sw=2.6)
        s.text(x0 + bw * 0.05, y_top + bh_top - 8, "界面开窗 / 进深采光", size=9.0,
               color=accent)
    elif step.scene == "core":
        # 核心空间：指"公共核"那一条，而不是走廊
        s.rect(x0 + bw * 0.05, y_top, bw * 0.90, bh_top, fill="none", stroke=accent,
               sw=2.2)
        s.text(x0 + bw * 0.90, y_top + bh_top - 8, "核心：{}".format(top), size=9.0,
               color=accent, anchor="end")
    return "".join(s.body)


def _land_body(step: Step, p: Plan, pal: Pal, w: int, h: int) -> str:
    """景观总平面示意：场地、层次、游线、水与种植，一步步叠上去。"""
    s = _canvas(w, h)
    x0, y0, bw, bh = _frame(s, w, h, pal, pad=14)
    ink = pal.get("ink", "#1E2328")
    line = pal.get("line", "#D6D2C6")
    accent = pal.get("accent", "#2F5D45")
    labels = (p.labels + ["", "", ""])[:3]

    # 建筑边界：院子必须有房子作参照，否则看不懂朝向与尺度
    s.rect(x0 + bw * 0.06, y0 + bh * 0.05, bw * 0.26, bh * 0.15,
           fill=pal.get("mass", "#E9E4D6"), stroke=ink, sw=1.0)
    _label(s, x0 + bw * 0.06 + 8, y0 + bh * 0.05 + 17, "建筑", size=9.5, color=ink)

    # 主入口始终画：入口方向是景观的第一条约束
    s.line(x0 + bw * 0.62, y0 + bh * 1.0, x0 + bw * 0.62, y0 + bh * 0.90,
           stroke=accent, sw=1.8, arrow=True)
    _label(s, x0 + bw * 0.62 + 12, y0 + bh * 0.93, "主入口", size=9.0, color=accent)

    if step.scene == "site":
        s.rect(x0 + bw * 0.04, y0 + bh * 0.03, bw * 0.92, bh * 0.94, fill="none",
               stroke=accent, sw=1.2, dash="7 5")
        _label(s, x0 + bw * 0.34, y0 + bh * 0.10, labels[0] or "场地边界",
               size=10.5, color=ink)
        return "".join(s.body)

    # 空间层次：三条带，越靠房子越"前"
    band_y = (0.24, 0.44, 0.64)
    names = ("前院", "中景", "背景种植")
    for i, ry in enumerate(band_y):
        s.rect(x0 + bw * 0.05, y0 + bh * ry, bw * 0.90, bh * 0.18,
               fill=pal.get("mass", "#E7EDE6"), stroke="none", sw=0,
               opacity=0.22 + i * 0.08)
        _label(s, x0 + bw * 0.06, y0 + bh * ry + 14, names[i], size=9.0, color=ink)
    _label(s, x0 + bw * 0.34, y0 + bh * 0.10, labels[0], size=10.0, color=ink)

    if step.scene == "layers":
        s.line(x0 + bw * 0.32, y0 + bh * 0.22, x0 + bw * 0.88, y0 + bh * 0.72,
               stroke=accent, sw=1.1, dash="6 5", arrow=True)
        _label(s, x0 + bw * 0.60, y0 + bh * 0.40, "视线", size=9.5, color=accent)
        if len(labels) > 1 and labels[1]:
            _label(s, x0 + bw * 0.06, y0 + bh * 0.88, labels[1], size=9.0, color=ink)

    if step.scene in ("paths", "water"):
        if PLAN_KIND.get(p.family) == "ring":
            cx, cy = x0 + bw * 0.58, y0 + bh * 0.58
            pts = [(cx + bw * 0.24 * math.cos(2 * math.pi * i / 30),
                    cy + bh * 0.22 * math.sin(2 * math.pi * i / 30)) for i in range(30)]
            s.polygon(pts, fill="none", stroke="#CDC2A8", sw=5.0)
            s.polygon(pts, fill="none", stroke="#B3A88D", sw=0.9, dash="9 7")
        else:
            s.polyline([(x0 + bw * 0.12, y0 + bh * 0.90), (x0 + bw * 0.44, y0 + bh * 0.60),
                        (x0 + bw * 0.72, y0 + bh * 0.62), (x0 + bw * 0.90, y0 + bh * 0.36)],
                       stroke="#CDC2A8", sw=5.0, arrow=False)
        if step.scene == "water" and len(labels) > 1 and labels[1]:
            _label(s, x0 + bw * 0.06, y0 + bh * 0.88, labels[1], size=9.0, color=ink)

    if step.scene == "water":
        cx, cy = x0 + bw * 0.58, y0 + bh * 0.56
        s.polygon([(cx + bw * 0.13 * math.cos(2 * math.pi * i / 18),
                    cy + bh * 0.10 * math.sin(2 * math.pi * i / 18)) for i in range(18)],
                  fill="#DDE7EE", stroke="#9FB3BF", sw=1.0)
        _label(s, cx, cy + 4, "水面", size=9.5, color="#5E7484", anchor="middle")
        for tx, ty, tr in ((x0 + bw * 0.16, y0 + bh * 0.70, 0.042),
                           (x0 + bw * 0.88, y0 + bh * 0.26, 0.038),
                           (x0 + bw * 0.42, y0 + bh * 0.86, 0.034),
                           (x0 + bw * 0.74, y0 + bh * 0.84, 0.032)):
            s.circle(tx, ty, min(w, h) * tr, fill=pal.get("green", "#DCE6D3"),
                     stroke="#8FA684", sw=0.9)
    return "".join(s.body)


# --------------------------------------------------------------------------
# 两种交付形态：静态四联 / 动画分镜
# --------------------------------------------------------------------------
def strip(concept: Dict[str, Any], discipline: str = "architecture", *,
          width: int = 700, height: int = 460,
          theme: Optional[Dict[str, str]] = None) -> str:
    """四步静态图版：一页看完整条推敲，适合放进提案。"""
    p = plan(concept, discipline)
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
           theme: Optional[Dict[str, str]] = None) -> List[str]:
    """每一步一张独立 SVG，给动画用。"""
    p = plan(concept, discipline)
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
    pal = {"paper": "#FAF8F3", "ink": "#1E2328", "muted": "#6E736A",
           "line": "#D6D2C6", "accent": "#2F5D45", "mass": "#E4EDE3",
           "mass2": "#C9DCC8", "ground": "#F2F0E8", "court": "#EFE3D2",
           "green": "#C6D6BE"}
    for k, v in (theme or {}).items():
        if k in pal and isinstance(v, str) and v.startswith("#"):
            pal[k] = v
    return pal


__all__ = ["DISCIPLINE_CN", "DISCIPLINE_STEPS", "PLAN_KIND", "Plan", "Step",
           "applicable", "plan", "scenes", "strip"]
